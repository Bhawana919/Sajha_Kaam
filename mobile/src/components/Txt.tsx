// Text that picks Noto Sans Devanagari whenever the content has Devanagari, Inter otherwise.
// Line height is always 1.5x or more; no fixed heights, so 200% font scale never clips.
import { Children, type ReactNode } from 'react';
import { Text, type TextProps, type TextStyle } from 'react-native';

import { colors, fonts, typeScale, type TypeVariant } from '@/theme';

const DEVANAGARI = /[ऀ-ॿ]/;

function plainText(children: ReactNode): string {
  return Children.toArray(children)
    .map((c) => (typeof c === 'string' || typeof c === 'number' ? String(c) : ''))
    .join('');
}

type Props = TextProps & { variant?: TypeVariant; color?: string; center?: boolean };

export function Txt({ variant = 'body', color = colors.ink, center, style, children, ...rest }: Props) {
  const spec = typeScale[variant];
  const isNe = DEVANAGARI.test(plainText(children));
  const family = isNe ? fonts.devanagari : fonts.latin;
  // Devanagari gets +1 px optical size: the headline (shirorekha) makes it look smaller at equal size.
  const size = spec.fontSize + (isNe ? 1 : 0);
  const tight = variant === 'display' || variant === 'h1' || variant === 'h2';
  const base: TextStyle = {
    fontFamily: family[spec.weight],
    fontSize: size,
    lineHeight: Math.round(size * (tight ? (isNe ? 1.5 : 1.3) : 1.55)),
    color,
    textAlign: center ? 'center' : undefined,
    ...(variant === 'label' && !isNe ? { letterSpacing: 0.4 } : null),
    ...(tight && !isNe ? { letterSpacing: -0.3 } : null),
  };
  return (
    <Text {...rest} style={[base, style]}>
      {children}
    </Text>
  );
}
