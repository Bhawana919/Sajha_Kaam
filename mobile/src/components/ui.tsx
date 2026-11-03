import type { ReactNode } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, View, type ViewStyle } from 'react-native';

import { useT } from '@/i18n';
import { usePrefs } from '@/state/prefs';
import { border, colors, radius, space, touchMin } from '@/theme';

import Svg, { Path } from 'react-native-svg';

import { hexPath } from './brand/geometry';
import { Mauri, type Pose } from './brand/Mauri';
import { Icon, type IconName } from './Icon';
import { PressScale, Skeleton } from './motion';
import { Txt } from './Txt';

type ButtonProps = {
  label: string;
  onPress?: () => void;
  kind?: 'primary' | 'secondary' | 'quiet';
  icon?: IconName;
  disabled?: boolean;
  busy?: boolean;
  accessibilityHint?: string;
  style?: ViewStyle;
};

/**
 * Primary = brick, one per screen (the "next action"). Secondary = white with a line.
 * Quiet = text only. Disabled buttons keep their label readable (55 % opacity, not grey-on-grey).
 */
export function Button({ label, onPress, kind = 'primary', icon, disabled, busy, accessibilityHint, style }: ButtonProps) {
  const off = disabled || busy;
  const bg = kind === 'primary' ? colors.brick : kind === 'secondary' ? colors.white : 'transparent';
  const fg = kind === 'primary' ? colors.white : kind === 'quiet' ? colors.brick : colors.ink;
  return (
    <PressScale
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityHint={accessibilityHint}
      accessibilityState={{ disabled: !!off, busy: !!busy }}
      onPress={off ? undefined : onPress}
      disabled={!!off}
      style={[
        styles.button,
        { backgroundColor: bg, opacity: off ? 0.55 : 1 },
        kind === 'secondary' && styles.buttonOutline,
        kind === 'primary' && styles.buttonPrimary,
        style,
      ]}
    >
      {busy ? (
        <ActivityIndicator color={fg} />
      ) : (
        <View style={styles.buttonRow}>
          {icon ? <Icon name={icon} size={20} color={fg} /> : null}
          <Txt variant="h3" color={fg} center>{label}</Txt>
        </View>
      )}
    </PressScale>
  );
}

type Tone = 'white' | 'clay' | 'warn' | 'sage' | 'honey' | 'ink';
const PANEL_BG: Record<Tone, string> = {
  white: colors.white,
  clay: colors.clay,
  warn: colors.warnSoft,
  sage: colors.sageSoft,
  honey: colors.honeyWash,
  ink: colors.ink,
};

export function Panel({ children, tone = 'white', style }: { children: ReactNode; tone?: Tone; style?: ViewStyle }) {
  return (
    <View style={[styles.panel, { backgroundColor: PANEL_BG[tone] }, tone === 'ink' && { borderColor: colors.ink }, style]}>
      {children}
    </View>
  );
}

export function Tag({ label, tone = 'clay', icon }: { label: string; tone?: 'clay' | 'brick' | 'sage' | 'demo' | 'honey'; icon?: IconName }) {
  const map = {
    clay: [colors.clay, colors.ink],
    brick: [colors.brickSoft, colors.brickDeep],
    sage: [colors.sageSoft, colors.sage],
    demo: [colors.warnSoft, colors.warnInk],
    honey: [colors.honeyWash, colors.warnInk],
  } as const;
  const [bg, fg] = map[tone];
  return (
    <View style={[styles.tag, { backgroundColor: bg }]}>
      {icon ? <Icon name={icon} size={14} color={fg} strokeWidth={2} /> : null}
      <Txt variant="label" color={fg}>{label}</Txt>
    </View>
  );
}

/** A labelled on/off chip, e.g. the Pahilo Kaam filter. State is announced and shown by a check, not only colour. */
export function Chip({ label, on, onToggle }: { label: string; on: boolean; onToggle: () => void }) {
  return (
    <Pressable
      accessibilityRole="switch"
      accessibilityState={{ checked: on }}
      accessibilityLabel={label}
      onPress={onToggle}
      style={({ pressed }) => [styles.chip, on ? styles.chipOn : null, pressed ? { opacity: 0.8 } : null]}
    >
      {on ? <Icon name="check" size={16} color={colors.white} strokeWidth={2.2} /> : null}
      <Txt variant="small" color={on ? colors.white : colors.ink}>{label}</Txt>
    </Pressable>
  );
}

export function Section({ title, help, children }: { title: string; help?: string; children: ReactNode }) {
  return (
    <View style={{ gap: space.sm }}>
      <Txt variant="label" color={colors.sage} accessibilityRole="header">{title}</Txt>
      {help ? <Txt variant="small" color={colors.inkSoft}>{help}</Txt> : null}
      {children}
    </View>
  );
}

/**
 * A list line. Symbol marks are drawn as vectors (font glyphs like ☐ ✗ are missing from many
 * Android fonts and turn into boxes): '☐' = checklist cell, '✗' = missing, '✓' = met.
 */
