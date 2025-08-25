import express from 'express';
import { supabase } from '../utils/supabaseClient.js';
import {
  fetchBingLinks,
  scrapeProductInfo,
  fetchSdsByName,
  searchWithManualData,
} from '../utils/scraper.js';
import { isValidCode, isValidName, isValidSize } from '../utils/validation.js';
import logger from '../utils/logger.js';
import puppeteer from 'puppeteer-extra';
import StealthPlugin from 'puppeteer-extra-plugin-stealth';
import { triggerAutoSdsParsing } from '../utils/autoSdsParsing.js';

const router = express.Router();
puppeteer.use(StealthPlugin());

export type ScrapedProduct = {
  name?: string;
  contents_size_weight?: string;
  url: string;
  size?: string;
  sdsUrl?: string;
};

// --- Helpers -----------------------------------------------------------------
function isProbablyA1Base64(s: string): boolean {
  if (!s || s.length < 3) return false;
  const c0 = s.charCodeAt(0);
  const c1 = s.charCodeAt(1);
  const firstIsLetter = (c0 >= 65 && c0 <= 90) || (c0 >= 97 && c0 <= 122);
  const secondIsDigit = c1 >= 48 && c1 <= 57; // '0'-'9'
  return firstIsLetter && secondIsDigit;
}

function normaliseUrl(u: string): string | null {
  if (!u) return null;
  let s = String(u).trim();
  try {
    const parsed = new URL(s);
    // Unwrap Bing redirect links: https://www.bing.com/ck/a?...&u=<encoded>
    if (parsed.hostname.includes('bing.com') && parsed.searchParams.has('u')) {
      let target = parsed.searchParams.get('u') || '';
      try {
        if (isProbablyA1Base64(target)) {
          target = Buffer.from(target.slice(2), 'base64').toString('utf8');
        } else {
          target = decodeURIComponent(target);
        }
      } catch {}
      s = target.trim();
    }
  } catch {}
  try {
    if (isProbablyA1Base64(s)) {
      const decoded = Buffer.from(s.slice(2), 'base64').toString('utf8');
      if (decoded.startsWith('http://') || decoded.startsWith('https://')) s = decoded;
    }
  } catch {}
  if (!(s.startsWith('http://') || s.startsWith('https://'))) return null;
  if (s.includes('dummy.local')) return null; // kill placeholder host
  return s;
}

// --- Routes ------------------------------------------------------------------
router.post('/sds-by-name', async (req, res) => {
  const { name, size } = req.body || {};
  if (!isValidName(name)) return res.status(403).json({ error: 'Invalid name' });

  try {
    logger.info({ name, size }, '[SDS] Fetching by name');
    const { sdsUrl, topLinks } = await fetchSdsByName(name, size);
    logger.info({ name, size, sdsUrl, topLinks }, '[SDS] Fetched SDS URL and top links');
    return res.json({ sdsUrl, topLinks });
  } catch (err: any) {
    logger.error({ err: String(err), name }, '[SDS] Failed');
    return res
      .status(502)
      .json({ error: 'SDS_LOOKUP_FAILED', message: String(err?.message || err) });
  }
});

