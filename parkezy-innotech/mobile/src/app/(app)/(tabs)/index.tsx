import Ionicons from '@expo/vector-icons/Ionicons';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { BlurTargetView } from 'expo-blur';
import { Image } from 'expo-image';
import { router } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import { FlatList, Modal, Pressable, ScrollView, StyleSheet, TextInput, View } from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';

import { errorMessage } from '@/api/client';
import { discoveryApi, type SearchParams } from '@/api/endpoints';
import type { ListingSearchItem } from '@/api/types';
import { keys, useConfig } from '@/hooks/queries';
import { currentUserPosition, geocode, metresBetween, type UserPosition, watchUserPosition } from '@/services/location';
import { Backdrop, BlurTargetProvider } from '@/ui/Backdrop';
import { Meter } from '@/ui/charts';
import {
  Banner,
  Button,
  Card,
  Chip,
  EmptyState,
  ErrorState,
  IconButton,
  IconOrb,
  type IconName,
  Loading,
  Row,
  Text,
} from '@/ui/components';
import { Glass } from '@/ui/Glass';
import { type MapRegion as Region, ParkingMap, type ParkingMapHandle } from '@/ui/ParkingMap';
import { fonts, radius, spacing, useTheme } from '@/ui/theme';
import { defaultWindow, type Window, WhenPicker, windowIso } from '@/ui/WhenPicker';
import { dateTime, distance, duration, money, titleCase } from '@/utils/format';

const KM_PER_DEGREE = 111;
/** Radius of the "near you" zone drawn around the user; spots inside it are listed first. */
const NEARBY_ZONE_M = 1000;

function radiusFor(region: Region, maxKm: number): number {
  const km = (Math.max(region.latitudeDelta, region.longitudeDelta) * KM_PER_DEGREE) / 2;
  return Math.min(Math.max(km, 0.5), maxKm);
}

const AMENITY_ICONS: Record<string, IconName> = {
  covered: 'shield-checkmark-outline',
  cctv: 'videocam-outline',
  security_guard: 'person-outline',
  wheelchair_access: 'body-outline',
  well_lit: 'sunny-outline',
  gated: 'lock-closed-outline',
  restroom: 'water-outline',
};

