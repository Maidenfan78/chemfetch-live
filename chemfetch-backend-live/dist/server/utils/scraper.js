import axios from 'axios';
import * as cheerio from 'cheerio';
import puppeteer from 'puppeteer-extra';
import StealthPlugin from 'puppeteer-extra-plugin-stealth';
import { setTimeout as delay } from 'timers/promises';
import { TTLCache } from './cache.js';
puppeteer.use(StealthPlugin());
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36';
const OCR_SERVICE_URL = process.env.OCR_SERVICE_URL || 'http://127.0.0.1:5001';
// Google Search API configuration
// Note: Load environment variables when needed, not at module init
let GOOGLE_SEARCH_API_KEY;
let GOOGLE_SEARCH_ENGINE_ID;
function getGoogleSearchConfig() {
    if (!GOOGLE_SEARCH_API_KEY) {
        GOOGLE_SEARCH_API_KEY = process.env.GOOGLE_SEARCH_API_KEY;
        GOOGLE_SEARCH_ENGINE_ID = process.env.GOOGLE_SEARCH_ENGINE_ID || '45c531108e8b44924';
        console.log('[GOOGLE_SEARCH_CONFIG] API Key present:', !!GOOGLE_SEARCH_API_KEY);
        console.log('[GOOGLE_SEARCH_CONFIG] Search Engine ID:', GOOGLE_SEARCH_ENGINE_ID);
        if (GOOGLE_SEARCH_API_KEY) {
            console.log('[GOOGLE_SEARCH_CONFIG] API Key length:', GOOGLE_SEARCH_API_KEY.length);
            console.log('[GOOGLE_SEARCH_CONFIG] API Key starts with:', GOOGLE_SEARCH_API_KEY.substring(0, 10) + '...');
        }
    }
    return { GOOGLE_SEARCH_API_KEY, GOOGLE_SEARCH_ENGINE_ID };
}
const BARCODE_CACHE = new TTLCache(5 * 60 * 1000);
const SDS_CACHE = new TTLCache(10 * 60 * 1000);
// -----------------------------------------------------------------------------
// Axios helpers
// -----------------------------------------------------------------------------
const http = axios.create({
    timeout: 8000, // Reduced from 15000 to 8000ms for faster failures
    maxRedirects: 3, // Reduced from 5 to 3
    headers: {
        'User-Agent': UA,
        'Accept-Language': 'en-AU,en;q=0.9',
    },
    validateStatus: () => true,
});
// Helper to verify SDS PDF by calling the OCR microservice verify-sds endpoint
async function verifySdsUrl(url, productName, isManualEntry = false) {
    try {
        console.log(`[SCRAPER] Verifying SDS URL: ${url} for product: ${productName}`);
        // For manual entries with obvious SDS URLs, be more lenient
        if (isManualEntry &&
            (url.toLowerCase().includes('sds') ||
                url.toLowerCase().includes('msds') ||
                url.toLowerCase().includes('safety'))) {
            console.log(`[SCRAPER] Manual entry with obvious SDS URL, accepting: ${url}`);
            return true;
        }
        // Also accept URLs from known SDS providers for manual entries
        if (isManualEntry) {
            const sdsProviders = [
                'msdsdigital.com',
                'chemwatch.net',
                'chemscape.com',
                'safeworkdata.com',
            ];
            if (sdsProviders.some(domain => url.toLowerCase().includes(domain))) {
                console.log(`[SCRAPER] Manual entry from known SDS provider, accepting: ${url}`);
                return true;
            }
        }
        const resp = await axios.post(`${OCR_SERVICE_URL}/verify-sds`, { url, name: productName }, { timeout: 20000 });
        console.log(`[SCRAPER] OCR verification response:`, resp.data);
        const isVerified = resp.data.verified === true;
        console.log(`[SCRAPER] OCR verification result: ${isVerified}`);
        return isVerified;
    }
    catch (err) {
        console.error('[verifySdsUrl] Proxy verify failed:', err);
        return false;
    }
}
// -----------------------------------------------------------------------------
// Enhanced Google Search with multiple query strategies
// -----------------------------------------------------------------------------
async function fetchGoogleSearchResults(query) {
    const { GOOGLE_SEARCH_API_KEY, GOOGLE_SEARCH_ENGINE_ID } = getGoogleSearchConfig();
    console.log(`[GOOGLE_SEARCH] API Key check: ${!!GOOGLE_SEARCH_API_KEY}`);
    console.log(`[GOOGLE_SEARCH] Search Engine ID: ${GOOGLE_SEARCH_ENGINE_ID}`);
    if (!GOOGLE_SEARCH_API_KEY) {
        console.warn('[GOOGLE_SEARCH] API key not configured, falling back to Bing');
        return fetchBingLinksRaw(query);
    }
    if (!GOOGLE_SEARCH_ENGINE_ID || GOOGLE_SEARCH_ENGINE_ID === 'YOUR_SEARCH_ENGINE_ID') {
        console.warn('[GOOGLE_SEARCH] Search Engine ID not configured properly, falling back to Bing');
        return fetchBingLinksRaw(query);
    }
    try {
        // Try multiple search strategies for better product discovery
        const searchStrategies = [
            query, // Original barcode
            `${query} product Australia`, // Add product context
            `${query} shop buy Australia`, // Shopping context
            `${query} supermarket pharmacy`, // Retail context
        ];
        let allResults = [];
        for (const searchQuery of searchStrategies) {
            console.log(`[GOOGLE_SEARCH] Searching for: ${searchQuery}`);
            // Build search URL with Australian targeting
            const searchUrl = new URL('https://customsearch.googleapis.com/customsearch/v1');
            searchUrl.searchParams.set('key', GOOGLE_SEARCH_API_KEY);
            searchUrl.searchParams.set('cx', GOOGLE_SEARCH_ENGINE_ID);
            searchUrl.searchParams.set('q', searchQuery);
            searchUrl.searchParams.set('num', '10'); // Return up to 10 results
            searchUrl.searchParams.set('gl', 'au'); // Geographic location: Australia
            searchUrl.searchParams.set('hl', 'en'); // Interface language: English
            searchUrl.searchParams.set('lr', 'lang_en'); // Language restrict: English
            searchUrl.searchParams.set('safe', 'off'); // Don't filter results
            console.log(`[GOOGLE_SEARCH] API URL: ${searchUrl.toString()}`);
            const response = await axios.get(searchUrl.toString(), { timeout: 10000 });
            if (response.status !== 200) {
                console.error(`[GOOGLE_SEARCH] API returned status ${response.status}:`, response.data);
                continue; // Try next strategy
            }
            const results = response.data?.items || [];
            console.log(`[GOOGLE_SEARCH] Found ${results.length} results for query: ${searchQuery}`);
            const links = results.map((item) => ({
                title: item.title || '',
                url: item.link || '',
            }));
            // Filter out SDS PDFs from early results to prioritize product pages
            const productResults = links.filter(link => !link.url.toLowerCase().endsWith('.pdf') &&
                !link.url.toLowerCase().includes('sds') &&
                !link.url.toLowerCase().includes('msds'));
            allResults = [...allResults, ...productResults];
            // If we found good product pages, stop searching
            if (productResults.length >= 3) {
                console.log(`[GOOGLE_SEARCH] Found sufficient product pages, stopping search`);
                break;
            }
            // Add back PDF results at the end as fallback
            const pdfResults = links.filter(link => link.url.toLowerCase().endsWith('.pdf') ||
                link.url.toLowerCase().includes('sds') ||
                link.url.toLowerCase().includes('msds'));
            allResults = [...allResults, ...pdfResults];
        }
        // Remove duplicates while preserving order
        const uniqueResults = allResults.filter((item, index, self) => index === self.findIndex(other => other.url === item.url));
        console.log(`[GOOGLE_SEARCH] Total unique results: ${uniqueResults.length}`);
        console.log(`[GOOGLE_SEARCH] Final results:`, uniqueResults.slice(0, 5)); // Log first 5 results
        return uniqueResults;
    }
    catch (error) {
        console.error('[GOOGLE_SEARCH] API error:', {
            message: error.message,
            status: error.response?.status,
            data: error.response?.data,
        });
        // Fallback to Bing if Google Search fails
        console.log('[GOOGLE_SEARCH] Falling back to Bing search');
        return fetchBingLinksRaw(query);
    }
}
// -----------------------------------------------------------------------------
// Bing search fallback (AU-biased) via Puppeteer (stealth)
// -----------------------------------------------------------------------------
async function fetchBingLinksRaw(query) {
    const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox'] });
    try {
        const page = await browser.newPage();
        await page.setExtraHTTPHeaders({ 'Accept-Language': 'en-AU,en;q=0.9' });
        await page.setUserAgent(UA);
        const url = `https://www.bing.com/search?q=${encodeURIComponent(query)}&mkt=en-AU&cc=AU`;
        console.log(`[BING_SEARCH] Fallback search URL: ${url}`);
        await page.goto(url, { waitUntil: 'domcontentloaded' });
        await page.waitForSelector('li.b_algo h2 a', { timeout: 10000 }).catch(() => { });
        const links = await page.$$eval('li.b_algo h2 a', els => els.map(el => ({ title: el.textContent?.trim() || '', url: el.getAttribute('href') || '' })));
        console.log(`[BING_SEARCH] Found ${links.length} fallback results`);
        return links;
    }
    finally {
        await browser.close();
    }
}
export async function searchAu(query) {
    try {
        // Use Google Search API primarily, with Bing as fallback
        return await fetchGoogleSearchResults(query);
    }
    catch (e) {
        console.warn('[searchAu] failed:', e);
        return [];
    }
}
// -----------------------------------------------------------------------------
// URL / PDF utilities
// -----------------------------------------------------------------------------
function isProbablyA1Base64(s) {
    if (!s || s.length < 3)
        return false;
    const c0 = s.charCodeAt(0);
    const c1 = s.charCodeAt(1);
    const firstIsLetter = (c0 >= 65 && c0 <= 90) || (c0 >= 97 && c0 <= 122);
    const secondIsDigit = c1 >= 48 && c1 <= 57; // '0'-'9'
    return firstIsLetter && secondIsDigit;
}
function extractBingTarget(url) {
    if (!url)
        return url;
    let s = String(url).trim();
    // Handle Bing redirector links with u= parameter
    try {
        const parsed = new URL(s);
        if (parsed.hostname.includes('bing.com') && parsed.searchParams.has('u')) {
            let target = parsed.searchParams.get('u') || '';
            try {
                if (isProbablyA1Base64(target)) {
                    target = Buffer.from(target.slice(2), 'base64').toString('utf8');
                }
                else {
                    target = decodeURIComponent(target);
                }
            }
            catch { }
            s = target.trim();
        }
    }
    catch { }
    // Handle direct base64-encoded URLs that start with a1a
    try {
        if (isProbablyA1Base64(s)) {
            const decoded = Buffer.from(s.slice(2), 'base64').toString('utf8');
            if (decoded.startsWith('http://') || decoded.startsWith('https://')) {
                s = decoded;
            }
        }
    }
    catch { }
    // Return original if not a valid URL or contains dummy domains
    if (!(s.startsWith('http://') || s.startsWith('https://')))
        return url;
    if (s.includes('dummy.local'))
        return url;
    return s;
}
// Clean up Google Search results (no redirect unwrapping needed)
function extractGoogleTarget(url) {
    if (!url)
        return url;
    let s = String(url).trim();
    // Google Custom Search API returns direct URLs, no redirect unwrapping needed
    if (!(s.startsWith('http://') || s.startsWith('https://')))
        return url;
    if (s.includes('dummy.local'))
        return url;
    return s;
}
function looksLikeSdsUrl(url) {
    const u = url.toLowerCase();
    return /(sds|msds|safety[-_\s]?data)/i.test(u);
}
async function isPdfByHeaders(url) {
    try {
        const res = await http.head(url);
        const ct = (res.headers?.['content-type'] || '').toString().toLowerCase();
        const finalUrl = res.request?.res?.responseUrl || url;
        if (ct.includes('application/pdf'))
            return { isPdf: true, finalUrl };
        // Some servers lie on HEAD or block it; try a ranged GET for a sniff
        if (res.status >= 400 || !ct) {
            const g = await http.get(url, { responseType: 'arraybuffer' });
            const gCt = (g.headers?.['content-type'] || '').toString().toLowerCase();
            const fUrl = g.request?.res?.responseUrl || url;
            return { isPdf: gCt.includes('application/pdf'), finalUrl: fUrl };
        }
        return { isPdf: false, finalUrl };
    }
    catch {
        return { isPdf: false, finalUrl: url };
    }
}
async function discoverPdfOnHtmlPage(pageUrl) {
    try {
        const res = await http.get(pageUrl);
        if (res.status >= 400)
            return null;
        const finalUrl = res.request?.res?.responseUrl || pageUrl;
        const $ = cheerio.load(res.data);
        // Look for ANY PDF links, not just ones with SDS keywords
        const candidates = [];
        $('a[href]').each((_, a) => {
            const href = String($(a).attr('href') || '').trim();
            if (!href)
                return;
            try {
                const abs = new URL(href, finalUrl).toString();
                const lower = abs.toLowerCase();
                // Accept any PDF or any link with SDS-related terms
                if (lower.endsWith('.pdf') || /pdf|sds|msds|safety|data|sheet|document/i.test(lower)) {
                    candidates.push(abs);
                }
            }
            catch { }
        });
        console.log(`[SCRAPER] Found ${candidates.length} PDF candidates on ${pageUrl}:`, candidates);
        // Light ranking: prefer explicit SDS keywords then .pdf suffix
        candidates.sort((a, b) => {
            const sa = (looksLikeSdsUrl(a) ? 1 : 0) + (a.toLowerCase().endsWith('.pdf') ? 1 : 0);
            const sb = (looksLikeSdsUrl(b) ? 1 : 0) + (b.toLowerCase().endsWith('.pdf') ? 1 : 0);
            return sb - sa;
        });
        for (const c of candidates) {
            const { isPdf, finalUrl: f } = await isPdfByHeaders(c);
            if (isPdf)
                return f;
        }
        return null;
    }
    catch {
        return null;
    }
}
function isProbablyHome(url) {
    try {
        const u = new URL(url);
        return !u.pathname || u.pathname === '/' || u.pathname.split('/').filter(Boolean).length <= 1;
    }
    catch {
        return false;
    }
}
// Filter for Australian/relevant results
function isRelevantForAustralia(url, title) {
    const urlLower = url.toLowerCase();
    const titleLower = title.toLowerCase();
    // Prefer Australian sites
    if (urlLower.includes('.com.au') || urlLower.includes('australia'))
        return true;
    // Exclude obviously irrelevant domains
    if (urlLower.includes('.tw') || urlLower.includes('.cn') || urlLower.includes('.jp'))
        return false;
    // Exclude software/gaming/unrelated content
    if (titleLower.includes('emulator') ||
        titleLower.includes('software') ||
        titleLower.includes('firewall'))
        return false;
    return true;
}
// -----------------------------------------------------------------------------
// Public: barcode → product name/size
// -----------------------------------------------------------------------------
export async function searchItemByBarcode(barcode) {
    const cached = BARCODE_CACHE.get(barcode);
    if (cached)
        return cached;
    const hits = await searchAu(`${barcode} product Australia`); // More targeted barcode search
    for (const hit of hits.slice(0, 7)) {
        const target = extractGoogleTarget(hit.url);
        try {
            const html = await http.get(target).then(r => r.data);
            const $ = cheerio.load(html);
            const name = $('h1').first().text().trim() || $("meta[property='og:title']").attr('content') || '';
            const bodyText = $('body').text();
            const sizeMatch = bodyText.match(/(\d+(?:[\.,]\d+)?\s?(?:ml|mL|g|kg|oz|l|L)\b)/);
            const size = sizeMatch ? sizeMatch[0].replace(',', '.') : '';
            if (name) {
                const result = { name, contents_size_weight: size };
                BARCODE_CACHE.set(barcode, result);
                return result;
            }
        }
        catch { }
        await delay(200);
    }
    return null;
}
// -----------------------------------------------------------------------------
// Public: name (+ optional size) → SDS (robust PDF finder)
// -----------------------------------------------------------------------------
export async function fetchSdsByName(name, size, isManualEntry = false) {
    const cacheKey = size ? `${name}|${size}` : name;
    const cached = SDS_CACHE.get(cacheKey);
    if (cached !== undefined)
        return { sdsUrl: cached || '', topLinks: [] };
    // Enhanced search strategy with better targeting
    const baseQuery = `${name} ${size || ''} sds`.trim();
    console.log(`[SCRAPER] Enhanced search query: ${baseQuery}`);
    let hits = await searchAu(baseQuery);
    // Filter out irrelevant results and prioritize Australian content
    const relevantHits = hits.filter(h => isRelevantForAustralia(h.url, h.title));
    console.log(`[SCRAPER] Filtered ${hits.length} results to ${relevantHits.length} relevant results`);
    // Use relevant hits if we have them, otherwise fall back to all hits
    const searchHits = relevantHits.length > 0 ? relevantHits : hits;
    const topLinks = searchHits.slice(0, 5).map(h => extractGoogleTarget(h.url));
    for (const h of searchHits) {
        const url = extractGoogleTarget(h.url);
        console.log(`[SCRAPER] Evaluating link: ${url}`);
        console.log(`[SCRAPER] Link title: ${h.title}`);
        // 1) Check if it's a direct PDF link
        if (url.toLowerCase().endsWith('.pdf')) {
            const { isPdf, finalUrl } = await isPdfByHeaders(url);
            if (isPdf) {
                console.log('[SCRAPER] Found direct PDF, verifying:', finalUrl);
                const ok = await verifySdsUrl(finalUrl, name, isManualEntry);
                if (ok) {
                    console.log('[SCRAPER] Valid SDS PDF found', finalUrl);
                    SDS_CACHE.set(cacheKey, finalUrl);
                    return { sdsUrl: finalUrl, topLinks };
                }
            }
        }
        // 2) Check if URL looks like it might have SDS content
        if (looksLikeSdsUrl(url)) {
            const { isPdf, finalUrl } = await isPdfByHeaders(url);
            if (isPdf) {
                console.log('[SCRAPER] Found SDS-like PDF, verifying:', finalUrl);
                const ok = await verifySdsUrl(finalUrl, name, isManualEntry);
                if (ok) {
                    console.log('[SCRAPER] Valid SDS PDF found', finalUrl);
                    SDS_CACHE.set(cacheKey, finalUrl);
                    return { sdsUrl: finalUrl, topLinks };
                }
            }
        }
        // 3) Scan HTML pages for PDF links (but be more aggressive about checking them)
        if (!url.toLowerCase().endsWith('.pdf') && !isProbablyHome(url)) {
            const pdf = await discoverPdfOnHtmlPage(url);
            if (pdf) {
                console.log('[SCRAPER] Found PDF via page scan, verifying:', pdf);
                const ok = await verifySdsUrl(pdf, name, isManualEntry);
                if (ok) {
                    console.log('[SCRAPER] Valid SDS PDF via page hop', pdf);
                    SDS_CACHE.set(cacheKey, pdf);
                    return { sdsUrl: pdf, topLinks };
                }
            }
        }
    }
    // Try more specific searches if nothing found yet
    console.log('[SCRAPER] No valid SDS found in initial search, trying alternative strategies');
    // Manufacturer-specific search as a fallback
    const manufacturerQuery = `"${name}" manufacturer safety data sheet Australia`;
    console.log(`[SCRAPER] Trying manufacturer search: ${manufacturerQuery}`);
    const manufacturerHits = await searchAu(manufacturerQuery);
    for (const h of manufacturerHits.slice(0, 3)) {
        const url = extractGoogleTarget(h.url);
        console.log(`[SCRAPER] Checking manufacturer result: ${url}`);
        if (url.toLowerCase().endsWith('.pdf')) {
            const { isPdf, finalUrl } = await isPdfByHeaders(url);
            if (isPdf) {
                const ok = await verifySdsUrl(finalUrl, name, isManualEntry);
                if (ok) {
                    console.log('[SCRAPER] Valid SDS PDF found via manufacturer search', finalUrl);
                    SDS_CACHE.set(cacheKey, finalUrl);
                    // Preserve existing top links if we had any; otherwise return the found PDF
                    const resultTopLinks = topLinks.length > 0 ? topLinks : [finalUrl];
                    return { sdsUrl: finalUrl, topLinks: resultTopLinks };
                }
            }
        }
    }
    console.log('[SCRAPER] No valid SDS PDF found');
    SDS_CACHE.set(cacheKey, null);
    return { sdsUrl: '', topLinks };
}
// Simple wrapper kept for compatibility
export async function fetchBingLinks(query) {
    const hits = await searchAu(query);
    return hits.map(h => extractGoogleTarget(h.url));
}
// -----------------------------------------------------------------------------
// Public: Search using manual entry data (name + size + barcode)
// -----------------------------------------------------------------------------
export async function searchWithManualData(name, size, barcode) {
    console.log(`[SCRAPER] Manual search for: ${name} ${size} ${barcode || ''}`);
    // Use provided data directly, then search for SDS
    const result = {
        name: name.trim(),
        contents_size_weight: size.trim(),
        sdsUrl: '',
    };
    try {
        const { sdsUrl } = await fetchSdsByName(name, size, true); // Pass true for isManualEntry
        if (sdsUrl) {
            result.sdsUrl = sdsUrl;
            console.log(`[SCRAPER] Found SDS for manual entry: ${sdsUrl}`);
        }
        else {
            console.log(`[SCRAPER] No SDS found for manual entry: ${name} ${size}`);
        }
    }
    catch (err) {
        console.error(`[SCRAPER] SDS search failed for manual entry:`, err);
    }
    return result;
}
// -----------------------------------------------------------------------------
// Public: scrape product info from a single URL
// -----------------------------------------------------------------------------
export async function scrapeProductInfo(url, identifier) {
    // Check if the URL points directly to a PDF (likely an SDS)
    const { isPdf, finalUrl } = await isPdfByHeaders(url);
    if (isPdf) {
        // If we got a PDF directly, try to extract product name from the URL or title
        let extractedName = '';
        let extractedSize = '';
        try {
            // Try to extract product name from PDF filename
            const urlParts = finalUrl.split('/');
            const filename = urlParts[urlParts.length - 1];
            // Decode URL encoding first
            const decodedFilename = decodeURIComponent(filename);
            const nameFromFile = decodedFilename
                .replace(/\.(pdf|PDF)$/, '')
                .replace(/[_-]/g, ' ')
                .trim();
            // Extract size before cleaning (look for patterns like (2L), 75mL, etc.)
            const sizeMatch = nameFromFile.match(/\(?\d+(?:[\.,]\d+)?\s?(?:ml|mL|g|kg|oz|l|L)\)?/i);
            if (sizeMatch) {
                extractedSize = sizeMatch[0].replace(/[()]/g, '').trim();
            }
            // Clean up common patterns for name
            extractedName = nameFromFile
                .replace(/\b(sds|msds|safety|data|sheet|document)\b/gi, '')
                .replace(/\b\d{7,}\b/g, '') // Remove long number codes
                .replace(/\b(\d{3}_\d{3}_\d{3})\b/g, '') // Remove patterns like 3089176_001_001
                .replace(/\(?\d+(?:[\.,]\d+)?\s?(?:ml|mL|g|kg|oz|l|L)\)?/gi, '') // Remove size from name
                .replace(/\s+/g, ' ')
                .trim();
            // If we still don't have a good name, try to extract from URL path
            if (!extractedName || extractedName.length < 3) {
                const pathParts = finalUrl.split('/').filter(part => part &&
                    part !== 'system' &&
                    part !== 'files' &&
                    part !== 'download' &&
                    !part.match(/^\d+$/) // Skip pure numbers
                );
                for (const part of pathParts.reverse()) {
                    const decoded = decodeURIComponent(part)
                        .replace(/[_-]/g, ' ')
                        .replace(/\b(sds|msds|safety|data|sheet)\b/gi, '')
                        .replace(/\s+/g, ' ')
                        .trim();
                    if (decoded && decoded.length > 3) {
                        extractedName = decoded;
                        break;
                    }
                }
            }
            console.log(`[SCRAPER] Extracted name from PDF filename: "${extractedName}"`);
            console.log(`[SCRAPER] Extracted size from PDF filename: "${extractedSize}"`);
        }
        catch (e) {
            console.warn('[SCRAPER] Failed to extract name from PDF filename:', e);
        }
        // Attempt verification for logging/validation, but accept the PDF regardless
        try {
            await verifySdsUrl(finalUrl, extractedName || identifier || '');
        }
        catch { }
        return {
            name: extractedName || '',
            contents_size_weight: extractedSize || '',
            url: finalUrl,
            sdsUrl: finalUrl,
        };
    }
    const res = await http.get(finalUrl);
    const html = res.data;
    const $ = cheerio.load(html);
    const name = $('h1').first().text().trim() || $("meta[property='og:title']").attr('content') || '';
    const bodyText = $('body').text();
    const sizeMatch = bodyText.match(/(\d+(?:[\.,]\d+)?\s?(?:ml|mL|g|kg|oz|l|L)\b)/);
    const size = sizeMatch ? sizeMatch[0].replace(',', '.') : '';
    return { name, contents_size_weight: size, url: finalUrl };
}
