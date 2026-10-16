import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Image } from 'expo-image';
import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { View } from 'react-native';

import { ApiError, errorMessage } from '@/api/client';
import { hostApi } from '@/api/endpoints';
import type { Listing, ListingStatus } from '@/api/types';
import { keys, useConfig } from '@/hooks/queries';
import {
  Banner,
  Button,
  Card,
  Divider,
  ErrorState,
  IconButton,
  IconOrb,
  Loading,
  Pill,
  Row,
  Screen,
  Section,
  StatusText,
  Text,
  TextField,
  Toggle,
} from '@/ui/components';
import { draftFrom, draftToInput, type ListingDraft, ListingFields, validateDraft } from '@/ui/ListingForm';
import { confirmAction } from '@/ui/dialogs';
import { PhotoPicker, type UploadedPhoto } from '@/ui/PhotoPicker';
import { fonts, radius, spacing, useTheme } from '@/ui/theme';
import { money, titleCase } from '@/utils/format';

type Handlers = {
  onSaved: (l: Listing) => void;
  setNotice: (m: string | null) => void;
  setErrors: (e: Record<string, string>) => void;
};

function useListingMutation<T>(fn: (arg: T) => Promise<Listing>, h: Handlers, message?: string) {
  return useMutation({
    mutationFn: fn,
    onMutate: () => h.setNotice(null),
    onSuccess: (updated) => {
      h.onSaved(updated);
      if (message) h.setNotice(message);
    },
    onError: (e) => e instanceof ApiError && h.setErrors(e.fieldErrors),
  });
}

