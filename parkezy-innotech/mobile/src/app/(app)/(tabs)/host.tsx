import { useMutation, useQuery } from '@tanstack/react-query';
import { Image } from 'expo-image';
import { router } from 'expo-router';
import { View } from 'react-native';

import { errorMessage } from '@/api/client';
import { hostApi, meApi } from '@/api/endpoints';
import type { HostDashboard } from '@/api/types';
import { useAuth } from '@/auth/AuthProvider';
import { keys } from '@/hooks/queries';
import { BookingCard } from '@/ui/BookingCard';
import { BarChart } from '@/ui/charts';
import {
  Banner,
  Button,
  Card,
  EmptyState,
  ErrorState,
  FeaturedCard,
  IconOrb,
  Loading,
  Row,
  Screen,
  Section,
  StatusText,
  Text,
} from '@/ui/components';
import { ScreenTitle } from '@/ui/ScreenTitle';
import { radius, spacing, useTheme } from '@/ui/theme';
import { money, titleCase } from '@/utils/format';

const PERIOD_DAYS = 14;

function BecomeHost() {
  const { user, setUser } = useAuth();
  const become = useMutation({ mutationFn: meApi.becomeHost, onSuccess: setUser });
  const needsVerify = !user?.email_verified;
  const needsPhone = !user?.phone;
  return (
    <Screen edges={['top']}>
      <ScreenTitle title="Host" subtitle="Earn from your parking space" />
      <Card tier="strong">
        <EmptyState
          icon="home-outline"
          title="List a driveway, garage or lot"
          body="You set the price and hours, approve who parks, and get paid for every booking."
        />
      </Card>
      <View style={{ gap: spacing.md, marginTop: spacing.xl }}>
        {needsVerify ? <Banner tone="info">Verify your email first.</Banner> : null}
        {needsPhone ? <Banner tone="info">Add a phone number so drivers can reach you.</Banner> : null}
        {become.error ? <Banner tone="danger">{errorMessage(become.error)}</Banner> : null}
        {needsVerify ? <Button title="Verify email" kind="secondary" onPress={() => router.push('/verify-email')} /> : null}
        {needsPhone ? <Button title="Add phone number" kind="secondary" onPress={() => router.push('/account/profile')} /> : null}
        <Button title="Start hosting" icon="arrow-forward" onPress={() => become.mutate()} loading={become.isPending} disabled={needsVerify || needsPhone} />
      </View>
    </Screen>
  );
}

/** Fill missing days with 0 so the chart has one bar per day of the period. */
function dailySeries(d: HostDashboard): { values: number[]; labels: string[] } {
  const byDay = new Map(d.daily_earnings.map((e) => [e.day, Number(e.amount)]));
  const values: number[] = [];
  const labels: string[] = [];
  for (let i = d.period_days - 1; i >= 0; i--) {
    const day = new Date(Date.now() - i * 86_400_000);
    const key = day.toISOString().slice(0, 10);
    values.push(byDay.get(key) ?? 0);
    labels.push(day.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }));
  }
  return { values, labels };
}

function Stat({ label, value, icon }: { label: string; value: number; icon: 'car-outline' | 'calendar-outline' | 'hourglass-outline' }) {
  return (
    <Card style={{ flex: 1 }} tier="mid" padded={false}>
      <View style={{ padding: spacing.lg, gap: spacing.xs }}>
        <IconOrb icon={icon} size={36} tone={label === 'Requests' && value > 0 ? 'warning' : 'accent'} />
        <Text variant="number" style={{ marginTop: spacing.xs }}>
          {value}
        </Text>
        <Text variant="small" numberOfLines={1} adjustsFontSizeToFit>
          {label}
        </Text>
      </View>
    </Card>
  );
}

