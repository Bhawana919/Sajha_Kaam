// Render assets/brand/*.svg to the PNGs app.json uses, with a local Edge/Chrome (playwright-core).
// Run: node scripts/render-icons.mjs [path-to-playwright-core]   (after npx tsx scripts/make-icons.ts)
// Linux/macOS without Edge: python scripts/render-icons.py (cairosvg).
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const assets = join(here, '..', 'assets');
const require = createRequire(import.meta.url);
const { chromium } = require(process.argv[2] ?? 'playwright-core');

const jobs = [
  ['icon.svg', 'icon.png', 1024, false],
  ['android-icon-foreground.svg', 'android-icon-foreground.png', 1024, true],
  ['android-icon-background.svg', 'android-icon-background.png', 1024, false],
  ['android-icon-monochrome.svg', 'android-icon-monochrome.png', 1024, true],
  ['splash-icon.svg', 'splash-icon.png', 1024, true],
  ['favicon.svg', 'favicon.png', 196, true], // browsers scale it down; tiny viewports fail to render
];

const browser = await chromium.launch({ channel: 'msedge', headless: true });
const page = await browser.newPage({ deviceScaleFactor: 1 });
for (const [src, out, size, transparent] of jobs) {
  const svg = readFileSync(join(assets, 'brand', src), 'utf8').replace(/width="\d+" height="\d+"/, `width="${size}" height="${size}"`);
  await page.setViewportSize({ width: size, height: size });
  await page.setContent(`<html><body style="margin:0;background:transparent">${svg}</body></html>`);
  await page.locator('svg').screenshot({ path: join(assets, out), omitBackground: transparent });
  console.log('rendered', out, size);
}
await browser.close();
