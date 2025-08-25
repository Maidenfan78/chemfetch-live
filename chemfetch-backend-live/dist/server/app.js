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
import verifySdsProxy from './routes/verifySds.js'; // Keep SDS verification OCR
import parseSDSEnhancedRoute from './routes/parseSDSEnhanced.js';
dotenv.config();
const app = express();
// CORS configuration
const corsOptions = {
    origin: process.env.NODE_ENV === 'production' ? process.env.FRONTEND_URL?.split(',') || true : true,
    credentials: true,
    optionsSuccessStatus: 200,
};
app.use(cors(corsOptions));
app.use(express.json({ limit: '15mb' }));
app.use('/sds-by-name', sdsByNameRoute);
app.use(pinoHttp({ logger }));
const limiter = rateLimit({ windowMs: 60_000, max: 60 });
app.use(limiter);
// Security headers
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
app.use('/verify-sds', verifySdsProxy); // Keep SDS verification OCR
// Load parse-sds route dynamically to avoid ESM parsing issues in tests
try {
    const parseSdsRoute = require('./routes/parseSds').default;
    app.use('/parse-sds', parseSdsRoute);
}
catch (err) {
    logger.warn({ err }, 'parse-sds route not loaded');
}
app.use('/parse-sds-enhanced', parseSDSEnhancedRoute);
app.use('/batch-sds', batchSdsRoute);
export default app;
