// app/register.tsx
import { supabase } from '@/lib/supabase';
import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Alert, FlatList, Pressable, Text, View } from 'react-native';

interface WatchItem {
  id: string;
  product: {
    name: string;
    contents_size_weight: string;
    sds_url: string | null;
  };
  sds_issue_date: string | null;
}

export default function WatchListScreen() {
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<WatchItem[]>([]);
  const router = useRouter();

  useEffect(() => {
    const fetchWatchList = async () => {
      setLoading(true);

      const {
        data: { session },
        error: sessionError,
      } = await supabase.auth.getSession();

      if (sessionError || !session?.user) {
        Alert.alert('Error', 'You must be logged in to view this page.');
        router.replace('/login');
        return;
      }

      const { data, error } = await supabase
        .from('user_chemical_watch_list')
        .select(
          `
    id,
    sds_issue_date,
    product (
      name,
      contents_size_weight,
      sds_url
    )
  `
        )
        .eq('user_id', session.user.id)
        .order('sds_issue_date', { ascending: false });

      if (error) {
        Alert.alert('Error', error.message);
      } else {
        // Ensure TS type matches
        setItems(data as unknown as WatchItem[]);
      }

      setLoading(false);
    };

    fetchWatchList();
  }, [router]);

  const openSds = (url: string | null) => {
    if (!url) {
      Alert.alert('No SDS Found', 'This product has no SDS URL recorded.');
    } else {
      router.push(`/sds-viewer?url=${encodeURIComponent(url)}`);
    }
  };

  if (loading) {
    return (
      <View className="flex-1 items-center justify-center bg-white">
        <ActivityIndicator size="large" color="#3A3D98" />
      </View>
    );
  }

  return (
    <View className="flex-1 bg-white p-4">
      <Text className="mb-4 text-center text-xl font-bold text-dark-100">
        📋 My Chemical Register
      </Text>
      {items.length === 0 ? (
        <Text className="text-center text-dark-100">Your watch list is empty.</Text>
      ) : (
        <FlatList
          data={items}
          keyExtractor={item => item.id}
          renderItem={({ item }) => (
            <View className="mb-4 rounded-xl border border-gray-200 bg-light-100 p-4">
              <Text className="text-lg font-bold text-dark-100">{item.product.name}</Text>
              <Text className="text-dark-100">
                Size: {item.product.contents_size_weight || 'N/A'}
              </Text>
              <Text className="text-dark-100">
                SDS Available: {item.product.sds_url ? '✅' : '❌'}
              </Text>

              <Pressable
                onPress={() => openSds(item.product.sds_url)}
                className="mt-3 rounded-lg bg-primary px-4 py-2"
              >
                <Text className="text-center font-semibold text-white">🔎 View SDS</Text>
              </Pressable>
            </View>
          )}
        />
      )}
    </View>
  );
}
