import express from 'express';
import { supabase } from '../utils/supabaseClient.js';
import { searchWithManualData } from '../utils/scraper.js';
import { isValidCode, isValidName, isValidSize } from '../utils/validation.js';
import logger from '../utils/logger.js';
import { triggerAutoSdsParsing } from '../utils/autoSdsParsing.js';
const router = express.Router();
/**
 * Manual entry endpoint - accepts name, size, and barcode directly
 * Skips web scraping and uses provided data to create/update product records
 */
router.post('/', async (req, res) => {
    const { code, name, size, userId } = req.body || {};
    // Validate all required fields
    if (!isValidCode(code))
        return res.status(403).json({ error: 'Invalid barcode' });
    if (!isValidName(name))
        return res.status(403).json({ error: 'Invalid name' });
    if (!isValidSize(size))
        return res.status(403).json({ error: 'Invalid size' });
    logger.info({ code, name, size, userId }, '[MANUAL_SCAN] Processing manual entry');
    try {
        // 1) Check if user already has this item in their watchlist
        if (userId) {
            const { data: product, error: productError } = await supabase
                .from('product')
                .select('id, name')
                .eq('barcode', code)
                .maybeSingle();
            if (!productError && product) {
                const { data: watchlistItem, error: watchlistError } = await supabase
                    .from('user_chemical_watch_list')
                    .select('id, created_at')
                    .eq('user_id', userId)
                    .eq('product_id', product.id)
                    .maybeSingle();
                if (!watchlistError && watchlistItem) {
                    logger.info({ code, productId: product.id, userId }, '[MANUAL_SCAN] Item already in user watchlist');
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
        // 2) Check if product exists in database
        const { data: existing, error: fetchErr } = await supabase
            .from('product')
            .select('*')
            .eq('barcode', code)
            .maybeSingle();
        if (fetchErr)
            return res.status(500).json({ error: fetchErr.message });
        if (existing) {
            // Update existing product with manual data if it's more complete
            let shouldUpdate = false;
            const updates = {};
            if (!existing.name && name) {
                updates.name = name;
                shouldUpdate = true;
            }
            if (!existing.contents_size_weight && size) {
                updates.contents_size_weight = size;
                shouldUpdate = true;
            }
            // Always try to find SDS if missing
            if (!existing.sds_url) {
                try {
                    const manualResult = await searchWithManualData(name, size, code);
                    if (manualResult.sdsUrl) {
                        updates.sds_url = manualResult.sdsUrl;
                        shouldUpdate = true;
                    }
                }
                catch (err) {
                    logger.warn({ err: String(err) }, '[MANUAL_SCAN] SDS search failed');
                }
            }
            if (shouldUpdate) {
                const { data: updated, error: updateError } = await supabase
                    .from('product')
                    .update(updates)
                    .eq('barcode', code)
                    .select()
                    .maybeSingle();
                if (updateError)
                    return res.status(500).json({ error: updateError.message });
                // Trigger auto-SDS parsing if we added an SDS URL
                if (updates.sds_url && updated?.id) {
                    logger.info({ productId: updated.id }, '[MANUAL_SCAN] Triggering auto-SDS parsing for updated product');
                    triggerAutoSdsParsing(updated.id, { delay: 1000 });
                }
                logger.info({ code, updates }, '[MANUAL_SCAN] Updated existing product with manual data');
                return res.json({
                    code,
                    product: updated,
                    existingInDatabase: true,
                    updated: true,
                    message: 'Product updated with manual entry data',
                });
            }
            else {
                logger.info({ code }, '[MANUAL_SCAN] Existing product already complete');
                return res.json({
                    code,
                    product: existing,
                    existingInDatabase: true,
                    message: 'Product found in database',
                });
            }
        }
        // 3) Create new product from manual entry
        const manualResult = await searchWithManualData(name, size, code);
        const insert = await supabase
            .from('product')
            .insert({
            barcode: code,
            name: manualResult.name,
            contents_size_weight: manualResult.contents_size_weight,
            sds_url: manualResult.sdsUrl || null,
        })
            .select()
            .maybeSingle();
        const data = insert.data;
        const error = insert.error;
        logger.info({ code, data, error }, '[MANUAL_SCAN] Database insert result');
        if (error)
            return res.status(500).json({ error: error.message });
        // Trigger auto-SDS parsing if we found an SDS URL
        if (data?.sds_url && data?.id) {
            logger.info({ productId: data.id }, '[MANUAL_SCAN] Triggering auto-SDS parsing for new product');
            triggerAutoSdsParsing(data.id, { delay: 2000 });
        }
        return res.json({
            code,
            product: data,
            isManualEntry: true,
            message: 'Product created from manual entry',
        });
    }
    catch (err) {
        logger.error({ code, err: String(err) }, '[MANUAL_SCAN] failed');
        return res
            .status(502)
            .json({ error: 'MANUAL_SCAN_FAILED', message: String(err?.message || err) });
    }
});
export default router;
