// Job detail: the bilingual Kaam Card a worker reads before applying.
import { router, useLocalSearchParams } from 'expo-router';
import { View } from 'react-native';

import { useCard, useMe } from '@/api/hooks';
import { KaamCardBody } from '@/components/KaamCard';
import { Screen } from '@/components/Screen';
import { Txt } from '@/components/Txt';
import { Button, Panel, StateView, Tag } from '@/components/ui';
import { useT } from '@/i18n';
import { money } from '@/lib/format';
import { colors, space } from '@/theme';

export default function CardDetailScreen() {
  const { t, country } = useT();
  const { id } = useLocalSearchParams<{ id: string }>();
  const card = useCard(id);
  const me = useMe();

  if (card.isPending) return <Screen back><StateView state="loading" /></Screen>;
  if (card.isError || !card.data) {
    return <Screen back><StateView state="error" message={t('card.notFound')} onRetry={() => card.refetch()} /></Screen>;
  }
  const c = card.data;
  return (
    <Screen back title={t('board.title')}>
      <View style={{ flexDirection: 'row', gap: space.sm, flexWrap: 'wrap' }}>
        {c.pahilo_kaam ? <Tag tone="brick" label={t('board.pahiloTag')} /> : null}
        {c.reviewed_by_sajha ? <Tag tone="sage" label={t('card.reviewed')} /> : null}
        <Tag label={t('board.clientIn', { country: country(c.client_country) })} />
      </View>
      <Panel tone="clay">
        <Txt variant="label" color={colors.sage}>{t('card.fixedPrice')}</Txt>
        <Txt variant="h1">{money(c.price.amount_minor, c.price.currency)}</Txt>
        <Txt color={colors.inkSoft}>
          {`${t('card.days', { count: c.deadline_days })} · ${t('card.revisions', { count: c.revisions_included })}`}
        </Txt>
      </Panel>
      <KaamCardBody card={c} />
      <Panel tone="sage">
        <Txt variant="h3">{t('card.workersPayNothing')}</Txt>
        <Txt>{t('card.payoutNote')}</Txt>
      </Panel>
      {me.data?.role === 'client' ? null : (
        <Button
          label={me.data ? t('card.apply') : t('auth.signIn')}
          onPress={() =>
            me.data
              ? router.push({ pathname: '/apply/[id]', params: { id: c.id } })
              : router.push({ pathname: '/sign-in', params: { role: 'worker' } })
          }
        />
      )}
    </Screen>
  );
}
