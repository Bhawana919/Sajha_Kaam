// Review tab: cards whose application window has closed, ready for Fair Pick.
import { router } from 'expo-router';

import { useMyCards } from '@/api/hooks';
import { CardRow } from '@/components/CardRow';
import { useErrorText } from '@/components/forms';
import { Screen } from '@/components/Screen';
import { Txt } from '@/components/Txt';
import { Button, Panel, StateView } from '@/components/ui';
import { useT } from '@/i18n';
import { colors } from '@/theme';

export default function ReviewTab() {
  const { t } = useT();
  const cards = useMyCards();
  const errorText = useErrorText();
  const ready = (cards.data ?? []).filter((c) => c.group === 'in_review');
  const open = (cards.data ?? []).filter((c) => c.state === 'open');
  return (
    <Screen title={t('review.title')}>
      <Txt color={colors.inkSoft}>{t('review.intro')}</Txt>
      {cards.isPending ? <StateView state="loading" /> : null}
      {cards.isError ? <StateView state="error" message={errorText(cards.error) ?? undefined} onRetry={() => cards.refetch()} /> : null}
      {cards.isSuccess && ready.length === 0 ? <StateView state="empty" message={t('review.noCards')} /> : null}
      {ready.map((c) => <CardRow key={c.id} c={c} />)}
      {ready.length === 0 && open.length ? (
        <Panel tone="clay">
          <Txt>{t('manage.openWaiting')}</Txt>
          {open.map((c) => (
            <Button key={c.id} kind="secondary" label={t('manage.title')}
                    onPress={() => router.push({ pathname: '/manage/[id]', params: { id: c.id } })} />
          ))}
        </Panel>
      ) : null}
    </Screen>
  );
}
