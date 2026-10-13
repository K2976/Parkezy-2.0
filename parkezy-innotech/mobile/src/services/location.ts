import * as Location from 'expo-location';

import { env } from '@/config/env';

export type Coords = { latitude: number; longitude: number };

/** Current position if the user allows it; otherwise the configured default city centre. */
export async function currentOrDefault(): Promise<{ coords: Coords; granted: boolean }> {
  try {
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') return { coords: env.defaultRegion, granted: false };
    const last = await Location.getLastKnownPositionAsync();
    const position = last ?? (await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced }));
    return { coords: { latitude: position.coords.latitude, longitude: position.coords.longitude }, granted: true };
  } catch {
    return { coords: env.defaultRegion, granted: false };
  }
}

export async function geocode(query: string): Promise<Coords | null> {
  const results = await Location.geocodeAsync(query);
  return results[0] ? { latitude: results[0].latitude, longitude: results[0].longitude } : null;
}

export async function reverseGeocode(coords: Coords): Promise<{ address: string; city: string; postalCode: string }> {
  const [place] = await Location.reverseGeocodeAsync(coords);
  if (!place) return { address: '', city: '', postalCode: '' };
  const address = [place.name, place.street].filter(Boolean).join(', ');
  return { address, city: place.city ?? place.subregion ?? '', postalCode: place.postalCode ?? '' };
}