export default function FindParking() {
  const { colors, shadows } = useTheme();
  const insets = useSafeAreaInsets();
  const config = useConfig();
  const map = useRef<ParkingMapHandle>(null);
  const mapTarget = useRef<View | null>(null);
  const [region, setRegion] = useState<Region | null>(null);
  const [userPos, setUserPos] = useState<UserPosition | null>(null);
  const [locationDenied, setLocationDenied] = useState(false);
  const [view, setView] = useState<'map' | 'list'>('map');
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [filters, setFilters] = useState<{ kind?: string; amenities: string[]; slot_type?: string }>({ amenities: [] });
  const [showFilters, setShowFilters] = useState(false);
  const [chosenWhen, setWhen] = useState<Window | null>(null);
  const [showWhen, setShowWhen] = useState(false);
  const [selectedNearestIndex, setSelectedNearestIndex] = useState(0);
  const [hideNearestCard, setHideNearestCard] = useState(false);

  const fetchUserLocation = async () => {
    const pos = await currentUserPosition();
    setUserPos(pos);
    setLocationDenied(!pos.granted);
    return pos;
  };

  useEffect(() => {
    let cancelled = false;
    currentUserPosition().then((pos) => {
      if (cancelled) return;
      setUserPos(pos);
      setLocationDenied(!pos.granted);
      setRegion({ ...pos.coords, latitudeDelta: 0.03, longitudeDelta: 0.03 });
    });
    return () => {
      cancelled = true;
    };
  }, []);

  // Keep the arrow live (position + compass) once permission is granted.
  const granted = !!userPos?.granted;
  useEffect(() => {
    if (!granted) return;
    let stop: (() => void) | undefined;
    let cancelled = false;
    watchUserPosition((u) => setUserPos((prev) => (prev ? { ...prev, ...u, coords: u.coords ?? prev.coords } : prev))).then((fn) => {
      if (cancelled) fn();
      else stop = fn;
    });
    return () => {
      cancelled = true;
      stop?.();
    };
  }, [granted]);

  const recenterToUser = () => {
    if (userPos?.granted) {
      const next = { ...userPos.coords, latitudeDelta: 0.04, longitudeDelta: 0.04 };
      map.current?.animateTo(next);
      setRegion(next);
    } else {
      fetchUserLocation().then((pos) => {
        if (pos.granted) {
          const next = { ...pos.coords, latitudeDelta: 0.04, longitudeDelta: 0.04 };
          map.current?.animateTo(next);
          setRegion(next);
        }
      });
    }
  };

  const isNearUser = !!(
    userPos?.coords &&
    region &&
    Math.abs(region.latitude - userPos.coords.latitude) < 0.01 &&
    Math.abs(region.longitude - userPos.coords.longitude) < 0.01
  );

  // Until the user picks a time, search "now" for the default duration (computed once per config load).
  const initialWhen = useMemo(() => (config.data ? defaultWindow(config.data) : null), [config.data]);
  const when = chosenWhen ?? initialWhen;

  // While looking around their own location, always fetch the whole "near you" zone, even when zoomed in
  // past it, so the zone count and nearest list don't change just because the user zoomed.
  const zoneUser = userPos?.granted ? userPos.coords : null;
  const zoneMinKm =
    zoneUser && region && metresBetween(region, zoneUser) < NEARBY_ZONE_M * 2
      ? Math.ceil((metresBetween(region, zoneUser) + NEARBY_ZONE_M) / 100) / 10
      : 0;

  const params: SearchParams | null = useMemo(() => {
    if (!region || !config.data || !when) return null;
    const maxKm = config.data.search_max_radius_km;
    return {
      latitude: Number(region.latitude.toFixed(4)),
      longitude: Number(region.longitude.toFixed(4)),
      radius_km: Number(Math.min(Math.max(radiusFor(region, maxKm), zoneMinKm), maxKm).toFixed(1)),
      kind: filters.kind,
      amenities: filters.amenities,
      slot_type: filters.slot_type,
      ...windowIso(when),
    };
  }, [region, config.data, when, filters, zoneMinKm]);

  const results = useQuery({
    queryKey: keys.search(params ?? {}),
    queryFn: ({ signal }) => discoveryApi.search(params!, signal),
    enabled: !!params,
    placeholderData: keepPreviousData,
  });

  const runSearch = async () => {
    const trimmed = query.trim();
    if (!trimmed) return;
    setSearchError(null);
    setIsSearching(true);
    try {
      const found = await geocode(trimmed);
      if (!found) {
        setSearchError(`We couldn’t find "${trimmed}". Try another landmark or city.`);
        return;
      }
      const next = { ...found, latitudeDelta: 0.04, longitudeDelta: 0.04 };
      map.current?.animateTo(next);
      setRegion(next);
      setSelectedNearestIndex(0);
      setHideNearestCard(false);
    } catch {
      setSearchError('Search is currently unavailable. Please check your connection.');
    } finally {
      setIsSearching(false);
    }
  };

  const toggleAmenity = (a: string) =>
    setFilters((f) => ({ ...f, amenities: f.amenities.includes(a) ? f.amenities.filter((x) => x !== a) : [...f.amenities, a] }));

  if (config.isError) return <ErrorState message={errorMessage(config.error)} onRetry={() => config.refetch()} />;
  if (!region || !config.data || !when) return <Loading />;

  const items = results.data ?? [];
  const open = (item: ListingSearchItem) => router.push({ pathname: '/listing/[id]', params: { id: item.id, ...windowIso(when) } });
  const isNow = !!initialWhen && when.start.getTime() <= initialWhen.start.getTime();
  const activeFilterCount = (filters.kind ? 1 : 0) + (filters.slot_type ? 1 : 0) + filters.amenities.length;

  // Available spots sorted by distance from the user (or from the map centre when location is off).
  const userCoords = userPos?.granted ? userPos.coords : null;
  const availableSpots = items
    .filter((item) => item.available_slots === undefined || item.available_slots === null || item.available_slots > 0)
    .map((item) => ({ ...item, distance_m: userCoords ? metresBetween(userCoords, item) : item.distance_m }))
    .sort((a, b) => a.distance_m - b.distance_m);
  const inZoneCount = userCoords ? availableSpots.filter((x) => x.distance_m <= NEARBY_ZONE_M).length : 0;
  // Results change as the map moves; keep the carousel index inside the (max 5) list.
  const nearestCount = Math.min(availableSpots.length, 5);
  const nearestIndex = Math.min(selectedNearestIndex, Math.max(0, nearestCount - 1));
  const activeNearest = availableSpots[nearestIndex];

  // Search and filters float on strong glass; controls inside are clay.
  const controls = (
    <SafeAreaView
      edges={['top']}
      style={{ paddingHorizontal: spacing.md, paddingTop: spacing.sm, gap: spacing.sm }}
      pointerEvents="box-none">
      <Glass
        tier="strong"
        rounded={radius.card}
        style={{ borderWidth: 1, borderColor: colors.glassBorder }}
        contentStyle={{ padding: spacing.sm + 2, gap: spacing.sm }}>
        <Row gap={spacing.xs}>
          <View style={[styles.search, { backgroundColor: colors.clayRecessed, boxShadow: shadows.clayPressed, overflow: 'hidden' }]}>
            <Ionicons name="search" size={17} color={colors.muted} />
            <TextInput
              value={query}
              onChangeText={setQuery}
              onSubmitEditing={runSearch}
              placeholder="Search any locality, landmark, or city…"
              placeholderTextColor={colors.muted}
              returnKeyType="search"
              accessibilityLabel="Search an area or address"
              style={{ flex: 1, minWidth: 0, color: colors.text, fontSize: 14, fontFamily: fonts.body, paddingVertical: 9 }}
            />
            {query.length > 0 ? (
              <Pressable
                onPress={() => {
                  setQuery('');
                  setSearchError(null);
                }}
                hitSlop={8}
                style={{ padding: 4 }}>
                <Ionicons name="close-circle" size={17} color={colors.muted} />
              </Pressable>
            ) : null}
            {isSearching ? <Loading label="Searching" /> : null}
          </View>
          <View style={{ position: 'relative' }}>
            <IconButton
              icon="options-outline"
              label="Filters"
              tone={activeFilterCount > 0 ? 'accent' : 'neutral'}
              onPress={() => setShowFilters(true)}
              size={44}
            />
            {activeFilterCount > 0 ? (
              <View
                pointerEvents="none"
                style={[
                  styles.filterBadge,
                  {
                    backgroundColor: colors.accent,
                    borderColor: colors.clay,
                  },
                ]}>
                <Text style={{ color: colors.onAccent, fontSize: 10, fontFamily: fonts.heading, lineHeight: 12 }}>
                  {activeFilterCount}
                </Text>
              </View>
            ) : null}
          </View>
          <IconButton
            icon={view === 'map' ? 'list' : 'map'}
            label={view === 'map' ? 'Show list' : 'Show map'}
            onPress={() => setView(view === 'map' ? 'list' : 'map')}
            size={44}
          />
        </Row>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={{ paddingVertical: 4, paddingHorizontal: 2, alignItems: 'center', gap: 6 }}>
          <Chip
            icon="navigate-outline"
            label="Near Me"
            selected={isNearUser}
            onPress={recenterToUser}
          />
          <Chip
            icon="time-outline"
            label={isNow ? `Now · ${duration(when.minutes)}` : `${dateTime(when.start.toISOString())} · ${duration(when.minutes)}`}
            selected={showWhen}
            onPress={() => setShowWhen((s) => !s)}
          />
          <Chip
            icon="flash-outline"
            label="EV Ready"
            selected={filters.slot_type === 'ev'}
            onPress={() => setFilters((f) => ({ ...f, slot_type: f.slot_type === 'ev' ? undefined : 'ev' }))}
          />
          <Chip
            icon="shield-checkmark-outline"
            label="Covered"
            selected={filters.amenities.includes('covered')}
            onPress={() => toggleAmenity('covered')}
          />
          {activeFilterCount > 0 ? (
            <Chip
              icon="close-circle-outline"
              label="Clear Filters"
              selected={false}
              onPress={() => setFilters({ amenities: [] })}
            />
          ) : null}
        </ScrollView>
        {showWhen ? (
          <View style={{ paddingHorizontal: spacing.xs, paddingBottom: spacing.xs }}>
            <WhenPicker config={config.data} value={when} onChange={setWhen} />
          </View>
        ) : null}
      </Glass>

      <Modal visible={showFilters} transparent animationType="slide" onRequestClose={() => setShowFilters(false)}>
        <View style={{ flex: 1, justifyContent: 'flex-end', backgroundColor: colors.scrim }}>
          <Pressable style={StyleSheet.absoluteFill} onPress={() => setShowFilters(false)} />
          <View style={{ maxHeight: '82%', width: '100%' }}>
            <Glass
              tier="strong"
              rounded={radius.card}
              style={{ borderBottomLeftRadius: 0, borderBottomRightRadius: 0 }}
              contentStyle={{ padding: spacing.xl, gap: spacing.lg }}>
              <Row style={{ justifyContent: 'space-between', alignItems: 'center' }}>
                <Row gap={spacing.sm}>
                  <IconOrb icon="options-outline" tone="accent" size={38} />
                  <View>
                    <Text variant="heading">Filters</Text>
                    <Text variant="small">
                      {activeFilterCount > 0 ? `${activeFilterCount} active filter${activeFilterCount > 1 ? 's' : ''}` : 'Refine parking spots'}
                    </Text>
                  </View>
                </Row>
                <Row gap={spacing.xs}>
                  {activeFilterCount > 0 ? (
                    <Button title="Reset" kind="ghost" size="sm" onPress={() => setFilters({ amenities: [] })} />
                  ) : null}
                  <IconButton icon="close" label="Close filters" onPress={() => setShowFilters(false)} size={38} />
                </Row>
              </Row>

              <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ gap: spacing.lg, paddingBottom: spacing.md }}>
                <View style={{ gap: spacing.xs }}>
                  <Text variant="label">Listing Type</Text>
                  <Row style={{ flexWrap: 'wrap' }} gap={spacing.xs}>
                    <Chip
                      label="All Types"
                      selected={!filters.kind}
                      onPress={() => setFilters((f) => ({ ...f, kind: undefined }))}
                    />
                    <Chip
                      label="Private Spot"
                      selected={filters.kind === 'private'}
                      onPress={() => setFilters((f) => ({ ...f, kind: f.kind === 'private' ? undefined : 'private' }))}
                    />
                    <Chip
                      label="Commercial Facility"
                      selected={filters.kind === 'commercial'}
                      onPress={() => setFilters((f) => ({ ...f, kind: f.kind === 'commercial' ? undefined : 'commercial' }))}
                    />
                  </Row>
                </View>

                <View style={{ gap: spacing.xs }}>
                  <Text variant="label">Vehicle & Power</Text>
                  <Row style={{ flexWrap: 'wrap' }} gap={spacing.xs}>
                    <Chip
                      label="All Vehicles"
                      selected={!filters.slot_type}
                      onPress={() => setFilters((f) => ({ ...f, slot_type: undefined }))}
                    />
                    <Chip
                      icon="flash-outline"
                      label="EV Charging Only"
                      selected={filters.slot_type === 'ev'}
                      onPress={() => setFilters((f) => ({ ...f, slot_type: f.slot_type === 'ev' ? undefined : 'ev' }))}
                    />
                  </Row>
                </View>

                <View style={{ gap: spacing.xs }}>
                  <Text variant="label">Amenities</Text>
                  <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
                    {config.data.amenities
                      .filter((a) => a !== 'ev_charging')
                      .map((a) => (
                        <Chip
                          key={a}
                          icon={AMENITY_ICONS[a] ?? 'checkmark-outline'}
                          label={titleCase(a)}
                          selected={filters.amenities.includes(a)}
                          onPress={() => toggleAmenity(a)}
                        />
                      ))}
                  </View>
                </View>
              </ScrollView>

              <Button
                title={items.length ? `Show ${items.length} spots` : 'Apply filters'}
                onPress={() => setShowFilters(false)}
              />
            </Glass>
          </View>
        </View>
      </Modal>

      {searchError ? <Banner tone="warning">{searchError}</Banner> : null}
      {items.length === 0 && !results.isFetching ? (
        <Banner tone="info">No parking spots found in this immediate area. Pan the map or search another locality.</Banner>
      ) : null}
      {locationDenied ? <Banner tone="info">Location permission is off. Use search or tap Near Me to enable GPS.</Banner> : null}
    </SafeAreaView>
  );

  if (view === 'list') {
    return (
      <Backdrop>
        <FlatList
          data={items}
          keyExtractor={(x) => x.id}
          ListHeaderComponent={<View style={{ marginHorizontal: -spacing.lg, marginBottom: spacing.sm }}>{controls}</View>}
          contentContainerStyle={{ padding: spacing.lg, paddingTop: 0, gap: spacing.lg, paddingBottom: 130 }}
          refreshing={results.isFetching}
          onRefresh={() => results.refetch()}
          ListEmptyComponent={
            results.isLoading ? (
              <Loading />
            ) : results.isError ? (
              <Banner tone="danger">{errorMessage(results.error)}</Banner>
            ) : (
              <EmptyState icon="car-outline" title="No spots here yet" body="Try zooming out or searching another locality." />
            )
          }
          renderItem={({ item }) => <ResultCard item={item} onPress={() => open(item)} />}
        />
      </Backdrop>
    );
  }

  const bottomDockOffset = Math.max(insets.bottom, 10) + 72;

  return (
    <View style={{ flex: 1, backgroundColor: colors.canvas }}>
      <BlurTargetView ref={mapTarget} style={StyleSheet.absoluteFill}>
        <ParkingMap
          ref={map}
          initialRegion={region}
          items={items}
          showsUserLocation={!locationDenied}
          userLocation={userPos?.granted ? { ...userPos.coords, heading: userPos.heading } : null}
          zoneRadiusM={NEARBY_ZONE_M}
          onRegionChange={setRegion}
          onSelect={open}
        />
      </BlurTargetView>
      <BlurTargetProvider target={mapTarget}>
        {controls}

        {/* Floating action controls (Center on my location) */}
        <View
          pointerEvents="box-none"
          style={[
            styles.fabContainer,
            { bottom: bottomDockOffset + (activeNearest && !hideNearestCard ? 130 : 16) },
          ]}>
          <IconButton
            icon="locate"
            label="Center on my location"
            tone="neutral"
            size={46}
            onPress={recenterToUser}
          />
        </View>

        {/* Floating Nearest Available Spot Card */}
        {activeNearest && !hideNearestCard ? (
          <View
            pointerEvents="box-none"
            style={[styles.nearestContainer, { bottom: bottomDockOffset }]}>
            <Glass
              tier="strong"
              rounded={24}
              style={{
                width: '100%',
                maxWidth: 480,
                borderRadius: 24,
                overflow: 'hidden',
                borderWidth: 1,
                borderColor: colors.glassBorder,
              }}
              contentStyle={{
                padding: spacing.md,
                gap: 6,
              }}>
              <Row style={{ justifyContent: 'space-between', alignItems: 'center' }}>
                <Row gap={6}>
                  <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: colors.success }} />
                  <Text style={{ fontFamily: fonts.heading, fontSize: 11, color: colors.success, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                    {inZoneCount > 0
                      ? `${inZoneCount} ${inZoneCount === 1 ? 'spot' : 'spots'} within ${distance(NEARBY_ZONE_M)} of you`
                      : 'Nearest Available Spot'}
                  </Text>
                </Row>
                <Row gap={6}>
                  <View style={{ backgroundColor: colors.accentSoft, borderRadius: radius.pill, paddingHorizontal: 8, paddingVertical: 3 }}>
                    <Text style={{ fontFamily: fonts.bodyBold, fontSize: 11, color: colors.accent }}>
                      📍 {distance(activeNearest.distance_m)} away
                    </Text>
                  </View>
                  {availableSpots.length > 1 ? (
                    <Text style={{ fontFamily: fonts.bodyMedium, fontSize: 11, color: colors.muted }}>
                      {nearestIndex + 1}/{nearestCount}
                    </Text>
                  ) : null}
                  <Pressable
                    hitSlop={8}
                    onPress={() => setHideNearestCard(true)}
                    style={{ padding: 2 }}>
                    <Ionicons name="close" size={16} color={colors.muted} />
                  </Pressable>
                </Row>
              </Row>

              <Row style={{ justifyContent: 'space-between', alignItems: 'center' }}>
                <Pressable
                  onPress={() => open(activeNearest)}
                  style={{ flex: 1, paddingRight: spacing.sm, gap: 2 }}>
                  <Text variant="heading" numberOfLines={1} style={{ fontSize: 15 }}>
                    {activeNearest.title}
                  </Text>
                  <Text variant="muted" numberOfLines={1} style={{ fontSize: 12 }}>
                    {activeNearest.address_line}
                  </Text>
                  <Row gap={8} style={{ marginTop: 2 }}>
                    <Text style={{ fontFamily: fonts.heading, fontSize: 15, color: colors.accent }}>
                      {money(activeNearest.hourly_rate, activeNearest.currency)}/hr
                    </Text>
                    <Text style={{ fontFamily: fonts.bodyMedium, fontSize: 12, color: colors.muted }}>
                      ● {activeNearest.available_slots ?? activeNearest.total_slots} free
                    </Text>
                  </Row>
                </Pressable>

                <Row gap={6}>
                  {availableSpots.length > 1 ? (
                    <Row gap={4}>
                      <IconButton
                        icon="chevron-back"
                        size={34}
                        label="Previous nearest"
                        disabled={nearestIndex === 0}
                        onPress={() => setSelectedNearestIndex(Math.max(0, nearestIndex - 1))}
                      />
                      <IconButton
                        icon="chevron-forward"
                        size={34}
                        label="Next nearest"
                        disabled={nearestIndex >= nearestCount - 1}
                        onPress={() => setSelectedNearestIndex(Math.min(nearestCount - 1, nearestIndex + 1))}
                      />
                    </Row>
                  ) : null}
                  <Button
                    title="Book Spot"
                    size="sm"
                    onPress={() => open(activeNearest)}
                    style={{ minWidth: 92 }}
                  />
                </Row>
              </Row>
            </Glass>
          </View>
        ) : null}

        {/* Small in-view counter when nearest card is dismissed or no available spots */}
        {(!activeNearest || hideNearestCard) ? (
          <View style={[styles.status, { bottom: bottomDockOffset + 8 }]} pointerEvents="box-none">
            <Glass tier="strong" rounded={radius.pill} contentStyle={{ paddingHorizontal: spacing.lg, paddingVertical: spacing.sm }}>
              <Text variant="small" style={{ color: results.isError ? colors.danger : colors.text }}>
                {results.isFetching
                  ? 'Searching…'
                  : results.isError
                    ? errorMessage(results.error)
                    : items.length
                      ? `${items.length} spots in view`
                      : 'No spots in this area'}
              </Text>
            </Glass>
          </View>
        ) : null}
      </BlurTargetProvider>
    </View>
  );
}

