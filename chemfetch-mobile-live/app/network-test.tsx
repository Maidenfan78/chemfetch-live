import { NetworkUtil } from '../lib/network';
import { BACKEND_API_URL } from '../lib/constants';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, Alert, Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export default function NetworkTest() {
  const [testing, setTesting] = useState(false);
  const [results, setResults] = useState<string[]>([]);
  const router = useRouter();

  const addResult = (message: string) => {
    setResults(prev => [...prev, `${new Date().toLocaleTimeString()}: ${message}`]);
  };

  const runTests = async () => {
    setTesting(true);
    setResults([]);

    addResult(`Testing backend connection...`);
    addResult(`Backend URL: ${BACKEND_API_URL}`);

    try {
      // Test 1: Basic connectivity
      const healthTest = await NetworkUtil.testBackendConnection();
      if (healthTest.error) {
        addResult(`❌ Health check failed: ${healthTest.error}`);
      } else {
        addResult(`✅ Health check passed: ${JSON.stringify(healthTest.data)}`);
      }

      // Test 2: Scan endpoint
      addResult(`Testing scan endpoint...`);
      const scanTest = await NetworkUtil.scanBarcode('1234567890123');
      if (scanTest.error) {
        addResult(`❌ Scan test failed: ${scanTest.error}`);
      } else {
        addResult(`✅ Scan test passed: Status ${scanTest.status}`);
      }
    } catch (error: any) {
      addResult(`❌ Test suite failed: ${error.message}`);
    }

    setTesting(false);
  };

  const clearResults = () => {
    setResults([]);
  };

  const showSummary = () => {
    const successCount = results.filter(r => r.includes('✅')).length;
    const failCount = results.filter(r => r.includes('❌')).length;

    Alert.alert(
      'Test Summary',
      `Passed: ${successCount}\nFailed: ${failCount}\n\nCheck console logs for detailed output.`,
      [{ text: 'OK' }]
    );
  };

  return (
    <SafeAreaView className="flex-1 bg-white">
      <View className="flex-1 p-4">
        <Text className="mb-4 text-2xl font-bold">Network Diagnostics</Text>

        <Text className="mb-2 text-base">Backend URL:</Text>
        <Text className="mb-4 rounded bg-gray-100 p-2 text-sm text-gray-600">
          {BACKEND_API_URL}
        </Text>

        <View className="mb-4 flex-row gap-2">
          <Pressable
            className={`flex-1 rounded px-4 py-3 ${testing ? 'bg-gray-400' : 'bg-blue-500'}`}
            onPress={runTests}
            disabled={testing}
          >
            <Text className="text-center font-semibold text-white">
              {testing ? 'Testing...' : 'Run Tests'}
            </Text>
          </Pressable>

          <Pressable className="rounded bg-gray-500 px-4 py-3" onPress={clearResults}>
            <Text className="text-center font-semibold text-white">Clear</Text>
          </Pressable>
        </View>

        {results.length > 0 && (
          <View className="mb-4 flex-row gap-2">
            <Pressable className="rounded bg-green-500 px-4 py-2" onPress={showSummary}>
              <Text className="text-center text-sm text-white">Summary</Text>
            </Pressable>
          </View>
        )}

        <ScrollView className="flex-1 rounded bg-gray-50 p-3">
          {testing && (
            <View className="items-center py-4">
              <ActivityIndicator size="large" color="#3B82F6" />
            </View>
          )}

          {results.map((result, index) => (
            <Text key={index} className="mb-1 font-mono text-sm">
              {result}
            </Text>
          ))}

          {results.length === 0 && !testing && (
            <Text className="py-8 text-center text-gray-500">
              Tap &quot;Run Tests&quot; to start network diagnostics
            </Text>
          )}
        </ScrollView>

        <Pressable className="mt-4 rounded bg-gray-600 py-3" onPress={() => router.back()}>
          <Text className="text-center font-semibold text-white">Back</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}
