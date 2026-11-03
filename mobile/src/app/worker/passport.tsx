// Work Passport: Kaam Path (private), records private by default, QR to the public page,
// expiring share links, "Use anywhere" lines, export and delete. Signed records + Verify come in P1.
import { router } from 'expo-router';
import { useState } from 'react';
import { Linking, Share, StyleSheet, View } from 'react-native';
import QRCode from 'react-native-qrcode-svg';

import {
  useCreateShare,
  useDeleteMyData,
  useExportPassport,
  usePassport,
  useRevokeShare,
  useSetVisibility,
  useShares,
  useSigningKeys,
} from '@/api/hooks';
import type { ClaimOut } from '@/api/types';
import { HoneycombCell } from '@/components/brand/Honeycomb';
import { Mauri } from '@/components/brand/Mauri';
import { Checkbox, useErrorText } from '@/components/forms';
import { Screen } from '@/components/Screen';
import { Txt } from '@/components/Txt';
import { Button, DemoBanner, Panel, Section, StateView, Tag } from '@/components/ui';
import { useT } from '@/i18n';
import { type PublicKey, verifyCredential } from '@/lib/proof';
import { colors, radius, space } from '@/theme';

/** Open the phone's share sheet. Where there is none (some browsers), the text is already on screen to copy. */
function shareText(content: { message: string }) {
  Share.share(content).catch(() => undefined);
}

function ClaimCard({ c, selected, onSelect, keys, base }: {
  c: ClaimOut;
  selected: boolean;
  onSelect: (v: boolean) => void;
  keys: PublicKey[] | undefined;
  base: string;
}) {
  const { t, pick, digits } = useT();
  const visibility = useSetVisibility();
  const isPublic = c.visibility === 'public';
  // Checked here, with the public key, not taken on trust from the server's "signed" flag.
  const valid = keys && c.credential && c.signature_b64 && c.key_id
    ? verifyCredential(c.credential, c.signature_b64, c.key_id, keys)
    : null;
  return (
    <Panel>
      <View style={{ flexDirection: 'row', gap: space.sm, flexWrap: 'wrap' }}>
        <Tag tone="sage" icon="stamp" label={t(`passport.claim_${c.type}`)} />
        <Tag label={c.on_time ? t('passport.onTime') : t('passport.late')} />
        <Tag tone={isPublic ? 'brick' : 'clay'} label={isPublic ? t('passport.public') : t('passport.private')} />
      </View>
      <Txt variant="h3">{pick(c.summary_ne, c.summary_en)}</Txt>
      <Txt variant="small" color={colors.inkSoft}>{digits(c.issued_at.slice(0, 10))}</Txt>
      {valid !== null ? (
        <Txt variant="small" color={valid ? colors.sage : colors.brick}>{valid ? t('passport.signedOk') : t('passport.signedBad')}</Txt>
      ) : null}
      {isPublic ? (
        <Button kind="quiet" label={t('passport.openVerify')} onPress={() => void Linking.openURL(`${base}/verify/${c.id}`)} />
      ) : null}
      <Button kind="secondary" busy={visibility.isPending}
              label={isPublic ? t('passport.makePrivate') : t('passport.makePublic')}
              onPress={() => visibility.mutate({ id: c.id, visibility: isPublic ? 'private' : 'public' })} />
      <Checkbox label={t('passport.includeInShare')} checked={selected} onChange={onSelect} />
    </Panel>
  );
}

