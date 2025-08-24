// This screen is no longer needed since OCR functionality has been removed
// Users will go directly from barcode scanning to the confirm screen

import { useRouter } from 'expo-router';
import { useEffect } from 'react';

export default function OcrInfoScreen() {
  const router = useRouter();

  // Redirect to confirm screen immediately
  useEffect(() => {
    router.replace('/confirm');
  }, [router]);

  return null;
}
