"""Write mobile/src/mocks/fixtures.json from real API responses against a fresh seeded DB.

Mock mode (EXPO_PUBLIC_USE_MOCK=1) serves these, so mocks always match the contract.
"""

import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["DATABASE_URL"] = f"sqlite:///{Path(tempfile.mkdtemp()) / 'fixtures.db'}"
os.environ["DEMO_MODE"] = "1"
os.environ["LLM_PROVIDER"] = "none"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

DRAFT_EXAMPLES = ["५ वटा दसैं पोस्ट चाहियो", "I need 3 reels for my momo truck, $75, 4 days"]

with TestClient(app) as c:
    board = c.get("/v1/board").json()
    fixtures = {
        # Mock mode shifts window times by (now - generated_at) so "closes in 2 h" stays true.
        "generated_at": datetime.now(UTC).isoformat(),
        "skills": c.get("/v1/skills").json(),
        "board": board,
        "cards": {item["id"]: c.get(f"/v1/cards/{item['id']}").json() for item in board["items"]},
        "drafts": {text: c.post("/v1/cards/draft", json={"text": text}).json() for text in DRAFT_EXAMPLES},
    }

    # A real signed claim, so the app's on-phone verifier is tested against the backend's signer.
    from app.services import signing  # noqa: E402

    sample = {"title": "verification sample"}
    credential = {"@context": ["https://www.w3.org/ns/credentials/v2"], "type": ["VerifiableCredential"],
                  "credentialSubject": {"displayName": "अञ्जली (sample)", "summary": {"en": "5 posts", "ne": "५ वटा पोस्ट"},
                                        "onTime": True}, "issuer": signing.ISSUER, "sample": sample}
    sig, kid = signing.sign(credential)
    fixtures["proof_sample"] = {"credential": credential, "signature_b64": sig, "key_id": kid,
                                "keys": signing.keyset()["keys"]}

out = ROOT.parent / "mobile" / "src" / "mocks" / "fixtures.json"
out.write_text(json.dumps(fixtures, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"wrote {out}")
