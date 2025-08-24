import * as FileSystem from 'expo-file-system';
import { Platform } from 'react-native';
import { OCR_API_URL } from './constants';

export interface OcrResult {
  bestName?: string;
  bestSize?: string;
  text?: string;
}

export interface CropInfo {
  left: number;
  top: number;
  width: number;
  height: number;
  screenWidth: number;
  screenHeight: number;
  photoWidth: number;
  photoHeight: number;
}

async function safeJson(res: Response) {
  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`Unexpected response from OCR service (${res.status}): ${text.slice(0, 120)}…`);
  }
}

export async function runOcr(imageUri: string, cropInfo: CropInfo): Promise<OcrResult> {
  // DEBUG: Raw image URI
  console.debug('[DEBUG][imageUri]', imageUri);
  // DEBUG: Crop coordinates
  console.debug('[DEBUG][cropInfo]', cropInfo);

  try {
    const info = await FileSystem.getInfoAsync(imageUri);
    console.debug('[DEBUG][file exists]', info.exists);
  } catch (e) {
    console.warn('[DEBUG][file] Could not check file existence', e);
  }

  const form = new FormData();
  // Append crop metadata
  form.append('left', String(cropInfo.left));
  form.append('top', String(cropInfo.top));
  form.append('width', String(cropInfo.width));
  form.append('height', String(cropInfo.height));
  form.append('screenWidth', String(cropInfo.screenWidth));
  form.append('screenHeight', String(cropInfo.screenHeight));
  form.append('photoWidth', String(cropInfo.photoWidth));
  form.append('photoHeight', String(cropInfo.photoHeight));

  const fileName = `capture.${Platform.OS === 'ios' ? 'heic' : 'jpg'}`;
  form.append('image', { uri: imageUri, name: fileName, type: 'image/jpeg' } as any, fileName);

  const ocrUrl = `${OCR_API_URL}/ocr${__DEV__ ? '?mode=debug' : ''}`;
  console.info('[OCR] Posting to', ocrUrl);

  const res = await fetch(ocrUrl, {
    method: 'POST',
    body: form,
  });

  if (__DEV__) console.info('[OCR] POST status', res.status);
  if (!res.ok) {
    const errBody = await res.text();
    console.error('[OCR] Server error body:', errBody);
    throw new Error(`OCR request failed with status ${res.status}`);
  }

  const data: any = await safeJson(res);
  if (data.error) throw new Error(data.error);

  let bestName = '';
  let bestSize = '';

  if (data.predominant?.text) {
    bestName = String(data.predominant.text).replace(/\n+/g, ' ').trim();
  } else if (typeof data.text === 'string') {
    bestName = data.text.replace(/\n+/g, ' ').trim();
  }

  const sizePattern = /(\d+(?:\.\d+)?\s?(?:ml|mL|g|kg|oz|l))/i;
  if (Array.isArray(data.lines)) {
    for (const line of data.lines) {
      const txt = String(line.text || '').trim();
      if (!bestSize) {
        const m = txt.match(sizePattern);
        if (m) bestSize = m[0];
      }
    }
  }
  if (!bestSize && typeof data.text === 'string') {
    const m = data.text.match(sizePattern);
    if (m) bestSize = m[0];
  }

  return { bestName, bestSize, text: data.text };
}
