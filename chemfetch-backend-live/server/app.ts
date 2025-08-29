// server/app.ts
import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import rateLimit from 'express-rate-limit';
import pinoHttp from 'pino-http';

// 👇 add .js on all relative imports
import sdsByNameRoute from './routes/sdsByName.js';
import batchSdsRoute from './routes/batchSds.js';
import logger from './utils/logger.js';
import scanRoute from './routes/scan.js';
import manualScanRoute from './routes/manualScan.js';
import sdsTriggerRoute from './routes/sdsTrigger.js';
import confirmRoute from './routes/confirm.js';
import healthRoute from './routes/health.js';
import verifySdsProxy from './routes/verifySds.js';
import parseSDSEnhancedRoute from './routes/parseSDSEnhanced.js';
import parseSdsRoute from './routes/parseSds.js';

dotenv.config();

const app = express();

// CORS configuration (kept as-is) …
const corsOptions = {
  origin: (origin: string | undefined, callback: (err: Error | null, allow?: boolean) => void) => {
    if (!origin) return callback(null, true);
    if (process.env.NODE_ENV === 'production') {
      const allowedOrigins = process.env.FRONTEND_URL?.split(',') || [
        'https://chemfetch.com',
        'https://*.vercel.app',
        'exp://localhost:8081',
        'exp://192.168.*:*',
      ];
      return callback(null, true);
    }
    callback(null, true);
  },
  credentials: true,
  optionsSuccessStatus: 200,
};

app.use(cors(corsOptions));
app.use(express.json({ limit: '15mb' }));
app.use('/sds-by-name', sdsByNameRoute);

// 🔧 Fix: pino-http callable typing under ESM/NodeNext
const pinoHttpFactory = pinoHttp as unknown as (opts?: {
  logger?: any;
}) => import('pino-http').HttpLogger;
app.use(pinoHttpFactory({ logger }));

const limiter = rateLimit({ windowMs: 60_000, max: 60 });
app.use(limiter);

// Security headers …
app.use((req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  next();
});

app.use('/scan', scanRoute);
app.use('/manual-scan', manualScanRoute);
app.use('/sds-trigger', sdsTriggerRoute);
app.use('/confirm', confirmRoute);
app.use('/health', healthRoute);
app.use('/verify-sds', verifySdsProxy);
app.use('/parse-sds', parseSdsRoute);
app.use('/parse-sds-enhanced', parseSDSEnhancedRoute);
app.use('/batch-sds', batchSdsRoute);

export default app;
