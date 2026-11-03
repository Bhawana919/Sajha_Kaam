"""Bilingual skill search over config/skills.yaml (en, ne and aliases)."""

from app.config import load_yaml


def skills() -> list[dict]:
    return load_yaml("skills.yaml")["skills"]


def match_skill_ids(query: str) -> set[str]:
    q = query.strip().lower()
    if not q:
        return set()
    hits = set()
    for s in skills():
        terms = [s["en"].lower(), s["ne"], s["id"].replace("_", " "), *[a.lower() for a in s.get("aliases", [])]]
        if any(q in t or t in q for t in terms):
            hits.add(s["id"])
    return hits
