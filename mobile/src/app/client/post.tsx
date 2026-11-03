// Create a Kaam Card: type the job -> AI or template draft -> edit (NE/EN) -> Save & post -> rule result.
import { router } from 'expo-router';
import { useState } from 'react';
import { View } from 'react-native';

import { useDraftCard, useSaveAndPost, useSkills } from '@/api/hooks';
import type { KaamCardDraft, PostResult, Skill } from '@/api/types';
import { Checkbox, Field, useErrorText } from '@/components/forms';
import { KaamCardBody } from '@/components/KaamCard';
import { Mauri } from '@/components/brand/Mauri';
import { SuccessMark } from '@/components/motion';
import { Screen } from '@/components/Screen';
import { StressPanel } from '@/components/StressPanel';
import { Txt } from '@/components/Txt';
import { Bullet, Button, Chip, Panel, Section, StateView, Tag } from '@/components/ui';
import { useT } from '@/i18n';
import { money, toLatinDigits } from '@/lib/format';
import { useDraft } from '@/lib/offline';
import { colors, space } from '@/theme';

const EXAMPLE = '५ वटा दसैं पोस्ट चाहियो';

type PostDraft = {
  text: string;
  card: KaamCardDraft | null;
  source: 'ai' | 'template';
  skill: string;
  pahilo: boolean;
  savedId?: string;
};
const EMPTY_DRAFT: PostDraft = { text: '', card: null, source: 'template', skill: '', pahilo: true };

function guessSkill(card: KaamCardDraft, skills: Skill[]): string {
  const text = `${card.title_en} ${card.title_ne}`.toLowerCase();
  const order = ['video_editing', 'translation', 'data_entry', 'content_writing', 'social_media_posts', 'graphic_design'];
  const hit = order.find((id) => {
    const s = skills.find((k) => k.id === id);
    return s && (text.includes(s.en.toLowerCase().split(' ')[0]) || text.includes(s.ne.split(' ')[0]));
  });
  return hit ?? (text.includes('post') ? 'social_media_posts' : 'graphic_design');
}

const toInt = (v: string) => parseInt(toLatinDigits(v).replace(/[^0-9]/g, '') || '0', 10);

function Editor({ card, setCard, side }: { card: KaamCardDraft; setCard: (c: KaamCardDraft) => void; side: 'ne' | 'en' }) {
  const { t, digits } = useT();
  const key = (base: string) => `${base}_${side}` as const;
  return (
    <View style={{ gap: space.md }}>
      <Field
        label={t('post.fieldTitle')}
        value={card[key('title') as 'title_ne']}
        onChangeText={(v) => setCard({ ...card, [key('title')]: v })}
      />
      <View style={{ flexDirection: 'row', gap: space.md, flexWrap: 'wrap' }}>
        <View style={{ flex: 1, minWidth: 140 }}>
          <Field
            label={t('post.priceUsd')}
            keyboardType="number-pad"
            value={String(Math.round(card.price.amount_minor / 100))}
            onChangeText={(v) => setCard({ ...card, price: { ...card.price, amount_minor: toInt(v) * 100, is_suggestion: false } })}
          />
        </View>
        <View style={{ flex: 1, minWidth: 140 }}>
          <Field
            label={t('post.daysLabel')}
            keyboardType="number-pad"
            value={digits(card.deadline_days)}
            onChangeText={(v) => setCard({ ...card, deadline_days: Math.max(1, Math.min(60, toInt(v) || 1)) })}
          />
        </View>
      </View>
      <Field
        label={t('post.revisionsLabel')}
        keyboardType="number-pad"
        value={digits(card.revisions_included)}
        onChangeText={(v) => setCard({ ...card, revisions_included: Math.min(3, toInt(v)) })}
      />
      {card.checklist.map((c, i) => (
        <Field
          key={c.id}
          label={t('post.checklistItem', { n: i + 1 })}
          value={side === 'ne' ? c.text_ne : c.text_en}
          onChangeText={(v) =>
            setCard({ ...card, checklist: card.checklist.map((x) => (x.id === c.id ? { ...x, [`text_${side}`]: v } : x)) })
          }
        />
      ))}
    </View>
  );
}

function RulesResult({ result }: { result: PostResult }) {
  const { t, pick } = useT();
  const errors = result.rules.filter((r) => r.severity === 'error');
  const warnings = result.rules.filter((r) => r.severity === 'warning');
  return (
    <View style={{ gap: space.md }}>
      {errors.length ? (
        <Panel tone="warn">
          <Section title={t('post.rulesFailed')}>
            {errors.map((r, i) => <Bullet key={i} mark="✗">{pick(r.message_ne, r.message_en)}</Bullet>)}
          </Section>
        </Panel>
      ) : null}
      {warnings.length ? (
        <Panel tone="clay">
          <Section title={t('post.rulesWarnings')}>
            {warnings.map((r, i) => <Bullet key={i} mark="!">{pick(r.message_ne, r.message_en)}</Bullet>)}
          </Section>
        </Panel>
      ) : null}
    </View>
  );
}