router.post('/', async (req, res) => {
  const requestStartTime = Date.now();
  const { code, userId, name, size } = req.body || {};
  if (!isValidCode(code)) return res.status(403).json({ error: 'Invalid barcode' });

  // Validate manual entry fields if provided
  const isManualEntry = !!(name && size);
  if (isManualEntry) {
    if (!isValidName(name)) return res.status(403).json({ error: 'Invalid name' });
    if (!isValidSize(size)) return res.status(403).json({ error: 'Invalid size' });
  }

  logger.info(
    { code, userId, name, size, isManualEntry, timestamp: Date.now() },
    '[SCAN] Processing scan request'
  );

  try {
    // 1) First check if user already has this item in their watchlist
    if (userId) {
      // Get product by barcode first
      const { data: product, error: productError } = await supabase
        .from('product')
        .select('id, name')
        .eq('barcode', code)
        .maybeSingle();

      if (!productError && product) {
        // Check if user already has this product in their watchlist
        const { data: watchlistItem, error: watchlistError } = await supabase
          .from('user_chemical_watch_list')
          .select('id, created_at')
          .eq('user_id', userId)
          .eq('product_id', product.id)
          .maybeSingle();

        if (!watchlistError && watchlistItem) {
          logger.info(
            { code, productId: product.id, userId },
            '[SCAN] Item already in user watchlist'
          );
          return res.json({
            code,
            alreadyInWatchlist: true,
            product: product,
            watchlistEntry: {
              id: watchlistItem.id,
              created_at: watchlistItem.created_at,
            },
            message: `"${product.name}" is already in your chemical register list`,
          });
        }
      }
    }

    // 2) DB lookup for product (continue with normal flow if no userId provided)
    const dbLookupStart = Date.now();
    const { data: existing, error: fetchErr } = await supabase
      .from('product')
      .select('*')
      .eq('barcode', code)
      .maybeSingle();

    logger.info(
      { code, dbLookupTime: Date.now() - dbLookupStart },
      '[SCAN] Database lookup completed'
    );

    if (fetchErr) return res.status(500).json({ error: fetchErr.message });

    if (existing) {
      let updated = { ...existing } as typeof existing & { sds_url?: string };

      // Only fetch SDS if it's missing AND we have a product name
      if (!existing.sds_url && existing.name) {
        try {
          logger.info(
            { name: existing.name },
            '[SCAN] Fetching missing SDS URL for existing product'
          );
          const { sdsUrl: foundSds } = await fetchSdsByName(
            existing.name,
            existing.contents_size_weight || undefined
          );
          logger.info({ name: existing.name, foundSds }, '[SCAN] Fallback SDS result');
          if (foundSds) {
            const updateResult = await supabase
              .from('product')
              .update({ sds_url: foundSds })
              .eq('barcode', code)
              .select()
              .maybeSingle();
            logger.info({ updateResult }, '[SCAN] Updated product with SDS');
            updated.sds_url = foundSds;
            // Trigger auto-SDS parsing for newly added SDS URL
            if (updated.id) {
              logger.info(
                { productId: updated.id },
                '[SCAN] Triggering auto-SDS parsing for updated product'
              );
              triggerAutoSdsParsing(updated.id, { delay: 1000 });
            }
          }
        } catch (err: any) {
          logger.warn({ err: String(err) }, '[SCAN] SDS enrichment failed');
        }
      }

      logger.info(
        { code, updated },
        '[SCAN] Returning existing product from database (no scraping)'
      );
      return res.json({
        code,
        product: updated,
        existingInDatabase: true,
        scraped: [
          {
            url: '',
            name: updated.name || '',
            size: updated.contents_size_weight || '',
            sdsUrl: updated.sds_url || '',
          },
        ],
        message: 'Product found in database',
      });
    }

    // 2) Handle manual entry vs web scraping
    let top: ScrapedProduct;
    let scraped: ScrapedProduct[] = [];

    if (isManualEntry) {
      // For manual entry, use provided data directly and search for SDS
      logger.info({ code, name, size }, '[SCAN] Using manual entry data');

      const manualResult = await searchWithManualData(name, size, code);

      top = {
        name: manualResult.name,
        contents_size_weight: manualResult.contents_size_weight,
        size: manualResult.contents_size_weight,
        url: '',
        sdsUrl: manualResult.sdsUrl,
      };

      scraped = [top];
    } else {
      // Original web scraping logic for barcode-only scans
      const searchStart = Date.now();
      const urls = await fetchBingLinks(code);
      logger.info(
        { code, rawUrls: urls, searchTime: Date.now() - searchStart },
        '[SCAN] Raw URLs from search'
      );

      const cleaned = [...new Set((urls || []).map(normaliseUrl).filter(Boolean))] as string[];
      logger.info({ code, cleaned }, '[SCAN] Normalised URLs for scraping');

      const scrapingStart = Date.now();

      // Try scraping sequentially instead of parallel for better control
      scraped = [];
      let foundGoodResult = false;

      for (const u of cleaned.slice(0, 5)) {
        if (foundGoodResult) break; // Stop when we find a good result

        const startTime = Date.now();
        try {
          const r = (await scrapeProductInfo(u, code)) as ScrapedProduct;
          const duration = Date.now() - startTime;
          logger.info({ url: u, duration, hasName: !!r.name }, '[SCAN] scrape completed');
          scraped.push(r);

          // If we found a good result with name and size, we can stop
          if (r.name && r.contents_size_weight) {
            foundGoodResult = true;
            logger.info({ code, url: u }, '[SCAN] Found complete product info, stopping scraping');
          }
        } catch (err: any) {
          const duration = Date.now() - startTime;
          logger.warn({ url: u, err: String(err), duration }, '[SCAN] scrape failed');
          scraped.push({ url: u, name: '', size: '', sdsUrl: '' });
        }
      }

      const totalScrapingTime = Date.now() - scrapingStart;
      logger.info({ code, scraped, totalScrapingTime }, '[SCAN] Scraped results');
      top = scraped.find(s => s?.name) ||
        scraped.find(s => s?.sdsUrl) || {
          name: '',
          size: '',
          sdsUrl: '',
          url: '',
        };
      logger.info({ top }, '[SCAN] Top scraped result');
    }

    // Only run fallback SDS search for non-manual entries (manual entries already searched for SDS)
    if (!isManualEntry && !top.sdsUrl && top.name) {
      try {
        const sdsSearchStart = Date.now();
        logger.info({ name: top.name }, '[SCAN] Fetching SDS URL via fallback');
        const { sdsUrl: fallbackSds, topLinks } = await fetchSdsByName(
          top.name,
          top.size ?? top.contents_size_weight
        );
        const sdsSearchTime = Date.now() - sdsSearchStart;
        logger.info(
          { name: top.name, fallbackSds, topLinks, sdsSearchTime },
          '[SCAN] Fallback SDS result'
        );
        if (fallbackSds) top.sdsUrl = fallbackSds;
      } catch (err: any) {
        logger.warn({ name: top.name, err: String(err) }, '[SCAN] SDS fallback failed');
      }
    }

    const insert = await supabase
      .from('product')
      .upsert({
        barcode: code,
        name: top.name || null,
        contents_size_weight: top.size ?? top.contents_size_weight ?? null,
        sds_url: top.sdsUrl || null,
      })
      .select()
      .maybeSingle();

    const data = insert.data;
    const error = insert.error;

    logger.info({ code, data, error }, '[SCAN] Final database write result');
    if (error) return res.status(500).json({ error: error.message });

    // Trigger auto-SDS parsing if we found an SDS URL
    if (data?.sds_url && data?.id) {
      logger.info({ productId: data.id }, '[SCAN] Triggering auto-SDS parsing for new product');
      triggerAutoSdsParsing(data.id, { delay: 2000 }); // 2 second delay for new products
    }

    const totalRequestTime = Date.now() - requestStartTime;
    logger.info({ code, totalRequestTime, isManualEntry }, '[SCAN] Request completed');

    return res.json({
      code,
      scraped,
      product: data,
      isManualEntry,
      message: isManualEntry ? 'Product created from manual entry' : 'Product found via web search',
    });
  } catch (err: any) {
    logger.error({ code, err: String(err) }, '[SCAN] failed');
    return res.status(502).json({ error: 'SCAN_FAILED', message: String(err?.message || err) });
  }
});

export default router;
