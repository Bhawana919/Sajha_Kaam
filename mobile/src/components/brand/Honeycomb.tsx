// Honeycomb design language: one confirmed job = one filled cell. A record, not a streak:
// cells never empty again, there is no timer, and nobody else's comb is shown.
import { View } from 'react-native';
import Svg, { Path } from 'react-native-svg';

import { colors, space } from '@/theme';

import { FadeIn } from '../motion';
import { Txt } from '../Txt';
import { hexPath } from './geometry';
import { Mauri } from './Mauri';

export function HoneycombCell({ size = 32, state = 'filled' }: { size?: number; state?: 'filled' | 'next' | 'empty' }) {
  const fill = state === 'filled' ? colors.honey : state === 'next' ? colors.honeyWash : colors.paper;
  const stroke = state === 'empty' ? colors.line : colors.ink;
  return (
    <Svg width={size} height={size} viewBox="0 0 32 32">
      <Path d={hexPath(16, 16, 14.5)} fill={fill} stroke={stroke} strokeWidth={1.6} strokeDasharray={state === 'empty' ? '3 3' : undefined} strokeLinejoin="round" />
      {state === 'filled' ? (
        <Path d="M10.6 16.4l3.6 3.6 7.2-7.6" fill="none" stroke={colors.ink} strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" />
      ) : null}
    </Svg>
  );
}

/**
 * The Kaam Path: a honeycomb row, one cell per confirmed job, with the next cell outlined.
 * Mauri flies beside the newest cell. Private to the worker.
 */
export function KaamPath({ filled, toNext, label }: { filled: number; toNext?: number | null; label: string }) {
  const total = Math.min(10, Math.max(5, filled + Math.max(1, toNext ?? 1)));
  const cell = 34;
  const step = cell * 0.88; // pointy-top hexes nest when offset by ~sqrt(3)/2 of their height
  return (
    <View accessible accessibilityRole="image" accessibilityLabel={label} style={{ gap: space.sm }}>
      <View style={{ flexDirection: 'row', alignItems: 'flex-end', height: cell * 1.5 + 8 }}>
        {Array.from({ length: total }, (_, i) => {
          const state = i < filled ? 'filled' : i === filled ? 'next' : 'empty';
          return (
            <FadeIn key={i} delay={i * 40} style={{ width: step, marginBottom: i % 2 ? cell * 0.5 : 0 }}>
              <HoneycombCell size={cell} state={state} />
            </FadeIn>
          );
        })}
        <Mauri pose="fly" size={44} motion="hover" style={{ marginLeft: -4, marginBottom: cell * 0.6 }} />
      </View>
    </View>
  );
}

/**
 * Engagement progress as connected cells. The current step is written out underneath, so long
 * Nepali labels never have to squeeze into five columns.
 */
export function Stepper({ steps, current, caption }: { steps: string[]; current: number; caption: string }) {
  return (
    <View
      accessible
      accessibilityRole="progressbar"
      accessibilityLabel={caption}
      accessibilityValue={{ min: 1, max: steps.length, now: Math.min(current + 1, steps.length) }}
      style={{ gap: space.sm }}
    >
      <View style={{ flexDirection: 'row', alignItems: 'center' }}>
        {steps.map((s, i) => {
          const done = i < current;
          const now = i === current;
          return (
            <View key={s} style={{ flexDirection: 'row', alignItems: 'center', flex: i < steps.length - 1 ? 1 : 0 }}>
              <Svg width={26} height={26} viewBox="0 0 26 26">
                <Path
                  d={hexPath(13, 13, 11.5)}
                  fill={done ? colors.sage : now ? colors.brick : colors.paper}
                  stroke={done ? colors.sage : now ? colors.brick : colors.line}
                  strokeWidth={1.6}
                  strokeLinejoin="round"
                />
                {done ? (
                  <Path d="M8.6 13.2l3 3 5.6-5.8" fill="none" stroke={colors.paper} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                ) : now ? (
                  <Path d={hexPath(13, 13, 4)} fill={colors.paper} />
                ) : null}
              </Svg>
              {i < steps.length - 1 ? (
                <View style={{ flex: 1, height: 2, marginHorizontal: 2, backgroundColor: done ? colors.sage : colors.line }} />
              ) : null}
            </View>
          );
        })}
      </View>
      <Txt variant="small" color={colors.inkSoft}>{caption}</Txt>
    </View>
  );
}

/**
 * Blind Review identity: the applicant is only a letter in a cell, the same for everyone.
 * Ink cell, honey letter. Deliberately no mascot and no colour per person.
 */
export function LetterCell({ letter, size = 48 }: { letter: string; size?: number }) {
  return (
    <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}>
      <Svg width={size} height={size} viewBox="0 0 48 48" style={{ position: 'absolute' }}>
        <Path d={hexPath(24, 24, 23)} fill={colors.ink} />
      </Svg>
      <Txt variant="h2" color={colors.honeyLight}>{letter}</Txt>
    </View>
  );
}
