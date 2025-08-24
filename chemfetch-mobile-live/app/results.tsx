import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Alert, Linking, Pressable, Share, Text, View } from 'react-native';
import { BACKEND_API_URL } from '../lib/constants';
import { useProductStore } from '../lib/store';

export default function ResultsScreen() {
  const { code } = useLocalSearchParams<{ code: string }>();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const setProduct = useProductStore(state => state.setProduct);
  const product = useProductStore(state => state);

  useEffect(() => {
    if (!code) {
      return;
    }

    fetch(`${BACKEND_API_URL}/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    })
      .then(res => res.json())
      .then(data => {
        if (data.message) {
          Alert.alert('Info', data.message);
        }

        const prod = data.product ?? data;

        setProduct({
          barcode: code,
          name: prod.product_name || prod.name || '',
          size: prod.contents_size_weight || prod.size || '',
          sdsUrl: prod.sds_url || prod.sdsUrl || '',
        });

        if (!prod.sds_url && (prod.product_name || prod.name)) {
          fetch(`${BACKEND_API_URL}/sds-by-name`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: prod.product_name || prod.name }),
          })
            .then(res => res.json())
            .then(sds => {
              if (sds.sdsUrl) {
                setProduct({ sdsUrl: sds.sdsUrl });
              }
            })
            .catch(err => console.error('SDS fetch error', err));
        }

        setLoading(false);
      })
      .catch(err => {
        console.error('Scan fetch error:', err);
        setLoading(false);
      });
  }, [code, setProduct]);

  const shareSds = async () => {
    if (!product.sdsUrl) {
      return;
    }
    try {
      await Share.share({
        title: `SDS for ${product.name}`,
        message: product.sdsUrl,
        url: product.sdsUrl,
      });
    } catch (err) {
      console.error('Share error:', err);
    }
  };

  const downloadSds = () => {
    if (!product.sdsUrl) {
      return;
    }
    Linking.openURL(product.sdsUrl);
  };

  if (loading) {
    return (
      <View className="flex-1 items-center justify-center bg-white">
        <ActivityIndicator size="large" color="#3A3D98" />
      </View>
    );
  }

  if (!product.name) {
    return (
      <View className="flex-1 items-center justify-center bg-white px-6">
        <Text className="text-center text-lg text-dark-100">No results found for {code}</Text>
      </View>
    );
  }

  return (
    <View className="flex-1 bg-white p-6">
      <View className="mb-6 rounded-xl border border-gray-200 bg-light-100 p-4">
        <Text className="mb-1 text-xl font-bold text-dark-100">
          {product.name || 'Unknown product'}
        </Text>
        <Text className="text-dark-100">Size: {product.size || 'N/A'}</Text>
        {product.sdsUrl ? (
          <View className="mt-3 space-y-2">
            <Text className="text-accent">SDS: {product.sdsUrl}</Text>
            <Pressable className="rounded-lg bg-primary px-4 py-2" onPress={shareSds}>
              <Text className="text-center font-semibold text-white">📤 Share SDS</Text>
            </Pressable>
            <Pressable className="rounded-lg bg-gray-700 px-4 py-2" onPress={downloadSds}>
              <Text className="text-center font-semibold text-white">⬇️ Open in Browser</Text>
            </Pressable>
          </View>
        ) : (
          <Text className="mt-2 text-dark-100">No SDS link found</Text>
        )}
      </View>

      <Pressable
        className="mb-4 rounded-lg bg-primary px-6 py-3"
        onPress={() =>
          router.push({
            pathname: './confirm',
            params: {
              code: code ?? '',
              name: product.name,
              size: product.size,
              editOnly: '1',
            },
          })
        }
      >
        <Text className="text-center text-base font-bold text-white">✍️ Edit / Confirm Info</Text>
      </Pressable>

      <Pressable className="rounded-lg bg-gray-300 px-6 py-3" onPress={() => router.replace('/')}>
        <Text className="text-center text-base font-semibold text-dark-100">🔙 Back to Home</Text>
      </Pressable>
    </View>
  );
}
