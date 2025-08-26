import { supabase } from '../lib/supabase';
import { useRouter } from 'expo-router';
import { Pressable, Text, View, ScrollView, StatusBar, Animated } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useEffect, useRef } from 'react';
import './global.css';

export default function HomeScreen() {
  const router = useRouter();
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(50)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 800,
        useNativeDriver: true,
      }),
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 800,
        useNativeDriver: true,
      }),
    ]).start();
  }, [fadeAnim, slideAnim]);

  const ActionButton = ({
    onPress,
    children,
    style,
    textColor = 'text-white',
  }: {
    onPress: () => void;
    children: React.ReactNode;
    style: string;
    textColor?: string;
  }) => (
    <Pressable
      className={`mb-4 rounded-xl px-6 py-4 shadow-lg active:scale-95 ${style}`}
      onPress={onPress}
    >
      <Text className={`text-center text-base font-semibold ${textColor}`}>{children}</Text>
    </Pressable>
  );

  return (
    <SafeAreaView className="flex-1 bg-bg-secondary">
      <StatusBar barStyle="dark-content" backgroundColor="#f8fafc" />
      <ScrollView contentContainerStyle={{ flexGrow: 1 }}>
        <Animated.View
          className="flex-1 px-6 pt-8"
          style={{
            opacity: fadeAnim,
            transform: [{ translateY: slideAnim }],
          }}
        >
          {/* Header */}
          <View className="mb-8 items-center">
            <Text className="mb-2 text-5xl">🧪</Text>
            <Text className="mb-2 text-3xl font-bold text-text-primary">ChemFetch</Text>
            <Text className="mb-4 text-center text-lg text-text-secondary">
              Professional Chemical Safety Management
            </Text>
            <View className="h-1 w-20 rounded-full bg-primary" />
          </View>

          {/* Testing Phase Notice */}
          <View className="mb-4 rounded-2xl border border-orange-300 bg-orange-50 p-4 shadow-sm">
            <Text className="mb-1 text-center text-base font-semibold text-orange-800">
              ⚠️ Testing Phase
            </Text>
            <Text className="text-center text-sm leading-5 text-orange-700">
              This app is currently in development. Some features may be limited.
            </Text>
          </View>

          {/* Welcome Message */}
          <View className="mb-8 rounded-2xl border border-border-color bg-white p-6 shadow-sm">
            <Text className="mb-2 text-xl font-semibold text-text-primary">Welcome back!</Text>
            <Text className="text-base leading-6 text-text-secondary">
              Scan and manage your chemical products with barcode scanning, OCR recognition, and
              Safety Data Sheet verification.
            </Text>
          </View>

          {/* Action Buttons */}
          <View className="space-y-4">
            <ActionButton style="bg-primary" onPress={() => router.push('/barcode')}>
              📷 Scan Chemical Product
            </ActionButton>

            <ActionButton style="bg-secondary" onPress={() => router.push('/register')}>
              📋 Chemical Register
            </ActionButton>

            <ActionButton style="bg-accent" onPress={() => router.push('/manual')}>
              ✍️ Manual Entry
            </ActionButton>

            {/* Secondary Actions */}
            <View className="border-t border-border-color pt-4">
              <ActionButton
                style="bg-orange-500"
                onPress={() => router.push('/network-test')}
              >
                🔧 Network Diagnostics
              </ActionButton>

              <ActionButton
                style="bg-white border border-border-color"
                textColor="text-text-primary"
                onPress={async () => {
                  await supabase.auth.signOut();
                  router.replace('/login');
                }}
              >
                🚪 Sign Out
              </ActionButton>
            </View>
          </View>

          {/* Stats Section */}
          <View className="mt-8 rounded-2xl bg-primary p-6">
            <Text className="mb-4 text-center text-lg font-semibold text-white">
              Platform Features
            </Text>
            <View className="flex-row justify-around">
              <View className="items-center">
                <Text className="text-2xl font-bold text-white">~2-5s</Text>
                <Text className="text-sm text-blue-100">Scan Time</Text>
              </View>
              <View className="items-center">
                <Text className="text-2xl font-bold text-white">95%+</Text>
                <Text className="text-sm text-blue-100">OCR Accuracy</Text>
              </View>
              <View className="items-center">
                <Text className="text-2xl font-bold text-white">24/7</Text>
                <Text className="text-sm text-blue-100">Availability</Text>
              </View>
            </View>
          </View>
        </Animated.View>
      </ScrollView>
    </SafeAreaView>
  );
}
