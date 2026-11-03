// Motion rules (docs/BRAND.md § Motion):
//  - UI feedback 120-250 ms; content arriving 220 ms; the splash sequence is the one exception (≤ 1.2 s, skippable).
//  - Ease-out for things arriving, ease-in-out for things moving, a light spring only for press feedback.
//  - Motion explains something (arrived, confirmed, moved); it never decorates or nags.
//  - None at all with the phone's "reduce motion" setting or in Lite Mode.
import { useEffect, useState } from 'react';
import { AccessibilityInfo, Easing, Platform } from 'react-native';

import { usePrefs } from '@/state/prefs';

export const DURATION = 220;
export const FAST = 140;
// Material 3 "emphasized decelerate"-style curve: quick start, soft landing.
export const EASE_OUT = Easing.bezier(0.05, 0.7, 0.1, 1);
export const EASE_IN_OUT = Easing.bezier(0.2, 0, 0, 1);
// Native driver is not available on web; there the JS driver is used.
export const NATIVE = Platform.OS !== 'web';

export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    let alive = true;
    AccessibilityInfo.isReduceMotionEnabled()
      .then((v) => alive && setReduced(v))
      .catch(() => undefined);
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduced);
    return () => {
      alive = false;
      sub.remove();
    };
  }, []);
  return reduced;
}

/** True when decorative/explanatory motion may play: not reduce-motion, not Lite Mode. */
export function useMotionOK(): boolean {
  const reduced = useReducedMotion();
  const lite = usePrefs((s) => s.lite);
  return !reduced && !lite;
}
