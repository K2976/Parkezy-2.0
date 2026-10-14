import 'expo-blob';

import { DMSans_400Regular } from '@expo-google-fonts/dm-sans/400Regular';
import { DMSans_500Medium } from '@expo-google-fonts/dm-sans/500Medium';
import { DMSans_700Bold } from '@expo-google-fonts/dm-sans/700Bold';
import { Nunito_800ExtraBold } from '@expo-google-fonts/nunito/800ExtraBold';
import { Nunito_900Black } from '@expo-google-fonts/nunito/900Black';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useFonts } from 'expo-font';
import { DarkTheme, DefaultTheme, Stack, ThemeProvider } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useMemo, useState } from 'react';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { ApiError, NETWORK_ERROR } from '@/api/client';
import { AuthProvider, useAuth } from '@/auth/AuthProvider';
import { fonts, useTheme } from '@/ui/theme';

SplashScreen.preventAutoHideAsync();

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 15_000,
        // Retry only transient failures; a 4xx will not fix itself.
        retry: (count, error) =>
          count < 2 && (!(error instanceof ApiError) || error.code === NETWORK_ERROR || error.status >= 500),
      },
    },
  });
}

function RootNavigator({ fontsReady }: { fontsReady: boolean }) {
  const { status } = useAuth();
  const { colors } = useTheme();
  const header = {
    headerShown: true,
    headerBackButtonDisplayMode: 'minimal' as const,
    headerShadowVisible: false,
    headerTintColor: colors.accent,
    headerTitleStyle: { fontFamily: fonts.heading, color: colors.text },
    headerStyle: { backgroundColor: colors.canvas },
  };
  const ready = status !== 'loading' && fontsReady;
  useEffect(() => {
    if (ready) SplashScreen.hideAsync();
  }, [ready]);
  if (!ready) return null;
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Protected guard={status === 'signedIn'}>
        <Stack.Screen name="(app)" />
      </Stack.Protected>
      <Stack.Protected guard={status === 'signedOut'}>
        <Stack.Screen name="(auth)" />
      </Stack.Protected>
      {/* Reachable signed in or out: sign-up links to the legal pages, and locked-out users need support. */}
      <Stack.Screen name="legal/[doc]" options={{ ...header, title: '' }} />
      <Stack.Screen name="support" options={{ ...header, title: 'Contact support' }} />
    </Stack>
  );
}

export default function RootLayout() {
  const theme = useTheme();
  const [queryClient] = useState(createQueryClient);
  const [fontsLoaded, fontError] = useFonts({
    Nunito_800ExtraBold,
    Nunito_900Black,
    DMSans_400Regular,
    DMSans_500Medium,
    DMSans_700Bold,
  });
  // Navigation chrome uses the same tokens as the app: canvas background, Nunito titles, accent tint.
  const navTheme = useMemo(() => {
    const base = theme.scheme === 'dark' ? DarkTheme : DefaultTheme;
    return {
      ...base,
      colors: {
        ...base.colors,
        primary: theme.colors.accent,
        background: theme.colors.canvas,
        card: theme.colors.canvas,
        text: theme.colors.text,
        border: theme.colors.hairline,
      },
      fonts: {
        ...base.fonts,
        bold: { fontFamily: fonts.heading, fontWeight: '800' as const },
        heavy: { fontFamily: fonts.display, fontWeight: '900' as const },
      },
    };
  }, [theme]);

  return (
    <SafeAreaProvider>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <ThemeProvider value={navTheme}>
            <StatusBar style={theme.scheme === 'dark' ? 'light' : 'dark'} />
            {/* If fonts fail to load we still render with system fonts rather than block the app. */}
            <RootNavigator fontsReady={fontsLoaded || !!fontError} />
          </ThemeProvider>
        </AuthProvider>
      </QueryClientProvider>
    </SafeAreaProvider>
  );
}
