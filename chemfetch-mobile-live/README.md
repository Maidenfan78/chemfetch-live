# 📱 ChemFetch Mobile

**Expo + React Native** mobile app for barcode scanning, OCR, and chemical safety management. Part of the ChemFetch platform for field workers and safety personnel.

This mobile application enables on-site chemical identification, Safety Data Sheet verification, and inventory management through an intuitive touch interface optimized for industrial environments.

---

## ✨ Features

### Core Functionality

- **📸 Barcode Scanning**: EAN-8, EAN-13, UPC-A, UPC-E, ITF-14, Code128/39/93 formats
- **✨ GTIN Normalization**: Smart barcode format conversion and validation
- **📝 Manual Entry**: Direct product entry with barcode, name, and size
- **🔍 Duplicate Detection**: Prevents adding items already in user's register
- **📊 Auto-SDS Discovery**: Intelligent Safety Data Sheet search and verification
- **📱 Native Performance**: Optimized for industrial use with haptic feedback

### User Experience

- **🎯 Intuitive Interface**: Simple, touch-friendly design for field use
- **🌙 Dark Mode Support**: Optimized for various lighting conditions
- **⚡ Fast Performance**: Optimized for quick scanning workflows
- **🔒 Secure Authentication**: User login with role-based permissions
- **📱 Cross-Platform**: Native iOS and Android support via Expo

---

## 🛠️ Tech Stack

### Core Framework

- **React Native 0.79** with Expo 53 for cross-platform development
- **Expo Router 5** for file-based navigation
- **TypeScript** for type safety and better development experience

### UI & Styling

- **NativeWind 4** (Tailwind CSS for React Native)
- **Expo Vector Icons 14** for consistent iconography
- **React Native Reanimated 3** for smooth animations
- **React Native Gesture Handler 2** for touch interactions
- **React Native Safe Area Context 5** for proper screen layouts
- **React Native PDF 6** for PDF document viewing

### Device Integration

- **Expo Camera 16** for barcode scanning and photo capture
- **Expo File System 18** for local file management
- **Expo Haptics 14** for tactile feedback on scan confirmation
- **Expo Constants 17** for environment and configuration access
- **React Native Blob Util** for advanced file handling

### State & Data Management

- **Zustand 5** for lightweight state management
- **Supabase** for authentication and data sync
- **React Native Blob Util** for file handling

---

## ⚙️ Quick Start

### Prerequisites

- Node.js 18+ and npm
- Expo CLI: `npm install -g expo-cli`
- iOS Simulator (macOS) or Android Emulator
- Physical device with Expo Go app (recommended)

### 1. Environment Setup

Create `.env` file in project root:

```env
# Supabase Configuration
EXPO_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# Backend API
EXPO_PUBLIC_BACKEND_API_URL=http://your-backend-host:3001
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Start Development Server

```bash
npx expo start
```

**Options:**

- Scan QR code with Expo Go app (iOS/Android)
- Press `i` to open iOS Simulator
- Press `a` to open Android Emulator

### 4. Build for Production

```bash
# Install EAS CLI
npm install -g @expo/eas-cli

# Configure build (if not already done)
eas build:configure

# Build for specific platforms
eas build --platform android
eas build --platform ios
eas build --platform all

# Submit to app stores
eas submit --platform android
eas submit --platform ios
```

### Additional Scripts

```bash
# Development
npm run android          # Start with Android emulator
npm run ios             # Start with iOS simulator
npm run web             # Start web version

# Code Quality
npm run lint            # Run ESLint
npm run lint:fix        # Fix ESLint issues
npm run format          # Format with Prettier
npm run format:check    # Check formatting
npm run type-check      # TypeScript checking

# Building
npm run build:web       # Export web version
npm run build:android   # EAS Android build
npm run build:ios       # EAS iOS build
npm run build:all       # EAS build for both platforms

