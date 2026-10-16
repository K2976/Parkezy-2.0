import MaterialCommunityIcons from '@expo/vector-icons/MaterialCommunityIcons';
import { forwardRef, useImperativeHandle, useRef } from 'react';
import { Platform, StyleSheet, View } from 'react-native';
import MapView, { Circle, Marker, PROVIDER_GOOGLE } from 'react-native-maps';

import type { ListingSearchItem } from '@/api/types';
import { Text } from '@/ui/components';
import { fonts, radius, useTheme } from '@/ui/theme';
import { money } from '@/utils/format';

export type MapRegion = { latitude: number; longitude: number; latitudeDelta: number; longitudeDelta: number };
export type ParkingMapHandle = { animateTo: (region: MapRegion) => void };

type Props = {
  initialRegion: MapRegion;
  items: ListingSearchItem[];
  showsUserLocation: boolean;
  userLocation?: { latitude: number; longitude: number; heading?: number } | null;
  /** Radius in metres of the "near you" zone drawn around the user's location. */
  zoneRadiusM?: number;
  onRegionChange: (region: MapRegion) => void;
  onSelect: (item: ListingSearchItem) => void;
};

/** Native map with Google Maps on Android, clay price pins, and user standing navigation arrow. */
export const ParkingMap = forwardRef<ParkingMapHandle, Props>(function ParkingMap(
  { initialRegion, items, showsUserLocation, userLocation, zoneRadiusM, onRegionChange, onSelect },
  ref,
) {
  const { colors, shadows } = useTheme();
  const map = useRef<MapView>(null);
  useImperativeHandle(ref, () => ({ animateTo: (region) => map.current?.animateToRegion(region, 400) }));
  return (
    <MapView
      ref={map}
      provider={Platform.OS === 'android' ? PROVIDER_GOOGLE : undefined}
      style={StyleSheet.absoluteFill}
      initialRegion={initialRegion}
      mapType="standard"
      showsUserLocation={showsUserLocation && !userLocation}
      onRegionChangeComplete={onRegionChange}
      accessibilityLabel="Map of parking spots">
      {userLocation && zoneRadiusM ? (
        <Circle
          center={{ latitude: userLocation.latitude, longitude: userLocation.longitude }}
          radius={zoneRadiusM}
          strokeWidth={1.5}
          strokeColor={colors.accent}
          fillColor="rgba(110, 91, 196, 0.10)"
          zIndex={2}
        />
      ) : null}
      {userLocation ? (
        <Marker
          coordinate={{ latitude: userLocation.latitude, longitude: userLocation.longitude }}
          anchor={{ x: 0.5, y: 0.5 }}
          flat
          // Rotate the marker natively so compass updates show without re-rendering the view.
          rotation={userLocation.heading ?? 0}
          tracksViewChanges={false}
          zIndex={999}
          accessibilityLabel="Your standing location">
          <View style={styles.userBeacon}>
            <View style={[styles.userPulse, { borderColor: colors.accent, backgroundColor: colors.accentSoft }]} />
            <View
              style={[
                styles.userArrowDisc,
                { backgroundColor: colors.accent, borderColor: colors.clay },
              ]}>
              <MaterialCommunityIcons name="navigation" size={17} color={colors.onAccent} />
            </View>
          </View>
        </Marker>
      ) : null}
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

const styles = StyleSheet.create({
  userBeacon: {
    width: 48,
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
  },
  userPulse: {
    position: 'absolute',
    width: 46,
    height: 46,
    borderRadius: 23,
    borderWidth: 2,
    opacity: 0.4,
  },
  userArrowDisc: {
    width: 30,
    height: 30,
    borderRadius: 15,
    borderWidth: 2.5,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3,
    elevation: 4,
  },
});