export default function ManageListing() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { shadows } = useTheme();
  const config = useConfig();
  const queryClient = useQueryClient();
  const listing = useQuery({ queryKey: keys.hostListing(id), queryFn: () => hostApi.listing(id) });
  const [editedDraft, setDraft] = useState<ListingDraft | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [newPhotos, setNewPhotos] = useState<UploadedPhoto[]>([]);
  const [newSlot, setNewSlot] = useState('');
  const [notice, setNotice] = useState<string | null>(null);

  const draft = editedDraft ?? (listing.data ? draftFrom(listing.data) : null);

  const onSaved = (updated: Listing) => {
    queryClient.setQueryData(keys.hostListing(id), updated);
    queryClient.invalidateQueries({ queryKey: keys.hostListings });
    queryClient.invalidateQueries({ queryKey: ['listings'] });
  };
  const handlers = { onSaved, setNotice, setErrors };

  const save = useListingMutation((d: ListingDraft) => hostApi.updateListing(id, draftToInput(d)), handlers, 'Changes saved');
  const setStatus = useListingMutation((status: ListingStatus) => hostApi.updateListing(id, { status }), handlers);
  const addSlot = useListingMutation((label: string) => hostApi.addSlots(id, [{ label }]), handlers);
  const toggleSlot = useListingMutation((s: { id: string; active: boolean }) => hostApi.updateSlot(id, s.id, { is_active: s.active }), handlers);
  const removeSlot = useListingMutation((slotId: string) => hostApi.deleteSlot(id, slotId), handlers);
  const removePhoto = useListingMutation((mediaId: string) => hostApi.removePhoto(id, mediaId), handlers);
  const attachPhotos = useListingMutation((ids: string[]) => hostApi.addPhotos(id, ids), handlers);

  // Attach freshly uploaded photos as soon as they finish uploading.
  useEffect(() => {
    const ready = newPhotos.filter((p) => p.uploadId);
    if (ready.length && ready.length === newPhotos.filter((p) => !p.failed).length && !attachPhotos.isPending) {
      attachPhotos.mutate(ready.map((p) => p.uploadId!), { onSuccess: () => setNewPhotos([]) });
    }
  }, [newPhotos, attachPhotos]);

  if (listing.isLoading || config.isLoading || !draft) return <Loading />;
  if (listing.isError || !listing.data || !config.data)
    return <ErrorState message={errorMessage(listing.error ?? config.error)} onRetry={() => listing.refetch()} />;
  const l = listing.data;
  const cfg = config.data;
  const anyError = [save, setStatus, addSlot, toggleSlot, removeSlot, removePhoto, attachPhotos].find((m) => m.error)?.error;

  const confirm = (title: string, body: string, action: () => void) => confirmAction(title, body, action);

  return (
    <Screen refreshing={listing.isRefetching} onRefresh={() => listing.refetch()}>
      <Row style={{ justifyContent: 'space-between' }}>
        <Text variant="heading" style={{ flex: 1 }}>
          {l.title}
        </Text>
        <StatusText label={titleCase(l.status)} />
      </Row>
      <Text variant="muted">
        {l.address_line}, {l.city}
      </Text>
      {notice ? <Banner tone="success">{notice}</Banner> : null}
      {anyError ? <Banner tone="danger">{errorMessage(anyError)}</Banner> : null}

      <Row style={{ marginTop: spacing.md }}>
        {l.status === 'active' ? (
          <Button title="Pause bookings" kind="secondary" style={{ flex: 1 }} onPress={() => setStatus.mutate('paused')} loading={setStatus.isPending} />
        ) : l.status !== 'archived' ? (
          <Button title="Publish" style={{ flex: 1 }} onPress={() => setStatus.mutate('active')} loading={setStatus.isPending} />
        ) : null}
        {l.status !== 'archived' ? (
          <Button
            title="Archive"
            kind="danger"
            style={{ flex: 1 }}
            onPress={() =>
              confirm(
                'Archive',
                'Drivers will no longer see or book this spot, and it leaves your list. Spots with upcoming or active bookings can\'t be archived until those bookings finish or are cancelled.',
                // Archived spots are gone for good, so leave this screen once it's done.
                () => setStatus.mutate('archived', { onSuccess: () => router.back() }),
              )
            }
          />
        ) : null}
      </Row>

      <Section title={`Photos (${l.media.length}/${cfg.max_listing_photos})`}>
        <Row style={{ flexWrap: 'wrap' }} gap={spacing.lg}>
          {l.media.map((m) => (
            <View key={m.id} style={{ borderRadius: radius.control, boxShadow: shadows.clayRaised }}>
              <Image source={{ uri: m.url }} style={{ width: 96, height: 96, borderRadius: radius.control }} accessibilityLabel="Listing photo" />
              <View style={{ position: 'absolute', top: -8, right: -8 }}>
                <IconButton icon="close" tone="danger" size={30} label="Remove photo" onPress={() => confirm('Remove', 'Remove this photo?', () => removePhoto.mutate(m.id))} />
              </View>
            </View>
          ))}
        </Row>
        {l.media.length < cfg.max_listing_photos ? (
          <PhotoPicker photos={newPhotos} onChange={setNewPhotos} max={cfg.max_listing_photos - l.media.length} purpose="listing_photo" />
        ) : null}
      </Section>

      <Section title={`Slots (${l.slots.filter((s) => s.is_active).length} active)`}>
        {l.slots.length === 0 ? (
          <Card tier="light">
            <Text variant="muted" style={{ textAlign: 'center', paddingVertical: spacing.sm }}>
              No parking slots added yet. Add your first bay or space below.
            </Text>
          </Card>
        ) : null}

        {l.slots.map((s) => (
          <Card key={s.id} tier="light">
            <View style={{ gap: spacing.sm }}>
              {/* Slot details & actions */}
              <Row style={{ justifyContent: 'space-between', alignItems: 'center' }}>
                <Row gap={spacing.md} style={{ flex: 1, paddingRight: spacing.sm }}>
                  <IconOrb
                    icon={s.slot_type === 'ev' ? 'flash-outline' : 'car-outline'}
                    tone={s.is_active ? 'accent' : 'neutral'}
                    size={40}
                  />
                  <View style={{ flex: 1 }}>
                    <Text style={{ fontFamily: fonts.heading, fontSize: 16 }}>{s.label}</Text>
                    <Text variant="small">
                      {titleCase(s.slot_type)} · {money(s.hourly_rate, l.currency)}/h
                    </Text>
                  </View>
                </Row>
                <IconButton
                  icon="trash-outline"
                  tone="danger"
                  size={36}
                  label={`Delete slot ${s.label}`}
                  onPress={() =>
                    confirm(
                      'Delete',
                      `Delete slot ${s.label}? Slots with past bookings are switched off instead.`,
                      () => removeSlot.mutate(s.id),
                    )
                  }
                />
              </Row>

              <Divider />

              {/* Status & availability toggle */}
              <Row style={{ justifyContent: 'space-between', alignItems: 'center' }}>
                <Row gap={spacing.sm} style={{ flex: 1, paddingRight: spacing.sm }}>
                  <Pill label={s.is_active ? 'Active' : 'Paused'} tone={s.is_active ? 'success' : 'neutral'} />
                  <Text variant="small" style={{ flexShrink: 1 }}>
                    {s.is_active ? 'Available for bookings' : 'Hidden from drivers'}
                  </Text>
                </Row>
                <Toggle
                  value={s.is_active}
                  onChange={(v) => toggleSlot.mutate({ id: s.id, active: v })}
                />
              </Row>
            </View>
          </Card>
        ))}

        <Card tier="light">
          <Text style={{ fontFamily: fonts.heading, fontSize: 15, marginBottom: spacing.xs }}>
            Add new slot
          </Text>
          <TextField
            label="Slot or bay label"
            placeholder="e.g. Bay A-1, Slot 4"
            value={newSlot}
            onChangeText={setNewSlot}
            maxLength={32}
            autoCapitalize="characters"
          />
          <Button
            title="Add slot"
            icon="add-circle-outline"
            kind="secondary"
            disabled={!newSlot.trim()}
            loading={addSlot.isPending}
            onPress={() => addSlot.mutate(newSlot.trim(), { onSuccess: () => setNewSlot('') })}
          />
        </Card>
      </Section>

      <Section title="Details">
        <ListingFields draft={draft} onChange={setDraft} errors={errors} config={cfg} />
        <Button
          title="Save changes"
          loading={save.isPending}
          disabled={l.status === 'archived'}
          onPress={() => {
            const found = validateDraft(draft);
            setErrors(found);
            if (!Object.keys(found).length) save.mutate(draft);
          }}
        />
      </Section>
    </Screen>
  );
}