# Utility
npm run reset-project   # Reset project to clean state
```

---

## 🎯 Core Screens & Workflows

### Home Screen (`/`)

- **Quick Actions**: Direct access to barcode scanning, manual entry, and chemical register
- **Welcome Message**: User-friendly introduction to the platform
- **Platform Stats**: Real-time performance metrics (scan time, OCR accuracy)
- **Navigation Hub**: Central access to all major app features

### Barcode Scanning (`/barcode`)

- **Live Camera View**: Real-time barcode detection with overlay frame
- **Multiple Formats**: EAN-8, EAN-13, UPC-A, UPC-E, ITF-14, Code128/39/93 support
- **Scan Confirmation**: Requires multiple identical reads to prevent false positives
- **Duplicate Detection**: Alerts if item already exists in user's register
- **GTIN Normalization**: Converts various barcode formats to standard GTIN
- **Haptic Feedback**: Vibration confirmation on successful scans

### Manual Entry (`/manual`)

- **Direct Input**: Enter product name, size, and barcode manually
- **Barcode Validation**: Real-time validation of entered barcode formats
- **Smart Defaults**: Pre-fills data when available from previous scans
- **Duplicate Prevention**: Checks for existing products before creating new entries

### Product Confirmation (`/confirm`)

- **Dual Input Mode**: Choose between web-scraped data or manual entry
- **Data Editing**: Edit product name and size before saving
- **Size Prompting**: Modal prompt when size information is missing
- **SDS Integration**: Automatic SDS search and verification after saving
- **Watchlist Management**: Adds confirmed products to user's chemical register

### Chemical Register (`/register`)

- **Product Listing**: View all registered chemicals with key information
- **Direct Navigation**: Quick access from successful scans and manual entries
- **User-Specific Data**: Displays only the current user's chemical inventory

### SDS Viewer (`/sds-viewer`)

- **PDF Display**: Native PDF viewing with zoom and scroll
- **Direct Access**: Navigate from product confirmations and register listings
- **Web Browser Integration**: Seamless PDF viewing experience

---

## 🔧 Core Implementation

### Barcode Scanner Integration

```typescript
// app/barcode.tsx
import { CameraView, useCameraPermissions } from 'expo-camera';
import { useState, useRef } from 'react';

const SCAN_CONFIRMATIONS = 2; // Require multiple identical reads
const SCAN_WINDOW_MS = 1200; // Time window for confirmations
const RESCAN_COOLDOWN_MS = 1200; // Cooldown between scans

export default function BarcodeScreen() {
  const [permission, requestPermission] = useCameraPermissions();
  const [scanning, setScanning] = useState(true);
  const [confirming, setConfirming] = useState(false);
  const [loading, setLoading] = useState(false);

  // GTIN normalization and validation
  const normalizeToGtin = (raw: string): string | null => {
    // Supports EAN-8, EAN-13, UPC-A, UPC-E, ITF-14
    // with proper checksum validation
  };

  const handleBarcodeScanned = ({ data }: BarcodeScanningResult) => {
    if (!scanning || loading) return;

    // Prevent rapid-fire duplicate scans
    if (Date.now() - cooldownRef.current < RESCAN_COOLDOWN_MS) return;

    const confirmed = maybeConfirm(data);
    if (!confirmed) return;

    // Process confirmed, normalized GTIN
    setScanning(false);
    setLoading(true);
    Vibration.vibrate(80);

    // Call backend with user ID for duplicate detection
    processBarcode(confirmed);
  };

  return (
    <SafeAreaView className="flex-1 bg-black">
      <CameraView
        style={StyleSheet.absoluteFill}
        onBarcodeScanned={scanning ? handleBarcodeScanned : undefined}
        barcodeScannerSettings={{
          barcodeTypes: ['ean8', 'ean13', 'upc_a', 'upc_e', 'itf14', 'code128'],
        }}
      >
        <View className="absolute inset-0 items-center justify-center">
          <View className="h-48 w-[70%] border-4 border-white bg-white/10 rounded-xl">
            <Text className="text-white text-center font-bold">
              Align barcode here
            </Text>
          </View>
        </View>
      </CameraView>
    </SafeAreaView>
  );
}
```

### State Management with Zustand

```typescript
// lib/store.ts
import { create } from 'zustand';

// Confirm screen state management
interface ConfirmStore {
  photo: any | null;
  crop: CropRatios;
  setPhoto: (photo: any) => void;
  clearPhoto: () => void;
  setCrop: (crop: Partial<CropRatios>) => void;
  resetCrop: () => void;
}

export const useConfirmStore = create<ConfirmStore>(set => ({
  photo: null,
  crop: { leftRatio: 0.1, topRatio: 0.4, widthRatio: 0.8, heightRatio: 0.2 },
  setPhoto: photo => set({ photo }),
  clearPhoto: () => set({ photo: null }),
  setCrop: crop => set(state => ({ crop: { ...state.crop, ...crop } })),
  resetCrop: () => set({ crop: defaultCrop }),
}));

// Product state management
interface ProductState {
  barcode: string;
  name: string;
  size: string;
  sdsUrl?: string;
  setProduct: (p: Partial<Product>) => void;
  clear: () => void;
}

export const useProductStore = create<ProductState>(set => ({
  barcode: '',
  name: '',
  size: '',
  sdsUrl: '',
  setProduct: p => set(state => ({ ...state, ...p })),
  clear: () => set({ barcode: '', name: '', size: '', sdsUrl: '' }),
}));
```

### API Integration

```typescript
// lib/constants.ts
import Constants from 'expo-constants';
import { Platform } from 'react-native';

