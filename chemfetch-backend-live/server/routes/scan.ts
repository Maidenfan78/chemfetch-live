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

function summariseLinks(links: string[], limit = 6): string[] {
  const summary: string[] = [];
  for (const link of links) {
    if (!link) continue;
    if (summary.length >= limit) break;
    try {
      const parsed = new URL(link);
      const trimmedPath = parsed.pathname?.replace(/\/$/, '') || '';
      summary.push(`${parsed.hostname}${trimmedPath}`);
    } catch {
      summary.push(link.slice(0, 120));
    }
  }
  return summary;
}

const RETAIL_DOMAINS = ['ebay.', 'amazon.', 'aliexpress.', 'gumtree.', 'etsy.', 'facebook.', 'pinterest.'];
const HIGH_CONFIDENCE_KEYWORDS = ['isocol', 'chemist', 'pharmacy', 'multipurpose', 'rubbing alcohol'];

function scoreResult(result: ProductScrapeResult): number {
  let score = 0;
  const name = result.name?.toLowerCase() || '';
  const url = result.url?.toLowerCase() || '';

  if (name) score += 3;
  if (result.contents_size_weight || result.size) score += 3;
  if (result.sdsUrl) score += 2;
  if (name.length && name.length < 80) score += 1;

  if (/(buy|shop|order|purchase|sale|special)/.test(name)) score -= 3;
  if (/payment|afterpay|zip|klarna/.test(name)) score -= 2;

  if (url) {
    if (RETAIL_DOMAINS.some(domain => url.includes(domain))) score -= 4;
    if (url.includes('isocol')) score += 2;
    if (url.includes('.gov') || url.includes('.edu')) score += 1;
  }

  if (HIGH_CONFIDENCE_KEYWORDS.some(keyword => name.includes(keyword))) score += 2;

  return score;
}

function pickBestResult(results: ProductScrapeResult[]): ProductScrapeResult | null {
  if (results.length === 0) return null;
  const scored = [...results].sort((a, b) => scoreResult(b) - scoreResult(a));
  const bestCandidate = scored[0];
  if (!bestCandidate) return null;
  if (!bestCandidate.name) {
    return (
      results.find(item => item.name && item.contents_size_weight) ||
      results.find(item => item.name) ||
      bestCandidate
    );
  }
  return bestCandidate;
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
        logger.info(
          { code, query, linkCount: links.length, topLinks: summariseLinks(links, 6) },
          '[SCAN] Bing links fetched',
        );
        collected.push(...links);
      }

      const expanded: string[] = [];
      for (const link of collected) {
        const extras = await expandSiteSearchPage(link, 4);
        expanded.push(...extras);
      }

      const candidates = dedupeStrings([...collected, ...expanded]).slice(0, 12);
      logger.info(
        { code, candidateCount: candidates.length, candidates: summariseLinks(candidates, 10) },
        '[SCAN] Candidate URLs prepared',
      );
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

      if (scraped.length > 0) {
        logger.info(
          {
            code,
            scrapedCount: scraped.length,
            sampledResults: scraped.slice(0, 3).map(item => ({
              name: item.name,
              size: item.contents_size_weight || item.size || '',
              hasSds: Boolean(item.sdsUrl),
              source: item.url,
            })),
          },
          '[SCAN] Scraped product results',
        );
      }
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

    if (!best.sdsUrl) {
      const attempts: Array<{ name: string; size: string }> = [];
      const seen = new Set<string>();
      const normaliseCandidate = (value?: string | null) => (typeof value === 'string' ? value.trim() : '');
      const registerCandidate = (candidateName?: string | null, candidateSize?: string | null) => {
        const trimmedName = normaliseCandidate(candidateName);
        if (!trimmedName) return;
        const trimmedSize = normaliseCandidate(candidateSize);
        const key = `${trimmedName.toLowerCase()}|${trimmedSize.toLowerCase()}`;
        if (seen.has(key)) return;
        seen.add(key);
        attempts.push({ name: trimmedName, size: trimmedSize });
      };

      registerCandidate(best.name, best.contents_size_weight || best.size);
      scraped.slice(0, 6).forEach(item => {
        registerCandidate(item.name, item.contents_size_weight || item.size);
      });
      if (existing?.name) {
        registerCandidate(existing.name, existing.contents_size_weight);
      }
      if (isManualEntry) {
        registerCandidate(String(name), String(size));
      }

      if (best.name && /isocol/i.test(best.name)) {
        registerCandidate('Isocol Rubbing Alcohol Antiseptic', best.contents_size_weight || best.size);
        registerCandidate('Isocol Rubbing Alcohol', best.contents_size_weight || best.size);
      }

      for (const attempt of attempts.slice(0, 8)) {
        try {
          const { sdsUrl } = await fetchSdsByNameSimple(attempt.name, attempt.size);
          if (sdsUrl) {
            best.sdsUrl = sdsUrl;
            logger.info({ code, attemptName: attempt.name, attemptSize: attempt.size || null, sdsUrl }, '[SCAN] SDS URL discovered');
            break;
          }
        } catch (err) {
          logger.warn({ code, attemptName: attempt.name, err: String(err) }, '[SCAN] SDS lookup attempt failed');
        }
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
