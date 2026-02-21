"""Unit tests for aegis.core.prompt.state — PromptStateMachine transitions."""

from __future__ import annotations

from datetime import UTC

import pytest

from aegis.core.prompt.models import Confidence, PromptEvent, PromptStatus, PromptType
from aegis.core.prompt.state import TERMINAL_STATES, VALID_TRANSITIONS, PromptStateMachine


def _event(ttl_seconds: int = 300) -> PromptEvent:
    return PromptEvent.create(
        session_id="test-session",
        prompt_type=PromptType.TYPE_YES_NO,
        confidence=Confidence.HIGH,
        excerpt="Continue?",
        ttl_seconds=ttl_seconds,
    )


def _machine(ttl_seconds: int = 300) -> PromptStateMachine:
    return PromptStateMachine(event=_event(ttl_seconds=ttl_seconds))


# ---------------------------------------------------------------------------
# Valid transitions
# ---------------------------------------------------------------------------


class TestValidTransitions:
    def test_initial_state_is_created(self) -> None:
        sm = _machine()
        assert sm.status == PromptStatus.CREATED

    def test_created_to_routed(self) -> None:
        sm = _machine()
        sm.transition(PromptStatus.ROUTED)
        assert sm.status == PromptStatus.ROUTED

    def test_routed_to_awaiting_reply(self) -> None:
        sm = _machine()
        sm.transition(PromptStatus.ROUTED)
        sm.transition(PromptStatus.AWAITING_REPLY)
        assert sm.status == PromptStatus.AWAITING_REPLY

    def test_awaiting_to_reply_received(self) -> None:
        sm = _machine()
        sm.transition(PromptStatus.ROUTED)
        sm.transition(PromptStatus.AWAITING_REPLY)
        sm.transition(PromptStatus.REPLY_RECEIVED)
        assert sm.status == PromptStatus.REPLY_RECEIVED

    def test_reply_received_to_injected(self) -> None:
        sm = _machine()
        sm.transition(PromptStatus.ROUTED)
        sm.transition(PromptStatus.AWAITING_REPLY)
        sm.transition(PromptStatus.REPLY_RECEIVED)
        sm.transition(PromptStatus.INJECTED)
        assert sm.status == PromptStatus.INJECTED

    def test_injected_to_resolved(self) -> None:
        sm = _machine()
        sm.transition(PromptStatus.ROUTED)
        sm.transition(PromptStatus.AWAITING_REPLY)
        sm.transition(PromptStatus.REPLY_RECEIVED)
        sm.transition(PromptStatus.INJECTED)
        sm.transition(PromptStatus.RESOLVED)
        assert sm.status == PromptStatus.RESOLVED
        assert sm.is_terminal

    def test_awaiting_to_expired(self) -> None:
        sm = _machine()
        sm.transition(PromptStatus.ROUTED)
        sm.transition(PromptStatus.AWAITING_REPLY)
        sm.transition(PromptStatus.EXPIRED, "TTL elapsed")
        assert sm.status == PromptStatus.EXPIRED
        assert sm.is_terminal

    def test_created_to_canceled(self) -> None:
        sm = _machine()
        sm.transition(PromptStatus.CANCELED)
        assert sm.status == PromptStatus.CANCELED
        assert sm.is_terminal

    def test_created_to_failed(self) -> None:
        sm = _machine()
        sm.transition(PromptStatus.FAILED)
        assert sm.status == PromptStatus.FAILED
        assert sm.is_terminal


# ---------------------------------------------------------------------------
# Invalid transitions
# ---------------------------------------------------------------------------


class TestInvalidTransitions:
    def test_created_to_resolved_invalid(self) -> None:
        sm = _machine()
        with pytest.raises(ValueError, match="Invalid transition"):
            sm.transition(PromptStatus.RESOLVED)

    def test_resolved_to_anything_invalid(self) -> None:
        sm = _machine()
        sm.transition(PromptStatus.ROUTED)
        sm.transition(PromptStatus.AWAITING_REPLY)
        sm.transition(PromptStatus.REPLY_RECEIVED)
        sm.transition(PromptStatus.INJECTED)
        sm.transition(PromptStatus.RESOLVED)
        # Terminal — no outgoing transitions
        with pytest.raises(ValueError):
            sm.transition(PromptStatus.FAILED)

    def test_terminal_set_is_correct(self) -> None:
        expected = {
            PromptStatus.RESOLVED,
            PromptStatus.EXPIRED,
            PromptStatus.CANCELED,
            PromptStatus.FAILED,
        }
        assert TERMINAL_STATES == expected


# ---------------------------------------------------------------------------
# TTL expiry
# ---------------------------------------------------------------------------


class TestTTLExpiry:
    def test_not_expired_fresh_prompt(self) -> None:
        sm = _machine(ttl_seconds=300)
        assert not sm.is_expired

    def test_expired_past_ttl(self) -> None:
        sm = _machine(ttl_seconds=1)
        # Manually push expires_at into the past
        from datetime import datetime, timedelta

        sm.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        assert sm.is_expired

    def test_expire_if_due_transitions(self) -> None:
        sm = _machine()
        sm.transition(PromptStatus.ROUTED)
        sm.transition(PromptStatus.AWAITING_REPLY)
        from datetime import datetime, timedelta

        sm.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        expired = sm.expire_if_due()
        assert expired
        assert sm.status == PromptStatus.EXPIRED

    def test_expire_if_due_does_not_fire_if_not_overdue(self) -> None:
        sm = _machine(ttl_seconds=300)
        sm.transition(PromptStatus.ROUTED)
        sm.transition(PromptStatus.AWAITING_REPLY)
        expired = sm.expire_if_due()
        assert not expired
        assert sm.status == PromptStatus.AWAITING_REPLY

    def test_expire_if_due_does_not_fire_if_already_terminal(self) -> None:
        sm = _machine()
        sm.transition(PromptStatus.CANCELED)
        from datetime import datetime, timedelta

        sm.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        expired = sm.expire_if_due()
        assert not expired
        assert sm.status == PromptStatus.CANCELED


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


class TestHistory:
    def test_history_records_transitions(self) -> None:
        sm = _machine()
        sm.transition(PromptStatus.ROUTED, "dispatching")
        sm.transition(PromptStatus.AWAITING_REPLY, "delivered")
        assert len(sm.history) == 2
        assert sm.history[0][0] == PromptStatus.ROUTED

    def test_on_transition_callback_called(self) -> None:
        calls = []

        def cb(old, new):
            calls.append((old, new))

        sm = PromptStateMachine(event=_event(), on_transition=cb)
        sm.transition(PromptStatus.ROUTED)
        sm.transition(PromptStatus.AWAITING_REPLY)
        assert len(calls) == 2
        assert calls[0] == (PromptStatus.CREATED, PromptStatus.ROUTED)


# ---------------------------------------------------------------------------
# VALID_TRANSITIONS completeness
# ---------------------------------------------------------------------------


class TestValidTransitionsTable:
    def test_all_statuses_have_entries(self) -> None:
        all_statuses = set(PromptStatus)
        assert all(s in VALID_TRANSITIONS for s in all_statuses)

    def test_terminal_states_have_empty_transitions(self) -> None:
        for s in TERMINAL_STATES:
            assert VALID_TRANSITIONS[s] == set(), f"{s} should have no outgoing transitions"
