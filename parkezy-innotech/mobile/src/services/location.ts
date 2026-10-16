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

/** Rejects if `promise` takes longer than `ms` (some calls never settle, e.g. compass on a laptop). */
function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('timeout')), ms);
    promise.then(
      (v) => {
        clearTimeout(timer);
        resolve(v);
      },
      (e) => {
        clearTimeout(timer);
        reject(e);
      },
    );
  });
}

/** Get user position with compass heading for standing orientation arrow. */
export async function currentUserPosition(): Promise<UserPosition> {
  try {
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') return { coords: env.defaultRegion, granted: false };
    const position = await withTimeout(
      Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High }),
      10_000,
    ).catch(async () => {
      // No high-accuracy fix in time: fall back to the last known one rather than leaving the map loading.
      const last = await Location.getLastKnownPositionAsync();
      if (!last) throw new Error('no position');
      return last;
    });
    let heading: number | undefined = position.coords.heading ?? undefined;
    if (heading === undefined || heading < 0) {
      try {
        // Devices without a compass never answer; don't hold the map for it.
        const compass = await withTimeout(Location.getHeadingAsync(), 1500);
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
 * Follows the user while the map is open: position updates as they move and compass heading
 * as they turn, so the arrow stays live. Only call after permission was granted.
 * Returns a function that stops both watchers.
 */
export async function watchUserPosition(onUpdate: (update: { coords?: Coords; heading?: number }) => void): Promise<() => void> {
  const subs: Location.LocationSubscription[] = [];
  try {
    subs.push(
      await Location.watchPositionAsync(
        { accuracy: Location.Accuracy.High, distanceInterval: 5, timeInterval: 3000 },
        (p) => onUpdate({ coords: { latitude: p.coords.latitude, longitude: p.coords.longitude } }),
      ),
    );
  } catch {
    // Position stays at the last known fix.
  }
  try {
    // No compass on web or some emulators; the arrow just keeps its last direction.
    subs.push(
      await Location.watchHeadingAsync((h) => {
        const heading = h.trueHeading >= 0 ? h.trueHeading : h.magHeading;
        if (heading >= 0) onUpdate({ heading });
      }),
    );
  } catch {
    // Ignore.
  }
  return () => subs.forEach((s) => s.remove());
}

/** Distance in metres between two coordinates (haversine). */
export function metresBetween(a: Coords, b: Coords): number {
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(b.latitude - a.latitude);
  const dLon = toRad(b.longitude - a.longitude);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a.latitude)) * Math.cos(toRad(b.latitude)) * Math.sin(dLon / 2) ** 2;
  return 2 * 6_371_000 * Math.asin(Math.sqrt(h));
}

/**
 * Universal geocoding: tries Google Maps API if configured, then Expo native geocoder,
 * falling back to OpenStreetMap Nominatim for 100% reliable worldwide location discovery.
 */
export async function geocode(query: string): Promise<Coords | null> {
  const clean = query.trim();
  if (!clean) return null;

  // 1. Try Google Maps Geocoding if API key is configured
  if (env.googleMapsApiKey) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 3000);
      const url = `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(clean)}&key=${env.googleMapsApiKey}`;
      const res = await fetch(url, { signal: controller.signal });
      clearTimeout(timer);
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'OK' && data.results && data.results[0]?.geometry?.location) {
          const loc = data.results[0].geometry.location;
          return { latitude: loc.lat, longitude: loc.lng };
        }
      }
    } catch {
      // Fallback to native
    }
  }

  // 2. Try native geocoding
  try {
    const results = await Location.geocodeAsync(clean);
    if (results && results[0]) {
      return { latitude: results[0].latitude, longitude: results[0].longitude };
    }
  } catch {
    // Proceed to OSM fallback
  }

  // 3. Universal OpenStreetMap Nominatim fallback (works for any city, landmark, or address globally)
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
 * Universal reverse geocoding with Google Maps, native, and Nominatim fallback.
 */
export async function reverseGeocode(coords: Coords): Promise<{ address: string; city: string; postalCode: string }> {
  // 1. Try Google Maps Reverse Geocoding if API key is configured
  if (env.googleMapsApiKey) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 3000);
      const url = `https://maps.googleapis.com/maps/api/geocode/json?latlng=${coords.latitude},${coords.longitude}&key=${env.googleMapsApiKey}`;
      const res = await fetch(url, { signal: controller.signal });
      clearTimeout(timer);
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'OK' && data.results && data.results[0]) {
          const r = data.results[0];
          let city = '';
          let postalCode = '';
          for (const comp of r.address_components || []) {
            if (comp.types.includes('locality')) city = comp.long_name;
            else if (!city && comp.types.includes('administrative_area_level_2')) city = comp.long_name;
            if (comp.types.includes('postal_code')) postalCode = comp.long_name;
          }
          return { address: r.formatted_address || '', city, postalCode };
        }
      }
    } catch {
      // Fallback
    }
  }

  // 2. Try native reverse geocoding
  try {
    const [place] = await Location.reverseGeocodeAsync(coords);
    if (place) {
      const address = [place.name, place.street].filter(Boolean).join(', ');
      return { address, city: place.city ?? place.subregion ?? '', postalCode: place.postalCode ?? '' };
    }
  } catch {
    // Proceed to OSM fallback
  }

  // 3. OpenStreetMap Nominatim fallback
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
