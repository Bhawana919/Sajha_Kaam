// Bottom tabs with our own icons. The active tab sits in a small honey hexagon (the brand cell),
// which also gives a second, non-colour cue for the current tab.
import { Tabs } from 'expo-router';
import { useEffect, useState } from 'react';
import { Animated, View } from 'react-native';
import Svg, { Path } from 'react-native-svg';

import { useT } from '@/i18n';
import { EASE_OUT, NATIVE, useMotionOK } from '@/lib/motion';
import { colors, fonts } from '@/theme';

import { hexPath } from './brand/geometry';
import { Icon, type IconName } from './Icon';

type Tab = { name: string; titleKey: string; icon: IconName };

function TabIcon({ name, focused, color }: { name: IconName; focused: boolean; color: string }) {
  const ok = useMotionOK();
  const [v] = useState(() => new Animated.Value(focused ? 1 : 0));
  useEffect(() => {
    if (!ok) {
      v.setValue(focused ? 1 : 0);
      return;
    }
    Animated.timing(v, { toValue: focused ? 1 : 0, duration: 200, easing: EASE_OUT, useNativeDriver: NATIVE }).start();
  }, [focused, ok, v]);
  return (
    <View style={{ width: 40, height: 34, alignItems: 'center', justifyContent: 'center' }}>
      <Animated.View style={{ position: 'absolute', opacity: v, transform: [{ scale: v.interpolate({ inputRange: [0, 1], outputRange: [0.6, 1] }) }] }}>
        <Svg width={40} height={36} viewBox="0 0 40 36">
          <Path d={hexPath(20, 18, 17.5)} fill={colors.honeyWash} />
        </Svg>
      </Animated.View>
      <Icon name={name} size={22} color={color} strokeWidth={focused ? 2.1 : 1.8} />
    </View>
  );
}

export function RoleTabs({ tabs }: { tabs: Tab[] }) {
  const { t, locale } = useT();
  const ok = useMotionOK();
  const family = locale === 'ne' ? fonts.devanagari.semibold : fonts.latin.semibold;
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        animation: ok ? 'shift' : 'none',
        tabBarActiveTintColor: colors.ink,
        tabBarInactiveTintColor: colors.inkSoft,
        tabBarStyle: { backgroundColor: colors.paper, borderTopColor: colors.line, minHeight: 64, paddingTop: 6 },
        tabBarLabelStyle: { fontFamily: family, fontSize: 11 },
      }}
    >
      {tabs.map((tab) => (
        <Tabs.Screen
          key={tab.name}
          name={tab.name}
          options={{
            title: t(tab.titleKey),
            tabBarAccessibilityLabel: t(tab.titleKey),
            tabBarIcon: ({ color, focused }) => <TabIcon name={tab.icon} focused={focused} color={color as string} />,
          }}
        />
      ))}
    </Tabs>
  );
}
