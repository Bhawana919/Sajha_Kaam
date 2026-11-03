// Board list item and the full bilingual Kaam Card body (used by job detail and draft preview).
import { StyleSheet, View } from 'react-native';

import type { BoardCard, KaamCardDraft } from '@/api/types';
import { useT } from '@/i18n';
import { hoursUntil, money } from '@/lib/format';
import { border, colors, radius, space } from '@/theme';

import { Icon } from './Icon';
import { PressScale } from './motion';
import { Txt } from './Txt';
import { Bullet, Section, Tag } from './ui';

/**
 * A Kaam Card on the board, drawn as a ticket: the job on top, a perforation, and a honey "stub"
 * with what the worker actually weighs: the fixed price, the days, the revisions. A ticket is a
 * promise you can hold; that is what a Kaam Card is. Time left is calm text, never a countdown.
 */
export function BoardItem({ card, onPress }: { card: BoardCard; onPress: () => void }) {
  const { t, pick, country } = useT();
  const hours = hoursUntil(card.window_closes_at);
  const title = pick(card.title_ne, card.title_en);
  const price = money(card.price.amount_minor, card.price.currency);
  return (
    <PressScale accessibilityRole="button" accessibilityLabel={`${title}, ${price}`} onPress={onPress}>
      <View style={ticket.root}>
        <View style={ticket.top}>
          <View style={{ flexDirection: 'row', gap: space.sm, flexWrap: 'wrap' }}>
            {card.pahilo_kaam ? <Tag tone="honey" icon="stamp" label={t('board.pahiloTag')} /> : null}
            <Tag icon="globe" label={t('board.clientIn', { country: country(card.client_country) })} />
          </View>
          <Txt variant="h3">{title}</Txt>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', flexWrap: 'wrap', gap: space.sm }}>
            <Txt variant="small" color={colors.inkSoft}>
              {t('board.applicants', { count: card.applicant_count, max: card.max_applicants })}
            </Txt>
            {hours !== null ? (
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                <Icon name="clock" size={14} color={colors.inkSoft} />
                <Txt variant="small" color={colors.inkSoft}>{t('board.closesInHours', { count: hours })}</Txt>
              </View>
            ) : null}
          </View>
        </View>
        <View style={ticket.perfRow}>
          <View style={[ticket.notch, { left: -9 }]} />
          <View style={ticket.perf} />
          <View style={[ticket.notch, { right: -9 }]} />
        </View>
        <View style={ticket.stub}>
          <Txt variant="h1">{price}</Txt>
          <View style={{ flexDirection: 'row', gap: space.md, flexWrap: 'wrap' }}>
            <Txt variant="small" color={colors.warnInk}>{t('card.days', { count: card.deadline_days })}</Txt>
            <Txt variant="small" color={colors.warnInk}>{t('card.revisions', { count: card.revisions_included })}</Txt>
          </View>
        </View>
      </View>
    </PressScale>
  );
}

const ticket = StyleSheet.create({
  root: { borderWidth: border, borderColor: colors.line, borderRadius: radius.lg, backgroundColor: colors.white, overflow: 'hidden' },
  top: { padding: space.lg, gap: space.sm },
  perfRow: { height: 18, justifyContent: 'center', backgroundColor: colors.white },
  perf: { marginHorizontal: space.md, borderTopWidth: 1.5, borderColor: colors.line, borderStyle: 'dashed' },
  notch: {
    position: 'absolute',
    top: 0,
    width: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: colors.paper,
    borderWidth: border,
    borderColor: colors.line,
  },
  stub: {
    backgroundColor: colors.honeyWash,
    paddingHorizontal: space.lg,
    paddingVertical: space.md,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: space.sm,
  },
});

type CardBody = Pick<
  KaamCardDraft,
  | 'title_ne' | 'title_en' | 'summary_ne' | 'summary_en' | 'deliverables' | 'checklist'
  | 'sample_brief_ne' | 'sample_brief_en' | 'questions' | 'reference_language'
>;

/** The card in the reader's language, with the reference-version tag. */
export function KaamCardBody({ card }: { card: CardBody }) {
  const { t, pick, digits } = useT();
  const refLang = card.reference_language === 'ne' ? t('lang.ne') : t('lang.en');
  return (
    <View style={{ gap: space.lg }}>
      <View style={{ gap: space.sm }}>
        <Txt variant="h1">{pick(card.title_ne, card.title_en)}</Txt>
        <Txt color={colors.inkSoft}>{pick(card.summary_ne, card.summary_en)}</Txt>
        <Tag label={t('card.reference', { lang: refLang })} />
      </View>
      <Section title={t('card.deliverables')}>
        {card.deliverables.map((d) => (
          <Bullet key={d.id}>{pick(d.text_ne, d.text_en)}</Bullet>
        ))}
      </Section>
      <Section title={t('card.doneWhen')} help={t('card.doneWhenHelp')}>
        {card.checklist.map((c) => (
          <Bullet key={c.id} mark="☐">{pick(c.text_ne, c.text_en)}</Bullet>
        ))}
      </Section>
      <Section title={t('card.sampleBrief')}>
        <Txt>{pick(card.sample_brief_ne, card.sample_brief_en)}</Txt>
      </Section>
      <Section title={t('card.questions')}>
        {card.questions.map((q, i) => (
          <Bullet key={i} mark={`${digits(i + 1)}.`}>{pick(q.ne, q.en)}</Bullet>
        ))}
      </Section>
    </View>
  );
}
