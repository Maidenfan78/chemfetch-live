import { Router } from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
import dotenv from 'dotenv';
import logger from '../utils/logger.js';

dotenv.config();

const OCR_SERVICE_URL = process.env.OCR_SERVICE_URL || 'http://localhost:5001';

const router = Router();

const proxy = createProxyMiddleware({
  target: OCR_SERVICE_URL,
  changeOrigin: true,
  pathRewrite: () => '/ocr',
  onProxyReq: proxyReq => {
    logger.debug(
      {
        method: proxyReq.method,
        path: proxyReq.path,
        headers: {
          'content-type': proxyReq.getHeader('content-type'),
          'content-length': proxyReq.getHeader('content-length'),
        },
      },
      '[OCR Proxy] Forwarding request',
    );
  },
  onProxyRes: proxyRes => {
    logger.debug(
      {
        statusCode: proxyRes.statusCode,
        headers: proxyRes.headers,
      },
      '[OCR Proxy] Response received',
    );
  },
  headers: {
    'X-Forwarded-By': 'chemfetch-backend',
  },
} as any);

router.use('/', proxy);

export default router;
