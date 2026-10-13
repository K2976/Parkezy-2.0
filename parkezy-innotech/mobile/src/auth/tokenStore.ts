import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const REFRESH_KEY = 'parkezy.refresh_token';

// SecureStore has no web implementation. On web the refresh token lives in sessionStorage so a page
// refresh keeps you signed in, but it is gone when the tab closes (never in long-lived localStorage).
let memoryToken: string | null = null;
const native = Platform.OS === 'ios' || Platform.OS === 'android';

const webSession = {
  get(): string | null {
    try {
      return globalThis.sessionStorage?.getItem(REFRESH_KEY) ?? memoryToken;
    } catch {
      return memoryToken;
    }
  },
  set(token: string | null): void {
    memoryToken = token;
    try {
      if (token) globalThis.sessionStorage?.setItem(REFRESH_KEY, token);
      else globalThis.sessionStorage?.removeItem(REFRESH_KEY);
    } catch {
      // Storage blocked (private mode): memory only.
    }
  },
};

/** Only the long-lived refresh token is persisted (in the Keychain/Keystore); access tokens stay in memory. */
export const tokenStore = {
  async loadRefresh(): Promise<string | null> {
    if (!native) return webSession.get();
    try {
      return await SecureStore.getItemAsync(REFRESH_KEY);
    } catch {
      return null;
    }
  },
  async saveRefresh(token: string): Promise<void> {
    if (!native) {
      webSession.set(token);
      return;
    }
    await SecureStore.setItemAsync(REFRESH_KEY, token);
  },
  async clear(): Promise<void> {
    if (!native) {
      webSession.set(null);
      return;
    }
    await SecureStore.deleteItemAsync(REFRESH_KEY);
  },
};
