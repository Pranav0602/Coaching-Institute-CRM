/**
 * App root: fonts, theme, query cache and the session provider.
 *
 * Provider order matters. The theme must be resolved before Paper mounts (Paper
 * reads it once), and the auth provider must sit above anything that could fire a
 * request, because a query that runs before the session is restored is a guaranteed
 * 401.
 */
/**
 * Per-weight subpath imports, not the package root. The root re-exports every
 * weight *and* every italic, which Metro would then bundle - roughly 1.4MB of
 * typefaces the app never renders.
 */
import { useFonts } from 'expo-font';
import PlusJakartaSans_400Regular from '@expo-google-fonts/plus-jakarta-sans/400Regular/PlusJakartaSans_400Regular.ttf';
import PlusJakartaSans_500Medium from '@expo-google-fonts/plus-jakarta-sans/500Medium/PlusJakartaSans_500Medium.ttf';
import PlusJakartaSans_600SemiBold from '@expo-google-fonts/plus-jakarta-sans/600SemiBold/PlusJakartaSans_600SemiBold.ttf';
import PlusJakartaSans_700Bold from '@expo-google-fonts/plus-jakarta-sans/700Bold/PlusJakartaSans_700Bold.ttf';
import PlusJakartaSans_800ExtraBold from '@expo-google-fonts/plus-jakarta-sans/800ExtraBold/PlusJakartaSans_800ExtraBold.ttf';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import React, { useEffect, useMemo } from 'react';
import { LogBox } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { PaperProvider } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { ApiError } from '@/api/client';
import { buildTheme } from '@/constants/theme';
import { AuthProvider } from '@/context/AuthContext';
import { ThemeProvider, useThemeMode } from '@/context/ThemeContext';
import { PaperIcon } from '@/theme/PaperIcon';

void SplashScreen.preventAutoHideAsync();
LogBox.ignoreLogs(['Sending network request from view manager']);

/**
 * Queries are cached for five minutes and retried once, except on 4xx: a 404 or a
 * 403 will not become a 200 on a second attempt, and retrying only delays the
 * error the user needs to see.
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      gcTime: 30 * 60 * 1000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false;
        return failureCount < 1;
      },
    },
  },
});

const Navigation = () => {
  const { mode, isDark } = useThemeMode();
  const theme = useMemo(() => buildTheme(mode), [mode]);

  return (
    <PaperProvider theme={theme} settings={{ icon: PaperIcon }}>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: theme.colors.background },
        }}
      />
    </PaperProvider>
  );
};

export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts({
    PlusJakartaSans_400Regular,
    PlusJakartaSans_500Medium,
    PlusJakartaSans_600SemiBold,
    PlusJakartaSans_700Bold,
    PlusJakartaSans_800ExtraBold,
  });

  useEffect(() => {
    // A font failure must not strand the user on the splash screen; fall through
    // to the system font rather than showing nothing at all.
    if (fontsLoaded || fontError) void SplashScreen.hideAsync();
  }, [fontsLoaded, fontError]);

  if (!fontsLoaded && !fontError) return null;

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <ThemeProvider>
          <QueryClientProvider client={queryClient}>
            <AuthProvider>
              <Navigation />
            </AuthProvider>
          </QueryClientProvider>
        </ThemeProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
