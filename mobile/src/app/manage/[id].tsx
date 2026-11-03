// The client's card: its state and the one next action (review, reveal, workroom, extend).
import { router, useLocalSearchParams } from 'expo-router';
import { Linking, View } from 'react-native';

import { PUBLIC_BASE } from '@/api/client';
import { useCardAction, useDemo, useOwnerCard, useReveal } from '@/api/hooks';
import type { OwnerCard } from '@/api/types';
import { useErrorText } from '@/components/forms';
import { KaamCardBody } from '@/components/KaamCard';
import { Screen } from '@/components/Screen';
import { Txt } from '@/components/Txt';
import { Button, Panel, Section, StateView, Tag } from '@/components/ui';
import { useT } from '@/i18n';
import { hoursUntil, money } from '@/lib/format';
import { border, colors, space } from '@/theme';

const REVIEW_STATES = ['closed_for_applications', 'in_review'];
const BEFORE_RECEIPT = ['draft', 'ai_drafted', 'client_edited', 'rules_failed', 'rules_passed', 'pending_review', 'approved',
  'open', 'expired', 'closed_for_applications', 'in_review', 'cancelled'];

/** Every applicant by ID, role and status. Names stay hidden until "Reveal & hire" (Fair Pick). */
function ApplicantList({ card }: { card: OwnerCard }) {
  const { t, digits } = useT();
  const hiredName = card.engagement?.worker_display_name ?? null;
  return (
    <Panel>
      <Section title={`${t('manage.applicantsTitle')} · ${digits(card.applicants?.length ?? 0)}`} help={t('manage.applicantsHelp')}>
        {!card.applicants?.length ? <Txt color={colors.inkSoft}>{t('manage.noApplicants')}</Txt> : null}
        {(card.applicants ?? []).map((a) => {
          const hired = a.state === 'picked' && !!hiredName;
          return (
            <View key={a.application_id}
                  style={{ borderTopWidth: border, borderTopColor: colors.line, paddingTop: space.sm, gap: space.xs }}>
              <View style={{ flexDirection: 'row', gap: space.sm, alignItems: 'center', flexWrap: 'wrap' }}>
                <Txt variant="h3">{a.letter ? t('review.applicant', { letter: a.letter }) : a.application_ref}</Txt>
                <Tag label={t('auth.asWorker')} />
                <Tag tone={hired ? 'sage' : a.state === 'picked' ? 'brick' : 'clay'}
                     label={hired ? t('manage.hired') : t(`work.appState_${a.state}`)} />
              </View>
              {a.letter ? (
                <Txt variant="small" color={colors.inkSoft} selectable>{`${t('appCard.id')}: ${a.application_ref}`}</Txt>
              ) : null}
              <Txt variant="small" color={hired ? colors.ink : colors.inkSoft}>
                {`${t('appCard.applicant')}: ${hired ? hiredName : t('manage.nameHidden')}`}
              </Txt>
            </View>
          );
        })}
      </Section>
    </Panel>
  );
}