export default function HostHome() {
  const { user } = useAuth();
  const { colors } = useTheme();
  const dashboard = useQuery({ queryKey: keys.hostDashboard, queryFn: () => hostApi.dashboard(PERIOD_DAYS), enabled: !!user?.is_host });
  const listings = useQuery({ queryKey: keys.hostListings, queryFn: hostApi.listings, enabled: !!user?.is_host });
  const requests = useQuery({
    queryKey: keys.hostBookingsPreview('upcoming'),
    queryFn: () => hostApi.bookings('upcoming'),
    enabled: !!user?.is_host,
    refetchInterval: 30_000,
  });

  if (!user?.is_host) return <BecomeHost />;
  if (dashboard.isLoading || listings.isLoading) return <Loading />;
  if (dashboard.isError || listings.isError)
    return (
      <ErrorState
        message={errorMessage(dashboard.error ?? listings.error)}
        onRetry={() => {
          dashboard.refetch();
          listings.refetch();
        }}
      />
    );
  const d = dashboard.data!;
  const pending = requests.data?.items.filter((b) => b.status === 'pending_approval') ?? [];
  const series = dailySeries(d);

  return (
    <Screen
      edges={['top']}
      refreshing={dashboard.isRefetching}
      onRefresh={() => {
        dashboard.refetch();
        listings.refetch();
        requests.refetch();
      }}>
      <ScreenTitle title="Host" subtitle={`${d.active_listings} live ${d.active_listings === 1 ? 'spot' : 'spots'}`} />

      {/* The single solid card on the screen: earnings are what hosts come here for. */}
      <FeaturedCard>
        <Text variant="label" style={{ color: colors.onFeaturedMuted }}>
          Earned in the last {d.period_days} days
        </Text>
        <Text variant="display" style={{ color: colors.onFeatured }}>
          {money(d.earnings_period, d.currency)}
        </Text>
        <Text variant="small" style={{ color: colors.onFeaturedMuted }}>
          {money(d.earnings_total, d.currency)} all time · after platform fee
        </Text>
        <View style={{ marginTop: spacing.md }}>
          <BarChart
            values={series.values}
            labels={[series.labels[0], series.labels[series.labels.length - 1]]}
            inverse
            accessibilityLabel={`Daily earnings for the last ${d.period_days} days`}
          />
        </View>
      </FeaturedCard>

      <Row style={{ marginTop: spacing.lg }} gap={spacing.md}>
        <Stat label="Parked" value={d.parked_now} icon="car-outline" />
        <Stat label="Upcoming" value={d.upcoming_bookings} icon="calendar-outline" />
        <Stat label="Requests" value={d.pending_requests} icon="hourglass-outline" />
      </Row>

      <View style={{ gap: spacing.md, marginTop: spacing.xl }}>
        <Button title="Check a driver in or out" icon="qr-code-outline" onPress={() => router.push('/host/scan')} />
        <Button title="All bookings" kind="secondary" icon="list-outline" onPress={() => router.push('/host/bookings')} />
      </View>

      {pending.length ? (
        <Section title="Waiting for your answer">
          {pending.map((b) => (
            <BookingCard key={b.id} booking={b} perspective="host" onPress={() => router.push({ pathname: '/booking/[id]', params: { id: b.id } })} />
          ))}
        </Section>
      ) : null}

      <Section title="Your spots" right={<Button title="Add" size="sm" kind="secondary" icon="add" onPress={() => router.push('/host/new-listing')} />}>
        {listings.data!.length === 0 ? (
          <Card>
            <EmptyState
              icon="add-circle-outline"
              title="No spots yet"
              body="Add your first parking spot to start earning."
              action={<Button title="Add a spot" onPress={() => router.push('/host/new-listing')} />}
            />
          </Card>
        ) : (
          listings.data!.map((l) => (
            <Card key={l.id} onPress={() => router.push({ pathname: '/host/listing/[id]', params: { id: l.id } })} accessibilityLabel={`Manage ${l.title}`}>
              <Row gap={spacing.md}>
                {l.media[0] ? (
                  <Image source={{ uri: l.media[0].url }} style={{ width: 64, height: 64, borderRadius: radius.control }} />
                ) : (
                  <IconOrb icon="image-outline" tone="neutral" size={64} />
                )}
                <View style={{ flex: 1, gap: 4 }}>
                  <Text variant="heading" numberOfLines={1}>
                    {l.title}
                  </Text>
                  <Text variant="small">
                    {l.slots.filter((s) => s.is_active).length} slots · {money(l.hourly_rate, l.currency)}/h
                  </Text>
                </View>
                <StatusText label={titleCase(l.status)} />
              </Row>
            </Card>
          ))
        )}
      </Section>
    </Screen>
  );
}
