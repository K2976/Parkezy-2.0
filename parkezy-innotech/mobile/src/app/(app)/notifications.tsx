import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useEffect } from 'react';
import { FlatList, View } from 'react-native';

import { errorMessage } from '@/api/client';
import { notificationApi } from '@/api/endpoints';
import type { AppNotification } from '@/api/types';
import { keys } from '@/hooks/queries';
import { Backdrop } from '@/ui/Backdrop';
import { Card, EmptyState, ErrorState, IconOrb, type IconName, Loading, Row, Text, type Tone } from '@/ui/components';
import { fonts, spacing, useTheme } from '@/ui/theme';

const TYPE_ICON: Record<string, { icon: IconName; tone: Tone }> = {
  booking_request: { icon: 'hourglass-outline', tone: 'warning' },
  booking_update: { icon: 'calendar-outline', tone: 'accent' },
  session: { icon: 'car-outline', tone: 'success' },
  receipt: { icon: 'receipt-outline', tone: 'info' },
  dispute: { icon: 'flag-outline', tone: 'danger' },
};

function open(n: AppNotification) {
  if (n.data.booking_id) router.push({ pathname: '/booking/[id]', params: { id: n.data.booking_id } });
}

export default function Notifications() {
  const { colors } = useTheme();
  const queryClient = useQueryClient();
  const list = useQuery({ queryKey: keys.notifications, queryFn: () => notificationApi.list() });
  const markAll = useMutation({
    mutationFn: () => notificationApi.markRead(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.notifications }),
  });
  const unread = list.data?.unread_count ?? 0;

  // Opening the inbox marks everything as read (after it has rendered once with the unread markers).
  useEffect(() => {
    if (unread > 0) {
      const t = setTimeout(() => markAll.mutate(), 1500);
      return () => clearTimeout(t);
    }
  }, [unread, markAll]);

  if (list.isLoading) return <Loading />;
  if (list.isError) return <ErrorState message={errorMessage(list.error)} onRetry={() => list.refetch()} />;
  return (
    <Backdrop>
      <FlatList
        data={list.data?.items ?? []}
        keyExtractor={(n) => n.id}
        contentContainerStyle={{ padding: spacing.lg, gap: spacing.md, flexGrow: 1 }}
        refreshing={list.isRefetching}
        onRefresh={() => list.refetch()}
        ListEmptyComponent={<EmptyState icon="notifications-outline" title="You’re all caught up" />}
        renderItem={({ item }) => {
          const look = TYPE_ICON[item.type] ?? { icon: 'notifications-outline' as IconName, tone: 'neutral' as Tone };
          return (
            <Card onPress={() => open(item)} accessibilityLabel={`${item.read_at ? '' : 'Unread. '}${item.title}. ${item.body}`} tier={item.read_at ? 'light' : 'mid'}>
              <Row gap={spacing.md} style={{ alignItems: 'flex-start' }}>
                <IconOrb icon={look.icon} tone={look.tone} size={40} />
                <View style={{ flex: 1, gap: 2 }}>
                  <Row style={{ justifyContent: 'space-between' }}>
                    <Text style={{ fontFamily: item.read_at ? fonts.bodyMedium : fonts.bodyBold, flex: 1 }}>{item.title}</Text>
                    {!item.read_at ? <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: colors.accent }} /> : null}
                  </Row>
                  <Text variant="muted">{item.body}</Text>
                  <Text variant="small">{new Date(item.created_at).toLocaleString('en-IN')}</Text>
                </View>
              </Row>
            </Card>
          );
        }}
      />
    </Backdrop>
  );
}
