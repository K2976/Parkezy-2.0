import Ionicons from '@expo/vector-icons/Ionicons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Constants from 'expo-constants';
import { Image } from 'expo-image';
import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { Alert, Linking, Platform, View } from 'react-native';
import QRCode from 'react-native-qrcode-svg';

import { errorMessage } from '@/api/client';
import { bookingApi, hostApi } from '@/api/endpoints';
import type { Booking } from '@/api/types';
import { useAuth } from '@/auth/AuthProvider';
import { keys, useConfig } from '@/hooks/queries';
import { PaymentCancelledError, payForBooking } from '@/services/payments';
import { ProgressRing } from '@/ui/charts';
import {
  Banner,
  Button,
  Card,
  ErrorState,
  FeaturedCard,
  Loading,
  PriceRow,
  Row,
  Screen,
  Section,
  StatusBadge,
  Text,
} from '@/ui/components';
import { fonts, radius, spacing, useTheme } from '@/ui/theme';
import { dateTime, duration, money, shortDuration, time, titleCase } from '@/utils/format';
import { minutesBetween } from '@/utils/time';

const LIVE: Booking['status'][] = ['pending_approval', 'pending_payment', 'confirmed', 'checked_in'];

function useNow(intervalMs: number) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), intervalMs);
    return () => clearInterval(t);
  }, [intervalMs]);
  return now;
}

function AccessPass({ booking }: { booking: Booking }) {
  const { colors } = useTheme();
  // The QR token is short-lived and single-use; refresh it before it expires.
  const access = useQuery({
    queryKey: keys.access(booking.id),
    queryFn: () => bookingApi.access(booking.id),
    refetchInterval: (q) => {
      const exp = q.state.data ? new Date(q.state.data.qr_expires_at).getTime() - Date.now() : 0;
      return Math.max(exp - 15_000, 5_000);
    },
  });
  if (access.isLoading) return <Loading />;
  if (access.isError || !access.data) return <Banner tone="danger">{errorMessage(access.error)}</Banner>;
  return (
    <Card tier="strong" style={{ alignItems: 'stretch' }}>
      <View style={{ alignItems: 'center', gap: spacing.md }}>
        <Text variant="label">Show at the entrance</Text>
        {/* QR stays dark-on-white inside its own tile so every scanner can read it. */}
        <View style={{ padding: spacing.lg, backgroundColor: colors.qrBackground, borderRadius: radius.md }} accessibilityLabel="Entry QR code">
          <QRCode value={access.data.qr_token} size={196} color={colors.qrForeground} backgroundColor={colors.qrBackground} />
        </View>
        <Text variant="small">or tell the host your PIN</Text>
        <View accessible accessibilityLabel={`PIN ${access.data.pin.split('').join(' ')}`}>
          <Row gap={spacing.sm}>
            {access.data.pin.split('').map((d, i) => (
              <PinDigit key={i} digit={d} />
            ))}
          </Row>
        </View>
        <Text variant="small">Check-in opens {dateTime(access.data.check_in_opens_at, booking.listing.timezone)}</Text>
      </View>
    </Card>
  );
}

/** Each PIN digit sits in a recessed clay well, like keys pressed into the surface. */
function PinDigit({ digit }: { digit: string }) {
  const { colors, shadows } = useTheme();
  return (
    <View
      style={{
        width: 42,
        height: 52,
        borderRadius: 16,
        backgroundColor: colors.clayRecessed,
        boxShadow: shadows.clayPressed,
        alignItems: 'center',
        justifyContent: 'center',
      }}>
      <Text style={{ fontFamily: fonts.display, fontSize: 24, color: colors.text }}>{digit}</Text>
    </View>
  );
}

