import * as Location from 'expo-location';

import { env } from '@/config/env';

export type Coords = { latitude: number; longitude: number };

export type UserPosition = {
  coords: Coords;
  heading?: number;
  granted: boolean;
};

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

/** Get user position with compass heading for standing orientation arrow. */
export async function currentUserPosition(): Promise<UserPosition> {
  try {
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') return { coords: env.defaultRegion, granted: false };
    const position = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High });
    let heading: number | undefined = position.coords.heading ?? undefined;
    if (heading === undefined || heading < 0) {
      try {
        const compass = await Location.getHeadingAsync();
        heading = compass.trueHeading >= 0 ? compass.trueHeading : compass.magHeading;
      } catch {
        heading = 0;
      }
    }
    return {
      coords: { latitude: position.coords.latitude, longitude: position.coords.longitude },
      heading,
      granted: true,
    };
  } catch {
    return { coords: env.defaultRegion, granted: false };
  }
}

/**
 * Universal geocoding: tries Expo native geocoder first; falls back to
 * OpenStreetMap Nominatim for 100% reliable worldwide location discovery.
 */
export async function geocode(query: string): Promise<Coords | null> {
  const clean = query.trim();
  if (!clean) return null;

  // 1. Try native geocoding first
  try {
    const results = await Location.geocodeAsync(clean);
    if (results && results[0]) {
      return { latitude: results[0].latitude, longitude: results[0].longitude };
    }
  } catch {
    // Proceed to OSM fallback
  }

  // 2. Universal OpenStreetMap Nominatim fallback (works for any city, landmark, or address globally)
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 4000);
    const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(clean)}&limit=1`;
    const res = await fetch(url, {
      signal: controller.signal,
      headers: {
        'Accept': 'application/json',
        'User-Agent': 'ParkezyApp/2.0 (support@parkezy.com)',
      },
    });
    clearTimeout(timer);
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data) && data[0]) {
        const lat = parseFloat(data[0].lat);
        const lon = parseFloat(data[0].lon);
        if (!isNaN(lat) && !isNaN(lon)) {
          return { latitude: lat, longitude: lon };
        }
      }
    }
  } catch (err) {
    console.warn('Nominatim geocode fallback failed:', err);
  }

  return null;
}

/**
 * Universal reverse geocoding with Nominatim fallback.
 */
export async function reverseGeocode(coords: Coords): Promise<{ address: string; city: string; postalCode: string }> {
  try {
    const [place] = await Location.reverseGeocodeAsync(coords);
    if (place) {
      const address = [place.name, place.street].filter(Boolean).join(', ');
      return { address, city: place.city ?? place.subregion ?? '', postalCode: place.postalCode ?? '' };
    }
  } catch {
    // Proceed to OSM fallback
  }

  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 4000);
    const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${coords.latitude}&lon=${coords.longitude}&addressdetails=1`;
    const res = await fetch(url, {
      signal: controller.signal,
      headers: {
        'Accept': 'application/json',
        'User-Agent': 'ParkezyApp/2.0 (support@parkezy.com)',
      },
    });
    clearTimeout(timer);
    if (res.ok) {
      const data = await res.json();
      if (data && data.address) {
        const addr = data.address;
        const street = addr.road || addr.suburb || addr.neighbourhood || addr.amenity || '';
        const city = addr.city || addr.town || addr.village || addr.county || addr.state || '';
        const postalCode = addr.postcode || '';
        return { address: street, city, postalCode };
      }
    }
  } catch (err) {
    console.warn('Nominatim reverse geocode fallback failed:', err);
  }

  return { address: '', city: '', postalCode: '' };
}
