import { useInfiniteQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useState } from 'react';
import { FlatList, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { errorMessage } from '@/api/client';
import { bookingApi, type BookingGroup } from '@/api/endpoints';
import { keys } from '@/hooks/queries';
import { Backdrop } from '@/ui/Backdrop';
import { BookingCard } from '@/ui/BookingCard';
import { Banner, Button, EmptyState, Loading } from '@/ui/components';
import { ScreenTitle } from '@/ui/ScreenTitle';
import { Segmented } from '@/ui/Segmented';
import { spacing } from '@/ui/theme';

const GROUPS: { key: BookingGroup; label: string }[] = [
  { key: 'upcoming', label: 'Upcoming' },
  { key: 'active', label: 'Parked' },
  { key: 'past', label: 'Past' },
];

export default function MyBookings() {
  const [group, setGroup] = useState<BookingGroup>('upcoming');
  const query = useInfiniteQuery({
    queryKey: keys.myBookings(group),
    queryFn: ({ pageParam }) => bookingApi.list(group, pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_cursor,
  });
  const items = query.data?.pages.flatMap((p) => p?.items ?? []) ?? [];

  return (
    <Backdrop>
      <SafeAreaView edges={['top']} style={{ flex: 1 }}>
        <FlatList
          data={items}
          keyExtractor={(b) => b.id}
          contentContainerStyle={{ padding: spacing.lg, gap: spacing.lg, flexGrow: 1, paddingBottom: 130 }}
          refreshing={query.isRefetching}
          onRefresh={() => query.refetch()}
          onEndReached={() => query.hasNextPage && !query.isFetchingNextPage && query.fetchNextPage()}
          ListHeaderComponent={
            <View style={{ gap: spacing.md }}>
              <ScreenTitle title="Bookings" subtitle="Your parking, past and upcoming" />
              <Segmented options={GROUPS} value={group} onChange={setGroup} />
            </View>
          }
          renderItem={({ item }) => (
            <BookingCard booking={item} perspective="driver" onPress={() => router.push({ pathname: '/booking/[id]', params: { id: item.id } })} />
          )}
          ListFooterComponent={query.isFetchingNextPage ? <Loading /> : null}
          ListEmptyComponent={
            query.isLoading ? (
              <Loading />
            ) : query.isError ? (
              <Banner tone="danger">{errorMessage(query.error)}</Banner>
            ) : (
              <EmptyState
                icon="calendar-outline"
                title={group === 'past' ? 'No past bookings' : group === 'active' ? 'You’re not parked anywhere' : 'No upcoming bookings'}
                body="Find a spot near where you’re going."
                action={<Button title="Find parking" icon="search" onPress={() => router.navigate('/')} />}
              />
            )
          }
        />
      </SafeAreaView>
    </Backdrop>
  );
}
