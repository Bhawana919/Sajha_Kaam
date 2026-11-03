// Workroom (both roles): offer -> lock -> deliver -> check & confirm -> payment handoff -> Passport.
// Money never moves through Sajha Kaam: the client pays the worker's own Khalti link outside the app.
import { useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Linking, View } from 'react-native';

import { useEngagement, useEngagementAction, useMessageCheck, useMessages, useOpenCase, useSendMessage } from '@/api/hooks';
import type { EngagementOut } from '@/api/types';
import { Stepper } from '@/components/brand/Honeycomb';
import { Checkbox, Field, useErrorText } from '@/components/forms';
import { SuccessMark } from '@/components/motion';
import { Screen } from '@/components/Screen';
import { Txt } from '@/components/Txt';
import { Bullet, Button, DemoBanner, Panel, Section, StateView, Tag } from '@/components/ui';
import { useT } from '@/i18n';
import { money } from '@/lib/format';
import { colors, space } from '@/theme';

// Accepted -> Delivered -> Confirmed -> Paid -> Passport. "current" is the step being worked on now.
const STEP_KEYS = ['workroom.stepAccepted', 'workroom.stepDelivered', 'workroom.stepConfirmed', 'workroom.stepPaid', 'workroom.stepPassport'];
function stepIndex(state: string): number {
  if (['worker_accepted', 'in_progress', 'revision_requested'].includes(state)) return 1;
  if (state === 'delivered') return 2;
  if (state === 'client_confirmed' || state === 'payment_handoff') return 3;
  if (state === 'completed') return 4;
  if (state === 'passport_issued') return 5;
  return -1;
}

const LOCKED = ['in_progress', 'delivered', 'revision_requested', 'client_confirmed', 'payment_handoff', 'completed',
  'passport_issued', 'disputed'];

function Offer({ e }: { e: EngagementOut }) {
  const { t } = useT();
  const act = useEngagementAction(e.id);
  const errorText = useErrorText();
  const [link, setLink] = useState('');
  return (
    <Panel tone="clay">
      <Txt variant="h2">{t('workroom.offerTitle')}</Txt>
      <Field label={t('workroom.khaltiLabel')} help={t('workroom.khaltiHelp')} value={link} onChangeText={setLink}
             autoCapitalize="none" keyboardType="url" placeholder="https://" />
      {act.isError ? <Txt color={colors.brick}>{errorText(act.error)}</Txt> : null}
      <Button label={t('workroom.accept')} busy={act.isPending} disabled={!link.startsWith('https://')}
              onPress={() => act.mutate({ action: 'accept', body: { khalti_payment_link: link.trim() } })} />
      <Button kind="secondary" label={t('workroom.decline')} disabled={act.isPending} onPress={() => act.mutate({ action: 'decline' })} />
      <Txt variant="small" color={colors.inkSoft}>{t('workroom.declineNote')}</Txt>
    </Panel>
  );
}

function Deliver({ e }: { e: EngagementOut }) {
  const { t } = useT();
  const act = useEngagementAction(e.id);
  const errorText = useErrorText();
  const [note, setNote] = useState('');
  const [link, setLink] = useState('');
  return (
    <Panel>
      <Txt variant="h3">{t('workroom.deliverTitle')}</Txt>
      <Field label={t('workroom.deliverNote')} value={note} onChangeText={setNote} multiline />
      <Field label={`${t('workroom.deliverLink')} (${t('common.optional')})`} value={link} onChangeText={setLink}
             autoCapitalize="none" keyboardType="url" />
      {act.isError ? <Txt color={colors.brick}>{errorText(act.error)}</Txt> : null}
      <Button label={t('workroom.deliver')} busy={act.isPending} disabled={!note.trim()}
              onPress={() => act.mutate({ action: 'deliveries', body: { note: note.trim(), link: link.trim() || null } })} />
    </Panel>
  );
}

