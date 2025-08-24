// app/login.tsx
import { supabase } from '@/lib/supabase';
import { useRouter } from 'expo-router';
import { useState, useEffect, useRef } from 'react';
import {
  Alert,
  Pressable,
  Text,
  TextInput,
  View,
  ScrollView,
  StatusBar,
  Animated,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import './global.css';

export default function LoginScreen() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(30)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 1000,
        useNativeDriver: true,
      }),
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 1000,
        useNativeDriver: true,
      }),
    ]).start();
  }, [fadeAnim, slideAnim]);

  const handleAuth = async () => {
    const isValidEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    if (!isValidEmail) {
      Alert.alert('Invalid Email', 'Please enter a valid email address.');
      return;
    }

    if (password.length < 6) {
      Alert.alert('Password too short', 'Password must be at least 6 characters long.');
      return;
    }

    setIsLoading(true);

    const { data, error } = isRegistering
      ? await supabase.auth.signUp({ email, password })
      : await supabase.auth.signInWithPassword({ email, password });

    console.log(isRegistering ? '📝 Register result:' : '📥 Login result:', { data, error });

    setIsLoading(false);

    if (error) {
      Alert.alert(isRegistering ? 'Registration failed' : 'Login failed', error.message);
      return;
    }

    if (isRegistering && data.user && !data.session) {
      Alert.alert('Registration successful', 'Please check your email to verify your account.');
      return;
    }

    router.replace('/');
  };

  return (
    <SafeAreaView className="flex-1 bg-bg-secondary">
      <StatusBar barStyle="dark-content" backgroundColor="#f8fafc" />
      <ScrollView contentContainerStyle={{ flexGrow: 1 }}>
        <Animated.View
          className="flex-1 justify-center px-6 py-12"
          style={{
            opacity: fadeAnim,
            transform: [{ translateY: slideAnim }],
          }}
        >
          {/* Header */}
          <View className="mb-12 items-center">
            <View className="mb-6 h-20 w-20 items-center justify-center rounded-2xl bg-primary shadow-lg">
              <Text className="text-4xl">🧪</Text>
            </View>
            <Text className="mb-2 text-3xl font-bold text-text-primary">ChemFetch</Text>
            <Text className="mb-2 text-center text-lg text-text-secondary">
              {isRegistering ? 'Create Your Account' : 'Welcome Back'}
            </Text>
            <View className="h-1 w-16 rounded-full bg-primary" />
          </View>

          {/* Form */}
          <View className="rounded-2xl border border-border-color bg-white p-6 shadow-sm">
            <Text className="mb-6 text-center text-xl font-semibold text-text-primary">
              {isRegistering ? 'Sign up to get started' : 'Sign in to continue'}
            </Text>

            <View className="space-y-4">
              <View>
                <Text className="mb-2 text-sm font-medium text-text-secondary">Email Address</Text>
                <TextInput
                  placeholder="Enter your email"
                  value={email}
                  onChangeText={setEmail}
                  autoCapitalize="none"
                  autoCorrect={false}
                  keyboardType="email-address"
                  className="rounded-xl border border-border-color bg-bg-secondary px-4 py-4 text-base text-text-primary"
                  placeholderTextColor="#9ca3af"
                />
              </View>

              <View>
                <Text className="mb-2 text-sm font-medium text-text-secondary">Password</Text>
                <TextInput
                  placeholder={
                    isRegistering ? 'Create a password (min. 6 characters)' : 'Enter your password'
                  }
                  value={password}
                  onChangeText={setPassword}
                  secureTextEntry
                  autoCapitalize="none"
                  autoCorrect={false}
                  className="rounded-xl border border-border-color bg-bg-secondary px-4 py-4 text-base text-text-primary"
                  placeholderTextColor="#9ca3af"
                />
              </View>
            </View>

            {/* Submit Button */}
            <Pressable
              className={`mt-8 rounded-xl py-4 shadow-lg active:scale-95 ${
                isLoading || !email || !password ? 'bg-gray-300' : 'bg-primary'
              }`}
              onPress={handleAuth}
              disabled={isLoading || !email || !password}
            >
              <Text className="text-center text-base font-semibold text-white">
                {isLoading
                  ? isRegistering
                    ? 'Creating Account...'
                    : 'Signing In...'
                  : isRegistering
                    ? 'Create Account'
                    : 'Sign In'}
              </Text>
            </Pressable>

            {/* Toggle Auth Mode */}
            <Pressable
              onPress={() => setIsRegistering(!isRegistering)}
              className="mt-6 py-2 active:scale-95"
            >
              <Text className="text-center font-medium text-primary">
                {isRegistering
                  ? 'Already have an account? Sign In'
                  : "Don't have an account? Sign Up"}
              </Text>
            </Pressable>
          </View>

          {/* Footer */}
          <View className="mt-8 items-center">
            <Text className="text-center text-sm text-text-secondary">
              Professional Chemical Safety Management
            </Text>
            <View className="mt-4 flex-row">
              <View className="mx-6 items-center">
                <Text className="text-lg font-bold text-primary">~2-5s</Text>
                <Text className="text-xs text-text-secondary">Scan Time</Text>
              </View>
              <View className="mx-6 items-center">
                <Text className="text-lg font-bold text-primary">95%+</Text>
                <Text className="text-xs text-text-secondary">OCR Accuracy</Text>
              </View>
              <View className="mx-6 items-center">
                <Text className="text-lg font-bold text-primary">24/7</Text>
                <Text className="text-xs text-text-secondary">Available</Text>
              </View>
            </View>
          </View>
        </Animated.View>
      </ScrollView>
    </SafeAreaView>
  );
}
