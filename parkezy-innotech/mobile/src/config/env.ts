/**
 * Runtime configuration. Values come from mobile/.env (EXPO_PUBLIC_* are inlined at build time).
 * Business rules (prices, GST, booking steps…) are NOT here — they are fetched from GET /v1/config.
 */

function required(name: string, value: string | undefined): string {
  if (!value) {
    throw new Error(`Missing ${name}. Copy mobile/.env.example to mobile/.env and fill it in.`);
  }
  return value;
}

function number(name: string, value: string | undefined): number {
  const parsed = Number(required(name, value));
  if (Number.isNaN(parsed)) throw new Error(`${name} must be a number`);
  return parsed;
}

export const env = {
  apiUrl: required('EXPO_PUBLIC_API_URL', process.env.EXPO_PUBLIC_API_URL).replace(/\/$/, ''),
  apiTimeoutMs: number('EXPO_PUBLIC_API_TIMEOUT_MS', process.env.EXPO_PUBLIC_API_TIMEOUT_MS),
  defaultRegion: {
    latitude: number('EXPO_PUBLIC_DEFAULT_LATITUDE', process.env.EXPO_PUBLIC_DEFAULT_LATITUDE),
    longitude: number('EXPO_PUBLIC_DEFAULT_LONGITUDE', process.env.EXPO_PUBLIC_DEFAULT_LONGITUDE),
  },
  supportEmail: required('EXPO_PUBLIC_SUPPORT_EMAIL', process.env.EXPO_PUBLIC_SUPPORT_EMAIL),
  privacyUrl: required('EXPO_PUBLIC_PRIVACY_URL', process.env.EXPO_PUBLIC_PRIVACY_URL),
  termsUrl: required('EXPO_PUBLIC_TERMS_URL', process.env.EXPO_PUBLIC_TERMS_URL),
} as const;
