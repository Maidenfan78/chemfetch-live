import { BACKEND_API_URL } from '../lib/constants';
import { supabase } from '../lib/supabase';
import { mobileLogger } from '../lib/logger';
import { useIsFocused } from '@react-navigation/native';
import { BarcodeScanningResult, CameraView, useCameraPermissions } from 'expo-camera';
import { useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Image,
  Pressable,
  StyleSheet,
  Text,
  Vibration,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

// ------- Tuning knobs -------
const SCAN_CONFIRMATIONS = 2; // how many identical reads required
const SCAN_WINDOW_MS = 1200; // time window to accumulate confirmations
const RESCAN_COOLDOWN_MS = 1200; // how long before allowing another scan

// ================================================================
// Checksum validators & normalizers for common retail symbologies
// We normalize to a canonical GTIN when possible:
//  - EAN-13 => GTIN-13 (as-is)
//  - UPC-A (12) => prepend '0' -> GTIN-13
//  - UPC-E (8) => expand to UPC-A then prepend '0' -> GTIN-13
//  - EAN-8 => GTIN-8 (as-is)
//  - ITF-14 => GTIN-14 (as-is)
// Code128/Code39/Code93 may encode a GTIN; if the payload is purely
// digits with a valid length/checksum, we use it. Otherwise ignored.
// ================================================================

function isValidEAN8(code: string): boolean {
  if (!/^\d{8}$/.test(code)) {
    return false;
  }
  const d = code.split('').map(Number);
  const odd = d[0] + d[2] + d[4] + d[6];
  const even = d[1] + d[3] + d[5];
  const sum = odd * 3 + even;
  const check = (10 - (sum % 10)) % 10;
  return check === d[7];
}

function isValidEAN13(code: string): boolean {
  if (!/^\d{13}$/.test(code)) {
    return false;
  }
  const d = code.split('').map(Number);
  let sum = 0; // weight 1 at even indices (0‑based), 3 at odd
  for (let i = 0; i < 12; i++) {
    sum += d[i] * (i % 2 ? 3 : 1);
  }
  const check = (10 - (sum % 10)) % 10;
  return check === d[12];
}

function isValidUPCA(code: string): boolean {
  if (!/^\d{12}$/.test(code)) {
    return false;
  }
  const d = code.split('').map(Number);
  let sum = 0;
  // positions 0,2,4,6,8,10 weighted by 3; 1,3,5,7,9,11 by 1 (but 11 is check)
  for (let i = 0; i < 11; i++) {
    sum += d[i] * (i % 2 === 0 ? 3 : 1);
  }
  const check = (10 - (sum % 10)) % 10;
  return check === d[11];
}

// Expand UPC-E (NS 0/1) to UPC-A (per GS1 rules). Returns null if invalid.
function expandUPCEtoUPCA(upce: string): string | null {
  if (!/^\d{8}$/.test(upce)) {
    return null;
  }
  const d = upce.split('').map(Number);
  const numberSystem = d[0];
  const checkDigit = d[7];
  if (numberSystem !== 0 && numberSystem !== 1) {
    return null;
  } // only NS 0/1 supported here
  let upcaBody = '';
  switch (d[6]) {
    case 0:
    case 1:
    case 2:
      // MFG: M1 M2 R6, PROD: 0000 R4 R5
      upcaBody = `${numberSystem}${d[1]}${d[2]}${d[6]}0000${d[3]}${d[4]}${d[5]}`;
      break;
    case 3:
      // MFG: M1 M2 M3, PROD: 00000 R4
      upcaBody = `${numberSystem}${d[1]}${d[2]}${d[3]}00000${d[4]}`;
      break;
    case 4:
      // MFG: M1 M2 M3 M4, PROD: 00000 R5
      upcaBody = `${numberSystem}${d[1]}${d[2]}${d[3]}${d[4]}00000${d[5]}`;
      break;
    default:
      // 5-9: MFG: M1 M2 M3 M4 M5, PROD: 0000 R6
      upcaBody = `${numberSystem}${d[1]}${d[2]}${d[3]}${d[4]}${d[5]}0000${d[6]}`;
  }
  // calculate UPC-A checksum
  const digits = upcaBody.split('').map(Number);
  let sum = 0;
  for (let i = 0; i < 11; i++) {
    sum += digits[i] * (i % 2 === 0 ? 3 : 1);
  }
  const check = (10 - (sum % 10)) % 10;
  if (check !== checkDigit) {
    return null;
  }
  return `${upcaBody}${check}`; // 12-digit UPC-A
}

function isValidUPCE(code: string): boolean {
  const upca = expandUPCEtoUPCA(code);
  return !!upca; // expansion verified checksum
}

function isValidITF14(code: string): boolean {
  if (!/^\d{14}$/.test(code)) {
    return false;
  }
  const d = code.split('').map(Number);
  let sum = 0; // same mod-10 scheme as EAN-13 over first 13 digits
  for (let i = 0; i < 13; i++) {
    sum += d[i] * (i % 2 ? 3 : 1);
  }
  const check = (10 - (sum % 10)) % 10;
  return check === d[13];
}

// Normalize scanned payload to a canonical GTIN string we store/use.
function normalizeToGtin(raw: string): string | null {
  const data = (raw || '').trim();
  if (!data) {
    return null;
  }
  // Pure numeric? Try the standard GTIN forms.
  if (/^\d+$/.test(data)) {
    if (data.length === 8 && isValidEAN8(data)) {
      return data;
    } // GTIN-8
    if (data.length === 12 && isValidUPCA(data)) {
      return `0${data}`;
    } // UPC-A -> GTIN-13
    if (data.length === 13 && isValidEAN13(data)) {
      return data;
    } // GTIN-13
    if (data.length === 14 && isValidITF14(data)) {
      return data;
    } // GTIN-14
  }
  // UPC-E (8) encoded sometimes reported as payload w/ checksum
  if (/^\d{8}$/.test(data) && isValidUPCE(data)) {
    const upca = expandUPCEtoUPCA(data)!; // checked by isValidUPCE
    return `0${upca}`.slice(0, 13); // UPC-A -> GTIN-13
  }
  // Some 1D symbologies (Code128/39/93) may carry a GTIN as digits; if so, try to parse
  const digits = data.replace(/\D+/g, '');
  if (digits) {
    const n = normalizeToGtin(digits);
    if (n) {
      return n;
    }
  }
  return null; // unsupported payload
}

export default function BarcodeScanner() {
  const [permission, requestPermission] = useCameraPermissions();
  const [scanning, setScanning] = useState(true); // camera accepting reads
  const [confirming, setConfirming] = useState(false); // showing "confirming" UI
  const [loading, setLoading] = useState(false); // backend call in flight
  const router = useRouter();
  const isFocused = useIsFocused();

  // rolling buffer to tally codes within a short window
  const bufferRef = useRef<{
    counts: Record<string, number>; // keyed by normalized GTIN
    firstTs: number;
  }>({ counts: {}, firstTs: 0 });

  // cooldown timer after a confirmed scan
  const cooldownRef = useRef<number>(0);

  useEffect(() => {
    requestPermission();
  }, [requestPermission]);

  if (!permission) {
    return <Text className="p-4 text-center">Loading permissions…</Text>;
  }
  if (!permission.granted) {
    return <Text className="p-4 text-center">No camera access 🙁</Text>;
  }

  const resetBuffer = () => {
    bufferRef.current = { counts: {}, firstTs: 0 };
    setConfirming(false);
  };

  const maybeConfirm = (raw: string) => {
    const gtin = normalizeToGtin(raw);
    if (!gtin) {
      return null;
    } // ignore unsupported/invalid payloads

    const now = Date.now();
    const buf = bufferRef.current;

    // roll the time window
    if (!buf.firstTs || now - buf.firstTs > SCAN_WINDOW_MS) {
      buf.firstTs = now;
      buf.counts = {};
    }

    buf.counts[gtin] = (buf.counts[gtin] || 0) + 1;
    if (buf.counts[gtin] >= SCAN_CONFIRMATIONS) {
      resetBuffer();
      return gtin;
    }

    setConfirming(true);
    return null;
  };

  const handleBarcodeScanned = ({ data }: BarcodeScanningResult) => {
    if (!scanning || loading) {
      return;
    }

    // simple cooldown (prevents rapid-fire duplicate confirmations)
    if (Date.now() - cooldownRef.current < RESCAN_COOLDOWN_MS) {
      return;
    }

    const confirmed = maybeConfirm(data);
    if (!confirmed) {
      return;
    }

    // we have a confirmed + normalized GTIN
    setScanning(false);
    setConfirming(false);
    setLoading(true);
    Vibration.vibrate(80);

    // Get current user ID if available
    supabase.auth.getSession().then(({ data: { session } }) => {
      const userId = session?.user?.id;
      let responseData: any = null;

      const requestStart = Date.now();
      mobileLogger.info('BARCODE_SCAN', `Starting scan request for barcode: ${confirmed}`, {
        barcode: confirmed,
        userId,
      });

      fetch(`${BACKEND_API_URL}/scan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: confirmed, userId }),
      })
        .then(res => res.json())
        .then(json => {
          const requestTime = Date.now() - requestStart;
          mobileLogger.info('BARCODE_SCAN', `Backend response received`, {
            barcode: confirmed,
            requestTime,
            alreadyInWatchlist: json.alreadyInWatchlist,
            existingInDatabase: json.existingInDatabase,
          });

          responseData = json;
          // Check if item is already in watchlist
          if (json.alreadyInWatchlist) {
            setLoading(false);
            setScanning(true);
            cooldownRef.current = Date.now();

            // Show alert to user with navigation to register
            Alert.alert(
              'Item Already in Register',
              json.message || `This item is already in your chemical register list.`,
              [
                {
                  text: 'View Register',
                  onPress: () => {
                    // Navigate to chemical register list
                    router.replace('/register');
                  },
                },
                {
                  text: 'Scan Another',
                  onPress: () => {
                    // Reset scanner to allow scanning another item
                    resetBuffer();
                  },
                  style: 'cancel',
                },
              ]
            );
            return;
          }

          // Check if item was found in database (no scraping needed)
          const prod = json.product ?? json;

          if (json.existingInDatabase) {
            // Product exists in database - skip OCR and go straight to confirmation
            // This adds it to the user's watchlist without re-scraping

            // Quick double vibration to indicate product was found in database
            Vibration.vibrate([0, 50, 50, 50]);

            // Go directly to confirm screen with pre-filled data
            router.replace({
              pathname: '/confirm',
              params: {
                code: confirmed,
                name: prod.name || '',
                size: prod.contents_size_weight || '',
              },
            });
          } else {
            // New product - go directly to confirm screen with scraped data
            router.replace({
              pathname: '/confirm',
              params: {
                code: confirmed,
                name: prod.product_name || prod.name || '',
                size: prod.contents_size_weight || prod.size || '',
              },
            });
          }
        })
        .catch(err => {
          const requestTime = Date.now() - requestStart;
          mobileLogger.error('BARCODE_SCAN', 'Backend request failed', {
            barcode: confirmed,
            requestTime,
            error: err.message,
          });
          console.error('❌ Backend error:', err);
          router.replace({ pathname: '/confirm', params: { code: confirmed } });
        })
        .finally(() => {
          if (!responseData?.alreadyInWatchlist) {
            setLoading(false);
            cooldownRef.current = Date.now();
          }
        });
    });
  };

  return (
    <SafeAreaView className="flex-1 bg-black">
      {loading ? (
        <View className="flex-1 items-center justify-center bg-black">
          <Image source={require('@/assets/images/splash-icon.png')} className="mb-4 h-32 w-32" />
          <ActivityIndicator size="large" color="#fff" />
          <Text className="mt-2 text-white">Searching...</Text>
        </View>
      ) : (
        <>
          <View className="flex-1">
            {isFocused && (
              <CameraView
                style={StyleSheet.absoluteFill}
                onBarcodeScanned={scanning ? handleBarcodeScanned : undefined}
                barcodeScannerSettings={{
                  barcodeTypes: [
                    'ean8',
                    'ean13',
                    'upc_a',
                    'upc_e',
                    'itf14',
                    'code128',
                    'code39',
                    'code93',
                  ],
                }}
              />
            )}
          </View>

          {/* Overlay aim box */}
          <View className="pointer-events-none absolute inset-0 items-center justify-center">
            <View className="h-48 w-[70%] items-center justify-center rounded-xl border-4 border-white bg-white/10">
              <Text className="px-4 text-center text-base font-bold text-white">
                Align barcode here (EAN/UPC/ITF/Code128/39)
              </Text>
            </View>
          </View>

          {/* Confirming hint */}
          {confirming && !loading && (
            <View className="absolute bottom-24 self-center rounded-lg bg-black/70 px-4 py-2">
              <Text className="text-white">Hold steady… confirming barcode</Text>
            </View>
          )}

          {/* Scan Again button (after a read) */}
          {!scanning && !loading && (
            <Pressable
              className="absolute bottom-10 self-center rounded-lg bg-primary px-6 py-3"
              onPress={() => {
                resetBuffer();
                setScanning(true);
              }}
            >
              <Text className="text-base font-bold text-white">Scan Again</Text>
            </Pressable>
          )}
        </>
      )}
    </SafeAreaView>
  );
}
