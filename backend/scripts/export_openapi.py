"""Write shared/openapi.json so the app can generate TS types (npm run api:types)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import SHARED_DIR  # noqa: E402
from app.main import app  # noqa: E402

out = SHARED_DIR / "openapi.json"
out.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"wrote {out}")
