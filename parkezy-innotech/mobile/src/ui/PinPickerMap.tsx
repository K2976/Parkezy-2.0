import { StyleSheet } from 'react-native';
import MapView, { Marker, UrlTile } from 'react-native-maps';

import { env } from '@/config/env';
import type { MapRegion } from '@/ui/ParkingMap';

type Coords = { latitude: number; longitude: number };

const OSM_URL_TEMPLATE = env.osmTileUrl;

/** Map the host pans so the pin sits on their entrance, rendered with OpenStreetMap tiles. */
export function PinPickerMap({ initialRegion, pin, onMove }: { initialRegion: MapRegion; pin: Coords | null; onMove: (c: Coords) => void }) {
  return (
    <MapView
      style={StyleSheet.absoluteFill}
      initialRegion={initialRegion}
      mapType="none"
      onRegionChangeComplete={(r) => onMove({ latitude: r.latitude, longitude: r.longitude })}
      accessibilityLabel="Map to place your parking spot">
      <UrlTile
        urlTemplate={OSM_URL_TEMPLATE}
        maximumZ={19}
        flipY={false}
        tileSize={256}
        zIndex={1}
      />
      {pin ? <Marker coordinate={pin} /> : null}
    </MapView>
  );
}
