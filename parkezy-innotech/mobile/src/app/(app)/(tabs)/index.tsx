import Ionicons from '@expo/vector-icons/Ionicons';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { BlurTargetView } from 'expo-blur';
import { Image } from 'expo-image';
import { router } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import { FlatList, Modal, Pressable, ScrollView, StyleSheet, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { errorMessage } from '@/api/client';
import { discoveryApi, type SearchParams } from '@/api/endpoints';
import type { ListingSearchItem } from '@/api/types';
import { keys, useConfig } from '@/hooks/queries';
import { currentOrDefault, geocode } from '@/services/location';
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
  const config = useConfig();
  const map = useRef<ParkingMapHandle>(null);
  const mapTarget = useRef<View | null>(null);
  const [region, setRegion] = useState<Region | null>(null);
  const [locationDenied, setLocationDenied] = useState(false);
  const [view, setView] = useState<'map' | 'list'>('map');
  const [query, setQuery] = useState('');
  const [searchError, setSearchError] = useState<string | null>(null);
  const [filters, setFilters] = useState<{ kind?: string; amenities: string[]; slot_type?: string }>({ amenities: [] });
  const [showFilters, setShowFilters] = useState(false);
  const [chosenWhen, setWhen] = useState<Window | null>(null);
  const [showWhen, setShowWhen] = useState(false);

  useEffect(() => {
    currentOrDefault().then(({ coords, granted }) => {
      setLocationDenied(!granted);
      setRegion({ ...coords, latitudeDelta: 0.06, longitudeDelta: 0.06 });
    });
  }, []);

  // Until the user picks a time, search "now" for the default duration (computed once per config load).
  const initialWhen = useMemo(() => (config.data ? defaultWindow(config.data) : null), [config.data]);
  const when = chosenWhen ?? initialWhen;

  const params: SearchParams | null = useMemo(() => {
    if (!region || !config.data || !when) return null;
    return {
      latitude: Number(region.latitude.toFixed(4)),
      longitude: Number(region.longitude.toFixed(4)),
      radius_km: Number(radiusFor(region, config.data.search_max_radius_km).toFixed(1)),
      kind: filters.kind,
      amenities: filters.amenities,
      slot_type: filters.slot_type,
      ...windowIso(when),
    };
  }, [region, config.data, when, filters]);

  const results = useQuery({
    queryKey: keys.search(params ?? {}),
    queryFn: ({ signal }) => discoveryApi.search(params!, signal),
    enabled: !!params,
    placeholderData: keepPreviousData,
  });

  const runSearch = async () => {
    setSearchError(null);
    if (!query.trim()) return;
    try {
      const found = await geocode(query.trim());
      if (!found) return setSearchError('We couldn’t find that place');
      const next = { ...found, latitudeDelta: 0.04, longitudeDelta: 0.04 };
      map.current?.animateTo(next);
      setRegion(next);
    } catch {
      setSearchError('Search is unavailable right now');
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

  // Search and filters float on strong glass; the controls inside are clay.
  const controls = (
    <SafeAreaView edges={['top']} style={{ paddingHorizontal: spacing.md, gap: spacing.sm }} pointerEvents="box-none">
      <Glass tier="strong" rounded={radius.card} contentStyle={{ padding: spacing.sm + 2, gap: spacing.sm }}>
        <Row gap={spacing.xs}>
          <View style={[styles.search, { backgroundColor: colors.clayRecessed, boxShadow: shadows.clayPressed }]}>
            <Ionicons name="search" size={17} color={colors.muted} />
            <TextInput
              value={query}
              onChangeText={setQuery}
              onSubmitEditing={runSearch}
              placeholder="Where are you going?"
              placeholderTextColor={colors.muted}
              returnKeyType="search"
              accessibilityLabel="Search an area or address"
              style={{ flex: 1, minWidth: 0, color: colors.text, fontSize: 15, fontFamily: fonts.body, paddingVertical: 10 }}
            />
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
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingVertical: 4, paddingHorizontal: 2, alignItems: 'center' }}>
          <Chip
            icon="time-outline"
            label={isNow ? `Now · ${duration(when.minutes)}` : `${dateTime(when.start.toISOString())} · ${duration(when.minutes)}`}
            selected={showWhen}
            onPress={() => setShowWhen((s) => !s)}
          />
          <Chip
            icon="location-outline"
            label="Delhi NCR / Ghaziabad"
            selected={!!region && Math.abs(region.latitude - 28.6412) < 0.5}
            onPress={() => {
              const ncr = { latitude: 28.6412, longitude: 77.3712, latitudeDelta: 0.10, longitudeDelta: 0.10 };
              map.current?.animateTo(ncr);
              setRegion(ncr);
            }}
          />
          <Chip
            icon="location-outline"
            label="Bengaluru"
            selected={!!region && Math.abs(region.latitude - 12.9716) < 0.5}
            onPress={() => {
              const blr = { latitude: 12.9716, longitude: 77.5946, latitudeDelta: 0.10, longitudeDelta: 0.10 };
              map.current?.animateTo(blr);
              setRegion(blr);
            }}
          />
          {activeFilterCount > 0 ? (
            <Chip
              icon="close-circle-outline"
              label="Clear"
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
        <Banner tone="info">No spots at your current GPS spot. Tap &quot;Delhi NCR / Ghaziabad&quot; or &quot;Bengaluru&quot; above to view 200+ spots!</Banner>
      ) : null}
      {locationDenied ? <Banner tone="info">Location is off, so we’re showing the city centre. Search an area instead.</Banner> : null}
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
              <EmptyState icon="car-outline" title="No spots here yet" body="Try a wider area or a different time." />
            )
          }
          renderItem={({ item }) => <ResultCard item={item} onPress={() => open(item)} />}
        />
      </Backdrop>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.canvas }}>
      <BlurTargetView ref={mapTarget} style={StyleSheet.absoluteFill}>
        <ParkingMap
          ref={map}
          initialRegion={region}
          items={items}
          showsUserLocation={!locationDenied}
          onRegionChange={setRegion}
          onSelect={open}
        />
      </BlurTargetView>
      <BlurTargetProvider target={mapTarget}>
        {controls}
        <View style={styles.status} pointerEvents="none">
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
  status: { position: 'absolute', bottom: 84, alignSelf: 'center' },
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
