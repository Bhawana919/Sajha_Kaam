// Kaam Card Stress Test: clarity meter + issues with one-tap rewrites. Advice only, never blocks posting.
import { View } from 'react-native';

import { useStressTest } from '@/api/hooks';
import type { KaamCardDraft, StressResult } from '@/api/types';
import { useT } from '@/i18n';
import { colors, space } from '@/theme';

import { useErrorText } from './forms';
import { Txt } from './Txt';
import { Button, Panel, Section, StateView, Tag } from './ui';

type Issue = StressResult['issues'][number];

/** Apply a rewrite: replace a checklist item, or add one for a deliverable that had none. */
export function applyRewrite(card: KaamCardDraft, issue: Issue): KaamCardDraft {
  const text = { text_en: issue.suggested_rewrite_en, text_ne: issue.suggested_rewrite_ne };
  if (card.checklist.some((c) => c.id === issue.item_id)) {
    return { ...card, checklist: card.checklist.map((c) => (c.id === issue.item_id ? { ...c, ...text, testable: true } : c)) };
  }
  if (card.deliverables.some((d) => d.id === issue.item_id)) {
    const n = card.checklist.reduce((m, c) => Math.max(m, parseInt(c.id.replace(/\D/g, ''), 10) || 0), 0) + 1;
    return { ...card, checklist: [...card.checklist, { id: `c${n}`, deliverable_id: issue.item_id, ...text, testable: true }] };
  }
  return card;
}

export function StressPanel({ card, setCard }: { card: KaamCardDraft; setCard: (c: KaamCardDraft) => void }) {
  const { t, pick } = useT();
  const stress = useStressTest();
  const errorText = useErrorText();
  const result = stress.data;
  const isApplied = (i: Issue) =>
    card.checklist.some((c) => c.text_en === i.suggested_rewrite_en && c.text_ne === i.suggested_rewrite_ne);
  const label = (id: string) => {
    const item = card.checklist.find((c) => c.id === id) ?? card.deliverables.find((d) => d.id === id);
    return item ? pick(item.text_ne, item.text_en) : id;
  };

  return (
    <Panel tone="clay">
      <Section title={t('stress.title')} help={t('stress.help')}>
        <Button kind="secondary" label={t('stress.run')} busy={stress.isPending} onPress={() => stress.mutate(card)} />
      </Section>
      {stress.isError ? <StateView state="error" message={errorText(stress.error) ?? undefined} onRetry={() => stress.mutate(card)} /> : null}
      {result ? (
        <View style={{ gap: space.md }}>
          <View style={{ flexDirection: 'row', gap: space.sm, flexWrap: 'wrap' }}>
            <Tag tone={result.source === 'ai' ? 'brick' : 'clay'} label={result.source === 'ai' ? t('common.madeWithAi') : t('stress.ruleBased')} />
          </View>
          <Txt variant="h3">
            {t('stress.meter', { before: result.testable_before, after: result.testable_after_if_all_applied, total: result.total_items })}
          </Txt>
          {result.issues.length === 0 ? <Txt color={colors.sage}>{t('stress.noIssues')}</Txt> : null}
          {result.issues.map((i, n) => (
            <Panel key={`${i.item_id}-${n}`}>
              <Tag tone={i.severity === 'high' ? 'brick' : 'clay'} label={t(`stress.severity_${i.severity}`)} />
              <Txt variant="small" color={colors.inkSoft}>{label(i.item_id)}</Txt>
              <Txt variant="h3">{pick(i.problem_ne, i.problem_en)}</Txt>
              <Txt>{pick(i.why_dispute_risk_ne, i.why_dispute_risk_en)}</Txt>
              {i.suggested_rewrite_en ? (
                <>
                  <Txt color={colors.sage}>{`→ ${pick(i.suggested_rewrite_ne, i.suggested_rewrite_en)}`}</Txt>
                  <Button kind={isApplied(i) ? 'quiet' : 'secondary'} disabled={isApplied(i)}
                          icon={isApplied(i) ? 'check' : undefined} label={isApplied(i) ? t('stress.applied') : t('stress.apply')}
                          onPress={() => setCard(applyRewrite(card, i))} />
                </>
              ) : (
                <Txt variant="small" color={colors.inkSoft}>{t('stress.writeYourOwn')}</Txt>
              )}
            </Panel>
          ))}
        </View>
      ) : null}
    </Panel>
  );
}
