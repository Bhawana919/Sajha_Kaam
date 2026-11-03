import pytest

from app.services.state_machine import TransitionError, find, is_valid, locked_states, machine


def test_every_transition_uses_known_states():
    for entity in ("card", "application"):
        spec = machine()[entity]
        states = set(spec["states"])
        for t in spec["transitions"]:
            assert t["from"] in states or t["from"].startswith("*"), t
            assert t["to"] in states or t["to"].startswith("*"), t


@pytest.mark.parametrize(
    "state,action,actor",
    [
        ("draft", "draft_with_ai", "client"),
        ("rules_passed", "post", "client"),
        ("pending_review", "approve", "admin"),
        ("in_review", "pick", "client"),
        ("revealed", "accept", "worker"),
        ("revealed", "decline", "worker"),
        ("in_progress", "deliver", "worker"),
        ("delivered", "confirm", "client"),
        ("client_confirmed", "client_paid", "client"),
        ("payment_handoff", "worker_received", "worker"),
    ],
)
def test_valid_transitions(state, action, actor):
    assert is_valid("card", state, action, actor)


@pytest.mark.parametrize(
    "state,action,actor",
    [
        ("open", "pick", "client"),  # cannot pick before the window closes
        ("revealed", "accept", "client"),  # only the worker accepts
        ("delivered", "confirm", "worker"),  # only the client confirms the work
        ("client_confirmed", "worker_received", "worker"),  # client must mark paid first
        ("payment_handoff", "worker_received", "client"),  # only the worker says money arrived
        ("pending_review", "approve", "client"),  # clients cannot approve their own card
        ("draft", "post", "client"),  # rules must pass first
    ],
)
def test_invalid_transitions(state, action, actor):
    assert not is_valid("card", state, action, actor)
    with pytest.raises(TransitionError):
        find("card", state, action, actor)


def test_cases_only_after_lock():
    assert "worker_accepted" in locked_states()
    assert "open" not in locked_states()
    assert is_valid("card", "in_progress", "open_case", "worker")
    assert is_valid("card", "delivered", "open_case", "client")
    assert not is_valid("card", "open", "open_case", "client")
    assert not is_valid("card", "in_progress", "open_case", "admin")


def test_application_withdraw_only_before_pick():
    assert is_valid("application", "submitted", "withdraw", "worker")
    assert not is_valid("application", "picked", "withdraw", "worker")
