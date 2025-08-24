import { SizePromptModal } from '@/components/SizePromptModal';
import { BACKEND_API_URL } from '@/lib/constants';
import { supabase } from '@/lib/supabase';
import { useLocalSearchParams, useRouter } from 'expo-router';
import React, { useState } from 'react';
import { ActivityIndicator, Alert, Pressable, Text, TextInput, View } from 'react-native';

export default function Confirm() {
  // ─────────────────────── navigation & params ───────────────────────
  const router = useRouter();

  const {
    name: nameParam = '',
    size: sizeParam = '',
    code = '',
  } = useLocalSearchParams<{
    name: string;
    size: string;
    code: string;
  }>();

  // ─────────────────────────── UI state ──────────────────────────────

  // preview values coming from Web (scan/API) and params
  const [webName] = useState(nameParam);
  const [webSize] = useState(sizeParam);

  // manual inputs (used by Manual panel)
  const [manualName, setManualName] = useState(nameParam);
  const [manualSize, setManualSize] = useState(sizeParam);

  // current selection in the 2‑way choice (removed OCR)
  const [choice, setChoice] = useState<'web' | 'manual'>(webName ? 'web' : 'manual');

  // prompt when size missing
  const [sizePromptVisible, setSizePromptVisible] = useState(false);
  const [pendingName, setPendingName] = useState('');
  const [pendingSize, setPendingSize] = useState('');

  // saving feedback
  const [saving, setSaving] = useState(false);

  // ─────────────────────────── helpers ───────────────────────────────
  // Persist product (upsert) and add to user's watch list if possible
  const persistProduct = async (finalName: string, finalSize: string) => {
    try {
      await fetch(`${BACKEND_API_URL}/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, name: finalName, size: finalSize }),
      });

      const { data: sessionData } = await supabase.auth.getSession();
      const userId = sessionData.session?.user.id;
      const { data: product } = await supabase
        .from('product')
        .select('id')
        .eq('barcode', code)
        .single();

      if (userId && product?.id) {
        // Check if item already exists in watchlist before adding
        const { data: existingItem } = await supabase
          .from('user_chemical_watch_list')
          .select('id')
          .eq('user_id', userId)
          .eq('product_id', product.id)
          .maybeSingle();

        if (!existingItem) {
          const { error: wlError } = await supabase
            .from('user_chemical_watch_list')
            .insert({ user_id: userId, product_id: product.id });
          if (wlError) {
            console.warn('watch_list insert skipped:', wlError.message);
          }
        } else {
          console.info('Product already in watchlist, skipping insert');
        }
      }
    } catch (e) {
      console.error('❌ Persist error', e);
    }
  };

  // SDS: search → verify → upsert product.sds_url via Supabase client
  const searchVerifyAndUpsertSds = async (finalName: string) => {
    try {
      const sdsRes = await fetch(`${BACKEND_API_URL}/sds-by-name`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: finalName }),
      });
      const sds = await sdsRes.json();
      const url: string | undefined = sds.sdsUrl || sds.url;
      if (!url) {
        return;
      }

      // verify before persisting
      const verRes = await fetch(`${BACKEND_API_URL}/verify-sds`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, name: finalName }),
      });
      const ver = await verRes.json();
      if (ver?.verified !== false) {
        const { data: product } = await supabase
          .from('product')
          .select('id')
          .eq('barcode', code)
          .single();
        if (product?.id) {
          await supabase.from('product').update({ sds_url: url }).eq('id', product.id);
        }
      }
    } catch (e) {
      console.error('SDS lookup/verify failed', e);
    }
  };

  const onSubmitChoice = async () => {
    let finalName = '';
    let finalSize = '';

    if (choice === 'web') {
      finalName = webName.trim();
      finalSize = webSize.trim();
    } else {
      finalName = manualName.trim();
      finalSize = manualSize.trim();
    }

    if (!finalName) {
      Alert.alert('Missing name', 'Please provide a product name.');
      return;
    }

    // if size missing, prompt first
    if (!finalSize) {
      setPendingName(finalName);
      setPendingSize('');
      setSizePromptVisible(true);
      return;
    }

    try {
      setSaving(true);
      await persistProduct(finalName, finalSize);
      searchVerifyAndUpsertSds(finalName).catch(e => console.error('SDS lookup failed', e));
      router.replace('/register');
    } finally {
      setSaving(false);
    }
  };

  const confirmSizeFromPrompt = async () => {
    const n = pendingName;
    const s = pendingSize.trim();
    setSizePromptVisible(false);
    if (!s) {
      return;
    }
    try {
      setSaving(true);
      await persistProduct(n, s);
      searchVerifyAndUpsertSds(n).catch(e => console.error('SDS lookup failed', e));
      router.replace('/register');
    } finally {
      setSaving(false);
    }
  };

  // ─────────────────────────── render ───────────────────────────────
  return (
    <View className="flex-1 bg-white p-6">
      <Text className="mb-4 text-center text-lg font-semibold">Confirm product details</Text>

      <View className="flex-col space-y-4">
        {/* Web panel */}
        <Pressable
          onPress={() => setChoice('web')}
          className={`rounded-xl border p-4 ${choice === 'web' ? 'border-primary bg-blue-50' : 'border-gray-300 bg-light-100'}`}
        >
          <Text className="mb-1 font-bold">🌐 Web (Item {code || '—'})</Text>
          <Text className="text-dark-100">Name: {webName || '—'}</Text>
          <Text className="text-dark-100">Size: {webSize || '—'}</Text>
          {!webName && (
            <Text className="mt-1 text-xs text-gray-500">
              No web result provided. You can use Manual entry below.
            </Text>
          )}
        </Pressable>

        {/* Manual panel */}
        <Pressable
          onPress={() => setChoice('manual')}
          className={`rounded-xl border p-4 ${choice === 'manual' ? 'border-primary bg-blue-50' : 'border-gray-300 bg-light-100'}`}
        >
          <Text className="mb-2 font-bold">✍️ Manual</Text>
          <View className="space-y-2">
            <TextInput
              className="rounded-md border border-gray-300 bg-white px-3 py-2 text-dark-100"
              placeholder="Product name"
              value={manualName}
              onChangeText={setManualName}
              editable={choice === 'manual'}
            />
            <TextInput
              className="rounded-md border border-gray-300 bg-white px-3 py-2 text-dark-100"
              placeholder="Size/weight"
              value={manualSize}
              onChangeText={setManualSize}
              editable={choice === 'manual'}
            />
          </View>
        </Pressable>
      </View>

      {/* Actions */}
      <View className="mt-6 space-y-3">
        <Pressable className="rounded-lg bg-primary px-4 py-3" onPress={onSubmitChoice}>
          <Text className="text-center font-bold text-white">Save & Find SDS</Text>
        </Pressable>

        <Pressable className="rounded-lg bg-gray-300 px-4 py-3" onPress={() => router.replace('/')}>
          <Text className="text-center font-semibold text-dark-100">Cancel</Text>
        </Pressable>
      </View>

      <SizePromptModal
        visible={sizePromptVisible}
        name={pendingName}
        size={pendingSize}
        onChangeSize={setPendingSize}
        onSave={confirmSizeFromPrompt}
        onCancel={() => setSizePromptVisible(false)}
      />

      {saving && (
        <View className="absolute inset-0 items-center justify-center bg-black/40">
          <ActivityIndicator size="large" color="#fff" />
          <Text className="mt-2 text-white">Saving...</Text>
        </View>
      )}
    </View>
  );
}