function SessionRing({ booking, now }: { booking: Booking; now: Date }) {
  const { colors } = useTheme();
  const start = new Date(booking.checked_in_at ?? booking.starts_at);
  const end = new Date(booking.ends_at);
  const total = Math.max(minutesBetween(start, end), 1);
  const used = minutesBetween(start, now);
  const left = minutesBetween(now, end);
  const over = left < 0;
  return (
    <Card tier="strong">
      <Row gap={spacing.xl}>
        <ProgressRing
          progress={over ? 1 : used / total}
          tone={over || left <= 15 ? 'warning' : 'accent'}
          accessibilityLabel={over ? `Overstayed by ${duration(-left)}` : `${duration(left)} left`}
          center={
            // Compact value so long overstays ("+17h 2m", "+2d 3h") stay inside the ring.
            <View style={{ alignItems: 'center', paddingHorizontal: 14 }}>
              <Text
                variant="number"
                numberOfLines={1}
                style={{ fontSize: 22, lineHeight: 26, color: over ? colors.warning : colors.text }}>
                {over ? `+${shortDuration(-left)}` : shortDuration(left)}
              </Text>
              <Text variant="small">{over ? 'overtime' : 'left'}</Text>
            </View>
          }
        />
        <View style={{ flex: 1, gap: 4 }}>
          <Text variant="heading">{over ? 'Time’s up' : 'You’re parked'}</Text>
          {over ? (
            <>
              <Text variant="muted">Your booking ended at {time(booking.ends_at, booking.listing.timezone)}.</Text>
              <Text variant="small" style={{ color: colors.warning }}>
                Overstay fees are adding up. End parking as soon as you leave.
              </Text>
            </>
          ) : (
            <Text variant="muted">
              Until {time(booking.ends_at, booking.listing.timezone)}. End parking from here when you leave.
            </Text>
          )}
        </View>
      </Row>
    </Card>
  );
}

