// lib/network.ts - Network utility functions for debugging and API calls
import { BACKEND_API_URL } from './constants';
import { mobileLogger } from './logger';

export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  status?: number;
}

export class NetworkUtil {
  /**
   * Test connection to backend API
   */
  static async testBackendConnection(): Promise<ApiResponse> {
    try {
      mobileLogger.info('NETWORK_TEST', `Testing connection to: ${BACKEND_API_URL}`);
      
      const response = await fetch(`${BACKEND_API_URL}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        // Add timeout for mobile networks
      });

      const data = await response.json();
      
      if (response.ok) {
        mobileLogger.info('NETWORK_TEST', 'Backend connection successful', {
          status: response.status,
          data,
        });
        return { data, status: response.status };
      } else {
        mobileLogger.error('NETWORK_TEST', 'Backend connection failed', {
          status: response.status,
          statusText: response.statusText,
          data,
        });
        return { 
          error: `HTTP ${response.status}: ${response.statusText}`, 
          status: response.status 
        };
      }
    } catch (error: any) {
      mobileLogger.error('NETWORK_TEST', 'Network request failed', {
        error: error.message,
        backendUrl: BACKEND_API_URL,
      });
      return { 
        error: `Network error: ${error.message}`,
        status: 0
      };
    }
  }

  /**
   * Enhanced fetch with better error handling and logging
   */
  static async fetchWithLogging(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<Response> {
    const url = `${BACKEND_API_URL}${endpoint}`;
    const requestId = Math.random().toString(36).substring(7);
    
    mobileLogger.info('API_REQUEST', `[${requestId}] ${options.method || 'GET'} ${endpoint}`, {
      url,
      headers: options.headers,
      hasBody: !!options.body,
    });

    const startTime = Date.now();
    
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      const duration = Date.now() - startTime;
      
      if (response.ok) {
        mobileLogger.info('API_REQUEST', `[${requestId}] Success`, {
          status: response.status,
          duration,
        });
      } else {
        mobileLogger.warn('API_REQUEST', `[${requestId}] HTTP Error`, {
          status: response.status,
          statusText: response.statusText,
          duration,
        });
      }

      return response;
    } catch (error: any) {
      const duration = Date.now() - startTime;
      mobileLogger.error('API_REQUEST', `[${requestId}] Network Error`, {
        error: error.message,
        duration,
        url,
      });
      throw error;
    }
  }

  /**
   * Scan barcode with enhanced error handling
   */
  static async scanBarcode(code: string, userId?: string): Promise<ApiResponse> {
    try {
      const response = await this.fetchWithLogging('/scan', {
        method: 'POST',
        body: JSON.stringify({ code, userId }),
      });

      const data = await response.json();
      return { data, status: response.status };
    } catch (error: any) {
      return { 
        error: `Scan failed: ${error.message}`,
        status: 0
      };
    }
  }
}
