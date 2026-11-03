// Bilingual checks (must pass in CI):
//  (a) en.json and ne.json have identical keys
//  (b) no empty values
//  (c) every ne.json value contains Devanagari, except allow-listed keys
//  (d) the same {{variables}} appear in both languages
// `--write-review` also regenerates docs/NEPALI_REVIEW.md, keeping ticks for unchanged strings.
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const root = join(__dirname, '..');
const en = JSON.parse(readFileSync(join(root, 'src/i18n/en.json'), 'utf8'));
const ne = JSON.parse(readFileSync(join(root, 'src/i18n/ne.json'), 'utf8'));

// Keys whose Nepali value may legitimately have no Devanagari (language names shown in their own script).
const LATIN_OK = new Set(['lang.en']);

type Flat = Record<string, string>;
function flatten(obj: Record<string, unknown>, prefix = ''): Flat {
  const out: Flat = {};
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === 'object') Object.assign(out, flatten(v as Record<string, unknown>, key));
    else out[key] = String(v);
  }
  return out;
}

const fe = flatten(en);
const fn = flatten(ne);
const errors: string[] = [];
const vars = (s: string) => [...s.matchAll(/{{\s*(\w+)[^}]*}}/g)].map((m) => m[1]).sort().join(',');

for (const k of Object.keys(fe)) if (!(k in fn)) errors.push(`missing in ne.json: ${k}`);
for (const k of Object.keys(fn)) if (!(k in fe)) errors.push(`missing in en.json: ${k}`);
for (const [k, v] of Object.entries(fe)) if (!v.trim()) errors.push(`empty in en.json: ${k}`);
for (const [k, v] of Object.entries(fn)) {
  if (!v.trim()) errors.push(`empty in ne.json: ${k}`);
  else if (!LATIN_OK.has(k) && !/[ऀ-ॿ]/.test(v)) errors.push(`no Devanagari in ne.json: ${k} = "${v}"`);
  if (k in fe && vars(v) !== vars(fe[k])) errors.push(`variables differ for ${k}: en[${vars(fe[k])}] ne[${vars(v)}]`);
}

if (process.argv.includes('--write-review')) {
  const reviewPath = join(root, '..', 'docs', 'NEPALI_REVIEW.md');
  const ticked = new Map<string, string>();
  if (existsSync(reviewPath)) {
    for (const line of readFileSync(reviewPath, 'utf8').split('\n')) {
      const m = line.match(/^\| \[x\] \| `([^`]+)` \| (.*) \| .* \|$/);
      if (m) ticked.set(m[1], m[2]);
    }
  }
  const esc = (s: string) => s.replace(/\|/g, '\\|');
  const rows = Object.keys(fn).map((k) => {
    const neText = esc(fn[k]);
    const ok = ticked.get(k) === neText;
    return `| ${ok ? '[x]' : '[ ]'} | \`${k}\` | ${neText} | ${esc(fe[k] ?? '')} |`;
  });
  const done = rows.filter((r) => r.startsWith('| [x]')).length;
  writeFileSync(
    reviewPath,
    [
      '# Nepali review',
      '',
      'Every Nepali string in the app. A native speaker on the team ticks `[x]` after checking it reads as natural, simple Nepali (not Hindi) and keeps checklist items observable.',
      'Regenerate with `npm run i18n:review` (in `mobile/`). Ticks are kept only while the Nepali text is unchanged; an edited string returns to "needs review".',
      '',
      `Reviewed: ${done} of ${rows.length}`,
      '',
      '| OK | Key | नेपाली | English |',
      '|---|---|---|---|',
      ...rows,
      '',
    ].join('\n'),
    'utf8',
  );
  console.log(`wrote ${reviewPath} (${done}/${rows.length} reviewed)`);
}

if (errors.length) {
  console.error(errors.map((e) => `✗ ${e}`).join('\n'));
  process.exit(1);
}
console.log(`✓ i18n: ${Object.keys(fe).length} keys, parity, no empties, Devanagari present, variables match`);
