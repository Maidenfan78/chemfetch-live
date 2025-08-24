import { BACKEND_API_URL } from '../lib/constants';
import { supabase } from '../lib/supabase';
import { useRouter } from 'expo-router';
import React, { useState } from 'react';
import { ActivityIndicator, Alert, Pressable, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

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
  let sum = 0;
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
  for (let i = 0; i < 11; i++) {
    sum += d[i] * (i % 2 === 0 ? 3 : 1);
  }
  const check = (10 - (sum % 10)) % 10;
  return check === d[11];
}

function expandUPCEtoUPCA(upce: string): string | null {
  if (!/^\d{8}$/.test(upce)) {
    return null;
  }
  const d = upce.split('').map(Number);
  const numberSystem = d[0];
  const checkDigit = d[7];
  if (numberSystem !== 0 && numberSystem !== 1) {
    return null;
  }
  let upcaBody = '';
  switch (d[6]) {
    case 0:
    case 1:
    case 2:
      upcaBody = `${numberSystem}${d[1]}${d[2]}${d[6]}0000${d[3]}${d[4]}${d[5]}`;
      break;
    case 3:
      upcaBody = `${numberSystem}${d[1]}${d[2]}${d[3]}00000${d[4]}`;
      break;
    case 4:
      upcaBody = `${numberSystem}${d[1]}${d[2]}${d[3]}${d[4]}00000${d[5]}`;
      break;
    default:
      upcaBody = `${numberSystem}${d[1]}${d[2]}${d[3]}${d[4]}${d[5]}0000${d[6]}`;
  }
  const digits = upcaBody.split('').map(Number);
  let sum = 0;
  for (let i = 0; i < 11; i++) {
    sum += digits[i] * (i % 2 === 0 ? 3 : 1);
  }
  const check = (10 - (sum % 10)) % 10;
  if (check !== checkDigit) {
    return null;
  }
  return `${upcaBody}${check}`;
}

function isValidUPCE(code: string): boolean {
  const upca = expandUPCEtoUPCA(code);
  return !!upca;
}

function isValidITF14(code: string): boolean {
  if (!/^\d{14}$/.test(code)) {
    return false;
  }
  const d = code.split('').map(Number);
  let sum = 0;
  for (let i = 0; i < 13; i++) {
    sum += d[i] * (i % 2 ? 3 : 1);
  }
  const check = (10 - (sum % 10)) % 10;
  return check === d[13];
}

function normalizeToGtin(raw: string): string | null {
  const data = (raw || '').trim();
  if (!data) {
    return null;
  }
  if (/^\d+$/.test(data)) {
    if (data.length === 8 && isValidEAN8(data)) {
      return data;
    }
    if (data.length === 12 && isValidUPCA(data)) {
      return `0${data}`;
    }
    if (data.length === 13 && isValidEAN13(data)) {
      return data;
    }
    if (data.length === 14 && isValidITF14(data)) {
      return data;
    }
  }
  if (/^\d{8}$/.test(data) && isValidUPCE(data)) {
    const upca = expandUPCEtoUPCA(data)!;
    return `0${upca}`.slice(0, 13);
  }
  const digits = data.replace(/\D+/g, '');
  if (digits) {
    const n = normalizeToGtin(digits);
    if (n) {
      return n;
    }
  }
  return null;
}

export default function ManualEntry() {
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [size, setSize] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async () => {
    const normalized = normalizeToGtin(code);
    if (!normalized) {
      Alert.alert('Invalid barcode', 'Please enter a valid barcode.');
      return;
    }
    if (!name.trim() || !size.trim()) {
      Alert.alert('Missing information', 'Please enter both item name and size.');
      return;
    }
    setLoading(true);
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const userId = session?.user?.id;
      const res = await fetch(`${BACKEND_API_URL}/manual-scan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: normalized, name, size, userId }),
      });
      const json = await res.json();
      if (json.alreadyInWatchlist) {
        Alert.alert(
          'Item Already in Register',
          json.message || `This item is already in your chemical register list.`,
          [
            {
              text: 'View Register',
              onPress: () => router.replace('/register'),
            },
            { text: 'Enter Another', style: 'cancel' },
          ]
        );
        return;
      }
      const prod = json.product ?? json;
      const prodName = prod.product_name || prod.name || name;
      const prodSize = prod.contents_size_weight || prod.size || size;

      // For manual entries, always go to confirm screen since we have all the data
      if (json.existingInDatabase || json.isManualEntry) {
        router.replace({
          pathname: '/confirm',
          params: {
            code: normalized,
            name: prodName,
            size: prodSize,
            editOnly: json.existingInDatabase ? '1' : '0',
          },
        });
      } else {
        // This shouldn't happen for manual entries, but fallback to OCR
        router.replace({
          pathname: '/ocr-info',
          params: {
            code: normalized,
            name: prodName,
            size: prodSize,
          },
        });
      }
    } catch (err) {
      console.error('❌ Backend error:', err);
      // For manual entries, go directly to confirm with the entered data
      router.replace({
        pathname: '/confirm',
        params: {
          code: normalizeToGtin(code) || '',
          name,
          size,
          editOnly: '0',
        },
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-bg-secondary p-6">
      {loading ? (
        <View className="flex-1 items-center justify-center">
          <ActivityIndicator />
          <Text className="mt-2">Searching...</Text>
        </View>
      ) : (
        <View className="gap-4">
          <Text className="text-lg font-semibold text-text-primary">Item Name</Text>
          <TextInput
            className="rounded-xl border border-gray-300 bg-white p-4"
            placeholder="Item name"
            value={name}
            onChangeText={setName}
          />
          <Text className="text-lg font-semibold text-text-primary">Size</Text>
          <TextInput
            className="rounded-xl border border-gray-300 bg-white p-4"
            placeholder="Size (e.g. 500 mL)"
            value={size}
            onChangeText={setSize}
          />
          <Text className="text-lg font-semibold text-text-primary">Enter Barcode</Text>
          <TextInput
            className="rounded-xl border border-gray-300 bg-white p-4"
            placeholder="Barcode number"
            keyboardType="numeric"
            value={code}
            onChangeText={setCode}
          />
          <Pressable onPress={handleSubmit} className="rounded-xl bg-primary p-4">
            <Text className="text-center text-white">Search</Text>
          </Pressable>
        </View>
      )}
    </SafeAreaView>
  );
}
