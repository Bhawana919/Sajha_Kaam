// Small, meaningful motion. Content arriving (FadeIn), a confirmed step (SuccessMark),
// press feedback (PressScale) and calm loading placeholders (Skeleton).
// No bounce-for-fun, no confetti; nothing at all with "reduce motion" on or in Lite Mode.
import { type ReactNode, useEffect, useState } from 'react';
import { Animated, Easing, Pressable, type PressableProps, type StyleProp, type ViewStyle } from 'react-native';
import Svg, { Path } from 'react-native-svg';

import { DURATION, EASE_OUT, NATIVE, useMotionOK } from '@/lib/motion';
import { colors, radius } from '@/theme';

import { hexPath } from './brand/geometry';

/** Fades and lifts content 8 px into place. `delay` staggers list items (capped, so long lists never wait). */
export function FadeIn({ children, delay = 0, style }: { children: ReactNode; delay?: number; style?: StyleProp<ViewStyle> }) {
  const ok = useMotionOK();
  const [v] = useState(() => new Animated.Value(ok ? 0 : 1));
  useEffect(() => {
    if (!ok) {
      v.setValue(1);
      return;
    }
    Animated.timing(v, { toValue: 1, duration: DURATION, delay: Math.min(delay, 180), easing: EASE_OUT, useNativeDriver: NATIVE }).start();
  }, [ok, delay, v]);
  return (
    <Animated.View
      style={[style, { opacity: v, transform: [{ translateY: v.interpolate({ inputRange: [0, 1], outputRange: [8, 0] }) }] }]}
    >
      {children}
    </Animated.View>
  );
}

/**
 * Pressable that dips to 97 % while held and springs back: the finger feels the press
 * even on phones without haptics. Spring is critically damped (no wobble).
 */
export function PressScale({ children, style, disabled, ...rest }: PressableProps & { children: ReactNode; style?: StyleProp<ViewStyle> }) {
  const ok = useMotionOK();
  const [v] = useState(() => new Animated.Value(1));
  const to = (value: number) =>
    ok && Animated.spring(v, { toValue: value, useNativeDriver: NATIVE, speed: 40, bounciness: 0 }).start();
  return (
    <Pressable
      {...rest}
      disabled={disabled}
      onPressIn={(e) => { to(0.97); rest.onPressIn?.(e); }}
      onPressOut={(e) => { to(1); rest.onPressOut?.(e); }}
    >
      <Animated.View style={[style, { transform: [{ scale: v }] }]}>{children}</Animated.View>
    </Pressable>
  );
}

/** A sage honeycomb cell with a check that settles in once, for a step that really happened (sent, posted, paid). */
export function SuccessMark({ size = 64, label }: { size?: number; label: string }) {
  const ok = useMotionOK();
  const [v] = useState(() => new Animated.Value(ok ? 0 : 1));
  useEffect(() => {
    if (!ok) {
      v.setValue(1);
      return;
    }
    Animated.timing(v, { toValue: 1, duration: 260, easing: EASE_OUT, useNativeDriver: NATIVE }).start();
  }, [ok, v]);
  return (
    <Animated.View
      accessible
      accessibilityRole="image"
      accessibilityLabel={label}
      style={{
        width: size,
        height: size,
        opacity: v,
        transform: [
          { scale: v.interpolate({ inputRange: [0, 1], outputRange: [0.8, 1] }) },
          { rotate: v.interpolate({ inputRange: [0, 1], outputRange: ['-30deg', '0deg'] }) },
        ],
      }}
    >
      <Svg width={size} height={size} viewBox="0 0 24 24">
        <Path d={hexPath(12, 12, 11)} fill={colors.sage} />
        <Path d="M7.6 12.3l3 3 5.8-6" fill="none" stroke={colors.paper} strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" />
      </Svg>
    </Animated.View>
  );
}

/** A calm placeholder block that breathes while data loads (no shimmer sweep: cheaper and quieter). */
export function Skeleton({ height = 16, width = '100%', style }: { height?: number; width?: number | `${number}%`; style?: ViewStyle }) {
  const ok = useMotionOK();
  const [v] = useState(() => new Animated.Value(0.55));
  useEffect(() => {
    if (!ok) return;
    const ease = Easing.inOut(Easing.sin);
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(v, { toValue: 1, duration: 700, easing: ease, useNativeDriver: NATIVE }),
        Animated.timing(v, { toValue: 0.55, duration: 700, easing: ease, useNativeDriver: NATIVE }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [ok, v]);
  return <Animated.View style={[{ height, width, borderRadius: radius.sm, backgroundColor: colors.clay, opacity: v }, style]} />;
}
