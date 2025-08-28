// server/utils/autoSdsParsing.ts
import { createServiceRoleClient } from './supabaseClient.js';
import logger from './logger.js';
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

// CRITICAL: Use the same environment variable as scraper.ts and render.yaml
const OCR_SERVICE_URL = process.env.EXPO_PUBLIC_OCR_API_URL || 
                        process.env.OCR_SERVICE_URL || 
                        'http://127.0.0.1:5001';

// Enhanced debugging for OCR service configuration
console.log('[AUTO_SDS_DEBUG] ' + '='.repeat(30));
console.log('[AUTO_SDS_DEBUG] OCR Service URL:', OCR_SERVICE_URL);
console.log('[AUTO_SDS_DEBUG] Environment variables:', {
  EXPO_PUBLIC_OCR_API_URL: process.env.EXPO_PUBLIC_OCR_API_URL || 'NOT_SET',
  OCR_SERVICE_URL: process.env.OCR_SERVICE_URL || 'NOT_SET',
  NODE_ENV: process.env.NODE_ENV,
  PORT: process.env.PORT
});
console.log('[AUTO_SDS_DEBUG] ' + '='.repeat(30));

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

    // First, test if OCR service is available with enhanced error handling
    try {
      logger.info(`Auto-SDS: Testing OCR service at ${OCR_SERVICE_URL}`);
      const healthCheck = await axios.get(`${OCR_SERVICE_URL}/health`, {
        timeout: 10000, // Increased timeout for slow services
        validateStatus: (status) => status < 500, // Accept 4xx as valid responses
      });
      
      logger.info({
        status: healthCheck.status,
        data: healthCheck.data,
        productId
      }, `Auto-SDS: OCR health check response:`);
      
      if (healthCheck.status === 404) {
        logger.error(`Auto-SDS: OCR service not found at ${OCR_SERVICE_URL} - check service URL`);
        await createBasicSdsMetadata(productId, sdsUrl);
        return;
      }
      
      if (healthCheck.status !== 200) {
        logger.error(`Auto-SDS: OCR service unhealthy (status ${healthCheck.status})`);
        await createBasicSdsMetadata(productId, sdsUrl);
        return;
      }
      
      logger.info(`Auto-SDS: OCR service healthy, proceeding with parsing`);
    } catch (healthError: any) {
      logger.error(
        {
          error: healthError.message,
          code: healthError.code,
          url: OCR_SERVICE_URL,
          timeout: healthError.code === 'ECONNABORTED'
        },
        `Auto-SDS: OCR service health check failed for product ${productId}:`
      );
      // Create basic metadata entry without OCR parsing
      await createBasicSdsMetadata(productId, sdsUrl);
      return;
    }

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
      // Create basic metadata entry as fallback
      await createBasicSdsMetadata(productId, sdsUrl);
      return;
    }

    const parsedMetadata = response.data;

    if (parsedMetadata.error) {
      logger.error(
        { error: parsedMetadata.error, productId },
        `Auto-SDS: Parse error for product ${productId}`
      );
      // Create basic metadata entry as fallback
      await createBasicSdsMetadata(productId, sdsUrl);
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
    // Enhanced error handling with more specific error types
    logger.error({
      message: error.message,
      code: error.code,
      status: error.response?.status,
      url: OCR_SERVICE_URL,
      timeout: error.code === 'ECONNABORTED'
    }, `Auto-SDS: Execution error for product ${productId}:`);
    
    if (error.code === 'ECONNREFUSED' || error.code === 'ENOTFOUND') {
      logger.error(
        `Auto-SDS: OCR service not reachable at ${OCR_SERVICE_URL} for product ${productId}`
      );
    } else if (error.response?.status === 404) {
      logger.error(
        `Auto-SDS: OCR service endpoint not found - check service deployment`
      );
    } else if (error.code === 'ECONNABORTED') {
      logger.error(
        `Auto-SDS: OCR service timeout - PDF processing took too long`
      );
    } else if (error.response) {
      logger.error(
        `Auto-SDS: HTTP error ${error.response.status}: ${JSON.stringify(error.response.data)}`
      );
    }
    
    // Create basic metadata entry as fallback for all error types
    await createBasicSdsMetadata(productId, sdsUrl);
  }
}

/**
 * Creates basic SDS metadata when OCR parsing fails
 */
async function createBasicSdsMetadata(productId: number, sdsUrl: string): Promise<void> {
  try {
    const supabase = createServiceRoleClient();
    
    // Get product name for basic metadata
    const { data: product } = await supabase
      .from('product')
      .select('name')
      .eq('id', productId)
      .single();

    const { error: upsertError } = await supabase.from('sds_metadata').upsert({
      product_id: productId,
      vendor: null,
      issue_date: null,
      hazardous_substance: null,
      dangerous_good: null,
      dangerous_goods_class: null,
      description: product?.name || null,
      packing_group: null,
      subsidiary_risks: null,
      raw_json: {
        note: 'Basic metadata created - OCR parsing unavailable',
        sds_url: sdsUrl,
        created_at: new Date().toISOString(),
        ocr_service_url: OCR_SERVICE_URL,
        fallback_reason: 'OCR service unavailable or failed'
      },
    });

    if (!upsertError) {
      // Update user watch lists with basic info
      await supabase
        .from('user_chemical_watch_list')
        .update({
          sds_available: true,
          sds_issue_date: null,
          hazardous_substance: null,
          dangerous_good: null,
          dangerous_goods_class: null,
          packing_group: null,
          subsidiary_risks: null,
        })
        .eq('product_id', productId);

      logger.info(`Auto-SDS: Created basic metadata for product ${productId} (OCR unavailable)`);
    } else {
      logger.error(
        { error: upsertError, productId },
        `Auto-SDS: Failed to create basic metadata for product ${productId}`
      );
    }
  } catch (error) {
    logger.error(
      { error, productId },
      `Auto-SDS: Failed to create basic metadata for product ${productId}`
    );
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
