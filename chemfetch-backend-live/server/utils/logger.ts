import pino from 'pino';
import path from 'path';
import fs from 'fs';

// Ensure logs directory exists
const logsDir = path.join(process.cwd(), 'logs');
if (!fs.existsSync(logsDir)) {
  fs.mkdirSync(logsDir, { recursive: true });
}

// Simple file-based logger that also logs to console
const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  timestamp: () => `,"time":"${new Date().toISOString()}"`,
});

// Custom write function to also write to file
const originalWrite = process.stdout.write;
const getLogFileName = () => {
  const date = new Date().toISOString().split('T')[0];
  return path.join(logsDir, `backend-${date}.log`);
};

process.stdout.write = function (chunk: any, encoding?: any, callback?: any) {
  // Write to console (original behavior)
  const result = originalWrite.call(this, chunk, encoding, callback);

  // Also write to file if it's a log message
  if (typeof chunk === 'string' && chunk.includes('"level"')) {
    try {
      const logFile = getLogFileName();
      fs.appendFileSync(logFile, chunk, 'utf8');
    } catch (error) {
      // Ignore file write errors to not break console logging
    }
  }

  return result;
};

export default logger;
