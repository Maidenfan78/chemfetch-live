// components/BottomBar.tsx
import { supabase } from '../lib/supabase';
import { useRouter, usePathname } from 'expo-router';
import React from 'react';
import { Pressable, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export const BottomBar = () => {
  const router = useRouter();
  const pathname = usePathname();

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.replace('/login');
  };

  const TabButton = ({
    onPress,
    icon,
    label,
    isActive = false,
  }: {
    onPress: () => void;
    icon: string;
    label: string;
    isActive?: boolean;
  }) => (
    <Pressable
      onPress={onPress}
      className={`mx-1 flex-1 items-center rounded-xl px-2 py-3 active:scale-95 ${
        isActive ? 'bg-primary' : 'bg-transparent'
      }`}
    >
      <Text className="mb-1 text-lg">{icon}</Text>
      <Text className={`text-xs font-medium ${isActive ? 'text-white' : 'text-text-secondary'}`}>
        {label}
      </Text>
    </Pressable>
  );

  return (
    <SafeAreaView edges={['bottom']} className="bg-bg-primary">
      <View className="flex-row justify-around border-t border-border-color bg-bg-primary px-4 py-2">
        <TabButton
          onPress={() => router.replace('/')}
          icon="🏠"
          label="Home"
          isActive={pathname === '/'}
        />
        <TabButton
          onPress={() => router.replace('/barcode')}
          icon="📷"
          label="Scan"
          isActive={pathname === '/barcode'}
        />
        <TabButton
          onPress={() => router.replace('/register')}
          icon="📋"
          label="Register"
          isActive={pathname === '/register'}
        />
        <TabButton
          onPress={() => router.replace('/help')}
          icon="❓"
          label="Help"
          isActive={pathname === '/help'}
        />
        <TabButton onPress={handleLogout} icon="🚪" label="Sign Out" />
      </View>
    </SafeAreaView>
  );
};
