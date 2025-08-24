// app/_layout.tsx
import { BottomBar } from '@/components/BottomBar';
import { supabase } from '@/lib/supabase';
import { Stack, useRouter } from 'expo-router';
import { useEffect } from 'react';
import { View, StatusBar } from 'react-native';
import './global.css';

export default function RootLayout() {
  const router = useRouter();

  useEffect(() => {
    const checkAuth = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        router.replace('/login');
      }
    };

    checkAuth();
  }, [router]);

  return (
    <View className="flex-1 bg-bg-secondary">
      <StatusBar barStyle="dark-content" backgroundColor="#f8fafc" />
      <Stack
        screenOptions={{
          headerShown: false,
        }}
      />
      <BottomBar />
    </View>
  );
}