export default function PostCard() {
  const { t, pick, locale } = useT();
  // Everything the client typed survives an app restart until the card is posted.
  const draftState = useDraft<PostDraft>('post-card', EMPTY_DRAFT);
  const { text, card, source, skill, pahilo, savedId } = draftState.value;
  const patch = (p: Partial<PostDraft>) => draftState.set((d) => ({ ...d, ...p }));
  const setText = (v: string) => patch({ text: v });
  const setCard = (v: KaamCardDraft) => patch({ card: v });
  const setSkill = (v: string) => patch({ skill: v });
  const setPahilo = (v: boolean) => patch({ pahilo: v });
  const [side, setSide] = useState<'ne' | 'en'>(locale);
  const [result, setResult] = useState<PostResult | null>(null);
  const [postedId, setPostedId] = useState<string | undefined>();
  const draft = useDraftCard();
  const save = useSaveAndPost();
  const skills = useSkills();
  const errorText = useErrorText();

  const makeDraft = () =>
    draft.mutate(text.trim(), {
      onSuccess: (d) => {
        patch({ card: d.card, source: d.source, skill: guessSkill(d.card, skills.data ?? []), savedId: undefined });
        setResult(null);
      },
    });

  const reset = () => {
    draftState.clear();
    setPostedId(undefined);
    setResult(null);
    draft.reset();
  };

  if (result?.posted && postedId) {
    return (
      <Screen title={t('post.title')}>
        <Panel tone="sage" style={{ alignItems: 'center' }}>
          <View style={{ width: 112, height: 104 }}>
            <Mauri pose="card" size={104} motion="burst" />
            <View style={{ position: 'absolute', right: 0, bottom: 0 }}><SuccessMark size={36} label={t('post.saveAndPost')} /></View>
          </View>
          <Txt variant="h2" center>{result.state === 'open' ? t('post.postedOpen') : t('post.pendingReview')}</Txt>
        </Panel>
        <RulesResult result={{ ...result, rules: result.rules.filter((r) => r.severity === 'warning') }} />
        <Button label={t('post.viewCard')} onPress={() => router.push({ pathname: '/manage/[id]', params: { id: postedId } })} />
        <Button kind="secondary" label={t('post.newCard')} onPress={reset} />
      </Screen>
    );
  }

  const blocked = card?.warnings.includes('blocked_work');
  return (
    <Screen title={t('post.title')}>
      {draftState.restored && card ? (
        <Panel tone="sage">
          <Txt>{t('common.draftRestored')}</Txt>
          <Button kind="quiet" label={t('common.discardDraft')} onPress={reset} />
        </Panel>
      ) : null}
      <Section title={t('post.prompt')}>
        <Field label={t('post.prompt')} value={text} onChangeText={setText} placeholder={t('post.placeholder')} multiline />
        <Button kind="quiet" label={t('post.useExample')} onPress={() => setText(EXAMPLE)} />
        <Button label={t('post.make')} busy={draft.isPending} disabled={text.trim().length < 3} onPress={makeDraft} />
      </Section>
      {draft.isPending ? <StateView state="loading" message={t('post.drafting')} /> : null}
      {draft.isError ? <StateView state="error" message={errorText(draft.error) ?? undefined} onRetry={makeDraft} /> : null}
      {card && blocked ? <Panel tone="warn"><Txt variant="h3">{t('post.blocked')}</Txt></Panel> : null}

      {card && !blocked ? (
        <View style={{ gap: space.lg }}>
          <Tag tone={source === 'ai' ? 'brick' : 'clay'} label={source === 'ai' ? t('common.madeWithAi') : t('common.fromTemplate')} />
          {card.needs_clarification.length ? (
            <Panel tone="warn">
              <Section title={t('post.needsClarification')} help={t('post.needsClarificationHelp')}>
                {card.needs_clarification.map((c, i) => <Bullet key={i} mark="?">{pick(c.question_ne, c.question_en)}</Bullet>)}
              </Section>
            </Panel>
          ) : null}
          <Panel tone="clay">
            <Txt variant="label" color={colors.sage}>{card.price.is_suggestion ? t('post.suggestedPrice') : t('post.yourPrice')}</Txt>
            <Txt variant="h1">{money(card.price.amount_minor, card.price.currency)}</Txt>
            <Txt color={colors.inkSoft}>
              {`${t('post.deadline')}: ${t('card.days', { count: card.deadline_days })} · ${t('card.revisions', { count: card.revisions_included })}`}
            </Txt>
          </Panel>
          <KaamCardBody card={card} />

          <Panel>
            <Section title={t('post.editTitle')}>
              <View style={{ flexDirection: 'row', gap: space.sm }} accessibilityRole="tablist">
                <Chip label={t('lang.ne')} on={side === 'ne'} onToggle={() => setSide('ne')} />
                <Chip label={t('lang.en')} on={side === 'en'} onToggle={() => setSide('en')} />
              </View>
              <Editor card={card} setCard={setCard} side={side} />
            </Section>
            <Section title={t('post.skill')}>
              <View style={{ flexDirection: 'row', gap: space.sm, flexWrap: 'wrap' }}>
                {(skills.data ?? []).map((s) => (
                  <Chip key={s.id} label={pick(s.ne, s.en)} on={skill === s.id} onToggle={() => setSkill(s.id)} />
                ))}
              </View>
            </Section>
            <Checkbox label={t('post.pahiloToggle')} checked={pahilo} onChange={setPahilo} />
          </Panel>
          <StressPanel card={card} setCard={setCard} />

          {result && !result.posted ? <RulesResult result={result} /> : null}
          {save.isError ? <Txt color={colors.brick}>{errorText(save.error)}</Txt> : null}
          <Txt variant="small" color={colors.inkSoft}>{t('post.notPostedYet')}</Txt>
          <Button
            label={save.isPending ? t('post.posting') : t('post.saveAndPost')}
            busy={save.isPending}
            disabled={!skill}
            onPress={() =>
              save.mutate(
                { id: savedId, body: { card, skill, pahilo_kaam: pahilo, source } },
                {
                  onSuccess: ({ cardId, result: r }) => {
                    setResult(r);
                    if (r.posted) {
                      setPostedId(cardId);
                      draftState.clear(); // posted: nothing left to restore
                    } else {
                      patch({ savedId: cardId }); // rules failed: next save edits the same card
                    }
                  },
                },
              )
            }
          />
        </View>
      ) : null}
    </Screen>
  );
}
