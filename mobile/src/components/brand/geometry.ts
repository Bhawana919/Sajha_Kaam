// Mauri (मौरी), the Sajha Kaam honey bee: one geometry, two renderers.
// The app draws it with react-native-svg (Mauri.tsx); scripts/make-icons.ts writes the same shapes
// to the icon/splash SVGs, so the launcher icon, the splash and the in-app bee are pixel-identical.
//
// Style: flat fills + one ink outline weight, in the spirit of Mithila (Janakpur) painting and
// Nepali truck art: bold outline, flat colour, no gradients. It stays readable at 24 px and costs
// no image bytes. Her signature is the *brick* rear stripe (the brand colour) next to an ink one.
// No React Native imports here: this file is also read by Node scripts.
import { colors } from '../../theme';

export type Prim =
  | { t: 'p'; d: string; f?: string; s?: string; sw?: number; tr?: string; dash?: string }
  | { t: 'e'; cx: number; cy: number; rx: number; ry: number; f?: string; s?: string; sw?: number; tr?: string }
  | { t: 'c'; cx: number; cy: number; r: number; f?: string; s?: string; sw?: number }
  | { t: 'r'; x: number; y: number; w: number; h: number; rx?: number; f?: string; s?: string; sw?: number; tr?: string };

export type Pose = 'wave' | 'peek' | 'card' | 'tag' | 'sleep' | 'passport' | 'fly' | 'confused' | 'mark';

export type PoseSpec = {
  /** Drawn in their own layer so they can flutter. */
  wings: Prim[];
  body: Prim[];
  /** Whole-bee tilt in degrees (around the centre). */
  tilt?: number;
  /** Wing hinge, as a fraction of the 120 box, used as the flutter transform origin. */
  hinge?: [number, number];
};

const I = colors.ink;
const W = 4; // the one outline weight (in a 120 box)
const WING = '#FFFFFF';

/** A pointy-top hexagon path centred on (cx, cy). */
export function hexPath(cx: number, cy: number, r: number): string {
  const pts = [0, 1, 2, 3, 4, 5].map((i) => {
    const a = (Math.PI / 180) * (60 * i - 90);
    return `${(cx + r * Math.cos(a)).toFixed(2)} ${(cy + r * Math.sin(a)).toFixed(2)}`;
  });
  return `M${pts.join(' L')} Z`;
}

const wingsOpen: Prim[] = [
  { t: 'e', cx: 56, cy: 40, rx: 12, ry: 19, tr: 'rotate(-28 56 40)', f: WING, s: I, sw: W },
  { t: 'e', cx: 75, cy: 41, rx: 11, ry: 17, tr: 'rotate(24 75 41)', f: WING, s: I, sw: W },
];
const wingsFolded: Prim[] = [
  { t: 'e', cx: 66, cy: 47, rx: 8, ry: 18, tr: 'rotate(-72 66 47)', f: WING, s: I, sw: W },
];

const legs: Prim[] = [
  { t: 'p', d: 'M58 91 L55 99 M70 93 L69 101 M82 89 L85 97', s: I, sw: 3.5 },
];

const bodyCore: Prim[] = [
  { t: 'p', d: 'M94 65.5 L104.5 70 L94 74.5 Z', f: I, s: I, sw: 2, },
  { t: 'e', cx: 66, cy: 70, rx: 30, ry: 23, f: colors.honey },
  // ink stripe, then the brick brand stripe (shapes follow the body curve; the outline hides the joins)
  { t: 'p', d: 'M58 47.8 Q62 47 66 47 L66 93 Q62 93 58 92.2 Z', f: I },
  { t: 'p', d: 'M75 48.3 Q79.5 49.2 83.5 51.2 L83.5 88.8 Q79.5 90.8 75 91.7 Z', f: colors.brick },
  { t: 'e', cx: 66, cy: 70, rx: 30, ry: 23, s: I, sw: W },
];

const antennae = (dx = 0, dy = 0): Prim[] => [
  { t: 'p', d: `M${30 + dx} ${41 + dy} Q${26 + dx} ${29 + dy} ${17 + dx} ${26 + dy} M${42 + dx} ${40 + dy} Q${46 + dx} ${28 + dy} ${54 + dx} ${24 + dy}`, s: I, sw: 3.5 },
  { t: 'c', cx: 17 + dx, cy: 26 + dy, r: 4, f: I },
  { t: 'c', cx: 54 + dx, cy: 24 + dy, r: 4, f: I },
];

