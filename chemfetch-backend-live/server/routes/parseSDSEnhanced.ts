// server/routes/parseSDSEnhanced.ts
import { Router } from 'express';
import logger from '../utils/logger';
import { createServiceRoleClient } from '../utils/supabaseClient';

const router = Router();

interface ParseSDSEnhancedRequest {
  product_id: number;
  sds_url?: string;
  force?: boolean;
  use_direct_parser?: boolean; // Use the new direct parser endpoint
}

interface ParseSDSEnhancedResponse {
  success: boolean;
  product_id: number;
  message: string;
  parsed_data?: any;
  metadata?: any;
  error?: string;
}

/**
 * POST /parse-sds-enhanced
 * Enhanced SDS parsing using the improved parser
 * Body: { product_id: number, sds_url?: string, force?: boolean, use_direct_parser?: boolean }
 */
router.post('/', async (req, res) => {
  const {
    product_id,
    sds_url,
    force = false,
    use_direct_parser = true,
  }: ParseSDSEnhancedRequest = req.body;

  if (!product_id || typeof product_id !== 'number') {
    return res.status(400).json({
      success: false,
      message: 'product_id is required and must be a number',
    });
  }

  const supabase = createServiceRoleClient();

  try {
    // 1. Get product info from database
    const { data: product, error: productError } = await supabase
      .from('product')
      .select('id, name, sds_url, barcode')
      .eq('id', product_id)
      .single();

    if (productError) {
      logger.error({ error: productError }, 'Failed to fetch product');
      return res.status(404).json({
        success: false,
        message: 'Product not found',
        error: productError.message,
      });
    }

    // 2. Use provided sds_url or fallback to product's sds_url
    const targetSdsUrl = sds_url || product.sds_url;

    if (!targetSdsUrl) {
      return res.status(400).json({
        success: false,
        message: 'No SDS URL available for this product',
      });
    }

    // 3. Check if metadata already exists (unless force=true)
    if (!force) {
      const { data: existingMetadata, error: metadataError } = await supabase
        .from('sds_metadata')
        .select('product_id, created_at')
        .eq('product_id', product_id)
        .single();

      if (existingMetadata && !metadataError) {
        return res.status(200).json({
          success: false,
          product_id,
          message: 'SDS metadata already exists. Use force=true to re-parse.',
        });
      }
    }

    let parsedData: any;

    if (use_direct_parser) {
      // 4a. Use the new direct parser endpoint
      try {
        const ocrServiceUrl = process.env.OCR_SERVICE_URL || 'http://localhost:5001';
        const response = await fetch(`${ocrServiceUrl}/parse-pdf-direct`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            pdf_url: targetSdsUrl,
            product_id: product_id,
          }),
        });

        const ocrResult = await response.json();

        if (!response.ok || !ocrResult.success) {
          throw new Error(ocrResult.error || 'OCR service failed');
        }

        // Transform the direct parser result to chemfetch format
        parsedData = transformToChemfetchFormat(ocrResult.parsed_data, product_id, product.name);
      } catch (ocrError) {
        logger.error({ error: ocrError }, 'OCR service error');
        return res.status(500).json({
          success: false,
          product_id,
          message: 'Failed to parse SDS using enhanced parser',
          error: (ocrError as Error).message,
        });
      }
    } else {
      // 4b. Use the existing parse-sds endpoint
      try {
        const ocrServiceUrl = process.env.OCR_SERVICE_URL || 'http://localhost:5001';
        const response = await fetch(`${ocrServiceUrl}/parse-sds`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            product_id: product_id,
            pdf_url: targetSdsUrl,
          }),
        });

        parsedData = await response.json();

        if (!response.ok) {
          throw new Error(parsedData.error || 'OCR service failed');
        }
      } catch (ocrError) {
        logger.error({ error: ocrError }, 'OCR service error');
        return res.status(500).json({
          success: false,
          product_id,
          message: 'Failed to parse SDS using legacy parser',
          error: (ocrError as Error).message,
        });
      }
    }

    // 5. Store metadata in database
    logger.info(
      { parsedData, product_id },
      `Storing enhanced SDS metadata for product ${product_id}`
    );

    const { error: upsertError } = await supabase.from('sds_metadata').upsert({
      product_id,
      vendor: parsedData.vendor,
      issue_date: parsedData.issue_date,
      hazardous_substance: parsedData.hazardous_substance,
      dangerous_good: parsedData.dangerous_good,
      dangerous_goods_class: parsedData.dangerous_goods_class,
      description: parsedData.product_name,
      packing_group: parsedData.packing_group,
      subsidiary_risks: parsedData.subsidiary_risks,
      raw_json: parsedData,
    });

    if (upsertError) {
      logger.error({ error: upsertError }, 'Failed to store SDS metadata');
      return res.status(500).json({
        success: false,
        product_id,
        message: 'Failed to store SDS metadata',
        error: upsertError.message,
      });
    }

    // 6. Update user watch lists with parsed data
    const { error: updateError } = await supabase
      .from('user_chemical_watch_list')
      .update({
        sds_available: true,
        sds_issue_date: parsedData.issue_date,
        hazardous_substance: parsedData.hazardous_substance,
        dangerous_good: parsedData.dangerous_good,
        dangerous_goods_class: parsedData.dangerous_goods_class,
        packing_group: parsedData.packing_group,
        subsidiary_risks: parsedData.subsidiary_risks,
      })
      .eq('product_id', product_id);

    if (updateError) {
      logger.warn({ error: updateError }, 'Failed to update user watch lists');
    }

    logger.info(`Successfully parsed SDS for product ${product_id} using enhanced parser`);
    return res.status(200).json({
      success: true,
      product_id,
      message: 'SDS parsed and stored successfully using enhanced parser',
      parsed_data: use_direct_parser ? parsedData : undefined,
      metadata: parsedData,
    });
  } catch (error) {
    logger.error({ error }, 'Error in enhanced SDS parsing route');
    return res.status(500).json({
      success: false,
      product_id,
      message: 'Internal server error',
      error: (error as Error).message,
    });
  }
});

/**
 * Transform direct parser output to chemfetch format
 */
function transformToChemfetchFormat(
  directParserResult: any,
  productId: number,
  productName: string
): any {
  function getValue(fieldName: string): string | null {
    const field = directParserResult[fieldName];
    if (field && typeof field === 'object' && field.confidence > 0) {
      return field.value || null;
    }
    return null;
  }

  // Map dangerous goods class to boolean
  const dangerousGoodsClass = getValue('dangerous_goods_class');
  const isDangerousGood =
    dangerousGoodsClass &&
    !['none', 'not applicable', 'n/a', 'na'].includes(dangerousGoodsClass.toLowerCase());

  // Determine if it's hazardous (basic heuristic)
  const isHazardous = isDangerousGood;

  // Format subsidiary risks
  const subsidiaryRisk = getValue('subsidiary_risk');
  const subsidiaryRisks =
    subsidiaryRisk &&
    !['none', 'not applicable', 'n/a', 'na'].includes(subsidiaryRisk.toLowerCase())
      ? [subsidiaryRisk]
      : [];

  return {
    product_id: productId,
    product_name: getValue('product_name') || productName,
    vendor: getValue('manufacturer'),
    issue_date: getValue('issue_date'),
    hazardous_substance: isHazardous,
    dangerous_good: isDangerousGood,
    dangerous_goods_class: dangerousGoodsClass,
    packing_group: getValue('packing_group'),
    subsidiary_risks: subsidiaryRisks,
    hazard_statements: [], // Not extracted by current parser
    raw_json: directParserResult,
  };
}

export default router;