function ResultCard({ item, onPress }: { item: ListingSearchItem; onPress: () => void }) {
  const { colors } = useTheme();
  const free = item.available_slots ?? item.total_slots;
  const full = item.available_slots === 0;
  return (
    <Card onPress={onPress} accessibilityLabel={`${item.title}, ${money(item.hourly_rate, item.currency)} per hour`} padded={false}>
      {item.cover_photo_url ? (
        <Image
          source={{ uri: item.cover_photo_url }}
          style={{ height: 150, margin: spacing.sm, borderRadius: radius.md }}
          contentFit="cover"
          accessibilityIgnoresInvertColors
        />
      ) : null}
      <View style={{ padding: spacing.lg, paddingTop: item.cover_photo_url ? spacing.sm : spacing.lg, gap: spacing.sm }}>
        <Row style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <View style={{ flex: 1, gap: 2 }}>
            <Text variant="heading" numberOfLines={1}>
              {item.title}
            </Text>
            <Text variant="muted" numberOfLines={1}>
              {item.address_line} · {distance(item.distance_m)}
            </Text>
          </View>
          <View style={{ alignItems: 'flex-end' }}>
            <Text variant="heading" style={{ color: colors.accent }}>
              {money(item.hourly_rate, item.currency)}
            </Text>
            <Text variant="small">per hour</Text>
          </View>
        </Row>
        <Meter value={free} total={item.total_slots} accessibilityLabel={`${free} of ${item.total_slots} slots free`} />
        <Text variant="small">
          {full ? 'Full for this time' : `${free} of ${item.total_slots} free`} · {titleCase(item.kind)}
        </Text>
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  search: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 6, borderRadius: radius.control, paddingHorizontal: 12 },
  status: { position: 'absolute', alignSelf: 'center' },
  fabContainer: { position: 'absolute', right: spacing.md, alignItems: 'flex-end' },
  nearestContainer: { position: 'absolute', left: spacing.md, right: spacing.md, alignItems: 'center' },
  filterBadge: {
    position: 'absolute',
    top: -2,
    right: -2,
    minWidth: 18,
    height: 18,
    borderRadius: 9,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 4,
    borderWidth: 1.5,
  },
});

