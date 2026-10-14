import * as Crypto from 'expo-crypto';

/**
 * RFC 4122 v4 UUID from secure random bytes.
 *
 * Not `Crypto.randomUUID()`: on web that maps to the browser's `crypto.randomUUID`, which only
 * exists on secure origins (HTTPS / localhost), so the app crashes when opened over the LAN
 * (http://192.168.x.x:8081). `getRandomBytes` works on every platform and origin.
 */
export function uuidV4(): string {
  const b = Crypto.getRandomBytes(16);
  b[6] = (b[6] & 0x0f) | 0x40; // version 4
  b[8] = (b[8] & 0x3f) | 0x80; // RFC 4122 variant
  const hex = Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