const head: Prim[] = [{ t: 'c', cx: 36, cy: 60, r: 21, f: colors.honey, s: I, sw: W }];

const eyesOpen: Prim[] = [
  { t: 'e', cx: 29, cy: 59, rx: 3.4, ry: 4.6, f: I },
  { t: 'e', cx: 43, cy: 59, rx: 3.4, ry: 4.6, f: I },
  { t: 'c', cx: 30.2, cy: 57.2, r: 1.3, f: '#FFFFFF' },
  { t: 'c', cx: 44.2, cy: 57.2, r: 1.3, f: '#FFFFFF' },
];
const blush: Prim[] = [
  { t: 'e', cx: 23.5, cy: 67, rx: 4, ry: 2.4, f: colors.blush },
  { t: 'e', cx: 48.5, cy: 67, rx: 4, ry: 2.4, f: colors.blush },
];
const smile: Prim[] = [{ t: 'p', d: 'M31.5 67.5 Q36 72 40.5 67.5', s: I, sw: 2.8 }];

const face = [...head, ...eyesOpen, ...blush, ...smile];
const standard = (extra: Prim[] = [], withLegs = true): Prim[] => [
  ...(withLegs ? legs : []),
  ...bodyCore,
  ...antennae(),
  ...face,
  ...extra,
];

/** A small Kaam Card held in front of the body: two lines and a sage check. */
const heldCard: Prim[] = [
  { t: 'r', x: 46, y: 80, w: 42, h: 30, rx: 4, f: colors.paper, s: I, sw: 3.5, tr: 'rotate(-6 67 95)' },
  { t: 'p', d: 'M53 90 L72 88 M54 98 L67 96.6', s: I, sw: 3, tr: 'rotate(-6 67 95)' },
  { t: 'c', cx: 79, cy: 97, r: 6, f: colors.sage },
  { t: 'p', d: 'M76.3 97.2 L78.4 99.3 L82 95', s: '#FFFFFF', sw: 2.2 },
];

