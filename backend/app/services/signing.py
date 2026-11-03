"""Ed25519 signing for Work Passport claims.

Each claim is a JSON credential *shaped like* a W3C Verifiable Credential (v2 context),
signed by Sajha Kaam over canonical JSON (sorted keys, no whitespace, UTF-8). The public key
is served at /.well-known/sajha-kaam-keys.json so anyone can check a claim on their own device.
Full DID/VC wallet interoperability is future work.

SIGNING_SEED_B64: a base64 32-byte seed, or any secret string (hashed to 32 bytes).
Unset (local dev): derived from JWT_SECRET, so signatures survive restarts of a local DB.
"""

import base64
import binascii
import hashlib
from functools import lru_cache

from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey

from app.config import settings
from app.models import PassportClaim
from app.services.audit import canonical

ISSUER = {"id": "urn:sajha-kaam:issuer", "name": "Sajha Kaam (demo)"}
CLAIM_TYPES = {
    "client_confirmed_delivery": "ClientConfirmedDelivery",
    "both_confirmed_payment": "BothConfirmedPayment",
    "practice_badge": "PracticeBadge",
}


def _seed() -> bytes:
    raw = settings().signing_seed_b64
    if raw:
        try:
            decoded = base64.b64decode(raw, validate=True)
            if len(decoded) == 32:
                return decoded
        except (binascii.Error, ValueError):
            pass
        return hashlib.sha256(raw.encode()).digest()
    return hashlib.sha256(f"sajha-dev-signing|{settings().jwt_secret}".encode()).digest()


@lru_cache
def signing_key() -> SigningKey:
    return SigningKey(_seed())


def public_key_b64() -> str:
    return base64.b64encode(bytes(signing_key().verify_key)).decode()


def key_id() -> str:
    return "sk-" + hashlib.sha256(bytes(signing_key().verify_key)).hexdigest()[:16]


def keyset() -> dict:
    return {"issuer": ISSUER, "keys": [{"key_id": key_id(), "alg": "Ed25519", "public_key_b64": public_key_b64()}]}


def credential_for(claim: PassportClaim, display_name: str, passport_slug: str) -> dict:
    """The signed body. Holds no email, district, phone, Khalti link or client identity."""
    return {
        "@context": ["https://www.w3.org/ns/credentials/v2"],
        "type": ["VerifiableCredential", "SajhaKaamWorkClaim"],
        "id": f"urn:sajha-kaam:claim:{claim.id}",
        "issuer": ISSUER,
        "validFrom": claim.issued_at.replace(tzinfo=None).isoformat(timespec="seconds") + "Z",
        "credentialSubject": {
            "id": f"urn:sajha-kaam:passport:{passport_slug}",
            "displayName": display_name,
            "claimType": CLAIM_TYPES.get(claim.type, claim.type),
            "skill": claim.skill,
            "summary": {"en": claim.summary_en, "ne": claim.summary_ne},
            "levelAtTime": claim.level_at_time,
            "onTime": claim.on_time,
            "source": claim.source_label,
        },
    }


def sign(credential: dict) -> tuple[str, str]:
    """Return (signature_b64, key_id) over canonical JSON of the credential."""
    sig = signing_key().sign(canonical(credential).encode()).signature
    return base64.b64encode(sig).decode(), key_id()


def verify(credential: dict, signature_b64: str, public_b64: str | None = None) -> bool:
    try:
        vk = VerifyKey(base64.b64decode(public_b64 or public_key_b64()))
        vk.verify(canonical(credential).encode(), base64.b64decode(signature_b64))
        return True
    except (BadSignatureError, ValueError, binascii.Error):
        return False
