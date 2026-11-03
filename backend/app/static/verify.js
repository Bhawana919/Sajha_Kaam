// "Don't trust us, verify us": checks run in the viewer's own browser, not on our server.
// canonical() must match the backend: json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False).
(function (global) {
  'use strict';

  function canonical(v) {
    if (v === null || typeof v !== 'object') return JSON.stringify(v);
    if (Array.isArray(v)) return '[' + v.map(canonical).join(',') + ']';
    return '{' + Object.keys(v).sort().map(function (k) { return JSON.stringify(k) + ':' + canonical(v[k]); }).join(',') + '}';
  }

  function utf8(s) { return new TextEncoder().encode(s); }

  function hex(bytes) {
    return Array.prototype.map.call(bytes, function (b) { return ('0' + b.toString(16)).slice(-2); }).join('');
  }

  // Pure-JS SHA-256 for pages opened over plain http on a LAN (crypto.subtle needs https or localhost).
  var K = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,
    0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,
    0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,
    0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,
    0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
  function sha256Sync(msg) {
    var h = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
    var l = msg.length, withPad = ((l + 9 + 63) >> 6) << 6, m = new Uint8Array(withPad);
    m.set(msg); m[l] = 0x80;
    var bits = l * 8, dv = new DataView(m.buffer);
    dv.setUint32(withPad - 4, bits >>> 0); dv.setUint32(withPad - 8, Math.floor(bits / 0x100000000));
    var w = new Uint32Array(64);
    for (var off = 0; off < withPad; off += 64) {
      for (var i = 0; i < 16; i++) w[i] = dv.getUint32(off + i * 4);
      for (i = 16; i < 64; i++) {
        var a = w[i - 15], b = w[i - 2];
        var s0 = ((a >>> 7) | (a << 25)) ^ ((a >>> 18) | (a << 14)) ^ (a >>> 3);
        var s1 = ((b >>> 17) | (b << 15)) ^ ((b >>> 19) | (b << 13)) ^ (b >>> 10);
        w[i] = (w[i - 16] + s0 + w[i - 7] + s1) | 0;
      }
      var A = h[0], B = h[1], C = h[2], D = h[3], E = h[4], F = h[5], G = h[6], H = h[7];
      for (i = 0; i < 64; i++) {
        var S1 = ((E >>> 6) | (E << 26)) ^ ((E >>> 11) | (E << 21)) ^ ((E >>> 25) | (E << 7));
        var t1 = (H + S1 + ((E & F) ^ (~E & G)) + K[i] + w[i]) | 0;
        var S0 = ((A >>> 2) | (A << 30)) ^ ((A >>> 13) | (A << 19)) ^ ((A >>> 22) | (A << 10));
        var t2 = (S0 + ((A & B) ^ (A & C) ^ (B & C))) | 0;
        H = G; G = F; F = E; E = (D + t1) | 0; D = C; C = B; B = A; A = (t1 + t2) | 0;
      }
      h[0] = (h[0] + A) | 0; h[1] = (h[1] + B) | 0; h[2] = (h[2] + C) | 0; h[3] = (h[3] + D) | 0;
      h[4] = (h[4] + E) | 0; h[5] = (h[5] + F) | 0; h[6] = (h[6] + G) | 0; h[7] = (h[7] + H) | 0;
    }
    var out = new Uint8Array(32), odv = new DataView(out.buffer);
    for (i = 0; i < 8; i++) odv.setUint32(i * 4, h[i] >>> 0);
    return out;
  }

  function sha256Hex(text) {
    var bytes = utf8(text);
    if (global.crypto && global.crypto.subtle) {
      return global.crypto.subtle.digest('SHA-256', bytes).then(function (d) { return hex(new Uint8Array(d)); });
    }
    return Promise.resolve(hex(sha256Sync(bytes)));
  }

  function b64(s) {
    var bin = atob(s), out = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }

  /** Recompute the audit chain. Resolves to the seq of the first broken event, or null. */
  function verifyChain(events) {
    var prev = '0'.repeat(64), i = 0;
    function step() {
      if (i >= events.length) return Promise.resolve(null);
      var e = events[i];
      return sha256Hex(prev + canonical(e.body)).then(function (h) {
        if (e.prev_hash !== prev || h !== e.hash) return e.body.seq;
        prev = e.hash; i++;
        return step();
      });
    }
    return step();
  }

  /** Ed25519 check of a credential's canonical JSON (tweetnacl, public domain). */
  function verifySignature(credential, signatureB64, publicKeyB64) {
    try {
      return global.nacl.sign.detached.verify(utf8(canonical(credential)), b64(signatureB64), b64(publicKeyB64));
    } catch (err) {
      return false;
    }
  }

  global.SajhaVerify = { canonical: canonical, sha256Hex: sha256Hex, sha256Sync: sha256Sync, hex: hex,
    verifyChain: verifyChain, verifySignature: verifySignature };
})(this);
