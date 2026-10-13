import { useMutation, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { View } from 'react-native';

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

const STEPS = ['Location', 'Photos', 'Details', 'Review'] as const;

export default function NewListing() {
  const { user } = useAuth();
  const { colors: c, shadows } = useTheme();
  const config = useConfig();
  const queryClient = useQueryClient();
  const [step, setStep] = useState(0);
  const [pin, setPin] = useState<Coords | null>(null);
  const [region, setRegion] = useState<Region | null>(null);
  const [address, setAddress] = useState({ address_line: '', city: '', postal_code: '' });
  const [photos, setPhotos] = useState<UploadedPhoto[]>([]);
  const [draft, setDraft] = useState<ListingDraft>(emptyDraft);
  const [kind, setKind] = useState<ListingKind>('private');
  const [slotCount, setSlotCount] = useState('1');
  const [slotPrefix, setSlotPrefix] = useState('P');
  const [evCount, setEvCount] = useState('0');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const geocodeSeq = useRef(0);

  const movePin = useCallback(async (coords: Coords) => {
    setPin(coords);
    const seq = ++geocodeSeq.current;
    try {
      const found = await reverseGeocode(coords);
      if (seq === geocodeSeq.current) setAddress({ address_line: found.address, city: found.city, postal_code: found.postalCode });
    } catch {
      // Address can still be typed manually.
    }
  }, []);

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

  const validateStep = (): boolean => {
    let next: Record<string, string> = {};
    if (step === 0) {
      if (!pin) next.pin = 'Drop the pin on your spot';
      if (address.address_line.trim().length < 3) next.address_line = 'Enter the street address';
      if (address.city.trim().length < 2) next.city = 'Enter the city';
    }
    if (step === 1 && readyPhotos < cfg.min_listing_photos) next.photos = `Add at least ${cfg.min_listing_photos} photo(s)`;
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
      {/* Progress: recessed clay track, completed steps filled with solid accent. */}
      <Row style={{ marginBottom: spacing.xl }} gap={spacing.sm}>
        {STEPS.map((label, i) => (
          <View key={label} style={{ flex: 1, gap: 6 }} accessibilityLabel={`Step ${i + 1} of ${STEPS.length}: ${label}${i === step ? ', current' : ''}`}>
            <View style={{ height: 10, borderRadius: radius.pill, backgroundColor: c.clayRecessed, boxShadow: shadows.clayPressed, overflow: 'hidden' }}>
              {i <= step ? <View style={{ flex: 1, borderRadius: radius.pill, backgroundColor: c.accent }} /> : null}
            </View>
            <Text variant="small" style={i === step ? { color: c.accent, fontFamily: fonts.bodyBold } : undefined}>
              {label}
            </Text>
          </View>
        ))}
      </Row>

      {step === 0 ? (
        <>
          <Text variant="muted">Move the map so the pin sits exactly on the entrance.</Text>
          <View style={{ height: 260, borderRadius: radius.card, overflow: 'hidden', marginVertical: spacing.md, boxShadow: shadows.clayRaised }}>
            <PinPickerMap initialRegion={region} pin={pin} onMove={movePin} />
          </View>
          {errors.pin ? <Banner tone="danger">{errors.pin}</Banner> : null}
          <TextField label="Street address" value={address.address_line} onChangeText={(v) => setAddress((a) => ({ ...a, address_line: v }))} error={errors.address_line} />
          <Row style={{ alignItems: 'flex-start' }} gap={spacing.md}>
            <View style={{ flex: 2 }}>
              <TextField label="City" value={address.city} onChangeText={(v) => setAddress((a) => ({ ...a, city: v }))} error={errors.city} />
            </View>
            <View style={{ flex: 1 }}>
              <TextField label="PIN code" value={address.postal_code} onChangeText={(v) => setAddress((a) => ({ ...a, postal_code: v }))} keyboardType="number-pad" />
            </View>
          </Row>
        </>
      ) : null}

      {step === 1 ? (
        <>
          <Text variant="muted" style={{ marginBottom: spacing.md }}>
            Clear photos of the entrance and the space help drivers find you. {cfg.min_listing_photos}–{cfg.max_listing_photos} photos.
          </Text>
          <PhotoPicker photos={photos} onChange={setPhotos} max={cfg.max_listing_photos} purpose="listing_photo" />
          {errors.photos ? <Banner tone="danger">{errors.photos}</Banner> : null}
        </>
      ) : null}

      {step === 2 ? (
        <>
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
            <Text variant="small">You can rename slots and set per-slot prices later.</Text>
          </Section>
        </>
      ) : null}

      {step === 3 ? (
        <Card>
          <Text variant="heading">{draft.title}</Text>
          <Text variant="muted">
            {address.address_line}, {address.city}
          </Text>
          <PriceRow label="Price" value={`${money(draft.hourly_rate || 0, cfg.currency)}/h`} />
          {draft.daily_cap ? <PriceRow label="Daily max" value={money(draft.daily_cap, cfg.currency)} /> : null}
          <PriceRow label="Slots" value={slotCount} />
          <PriceRow label="Photos" value={String(readyPhotos)} />
          <PriceRow label="Booking" value={draft.auto_accept ? 'Instant' : 'You approve'} />
          <PriceRow label="Hours" value={draft.is_24h ? '24 hours' : `${draft.open_time}–${draft.close_time}`} />
        </Card>
      ) : null}

      {create.error ? <Banner tone="danger">{errorMessage(create.error)}</Banner> : null}
      <View style={{ gap: spacing.sm, marginTop: spacing.xl }}>
        {step < STEPS.length - 1 ? (
          <Button title="Continue" disabled={uploading} onPress={() => validateStep() && setStep(step + 1)} />
        ) : (
          <>
            <Button title="Publish" onPress={() => create.mutate(true)} loading={create.isPending && create.variables === true} />
            <Button title="Save as draft" kind="secondary" onPress={() => create.mutate(false)} loading={create.isPending && create.variables === false} />
          </>
        )}
        {step > 0 ? <Button title="Back" kind="ghost" onPress={() => setStep(step - 1)} /> : null}
      </View>
    </Screen>
  );
}
