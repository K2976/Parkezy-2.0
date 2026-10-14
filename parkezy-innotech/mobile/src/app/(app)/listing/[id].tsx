import Ionicons from '@expo/vector-icons/Ionicons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as Crypto from 'expo-crypto';
import { Image } from 'expo-image';
import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useMemo, useRef, useState } from 'react';
import { ScrollView, useWindowDimensions, View } from 'react-native';

import { ApiError, errorMessage } from '@/api/client';
import { bookingApi, discoveryApi } from '@/api/endpoints';
import { useAuth } from '@/auth/AuthProvider';
import { keys, useConfig } from '@/hooks/queries';
import { registerForPush } from '@/services/push';
import {
  Banner,
  Button,
  Card,
  Chip,
  ErrorState,
  FeaturedCard,
  IconOrb,
  Loading,
  PriceRow,
  Row,
  Screen,
  Section,
  Tag,
  Text,
  TextField,
} from '@/ui/components';
import { fonts, radius, spacing, useTheme } from '@/ui/theme';
import { defaultWindow, type Window, WhenPicker, windowIso } from '@/ui/WhenPicker';
import { money, titleCase, WEEKDAYS } from '@/utils/format';
import { minutesBetween } from '@/utils/time';

export default function ListingDetail() {
  const params = useLocalSearchParams<{ id: string; starts_at?: string; ends_at?: string }>();
  const { user } = useAuth();
  const { width } = useWindowDimensions();
  const { colors } = useTheme();
  const queryClient = useQueryClient();
  const config = useConfig();
  const [when, setWhen] = useState<Window | null>(() =>
    params.starts_at && params.ends_at
      ? { start: new Date(params.starts_at), minutes: minutesBetween(new Date(params.starts_at), new Date(params.ends_at)) }
      : null,
  );
  const [slotId, setSlotId] = useState<string | null>(null);
  const [vehicle, setVehicle] = useState('');
  const [photoIndex, setPhotoIndex] = useState(0);
  // One key per booking attempt: retries after a network error never double-book.
  const idempotencyKey = useRef(Crypto.randomUUID());

  const window = when ? windowIso(when) : undefined;
  const listing = useQuery({ queryKey: keys.listing(params.id, window), queryFn: () => discoveryApi.listing(params.id, window) });
  const quote = useQuery({
    queryKey: ['quote', params.id, slotId, window],
    queryFn: () => bookingApi.quote({ listing_id: params.id, slot_id: slotId, ...window! }),
    enabled: !!window,
    retry: false,
  });

  const book = useMutation({
    mutationFn: () =>
      bookingApi.create(
        { listing_id: params.id, slot_id: slotId, ...window!, vehicle_number: vehicle.trim() || null },
        idempotencyKey.current,
      ),
    onSuccess: (booking) => {
      idempotencyKey.current = Crypto.randomUUID();
      queryClient.invalidateQueries({ queryKey: ['bookings'] });
      queryClient.invalidateQueries({ queryKey: ['listings'] });
      void registerForPush(); // ask for notifications in context, right after booking
      router.replace({ pathname: '/booking/[id]', params: { id: booking.id } });
    },
  });

  const freeSlots = useMemo(() => listing.data?.slots.filter((s) => s.available !== false) ?? [], [listing.data]);

  if (listing.isLoading || config.isLoading) return <Loading />;
  if (listing.isError || !listing.data || !config.data)
    return <ErrorState message={errorMessage(listing.error ?? config.error)} onRetry={() => listing.refetch()} />;
  const l = listing.data;
  const isOwner = user?.id === l.host.id;
  const quoteError = quote.error instanceof ApiError ? quote.error.message : null;
  const bookError = book.error ? errorMessage(book.error) : null;

  return (
    <>
      <Stack.Screen options={{ title: l.title }} />
      <Screen>
        {(() => {
          const displayPhotos = l.media.length
            ? l.media.map((m) => ({ id: m.id, url: m.url }))
            : [
                { id: 'fb1', url: 'https://images.unsplash.com/photo-1506521781263-d8422e82f27a?auto=format&fit=crop&w=1200&q=80' },
                { id: 'fb2', url: 'https://images.unsplash.com/photo-1590674899484-d5640e854abe?auto=format&fit=crop&w=1200&q=80' },
                { id: 'fb3', url: 'https://images.unsplash.com/photo-1573348722427-f1d6819fdf98?auto=format&fit=crop&w=1200&q=80' },
              ];
          const cardWidth = width - spacing.lg * 2;
          return (
            <View style={{ marginHorizontal: -spacing.lg, marginBottom: spacing.md }}>
              <ScrollView
                horizontal
                pagingEnabled
                showsHorizontalScrollIndicator={false}
                contentContainerStyle={{ paddingHorizontal: spacing.lg, gap: spacing.lg }}
                snapToInterval={cardWidth + spacing.lg}
                decelerationRate="fast"
                onMomentumScrollEnd={(e) => {
                  const offset = e.nativeEvent.contentOffset.x;
                  const idx = Math.round(offset / (cardWidth + spacing.lg));
                  setPhotoIndex(Math.max(0, Math.min(idx, displayPhotos.length - 1)));
                }}>
                {displayPhotos.map((p, i) => (
                  <View
                    key={p.id}
                    style={{
                      width: cardWidth,
                      height: 230,
                      borderRadius: radius.card,
                      overflow: 'hidden',
                      backgroundColor: colors.clayRecessed,
                    }}>
                    <Image
                      source={{ uri: p.url }}
                      style={{ width: '100%', height: '100%' }}
                      contentFit="cover"
                      accessibilityLabel={`Photo ${i + 1} of ${displayPhotos.length}`}
                    />
                  </View>
                ))}
              </ScrollView>

              {/* Floating Photo Counter Badge */}
              <View
                style={{
                  position: 'absolute',
                  top: spacing.sm,
                  right: spacing.xl,
                  backgroundColor: 'rgba(0,0,0,0.65)',
                  paddingHorizontal: spacing.sm,
                  paddingVertical: 4,
                  borderRadius: radius.pill,
                  flexDirection: 'row',
                  alignItems: 'center',
                  gap: 4,
                }}>
                <Ionicons name="camera" size={13} color="#fff" />
                <Text style={{ color: '#fff', fontSize: 12, fontFamily: fonts.bodyBold }}>
                  {photoIndex + 1} / {displayPhotos.length}
                </Text>
              </View>

              {/* Dots Pagination */}
              {displayPhotos.length > 1 ? (
                <Row gap={6} style={{ justifyContent: 'center', marginTop: spacing.sm }}>
                  {displayPhotos.map((_, i) => (
                    <View
                      key={i}
                      style={{
                        width: i === photoIndex ? 18 : 6,
                        height: 6,
                        borderRadius: radius.pill,
                        backgroundColor: i === photoIndex ? colors.accent : colors.hairline,
                      }}
                    />
                  ))}
                </Row>
              ) : null}
            </View>
          );
        })()}
        <View style={{ gap: 6, marginTop: spacing.xl }}>
          <Text variant="title">{l.title}</Text>
          <Text variant="muted">
            {l.address_line}, {l.city}
          </Text>
          <Text variant="small">
            Hosted by {l.host.first_name} · {titleCase(l.kind)} · {l.auto_accept ? 'Instant booking' : 'Host approves requests'}
          </Text>
        </View>

        <Card tier="light" style={{ marginTop: spacing.lg }}>
          <Row gap={spacing.md}>
            <IconOrb icon="time-outline" size={40} />
            <View style={{ flex: 1 }}>
              <Text style={{ fontFamily: fonts.bodyBold }}>{l.is_24h ? 'Open 24 hours' : `${l.open_time?.slice(0, 5)} – ${l.close_time?.slice(0, 5)}`}</Text>
              <Text variant="small">{l.open_days.length === 7 ? 'Every day' : l.open_days.map((d) => WEEKDAYS[d - 1]).join(', ')}</Text>
            </View>
          </Row>
        </Card>

        {l.amenities.length ? (
          <Section title="Amenities">
            <Row style={{ flexWrap: 'wrap' }} gap={spacing.xs}>
              {l.amenities.map((a) => (
                <Tag key={a} label={titleCase(a)} icon="checkmark" />
              ))}
            </Row>
          </Section>
        ) : null}

        {l.description ? (
          <Section title="About">
            <Card tier="light">
              <Text>{l.description}</Text>
            </Card>
          </Section>
        ) : null}

        <Section title="When">
          <WhenPicker
            config={config.data}
            // Aligned to the booking step: a raw `new Date()` carries seconds and the server rejects it.
            value={when ?? defaultWindow(config.data)}
            onChange={(w) => {
              setWhen(w);
              setSlotId(null);
            }}
          />
        </Section>

        {window ? (
          <Section title="Choose a slot" right={<Text variant="small">{freeSlots.length} free</Text>}>
            <Row style={{ flexWrap: 'wrap' }} gap={spacing.xs}>
              <Chip label="Any free slot" selected={slotId === null} onPress={() => setSlotId(null)} />
              {l.slots.map((s) => (
                <Chip
                  key={s.id}
                  label={`${s.label}${s.slot_type !== 'standard' ? ` · ${titleCase(s.slot_type)}` : ''}${s.available === false ? ' (taken)' : ''}`}
                  selected={slotId === s.id}
                  onPress={() => s.available !== false && setSlotId(s.id)}
                />
              ))}
            </Row>
          </Section>
        ) : null}

        <Section title="Vehicle">
          <TextField label="Vehicle number (optional)" value={vehicle} onChangeText={setVehicle} autoCapitalize="characters" placeholder="KA01AB1234" />
        </Section>

        {window ? (
          <Section title="Price">
            {quote.isLoading ? (
              <Card tier="light">
                <Text variant="muted">Calculating price…</Text>
              </Card>
            ) : quoteError ? (
              <Banner tone="warning">{quoteError}</Banner>
            ) : quote.data ? (
              <>
                {/* The price is this screen's one solid, featured surface. */}
                <FeaturedCard>
                  <PriceRow inverse label={`Parking · ${money(quote.data.hourly_rate, quote.data.currency)}/h`} value={money(quote.data.subtotal, quote.data.currency)} />
                  <PriceRow inverse label={`GST ${Math.round(Number(quote.data.tax_rate) * 100)}%`} value={money(quote.data.tax_amount, quote.data.currency)} />
                  <Row style={{ justifyContent: 'space-between', alignItems: 'flex-end', marginTop: spacing.sm }}>
                    <Text variant="label" style={{ color: colors.onFeaturedMuted }}>
                      Total
                    </Text>
                    <Text variant="number" style={{ color: colors.onFeatured }}>
                      {money(quote.data.total, quote.data.currency)}
                    </Text>
                  </Row>
                </FeaturedCard>
                <Text variant="small">
                  {quote.data.payment_mode === 'online' ? 'Pay securely in the app.' : 'Pay the host when you leave.'} Free cancellation up to{' '}
                  {config.data.free_cancellation_minutes} min before start. Overstay is{' '}
                  {money(config.data.overstay_block_fee, config.data.currency)} per {config.data.overstay_block_minutes} min after a{' '}
                  {config.data.overstay_grace_minutes}-min grace period.
                </Text>
                {!quote.data.available ? <Banner tone="warning">No free slot for this time. Try another time.</Banner> : null}
              </>
            ) : null}
          </Section>
        ) : null}

        {!user?.email_verified ? (
          <Banner tone="info">
            <Text>
              Verify your email to book.{' '}
              <Text style={{ fontFamily: fonts.bodyBold, color: colors.accent }} onPress={() => router.push('/verify-email')}>
                Verify now
              </Text>
            </Text>
          </Banner>
        ) : null}
        {bookError ? <Banner tone="danger">{bookError}</Banner> : null}
        <View style={{ height: spacing.xl }} />
        {isOwner ? (
          <Button title="Manage this spot" kind="secondary" onPress={() => router.push({ pathname: '/host/listing/[id]', params: { id: l.id } })} />
        ) : (
          <Button
            title={quote.data?.requires_approval ? 'Request to book' : 'Book now'}
            onPress={() => book.mutate()}
            loading={book.isPending}
            disabled={!window || !quote.data?.available || !user?.email_verified}
          />
        )}
      </Screen>
    </>
  );
}
