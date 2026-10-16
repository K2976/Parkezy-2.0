import { Platform, StyleSheet } from 'react-native';
import MapView, { Marker, PROVIDER_GOOGLE } from 'react-native-maps';

import type { MapRegion } from '@/ui/ParkingMap';

type Coords = { latitude: number; longitude: number };

/** Map the host pans so the pin sits on their entrance, rendered with native Google Maps on Android. */
export function PinPickerMap({ initialRegion, pin, onMove }: { initialRegion: MapRegion; pin: Coords | null; onMove: (c: Coords) => void }) {
  return (
    <MapView
      provider={Platform.OS === 'android' ? PROVIDER_GOOGLE : undefined}
      style={StyleSheet.absoluteFill}
      initialRegion={initialRegion}
      mapType="standard"
      onRegionChangeComplete={(r) => onMove({ latitude: r.latitude, longitude: r.longitude })}
      accessibilityLabel="Map to place your parking spot">
      {pin ? <Marker coordinate={pin} /> : null}
    </MapView>
  );
}
