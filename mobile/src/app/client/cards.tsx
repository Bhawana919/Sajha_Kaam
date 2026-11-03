// My cards, grouped: Draft / Open / In review / In progress / Completed.
import { router } from 'expo-router';
import { useState } from 'react';
import { View } from 'react-native';

import { useMyCards } from '@/api/hooks';
import { CardRow } from '@/components/CardRow';
import { useErrorText } from '@/components/forms';
import { Screen } from '@/components/Screen';
import { Button, Chip, StateView } from '@/components/ui';
import { useT } from '@/i18n';
import { space } from '@/theme';

const GROUPS = ['draft', 'open', 'in_review', 'in_progress', 'completed'] as const;
const GROUP_KEY = { draft: 'myCards.draft', open: 'myCards.open', in_review: 'myCards.inReview',
  in_progress: 'myCards.inProgress', completed: 'myCards.completed' } as const;

export default function MyCards() {
  const { t } = useT();
  const cards = useMyCards();
  const errorText = useErrorText();
  const items = cards.data ?? [];
  const firstNonEmpty = GROUPS.find((g) => items.some((c) => c.group === g)) ?? 'open';
  const [group, setGroup] = useState<(typeof GROUPS)[number] | null>(null);
  const active = group ?? firstNonEmpty;
  const shown = items.filter((c) => c.group === active);

  return (
    <Screen title={t('myCards.title')}>
      <View style={{ flexDirection: 'row', gap: space.sm, flexWrap: 'wrap' }} accessibilityRole="tablist">
        {GROUPS.map((g) => {
          const n = items.filter((c) => c.group === g).length;
          return <Chip key={g} label={n ? `${t(GROUP_KEY[g])} · ${n}` : t(GROUP_KEY[g])} on={active === g} onToggle={() => setGroup(g)} />;
        })}
      </View>
      {cards.isPending ? <StateView state="loading" /> : null}
      {cards.isError ? <StateView state="error" message={errorText(cards.error) ?? undefined} onRetry={() => cards.refetch()} /> : null}
      {cards.isSuccess && shown.length === 0 ? (
        <StateView state="empty" message={t('myCards.empty')}
                   action={<Button label={t('post.title')} onPress={() => router.push('/client/post')} />} />
      ) : null}
      {shown.map((c) => <CardRow key={c.id} c={c} />)}
    </Screen>
  );
}
