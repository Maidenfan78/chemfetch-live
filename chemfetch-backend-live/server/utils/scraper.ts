import * as cheerio from 'cheerio';
import logger from './logger.js';

const USER_AGENT =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36';
const REQUEST_TIMEOUT = 8000;
const SIZE_PATTERN =
  /\b\d+(?:[.,]\d+)?\s?(?:ml|mL|l|L|litre|liter|g|kg|oz|fl\s?oz|pack|packs|tablet|tablets)\b/i;

const SDS_BANNED_HOSTS = ['sdsmanager.', 'msdsmanager.', 'msds.com', 'hazard.com', 'msdsdigital.com', 'chemtrac.com'];
const SDS_PREFERRED_HOSTS = ['blob.core.windows.net', 'chemwatch.net', 'chemicalsafety.com', 'productsds', 'azuredge.net'];

function normaliseUrl(url: string | null | undefined): string {
  return cleanText(url || '').toLowerCase();
}

function scoreSdsLink(link: string, productName: string): number {
  const lower = normaliseUrl(link);
  if (!lower) return -Infinity;
  let score = 0;
  if (lower.startsWith('http')) score += 1;
  if (lower.includes('.pdf')) score += 6;
  if (lower.endsWith('.pdf')) score += 2;
  for (const host of SDS_PREFERRED_HOSTS) {
    if (lower.includes(host)) score += 3;
  }
  for (const host of SDS_BANNED_HOSTS) {
    if (lower.includes(host)) score -= 6;
  }
  const tokens = productName.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);
  if (tokens.length) {
    const matches = tokens.filter(token => token.length > 2 && lower.includes(token)).length;
    score += matches;
  }
  return score;
}

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

