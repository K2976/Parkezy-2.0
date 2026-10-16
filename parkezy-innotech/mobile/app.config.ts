import type { ConfigContext, ExpoConfig } from 'expo/config';

// Every value that differs per environment comes from mobile/.env (see .env.example).
const env = (name: string, fallback?: string): string => {
  const value = process.env[name] ?? fallback;
  if (value === undefined) throw new Error(`Missing ${name} in mobile/.env`);
  return value;
};

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: env('APP_DISPLAY_NAME', 'Parkezy'),
  slug: 'parkezy',
  owner: 'honourss-team',
  version: '1.0.0',
  orientation: 'portrait',
  icon: './assets/images/icon.png',
  scheme: env('APP_SCHEME', 'parkezy'),
  userInterfaceStyle: 'light',
  ios: {
    bundleIdentifier: env('IOS_BUNDLE_ID', 'com.parkezy.app'),
    supportsTablet: false,
    infoPlist: {
      NSLocationWhenInUseUsageDescription: 'Parkezy uses your location to show parking spots near you.',
      NSPhotoLibraryUsageDescription: 'Parkezy needs your photos to add pictures of your parking spot or a report.',
      NSCameraUsageDescription: 'Parkezy uses the camera to scan driver QR codes and photograph parking spots.',
    },
  },
  android: {
    package: env('ANDROID_PACKAGE', 'com.parkezy.app'),
    adaptiveIcon: {
      backgroundColor: '#E6F4FE',
      foregroundImage: './assets/images/android-icon-foreground.png',
      backgroundImage: './assets/images/android-icon-background.png',
      monochromeImage: './assets/images/android-icon-monochrome.png',
    },
    permissions: ['ACCESS_COARSE_LOCATION', 'ACCESS_FINE_LOCATION', 'CAMERA'],
    blockedPermissions: ['android.permission.RECORD_AUDIO'],
  },
  web: { output: 'static', favicon: './assets/images/favicon.png' },
  plugins: [
    'expo-router',
    'expo-secure-store',
    '@clerk/expo',
    'expo-web-browser',
    '@react-native-community/datetimepicker',
    ['expo-splash-screen', { backgroundColor: '#F4F1FA', image: './assets/images/splash-icon.png', imageWidth: 76 }],
    ['expo-location', { locationWhenInUsePermission: 'Parkezy uses your location to show parking spots near you.' }],
    [
      'expo-camera',
      {
        cameraPermission: 'Parkezy uses the camera to scan driver QR codes at your parking spot.',
        recordAudioAndroid: false,
      },
    ],
    ['expo-image-picker', { photosPermission: 'Parkezy needs your photos to add pictures of your parking spot.' }],
    ['expo-notifications', { color: '#6E5BC4' }],
    ['react-native-maps', { androidGoogleMapsApiKey: process.env.GOOGLE_MAPS_ANDROID_API_KEY || process.env.GOOGLE_MAPS_API_KEY || process.env.EXPO_PUBLIC_GOOGLE_MAPS_API_KEY || '' }],
  ],
  experiments: { typedRoutes: true, reactCompiler: true },
  extra: {
    eas: process.env.EAS_PROJECT_ID ? { projectId: process.env.EAS_PROJECT_ID } : undefined,
  },
});
