// Every screen: safe area, a header with the persistent ने | EN switch, scrollable content.
import { router } from 'expo-router';
import type { ReactNode } from 'react';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useUpdateMe } from '@/api/hooks';
import { applyLocale, useT } from '@/i18n';
import { useOffline } from '@/lib/offline';
import { usePrefs } from '@/state/prefs';
import { useSession } from '@/state/session';
import { border, colors, contentMaxWidth, radius, space, touchMin } from '@/theme';

import { Mauri } from './brand/Mauri';
import { Icon } from './Icon';
import { Txt } from './Txt';

export function LangSwitch() {
  const { t, locale } = useT();
  const setLocale = usePrefs((s) => s.setLocale);
  const signedIn = useSession((s) => !!s.tokens);
  const updateMe = useUpdateMe();
  const choose = (l: 'ne' | 'en') => {
    setLocale(l);
    applyLocale(l);
    // Saved on the profile too, so notices and AI output follow the choice next session.
    if (signedIn) updateMe.mutate({ locale: l });
  };
  return (
    <View style={styles.switch} accessibilityRole="radiogroup" accessibilityLabel={t('lang.switchA11y')}>
      {(['ne', 'en'] as const).map((l) => (
        <Pressable
          key={l}
          accessibilityRole="radio"
          accessibilityState={{ checked: locale === l }}
          accessibilityLabel={l === 'ne' ? 'नेपाली' : 'English'}
          onPress={() => choose(l)}
          style={[styles.switchSide, locale === l && styles.switchOn]}
        >
          <Txt variant="h3" color={locale === l ? colors.white : colors.ink}>{l === 'ne' ? 'ने' : 'EN'}</Txt>
        </Pressable>
      ))}
    </View>
  );
}

type Props = {
  title?: string;
  back?: boolean;
  scroll?: boolean;
  children: ReactNode;
  edges?: ('top' | 'bottom')[];
  /** false hides the header row (welcome screens that carry their own brand). */
  header?: boolean;
};

/** Shown under every header while the phone has no connection. No countdowns, no pressure. */
export function OfflineBanner() {
  const { t } = useT();
  if (!useOffline()) return null;
  return (
    <View style={styles.offline} accessibilityRole="alert" accessibilityLiveRegion="polite">
      <Mauri pose="sleep" size={36} />
      <View style={{ flex: 1 }}>
        <Txt variant="small" color={colors.warnInk}>{t('common.offline')}</Txt>
      </View>
      <Icon name="wifiOff" size={18} color={colors.warnInk} />
    </View>
  );
}

export function Screen({ title, back, scroll = true, children, edges = ['top'], header = true }: Props) {
  const { t } = useT();
  const body = <View style={styles.body}>{children}</View>;
  return (
    <SafeAreaView style={styles.root} edges={edges}>
      {header ? (
      <View style={styles.header}>
        <View style={styles.headerRow}>
          {back ? (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={t('common.back')}
              onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))}
              style={styles.back}
            >
              <Icon name="chevronLeft" size={26} />
            </Pressable>
          ) : null}
          <Txt variant="h2" accessibilityRole="header" style={{ flex: 1 }} numberOfLines={2}>
            {title ?? t('common.appName')}
          </Txt>
          <LangSwitch />
        </View>
      </View>
      ) : null}
      <OfflineBanner />
      {scroll ? (
        <ScrollView contentContainerStyle={{ paddingBottom: space.xxl }} keyboardShouldPersistTaps="handled">
          {body}
        </ScrollView>
      ) : (
        body
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.paper },
  header: { paddingHorizontal: space.lg, paddingVertical: space.sm, borderBottomWidth: border, borderBottomColor: colors.line },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.sm,
    width: '100%',
    maxWidth: contentMaxWidth,
    alignSelf: 'center',
  },
  back: { minWidth: touchMin, minHeight: touchMin, justifyContent: 'center' },
  body: { flex: 1, padding: space.lg, gap: space.lg, width: '100%', maxWidth: contentMaxWidth, alignSelf: 'center' },
  offline: { backgroundColor: colors.warnSoft, paddingHorizontal: space.lg, paddingVertical: space.xs, flexDirection: 'row', alignItems: 'center', gap: space.sm },
  switch: { flexDirection: 'row', borderWidth: border, borderColor: colors.line, borderRadius: radius.md, overflow: 'hidden' },
  switchSide: { minWidth: touchMin, minHeight: touchMin - 4, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.white },
  switchOn: { backgroundColor: colors.ink },
});