// Smart host detection for development
function guessHost(): string {
  if (process.env.EXPO_PUBLIC_DEV_HOST) return process.env.EXPO_PUBLIC_DEV_HOST;

  const uri = Constants?.expoConfig?.hostUri || Constants?.expoGoConfig?.debuggerHost || '';
  if (uri) return uri.split(':').shift()!;

  if (Platform.OS === 'android') return '10.0.2.2';
  return 'localhost';
}

export const BACKEND_API_URL =
  process.env.EXPO_PUBLIC_BACKEND_API_URL || `http://${guessHost()}:3001`;

// API usage example
const processBarcode = async (code: string) => {
  try {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    const userId = session?.user?.id;

    const response = await fetch(`${BACKEND_API_URL}/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, userId }),
    });

    const result = await response.json();

    if (result.alreadyInWatchlist) {
      // Handle duplicate detection
      Alert.alert('Item Already in Register', result.message);
      return;
    }

    // Navigate to confirmation with product data
    router.replace({
      pathname: '/confirm',
      params: {
        code,
        name: result.product?.name || '',
        size: result.product?.contents_size_weight || '',
      },
    });
  } catch (error) {
    console.error('API Error:', error);
  }
};
```

---

## 🔒 Authentication

### Supabase Integration

```typescript
// lib/supabase.ts
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.EXPO_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// Authentication usage in app
const handleLogin = async (email: string, password: string) => {
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });

  if (error) {
    Alert.alert('Login Failed', error.message);
    return;
  }

  router.replace('/');
};

const handleSignOut = async () => {
  await supabase.auth.signOut();
  router.replace('/login');
};

// Get current user session
const getCurrentUser = async () => {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.user || null;
};
```

---

## 🧪 Testing

### Unit Testing

```bash
# Run tests
npm test

# Run tests in watch mode
npm test -- --watch

# Generate coverage report
npm test -- --coverage
```

---

## 🚀 Deployment

### EAS Build Configuration

```json
// eas.json
{
  "cli": {
    "version": ">= 12.4.0"
  },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal",
      "channel": "dev",
      "env": {
        "EXPO_PUBLIC_BACKEND_API_URL": "http://your-backend-host:3001"
      }
    },
    "preview": {
      "distribution": "internal",
      "channel": "preview",
      "android": { "buildType": "apk" }
    },
    "production": {
      "distribution": "store",
      "autoIncrement": true,
      "channel": "production",
      "env": {
        "EXPO_PUBLIC_BACKEND_API_URL": "http://your-backend-host:3001"
      }
    }
  },
  "submit": {
    "production": {
      "android": {
        "track": "production",
        "serviceAccountKeyPath": "./google-service-account.json"
      }
    }
  }
}
```

### Build Commands

```bash
# Development build
eas build --profile development --platform all

# Preview build for internal testing
eas build --profile preview --platform all

# Production build
eas build --profile production --platform all

# Platform-specific builds
eas build --profile production --platform android
eas build --profile production --platform ios

# Submit to app stores
eas submit --profile production --platform android
eas submit --profile production --platform ios
```

---

## 🔄 Recent Updates

### Version 2024.12

**New Features:**

- ✅ **Enhanced OCR Processing**: Improved text recognition accuracy
- ✅ **Offline Support**: Queue actions when network unavailable
- ✅ **Better Error Handling**: Graceful fallbacks for failed operations
- ✅ **Performance Optimization**: Faster app startup and smoother animations

**UI/UX Improvements:**

- 🎨 **Redesigned Scanning Interface**: Cleaner barcode scanning overlay
- 🎨 **Improved Navigation**: More intuitive tab-based navigation
- 🎨 **Better Feedback**: Enhanced loading states and success indicators
- 🎨 **Dark Mode Refinements**: Better contrast and readability

**Bug Fixes:**

- 🔧 **Camera Permissions**: Fixed permission handling on Android 13+
- 🔧 **OCR Stability**: Resolved crashes with large images
- 🔧 **Memory Management**: Better cleanup of camera resources
- 🔧 **Authentication Flow**: Fixed login persistence issues

---

## 📄 License

This project is proprietary software. All rights reserved.

---

## 👥 Support

**Technical Issues:**

- Check device permissions for camera and storage
- Verify network connectivity for API calls
- Review app logs in development mode

**Device Compatibility:**

- iOS 13.0+ required
- Android API level 21+ (Android 5.0+)
- Camera required for barcode scanning
- Network connection for data sync

---

## 🗺️ Roadmap

### Q1 2025

- **Push Notifications**: Real-time alerts for SDS updates
- **Bulk Scanning**: Process multiple barcodes in sequence
- **Advanced Filters**: Enhanced search and filtering options
- **Export Functions**: Generate PDF reports from mobile

### Q2 2025

- **AR Integration**: Augmented reality chemical identification
- **Voice Commands**: Hands-free operation for industrial use
- **Wearable Support**: Apple Watch and Android Wear integration
- **Multi-language**: Localization for international markets
