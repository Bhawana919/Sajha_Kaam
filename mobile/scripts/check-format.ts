// Quick self-check for numerals and money formatting (run: npx tsx scripts/check-format.ts).
import assert from 'node:assert/strict';

import { localDigits, money } from '../src/lib/format';

assert.equal(localDigits('Closes in 2 hours', 'ne', 'devanagari'), 'Closes in २ hours');
assert.equal(localDigits('शुल्क: $0, कुल USD 40.50', 'ne', 'devanagari'), 'शुल्क: $0, कुल USD 40.50');
assert.equal(localDigits('12/15', 'ne', 'devanagari'), '१२/१५');
assert.equal(localDigits('12/15', 'ne', 'latin'), '12/15');
assert.equal(localDigits('12/15', 'en', 'devanagari'), '12/15');
assert.equal(money(4000, 'USD'), '$40');
assert.equal(money(4050, 'USD'), '$40.50');
console.log('✓ format: numerals and money');
