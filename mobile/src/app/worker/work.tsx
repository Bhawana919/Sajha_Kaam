// My work: applications (with checklist feedback), active jobs and completed jobs.
import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, View } from 'react-native';

import { useMyApplications, useMyEngagements, usePassport, useWithdraw } from '@/api/hooks';
import type { MyApplication } from '@/api/types';
import { ApplicationCard } from '@/components/ApplicationCard';
import { KaamPath } from '@/components/brand/Honeycomb';
import { useErrorText } from '@/components/forms';
import { Screen } from '@/components/Screen';
import { Txt } from '@/components/Txt';
import { Bullet, Button, Chip, NextAction, Panel, StateView, Tag } from '@/components/ui';
import { useT } from '@/i18n';
import { money } from '@/lib/format';
import { colors, space } from '@/theme';

const DONE = ['completed', 'passport_issued'];

function ApplicationRow({ a }: { a: MyApplication }) {
  const { t, pick } = useT();
  const withdraw = useWithdraw();
  const offered = a.state === 'picked' && a.card_state === 'revealed' && a.engagement_id;
  return (
    <ApplicationCard a={a} tone={offered ? 'clay' : 'white'}>
      {offered ? (
        <>
          <Txt>{t('work.offer')}</Txt>
          <Button label={t('work.openJob')} onPress={() => router.push({ pathname: '/workroom/[id]', params: { id: a.engagement_id! } })} />
        </>
      ) : null}
      {a.feedback ? (
        <View style={{ gap: space.xs }}>
          <Txt>{t('work.feedbackMet', { met: a.feedback.met, total: a.feedback.total })}</Txt>
          {a.feedback.missing.length ? <Txt variant="label" color={colors.brick}>{t('work.missing')}</Txt> : null}
          {a.feedback.missing.map((m) => <Bullet key={m.id} mark="✗">{pick(m.text_ne, m.text_en)}</Bullet>)}
        </View>
      ) : null}
      {['submitted', 'scored'].includes(a.state) && ['open', 'closed_for_applications', 'in_review'].includes(a.card_state) ? (
        <Button kind="quiet" label={t('work.withdraw')} busy={withdraw.isPending} onPress={() => withdraw.mutate(a.id)} />
      ) : null}
    </ApplicationCard>
  );
}

export default function MyWork() {
  const { t, pick } = useT();
  const apps = useMyApplications();
  const engs = useMyEngagements();
  const errorText = useErrorText();
  const [tab, setTab] = useState<'applications' | 'active' | 'completed'>('applications');
  const accepted = (engs.data ?? []).filter((e) => e.state === 'accepted');
  const active = accepted.filter((e) => !DONE.includes(e.card_state));
  const completed = accepted.filter((e) => DONE.includes(e.card_state));
  const error = apps.error ?? engs.error;
  const passport = usePassport();
  const p = passport.data;
  const offer = (apps.data ?? []).find((a) => a.state === 'picked' && a.card_state === 'revealed' && a.engagement_id);
  const next = offer
    ? { body: t('work.offer'), cta: t('work.openJob'), go: () => router.push({ pathname: '/workroom/[id]', params: { id: offer.engagement_id! } }) }
    : active[0]
      ? { body: pick(active[0].title_ne, active[0].title_en), cta: t('work.openJob'), go: () => router.push({ pathname: '/workroom/[id]', params: { id: active[0].id } }) }
      : apps.isSuccess && apps.data.length === 0
        ? { body: t('work.nextFind'), cta: t('board.title'), go: () => router.push('/worker/board') }
        : null;

  return (
    <Screen title={t('work.title')}>
      {next ? <NextAction title={t('work.nextTitle')} body={next.body} cta={next.cta} onPress={next.go} /> : null}
      {p ? (
        <Panel>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: space.sm }}>
            <Txt variant="label" color={colors.sage}>{t('level.pathTitle')}</Txt>
            <Tag tone="honey" label={pick(p.level.ne, p.level.en)} />
          </View>
          <KaamPath filled={p.confirmed_jobs} toNext={p.jobs_to_next} label={t('level.pathA11y', { count: p.confirmed_jobs })} />
          <Txt variant="small" color={colors.inkSoft}>
            {p.next_level && p.jobs_to_next != null
              ? t('passport.nextLevel', { count: p.jobs_to_next, level: pick(p.next_level.ne, p.next_level.en) })
              : t('level.private')}
          </Txt>
        </Panel>
      ) : null}
      <View style={{ flexDirection: 'row', gap: space.sm, flexWrap: 'wrap' }} accessibilityRole="tablist">
        <Chip label={t('work.applications')} on={tab === 'applications'} onToggle={() => setTab('applications')} />
        <Chip label={t('work.active')} on={tab === 'active'} onToggle={() => setTab('active')} />
        <Chip label={t('work.completed')} on={tab === 'completed'} onToggle={() => setTab('completed')} />
      </View>
      {apps.isPending || engs.isPending ? <StateView state="loading" /> : null}
      {error ? <StateView state="error" message={errorText(error) ?? undefined} onRetry={() => { void apps.refetch(); void engs.refetch(); }} /> : null}

      {tab === 'applications' ? (
        apps.data?.length ? apps.data.map((a) => <ApplicationRow key={a.id} a={a} />) : apps.isSuccess ? (
          <StateView state="empty" message={t('work.empty')}
                     action={<Button label={t('board.title')} onPress={() => router.push('/worker/board')} />} />
        ) : null
      ) : null}

      {tab !== 'applications'
        ? (tab === 'active' ? active : completed).map((e) => (
            <Pressable key={e.id} accessibilityRole="button" onPress={() => router.push({ pathname: '/workroom/[id]', params: { id: e.id } })}>
              <Panel>
                <Tag tone={DONE.includes(e.card_state) ? 'sage' : 'brick'} label={t(`cardState.${e.card_state}`)} />
                <Txt variant="h3">{pick(e.title_ne, e.title_en)}</Txt>
                <Txt color={colors.inkSoft}>{money(e.price_minor, e.currency)}</Txt>
              </Panel>
            </Pressable>
          ))
        : null}
      {tab !== 'applications' && engs.isSuccess && (tab === 'active' ? active : completed).length === 0 ? (
        <StateView state="empty" message={t('work.empty')} />
      ) : null}
    </Screen>
  );
}
