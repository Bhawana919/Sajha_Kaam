// Write every app-icon / splash / favicon SVG from the same Mauri geometry the app draws
// (src/components/brand/geometry.ts), so launcher, splash and in-app bee always match.
// Run: npx tsx scripts/make-icons.ts && python scripts/render-icons.py
//      (or node scripts/render-icons.mjs on Windows with Edge)
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

import { hexPath, POSES, type Prim, primsToSvg } from '../src/components/brand/geometry';
import { colors } from '../src/theme';

const OUT = join(__dirname, '..', 'assets', 'brand');
mkdirSync(OUT, { recursive: true });

const svg = (inner: string, size = 1024) =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 1024 1024">${inner}</svg>\n`;

/** The bee (120 box) scaled to `frac` of the 1024 canvas, centred, nudged by (dx, dy) in canvas px. */
function bee(frac: number, dx = 0, dy = 0, body?: string, wings?: string): string {
  const s = (1024 * frac) / 120;
  const off = (1024 - 1024 * frac) / 2;
  const spec = POSES.mark;
  return `<g transform="translate(${off + dx} ${off + dy}) scale(${s.toFixed(4)})">${wings ?? primsToSvg(spec.wings)}${body ?? primsToSvg(spec.body)}</g>`;
}

/** The sage "confirmed" cell (bottom-right), in canvas px. */
function badge(cx: number, cy: number, r: number, ring = colors.brick): string {
  const k = r / 11;
  return (
    `<path d="${hexPath(cx, cy, r)}" fill="${colors.sage}" stroke="${ring}" stroke-width="${(2 * k).toFixed(1)}" stroke-linejoin="round"/>` +
    `<path d="M${cx - 4.2 * k} ${cy + 0.3 * k} l${2.9 * k} ${2.9 * k} l${5.6 * k} ${-5.9 * k}" fill="none" stroke="${colors.paper}" stroke-width="${(2.4 * k).toFixed(1)}" stroke-linecap="round" stroke-linejoin="round"/>`
  );
}

// Monochrome (Android themed icon): alpha only. Silhouette in white, details cut out.
function mono(p: Prim): 'cut' | 'keep' {
  const dark = p.f === colors.ink || p.f === colors.brick;
  if (p.t === 'c' && p.r >= 3.5) return 'keep'; // antenna tips are part of the silhouette
  if (dark && !p.s) return 'cut';
  if (p.s && !p.f && (p.sw ?? 4) < 3) return 'cut';
  return 'keep';
}
function monoLayers(frac: number) {
  const all = [...POSES.mark.wings, ...POSES.mark.body];
  const keep = primsToSvg(all.filter((p) => mono(p) === 'keep'), '#FFFFFF');
  const cut = primsToSvg(all.filter((p) => mono(p) === 'cut'), '#000000');
  const s = (1024 * frac) / 120;
  const off = (1024 - 1024 * frac) / 2;
  const g = (inner: string) => `<g transform="translate(${off} ${off}) scale(${s.toFixed(4)})">${inner}</g>`;
  return { keep: g(keep), cut: g(cut) };
}
function monoBee(frac: number): string {
  const all = [...POSES.mark.wings, ...POSES.mark.body];
  const keep = primsToSvg(all.filter((p) => mono(p) === 'keep'), '#FFFFFF');
  const cut = primsToSvg(all.filter((p) => mono(p) === 'cut'), '#000000');
  const s = (1024 * frac) / 120;
  const off = (1024 - 1024 * frac) / 2;
  return (
    `<mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="1024" height="1024"><rect width="1024" height="1024" fill="#000"/>` +
    `<g transform="translate(${off} ${off}) scale(${s.toFixed(4)})">${keep}${cut}</g></mask>` +
    `<rect width="1024" height="1024" fill="#FFFFFF" mask="url(#m)"/>`
  );
}

const files: Record<string, string> = {
  // Store / iOS icon: full-bleed brick (the OS applies its own mask).
  'icon.svg': svg(`<rect width="1024" height="1024" fill="${colors.brick}"/>${bee(0.74, 0, 10)}${badge(760, 770, 92)}`),
  'android-icon-background.svg': svg(`<rect width="1024" height="1024" fill="${colors.brick}"/>`),
  // Adaptive foreground: everything inside the central ~60 % safe zone (survives circle/squircle masks).
  'android-icon-foreground.svg': svg(`${bee(0.62, 0, 6)}${badge(676, 690, 64)}`),
  'android-icon-monochrome.svg': svg(monoBee(0.62)),
  // Same monochrome as two plain layers, for renderers without SVG mask support (render-icons.py).
  '_mono-keep.svg': svg(monoLayers(0.62).keep),
  '_mono-cut.svg': svg(monoLayers(0.62).cut),
  // Splash: the bee alone at 66 % of the image, which AnimatedSplash reproduces exactly (132 of 200 dp).
  'splash-icon.svg': svg(bee(0.66)),
  'favicon.svg': svg(`<rect width="1024" height="1024" rx="230" fill="${colors.brick}"/>${bee(0.84, 0, 16)}`),
  // Mark only (for docs, web, press): transparent.
  'mauri-mark.svg': svg(bee(0.92)),
};

for (const [name, body] of Object.entries(files)) {
  writeFileSync(join(OUT, name), body);
  console.log('wrote', name, `${body.length} bytes`);
}
