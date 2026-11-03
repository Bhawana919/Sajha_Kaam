// Fair Pick blind review: applicants A, B, C... scored 1-3 stars per checklist item.
// Only BlindApplicant data reaches this screen; names arrive only after "Reveal & hire".
import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { View } from 'react-native';

import { useBlindReview, useCardAction, useOwnerCard, usePick, useScore, useTranslate } from '@/api/hooks';
import type { BlindApplicant } from '@/api/types';
import { LetterCell } from '@/components/brand/Honeycomb';
import { Checkbox, Field, Stars, useErrorText } from '@/components/forms';
import { Screen } from '@/components/Screen';
import { Txt } from '@/components/Txt';
import { Button, Chip, DemoBanner, Panel, Section, StateView, Tag } from '@/components/ui';
import { useT } from '@/i18n';
import { colors, space } from '@/theme';

/** Applicant text with an AI translate toggle (after Leak Guard; never used to score). */
function Translatable({ text, lang }: { text: string; lang: string }) {
  const { t, locale } = useT();
  const translate = useTranslate();
  const [shown, setShown] = useState<'original' | 'translated'>('original');
  const canTranslate = lang !== locale;
  const translated = translate.data;
  return (
    <View style={{ gap: space.xs }}>
      <Txt>{shown === 'translated' && translated ? translated.text : text}</Txt>
      {canTranslate ? (
        <View style={{ flexDirection: 'row', gap: space.sm, alignItems: 'center', flexWrap: 'wrap' }}>
          <Button
            kind="quiet"
            label={shown === 'translated' ? t('common.showOriginal') : t('common.translate')}
            busy={translate.isPending}
            onPress={() => {
              if (shown === 'translated') return setShown('original');
              if (!translated) translate.mutate({ text, target: locale });
              setShown('translated');
            }}
          />
          {shown === 'translated' && translated?.source === 'ai' ? <Tag tone="brick" label={t('common.translatedByAi')} /> : null}
          {shown === 'translated' && translated?.source === 'original' ? <Txt variant="small" color={colors.inkSoft}>{t('common.noTranslation')}</Txt> : null}
        </View>
      ) : null}
    </View>
  );
}

function ApplicantPanel({ a, checklist, saved, saving, onSave }: {
  a: BlindApplicant;
  checklist: { id: string; text_ne: string; text_en: string }[];
  saved: Record<string, number> | undefined;
  saving: boolean;
  onSave: (stars: Record<string, number>) => void;
}) {
  const { t, pick, digits } = useT();
  const [stars, setStars] = useState<Record<string, number>>(saved ?? {});
  const complete = checklist.every((c) => stars[c.id]);
  const total = Object.values(stars).reduce((s, n) => s + n, 0);
  const dirty = checklist.some((c) => (stars[c.id] ?? 0) !== (saved?.[c.id] ?? 0));
  return (
    <Panel>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: space.sm }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.md }}>
          <LetterCell letter={a.letter} />
          <Txt variant="h2">{t('review.applicant', { letter: a.letter })}</Txt>
        </View>
        <Tag label={t('review.confirmedJobs', { count: a.confirmed_jobs })} />
      </View>
      <Txt variant="small" color={colors.inkSoft}>{t('review.notScored')}</Txt>
      <Section title={t('review.sample')}>
        <Translatable text={a.sample_text} lang={a.sample_lang} />
      </Section>
      <Section title={t('review.answers')}>
        {a.answers.map((ans) => (
          <View key={ans.question_index} style={{ flexDirection: 'row', gap: space.sm }}>
            <Txt>{`${digits(ans.question_index + 1)}.`}</Txt>
            <View style={{ flex: 1 }}><Translatable text={ans.text} lang={ans.lang} /></View>
          </View>
        ))}
      </Section>
      {checklist.map((c) => (
        <Stars key={c.id} label={pick(c.text_ne, c.text_en)} value={stars[c.id] ?? 0}
               onChange={(n) => setStars({ ...stars, [c.id]: n })} />
      ))}
      <Txt variant="h3">{t('review.total', { total, max: checklist.length * 3 })}</Txt>
      <Button kind={saved && !dirty ? 'secondary' : 'primary'} icon={saved && !dirty ? 'check' : undefined} label={t('common.save')}
              busy={saving} disabled={!complete || (!!saved && !dirty)} onPress={() => onSave(stars)} />
    </Panel>
  );
}

