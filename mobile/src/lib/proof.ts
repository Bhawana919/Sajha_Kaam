// On-phone checks for signed Work Passport records ("don't trust us, verify us").
// canonical() must match the backend: json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False).
import nacl from 'tweetnacl';

export type PublicKey = { key_id: string; alg: string; public_key_b64: string };

export function canonical(v: unknown): string {
  if (v === null || typeof v !== 'object') return JSON.stringify(v);
  if (Array.isArray(v)) return `[${v.map(canonical).join(',')}]`;
  const obj = v as Record<string, unknown>;
  return `{${Object.keys(obj).sort().map((k) => `${JSON.stringify(k)}:${canonical(obj[k])}`).join(',')}}`;
}

const B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';

/** Base64 to bytes without relying on atob (not on every JS engine). */
export function fromBase64(s: string): Uint8Array {
  const clean = s.replace(/[^A-Za-z0-9+/]/g, '');
  const out = new Uint8Array(Math.floor((clean.length * 3) / 4));
  let bits = 0;
  let value = 0;
  let i = 0;
  for (const ch of clean) {
    value = (value << 6) | B64.indexOf(ch);
    bits += 6;
    if (bits >= 8) {
      bits -= 8;
      out[i++] = (value >> bits) & 0xff;
    }
  }
  return out.slice(0, i);
}

export function verifyCredential(credential: unknown, signatureB64: string, keyId: string, keys: PublicKey[]): boolean {
  const key = keys.find((k) => k.key_id === keyId && k.alg === 'Ed25519');
  if (!key) return false;
  try {
    return nacl.sign.detached.verify(
      new TextEncoder().encode(canonical(credential)),
      fromBase64(signatureB64),
      fromBase64(key.public_key_b64),
    );
  } catch {
    return false;
  }
}
