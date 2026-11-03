import { Inter_400Regular, Inter_600SemiBold } from '@expo-google-fonts/inter';
import { NotoSansDevanagari_400Regular, NotoSansDevanagari_600SemiBold } from '@expo-google-fonts/noto-sans-devanagari';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { AnimatedSplash } from '@/components/AnimatedSplash';
import { applyLocale } from '@/i18n';
import { useMotionOK } from '@/lib/motion';
import '@/lib/offline';
import { usePrefs } from '@/state/prefs';
import { useSession } from '@/state/session';
import { colors } from '@/theme';

// Keep the native splash up until the JS splash (same picture) has drawn its first frame.
SplashScreen.preventAutoHideAsync().catch(() => undefined);

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000, gcTime: 10 * 60_000 } },
});

function usePrefsHydrated() {
  const [hydrated, setHydrated] = useState(usePrefs.persist.hasHydrated());
  useEffect(() => usePrefs.persist.onFinishHydration(() => setHydrated(true)), []);
  return hydrated;
}

export default function RootLayout() {
  // 400 + 600 only: "bold" is semibold everywhere (smaller APK, one less font to load).
  const [fontsLoaded, fontError] = useFonts({
    Inter_400Regular,
    Inter_600SemiBold,
    NotoSansDevanagari_400Regular,
    NotoSansDevanagari_600SemiBold,
  });
  const hydrated = usePrefsHydrated();
  const locale = usePrefs((s) => s.locale);
  const { loaded: sessionLoaded, load } = useSession();
  const [splashDone, setSplashDone] = useState(false);
  const motionOK = useMotionOK();

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (hydrated && locale) applyLocale(locale);
  }, [hydrated, locale]);

  // If fonts fail to load we still start: system fonts are the fallback.
  const fontsReady = fontsLoaded || !!fontError;
  const ready = fontsReady && hydrated && sessionLoaded;

  return (
    <View style={{ flex: 1, backgroundColor: colors.brick }}>
      {ready ? (
        <SafeAreaProvider>
          <QueryClientProvider client={queryClient}>
            <StatusBar style={splashDone ? 'dark' : 'light'} />
            <Stack
              screenOptions={{
                headerShown: false,
                contentStyle: { backgroundColor: colors.paper },
                // A short push from the right: a clear "forward" with a parallax back-stack.
                animation: motionOK ? 'ios_from_right' : 'none',
                animationDuration: 260,
                gestureEnabled: true,
              }}
            >
              <Stack.Screen name="index" options={{ animation: motionOK ? 'fade' : 'none' }} />
            </Stack>
          </QueryClientProvider>
        </SafeAreaProvider>
      ) : null}
      {!splashDone ? <AnimatedSplash ready={ready} fontsReady={fontsReady} onDone={() => setSplashDone(true)} /> : null}
    </View>
  );
}
