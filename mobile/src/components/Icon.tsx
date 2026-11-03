// The Sajha Kaam icon set: one 24 px grid, one 1.8 stroke, round caps. Pure react-native-svg,
// replacing @expo/vector-icons (which ships whole icon fonts in the APK).
// House trait: where an icon stands for *our* idea (board, blind review, passport stamp, Kaam Path)
// it is built on the honeycomb hexagon, so the brand is in the icons, not pasted on top of them.
import Svg, { Circle, Path, Rect } from 'react-native-svg';

import { colors } from '@/theme';

import { hexPath } from './brand/geometry';

type Shape = { d?: string; rect?: [number, number, number, number, number]; circle?: [number, number, number]; fill?: boolean };

const H = (cx: number, cy: number, r: number) => hexPath(cx, cy, r);

const ICONS = {
  board: [{ d: H(7.6, 8, 4.3) }, { d: H(16.4, 8, 4.3) }, { d: H(12, 15.6, 4.3) }],
  post: [{ rect: [4, 3, 16, 18, 2.5] }, { d: 'M12 8v8M8 12h8' }],
  cards: [{ rect: [8, 3, 12, 15, 2] }, { d: 'M4.5 7v11.5a2.5 2.5 0 0 0 2.5 2.5h9' }],
  review: [{ d: H(12, 12, 9.5) }, { d: 'M7.8 11.6c2.6 2.6 5.8 2.6 8.4 0M9.4 13.9l-.9 1.5M12 14.7v1.7M14.6 13.9l.9 1.5' }],
  work: [{ rect: [3, 7, 18, 13, 2.5] }, { d: 'M9 7V5.5A1.5 1.5 0 0 1 10.5 4h3A1.5 1.5 0 0 1 15 5.5V7M3 12.5h18' }],
  passport: [{ rect: [5, 3, 14, 18, 2.2] }, { d: H(12, 10, 3.2) }, { d: 'M9 16.5h6' }],
  inbox: [{ d: 'M6 16v-5a6 6 0 0 1 12 0v5l1.5 2h-15L6 16zM10 20.5a2 2 0 0 0 4 0' }],
  help: [{ circle: [12, 12, 9] }, { d: 'M9.6 9.6a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1.1.8-1.1 1.6v.3' }, { circle: [12, 17, 0.9], fill: true }],
  check: [{ d: 'M5 12.5l4.5 4.5L19 7.5' }],
  chevronRight: [{ d: 'M9.5 5l7 7-7 7' }],
  chevronLeft: [{ d: 'M14.5 5l-7 7 7 7' }],
  clock: [{ circle: [12, 12, 9] }, { d: 'M12 7.5V12l3 2' }],
  lock: [{ rect: [5, 10.5, 14, 10, 2] }, { d: 'M8 10.5V8a4 4 0 0 1 8 0v2.5' }],
  shield: [{ d: 'M12 3l7 3v5.5c0 4.4-3 8-7 9.5-4-1.5-7-5.1-7-9.5V6l7-3z' }, { d: 'M9 12l2 2 4-4' }],
  share: [{ d: 'M12 3.5v11M7.5 8L12 3.5 16.5 8M5 13v5a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-5' }],
  qr: [{ rect: [4, 4, 6, 6, 1] }, { rect: [14, 4, 6, 6, 1] }, { rect: [4, 14, 6, 6, 1] }, { d: 'M14 14h2.5v2.5H14zM17.5 17.5H20V20h-2.5zM14 20h.01M20 14h.01' }],
  globe: [{ circle: [12, 12, 9] }, { d: 'M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3z' }],
  wifiOff: [{ d: 'M2.5 8.8a14 14 0 0 1 5-2.9M11 5a14 14 0 0 1 10.5 3.8M5.5 12.3a9.5 9.5 0 0 1 4-2.1M15 10.6a9.5 9.5 0 0 1 3.5 1.7M9 15.8a4.6 4.6 0 0 1 6 0M12 19.3h.01M3.5 3.5l17 17' }],
  upload: [{ d: 'M12 15V4.5M7.5 9L12 4.5 16.5 9M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3' }],
  message: [{ d: 'M4.5 5h15a1 1 0 0 1 1 1v9.5a1 1 0 0 1-1 1H10L5.5 20v-3.5h-1a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z' }],
  flag: [{ d: 'M5.5 21V4M5.5 4.5h11l-2.2 4 2.2 4h-11' }],
  trail: [{ d: 'M4 20c5 0 4-8 8-8s3-8 8-8', fill: false }, { d: H(19.5, 4.5, 2.6) }],
  stamp: [{ d: H(12, 12, 9.5) }, { d: 'M8.4 12.2l2.5 2.5 4.7-4.9' }],
  search: [{ circle: [11, 11, 6.5] }, { d: 'M16 16l4.5 4.5' }],
  close: [{ d: 'M6 6l12 12M18 6L6 18' }],
  plus: [{ d: 'M12 5v14M5 12h14' }],
  star: [{ d: 'M12 3.8l2.5 5.1 5.6.8-4 4 .9 5.6-5-2.7-5 2.7.9-5.6-4-4 5.6-.8L12 3.8z' }],
  brush: [{ d: 'M14.5 4.5l5 5L9.5 19.5H4.5v-5l10-10zM12.5 6.5l5 5' }],
  leaf: [{ d: 'M5 19C5 10.5 10 5 19.5 4.5 19 14 13.5 19 5 19zM5 19l8.5-8.5' }],
  eye: [{ d: 'M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z' }, { circle: [12, 12, 3] }],
} satisfies Record<string, Shape[]>;

export type IconName = keyof typeof ICONS;

export function Icon({ name, size = 24, color = colors.ink, strokeWidth = 1.8 }: {
  name: IconName;
  size?: number;
  color?: string;
  strokeWidth?: number;
}) {
  const shapes: Shape[] = ICONS[name];
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" accessibilityElementsHidden importantForAccessibility="no">
      {shapes.map((s, i) => {
        const paint = s.fill
          ? { fill: color }
          : { fill: 'none', stroke: color, strokeWidth, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };
        if (s.rect) {
          const [x, y, w, h, r] = s.rect;
          return <Rect key={i} x={x} y={y} width={w} height={h} rx={r} {...paint} />;
        }
        if (s.circle) {
          const [cx, cy, r] = s.circle;
          return <Circle key={i} cx={cx} cy={cy} r={r} {...paint} />;
        }
        return <Path key={i} d={s.d} {...paint} />;
      })}
    </Svg>
  );
}