export default function BookingDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useAuth();
  const { colors } = useTheme();
  const config = useConfig();
  const queryClient = useQueryClient();
  const now = useNow(30_000);
  const [payError, setPayError] = useState<string | null>(null);

  const booking = useQuery({
    queryKey: keys.booking(id),
    queryFn: () => bookingApi.get(id),
    // Poll while the booking can change on the server (host approval, check-in, expiry).
    refetchInterval: (q) => (q.state.data && LIVE.includes(q.state.data.status) ? 20_000 : false),
  });

  const refreshAll = () => {
    queryClient.invalidateQueries({ queryKey: ['bookings'] });
    queryClient.invalidateQueries({ queryKey: ['host'] });
  };
  const cancel = useMutation({ mutationFn: () => bookingApi.cancel(id), onSuccess: refreshAll });
  const approve = useMutation({ mutationFn: () => hostApi.approve(id), onSuccess: refreshAll });
  const reject = useMutation({ mutationFn: () => hostApi.reject(id), onSuccess: refreshAll });
  const checkOut = useMutation({ mutationFn: () => bookingApi.checkOut(id), onSuccess: refreshAll });
  const pay = useMutation({
    mutationFn: () => payForBooking(id, Constants.expoConfig?.name ?? 'Parkezy', colors.accent),
    onMutate: () => setPayError(null),
    onSuccess: refreshAll,
    onError: (e) => !(e instanceof PaymentCancelledError) && setPayError(errorMessage(e)),
  });

  if (booking.isLoading) return <Loading />;
  if (booking.isError || !booking.data) return <ErrorState message={errorMessage(booking.error)} onRetry={() => booking.refetch()} />;
  const b = booking.data;
  const tz = b.listing.timezone;
  const isDriver = user?.id === b.driver.id;
  const starts = new Date(b.starts_at);
  const minutesToStart = minutesBetween(now, starts);
  const freeCancel = config.data ? minutesToStart >= config.data.free_cancellation_minutes : true;
  const total = b.final_amount ?? b.total_amount;
  const due = Number(b.amount_due);
  const actionError = cancel.error ?? checkOut.error ?? approve.error ?? reject.error;

  const confirmCancel = () => {
    const fee =
      isDriver && b.status === 'confirmed' && !freeCancel && Number(b.amount_paid) > 0 && config.data
        ? ` A late-cancellation fee of ${Math.round(Number(config.data.late_cancellation_fee_rate) * 100)}% of the parking price applies.`
        : '';
    Alert.alert('Cancel booking?', `This can’t be undone.${fee}`, [
      { text: 'Keep booking', style: 'cancel' },
      { text: 'Cancel booking', style: 'destructive', onPress: () => cancel.mutate() },
    ]);
  };

  const openMaps = () => {
    const { latitude, longitude } = b.listing;
    const url = Platform.select({
      ios: `maps:0,0?q=${encodeURIComponent(b.listing.title)}@${latitude},${longitude}`,
      default: `geo:0,0?q=${latitude},${longitude}(${encodeURIComponent(b.listing.title)})`,
    });
    Linking.openURL(url);
  };

  return (
    <Screen refreshing={booking.isRefetching} onRefresh={() => booking.refetch()}>
      {/* Spot Photo Preview */}
      <View
        style={{
          height: 170,
          borderRadius: radius.card,
          overflow: 'hidden',
          marginBottom: spacing.md,
          backgroundColor: colors.clayRecessed,
        }}>
        <Image
          source={{ uri: 'https://images.unsplash.com/photo-1506521781263-d8422e82f27a?auto=format&fit=crop&w=1200&q=80' }}
          style={{ width: '100%', height: '100%' }}
          contentFit="cover"
          accessibilityLabel="Photo of the parking spot"
        />
        <View
          style={{
            position: 'absolute',
            bottom: spacing.sm,
            left: spacing.sm,
            backgroundColor: 'rgba(0,0,0,0.65)',
            paddingHorizontal: spacing.sm,
            paddingVertical: 4,
            borderRadius: radius.pill,
            flexDirection: 'row',
            alignItems: 'center',
            gap: 4,
          }}>
          <Ionicons name="car-outline" size={14} color="#fff" />
          <Text style={{ color: '#fff', fontSize: 12, fontFamily: fonts.bodyBold }}>
            Slot {b.slot.label} · {b.listing.title}
          </Text>
        </View>
      </View>

      <View style={{ gap: spacing.sm }}>
        <StatusBadge status={b.status} />
        <Text variant="title">{b.listing.title}</Text>
        <Text variant="muted">
          {b.listing.address_line}, {b.listing.city}
        </Text>
      </View>

      <View style={{ gap: spacing.sm, marginTop: spacing.lg }}>
        {b.status === 'pending_approval' && b.approval_expires_at ? (
          <Banner tone="warning">{`Waiting for the host to accept, until ${time(b.approval_expires_at, tz)}.`}</Banner>
        ) : null}
        {b.status === 'pending_payment' && b.hold_expires_at ? (
          <Banner tone="warning">{`Pay by ${time(b.hold_expires_at, tz)} to keep this slot.`}</Banner>
        ) : null}
        {b.status === 'rejected' ? <Banner tone="danger">{`The host declined this request. ${b.cancel_reason ?? ''}`}</Banner> : null}
        {b.status === 'expired' ? <Banner tone="info">This booking expired.</Banner> : null}
        {actionError ? <Banner tone="danger">{errorMessage(actionError)}</Banner> : null}
        {payError ? <Banner tone="danger">{payError}</Banner> : null}
      </View>

      {b.status === 'checked_in' ? (
        <View style={{ marginTop: spacing.lg }}>
          <SessionRing booking={b} now={now} />
        </View>
      ) : null}

      {isDriver && (b.status === 'confirmed' || b.status === 'checked_in') ? (
        <Section title="Access">
          <AccessPass booking={b} />
        </Section>
      ) : null}

      <Section title="Details">
        <Card>
          <PriceRow label="When" value={`${dateTime(b.starts_at, tz)} – ${time(b.ends_at, tz)}`} />
          <PriceRow label="Duration" value={duration(minutesBetween(starts, new Date(b.ends_at)))} />
          <PriceRow label="Slot" value={`${b.slot.label}${b.slot.floor ? ` · Floor ${b.slot.floor}` : ''} · ${titleCase(b.slot.slot_type)}`} />
          {b.vehicle_number ? <PriceRow label="Vehicle" value={b.vehicle_number} /> : null}
          {isDriver && b.host.phone ? <PriceRow label="Host" value={`${b.host.full_name} · ${b.host.phone}`} /> : null}
          {!isDriver ? <PriceRow label="Driver" value={`${b.driver.full_name}${b.driver.phone ? ` · ${b.driver.phone}` : ''}`} /> : null}
        </Card>
        {b.access_instructions ? (
          <Card tier="light">
            <Text variant="label">How to get in</Text>
            <Text>{b.access_instructions}</Text>
          </Card>
        ) : null}
      </Section>

      <Section title="Payment">
        {/* The money summary is this screen's one solid, featured surface. */}
        <FeaturedCard>
          <PriceRow inverse label="Parking" value={money(b.subtotal, b.currency)} />
          {Number(b.overstay_fee) > 0 ? <PriceRow inverse label={`Overstay · ${b.overstay_minutes} min`} value={money(b.overstay_fee, b.currency)} /> : null}
          <PriceRow inverse label="GST" value={money(Number(b.tax_amount) + Number(b.overstay_tax), b.currency)} />
          <View style={{ height: 1, backgroundColor: colors.onFeaturedMuted, opacity: 0.3, marginVertical: spacing.sm }} />
          <Row style={{ justifyContent: 'space-between', alignItems: 'flex-end' }}>
            <Text variant="label" style={{ color: colors.onFeaturedMuted }}>
              {!isDriver && b.host_earnings ? 'Your earnings' : 'Total'}
            </Text>
            <Text variant="number" style={{ color: colors.onFeatured }}>
              {money(!isDriver && b.host_earnings ? b.host_earnings : total, b.currency)}
            </Text>
          </Row>
          {isDriver && b.payment_mode === 'online' ? (
            <Text variant="small" style={{ color: colors.onFeaturedMuted }}>
              Paid {money(b.amount_paid, b.currency)}
              {due > 0 ? ` · ${money(b.amount_due, b.currency)} due` : ''}
            </Text>
          ) : isDriver ? (
            <Text variant="small" style={{ color: colors.onFeaturedMuted }}>
              Pay the host at the venue when you leave.
            </Text>
          ) : null}
        </FeaturedCard>
      </Section>

      <View style={{ gap: spacing.md, marginTop: spacing.xl }}>
        {!isDriver && b.status === 'pending_approval' ? (
          <>
            <Button title="Accept request" icon="checkmark" onPress={() => approve.mutate()} loading={approve.isPending} />
            <Button title="Decline" kind="danger" onPress={() => reject.mutate()} loading={reject.isPending} />
          </>
        ) : null}
        {isDriver && b.payment_mode === 'online' && due > 0 && ['pending_payment', 'completed'].includes(b.status) ? (
          <Button title={`Pay ${money(b.amount_due, b.currency)}`} icon="card-outline" onPress={() => pay.mutate()} loading={pay.isPending} />
        ) : null}
        {isDriver && b.status === 'checked_in' ? (
          <Button title="End parking" icon="exit-outline" onPress={() => checkOut.mutate()} loading={checkOut.isPending} />
        ) : null}
        {LIVE.includes(b.status) ? <Button title="Directions" kind="secondary" icon="navigate-outline" onPress={openMaps} /> : null}
        {['pending_approval', 'pending_payment', 'confirmed'].includes(b.status) ? (
          <Button title="Cancel booking" kind="danger" icon="close" onPress={confirmCancel} loading={cancel.isPending} />
        ) : null}
        {['confirmed', 'checked_in', 'completed', 'expired', 'cancelled'].includes(b.status) ? (
          <Button
            title="Report a problem"
            kind="ghost"
            icon="flag-outline"
            onPress={() => router.push({ pathname: '/report/[bookingId]', params: { bookingId: b.id } })}
          />
        ) : null}
      </View>
    </Screen>
  );
}
