// The app's on-phone verifier must accept what the backend signs and reject any change
// (run: npx tsx scripts/check-verify.ts; the sample comes from backend/scripts/export_fixtures.py).
import assert from 'node:assert/strict';

import { canonical, fromBase64, verifyCredential } from '../src/lib/proof';
import fixtures from '../src/mocks/fixtures.json';

const { credential, signature_b64, key_id, keys } = fixtures.proof_sample;

assert.equal(Buffer.from(fromBase64('aGVsbG8=')).toString(), 'hello');
assert.equal(canonical({ b: 1, a: [true, null, 'दसैं'] }), '{"a":[true,null,"दसैं"],"b":1}');
assert.ok(verifyCredential(credential, signature_b64, key_id, keys), 'backend-signed sample should verify');

const changed = JSON.parse(JSON.stringify(credential));
changed.credentialSubject.onTime = false;
assert.ok(!verifyCredential(changed, signature_b64, key_id, keys), 'a changed record must fail');
assert.ok(!verifyCredential(credential, signature_b64, 'unknown-key', keys), 'unknown key must fail');
console.log('✓ verify: on-phone Ed25519 check matches the backend signer');