export function Bullet({ children, mark = '•' }: { children: string; mark?: string }) {
  const icon =
    mark === '☐' ? <HexOutline /> :
    mark === '✗' ? <Icon name="close" size={16} color={colors.brick} strokeWidth={2.2} /> :
    mark === '✓' ? <Icon name="check" size={16} color={colors.sage} strokeWidth={2.4} /> : null;
  return (
    <View style={{ flexDirection: 'row', gap: space.sm, alignItems: 'flex-start' }}>
      {icon ? <View style={{ paddingTop: 3 }}>{icon}</View> : <Txt color={colors.sage}>{mark}</Txt>}
      <Txt style={{ flex: 1 }}>{children}</Txt>
    </View>
  );
}

function HexOutline() {
  return (
    <Svg width={16} height={16} viewBox="0 0 16 16">
      <Path d={hexPath(8, 8, 7)} fill="none" stroke={colors.sage} strokeWidth={1.6} strokeLinejoin="round" />
    </Svg>
  );
}

/** Mauri + one sentence + one action. Used for every empty, error and offline state. Never blames the user. */
export function EmptyState({ pose = 'peek', message, action }: { pose?: Pose; message: string; action?: ReactNode }) {
  const lite = usePrefs((s) => s.lite);
  return (
    <View style={styles.state} accessibilityLiveRegion="polite">
      <Mauri pose={pose} size={lite ? 56 : 104} motion="hover" />
      <Txt center color={colors.inkSoft} style={{ maxWidth: 320 }}>{message}</Txt>
      {action}
    </View>
  );
}

/** Loading (skeleton rows), error (Mauri confused + retry) and empty (Mauri peeking) states. */
export function StateView({ state, message, onRetry, action }: {
  state: 'loading' | 'error' | 'empty';
  message?: string;
  onRetry?: () => void;
  action?: ReactNode;
}) {
  const { t } = useT();
  if (state === 'loading') {
    return (
      <View style={{ gap: space.md }} accessibilityLabel={message ?? t('common.loading')} accessibilityLiveRegion="polite">
        {[0, 1].map((i) => (
          <View key={i} style={[styles.panel, { backgroundColor: colors.white }]}>
            <Skeleton width={96} height={14} />
            <Skeleton height={18} />
            <Skeleton width="60%" height={14} />
          </View>
        ))}
      </View>
    );
  }
  return (
    <EmptyState
      pose={state === 'error' ? 'confused' : 'peek'}
      message={message ?? (state === 'error' ? t('errors.generic') : t('mauri.empty'))}
      action={
        <>
          {state === 'error' && onRetry ? <Button kind="secondary" label={t('common.retry')} onPress={onRetry} /> : null}
          {action}
        </>
      }
    />
  );
}

/** The one highlighted "do this next" card: ink ticket with honey text, so it never competes with brick buttons. */
export function NextAction({ title, body, cta, onPress }: { title: string; body?: string; cta: string; onPress: () => void }) {
  return (
    <PressScale accessibilityRole="button" accessibilityLabel={`${title}. ${cta}`} onPress={onPress}
                style={[styles.panel, { backgroundColor: colors.ink, borderColor: colors.ink }]}>
      <Txt variant="label" color={colors.honeyLight}>{title}</Txt>
      {body ? <Txt variant="h3" color={colors.paper}>{body}</Txt> : null}
      <View style={styles.buttonRow}>
        <Txt variant="h3" color={colors.honeyLight}>{cta}</Txt>
        <Icon name="chevronRight" size={18} color={colors.honeyLight} strokeWidth={2.2} />
      </View>
    </PressScale>
  );
}

export function DemoBanner() {
  const { t } = useT();
  return (
    <View style={styles.demo} accessibilityRole="text">
      <Tag tone="demo" label={t('common.demoSimulated')} />
      <Txt variant="small" color={colors.warnInk} style={{ flex: 1 }}>{t('common.sampleData')}</Txt>
    </View>
  );
}

const styles = StyleSheet.create({
  button: {
    minHeight: touchMin + 4,
    paddingHorizontal: space.lg,
    paddingVertical: space.sm,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  // A 2 px darker brick "lip" under the primary button: reads as pressable without a shadow.
  buttonPrimary: { borderBottomWidth: 2, borderBottomColor: colors.brickDeep },
  buttonOutline: { borderWidth: border, borderColor: colors.line },
  buttonRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: space.sm },
  panel: { borderWidth: border, borderColor: colors.line, borderRadius: radius.lg, padding: space.lg, gap: space.md },
  tag: {
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: space.sm,
    paddingVertical: 3,
    borderRadius: radius.sm,
  },
  chip: {
    minHeight: touchMin,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: space.md,
    borderRadius: radius.pill,
    borderWidth: border,
    borderColor: colors.line,
    backgroundColor: colors.white,
  },
  chipOn: { backgroundColor: colors.ink, borderColor: colors.ink },
  state: { paddingVertical: space.xl, paddingHorizontal: space.lg, gap: space.md, alignItems: 'center' },
  demo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.sm,
    padding: space.md,
    borderRadius: radius.md,
    backgroundColor: colors.warnSoft,
  },
});