function Check({ e }: { e: EngagementOut }) {
  const { t, pick } = useT();
  const act = useEngagementAction(e.id);
  const errorText = useErrorText();
  const [ticks, setTicks] = useState<Record<string, boolean>>({});
  const [notes, setNotes] = useState<Record<string, string>>({});
  const allMet = e.checklist.every((c) => ticks[c.id]);
  const unticked = e.checklist.filter((c) => !ticks[c.id]);
  const canRevise = e.revisions_used < e.revisions_included;
  return (
    <Panel>
      <Txt variant="h3">{t('workroom.checkTitle')}</Txt>
      {e.checklist.map((c) => (
        <Checkbox key={c.id} label={pick(c.text_ne, c.text_en)} checked={!!ticks[c.id]}
                  onChange={(v) => setTicks({ ...ticks, [c.id]: v })} />
      ))}
      <Button label={t('workroom.confirm')} busy={act.isPending} disabled={!allMet}
              onPress={() => act.mutate({ action: 'confirm', body: { checklist: Object.fromEntries(e.checklist.map((c) => [c.id, true])) } })} />
      {!allMet ? <Txt variant="small" color={colors.inkSoft}>{t('workroom.needAll')}</Txt> : null}
      {!allMet && canRevise ? (
        <Section title={t('workroom.revision', { used: e.revisions_used, included: e.revisions_included })} help={t('workroom.revisionNote')}>
          {unticked.map((c) => (
            <Field key={c.id} label={pick(c.text_ne, c.text_en)} value={notes[c.id] ?? ''}
                   onChangeText={(v) => setNotes({ ...notes, [c.id]: v })} />
          ))}
          <Button kind="secondary" label={t('workroom.revision', { used: e.revisions_used, included: e.revisions_included })}
                  disabled={act.isPending || unticked.some((c) => !notes[c.id]?.trim())}
                  onPress={() => act.mutate({ action: 'request-revision', body: { notes: Object.fromEntries(unticked.map((c) => [c.id, notes[c.id].trim()])) } })} />
        </Section>
      ) : null}
      {!allMet && !canRevise ? <Txt variant="small" color={colors.inkSoft}>{t('workroom.noRevisionsLeft')}</Txt> : null}
      {act.isError ? <Txt color={colors.brick}>{errorText(act.error)}</Txt> : null}
    </Panel>
  );
}

function Payment({ e }: { e: EngagementOut }) {
  const { t } = useT();
  const act = useEngagementAction(e.id);
  const errorText = useErrorText();
  const client = e.my_role === 'client';
  if (e.card_state === 'completed' || e.card_state === 'passport_issued') {
    return (
      <Panel tone="sage" style={{ alignItems: 'center' }}>
        <SuccessMark label={t('workroom.done')} />
        <Txt variant="h3" center>{t('workroom.done')}</Txt>
      </Panel>
    );
  }
  return (
    <Panel tone="clay">
      <DemoBanner />
      {e.card_state === 'client_confirmed' && client ? (
        <>
          <Txt variant="h3">{t('workroom.payTitle')}</Txt>
          <Txt variant="h1">{money(e.price_minor, e.currency)}</Txt>
          <Txt>{t('workroom.payExplain')}</Txt>
          {e.khalti_payment_link ? (
            <Button kind="secondary" label={t('workroom.openKhalti')} onPress={() => void Linking.openURL(e.khalti_payment_link!)} />
          ) : null}
          <Button label={t('workroom.iPaid')} busy={act.isPending} onPress={() => act.mutate({ action: 'payment/client-paid' })} />
        </>
      ) : null}
      {e.card_state === 'client_confirmed' && !client ? <Txt>{t('workroom.waitingPayment')}</Txt> : null}
      {e.card_state === 'payment_handoff' && !client ? (
        <>
          <Txt variant="h3">{t('workroom.clientMarkedPaid')}</Txt>
          <Button label={t('workroom.received')} busy={act.isPending} onPress={() => act.mutate({ action: 'payment/worker-received' })} />
        </>
      ) : null}
      {e.card_state === 'payment_handoff' && client ? <Txt>{t('workroom.waitingWorker')}</Txt> : null}
      {act.isError ? <Txt color={colors.brick}>{errorText(act.error)}</Txt> : null}
    </Panel>
  );
}

function Messages({ e }: { e: EngagementOut }) {
  const { t, locale } = useT();
  const open = e.state === 'accepted';
  const list = useMessages(e.id, open);
  const send = useSendMessage(e.id);
  const check = useMessageCheck();
  const [text, setText] = useState('');
  const [warnings, setWarnings] = useState<string[]>([]);
  const doSend = () => send.mutate({ text: text.trim(), lang: locale }, { onSuccess: () => { setText(''); setWarnings([]); } });
  if (!open) return <Txt variant="small" color={colors.inkSoft}>{t('workroom.messagesLocked')}</Txt>;
  return (
    <Section title={t('workroom.messages')}>
      {(list.data ?? []).map((m) => (
        <View key={m.id} style={{ alignSelf: m.mine ? 'flex-end' : 'flex-start', maxWidth: '85%' }}>
          <Panel tone={m.mine ? 'sage' : 'white'} style={{ padding: space.md }}>
            <Txt>{m.text}</Txt>
          </Panel>
        </View>
      ))}
      <Field label={t('workroom.messagePlaceholder')} value={text} onChangeText={(v) => { setText(v); setWarnings([]); }} multiline />
      {warnings.length ? (
        <Panel tone="warn">
          {warnings.map((w) => <Bullet key={w} mark="!">{t(`workroom.warn_${w}`)}</Bullet>)}
          <Button kind="secondary" label={t('workroom.sendAnyway')} onPress={doSend} />
        </Panel>
      ) : (
        <Button label={t('common.send')} disabled={!text.trim()} busy={send.isPending || check.isPending}
                onPress={() => check.mutate(text, { onSuccess: (w) => (w.length ? setWarnings(w) : doSend()) })} />
      )}
    </Section>
  );
}

