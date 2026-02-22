"""Safety guard: BaseChannel ABC surface must not drift."""

from __future__ import annotations

import inspect

from atlasbridge.channels.base import BaseChannel, ChannelCircuitBreaker

# Frozen abstract method set for v0.9.0
FROZEN_ABSTRACT_METHODS = frozenset(
    {
        "start",
        "close",
        "send_prompt",
        "notify",
        "edit_prompt_message",
        "receive_replies",
        "is_allowed",
    }
)

FROZEN_OPTIONAL_METHODS = frozenset(
    {
        "healthcheck",
    }
)


def _get_abstract_methods(cls: type) -> set[str]:
    return {
        name
        for name, _ in inspect.getmembers(cls, predicate=inspect.isfunction)
        if getattr(getattr(cls, name), "__isabstractmethod__", False)
    }


def test_abstract_methods_frozen():
    """BaseChannel must have exactly the frozen set of abstract methods."""
    actual = _get_abstract_methods(BaseChannel)
    assert actual == FROZEN_ABSTRACT_METHODS, (
        f"BaseChannel abstract methods changed. "
        f"Expected: {sorted(FROZEN_ABSTRACT_METHODS)}, "
        f"Got: {sorted(actual)}. "
        f"Added: {sorted(actual - FROZEN_ABSTRACT_METHODS)}, "
        f"Removed: {sorted(FROZEN_ABSTRACT_METHODS - actual)}"
    )


def test_optional_methods_exist():
    """BaseChannel must have all frozen optional methods with defaults."""
    for method_name in FROZEN_OPTIONAL_METHODS:
        method = getattr(BaseChannel, method_name, None)
        assert method is not None, f"Optional method '{method_name}' missing from BaseChannel"
        assert not getattr(method, "__isabstractmethod__", False), (
            f"'{method_name}' was optional but is now abstract — this breaks existing channels"
        )


def test_circuit_breaker_exists():
    """ChannelCircuitBreaker must exist with expected interface."""
    cb = ChannelCircuitBreaker()
    assert hasattr(cb, "threshold")
    assert hasattr(cb, "recovery_seconds")
    assert hasattr(cb, "is_open")
    assert callable(getattr(cb, "record_success", None))
    assert callable(getattr(cb, "record_failure", None))
    assert callable(getattr(cb, "reset", None))


def test_circuit_breaker_defaults():
    """ChannelCircuitBreaker default parameters must not drift."""
    cb = ChannelCircuitBreaker()
    assert cb.threshold == 3, f"Circuit breaker threshold changed: {cb.threshold}"
    assert cb.recovery_seconds == 30.0, (
        f"Circuit breaker recovery_seconds changed: {cb.recovery_seconds}"
    )


def test_send_prompt_signature():
    """send_prompt() must accept (self, event) and return str."""
    sig = inspect.signature(BaseChannel.send_prompt)
    params = list(sig.parameters.keys())
    assert params == ["self", "event"], f"send_prompt signature changed: {params}"


def test_notify_signature():
    """notify() must accept (self, message, session_id)."""
    sig = inspect.signature(BaseChannel.notify)
    params = list(sig.parameters.keys())
    assert params == ["self", "message", "session_id"], f"notify signature changed: {params}"


def test_interface_version_accessible():
    """BaseChannel.INTERFACE_VERSION must be a semver string."""
    import re

    version = BaseChannel.INTERFACE_VERSION
    assert isinstance(version, str), f"INTERFACE_VERSION is not a string: {type(version)}"
    assert re.match(r"^\d+\.\d+\.\d+$", version), (
        f"INTERFACE_VERSION is not valid semver: {version!r}"
    )


def test_guarded_send_exists():
    """BaseChannel must have guarded_send (circuit-breaker wrapper)."""
    method = getattr(BaseChannel, "guarded_send", None)
    assert method is not None, "guarded_send missing from BaseChannel"
    assert not getattr(method, "__isabstractmethod__", False), (
        "guarded_send must not be abstract — it has a default implementation"
    )
