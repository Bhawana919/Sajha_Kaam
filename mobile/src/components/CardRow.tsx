// One of the client's cards in a list, with its state and time left.
import { router } from 'expo-router';
import { View } from 'react-native';

import type { MyCardItem } from '@/api/types';
import { useT } from '@/i18n';
import { hoursUntil } from '@/lib/format';
import { colors, space } from '@/theme';

import { Icon } from './Icon';
import { PressScale } from './motion';
import { Txt } from './Txt';
import { Panel, Tag } from './ui';

export function CardRow({ c }: { c: MyCardItem }) {
  const { t, pick } = useT();
  const hours = c.state === 'open' ? hoursUntil(c.window_closes_at) : null;
  return (
    <PressScale accessibilityRole="button" onPress={() => router.push({ pathname: '/manage/[id]', params: { id: c.id } })}>
      <Panel>
        <Tag tone={c.group === 'completed' ? 'sage' : c.group === 'in_review' ? 'brick' : 'clay'} label={t(`cardState.${c.state}`)} />
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.sm }}>
          <Txt variant="h3" style={{ flex: 1 }}>{pick(c.title_ne, c.title_en)}</Txt>
          <Icon name="chevronRight" size={20} color={colors.inkSoft} />
        </View>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', flexWrap: 'wrap', gap: space.sm }}>
          <Txt variant="small" color={colors.inkSoft}>{t('board.applicants', { count: c.applicant_count, max: 15 })}</Txt>
          {hours !== null ? (
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
              <Icon name="clock" size={14} color={colors.inkSoft} />
              <Txt variant="small" color={colors.inkSoft}>{t('board.closesInHours', { count: hours })}</Txt>
            </View>
          ) : null}
        </View>
      </Panel>
    </PressScale>
  );
}