function OpenCase({ e }: { e: EngagementOut }) {
  const { t } = useT();
  const open = useOpenCase();
  const errorText = useErrorText();
  const [reason, setReason] = useState('');
  if (open.isSuccess) return <Panel tone="sage"><Txt>{t('workroom.caseOpened')}</Txt></Panel>;
  return (
    <Panel tone="clay">
      <Field label={t('workroom.caseReason')} value={reason} onChangeText={setReason} multiline />
      {open.isError ? <Txt color={colors.brick}>{errorText(open.error)}</Txt> : null}
      <Button kind="secondary" label={t('workroom.openCase')} disabled={reason.trim().length < 3} busy={open.isPending}
              onPress={() => open.mutate({ card_id: e.card_id, reason: reason.trim() })} />
    </Panel>
  );
}

export default function Workroom() {
  const { t, pick, digits, country } = useT();
  const { id } = useLocalSearchParams<{ id: string }>();
  const eng = useEngagement(id);
  const errorText = useErrorText();

  if (eng.isPending) return <Screen back title={t('workroom.title')}><StateView state="loading" /></Screen>;
  if (eng.isError || !eng.data) {
    return <Screen back title={t('workroom.title')}><StateView state="error" message={errorText(eng.error) ?? undefined} onRetry={() => eng.refetch()} /></Screen>;
  }
  const e = eng.data;
  const worker = e.my_role === 'worker';
  const locked = LOCKED.includes(e.card_state);
  const due = e.due_at ? digits(e.due_at.slice(0, 10)) : null;

  return (
    <Screen back title={t('workroom.title')}>
      {stepIndex(e.card_state) >= 0 ? (
        <Panel>
          <Stepper
            steps={STEP_KEYS.map((k) => t(k))}
            current={stepIndex(e.card_state)}
            caption={t('workroom.stepCaption', {
              n: Math.min(stepIndex(e.card_state) + 1, STEP_KEYS.length),
              total: STEP_KEYS.length,
              label: t(STEP_KEYS[Math.min(stepIndex(e.card_state), STEP_KEYS.length - 1)]),
            })}
          />
        </Panel>
      ) : null}
      <Tag tone="brick" label={t(`cardState.${e.card_state}`)} />
      <Txt variant="h2">{pick(e.title_ne, e.title_en)}</Txt>
      <Panel tone="clay">
        <Txt variant="h1">{money(e.price_minor, e.currency)}</Txt>
        <Txt color={colors.inkSoft}>
          {worker ? t('board.clientIn', { country: country(e.client_country) }) : e.worker_display_name ?? ''}
        </Txt>
        {due ? <Txt>{t('workroom.due', { date: due })}</Txt> : null}
        {locked ? <Txt variant="small" color={colors.inkSoft}>{t('workroom.locked')}</Txt> : null}
        {worker ? (
          <>
            <Txt variant="small">{t('workroom.fee')}</Txt>
            <Txt variant="small" color={colors.inkSoft}>{t('workroom.providerFees')}</Txt>
          </>
        ) : null}
      </Panel>

      {worker && e.state === 'offered' && e.card_state === 'revealed' ? <Offer e={e} /> : null}

      <Section title={t('card.doneWhen')}>
        {e.checklist.map((c) => <Bullet key={c.id} mark="☐">{pick(c.text_ne, c.text_en)}</Bullet>)}
      </Section>

      {e.deliveries.length ? (
        <Section title={t('workroom.deliveries')}>
          {e.deliveries.map((d) => (
            <Panel key={d.id}>
              <Txt>{d.note}</Txt>
              {d.link ? <Txt variant="small" color={colors.sage}>{d.link}</Txt> : null}
              {d.revision_notes ? (
                <View style={{ gap: space.xs }}>
                  <Txt variant="label" color={colors.brick}>{t('workroom.revisionAsked')}</Txt>
                  {Object.entries(d.revision_notes).map(([itemId, note]) => {
                    const item = e.checklist.find((c) => c.id === itemId);
                    return <Bullet key={itemId} mark="!">{`${item ? pick(item.text_ne, item.text_en) : itemId}: ${note}`}</Bullet>;
                  })}
                </View>
              ) : null}
            </Panel>
          ))}
        </Section>
      ) : null}

      {worker && ['in_progress', 'revision_requested'].includes(e.card_state) ? <Deliver e={e} /> : null}
      {!worker && e.card_state === 'delivered' ? <Check e={e} /> : null}
      {['client_confirmed', 'payment_handoff', 'completed', 'passport_issued'].includes(e.card_state) ? <Payment e={e} /> : null}

      {e.state !== 'declined' ? <Messages e={e} /> : null}
      {locked && !['completed', 'passport_issued', 'disputed'].includes(e.card_state) ? <OpenCase e={e} /> : null}
    </Screen>
  );
}
