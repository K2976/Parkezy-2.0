import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

import { uuidV4 } from '@/utils/id';

const KEY = 'parkezy.device_id';
const native = Platform.OS === 'ios' || Platform.OS === 'android';
let cached: string | null = null;

/**
 * A random id for this app install, sent as X-Device-Id on sign-in only. The API uses it to
 * recognise a phone that signed in before (less friction under attack). It is not a fingerprint:
 * nothing about the device goes into it, and reinstalling the app gives a new one.
 */
export async function deviceId(): Promise<string> {
  if (cached) return cached;
  if (native) {
    try {
      cached = await SecureStore.getItemAsync(KEY);
      if (!cached) {
        cached = uuidV4();
        await SecureStore.setItemAsync(KEY, cached);
      }
      return cached;
    } catch {
      // Keystore unavailable: fall through to a per-session id.
    }
  }
  cached ??= uuidV4();
  return cached;
}
