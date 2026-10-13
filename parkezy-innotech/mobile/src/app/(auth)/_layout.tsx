import { Stack } from 'expo-router';

import { fonts, useTheme } from '@/ui/theme';

export default function AuthLayout() {
  const { colors } = useTheme();
  return (
    <Stack
      screenOptions={{
        headerTitle: '',
        headerShadowVisible: false,
        headerBackButtonDisplayMode: 'minimal',
        headerTintColor: colors.accent,
        headerTitleStyle: { fontFamily: fonts.heading },
        headerStyle: { backgroundColor: colors.canvas },
      }}>
      <Stack.Screen name="sign-in" options={{ headerShown: false }} />
      <Stack.Screen name="sign-up" />
      <Stack.Screen name="forgot-password" />
    </Stack>
  );
}
