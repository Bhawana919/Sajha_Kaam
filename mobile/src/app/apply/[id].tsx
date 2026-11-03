// Apply: one work sample + two short answers. Leak Guard scans as you type; nothing identifying is sent.
import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { View } from 'react-native';

import { ApiError } from '@/api/client';
import { useApply, useCard, useLeakScan } from '@/api/hooks';
import { ApplicationCard } from '@/components/ApplicationCard';
import { Checkbox, Field, useErrorText } from '@/components/forms';
import { Mauri } from '@/components/brand/Mauri';
import { SuccessMark } from '@/components/motion';
import { Screen } from '@/components/Screen';
import { Txt } from '@/components/Txt';
import { Bullet, Button, Chip, Panel, Section, StateView } from '@/components/ui';
import { useT } from '@/i18n';
import { useDraft } from '@/lib/offline';
import { colors, space } from '@/theme';

type Finding = { kind: string; start: number; end: number; text: string };
const MAX_ANSWER = 280;

function redact(text: string, findings: Finding[]): string {
  let out = text;
  for (const f of [...findings].sort((a, b) => b.start - a.start)) out = out.slice(0, f.start) + out.slice(f.end);
  return out.replace(/\s{2,}/g, ' ').trim();
}

/** Debounced Leak Guard scan of one text box. */
function useLeaks(text: string): Finding[] {
  const scan = useLeakScan();
  const [findings, setFindings] = useState<Finding[]>([]);
  const { mutate } = scan;
  useEffect(() => {
    if (!text.trim()) return;
    const timer = setTimeout(() => mutate(text, { onSuccess: (r) => setFindings(r.findings), onError: () => setFindings([]) }), 400);
    return () => clearTimeout(timer);
  }, [text, mutate]);
  // Findings refer to positions in the text they were scanned from: drop them once that text is gone.
  return text.trim() ? findings.filter((f) => text.slice(f.start, f.end) === f.text) : [];
}

export default function Apply() {
  const { t, pick, locale, digits } = useT();
  const { id } = useLocalSearchParams<{ id: string }>();
  const card = useCard(id);
  const apply = useApply(id);
  const errorText = useErrorText();
  // The sample and answers survive an app restart (per job) until the application is sent.
  const form = useDraft<{ sample: string; lang: 'ne' | 'en'; answers: string[] }>(`apply:${id}`,
    { sample: '', lang: locale, answers: ['', ''] });
  const { sample, lang, answers } = form.value;
  const setSample = (v: string) => form.set((f) => ({ ...f, sample: v }));
  const setLang = (v: 'ne' | 'en') => form.set((f) => ({ ...f, lang: v }));
  const setAnswers = (v: string[]) => form.set((f) => ({ ...f, answers: v }));
  const [consent, setConsent] = useState(false);
  const [clean, setClean] = useState(false);
  const leaks = [useLeaks(sample), useLeaks(answers[0]), useLeaks(answers[1])];
  const totalLeaks = leaks.reduce((n, l) => n + l.length, 0);

  if (card.isPending) return <Screen back title={t('apply.title')}><StateView state="loading" /></Screen>;
  if (card.isError || !card.data) return <Screen back title={t('apply.title')}><StateView state="error" message={t('card.notFound')} /></Screen>;

  if (apply.isSuccess) {
    return (
      <Screen back title={t('apply.title')}>
        <Panel tone="sage" style={{ alignItems: 'center' }}>
          <View style={{ width: 112, height: 104 }}>
            <Mauri pose="tag" size={104} motion="burst" />
            <View style={{ position: 'absolute', right: 0, bottom: 0 }}><SuccessMark size={36} label={t('apply.sent')} /></View>
          </View>
          <Txt variant="h2" center>{t('apply.sent')}</Txt>
        </Panel>
        <ApplicationCard a={apply.data} />
        <Button label={t('tabs.myWork')} onPress={() => router.replace('/worker/work')} />
      </Screen>
    );
  }

  const c = card.data;
  const ready = sample.trim().length >= 10 && answers.every((a) => a.trim()) && consent && clean && totalLeaks === 0;
  const err = apply.error instanceof ApiError ? apply.error : null;
  const applyError = err
    ? errorText(err, {
        pahilo_kaam_only_beginners: t('apply.reason_pahilo_kaam_only_beginners'),
        above_level_cap: t('apply.reason_above_level_cap'),
        too_many_active_applications: t('apply.reason_too_many_active_applications'),
        'you already applied': t('apply.already'),
        'applications are closed': t('apply.closed'),
        '422': t('apply.leakFound', { count: 1 }),
      })
    : null;

  return (
    <Screen back title={t('apply.title')}>
      <Txt variant="h2">{pick(c.title_ne, c.title_en)}</Txt>
      {form.restored ? <Panel tone="sage"><Txt>{t('common.draftRestored')}</Txt></Panel> : null}
      <Panel tone="clay">
        <Section title={t('card.sampleBrief')}>
          <Txt>{pick(c.sample_brief_ne, c.sample_brief_en)}</Txt>
        </Section>
      </Panel>

      <Field label={t('apply.sampleLabel')} help={t('apply.sampleHelp')} value={sample} onChangeText={setSample}
             multiline maxLength={2000} />
      <View style={{ flexDirection: 'row', gap: space.sm, alignItems: 'center', flexWrap: 'wrap' }}>
        <Txt variant="small">{t('apply.sampleLang')}</Txt>
        <Chip label={t('lang.ne')} on={lang === 'ne'} onToggle={() => setLang('ne')} />
        <Chip label={t('lang.en')} on={lang === 'en'} onToggle={() => setLang('en')} />
      </View>

      {c.questions.map((q, i) => (
        <Field key={i} label={`${t('apply.answerLabel', { n: i + 1 })}: ${pick(q.ne, q.en)}`}
               value={answers[i]} maxLength={MAX_ANSWER}
               help={t('apply.charsLeft', { count: MAX_ANSWER - answers[i].length })}
               onChangeText={(v) => setAnswers(answers.map((a, j) => (j === i ? v : a)))} />
      ))}

      {totalLeaks ? (
        <Panel tone="warn">
          <Txt variant="h3">{t('apply.leakFound', { count: totalLeaks })}</Txt>
          {leaks.flat().map((f, i) => (
            <Bullet key={i} mark="!">{`${t(`apply.leakKind_${f.kind}`)}: “${f.text}”`}</Bullet>
          ))}
          <Button kind="secondary" label={t('apply.removeAll')} onPress={() => {
            setSample(redact(sample, leaks[0]));
            setAnswers([redact(answers[0], leaks[1]), redact(answers[1], leaks[2])]);
          }} />
        </Panel>
      ) : null}
      <Txt variant="small" color={colors.inkSoft}>{t('apply.imageNote')}</Txt>

      <Panel>
        <Checkbox label={t('apply.consent')} checked={consent} onChange={setConsent} />
        <Checkbox label={t('apply.noIdentifying')} checked={clean} onChange={setClean} />
      </Panel>
      {applyError ? <Txt color={colors.brick}>{applyError}</Txt> : null}
      <Button
        label={t('apply.submit')}
        busy={apply.isPending}
        disabled={!ready}
        accessibilityHint={digits(`${sample.length}/2000`)}
        onPress={() => apply.mutate({ sample_text: sample.trim(), sample_lang: lang, answers: answers.map((a) => a.trim()),
                                      consent, no_identifying_details: clean }, { onSuccess: form.clear })}
      />
    </Screen>
  );
}
