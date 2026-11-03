// The launch sequence. The native splash (brick + Mauri, from app.json) hands over to this view,
// which starts with the identical picture, so there is no jump. Then, in about one second:
//   1. Mauri's wings beat and she lifts off               (0-420 ms)
//   2. she does a short "waggle run": in a hive this dance tells the others exactly where the
//      flowers are, our Kaam Card does the same for a job  (200-440 ms)
//   3. the bilingual wordmark and the promise rise in      (300-600 ms)
//   4. once the app is ready, the brick sheet fades away   (280 ms)
// Under Google's 1,000 ms guidance for an animated splash icon; tap anywhere to skip;
// with reduce motion or Lite Mode it is a plain 200 ms fade. It never waits longer than the app needs,
// beyond a 700 ms minimum so the bee is not a flicker.
import * as SplashScreen from 'expo-splash-screen';
import { useEffect, useRef, useState } from 'react';
import { Animated, Pressable, StyleSheet, View } from 'react-native';

import i18n from '@/i18n';
import { EASE_IN_OUT, EASE_OUT, NATIVE, useMotionOK } from '@/lib/motion';
import { colors, space } from '@/theme';

import { Mauri } from './brand/Mauri';
import { Txt } from './Txt';

const BEE = 132; // matches the bee's size inside assets/splash-icon.png at imageWidth 200

export function AnimatedSplash({ ready, fontsReady, onDone }: { ready: boolean; fontsReady: boolean; onDone: () => void }) {
  const ok = useMotionOK();
  const [lift] = useState(() => new Animated.Value(0));
  const [waggle] = useState(() => new Animated.Value(0));
  const [words] = useState(() => new Animated.Value(0));
  const [exit] = useState(() => new Animated.Value(0));
  const [introDone, setIntroDone] = useState(false);
  const leaving = useRef(false);

  const onLayout = () => {
    SplashScreen.hideAsync().catch(() => undefined);
  };

  useEffect(() => {
    if (!ok) {
      lift.setValue(1);
      words.setValue(1);
      const id = setTimeout(() => setIntroDone(true), 300);
      return () => clearTimeout(id);
    }
    const w = (to: number) => Animated.timing(waggle, { toValue: to, duration: 80, easing: EASE_IN_OUT, useNativeDriver: NATIVE });
    const seq = Animated.parallel([
      Animated.timing(lift, { toValue: 1, duration: 420, easing: EASE_OUT, useNativeDriver: NATIVE }),
      Animated.sequence([Animated.delay(200), w(1), w(-1), w(0)]),
      Animated.sequence([
        Animated.delay(300),
        Animated.timing(words, { toValue: 1, duration: 300, easing: EASE_OUT, useNativeDriver: NATIVE }),
      ]),
    ]);
    seq.start(() => setTimeout(() => setIntroDone(true), 100));
    return () => seq.stop();
  }, [ok, lift, waggle, words]);

  const leave = () => {
    if (leaving.current) return;
    leaving.current = true;
    Animated.timing(exit, { toValue: 1, duration: ok ? 280 : 200, easing: EASE_IN_OUT, useNativeDriver: NATIVE }).start(() => onDone());
  };

  useEffect(() => {
    if (ready && introDone) leave();
  });

  const ne = i18n.getFixedT('ne');
  const en = i18n.getFixedT('en');

  return (
    <Animated.View
      onLayout={onLayout}
      style={[StyleSheet.absoluteFill, styles.root, { opacity: exit.interpolate({ inputRange: [0, 1], outputRange: [1, 0] }) }]}
      accessibilityLabel={`${ne('common.appName')} · ${en('common.appName')}`}
    >
      <Pressable style={styles.center} onPress={() => ready && leave()} accessibilityRole="none">
        <Animated.View
          style={{
            transform: [
              { translateY: lift.interpolate({ inputRange: [0, 1], outputRange: [0, -40] }) },
              { translateX: waggle.interpolate({ inputRange: [-1, 1], outputRange: [-7, 7] }) },
              { rotate: waggle.interpolate({ inputRange: [-1, 1], outputRange: ['-8deg', '8deg'] }) },
              { scale: exit.interpolate({ inputRange: [0, 1], outputRange: [1, 0.92] }) },
            ],
          }}
        >
          <Mauri pose="mark" size={BEE} motion="burst" />
        </Animated.View>
        <Animated.View
          style={[
            styles.words,
            {
              opacity: words,
              transform: [{ translateY: words.interpolate({ inputRange: [0, 1], outputRange: [12, -24] }) }],
            },
          ]}
        >
          {fontsReady ? (
            <>
              <Txt variant="display" color={colors.paper} center>{ne('common.appName')}</Txt>
              <Txt variant="label" color={colors.honeyLight} center>{en('common.appName').toUpperCase()}</Txt>
              <View style={styles.rule} />
              <Txt variant="small" color={colors.brickSoft} center>{ne('common.tagline')}</Txt>
            </>
          ) : null}
        </Animated.View>
      </Pressable>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  root: { backgroundColor: colors.brick, zIndex: 10 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: space.xl },
  words: { position: 'absolute', top: '58%', left: space.xl, right: space.xl, alignItems: 'center', gap: 2 },
  rule: { width: 28, height: 2, borderRadius: 1, backgroundColor: colors.honey, marginVertical: space.sm },
});
