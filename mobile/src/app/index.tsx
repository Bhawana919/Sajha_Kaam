// Entry: language choice on first launch, then role choice (Client / Worker / guest).
// Signed-in users go straight to their role's tabs. Mauri greets once; the rest is calm.
import { Redirect, router } from 'expo-router';
import { View } from 'react-native';
import Svg, { Path } from 'react-native-svg';

import { useMe } from '@/api/hooks';
import { hexPath } from '@/components/brand/geometry';
import { Mauri } from '@/components/brand/Mauri';
import { Icon, type IconName } from '@/components/Icon';
import { BrandStacked } from '@/components/Logo';
import { FadeIn, PressScale } from '@/components/motion';
import { Screen } from '@/components/Screen';
import { Txt } from '@/components/Txt';
import { Button, DemoBanner, Panel, StateView } from '@/components/ui';
import i18n, { applyLocale, deviceLocale, useT } from '@/i18n';
import { usePrefs } from '@/state/prefs';
import { useSession } from '@/state/session';
import { border, colors, radius, space, touchMin } from '@/theme';

function LanguageTile({ label, sub, primary, onPress }: { label: string; sub: string; primary: boolean; onPress: () => void }) {
  return (
    <PressScale
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={onPress}
      style={{
        minHeight: touchMin + 24,
        borderRadius: radius.lg,
        borderWidth: border,
        borderColor: primary ? colors.brickDeep : colors.line,
        borderBottomWidth: primary ? 3 : border,
        backgroundColor: primary ? colors.brick : colors.white,
        paddingHorizontal: space.lg,
        flexDirection: 'row',
        alignItems: 'center',
        gap: space.md,
      }}
    >
      <View style={{ flex: 1 }}>
        <Txt variant="h1" color={primary ? colors.white : colors.ink}>{label}</Txt>
        <Txt variant="small" color={primary ? colors.brickSoft : colors.inkSoft}>{sub}</Txt>
      </View>
      <Icon name="chevronRight" color={primary ? colors.white : colors.inkSoft} />
    </PressScale>
  );
}

function LanguageChoice() {
  const setLocale = usePrefs((s) => s.setLocale);
  const suggested = deviceLocale();
  // Language is not chosen yet, so everything is shown in both, straight from the locale files.
  const [neT, enT] = [i18n.getFixedT('ne'), i18n.getFixedT('en')];
  const choose = (l: 'ne' | 'en') => {
    setLocale(l);
    applyLocale(l);
  };
  const order = suggested === 'ne' ? (['ne', 'en'] as const) : (['en', 'ne'] as const);
  return (
    <Screen scroll header={false}>
      <View style={{ alignItems: 'center', gap: space.md, paddingTop: space.xl }}>
        <Mauri pose="wave" size={148} motion="hover" />
        <BrandStacked />
      </View>
      <FadeIn delay={120} style={{ gap: space.xs }}>
        <Txt variant="h3" center>{neT('mauri.hello')}</Txt>
        <Txt variant="small" color={colors.inkSoft} center>{enT('mauri.hello')}</Txt>
      </FadeIn>
      <FadeIn delay={180} style={{ gap: space.md }}>
        <Txt variant="label" color={colors.sage}>{`${neT('lang.chooseTitle')} · ${enT('lang.chooseTitle')}`}</Txt>
        {order.map((l) => (
          <LanguageTile
            key={l}
            primary={l === suggested}
            label={neT(`lang.${l}`)}
            sub={l === 'ne' ? enT('lang.neName') : neT('lang.enName')}
            onPress={() => choose(l)}
          />
        ))}
        <Txt variant="small" color={colors.inkSoft}>{neT('lang.chooseSub')}</Txt>
      </FadeIn>
    </Screen>
  );
}

function RoleCard({ title, sub, icon, onPress, delay }: { title: string; sub: string; icon: IconName; onPress: () => void; delay: number }) {
  return (
    <FadeIn delay={delay}>
      <PressScale accessibilityRole="button" accessibilityLabel={`${title}. ${sub}`} onPress={onPress}>
        <Panel style={{ flexDirection: 'row', alignItems: 'center' }}>
          <View style={{ width: 56, height: 56, alignItems: 'center', justifyContent: 'center' }}>
            <Svg width={56} height={56} viewBox="0 0 56 56" style={{ position: 'absolute' }}>
              <Path d={hexPath(28, 28, 26)} fill={colors.honeyWash} stroke={colors.honey} strokeWidth={1.5} />
            </Svg>
            <Icon name={icon} size={26} color={colors.ink} />
          </View>
          <View style={{ flex: 1, gap: space.xs }}>
            <Txt variant="h2">{title}</Txt>
            <Txt color={colors.inkSoft}>{sub}</Txt>
          </View>
          <Icon name="chevronRight" size={22} color={colors.inkSoft} />
        </Panel>
      </PressScale>
    </FadeIn>
  );
}

export default function Entry() {
  const { t } = useT();
  const locale = usePrefs((s) => s.locale);
  const signedIn = useSession((s) => !!s.tokens);
  const me = useMe();

  if (!locale) return <LanguageChoice />;
  if (signedIn) {
    if (me.data?.role === 'client') return <Redirect href="/client/post" />;
    if (me.data?.role === 'worker') return <Redirect href="/worker/work" />;
    if (me.data?.role === 'admin') return <Redirect href="/admin" />;
    if (me.isPending) return <Screen><StateView state="loading" /></Screen>;
  }

  const start = (role: 'client' | 'worker') => router.push({ pathname: '/sign-in', params: { role } });
  return (
    <Screen>
      <View style={{ alignItems: 'center', gap: space.sm, paddingTop: space.md }}>
        <Mauri pose="wave" size={112} motion="hover" />
        <Txt variant="h1" center>{t('entry.promise')}</Txt>
        <Txt color={colors.inkSoft} center>{t('common.tagline')}</Txt>
      </View>
      <Txt variant="label" color={colors.sage} accessibilityRole="header">{t('entry.chooseRole')}</Txt>
      <RoleCard icon="work" delay={60} title={t('entry.clientTitle')} sub={t('entry.clientSub')} onPress={() => start('client')} />
      <RoleCard icon="brush" delay={120} title={t('entry.workerTitle')} sub={t('entry.workerSub')} onPress={() => start('worker')} />
      <Button kind="quiet" icon="board" label={t('entry.browseGuest')} onPress={() => router.push('/board')} />
      <DemoBanner />
      <Txt variant="small" color={colors.inkSoft} center>{t('common.closingLine')}</Txt>
    </Screen>
  );
}
