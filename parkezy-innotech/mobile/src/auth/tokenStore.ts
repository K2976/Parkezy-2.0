import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const REFRESH_KEY = 'parkezy.refresh_token';

// SecureStore has no web implementation; the web build (used for previews) keeps the token in memory.
let memoryToken: string | null = null;
const native = Platform.OS === 'ios' || Platform.OS === 'android';

/** Only the long-lived refresh token is persisted (in the Keychain/Keystore); access tokens stay in memory. */
export const tokenStore = {
  async loadRefresh(): Promise<string | null> {
    if (!native) return memoryToken;
    try {
      return await SecureStore.getItemAsync(REFRESH_KEY);
    } catch {
      return null;
    }
  },
  async saveRefresh(token: string): Promise<void> {
    if (!native) {
      memoryToken = token;
      return;
    }
    await SecureStore.setItemAsync(REFRESH_KEY, token);
  },
  async clear(): Promise<void> {
    memoryToken = null;
    if (native) await SecureStore.deleteItemAsync(REFRESH_KEY);
  },
};
