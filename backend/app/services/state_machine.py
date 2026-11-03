"""The shared state machine (shared/state_machine.json) as the single source of truth."""

import json
from dataclasses import dataclass
from functools import lru_cache

from app.config import SHARED_DIR


class TransitionError(ValueError):
    pass


@dataclass(frozen=True)
class Transition:
    entity: str
    from_state: str
    to_state: str
    action: str
    actor: str


@lru_cache
def machine() -> dict:
    with open(SHARED_DIR / "state_machine.json", encoding="utf-8") as f:
        return json.load(f)


def locked_states() -> set[str]:
    """States at or after the lock (worker accepted), excluding terminal/dispute states."""
    card = machine()["card"]
    states = card["states"]
    start = states.index(card["locked_from"])
    end = states.index("passport_issued")
    return set(states[start : end + 1])


def find(entity: str, from_state: str, action: str, actor: str, to_state: str | None = None) -> Transition:
    spec = machine()[entity]
    for t in spec["transitions"]:
        if t["action"] != action:
            continue
        src = t["from"]
        if src == "*locked":
            if from_state not in locked_states():
                continue
        elif src != from_state:
            continue
        if to_state is not None and t["to"] not in (to_state, "*previous"):
            continue
        if t["actor"] not in (actor, "any_party") or (t["actor"] == "any_party" and actor not in ("client", "worker")):
            raise TransitionError(f"{actor} may not {action} a {entity} in state {from_state}")
        return Transition(entity, from_state, to_state or t["to"], action, actor)
    raise TransitionError(f"no '{action}' from '{from_state}' for {entity}")


def is_valid(entity: str, from_state: str, action: str, actor: str, to_state: str | None = None) -> bool:
    try:
        find(entity, from_state, action, actor, to_state)
        return True
    except TransitionError:
        return False
