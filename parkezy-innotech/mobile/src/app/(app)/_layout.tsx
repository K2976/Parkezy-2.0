import { Stack } from 'expo-router';

import { fonts, useTheme } from '@/ui/theme';

export const unstable_settings = { initialRouteName: '(tabs)' };

export default function AppLayout() {
  const { colors } = useTheme();
  return (
    <Stack
      screenOptions={{
        headerBackButtonDisplayMode: 'minimal',
        headerShadowVisible: false,
        headerTintColor: colors.accent,
        headerTitleStyle: { fontFamily: fonts.heading, color: colors.text },
        headerStyle: { backgroundColor: colors.canvas },
      }}>
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen name="verify-email" options={{ title: 'Verify email', presentation: 'modal' }} />
      <Stack.Screen name="listing/[id]" options={{ title: '' }} />
      <Stack.Screen name="booking/[id]" options={{ title: 'Booking' }} />
      <Stack.Screen name="notifications" options={{ title: 'Notifications' }} />
      <Stack.Screen name="report/[bookingId]" options={{ title: 'Report a problem', presentation: 'modal' }} />
      <Stack.Screen name="host/new-listing" options={{ title: 'New parking spot' }} />
      <Stack.Screen name="host/listing/[id]" options={{ title: 'Manage spot' }} />
      <Stack.Screen name="host/bookings" options={{ title: 'Bookings' }} />
      <Stack.Screen name="host/scan" options={{ title: 'Check a driver in or out' }} />
      <Stack.Screen name="account/profile" options={{ title: 'Profile' }} />
      <Stack.Screen name="account/password" options={{ title: 'Change password' }} />
      <Stack.Screen name="account/delete" options={{ title: 'Delete account' }} />
    </Stack>
  );
}