export default function BlindReviewScreen() {
  const { t, digits } = useT();
  const { id } = useLocalSearchParams<{ id: string }>();
  const review = useBlindReview(id);
  const owner = useOwnerCard(id);
  const score = useScore(id);
  const attest = useCardAction(id);
  const pick = usePick(id);
  const errorText = useErrorText();
  const [tieChoice, setTieChoice] = useState<string | null>(null);
  const [tieNote, setTieNote] = useState('');

  if (review.isPending || owner.isPending) return <Screen back title={t('review.title')}><StateView state="loading" /></Screen>;
  if (review.isError || !review.data || !owner.data) {
    return <Screen back title={t('review.title')}><StateView state="error" message={errorText(review.error) ?? undefined} onRetry={() => review.refetch()} /></Screen>;
  }
  const r = review.data;
  const scores = r.scores ?? {};
  const checklist = owner.data.checklist;
  const scored = r.applicants.filter((a) => scores[a.application_id]).length;
  const totals = r.applicants.map((a) => ({ a, total: Object.values(scores[a.application_id] ?? {}).reduce((s, n) => s + n, 0) }));
  const top = Math.max(0, ...totals.map((x) => x.total));
  const tied = totals.filter((x) => x.total === top && scored === r.applicants.length);
  const isTie = tied.length > 1;
  const done = !['closed_for_applications', 'in_review'].includes(r.state);

  // The card screen opened this one: go back to it rather than stacking a second copy.
  const backToCard = () => (router.canGoBack() ? router.back() : router.replace({ pathname: '/manage/[id]', params: { id } }));
  const doPick = () =>
    pick.mutate(
      { path: `/v1/cards/${id}/pick`, body: isTie ? { application_id: tieChoice, tie_note: tieNote } : {} },
      { onSuccess: backToCard },
    );

  return (
    <Screen back title={t('review.title')}>
      <Txt color={colors.inkSoft}>{t('review.intro')}</Txt>
      <Txt variant="small" color={colors.inkSoft}>{t('review.scoreHelp')}</Txt>
      <DemoBanner />
      {r.applicants.length === 0 ? <StateView state="empty" message={t('review.empty')} /> : null}
      {r.applicants.map((a) => (
        <ApplicantPanel key={a.application_id} a={a} checklist={checklist} saved={scores[a.application_id]}
                        saving={score.isPending && score.variables?.applicationId === a.application_id}
                        onSave={(stars) => score.mutate({ applicationId: a.application_id, stars })} />
      ))}
      {score.isError ? <Txt color={colors.brick}>{errorText(score.error)}</Txt> : null}

      {!done ? (
        <Panel tone="clay">
          <Txt variant="h3">{t('review.scoredCount', { done: scored, count: r.applicant_count })}</Txt>
          <Checkbox label={t('review.attest')} checked={r.attested_unacquainted}
                    onChange={(v) => v && !r.attested_unacquainted && attest.mutate({ path: `/v1/cards/${id}/attest-unacquainted` })} />
          {isTie ? (
            <Section title={t('review.tieTitle')}>
              <View style={{ flexDirection: 'row', gap: space.sm, flexWrap: 'wrap' }}>
                {tied.map(({ a }) => (
                  <Chip key={a.application_id} label={`${t('review.applicant', { letter: a.letter })} · ${digits(top)}`}
                        on={tieChoice === a.application_id} onToggle={() => setTieChoice(a.application_id)} />
                ))}
              </View>
              <Field label={t('review.tieReason')} value={tieNote} onChangeText={setTieNote} maxLength={280} />
            </Section>
          ) : null}
          {scored < r.applicant_count ? <Txt variant="small" color={colors.inkSoft}>{t('review.scoreAllFirst')}</Txt> : null}
          {pick.isError ? <Txt color={colors.brick}>{errorText(pick.error)}</Txt> : null}
          <Button
            label={t('review.pick')}
            busy={pick.isPending}
            disabled={scored < r.applicant_count || !r.attested_unacquainted || (isTie && (!tieChoice || !tieNote.trim()))}
            onPress={doPick}
          />
        </Panel>
      ) : (
        <Panel tone="sage">
          <Txt variant="h3">{t('review.picked', { letter: owner.data.picked_letter ?? '?' })}</Txt>
          <Button label={t('manage.title')} onPress={backToCard} />
        </Panel>
      )}
    </Screen>
  );
}
