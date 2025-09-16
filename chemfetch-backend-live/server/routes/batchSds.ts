import express from 'express';
import { createServiceRoleClient } from '../utils/supabaseClient.js';
import { triggerAutoSdsParsing, triggerBatchAutoSdsParsing } from '../utils/autoSdsParsing.js';
import logger from '../utils/logger.js';

const router = express.Router();

router.post('/process-all', async (_req, res) => {
  try {
    logger.info('[BATCH-SDS] Starting full processing');
    triggerBatchAutoSdsParsing();
    res.json({
      success: true,
      message: 'Batch SDS processing started in background',
    });
  } catch (error) {
    logger.error({ error }, '[BATCH-SDS] Failed to trigger batch processing');
    res.status(500).json({
      success: false,
      message: 'Failed to start batch processing',
      error: error instanceof Error ? error.message : String(error),
    });
  }
});

router.post('/process-product', async (req, res) => {
  const { product_id, force = false } = req.body ?? {};

  if (typeof product_id !== 'number') {
    return res.status(400).json({
      success: false,
      message: 'product_id is required and must be a number',
    });
  }

  try {
    logger.info({ productId: product_id, force }, '[BATCH-SDS] Processing product');
    const triggered = await triggerAutoSdsParsing(product_id, { force: Boolean(force) });
    if (triggered) {
      res.json({
        success: true,
        message: `SDS parsing triggered for product ${product_id}`,
        product_id,
      });
    } else {
      res.json({
        success: false,
        message: `No SDS parsing needed for product ${product_id}`,
        product_id,
      });
    }
  } catch (error) {
    logger.error({ error, product_id }, '[BATCH-SDS] Failed to process product');
    res.status(500).json({
      success: false,
      message: `Failed to process product ${product_id}`,
      error: error instanceof Error ? error.message : String(error),
    });
  }
});

router.get('/status', async (_req, res) => {
  try {
    const supabase = createServiceRoleClient();

    const { count: totalWithSds = 0 } = await supabase
      .from('product')
      .select('*', { count: 'exact', head: true })
      .not('sds_url', 'is', null)
      .not('sds_url', 'eq', '');

    const { count: totalWithMetadata = 0 } = await supabase
      .from('sds_metadata')
      .select('*', { count: 'exact', head: true });

    const { data: productsWithSds = [] } = await supabase
      .from('product')
      .select('id')
      .not('sds_url', 'is', null)
      .not('sds_url', 'eq', '');

    const { data: productsWithMetadata = [] } = await supabase
      .from('sds_metadata')
      .select('product_id');

    const processedIds = new Set((productsWithMetadata ?? []).map(row => row.product_id));
    const pendingCount = (productsWithSds ?? []).filter(row => !processedIds.has(row.id)).length;

    res.json({
      success: true,
      statistics: {
        total_products_with_sds: totalWithSds,
        total_with_metadata: totalWithMetadata,
        pending_processing: pendingCount,
        processing_rate: totalWithSds
          ? Math.round(((totalWithMetadata ?? 0) / totalWithSds) * 100)
          : 0,
      },
    });
  } catch (error) {
    logger.error({ error }, '[BATCH-SDS] Failed to get status');
    res.status(500).json({
      success: false,
      message: 'Failed to get processing status',
      error: error instanceof Error ? error.message : String(error),
    });
  }
});

export default router;
