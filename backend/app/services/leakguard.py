"""Leak Guard: finds details that could identify an applicant (deterministic, no AI).

Runs on Devanagari-normalised text, so '९८१२३४५६७८' is caught like '9812345678'.
It cannot read names inside images (OCR is P2); images are re-encoded to strip EXIF.
"""

import io
import re
from dataclasses import asdict, dataclass

from PIL import Image

from app.services.i18n import normalise_digits

_PATTERNS = [
    ("phone", re.compile(r"(?:\+?977[\s-]?)?\b9[678]\d{8}\b|\+\d[\d\s-]{7,}\d")),
    ("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("url", re.compile(r"(?:https?://|www\.)\S+|\b[\w-]+\.(?:com|np|org|net|io|me|co)\b(?:/\S*)?", re.I)),
    ("handle", re.compile(r"(?<![\w@])@[A-Za-z0-9_.]{2,}")),
]
# Asking to move off-platform or for photos, in messages (shown as a warning to the sender).
_OFF_PLATFORM = re.compile(r"whatsapp|viber|imo\b|messenger|telegram|ह्वाट्सएप|भाइबर|send (?:me )?(?:a )?(?:photo|picture|selfie)|फोटो पठाउ", re.I)


@dataclass
class Finding:
    kind: str  # phone | email | url | handle | name | off_platform
    start: int
    end: int
    text: str


def scan(text: str, name_tokens: list[str] | None = None) -> list[Finding]:
    norm = normalise_digits(text)  # same length as text: digit-for-digit swap
    found: list[Finding] = []
    for kind, pattern in _PATTERNS:
        for m in pattern.finditer(norm):
            if kind == "url" and "@" in m.group():
                continue
            found.append(Finding(kind, m.start(), m.end(), text[m.start():m.end()]))
    for token in name_tokens or []:
        if len(token) < 2:
            continue
        boundary = r"(?<![\wऀ-ॿ]){}(?![\wऀ-ॿ])"
        for m in re.finditer(boundary.format(re.escape(token)), text, re.I):
            found.append(Finding("name", m.start(), m.end(), m.group()))
    found.sort(key=lambda f: f.start)
    merged: list[Finding] = []
    for f in found:  # drop overlaps (e.g. an email also matching url)
        if merged and f.start < merged[-1].end:
            continue
        merged.append(f)
    return merged


def scan_message(text: str) -> list[str]:
    kinds = {f.kind for f in scan(text) if f.kind in ("phone", "email")}
    if _OFF_PLATFORM.search(text):
        kinds.add("off_platform")
    return sorted(kinds)


def redact(text: str, findings: list[Finding]) -> str:
    out, last = [], 0
    for f in findings:
        out.append(text[last:f.start])
        out.append("▇▇▇")
        last = f.end
    out.append(text[last:])
    return "".join(out)


def to_json(findings: list[Finding]) -> list[dict]:
    return [asdict(f) for f in findings]


def strip_exif(data: bytes, max_side: int = 1280) -> bytes:
    """Re-encode the pixels only (drops EXIF/GPS), downscaled for low-end phones."""
    with Image.open(io.BytesIO(data)) as img:
        img = img.convert("RGB")
        img.thumbnail((max_side, max_side))
        clean = Image.new("RGB", img.size)
        clean.paste(img)
        out = io.BytesIO()
        clean.save(out, format="JPEG", quality=80)
        return out.getvalue()
