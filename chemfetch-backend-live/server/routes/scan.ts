import express from 'express';
import { supabase } from '../utils/supabaseClient.js';
import {
  fetchBingLinks,
  scrapeProductInfo,
  expandSiteSearchPage,
  fetchSdsByNameSimple,
  searchWithManualData,
  type ProductScrapeResult,
} from '../utils/scraper.js';
import { isValidCode, isValidName, isValidSize } from '../utils/validation.js';
import logger from '../utils/logger.js';
import { triggerAutoSdsParsing } from '../utils/autoSdsParsing.js';

const router = express.Router();

function dedupeStrings(items: string[]): string[] {
  const seen = new Set<string>();
  const ordered: string[] = [];
  for (const item of items) {
    const trimmed = item?.trim();
    if (!trimmed) continue;
    if (seen.has(trimmed)) continue;
    seen.add(trimmed);
    ordered.push(trimmed);
  }
  return ordered;
}

function pickBestResult(results: ProductScrapeResult[]): ProductScrapeResult | null {
  if (results.length === 0) return null;
  return (
    results.find(item => item.name && item.contents_size_weight) ||
    results.find(item => item.name) ||
    results[0] ||
    null
  );
}

router.post('/', async (req, res) => {
  const { code, userId, name, size } = req.body || {};

  if (!isValidCode(code)) {
    return res.status(403).json({ error: 'Invalid barcode' });
  }

  const isManualEntry = Boolean(name && size);
  if (isManualEntry) {
    if (!isValidName(name)) return res.status(403).json({ error: 'Invalid name' });
    if (!isValidSize(size)) return res.status(403).json({ error: 'Invalid size' });
  }

  logger.info({ code, userId, isManualEntry }, '[SCAN] Processing scan request');

  try {
    if (userId) {
      const { data: existingProduct, error: productError } = await supabase
        .from('product')
        .select('id, name')
        .eq('barcode', code)
        .maybeSingle();

      if (!productError && existingProduct) {
        const { data: watchlistItem } = await supabase
          .from('user_chemical_watch_list')
          .select('id, created_at')
          .eq('user_id', userId)
          .eq('product_id', existingProduct.id)
          .maybeSingle();

        if (watchlistItem) {
          logger.info({ code, userId }, '[SCAN] Item already in user watchlist');
          return res.json({
            code,
            alreadyInWatchlist: true,
            product: existingProduct,
            watchlistEntry: watchlistItem,
            message: 'Item already exists in your chemical register list',
          });
        }
      }
    }

    const { data: existing, error: fetchErr } = await supabase
      .from('product')
      .select('id, barcode, name, contents_size_weight, sds_url')
      .eq('barcode', code)
      .maybeSingle();

    if (fetchErr) return res.status(500).json({ error: fetchErr.message });

    let scraped: ProductScrapeResult[] = [];
    let best: ProductScrapeResult | null = null;

    if (isManualEntry) {
      const manualResult = await searchWithManualData(String(name), String(size), String(code));
      scraped = [manualResult];
      best = manualResult;
    } else {
      const queries = [`Item ${code}`, `${code} barcode`, `${code} product`];

      const collected: string[] = [];
      for (const query of queries) {
        const links = await fetchBingLinks(query, 6);
        logger.info({ code, query, linkCount: links.length }, '[SCAN] Bing links fetched');
        collected.push(...links);
      }

      const expanded: string[] = [];
      for (const link of collected) {
        const extras = await expandSiteSearchPage(link, 4);
        expanded.push(...extras);
      }

      const candidates = dedupeStrings([...collected, ...expanded]).slice(0, 12);
      logger.info({ code, candidateCount: candidates.length }, '[SCAN] Candidate URLs prepared');
      scraped = [];

      for (const candidate of candidates) {
        try {
          const result = await scrapeProductInfo(candidate, String(code));
          scraped.push(result);
        } catch (err) {
          logger.warn({ code, candidate, err: String(err) }, '[SCAN] scrape failed');
        }
      }

      best = pickBestResult(scraped);
    }

    if (!best) {
      best = {
        url: '',
        name: isManualEntry ? String(name).trim() : '',
        contents_size_weight: isManualEntry ? String(size).trim() : '',
        size: isManualEntry ? String(size).trim() : '',
        sdsUrl: null,
      };
    }

    if (!best.sdsUrl && best.name) {
      try {
        const { sdsUrl } = await fetchSdsByNameSimple(best.name, best.contents_size_weight);
        if (sdsUrl) best.sdsUrl = sdsUrl;
      } catch (err) {
        logger.warn({ code, err: String(err) }, '[SCAN] SDS lookup fallback failed');
      }
    }

    const payload = {
      barcode: code,
      name: best.name || existing?.name || null,
      contents_size_weight: best.contents_size_weight || existing?.contents_size_weight || null,
      sds_url: best.sdsUrl || existing?.sds_url || null,
    };

    const { data: upserted, error: upsertError } = await supabase
      .from('product')
      .upsert(payload, { onConflict: 'barcode' })
      .select()
      .maybeSingle();

    if (upsertError) return res.status(500).json({ error: upsertError.message });

    if (upserted?.sds_url && upserted?.id) {
      triggerAutoSdsParsing(upserted.id, { delay: 2000 });
    }

    const message = isManualEntry
      ? 'Product created from manual entry'
      : best.name
        ? 'Product found via web search'
        : 'No product details discovered';

    logger.info({ code, productId: upserted?.id, message }, '[SCAN] Request completed');

    return res.json({
      code,
      scraped,
      product: upserted,
      isManualEntry,
      message,
    });
  } catch (err: any) {
    logger.error({ code, err: String(err) }, '[SCAN] failed');
    return res.status(502).json({ error: 'SCAN_FAILED', message: String(err?.message || err) });
  }
});

export default router;
