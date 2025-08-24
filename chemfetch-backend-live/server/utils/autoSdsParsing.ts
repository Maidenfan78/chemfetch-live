// server/utils/autoSdsParsing.ts
import { createServiceRoleClient } from './supabaseClient';
import logger from './logger';
import axios from 'axios';

// Utility function to convert dates to ISO format for PostgreSQL
function convertToISODate(dateString: string | null | undefined): string | null {
  if (!dateString) return null;

  try {
    // Handle various date formats commonly found in SDS documents
    const date = new Date(dateString);

    // If direct parsing fails, try manual parsing for DD/MM/YYYY format
    if (isNaN(date.getTime()) && typeof dateString === 'string') {
      const match = dateString.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})$/);
      if (match) {
        const [, day, month, year] = match;
        const fullYear = year.length === 2 ? `20${year}` : year;
        const parsedDate = new Date(
          `${fullYear}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`
        );
        if (!isNaN(parsedDate.getTime())) {
          return parsedDate.toISOString().split('T')[0]; // Return YYYY-MM-DD format
        }
      }
    }

    if (!isNaN(date.getTime())) {
      return date.toISOString().split('T')[0]; // Return YYYY-MM-DD format
    }

    logger.warn(`Failed to parse date: ${dateString}`);
    return null;
  } catch (error) {
    logger.warn(`Error converting date '${dateString}': ${(error as Error).message}`);
    return null;
  }
}

const OCR_SERVICE_URL = process.env.OCR_SERVICE_URL || 'http://127.0.0.1:5001';

interface AutoParseOptions {
  force?: boolean;
  delay?: number; // Optional delay in milliseconds before parsing
}

/**
 * Automatically triggers SDS parsing for a product if it has an SDS URL
 * but no existing metadata (unless force=true)
 */
export async function triggerAutoSdsParsing(
  productId: number,
  options: AutoParseOptions = {}
): Promise<boolean> {
  const { force = false, delay = 0 } = options;

  try {
    const supabase = createServiceRoleClient();

    // Get product info
    const { data: product, error: productError } = await supabase
      .from('product')
      .select('id, name, sds_url')
      .eq('id', productId)
      .single();

    if (productError || !product?.sds_url) {
      logger.debug(`Auto-SDS: No SDS URL for product ${productId}`);
      return false;
    }

    // Check if metadata already exists (unless force=true)
    if (!force) {
      const { data: existingMetadata } = await supabase
        .from('sds_metadata')
        .select('product_id')
        .eq('product_id', productId)
        .single();

      if (existingMetadata) {
        logger.debug(`Auto-SDS: Metadata already exists for product ${productId}`);
        return false;
      }
    }

    // Add optional delay (useful for rate limiting or batching)
    if (delay > 0) {
      setTimeout(() => executeSdsParsing(productId, product.sds_url), delay);
    } else {
      // Execute immediately in background
      setImmediate(() => executeSdsParsing(productId, product.sds_url));
    }

    logger.info(`Auto-SDS: Triggered parsing for product ${productId}`);
    return true;
  } catch (error) {
    logger.error(
      { error, productId },
      `Auto-SDS: Failed to trigger parsing for product ${productId}`
    );
    return false;
  }
}

/**
 * Executes the actual SDS parsing using HTTP API
 */
