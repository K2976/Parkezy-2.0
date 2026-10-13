import { forwardRef, useImperativeHandle, useRef } from 'react';
import { StyleSheet, View } from 'react-native';
import MapView, { Marker, UrlTile } from 'react-native-maps';

import type { ListingSearchItem } from '@/api/types';
import { Text } from '@/ui/components';
import { fonts, radius, useTheme } from '@/ui/theme';
import { money } from '@/utils/format';

export type MapRegion = { latitude: number; longitude: number; latitudeDelta: number; longitudeDelta: number };
export type ParkingMapHandle = { animateTo: (region: MapRegion) => void };

/** OpenStreetMap tile server URL template */
const OSM_URL_TEMPLATE = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';

type Props = {
  initialRegion: MapRegion;
  items: ListingSearchItem[];
  showsUserLocation: boolean;
  onRegionChange: (region: MapRegion) => void;
  onSelect: (item: ListingSearchItem) => void;
};

/** Native map with OpenStreetMap tiles and clay price pins. */
export const ParkingMap = forwardRef<ParkingMapHandle, Props>(function ParkingMap(
  { initialRegion, items, showsUserLocation, onRegionChange, onSelect },
  ref,
) {
  const { colors, shadows } = useTheme();
  const map = useRef<MapView>(null);
  useImperativeHandle(ref, () => ({ animateTo: (region) => map.current?.animateToRegion(region, 400) }));
  return (
    <MapView
      ref={map}
      style={StyleSheet.absoluteFill}
      initialRegion={initialRegion}
      mapType="none"
      showsUserLocation={showsUserLocation}
      onRegionChangeComplete={onRegionChange}
      accessibilityLabel="Map of parking spots">
      <UrlTile
        urlTemplate={OSM_URL_TEMPLATE}
        maximumZ={19}
        flipY={false}
        tileSize={256}
        zIndex={-1}
      />
      {items.map((item) => {
        const full = item.available_slots === 0;
        return (
          <Marker
            key={item.id}
            coordinate={{ latitude: item.latitude, longitude: item.longitude }}
            onPress={() => onSelect(item)}
            accessibilityLabel={`${item.title}, ${money(item.hourly_rate, item.currency)} per hour`}
            tracksViewChanges={false}>
            {/* Clay price pin: solid accent when bookable, raised neutral when full. */}
            <View
              style={{
                paddingHorizontal: 10,
                paddingVertical: 6,
                borderRadius: radius.pill,
                backgroundColor: full ? colors.clay : colors.accent,
                boxShadow: full ? shadows.clayRaised : shadows.clayAccent,
              }}>
              <Text style={{ color: full ? colors.muted : colors.onAccent, fontFamily: fonts.heading, fontSize: 13 }}>
                {money(item.hourly_rate, item.currency)}
              </Text>
            </View>
          </Marker>
        );
      })}
    </MapView>
  );
});
