// The Sajha Kaam mark: Mauri the honey bee on a brick tile, the same art as the launcher icon.
// Lockups: `Logo` (mark only), `Brand` (horizontal: mark + name in both scripts + tagline),
// `BrandStacked` (centred, for welcome screens). The wordmark is live text in the app fonts,
// never a PNG, so it stays sharp and costs no bytes. Minimum mark size: 24 px; clear space = 1/4 of the mark.
import { View } from 'react-native';
import Svg, { Path } from 'react-native-svg';

import i18n, { useT } from '@/i18n';
import { colors, space } from '@/theme';

import { hexPath } from './brand/geometry';
import { Mauri } from './brand/Mauri';
import { Txt } from './Txt';

/** The mark on a brick tile, like the app icon. `animated` gives one wing burst (never with reduce motion / Lite). */
export function Logo({ size = 72, animated = false }: { size?: number; animated?: boolean }) {
  const { t } = useT();
  return (
    <View
      accessible
      accessibilityRole="image"
      accessibilityLabel={t('common.appName')}
      style={{ width: size, height: size, borderRadius: size * 0.24, backgroundColor: colors.brick, alignItems: 'center', justifyContent: 'center' }}
    >
      <Mauri pose="mark" size={size * 0.86} motion={animated ? 'burst' : 'none'} />
      {/* the sage "confirmed" cell, bottom-right, as on the icon */}
      <View style={{ position: 'absolute', right: size * 0.08, bottom: size * 0.08 }}>
        <Svg width={size * 0.26} height={size * 0.26} viewBox="0 0 24 24">
          <Path d={hexPath(12, 12, 11)} fill={colors.sage} stroke={colors.brick} strokeWidth={2} />
          <Path d="M7.8 12.3l2.9 2.9 5.6-5.9" fill="none" stroke={colors.paper} strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" />
        </Svg>
      </View>
    </View>
  );
}

function names() {
  return { ne: i18n.getFixedT('ne')('common.appName'), en: i18n.getFixedT('en')('common.appName') };
}

/** Horizontal lockup: mark + name in both scripts + tagline. The name is always bilingual: it is the brand. */
export function Brand({ animated = false, tagline = true }: { animated?: boolean; tagline?: boolean }) {
  const { t } = useT();
  const n = names();
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.md }}>
      <Logo size={60} animated={animated} />
      <View style={{ flex: 1, gap: 0 }}>
        <Txt variant="h2">{n.ne}</Txt>
        <Txt variant="label" color={colors.inkSoft}>{n.en.toUpperCase()}</Txt>
        {tagline ? <Txt variant="small" color={colors.inkSoft} style={{ marginTop: 2 }}>{t('common.tagline')}</Txt> : null}
      </View>
    </View>
  );
}

/** Stacked lockup for the welcome screen. */
export function BrandStacked() {
  const n = names();
  return (
    <View style={{ alignItems: 'center', gap: 2 }}>
      <Txt variant="display" center>{n.ne}</Txt>
      <Txt variant="label" color={colors.inkSoft} center>{n.en.toUpperCase()}</Txt>
    </View>
  );
}
