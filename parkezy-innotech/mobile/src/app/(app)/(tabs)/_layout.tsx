import { useQuery } from '@tanstack/react-query';
import { Tabs } from 'expo-router';

import { notificationApi } from '@/api/endpoints';
import { keys } from '@/hooks/queries';
import { GlassTabBar } from '@/ui/GlassTabBar';

export default function TabsLayout() {
  const { data } = useQuery({
    queryKey: keys.notifications,
    queryFn: () => notificationApi.list(),
    refetchInterval: 60_000,
  });
  return (
    // Each tab draws its own large title over the ambient backdrop, so native headers are off.
    <Tabs tabBar={(props) => <GlassTabBar {...props} />} screenOptions={{ headerShown: false }}>
      <Tabs.Screen name="index" options={{ title: 'Find' }} />
      <Tabs.Screen name="bookings" options={{ title: 'Bookings' }} />
      <Tabs.Screen name="host" options={{ title: 'Host' }} />
      <Tabs.Screen name="account" options={{ title: 'Account', tabBarBadge: data?.unread_count || undefined }} />
    </Tabs>
  );
}
