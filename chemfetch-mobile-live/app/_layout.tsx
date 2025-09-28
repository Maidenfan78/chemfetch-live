// app/_layout.tsx
import { BottomBar } from '@/components/BottomBar';
import { supabase } from '@/lib/supabase';
import { Slot, usePathname, useRouter } from 'expo-router';
import { useEffect } from 'react';
import { LogBox, StatusBar, View } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import './global.css';

export default function RootLayout() {
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    LogBox.ignoreLogs(['SafeAreaView has been deprecated']);
    const checkAuth = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session && pathname !== '/login') {
        router.replace('/login');
      }
    };

    checkAuth();
  }, [router, pathname]);

  return (
    <GestureHandlerRootView style={{ flex: 1 }} className="bg-bg-secondary">
      <StatusBar barStyle="dark-content" backgroundColor="#f8fafc" />
      <View style={{ flex: 1 }}>
        <Slot />
      </View>
      {pathname !== '/login' && <BottomBar />}
    </GestureHandlerRootView>
  );
}
