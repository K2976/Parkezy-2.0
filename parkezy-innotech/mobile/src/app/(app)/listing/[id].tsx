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
import { type Window, WhenPicker, windowIso } from '@/ui/WhenPicker';
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
        {l.media.length ? (
          <ScrollView
            horizontal
            pagingEnabled
            showsHorizontalScrollIndicator={false}
            style={{ marginHorizontal: -spacing.lg }}
            contentContainerStyle={{ paddingHorizontal: spacing.lg, gap: spacing.lg }}
            snapToInterval={width - spacing.lg}
            decelerationRate="fast">
            {l.media.map((m) => (
              <Image
                key={m.id}
                source={{ uri: m.url }}
                style={{ width: width - spacing.lg * 2, height: 230, borderRadius: radius.card }}
                contentFit="cover"
                accessibilityLabel="Photo of the parking spot"
              />
            ))}
          </ScrollView>
        ) : null}
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
            value={when ?? { start: new Date(), minutes: config.data.min_booking_minutes }}
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
