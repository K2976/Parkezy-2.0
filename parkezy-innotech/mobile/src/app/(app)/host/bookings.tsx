import { useInfiniteQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useState } from 'react';
import { FlatList, View } from 'react-native';

import { errorMessage } from '@/api/client';
import { type BookingGroup, hostApi } from '@/api/endpoints';
import { keys } from '@/hooks/queries';
import { Backdrop } from '@/ui/Backdrop';
import { BookingCard } from '@/ui/BookingCard';
import { Banner, EmptyState, Loading } from '@/ui/components';
import { Segmented } from '@/ui/Segmented';
import { spacing } from '@/ui/theme';

const GROUPS: { key: BookingGroup; label: string }[] = [
  { key: 'upcoming', label: 'Upcoming' },
  { key: 'active', label: 'Parked' },
  { key: 'past', label: 'History' },
];

export default function HostBookings() {
  const [group, setGroup] = useState<BookingGroup>('upcoming');
  const query = useInfiniteQuery({
    queryKey: keys.hostBookings(group),
    queryFn: ({ pageParam }) => hostApi.bookings(group, pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_cursor,
  });
  const items = query.data?.pages.flatMap((p) => p?.items ?? []) ?? [];
  return (
    <Backdrop>
      <FlatList
        data={items}
        keyExtractor={(b) => b.id}
        contentContainerStyle={{ padding: spacing.lg, gap: spacing.lg, flexGrow: 1, paddingBottom: spacing.xxl }}
        refreshing={query.isRefetching}
        onRefresh={() => query.refetch()}
        onEndReached={() => query.hasNextPage && !query.isFetchingNextPage && query.fetchNextPage()}
        ListHeaderComponent={
          <View>
            <Segmented options={GROUPS} value={group} onChange={setGroup} />
          </View>
        }
        renderItem={({ item }) => (
          <BookingCard booking={item} perspective="host" onPress={() => router.push({ pathname: '/booking/[id]', params: { id: item.id } })} />
        )}
        ListFooterComponent={query.isFetchingNextPage ? <Loading /> : null}
        ListEmptyComponent={
          query.isLoading ? (
            <Loading />
          ) : query.isError ? (
            <Banner tone="danger">{errorMessage(query.error)}</Banner>
          ) : (
            <EmptyState icon="calendar-outline" title="Nothing here yet" />
          )
        }
      />
    </Backdrop>
  );
}