function decodeBingRedirect(raw: string | null | undefined): string | null {
  if (!raw) return null;
  let candidate = raw.trim();
  if (!candidate) return null;

  try {
    const decoded = decodeURIComponent(candidate);
    if (decoded) candidate = decoded;
  } catch {
    /* ignore malformed URI sequences */
  }

  if (/^https?:\/\//i.test(candidate)) return candidate;

  const attempts: string[] = [candidate];
  for (let i = 1; i <= 3 && i < candidate.length; i++) {
    attempts.push(candidate.slice(i));
  }

  const base64Pattern = /^[A-Za-z0-9+/=_-]+$/;

  for (const attempt of attempts) {
    const trimmed = attempt.trim();
    if (trimmed.length < 8) continue;
    if (!base64Pattern.test(trimmed)) continue;

    const normalised = trimmed.replace(/-/g, '+').replace(/_/g, '/');
    const padding = normalised.length % 4;
    const padded = padding ? normalised + '='.repeat(4 - padding) : normalised;

    try {
      const decoded = Buffer.from(padded, 'base64').toString('utf8');
      if (/^https?:\/\//i.test(decoded)) {
        return decoded;
      }
    } catch {
      /* ignore invalid base64 */
    }
  }

  return null;
}

function getHostname(url: string): string {
  try {
    return new URL(url).hostname.toLowerCase();
  } catch {
    return '';
  }
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
    if (parsed.hostname.includes('bing.com') || parsed.hostname.includes('duckduckgo.com')) {
      const redirectParams = parsed.hostname.includes('duckduckgo.com')
        ? ['uddg', 'rut', 'u', 'url']
        : ['u', 'url', 'r', 'target'];
      for (const param of redirectParams) {
        const target = parsed.searchParams.get(param);
        const decoded = decodeBingRedirect(target);
        if (decoded) {
          href = decoded;
          break;
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

const CTA_PREFIXES = [/^(buy|shop|order|purchase|get|view|discover|compare)\s+/i, /^add to cart:?\s*/i];
const STORE_KEYWORDS = ['chemist', 'chemist warehouse', 'pharmacy', 'store', 'shop', 'online', 'discount', 'warehouse', 'market', 'supermarket', 'apothecary', 'amazon', 'ebay', 'target', 'walmart'];
const NAME_SPLIT_REGEX = /\s*(?:\||[\u2013\u2014\u2015]|-|\u2022|\u00b7|:)\s*/;

function looksLikeStoreFragment(fragment: string): boolean {
  const lower = fragment.toLowerCase();
  if (!lower) return false;
  if (lower.includes('http')) return true;
  if (lower.includes('.com')) return true;
  return STORE_KEYWORDS.some(keyword => lower.includes(keyword));
}

function normaliseProductName(raw: string | null | undefined): string {
  let value = cleanText(raw);
  if (!value) return '';
  const original = value;

  for (const pattern of CTA_PREFIXES) {
    if (pattern.test(value)) {
      value = value.replace(pattern, '');
      break;
    }
  }

  value = value.replace(/\s+online\s+at\s+.+$/i, '');
  value = value.replace(/\s+available\s+at\s+.+$/i, '');
  value = cleanText(value);

  const parts = value.split(NAME_SPLIT_REGEX).map(part => cleanText(part)).filter(Boolean);
  if (parts.length > 1) {
    const preferred = parts.find(part => !looksLikeStoreFragment(part));
    value = preferred || parts[0];
  }

  const trailingMatch = value.match(/^(.*?)(?:\s+(?:online|chemist|pharmacy|store|shop|discount|warehouse).*)$/i);
  if (trailingMatch && trailingMatch[1]) {
    value = cleanText(trailingMatch[1]);
  }

  value = cleanText(value);
  return value || original;
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

async function fetchDuckDuckGoLinks(query: string, limit = 6): Promise<string[]> {
  const trimmed = cleanText(query);
  if (!trimmed) return [];
  try {
    const searchUrl = `https://duckduckgo.com/html/?q=${encodeURIComponent(trimmed)}`;
    const { data } = await httpGet(searchUrl);
    const $ = cheerio.load(data);
    const links: string[] = [];
    $('a.result__a[href]').each((_, el) => {
      const raw = $(el).attr('href');
      const normalised = normaliseLink(raw, searchUrl);
      if (normalised) {
        links.push(normalised);
        if (links.length >= limit * 2) return false;
      }
      return undefined;
    });
    const deduped = dedupe(links);
    logger.info(
      { query: trimmed, linkCount: deduped.length, links: deduped.slice(0, limit) },
      '[SCRAPER] DuckDuckGo links collected',
    );
    return deduped.slice(0, limit);
  } catch (err) {
    logger.warn({ query: trimmed, err: String(err) }, '[SCRAPER] DuckDuckGo search failed');
    return [];
  }
}

async function httpGet(url: string) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);
  try {
    const response = await fetch(url, {
      headers: {
        'User-Agent': USER_AGENT,
        'Accept-Language': 'en-AU,en;q=0.9',
        Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      },
      redirect: 'follow',
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }
    const data = await response.text();
    return { data };
  } catch (err: any) {
    if (err?.name === 'AbortError') {
      throw new Error('Request timed out');
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

function hasUsefulHost(links: string[]): boolean {
  return links.some(link => {
    const host = getHostname(link);
    if (!host) return false;
    if (host.includes('bing.com')) return false;
    if (host.includes('baidu.com')) return false;
    return true;
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
    if (!hasUsefulHost(deduped.slice(0, limit))) {
      const duckLinks = await fetchDuckDuckGoLinks(trimmed, limit);
      if (duckLinks.length > 0) {
        const merged = dedupe([...duckLinks, ...deduped]);
        logger.info(
          { query: trimmed, duckCount: duckLinks.length, mergedPreview: merged.slice(0, limit) },
          '[SCRAPER] DuckDuckGo fallback applied',
        );
        return merged.slice(0, limit);
      }
    }
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
    const rawNameCandidates = [
      $("meta[property='og:title']").attr('content'),
      $("meta[name='title']").attr('content'),
      $('h1').first().text(),
      $('title').first().text(),
    ];
    const nameCandidates = rawNameCandidates.map(candidate => normaliseProductName(candidate));
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
      const fallback = normaliseProductName(deriveNameFromUrl(normalised));
      if (fallback) result.name = fallback;
    }

    result.name = normaliseProductName(result.name);

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
  const cleanedName = normaliseProductName(name);
  const cleanedSize = cleanText(size);
  if (!cleanedName) return { sdsUrl: null, topLinks: [] };
  const quotedName = cleanedName.includes(' ') ? `"${cleanedName}"` : cleanedName;
  const queries = dedupe([
    `${cleanedName} ${cleanedSize} safety data sheet`.trim(),
    `${cleanedName} ${cleanedSize} sds pdf`.trim(),
    `${cleanedName} sds pdf`.trim(),
    `${cleanedName} sds`.trim(),
    `${quotedName} sds`.trim(),
    `${cleanedName} msds`.trim(),
  ]);
  const collected: string[] = [];
  for (const query of queries) {
    if (!query) continue;
    const links = await fetchBingLinks(query, 6);
    collected.push(...links);
  }
  let ordered = dedupe(collected);
  let sdsUrl = ordered.find(link => isLikelySds(link)) || null;

  if (!sdsUrl) {
    for (const query of queries) {
      if (!query) continue;
      const duckLinks = await fetchDuckDuckGoLinks(query, 8);
      if (duckLinks.length > 0) {
        logger.info({ query, duckCount: duckLinks.length, links: duckLinks.slice(0, 6) }, '[SCRAPER] DuckDuckGo SDS links collected');
        collected.push(...duckLinks);
      }
    }
    ordered = dedupe(collected);
  }

  const scored = ordered
    .map(link => ({ link, score: scoreSdsLink(link, cleanedName) }))
    .filter(item => Number.isFinite(item.score))
    .sort((a, b) => b.score - a.score);

  const preferred = scored.find(item => isLikelySds(item.link));
  if (preferred) {
    sdsUrl = preferred.link;
  }

  const fallbackOrdered = scored.length > 0 ? scored : ordered.map(link => ({ link, score: scoreSdsLink(link, cleanedName) }));
  const topLinks = fallbackOrdered.slice(0, 10).map(item => item.link);

  return { sdsUrl: sdsUrl || null, topLinks };
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



