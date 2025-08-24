// lib/logger.ts - Mobile App Console Logging
// Expo captures console output - no file system logging needed

interface LogEntry {
  timestamp: string;
  level: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG';
  component: string;
  message: string;
  data?: any;
}

class MobileLogger {
  private formatLogEntry(entry: LogEntry): string {
    const dataStr = entry.data ? ` | ${JSON.stringify(entry.data)}` : '';
    return `${entry.timestamp} [${entry.level}] [${entry.component}] ${entry.message}${dataStr}`;
  }

  info(component: string, message: string, data?: any) {
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level: 'INFO',
      component,
      message,
      data,
    };
    console.info(this.formatLogEntry(entry));
  }

  warn(component: string, message: string, data?: any) {
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level: 'WARN',
      component,
      message,
      data,
    };
    console.warn(this.formatLogEntry(entry));
  }

  error(component: string, message: string, data?: any) {
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level: 'ERROR',
      component,
      message,
      data,
    };
    console.error(this.formatLogEntry(entry));
  }

  debug(component: string, message: string, data?: any) {
    if (__DEV__) {
      const entry: LogEntry = {
        timestamp: new Date().toISOString(),
        level: 'DEBUG',
        component,
        message,
        data,
      };
      console.debug(this.formatLogEntry(entry));
    }
  }

  // For compatibility with existing code that might expect these methods
  async getLogFilePath(): Promise<string> {
    return 'Console logging only - check Expo logs in terminal or Expo dashboard';
  }

  async getRecentLogs(lines: number = 100): Promise<string> {
    return 'Console logging only - check Expo logs in terminal or Expo dashboard';
  }
}

export const mobileLogger = new MobileLogger();
export default mobileLogger;
