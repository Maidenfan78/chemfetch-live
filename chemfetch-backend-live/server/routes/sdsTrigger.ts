import express from 'express';
import { supabase } from '../utils/supabaseClient';
import { triggerAutoSdsParsing, triggerBatchAutoSdsParsing } from '../utils/autoSdsParsing';
import logger from '../utils/logger';

const router = express.Router();

/**
 * Manually trigger SDS parsing for a specific product
 */
router.post('/trigger', async (req, res) => {
  const { productId, force = false } = req.body || {};

  if (!productId || typeof productId !== 'number') {
    return res.status(400).json({ error: 'Invalid or missing productId' });
  }

  logger.info({ productId, force }, '[SDS_TRIGGER] Manual trigger requested');

  try {
    // Get product info first
    const { data: product, error: productError } = await supabase
      .from('product')
      .select('id, name, sds_url')
      .eq('id', productId)
      .single();

    if (productError || !product) {
      return res.status(404).json({ error: 'Product not found' });
    }

    if (!product.sds_url) {
      return res.status(400).json({ error: 'Product has no SDS URL to parse' });
    }

    // Check if metadata already exists
    const { data: existingMetadata } = await supabase
      .from('sds_metadata')
      .select('product_id, vendor, issue_date')
      .eq('product_id', productId)
      .maybeSingle();

    if (existingMetadata && !force) {
      return res.json({
        success: false,
        message: 'SDS metadata already exists. Use force=true to reparse.',
        existing: existingMetadata,
      });
    }

    // Trigger parsing
    const triggered = await triggerAutoSdsParsing(productId, { force });

    if (triggered) {
      logger.info({ productId }, '[SDS_TRIGGER] Successfully triggered SDS parsing');
      return res.json({
        success: true,
        message: 'SDS parsing triggered successfully',
        productId,
        sdsUrl: product.sds_url,
      });
    } else {
      return res.status(500).json({ error: 'Failed to trigger SDS parsing' });
    }
  } catch (err: any) {
    logger.error({ productId, err: String(err) }, '[SDS_TRIGGER] Failed to trigger parsing');
    return res
      .status(500)
      .json({ error: 'Internal server error', message: String(err?.message || err) });
  }
});

/**
 * Trigger batch SDS parsing for all products with SDS URLs but no metadata
 */
router.post('/batch', async (req, res) => {
  logger.info('[SDS_TRIGGER] Batch parsing requested');

  try {
    // Get count of products that need parsing
    const { data: needsParsing, error: countError } = await supabase
      .from('product')
      .select('id, name')
      .not('sds_url', 'is', null)
      .not('sds_url', 'eq', '');

    if (countError) {
      return res.status(500).json({ error: countError.message });
    }

    const { data: existingMetadata } = await supabase.from('sds_metadata').select('product_id');

    const existingIds = new Set(existingMetadata?.map(m => m.product_id) || []);
    const pendingCount = (needsParsing || []).filter(p => !existingIds.has(p.id)).length;

    if (pendingCount === 0) {
      return res.json({
        success: true,
        message: 'No products need SDS parsing',
        pendingCount: 0,
      });
    }

    // Trigger batch processing
    await triggerBatchAutoSdsParsing();

    logger.info({ pendingCount }, '[SDS_TRIGGER] Batch parsing triggered');
    return res.json({
      success: true,
      message: `Batch SDS parsing triggered for ${pendingCount} products`,
      pendingCount,
    });
  } catch (err: any) {
    logger.error({ err: String(err) }, '[SDS_TRIGGER] Batch parsing failed');
    return res
      .status(500)
      .json({ error: 'Internal server error', message: String(err?.message || err) });
  }
});

/**
 * Check SDS parsing status for a product
 */
router.get('/status/:productId', async (req, res) => {
  const productId = parseInt(req.params.productId);

  if (isNaN(productId)) {
    return res.status(400).json({ error: 'Invalid productId' });
  }

  try {
    // Get product info
    const { data: product, error: productError } = await supabase
      .from('product')
      .select('id, name, sds_url')
      .eq('id', productId)
      .single();

    if (productError || !product) {
      return res.status(404).json({ error: 'Product not found' });
    }

    // Get metadata if it exists
    const { data: metadata, error: metadataError } = await supabase
      .from('sds_metadata')
      .select('*')
      .eq('product_id', productId)
      .maybeSingle();

    const status = {
      productId,
      productName: product.name,
      hasSdsUrl: !!product.sds_url,
      sdsUrl: product.sds_url,
      hasMetadata: !!metadata,
      metadata: metadata || null,
      status: !product.sds_url ? 'no_sds_url' : metadata ? 'parsed' : 'pending_parse',
    };

    return res.json(status);
  } catch (err: any) {
    logger.error({ productId, err: String(err) }, '[SDS_TRIGGER] Status check failed');
    return res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;