export default function ManageCard() {
  const { t } = useT();
  const { id } = useLocalSearchParams<{ id: string }>();
  const card = useOwnerCard(id);
  const reveal = useReveal(id);
  const extend = useCardAction(id);
  const demo = useDemo();
  const errorText = useErrorText();

  if (card.isPending) return <Screen back title={t('manage.title')}><StateView state="loading" /></Screen>;
  if (card.isError || !card.data) {
    return <Screen back title={t('manage.title')}><StateView state="error" message={errorText(card.error) ?? undefined} onRetry={() => card.refetch()} /></Screen>;
  }
  const c = card.data;
  const hours = c.state === 'open' ? hoursUntil(c.window_closes_at) : null;
  const goWorkroom = () => c.engagement && router.push({ pathname: '/workroom/[id]', params: { id: c.engagement.id } });
  const error = reveal.error ?? extend.error ?? demo.error;

  return (
    <Screen back title={t('manage.title')}>
      <View style={{ flexDirection: 'row', gap: space.sm, flexWrap: 'wrap' }}>
        <Tag tone="brick" label={t(`cardState.${c.state}`)} />
        {c.pahilo_kaam ? <Tag label={t('board.pahiloTag')} /> : null}
        {c.reviewed_by_sajha ? <Tag tone="sage" label={t('card.reviewed')} /> : null}
      </View>

      <Panel tone="clay">
        {c.state === 'open' ? (
          <>
            <Txt>{t('manage.openWaiting')}</Txt>
            <Txt variant="h3">{t('board.applicants', { count: c.applicant_count, max: c.max_applicants })}</Txt>
            {hours !== null ? <Txt color={colors.inkSoft}>{t('board.closesInHours', { count: hours })}</Txt> : null}
            <Button kind="secondary" label={t('common.demoFastForward')} busy={demo.isPending}
                    onPress={() => demo.mutate(`cards/${c.id}/fast-forward`, { onSuccess: () => card.refetch() })} />
          </>
        ) : null}
        {REVIEW_STATES.includes(c.state) ? (
          <>
            <Txt variant="h3">{t('board.applicants', { count: c.applicant_count, max: c.max_applicants })}</Txt>
            <Button label={t('manage.startReview')} onPress={() => router.push({ pathname: '/review/[id]', params: { id: c.id } })} />
          </>
        ) : null}
        {c.state === 'picked' ? (
          <>
            {c.engagement === null && c.picked_letter ? <Txt>{t('manage.revealExplain', { letter: c.picked_letter })}</Txt> : null}
            <Button label={t('manage.reveal')} busy={reveal.isPending}
                    onPress={() => reveal.mutate({ path: `/v1/cards/${c.id}/reveal` })} />
          </>
        ) : null}
        {c.state === 'revealed' && c.engagement?.worker_display_name ? (
          <Txt variant="h3">{t('manage.revealed', { name: c.engagement.worker_display_name })}</Txt>
        ) : null}
        {c.state === 'worker_declined' ? <Txt>{t('manage.declinedNext')}</Txt> : null}
        {c.state === 'expired' ? (
          <>
            <Txt>{t('manage.expired')}</Txt>
            <Button label={t('manage.extend')} busy={extend.isPending} onPress={() => extend.mutate({ path: `/v1/cards/${c.id}/extend` })} />
          </>
        ) : null}
        {['pending_review', 'ai_drafted', 'client_edited', 'rules_failed', 'rules_passed'].includes(c.state) ? (
          <Txt>{c.state === 'pending_review' ? t('post.pendingReview') : t('manage.draftNote')}</Txt>
        ) : null}
        {c.engagement && !['picked', 'revealed', 'worker_declined'].includes(c.state) ? (
          <Button label={t('manage.openWorkroom')} onPress={goWorkroom} />
        ) : null}
        {error ? <Txt color={colors.brick}>{errorText(error)}</Txt> : null}
      </Panel>

      {!BEFORE_RECEIPT.includes(c.state) && PUBLIC_BASE ? (
        <Panel tone="sage">
          <Txt variant="small">{t('manage.receiptHelp')}</Txt>
          <Button kind="secondary" label={t('manage.receipt')} onPress={() => void Linking.openURL(`${PUBLIC_BASE}/receipt/${c.id}`)} />
        </Panel>
      ) : null}
      <Panel>
        <Txt variant="label" color={colors.sage}>{t('card.fixedPrice')}</Txt>
        <Txt variant="h1">{money(c.price.amount_minor, c.price.currency)}</Txt>
        <Txt color={colors.inkSoft}>{`${t('card.days', { count: c.deadline_days })} · ${t('card.revisions', { count: c.revisions_included })}`}</Txt>
      </Panel>
      <ApplicantList card={c} />
      <KaamCardBody card={c} />
    </Screen>
  );
}
