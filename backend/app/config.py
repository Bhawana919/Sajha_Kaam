"""Settings from environment variables, plus paths to the shared config files."""

import os
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
SHARED_DIR = ROOT / "shared"


def _flag(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).lower() in {"1", "true", "yes"}


class Settings:
    def __init__(self) -> None:
        self.database_url = os.environ.get("DATABASE_URL", f"sqlite:///{ROOT / 'backend' / 'sajha_kaam.db'}")
        self.demo_mode = _flag("DEMO_MODE", "1")
        self.llm_provider = os.environ.get("LLM_PROVIDER", "none")  # "anthropic" | "none"
        self.llm_api_key = os.environ.get("LLM_API_KEY")
        self.llm_model = os.environ.get("LLM_MODEL", "claude-haiku-5-5")
        self.llm_timeout_s = float(os.environ.get("LLM_TIMEOUT_S", "8"))
        self.jwt_secret = os.environ.get("JWT_SECRET", "dev-only-secret-change-me-before-any-real-deploy")
        self.signing_seed_b64 = os.environ.get("SIGNING_SEED_B64")
        # Unset: links use the address the request came in on (works on a LAN with no setup).
        self.public_base_url = os.environ.get("PUBLIC_BASE_URL")
        self.admin_demo_password = os.environ.get("ADMIN_DEMO_PASSWORD", "sajha-admin-demo")


@lru_cache
def settings() -> Settings:
    return Settings()


@lru_cache
def load_yaml(name: str) -> dict:
    with open(CONFIG_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)