export default function Passport() {
  const { t, pick, digits } = useT();
  const passport = usePassport();
  const keys = useSigningKeys();
  const shares = useShares();
  const createShare = useCreateShare();
  const revoke = useRevokeShare();
  const exporter = useExportPassport();
  const del = useDeleteMyData();
  const errorText = useErrorText();
  const [picked, setPicked] = useState<string[]>([]);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const p = passport.data;

  const summary = p
    ? [
        t('passport.summaryLine1', { level: pick(p.level.ne, p.level.en), count: p.confirmed_jobs }),
        t('passport.summaryLine2'),
        `${t('passport.summaryLine3')} ${p.public_url}`, // URL outside t(): its digits must stay Latin
      ].join('\n')
    : '';

  return (
    <Screen title={t('passport.title')}>
      {passport.isPending ? <StateView state="loading" /> : null}
      {passport.isError ? <StateView state="error" message={errorText(passport.error) ?? undefined} onRetry={() => passport.refetch()} /> : null}
      {p ? (
        <>
          {/* The cover: a passport booklet in brick, Mauri carrying hers. Stamps are a record, not a reward. */}
          <View style={styles.cover}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.md }}>
              <View style={{ flex: 1, gap: space.xs }}>
                <Txt variant="label" color={colors.honeyLight}>{t('passport.coverKicker')}</Txt>
                <Txt variant="h1" color={colors.paper}>{t('passport.slogan')}</Txt>
              </View>
              <Mauri pose="passport" size={88} motion="burst" />
            </View>
            <View style={styles.coverRule} />
            <Txt variant="label" color={colors.brickSoft}>{t('level.pathTitle')}</Txt>
            <Txt variant="h2" color={colors.paper}>{pick(p.level.ne, p.level.en)}</Txt>
            <View accessible accessibilityRole="image" accessibilityLabel={t('passport.stampsA11y', { count: p.confirmed_jobs })}
                  style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
              {Array.from({ length: Math.min(10, Math.max(5, p.confirmed_jobs + 1)) }, (_, i) => (
                <HoneycombCell key={i} size={28} state={i < p.confirmed_jobs ? 'filled' : i === p.confirmed_jobs ? 'next' : 'empty'} />
              ))}
            </View>
            <Txt color={colors.paper}>{t('passport.confirmedJobs', { count: p.confirmed_jobs })}</Txt>
            {p.next_level && p.jobs_to_next !== null && p.jobs_to_next !== undefined ? (
              <Txt color={colors.brickSoft}>{t('passport.nextLevel', { count: p.jobs_to_next, level: pick(p.next_level.ne, p.next_level.en) })}</Txt>
            ) : null}
            <Txt variant="small" color={colors.brickSoft}>{t('level.private')}</Txt>
          </View>

          <Panel>
            <Txt variant="h3">{t('passport.qrTitle')}</Txt>
            <View style={{ alignItems: 'center', padding: space.md, backgroundColor: colors.white }}
                  accessible accessibilityRole="image" accessibilityLabel={t('passport.qrA11y')}>
              <QRCode value={p.public_url} size={200} color={colors.ink} backgroundColor={colors.white} />
            </View>
            <Txt variant="small" color={colors.inkSoft}>{t('passport.qrHelp')}</Txt>
            <Txt variant="small" selectable>{p.public_url}</Txt>
            <DemoBanner />
          </Panel>

          <Section title={t('passport.records')}>
            {p.claims.length === 0 ? (
              <StateView state="empty" message={t('passport.empty')}
                         action={<Button label={t('board.title')} onPress={() => router.push('/worker/board')} />} />
            ) : null}
            {p.claims.map((c) => (
              <ClaimCard key={c.id} c={c} keys={keys.data?.keys} base={p.public_url.replace(/\/p\/[^/]+$/, '')}
                         selected={picked.includes(c.id)}
                         onSelect={(v) => setPicked((cur) => (v ? [...cur, c.id] : cur.filter((x) => x !== c.id)))} />
            ))}
          </Section>

          {p.claims.length ? (
            <Panel tone="clay">
              <Section title={t('passport.shareTitle')} help={t('passport.shareHelp')}>
                <Button label={t('passport.createShare')} disabled={!picked.length} busy={createShare.isPending}
                        onPress={() => createShare.mutate(picked, {
                          onSuccess: (s) => { setPicked([]); if (s.url) shareText({ message: s.url }); },
                        })} />
                {!picked.length ? <Txt variant="small" color={colors.inkSoft}>{t('passport.pickRecords')}</Txt> : null}
                {createShare.data?.url ? <Txt variant="small" selectable>{createShare.data.url}</Txt> : null}
              </Section>
              {(shares.data ?? []).length ? (
                <Section title={t('passport.shareLinks')}>
                  {(shares.data ?? []).map((s) => (
                    <View key={s.id} style={{ flexDirection: 'row', alignItems: 'center', gap: space.sm, flexWrap: 'wrap' }}>
                      <Txt style={{ flex: 1, minWidth: 160 }}>
                        {s.revoked ? t('passport.shareRevoked') : t('passport.shareActive', { date: digits(s.expires_at.slice(0, 10)) })}
                      </Txt>
                      {!s.revoked ? <Button kind="quiet" label={t('passport.revoke')} onPress={() => revoke.mutate(s.id, { onSuccess: () => createShare.reset() })} /> : null}
                    </View>
                  ))}
                </Section>
              ) : null}
            </Panel>
          ) : null}

          <Panel>
            <Section title={t('passport.useAnywhere')} help={t('passport.useAnywhereHelp')}>
              <Txt selectable>{summary}</Txt>
              <Button kind="secondary" label={t('common.share')} onPress={() => shareText({ message: summary })} />
            </Section>
          </Panel>

          <Button kind="secondary" label={t('passport.export')} busy={exporter.isPending}
                  onPress={() => exporter.mutate(undefined, {
                    onSuccess: (data) => shareText({ message: JSON.stringify(data, null, 2) }),
                  })} />
          {confirmDelete ? (
            <Panel tone="warn">
              <Txt>{t('passport.deleteConfirm')}</Txt>
              <Button label={t('passport.deleteYes')} busy={del.isPending}
                      onPress={() => del.mutate(undefined, { onSuccess: () => router.replace('/') })} />
              <Button kind="quiet" label={t('common.cancel')} onPress={() => setConfirmDelete(false)} />
            </Panel>
          ) : (
            <Button kind="quiet" label={t('passport.deleteAll')} onPress={() => setConfirmDelete(true)} />
          )}
          {[createShare.error, revoke.error, exporter.error, del.error].some(Boolean) ? (
            <Txt color={colors.brick}>{errorText(createShare.error ?? revoke.error ?? exporter.error ?? del.error)}</Txt>
          ) : null}
        </>
      ) : null}
      <Txt variant="small" color={colors.inkSoft}>{t('passport.disclaimer')}</Txt>
    </Screen>
  );
}

const styles = StyleSheet.create({
  cover: {
    backgroundColor: colors.brick,
    borderRadius: radius.lg,
    padding: space.lg,
    gap: space.sm,
    // the booklet spine: a darker brick edge on the left
    borderLeftWidth: 6,
    borderLeftColor: colors.brickDeep,
  },
  coverRule: { height: 1, backgroundColor: colors.brickDeep, marginVertical: space.xs },
});
