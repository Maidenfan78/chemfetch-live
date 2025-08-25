// lib/constants.ts
// Centralised configuration helpers & URLs for ChemFetch mobile
// --------------------------------------------------------------

import Constants from 'expo-constants';
import { Platform } from 'react-native';

/**
 * Tries to determine the host machine running Metro / backend when in development.
 *
 * Priority:
 *   1. `EXPO_PUBLIC_DEV_HOST` env var (explicit override).
 *   2. Expo's `hostUri` (works in Expo Go + dev-client on real devices).
 *   3. Emulators: 10.0.2.2 (Android) or localhost (iOS/macOS simulator).
 */
function guessHost(): string {
  if (process.env.EXPO_PUBLIC_DEV_HOST) return process.env.EXPO_PUBLIC_DEV_HOST;

  const uri = Constants?.expoConfig?.hostUri || Constants?.expoGoConfig?.debuggerHost || '';
  if (uri) return uri.split(':').shift()!; // "192.168.0.23" when hostUri="192.168.0.23:8081"

  if (Platform.OS === 'android') return '10.0.2.2';
  return 'localhost';
}

// ----------------------  Debug / visibility  -----------------------------
/**
 * The value ChemFetch resolved for the host machine.  Surface it so that
 * other modules (or runtime logs) can display it for easier diagnostics.
 */
export const HOST_GUESS = guessHost();

if (__DEV__) {
  console.info(`[ChemFetch] guessHost() resolved to: ${HOST_GUESS}`);
  console.info(`[ChemFetch] BACKEND_API_URL resolved to: ${BACKEND_API_URL}`);
  console.info(`[ChemFetch] ENV EXPO_PUBLIC_BACKEND_API_URL: ${process.env.EXPO_PUBLIC_BACKEND_API_URL}`);
}

// ----------------------  Public URLs  ------------------------------------
// lib/constants.ts
export const BACKEND_API_URL =
  process.env.EXPO_PUBLIC_BACKEND_API_URL || `http://${HOST_GUESS}:3001`;

// Make OCR fall back to the backend proxy instead of :5001
export const OCR_API_URL = process.env.EXPO_PUBLIC_OCR_API_URL || BACKEND_API_URL;
