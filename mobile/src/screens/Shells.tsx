// Screens shared by both roles: the bilingual inbox and Help (numerals, sign out, demo reset).
import { useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { Pressable, View } from 'react-native';

import { USE_MOCK } from '@/api/client';
import { useDemo, useMe, useNotifications, useReadAll, useUpdateMe } from '@/api/hooks';
import type { NotificationOut } from '@/api/types';
import { Mauri } from '@/components/brand/Mauri';
import { useErrorText } from '@/components/forms';
import { Screen } from '@/components/Screen';
import { Txt } from '@/components/Txt';
import { Button, Chip, Panel, Section, StateView } from '@/components/ui';
import { useT } from '@/i18n';
import { usePrefs } from '@/state/prefs';
import { useSession } from '@/state/session';
import { colors, space } from '@/theme';

function notificationTarget(n: NotificationOut, role: string | undefined): { pathname: string; params: { id: string } } | null {
  const p = n.params as { engagement_id?: string; card_id?: string };
  if (p.engagement_id) return { pathname: '/workroom/[id]', params: { id: p.engagement_id } };
  if (p.card_id && role === 'client') return { pathname: '/manage/[id]', params: { id: p.card_id } };
  return null;
}

export function InboxScreen() {
  const { t, pick } = useT();
  const list = useNotifications();
  const readAll = useReadAll();
  const me = useMe();
  const errorText = useErrorText();
  const unread = (list.data ?? []).some((n) => !n.read);
  return (
    <Screen title={t('inbox.title')}>
      {list.isPending ? <StateView state="loading" /> : null}
      {list.isError ? <StateView state="error" message={errorText(list.error) ?? undefined} onRetry={() => list.refetch()} /> : null}
      {list.isSuccess && list.data.length === 0 ? <StateView state="empty" message={t('inbox.empty')} /> : null}
      {unread ? <Button kind="quiet" label={t('notif.markRead')} onPress={() => readAll.mutate()} /> : null}
      {(list.data ?? []).map((n) => {
        const p = n.params as Record<string, string | number>;
        const title = pick(String(p.title_ne ?? ''), String(p.title_en ?? ''));
        const target = notificationTarget(n, me.data?.role);
        return (
          <Pressable key={n.id} accessibilityRole={target ? 'button' : 'text'} disabled={!target}
                     onPress={() => target && router.push(target as never)}>
            <Panel tone={n.read ? 'white' : 'clay'}>
              <Txt>{t(`notif.${n.type}`, { ...p, title })}</Txt>
            </Panel>
          </Pressable>
        );
      })}
    </Screen>
  );
}

export function HelpScreen() {
  const { t, locale } = useT();
  const me = useMe();
  const qc = useQueryClient();
  const clear = useSession((s) => s.clear);
  const { numerals, setNumerals, lite, setLite } = usePrefs();
  const updateMe = useUpdateMe();
  const demo = useDemo();

  const chooseNumerals = (n: 'devanagari' | 'latin') => {
    setNumerals(n);
    updateMe.mutate({ numerals_pref: n });
  };
  const signOut = async () => {
    await clear();
    qc.clear();
    router.replace('/');
  };

  return (
    <Screen title={t('help.title')}>
      <Panel tone="honey" style={{ flexDirection: 'row', alignItems: 'center' }}>
        <Mauri pose="wave" size={64} />
        <Txt style={{ flex: 1 }}>{t('help.body')}</Txt>
      </Panel>
      {locale === 'ne' ? (
        <Section title={t('common.numerals')}>
          <View style={{ flexDirection: 'row', gap: space.sm, flexWrap: 'wrap' }}>
            <Chip label={t('common.numeralsDevanagari')} on={numerals === 'devanagari'} onToggle={() => chooseNumerals('devanagari')} />
            <Chip label={t('common.numeralsLatin')} on={numerals === 'latin'} onToggle={() => chooseNumerals('latin')} />
          </View>
        </Section>
      ) : null}
      <Section title={t('help.lite')} help={t('help.liteHelp')}>
        <View style={{ flexDirection: 'row' }}>
          <Chip label={t('help.lite')} on={lite} onToggle={() => setLite(!lite)} />
        </View>
      </Section>
      {me.data ? <Txt color={colors.inkSoft}>{t('common.signedInAs', { name: me.data.display_name })}</Txt> : null}
      <Button kind="secondary" label={t('common.signOut')} onPress={() => void signOut()} />
      {!USE_MOCK ? (
        <Button kind="quiet" label={t('common.demoReset')} busy={demo.isPending}
                onPress={() => demo.mutate('reset', { onSuccess: () => void signOut() })} />
      ) : null}
    </Screen>
  );
}
