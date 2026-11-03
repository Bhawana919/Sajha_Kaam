// Labelled inputs, checkboxes, star ratings and localized error text.
import { useState } from 'react';
import { Pressable, TextInput, View, type TextInputProps } from 'react-native';

import { ApiError } from '@/api/client';
import { useT } from '@/i18n';
import { border, colors, radius, space, touchMin } from '@/theme';

import { Icon } from './Icon';
import { Txt } from './Txt';

export function Field({ label, help, error, multiline, style, ...rest }: TextInputProps & {
  label: string;
  help?: string;
  error?: string | null;
}) {
  // Focus is shown by a 2 px ink border (not colour alone, and not the brick used for errors).
  const [focused, setFocused] = useState(false);
  return (
    <View style={{ gap: space.xs }}>
      <Txt variant="label" color={colors.ink}>{label}</Txt>
      <TextInput
        accessibilityLabel={label}
        accessibilityHint={help}
        placeholderTextColor={colors.inkSoft}
        multiline={multiline}
        {...rest}
        onFocus={(e) => { setFocused(true); rest.onFocus?.(e); }}
        onBlur={(e) => { setFocused(false); rest.onBlur?.(e); }}
        style={[
          {
            minHeight: multiline ? 96 : touchMin,
            borderWidth: focused ? 2 : border,
            borderColor: error ? colors.brick : focused ? colors.ink : colors.line,
            paddingHorizontal: focused ? space.md - 1 : space.md,
            borderRadius: radius.md,
            backgroundColor: colors.white,
            paddingVertical: space.sm,
            fontSize: 16,
            color: colors.ink,
            textAlignVertical: multiline ? 'top' : 'center',
          },
          style,
        ]}
      />
      {error ? <Txt variant="small" color={colors.brick}>{error}</Txt> : null}
      {help && !error ? <Txt variant="small" color={colors.inkSoft}>{help}</Txt> : null}
    </View>
  );
}

export function Checkbox({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <Pressable
      accessibilityRole="checkbox"
      accessibilityState={{ checked }}
      accessibilityLabel={label}
      onPress={() => onChange(!checked)}
      style={{ flexDirection: 'row', gap: space.md, alignItems: 'center', minHeight: touchMin }}
    >
      <View
        style={{
          width: 26,
          height: 26,
          borderRadius: 6,
          borderWidth: 2,
          borderColor: checked ? colors.sage : colors.inkSoft,
          backgroundColor: checked ? colors.sage : colors.white,
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {checked ? <Icon name="check" size={18} color={colors.white} strokeWidth={2.6} /> : null}
      </View>
      <Txt style={{ flex: 1 }}>{label}</Txt>
    </Pressable>
  );
}

/** 1-3 stars for one checklist item. Value is spoken, not only shown by colour. */
export function Stars({ value, onChange, label }: { value: number; onChange: (v: number) => void; label: string }) {
  const { t } = useT();
  return (
    <View style={{ gap: space.xs }}>
      <Txt variant="small">{label}</Txt>
      <View accessibilityRole="radiogroup" accessibilityLabel={label} style={{ flexDirection: 'row', gap: space.sm }}>
        {[1, 2, 3].map((n) => (
          <Pressable
            key={n}
            accessibilityRole="radio"
            accessibilityState={{ checked: value === n }}
            accessibilityLabel={t('review.starsA11y', { count: n })}
            onPress={() => onChange(n)}
            style={{
              minWidth: touchMin,
              minHeight: touchMin,
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: radius.md,
              borderWidth: border,
              borderColor: value >= n ? colors.brick : colors.line,
              backgroundColor: value >= n ? colors.brickSoft : colors.white,
            }}
          >
            <Txt variant="h2" color={value >= n ? colors.brick : colors.line}>★</Txt>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

/** Turn any API error into a message in the user's language. */
export function useErrorText() {
  const { t } = useT();
  return (e: unknown, overrides: Record<string, string> = {}): string | null => {
    if (!e) return null;
    if (!(e instanceof ApiError)) return t('errors.generic');
    if (e.kind === 'mock') return t('errors.needsBackend');
    if (e.kind === 'network') return t('errors.network');
    if (e.status === 401) return overrides['401'] ?? t('errors.signInFirst');
    const code = typeof e.detail === 'string' ? e.detail : '';
    if (overrides[code]) return overrides[code];
    if (overrides[String(e.status)]) return overrides[String(e.status)];
    if (e.status === 409) return t('errors.conflict');
    return t('errors.generic');
  };
}
