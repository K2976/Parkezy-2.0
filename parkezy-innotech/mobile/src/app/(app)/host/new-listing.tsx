import Ionicons from '@expo/vector-icons/Ionicons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, View } from 'react-native';

import { ApiError, errorMessage } from '@/api/client';
import { hostApi } from '@/api/endpoints';
import type { ListingKind } from '@/api/types';
import { useAuth } from '@/auth/AuthProvider';
import { useConfig } from '@/hooks/queries';
import { type Coords, currentOrDefault, reverseGeocode } from '@/services/location';
import { Banner, Button, Card, Chip, ErrorState, Loading, PriceRow, Row, Screen, Section, Text, TextField } from '@/ui/components';
import { draftToInput, emptyDraft, type ListingDraft, ListingFields, validateDraft } from '@/ui/ListingForm';
import type { MapRegion as Region } from '@/ui/ParkingMap';
import { PhotoPicker, type UploadedPhoto } from '@/ui/PhotoPicker';
import { PinPickerMap } from '@/ui/PinPickerMap';
import { fonts, radius, spacing, useTheme } from '@/ui/theme';
import { money, titleCase } from '@/utils/format';

const STEPS = ['Location & Price', 'Photos (Min 3)', 'Details', 'Review'] as const;
const MIN_REQUIRED_PHOTOS = 3;

