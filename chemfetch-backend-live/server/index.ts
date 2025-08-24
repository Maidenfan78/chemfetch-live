// server/index.ts
import app from './app';
import logger from './utils/logger';

// Note: OCR route registration is now handled in app.ts to avoid duplicate registration
// The proxy configuration is properly centralized in the main app configuration.

// ---------------------------------------------------------------------------
// 🩺  Health check (verifies proxy path)
// ---------------------------------------------------------------------------
app.get('/ocr/health', (_req, res) => res.json({ status: 'ok', target: '127.0.0.1:5001' }));

// Health check for Render
app.get('/health', (_req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV,
  });
});

// ---------------------------------------------------------------------------
// 🏁  Start server
// ---------------------------------------------------------------------------
const PORT = parseInt(process.env.PORT || '3001', 10);
app.listen(PORT, '0.0.0.0', () => {
  logger.info(`Backend API listening on port ${PORT}`);
  logger.info(`Environment: ${process.env.NODE_ENV}`);
});

// ---------------------------------------------------------------------------
// 🛑  Graceful shutdown
// ---------------------------------------------------------------------------
process.on('SIGINT', () => {
  logger.info('Received SIGINT, shutting down gracefully');
  process.exit(0);
});

process.on('SIGTERM', () => {
  logger.info('Received SIGTERM, shutting down gracefully');
  process.exit(0);
});