async function executeSdsParsing(productId: number, sdsUrl: string): Promise<void> {
  try {
    logger.info(`Auto-SDS: Starting HTTP parsing for product ${productId}`);
    logger.info(`Auto-SDS: SDS URL: ${sdsUrl}`);
    logger.info(`Auto-SDS: OCR Service URL: ${OCR_SERVICE_URL}`);

    const startTime = Date.now();

    // Call the OCR service HTTP endpoint
    const response = await axios.post(
      `${OCR_SERVICE_URL}/parse-sds`,
      {
        product_id: productId,
        pdf_url: sdsUrl,
      },
      {
        timeout: 3 * 60 * 1000, // 3 minutes timeout
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    const duration = Date.now() - startTime;
    logger.info(`Auto-SDS: HTTP parsing completed for product ${productId} in ${duration}ms`);

    if (response.status !== 200) {
      logger.error(
        `Auto-SDS: HTTP parsing failed for product ${productId} with status ${response.status}`
      );
      logger.error(`Auto-SDS: Response data: ${JSON.stringify(response.data)}`);
      return;
    }

    const parsedMetadata = response.data;

    if (parsedMetadata.error) {
      logger.error(
        { error: parsedMetadata.error, productId },
        `Auto-SDS: Parse error for product ${productId}`
      );
      return;
    }

    logger.debug(
      { parsedMetadata, productId },
      `Auto-SDS: Parsed metadata for product ${productId}`
    );

    // Store metadata in database
    const supabase = createServiceRoleClient();
    const { error: upsertError } = await supabase.from('sds_metadata').upsert({
      product_id: productId,
      vendor: parsedMetadata.vendor,
      issue_date: convertToISODate(parsedMetadata.issue_date),
      hazardous_substance: parsedMetadata.hazardous_substance,
      dangerous_good: parsedMetadata.dangerous_good,
      dangerous_goods_class: parsedMetadata.dangerous_goods_class,
      description: parsedMetadata.product_name,
      packing_group: parsedMetadata.packing_group,
      subsidiary_risks: parsedMetadata.subsidiary_risks,
      raw_json: parsedMetadata.raw_json || parsedMetadata,
    });

    if (upsertError) {
      logger.error(
        { error: upsertError, productId },
        `Auto-SDS: Failed to store metadata for product ${productId}`
      );
      return;
    }

    // Update user watch lists
    await supabase
      .from('user_chemical_watch_list')
      .update({
        sds_available: true,
        sds_issue_date: convertToISODate(parsedMetadata.issue_date),
        hazardous_substance: parsedMetadata.hazardous_substance,
        dangerous_good: parsedMetadata.dangerous_good,
        dangerous_goods_class: parsedMetadata.dangerous_goods_class,
        packing_group: parsedMetadata.packing_group,
        subsidiary_risks: parsedMetadata.subsidiary_risks,
      })
      .eq('product_id', productId);

    logger.info(`Auto-SDS: Successfully parsed and stored metadata for product ${productId}`);
  } catch (error: any) {
    if (error.code === 'ECONNREFUSED') {
      logger.error(
        `Auto-SDS: OCR service not available at ${OCR_SERVICE_URL} for product ${productId}`
      );
    } else if (error.response) {
      logger.error(
        {
          status: error.response.status,
          data: error.response.data,
          productId,
        },
        `Auto-SDS: HTTP error for product ${productId}`
      );
    } else {
      logger.error(
        { error: error.message, productId },
        `Auto-SDS: Execution error for product ${productId}`
      );
    }
  }
}

/**
 * Batch process all products with SDS URLs but no metadata
 */
export async function triggerBatchAutoSdsParsing(): Promise<void> {
  try {
    const supabase = createServiceRoleClient();

    // Get all products with SDS URLs that don't have metadata
    const { data: products } = await supabase
      .from('product')
      .select('id, name, sds_url')
      .not('sds_url', 'is', null)
      .not('sds_url', 'eq', '');

    if (!products?.length) {
      logger.info('Auto-SDS: No products found for batch processing');
      return;
    }

    // Get existing metadata to filter out already processed products
    const { data: existingMetadata } = await supabase.from('sds_metadata').select('product_id');

    const existingIds = new Set(existingMetadata?.map(m => m.product_id) || []);
    const pendingProducts = products.filter(p => !existingIds.has(p.id));

    logger.info(`Auto-SDS: Starting batch processing for ${pendingProducts.length} products`);

    // Process with delays to avoid overwhelming the system
    for (let i = 0; i < pendingProducts.length; i++) {
      const product = pendingProducts[i];
      const delay = i * 5000; // 5 second delay between each

      await triggerAutoSdsParsing(product.id, { delay });
    }
  } catch (error) {
    logger.error({ error }, 'Auto-SDS: Batch processing failed');
  }
}
