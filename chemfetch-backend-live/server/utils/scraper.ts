import axios from 'axios';
import * as cheerio from 'cheerio';
import logger from './logger.js';

const USER_AGENT =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36';
const REQUEST_TIMEOUT = 8000;
const SIZE_PATTERN =
  /\b\d+(?:[.,]\d+)?\s?(?:ml|mL|l|L|litre|liter|g|kg|oz|fl\s?oz|pack|packs|tablet|tablets)\b/i;

export interface ProductScrapeResult {
  url: string;
  name: string;
  contents_size_weight: string;
  size?: string;
  sdsUrl: string | null;
}

function cleanText(value?: string | null): string {
  if (!value) return '';
  return value.replace(/\s+/g, ' ').trim();
}

function dedupe(items: string[]): string[] {
  const seen = new Set<string>();
  const ordered: string[] = [];
  for (const item of items) {
    if (!seen.has(item)) {
      seen.add(item);
      ordered.push(item);
    }
  }
  return ordered;
}

function normaliseLink(raw: string | undefined | null, base?: string): string | null {
  if (!raw) return null;
  let href = raw.trim();
  if (!href) return null;
  if (href.startsWith('javascript:')) return null;
  if (href.startsWith('//')) href = `https:${href}`;
  if (base && href.startsWith('/')) {
    try {
      href = new URL(href, base).toString();
    } catch {
      return null;
    }
  }
  try {
    const parsed = new URL(href);
    if (parsed.hostname.includes('bing.com') && parsed.searchParams.has('u')) {
      const target = parsed.searchParams.get('u');
      if (target) {
        try {
          const decoded = decodeURIComponent(target);
          if (/^https?:\/\//i.test(decoded)) href = decoded;
        } catch {
          /* ignore */
        }
      }
    }
  } catch {
    if (!base) return null;
    try {
      href = new URL(href, base).toString();
    } catch {
      return null;
    }
  }
  if (!/^https?:\/\//i.test(href)) return null;
  return href;
}

function isLikelySiteSearch(url: string): boolean {
  try {
    const parsed = new URL(url);
    if (parsed.hostname.includes('bing.com')) return false;
    const path = (parsed.pathname + parsed.search).toLowerCase();
    return path.includes('/search') || parsed.searchParams.has('q');
  } catch {
    return false;
  }
}

function extractSize(text: string): string {
  const match = text.match(SIZE_PATTERN);
  return match ? cleanText(match[0]).replace(/,/g, '.') : '';
}

function isLikelySds(url: string, anchorText?: string): boolean {
  const lowerUrl = url.toLowerCase();
  const lowerText = anchorText?.toLowerCase() || '';
  if (
    lowerUrl.endsWith('.pdf') &&
    (lowerUrl.includes('sds') ||
      lowerUrl.includes('msds') ||
      lowerText.includes('sds') ||
      lowerText.includes('safety data'))
  ) {
    return true;
  }
  if (
    lowerUrl.includes('sds') ||
    lowerUrl.includes('msds') ||
    lowerUrl.includes('safety-data-sheet')
  ) {
    return true;
  }
  if (
    lowerText.includes('safety data') ||
    lowerText.includes('sds') ||
    lowerText.includes('msds')
  ) {
    return true;
  }
  return false;
}

function deriveNameFromUrl(url: string): string {
  try {
    const { pathname } = new URL(url);
    const slug = pathname.split('/').filter(Boolean).pop() || '';
    const withoutExt = slug.replace(/\.(html?|php|aspx|pdf)$/i, '');
    return cleanText(withoutExt.replace(/[-_]+/g, ' '));
  } catch {
    return '';
  }
}

async function httpGet(url: string) {
  return axios.get<string>(url, {
    headers: { 'User-Agent': USER_AGENT, 'Accept-Language': 'en-AU,en;q=0.9' },
    timeout: REQUEST_TIMEOUT,
  });
}

export async function fetchBingLinks(query: string, limit = 6): Promise<string[]> {
  const trimmed = cleanText(query);
  if (!trimmed) return [];
  try {
    const searchUrl = `https://www.bing.com/search?q=${encodeURIComponent(trimmed)}&setlang=en-US`;
    const { data } = await httpGet(searchUrl);
    const $ = cheerio.load(data);
    const links: string[] = [];
    'li.b_algo h2 a, li.b_algo a.title'.split(',').forEach(selector => {
      $(selector.trim()).each((_, el) => {
        const raw = $(el).attr('href');
        const normalised = normaliseLink(raw);
        if (normalised) links.push(normalised);
      });
    });
    $('a[href^=https://www.bing.com/ck/a]').each((_, el) => {
      const raw = $(el).attr('href');
      const normalised = normaliseLink(raw);
      if (normalised) links.push(normalised);
    });
    const deduped = dedupe(links);
    logger.info(
      { query: trimmed, linkCount: deduped.length, links: deduped.slice(0, limit) },
      '[SCRAPER] Bing links collected',
    );
    return deduped.slice(0, limit);
  } catch {
    logger.warn({ query: trimmed }, '[SCRAPER] Bing search failed');
    return [];
  }
}

export async function expandSiteSearchPage(url: string, limit = 5): Promise<string[]> {
  const normalised = normaliseLink(url);
  if (!normalised) return [];
  if (!isLikelySiteSearch(normalised)) return [];
  try {
    const { data } = await httpGet(normalised);
    const $ = cheerio.load(data);
    const candidates: string[] = [];
    $('a[href]').each((_, el) => {
      if (candidates.length >= limit) return false;
      const href = $(el).attr('href');
      const anchor = cleanText($(el).text());
      const resolved = normaliseLink(href, normalised);
      if (!resolved) return;
      if (isLikelySiteSearch(resolved)) return;
      if (!/^https?:\/\//i.test(resolved)) return;
      if (anchor.length < 3) return;
      candidates.push(resolved);
    });
    return dedupe(candidates).slice(0, limit);
  } catch {
    return [];
  }
}

export async function scrapeProductInfo(
  url: string,
  barcode?: string,
): Promise<ProductScrapeResult> {
  const normalised = normaliseLink(url);
  if (!normalised) {
    throw new Error('Invalid URL');
  }
  const result: ProductScrapeResult = {
    url: normalised,
    name: '',
    contents_size_weight: '',
    size: '',
    sdsUrl: null,
  };
  try {
    const { data } = await httpGet(normalised);
    const $ = cheerio.load(data);
    const nameCandidates = [
      cleanText($("meta[property='og:title']").attr('content')),
      cleanText($("meta[name='title']").attr('content')),
      cleanText($('h1').first().text()),
      cleanText($('title').first().text()),
    ];
    result.name = nameCandidates.find(Boolean) || '';
    const bodyText = cleanText($('body').text());
    const detectedSize = extractSize(bodyText);
    if (detectedSize) result.contents_size_weight = detectedSize;
    if (!result.contents_size_weight && barcode && bodyText.includes(barcode)) {
      const barcodeIndex = bodyText.indexOf(barcode);
      const windowText = bodyText.slice(Math.max(0, barcodeIndex - 120), barcodeIndex + 120);
      const nearbySize = extractSize(windowText);
      if (nearbySize) result.contents_size_weight = nearbySize;
    }
    $('a[href]').each((_, el) => {
      if (result.sdsUrl) return false;
      const href = $(el).attr('href');
      const anchor = cleanText($(el).text());
      const resolved = normaliseLink(href, normalised);
      if (resolved && isLikelySds(resolved, anchor)) {
        logger.info({ url: normalised, resolved, anchor }, '[SCRAPER] SDS link detected');
        result.sdsUrl = resolved;
        return false;
      }
      return undefined;
    });
    if (!result.name) {
      const fallback = deriveNameFromUrl(normalised);
      if (fallback) result.name = fallback;
    }
    if (!result.contents_size_weight) {
      const slugSize = extractSize(result.name) || extractSize(normalised);
      if (slugSize) result.contents_size_weight = slugSize;
    }
    result.size = result.contents_size_weight;
  } catch {
    return result;
  }
  logger.info(
    {
      url: normalised,
      name: result.name,
      size: result.contents_size_weight,
      sdsUrl: result.sdsUrl,
    },
    '[SCRAPER] scrape summary',
  );
  return result;
}

export async function fetchSdsByName(
  name: string,
  size?: string,
): Promise<{ sdsUrl: string | null; topLinks: string[] }> {
  const cleanedName = cleanText(name);
  const cleanedSize = cleanText(size);
  if (!cleanedName) return { sdsUrl: null, topLinks: [] };
  const queries = dedupe([
    `${cleanedName} ${cleanedSize} safety data sheet`.trim(),
    `${cleanedName} ${cleanedSize} sds pdf`.trim(),
    `${cleanedName} sds pdf`.trim(),
    `${cleanedName} msds`.trim(),
  ]);
  const collected: string[] = [];
  for (const query of queries) {
    if (!query) continue;
    const links = await fetchBingLinks(query, 6);
    collected.push(...links);
  }
  const ordered = dedupe(collected);
  const sdsUrl = ordered.find(link => isLikelySds(link)) || null;
  return { sdsUrl, topLinks: ordered.slice(0, 10) };
}

export async function fetchSdsByNameSimple(
  name: string,
  size?: string,
): Promise<{ sdsUrl: string | null; topLinks: string[] }> {
  return fetchSdsByName(name, size);
}

export async function searchWithManualData(
  name: string,
  size: string,
  code: string,
): Promise<ProductScrapeResult> {
  const cleanedName = cleanText(name);
  const cleanedSize = cleanText(size);
  const hint = cleanedSize || cleanText(code);
  const { sdsUrl } = await fetchSdsByName(cleanedName, hint);
  return {
    url: '',
    name: cleanedName,
    contents_size_weight: cleanedSize,
    size: cleanedSize,
    sdsUrl,
  };
}


