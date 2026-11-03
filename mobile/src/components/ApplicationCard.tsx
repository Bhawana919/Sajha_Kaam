// The worker's own application, as a small card: which Kaam Card, application ID, name, role, status.
// Only the worker sees their name here; clients see applicants by letter until they pick.
import type { ReactNode } from 'react';
import { View } from 'react-native';

import type { MyApplication } from '@/api/types';
import { useT } from '@/i18n';
import { colors, space } from '@/theme';

import { Txt } from './Txt';
import { Panel, Tag } from './ui';

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={{ flexDirection: 'row', gap: space.md, flexWrap: 'wrap' }}>
      <Txt variant="small" color={colors.inkSoft} style={{ minWidth: 120 }}>{label}</Txt>
      <Txt variant="small" style={{ flex: 1, minWidth: 140 }} selectable>{value}</Txt>
    </View>
  );
}

export function ApplicationCard({ a, tone = 'white', children }: { a: MyApplication; tone?: 'white' | 'clay' | 'sage'; children?: ReactNode }) {
  const { t, pick, digits } = useT();
  return (
    <Panel tone={tone}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: space.sm, flexWrap: 'wrap' }}>
        <Txt variant="label" color={colors.sage}>{t('appCard.title')}</Txt>
        <Tag tone={a.state === 'picked' ? 'brick' : 'clay'} label={t(`work.appState_${a.state}`)} />
      </View>
      <Txt variant="h3">{pick(a.title_ne, a.title_en)}</Txt>
      <View style={{ gap: space.xs }}>
        <Row label={t('appCard.id')} value={a.application_ref} />
        <Row label={t('appCard.applicant')} value={a.applicant_name} />
        <Row label={t('appCard.role')} value={a.role === 'worker' ? t('auth.asWorker') : a.role} />
        <Row label={t('appCard.status')} value={t(`work.appState_${a.state}`)} />
        <Row label={t('appCard.sentOn')} value={digits(a.created_at.slice(0, 10))} />
      </View>
      {children}
    </Panel>
  );
}
