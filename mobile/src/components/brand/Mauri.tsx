// Mauri (मौरी), the honey-bee guide. Pure vector (react-native-svg): no image bytes.
// Used only for guidance, empty / error / offline states, onboarding and a real confirmed step.
// Never on Blind Review scoring controls, never "speaking for" a decision.
//
// motion: 'hover' = a calm bob plus short wing bursts (empty states, welcome);
//         'burst' = one quick flutter (a confirmed step); 'none' = still.
// All motion is off with the phone's reduce-motion setting and in Lite Mode.
import { useEffect, useState } from 'react';
import { Animated, Easing, View, type ViewStyle } from 'react-native';
import Svg, { Circle, Ellipse, G, Path, Rect } from 'react-native-svg';

import { NATIVE, useMotionOK } from '@/lib/motion';

import { POSES, type Pose, type Prim } from './geometry';

function Prims({ items }: { items: Prim[] }) {
  return (
    <>
      {items.map((p, i) => {
        const paint = {
          fill: p.f ?? 'none',
          stroke: p.s,
          strokeWidth: p.s ? (p.sw ?? 4) : undefined,
          strokeLinecap: 'round' as const,
          strokeLinejoin: 'round' as const,
        };
        switch (p.t) {
          case 'p':
            return <Path key={i} d={p.d} {...paint} strokeDasharray={p.dash} transform={p.tr || undefined} />;
          case 'e':
            return <Ellipse key={i} cx={p.cx} cy={p.cy} rx={p.rx} ry={p.ry} {...paint} transform={p.tr || undefined} />;
          case 'c':
            return <Circle key={i} cx={p.cx} cy={p.cy} r={p.r} {...paint} />;
          case 'r':
            return <Rect key={i} x={p.x} y={p.y} width={p.w} height={p.h} rx={p.rx} {...paint} transform={p.tr || undefined} />;
        }
        return null;
      })}
    </>
  );
}

type Props = {
  pose?: Pose;
  size?: number;
  motion?: 'none' | 'burst' | 'hover';
  /** Decorative by default (hidden from screen readers). Pass a label when Mauri carries meaning. */
  label?: string;
  style?: ViewStyle;
};

export function Mauri({ pose = 'mark', size = 96, motion = 'none', label, style }: Props) {
  const spec = POSES[pose];
  const ok = useMotionOK();
  const play = ok && motion !== 'none';
  const [flap] = useState(() => new Animated.Value(0));
  const [bob] = useState(() => new Animated.Value(0));

  useEffect(() => {
    if (!play || spec.wings.length === 0) return;
    // One flap = 70 ms down + 70 ms up: fast enough to read as a bee, short enough to stay calm.
    const flapOnce = Animated.sequence([
      Animated.timing(flap, { toValue: 1, duration: 70, easing: Easing.linear, useNativeDriver: NATIVE }),
      Animated.timing(flap, { toValue: 0, duration: 70, easing: Easing.linear, useNativeDriver: NATIVE }),
    ]);
    const burst = Animated.sequence([flapOnce, flapOnce, flapOnce]);
    const anim = motion === 'hover'
      ? Animated.loop(Animated.sequence([burst, Animated.delay(2200)]))
      : burst;
    anim.start();
    return () => anim.stop();
  }, [play, motion, flap, spec.wings.length]);

  useEffect(() => {
    if (!play || motion !== 'hover') return;
    const ease = Easing.inOut(Easing.sin);
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(bob, { toValue: 1, duration: 1400, easing: ease, useNativeDriver: NATIVE }),
        Animated.timing(bob, { toValue: 0, duration: 1400, easing: ease, useNativeDriver: NATIVE }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [play, motion, bob]);

  const [hx, hy] = spec.hinge ?? [0.5, 0.5];
  const tilt = spec.tilt ? `rotate(${spec.tilt} 60 60)` : undefined;
  const a11y = label
    ? { accessible: true, accessibilityRole: 'image' as const, accessibilityLabel: label }
    : { accessibilityElementsHidden: true, importantForAccessibility: 'no-hide-descendants' as const };

  return (
    <Animated.View
      {...a11y}
      style={[
        { width: size, height: size },
        style,
        play && motion === 'hover'
          ? { transform: [{ translateY: bob.interpolate({ inputRange: [0, 1], outputRange: [0, -size * 0.04] }) }] }
          : null,
      ]}
    >
      {spec.wings.length ? (
        <Animated.View
          style={{
            position: 'absolute',
            width: size,
            height: size,
            transformOrigin: `${hx * 100}% ${hy * 100}%`,
            transform: [{ scaleY: flap.interpolate({ inputRange: [0, 1], outputRange: [1, 0.62] }) }],
          }}
        >
          <Svg width={size} height={size} viewBox="0 0 120 120">
            <G transform={tilt}><Prims items={spec.wings} /></G>
          </Svg>
        </Animated.View>
      ) : null}
      <View style={{ position: 'absolute', width: size, height: size }}>
        <Svg width={size} height={size} viewBox="0 0 120 120">
          <G transform={tilt}><Prims items={spec.body} /></G>
        </Svg>
      </View>
    </Animated.View>
  );
}

export type { Pose };
