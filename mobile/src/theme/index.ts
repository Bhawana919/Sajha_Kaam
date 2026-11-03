// Sajha Kaam design tokens: "Mauri" edition. Light theme, flat fills only (no gradients, no glass).
//
// Where the colours come from (see docs/BRAND.md for the reasoning):
//   brick  Newari terracotta (Bhaktapur, Patan): the primary action. One brick button per screen.
//   paper  Lokta paper: warm off-white surface instead of a clinical #FFF / #F8FAFC app grey.
//   ink    Near-black with a green cast, so text never reads as pure #000 on warm paper.
//   honey  Mauri's colour. Accent only: Kaam Path cells, Passport stamps, the one highlighted fact.
//   sage   "Confirmed / done". Never used for decoration, so it keeps its meaning.
// Highlights are honey *wash* + ink text (AA contrast), never a coloured left stripe or a glow.
export const colors = {
  paper: '#F6F2E9',
  paperDeep: '#EFE9DC',
  ink: '#252A25',
  inkSoft: '#5B6058',
  brick: '#A64C32',
  brickDeep: '#8A3D27',
  brickSoft: '#F3E1D8',
  sage: '#5F6B55',
  sageSoft: '#E3E7DC',
  honey: '#E3A72F',
  honeyLight: '#EDB63E',
  honeyDeep: '#B97A12',
  honeyWash: '#F8EBCB',
  blush: '#E98A5F', // inside the mascot only
  clay: '#EAE4D8',
  line: '#D5CFC2',
  white: '#FFFFFF',
  warnSoft: '#F6EBCF',
  warnInk: '#6B4700',
};

export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 };
export const radius = { sm: 6, md: 10, lg: 14, pill: 999 };
export const border = 1;
export const touchMin = 48;
/** Phone-width column, centred on tablets and desktop browsers so cards never stretch across the screen. */
export const contentMaxWidth = 640;

// Only 400 and 600 ship (smaller APK); "bold" maps to semibold.
export const fonts = {
  latin: { regular: 'Inter_400Regular', semibold: 'Inter_600SemiBold', bold: 'Inter_600SemiBold' },
  devanagari: {
    regular: 'NotoSansDevanagari_400Regular',
    semibold: 'NotoSansDevanagari_600SemiBold',
    bold: 'NotoSansDevanagari_600SemiBold',
  },
};

// Sizes only; line-height is always >= 1.4x and never a fixed container height.
export const typeScale = {
  display: { fontSize: 30, weight: 'semibold' },
  h1: { fontSize: 24, weight: 'semibold' },
  h2: { fontSize: 19, weight: 'semibold' },
  h3: { fontSize: 16, weight: 'semibold' },
  body: { fontSize: 15, weight: 'regular' },
  small: { fontSize: 13, weight: 'regular' },
  label: { fontSize: 12, weight: 'semibold' },
} as const;

export type TypeVariant = keyof typeof typeScale;
