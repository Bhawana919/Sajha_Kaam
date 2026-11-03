// Admin review queue (first cards and flagged cards). Web is fine for this screen.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { api } from '@/api/client';
import type { RuleIssue } from '@/api/types';
import { Field, useErrorText } from '@/components/forms';
import { Screen } from '@/components/Screen';
import { Txt } from '@/components/Txt';
import { Bullet, Button, Panel, StateView, Tag } from '@/components/ui';
import { useT } from '@/i18n';
import { HelpScreen } from '@/screens/Shells';
import { colors } from '@/theme';

type QueueItem = { card_id: string; title_en: string; title_ne: string; flagged: boolean; rules: RuleIssue[] };

function QueueCard({ item }: { item: QueueItem }) {
  const { t, pick } = useT();
  const qc = useQueryClient();
  const [reason, setReason] = useState('');
  const decide = useMutation({
    mutationFn: (decision: 'approve' | 'request_change') =>
      api(`/v1/admin/cards/${item.card_id}/decision`, { method: 'POST', body: { decision, reason } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['adminQueue'] }),
  });
  const errorText = useErrorText();
  return (
    <Panel>
      {item.flagged ? <Tag tone="brick" label={t('admin.flagged')} /> : null}
      <Txt variant="h3">{pick(item.title_ne, item.title_en)}</Txt>
      {item.rules.map((r, i) => <Bullet key={i} mark={r.severity === 'error' ? '✗' : '!'}>{pick(r.message_ne, r.message_en)}</Bullet>)}
      <Field label={t('admin.reason')} value={reason} onChangeText={setReason} />
      {decide.isError ? <Txt color={colors.brick}>{errorText(decide.error)}</Txt> : null}
      <Button label={t('admin.approve')} disabled={reason.trim().length < 3} busy={decide.isPending} onPress={() => decide.mutate('approve')} />
      <Button kind="secondary" label={t('admin.requestChange')} disabled={reason.trim().length < 3 || decide.isPending}
              onPress={() => decide.mutate('request_change')} />
    </Panel>
  );
}

export default function Admin() {
  const { t } = useT();
  const queue = useQuery({ queryKey: ['adminQueue'], queryFn: () => api<QueueItem[]>('/v1/admin/queue') });
  const errorText = useErrorText();
  return (
    <>
      <Screen title={t('admin.title')}>
        {queue.isPending ? <StateView state="loading" /> : null}
        {queue.isError ? <StateView state="error" message={errorText(queue.error) ?? undefined} onRetry={() => queue.refetch()} /> : null}
        {queue.isSuccess && queue.data.length === 0 ? <StateView state="empty" message={t('admin.empty')} /> : null}
        {(queue.data ?? []).map((item) => <QueueCard key={item.card_id} item={item} />)}
      </Screen>
      <HelpScreen />
    </>
  );
}