export default function NewListing() {
  const { user } = useAuth();
  const { colors: c, shadows } = useTheme();
  const config = useConfig();
  const queryClient = useQueryClient();
  const [step, setStep] = useState(0);
  const [pin, setPin] = useState<Coords | null>(null);
  const [region, setRegion] = useState<Region | null>(null);
  const [address, setAddress] = useState({ address_line: '', city: '', postal_code: '' });
  const [showManualCoords, setShowManualCoords] = useState(false);
  const [manualLat, setManualLat] = useState('');
  const [manualLng, setManualLng] = useState('');
  const [gpsLoading, setGpsLoading] = useState(false);
  const [photos, setPhotos] = useState<UploadedPhoto[]>([]);
  const [draft, setDraft] = useState<ListingDraft>(() => ({
    ...emptyDraft(),
    hourly_rate: '40', // Sensible default suggested price
  }));
  const [kind, setKind] = useState<ListingKind>('private');
  const [slotCount, setSlotCount] = useState('1');
  const [slotPrefix, setSlotPrefix] = useState('P');
  const [evCount, setEvCount] = useState('0');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const geocodeSeq = useRef(0);

  const movePin = useCallback(async (coords: Coords) => {
    setPin(coords);
    setManualLat(coords.latitude.toFixed(6));
    setManualLng(coords.longitude.toFixed(6));
    const seq = ++geocodeSeq.current;
    try {
      const found = await reverseGeocode(coords);
      if (seq === geocodeSeq.current) {
        setAddress((a) => ({
          ...a,
          address_line: a.address_line || found.address,
          city: a.city || found.city,
          postal_code: a.postal_code || found.postalCode,
        }));
      }
    } catch {
      // Address can still be typed manually.
    }
  }, []);

  const useGpsLocation = async () => {
    setGpsLoading(true);
    try {
      const { coords } = await currentOrDefault();
      setRegion({ ...coords, latitudeDelta: 0.005, longitudeDelta: 0.005 });
      await movePin(coords);
    } finally {
      setGpsLoading(false);
    }
  };

  const applyManualCoords = () => {
    const lat = parseFloat(manualLat);
    const lng = parseFloat(manualLng);
    if (!isNaN(lat) && !isNaN(lng) && lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180) {
      const coords = { latitude: lat, longitude: lng };
      setRegion({ ...coords, latitudeDelta: 0.005, longitudeDelta: 0.005 });
      movePin(coords);
    }
  };

  useEffect(() => {
    currentOrDefault().then(({ coords }) => {
      setRegion({ ...coords, latitudeDelta: 0.01, longitudeDelta: 0.01 });
      movePin(coords);
    });
  }, [movePin]);

  const create = useMutation({
    mutationFn: async (publish: boolean) => {
      const total = Number(slotCount);
      const ev = Number(evCount);
      const slots = Array.from({ length: total }, (_, i) => ({
        label: `${slotPrefix.trim() || 'P'}${i + 1}`,
        slot_type: i < ev ? 'ev' : 'standard',
      }));
      return hostApi.createListing({
        ...draftToInput(draft),
        kind,
        ...address,
        postal_code: address.postal_code || null,
        latitude: pin!.latitude,
        longitude: pin!.longitude,
        slots,
        photo_upload_ids: photos.map((p) => p.uploadId!).filter(Boolean),
        publish,
      });
    },
    onSuccess: (listing) => {
      queryClient.invalidateQueries({ queryKey: ['host'] });
      queryClient.invalidateQueries({ queryKey: ['listings'] });
      router.replace({ pathname: '/host/listing/[id]', params: { id: listing.id } });
    },
    onError: (e) => e instanceof ApiError && setErrors(e.fieldErrors),
  });

  if (config.isError) return <ErrorState message={errorMessage(config.error)} onRetry={() => config.refetch()} />;
  if (!config.data || !region) return <Loading />;
  const cfg = config.data;
  const uploading = photos.some((p) => !p.uploadId && !p.failed);
  const readyPhotos = photos.filter((p) => p.uploadId).length;
  const minPhotos = Math.max(MIN_REQUIRED_PHOTOS, cfg.min_listing_photos || MIN_REQUIRED_PHOTOS);

  const validateStep = (): boolean => {
    let next: Record<string, string> = {};
    if (step === 0) {
      if (!pin) next.pin = 'Drop the pin on your parking entrance';
      if (address.address_line.trim().length < 3) next.address_line = 'Enter the street address';
      if (address.city.trim().length < 2) next.city = 'Enter the city';
      const price = parseFloat(draft.hourly_rate);
      if (isNaN(price) || price <= 0) next.hourly_rate = 'Enter a valid hourly price (e.g. 40)';
    }
    if (step === 1 && readyPhotos < minPhotos) {
      next.photos = `Please upload at least ${minPhotos} photos of the slot (entrance, bay, landmark)`;
    }
    if (step === 2) {
      next = validateDraft(draft);
      const count = Number(slotCount);
      if (!Number.isInteger(count) || count < 1 || count > cfg.max_slots_per_listing)
        next.slots = `Between 1 and ${cfg.max_slots_per_listing} slots`;
      const ev = Number(evCount);
      if (!Number.isInteger(ev) || ev < 0 || ev > count) next.ev = 'Cannot exceed the number of slots';
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  return (
    <Screen>
      {/* Step Progress Bar */}
      <Row style={{ marginBottom: spacing.xl }} gap={spacing.sm}>
        {STEPS.map((label, i) => (
          <View key={label} style={{ flex: 1, gap: 6 }} accessibilityLabel={`Step ${i + 1} of ${STEPS.length}: ${label}${i === step ? ', current' : ''}`}>
            <View style={{ height: 10, borderRadius: radius.pill, backgroundColor: c.clayRecessed, boxShadow: shadows.clayPressed, overflow: 'hidden' }}>
              {i <= step ? <View style={{ flex: 1, borderRadius: radius.pill, backgroundColor: c.accent }} /> : null}
            </View>
            <Text variant="small" style={i === step ? { color: c.accent, fontFamily: fonts.bodyBold } : undefined} numberOfLines={1}>
              {label}
            </Text>
          </View>
        ))}
      </Row>

      {/* STEP 0: Location (GPS + Map + Manual) & Pricing */}
      {step === 0 ? (
        <View style={{ gap: spacing.md }}>
          <Section title="1. Spot Location">
            {/* Quick GPS Location Button */}
            <Card tier="light">
              <Row style={{ justifyContent: 'space-between', alignItems: 'center' }}>
                <View style={{ flex: 1, gap: 2 }}>
                  <Text style={{ fontFamily: fonts.bodyBold }}>Auto-detect Location via GPS</Text>
                  <Text variant="small" style={{ color: c.muted }}>
                    {pin ? `Lat: ${pin.latitude.toFixed(4)}, Lng: ${pin.longitude.toFixed(4)}` : 'Uses your phone GPS'}
                  </Text>
                </View>
                <Button
                  title={gpsLoading ? 'Locating…' : 'Use Current GPS'}
                  icon="navigate-outline"
                  kind="secondary"
                  size="sm"
                  onPress={useGpsLocation}
                  disabled={gpsLoading}
                />
              </Row>
            </Card>

            {/* Interactive Map Pin Drop */}
            <View style={{ height: 240, borderRadius: radius.card, overflow: 'hidden', marginVertical: spacing.xs, boxShadow: shadows.clayRaised }}>
              <PinPickerMap initialRegion={region} pin={pin} onMove={movePin} />
            </View>
            <Text variant="small" style={{ color: c.muted }}>
              Pan or drag the map so the pin sits exactly at your driveway or facility gate.
            </Text>
            {errors.pin ? <Banner tone="danger">{errors.pin}</Banner> : null}

            {/* Manual Location Input Form */}
            <TextField
              label="Street address"
              value={address.address_line}
              onChangeText={(v) => setAddress((a) => ({ ...a, address_line: v }))}
              placeholder="e.g. 14 Block B, Green Park"
              error={errors.address_line}
            />

            <Row style={{ alignItems: 'flex-start' }} gap={spacing.md}>
              <View style={{ flex: 2 }}>
                <TextField
                  label="City"
                  value={address.city}
                  onChangeText={(v) => setAddress((a) => ({ ...a, city: v }))}
                  placeholder="e.g. Ghaziabad or Delhi"
                  error={errors.city}
                />
              </View>
              <View style={{ flex: 1 }}>
                <TextField
                  label="PIN code"
                  value={address.postal_code}
                  onChangeText={(v) => setAddress((a) => ({ ...a, postal_code: v }))}
                  keyboardType="number-pad"
                  placeholder="201010"
                />
              </View>
            </Row>

            {/* Manual Coordinates Toggle */}
            <Pressable onPress={() => setShowManualCoords(!showManualCoords)} style={{ marginVertical: spacing.xs }}>
              <Row gap={spacing.xs} style={{ alignItems: 'center' }}>
                <Ionicons name={showManualCoords ? 'chevron-up' : 'options-outline'} size={16} color={c.accent} />
                <Text variant="small" style={{ color: c.accent, fontFamily: fonts.bodyBold }}>
                  {showManualCoords ? 'Hide manual GPS coordinates' : 'Enter manual GPS coordinates (Lat / Lng)'}
                </Text>
              </Row>
            </Pressable>

            {showManualCoords ? (
              <Card tier="light" style={{ gap: spacing.sm }}>
                <Row gap={spacing.sm}>
                  <View style={{ flex: 1 }}>
                    <TextField label="Latitude" value={manualLat} onChangeText={setManualLat} keyboardType="numeric" placeholder="28.6139" />
                  </View>
                  <View style={{ flex: 1 }}>
                    <TextField label="Longitude" value={manualLng} onChangeText={setManualLng} keyboardType="numeric" placeholder="77.2090" />
                  </View>
                </Row>
                <Button title="Apply Coordinates" kind="ghost" size="sm" onPress={applyManualCoords} />
              </Card>
            ) : null}
          </Section>

          {/* Pricing Upfront */}
          <Section title="2. Pricing">
            <TextField
              label={`Hourly Price (${cfg.currency}/hour)`}
              value={draft.hourly_rate}
              onChangeText={(v) => setDraft((d) => ({ ...d, hourly_rate: v }))}
              keyboardType="decimal-pad"
              placeholder="40"
              error={errors.hourly_rate}
            />
            <Text variant="small" style={{ color: c.muted }}>
              💡 Recommended rate: ₹40/hr based on nearby listings in Delhi NCR / Ghaziabad
            </Text>
            <TextField
              label={`Daily Maximum Cap (${cfg.currency}, optional)`}
              value={draft.daily_cap}
              onChangeText={(v) => setDraft((d) => ({ ...d, daily_cap: v }))}
              keyboardType="decimal-pad"
              placeholder="e.g. 350"
            />
          </Section>
        </View>
      ) : null}

      {/* STEP 1: Photos (Minimum 3 required) */}
      {step === 1 ? (
        <View style={{ gap: spacing.md }}>
          <Text variant="title">Add Spot Photos</Text>
          <Text variant="muted">
            Drivers rely on photos to locate your entrance and slot. Please provide at least <Text style={{ fontFamily: fonts.bodyBold, color: c.text }}>{minPhotos} clear photos</Text>.
          </Text>

          {/* Visual Checklist for required 3 photos */}
          <Card tier="light" style={{ gap: spacing.sm }}>
            <Text variant="label">Required Photo Checklist (Min 3)</Text>
            <Row gap={spacing.sm} style={{ alignItems: 'center' }}>
              <Ionicons name={readyPhotos >= 1 ? 'checkmark-circle' : 'camera-outline'} size={20} color={readyPhotos >= 1 ? c.accent : c.muted} />
              <Text variant="small" style={{ flex: 1 }}>1. Entrance / Gate (road view to guide arriving drivers)</Text>
            </Row>
            <Row gap={spacing.sm} style={{ alignItems: 'center' }}>
              <Ionicons name={readyPhotos >= 2 ? 'checkmark-circle' : 'camera-outline'} size={20} color={readyPhotos >= 2 ? c.accent : c.muted} />
              <Text variant="small" style={{ flex: 1 }}>2. Designated Parking Slot / Bay (shows width and ground)</Text>
            </Row>
            <Row gap={spacing.sm} style={{ alignItems: 'center' }}>
              <Ionicons name={readyPhotos >= 3 ? 'checkmark-circle' : 'camera-outline'} size={20} color={readyPhotos >= 3 ? c.accent : c.muted} />
              <Text variant="small" style={{ flex: 1 }}>3. Landmark / Approach View (helps identify the property)</Text>
            </Row>
          </Card>

          {/* Photo status badge */}
          <Banner tone={readyPhotos >= minPhotos ? 'success' : 'warning'}>
            {readyPhotos >= minPhotos
              ? `✓ ${readyPhotos} photos uploaded and ready!`
              : `⚠️ ${readyPhotos} of ${minPhotos} required photos uploaded (${minPhotos - readyPhotos} more needed)`}
          </Banner>

          <PhotoPicker photos={photos} onChange={setPhotos} max={cfg.max_listing_photos} purpose="listing_photo" />
          {errors.photos ? <Banner tone="danger">{errors.photos}</Banner> : null}
        </View>
      ) : null}

      {/* STEP 2: Details & Slots */}
      {step === 2 ? (
        <View style={{ gap: spacing.md }}>
          {user?.is_commercial_host ? (
            <Section title="Type">
              <Row>
                {(['private', 'commercial'] as const).map((k) => (
                  <Chip key={k} label={titleCase(k)} selected={kind === k} onPress={() => setKind(k)} />
                ))}
              </Row>
            </Section>
          ) : null}
          <ListingFields draft={draft} onChange={setDraft} errors={errors} config={cfg} />
          <Section title="Slots">
            <Row style={{ alignItems: 'flex-start' }} gap={spacing.md}>
              <View style={{ flex: 1 }}>
                <TextField label="How many" value={slotCount} onChangeText={setSlotCount} keyboardType="number-pad" error={errors.slots} />
              </View>
              <View style={{ flex: 1 }}>
                <TextField label="EV charging" value={evCount} onChangeText={setEvCount} keyboardType="number-pad" error={errors.ev} />
              </View>
              <View style={{ flex: 1 }}>
                <TextField label="Label prefix" value={slotPrefix} onChangeText={setSlotPrefix} maxLength={8} autoCapitalize="characters" />
              </View>
            </Row>
            <Text variant="small" style={{ color: c.muted }}>You can rename slots and set per-slot prices later.</Text>
          </Section>
        </View>
      ) : null}

      {/* STEP 3: Review & Publish */}
      {step === 3 ? (
        <Card style={{ gap: spacing.sm }}>
          <Text variant="heading">{draft.title}</Text>
          <Text variant="muted">
            {address.address_line}, {address.city} {address.postal_code ? `(${address.postal_code})` : ''}
          </Text>
          <PriceRow label="Price" value={`${money(draft.hourly_rate || 0, cfg.currency)}/h`} />
          {draft.daily_cap ? <PriceRow label="Daily max" value={money(draft.daily_cap, cfg.currency)} /> : null}
          <PriceRow label="Total Slots" value={slotCount} />
          {Number(evCount) > 0 ? <PriceRow label="EV Slots" value={evCount} /> : null}
          <PriceRow label="Verified Photos" value={`${readyPhotos} photos`} />
          <PriceRow label="Booking Mode" value={draft.auto_accept ? 'Instant Booking' : 'Host Approves Requests'} />
          <PriceRow label="Hours" value={draft.is_24h ? 'Open 24 hours' : `${draft.open_time}–${draft.close_time}`} />
        </Card>
      ) : null}

      {create.error ? <Banner tone="danger">{errorMessage(create.error)}</Banner> : null}

      {/* Navigation Buttons */}
      <View style={{ gap: spacing.sm, marginTop: spacing.xl }}>
        {step < STEPS.length - 1 ? (
          <Button
            title={step === 1 && readyPhotos < minPhotos ? `Add ${minPhotos - readyPhotos} more photo(s) to continue` : 'Continue'}
            disabled={uploading || (step === 1 && readyPhotos < minPhotos)}
            onPress={() => validateStep() && setStep(step + 1)}
          />
        ) : (
          <>
            <Button title="Publish Listing" onPress={() => create.mutate(true)} loading={create.isPending && create.variables === true} />
            <Button title="Save as Draft" kind="secondary" onPress={() => create.mutate(false)} loading={create.isPending && create.variables === false} />
          </>
        )}
        {step > 0 ? <Button title="Back" kind="ghost" onPress={() => setStep(step - 1)} /> : null}
      </View>
    </Screen>
  );
}