export const POSES: Record<Pose, PoseSpec> = {
  wave: {
    wings: wingsOpen,
    tilt: -6,
    hinge: [0.55, 0.42],
    body: standard([
      // a raised front leg, waving
      { t: 'p', d: 'M20 76 Q9 70 9 58', s: I, sw: 3.5 },
      { t: 'c', cx: 9, cy: 56, r: 3.5, f: I },
    ]),
  },
  mark: { wings: wingsOpen, hinge: [0.55, 0.42], body: standard() },
  card: { wings: wingsOpen, hinge: [0.55, 0.42], body: standard(heldCard, false) },
  tag: {
    wings: wingsOpen,
    hinge: [0.55, 0.42],
    body: standard(
      [
        { t: 'p', d: 'M66 93 L66 98', s: I, sw: 2.5 },
        { t: 'p', d: hexPath(66, 107, 10), f: colors.brick, s: I, sw: 3 },
        // the letter F as strokes, so it needs no font
        { t: 'p', d: 'M63 102 L63 112 M63 102 L69.5 102 M63 107 L68 107', s: '#FFFFFF', sw: 2.4 },
      ],
      false,
    ),
  },
  sleep: {
    wings: wingsFolded,
    hinge: [0.55, 0.4],
    body: [
      ...bodyCore,
      ...antennae(0, 4),
      ...head,
      { t: 'p', d: 'M25.5 60 Q29 63.5 32.5 60 M39.5 60 Q43 63.5 46.5 60', s: I, sw: 2.8 },
      ...blush,
      { t: 'p', d: 'M33.5 68.5 Q36 70.5 38.5 68.5', s: I, sw: 2.6 },
      { t: 'p', d: 'M82 24 L90 24 L82 33 L90 33 M96 10 L101.5 10 L96 16.5 L101.5 16.5', s: colors.inkSoft, sw: 3 },
    ],
  },
  passport: {
    wings: wingsOpen,
    hinge: [0.55, 0.42],
    body: standard(
      [
        { t: 'r', x: 50, y: 79, w: 32, h: 36, rx: 4, f: colors.brick, s: I, sw: 3.5, tr: 'rotate(-5 66 97)' },
        { t: 'p', d: hexPath(66, 94, 7), f: colors.honey, s: I, sw: 2.4 },
        { t: 'p', d: 'M58 107 L74 106', s: colors.paper, sw: 2.6 },
      ],
      false,
    ),
  },
  fly: {
    wings: wingsOpen,
    tilt: -12,
    hinge: [0.55, 0.42],
    body: [
      // the waggle trail she leaves: "this is where the work is"
      { t: 'p', d: 'M100 80 C110 92 100 104 114 112', s: colors.inkSoft, sw: 3, dash: '0.5 7' },
      ...bodyCore,
      ...antennae(),
      ...face,
    ],
  },
  confused: {
    wings: wingsOpen,
    tilt: 8,
    hinge: [0.55, 0.42],
    body: [
      ...legs,
      ...bodyCore,
      ...antennae(),
      ...head,
      ...eyesOpen,
      ...blush,
      { t: 'p', d: 'M25 50.5 Q28.5 47 33 49.5', s: I, sw: 2.6 },
      { t: 'p', d: 'M32 68.5 Q34 66.5 36 68.5 Q38 70.5 40 68.5', s: I, sw: 2.6 },
      { t: 'p', d: 'M92 18 Q92 10 99 10 Q106 10 106 17 Q106 22 100 24.5 L100 29', s: I, sw: 3.5 },
      { t: 'c', cx: 100, cy: 36, r: 2.4, f: I },
    ],
  },
  peek: {
    wings: [],
    body: [
      ...antennae(24, 9),
      { t: 'p', d: 'M39.22 84 A24 24 0 1 1 80.78 84 Z', f: colors.honey, s: I, sw: W },
      { t: 'e', cx: 52, cy: 69, rx: 3.4, ry: 4.6, f: I },
      { t: 'e', cx: 68, cy: 69, rx: 3.4, ry: 4.6, f: I },
      { t: 'c', cx: 53.2, cy: 67.2, r: 1.3, f: '#FFFFFF' },
      { t: 'c', cx: 69.2, cy: 67.2, r: 1.3, f: '#FFFFFF' },
      { t: 'e', cx: 43, cy: 75, rx: 4, ry: 2.2, f: colors.blush },
      { t: 'e', cx: 77, cy: 75, rx: 4, ry: 2.2, f: colors.blush },
      { t: 'p', d: 'M10 84 L110 84', s: I, sw: W },
      { t: 'c', cx: 46, cy: 84, r: 6, f: colors.honey, s: I, sw: 3.5 },
      { t: 'c', cx: 74, cy: 84, r: 6, f: colors.honey, s: I, sw: 3.5 },
    ],
  },
};

/** Serialise primitives to SVG markup (used by the icon scripts). */
export function primsToSvg(prims: Prim[], fillOverride?: string): string {
  const paint = (p: { f?: string; s?: string; sw?: number }) => {
    const f = p.f ? (fillOverride ?? p.f) : 'none';
    const s = p.s ? ` stroke="${fillOverride ?? p.s}" stroke-width="${p.sw ?? W}" stroke-linecap="round" stroke-linejoin="round"` : '';
    return `fill="${f}"${s}`;
  };
  return prims
    .map((p) => {
      const tr = 'tr' in p && p.tr ? ` transform="${p.tr}"` : '';
      switch (p.t) {
        case 'p':
          return `<path d="${p.d}" ${paint(p)}${p.dash ? ` stroke-dasharray="${p.dash}"` : ''}${tr}/>`;
        case 'e':
          return `<ellipse cx="${p.cx}" cy="${p.cy}" rx="${p.rx}" ry="${p.ry}" ${paint(p)}${tr}/>`;
        case 'c':
          return `<circle cx="${p.cx}" cy="${p.cy}" r="${p.r}" ${paint(p)}/>`;
        case 'r':
          return `<rect x="${p.x}" y="${p.y}" width="${p.w}" height="${p.h}" rx="${p.rx ?? 0}" ${paint(p)}${tr}/>`;
      }
    })
    .join('');
}

export function poseToSvg(pose: Pose): string {
  const spec = POSES[pose];
  const inner = primsToSvg(spec.wings) + primsToSvg(spec.body);
  return spec.tilt ? `<g transform="rotate(${spec.tilt} 60 60)">${inner}</g>` : inner;
}
