import { View } from 'react-native';

import type { Booking } from '@/api/types';
import { Card, IconOrb, type IconName, Row, StatusBadge, Text } from '@/ui/components';
import { fonts, spacing, useTheme } from '@/ui/theme';
import { dateTime, money, time } from '@/utils/format';

const STATUS_ICON: Record<Booking['status'], IconName> = {
  pending_approval: 'hourglass-outline',
  pending_payment: 'card-outline',
  confirmed: 'calendar-outline',
  checked_in: 'car-outline',
  completed: 'checkmark-done-outline',
  cancelled: 'close-outline',
  rejected: 'close-circle-outline',
  expired: 'time-outline',
};

export function BookingCard({ booking, onPress, perspective }: { booking: Booking; onPress: () => void; perspective: 'driver' | 'host' }) {
  const { colors } = useTheme();
  const tz = booking.listing.timezone;
  const amount = perspective === 'host' && booking.host_earnings ? booking.host_earnings : (booking.final_amount ?? booking.total_amount);
  const live = booking.status === 'checked_in' || booking.status === 'confirmed';
  return (
    <Card onPress={onPress} accessibilityLabel={`${booking.listing.title}, ${dateTime(booking.starts_at, tz)}`}>
      <Row gap={spacing.md} style={{ alignItems: 'flex-start' }}>
        <IconOrb icon={STATUS_ICON[booking.status]} tone={live ? 'accent' : 'neutral'} size={44} />
        <View style={{ flex: 1, gap: 4 }}>
          <Row style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <Text variant="heading" style={{ flex: 1 }} numberOfLines={1}>
              {perspective === 'driver' ? booking.listing.title : booking.driver.full_name}
            </Text>
            <StatusBadge status={booking.status} />
          </Row>
          <Text variant="muted">
            {dateTime(booking.starts_at, tz)} – {time(booking.ends_at, tz)}
          </Text>
          <Row style={{ justifyContent: 'space-between' }}>
            <Text variant="small" numberOfLines={1} style={{ flex: 1 }}>
              Slot {booking.slot.label}
              {perspective === 'host' ? ` · ${booking.listing.title}` : ''}
              {booking.vehicle_number ? ` · ${booking.vehicle_number}` : ''}
            </Text>
            <Text style={{ fontFamily: fonts.heading, color: colors.text }}>{money(amount, booking.currency)}</Text>
          </Row>
        </View>
      </Row>
    </Card>
  );
}
