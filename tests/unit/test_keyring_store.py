"""Unit tests for optional keyring integration."""

from __future__ import annotations

from atlasbridge.core.keyring_store import (
    KEYRING_PREFIX,
    SERVICE_NAME,
    is_keyring_placeholder,
    retrieve_token,
    store_token,
)


class TestIsKeyringPlaceholder:
    def test_valid_placeholder(self):
        assert is_keyring_placeholder("keyring:atlasbridge:telegram_bot_token")

    def test_plain_token(self):
        assert not is_keyring_placeholder("123456789:ABC...")

    def test_empty_string(self):
        assert not is_keyring_placeholder("")

    def test_prefix_only(self):
        assert is_keyring_placeholder("keyring:")


class TestStoreAndRetrieve:
    def test_round_trip_mocked(self, monkeypatch):
        """Mock keyring to verify store/retrieve round-trip."""
        import sys
        import types

        store: dict = {}
        mock_keyring = types.ModuleType("keyring")
        mock_keyring.set_password = lambda svc, key, val: store.update({f"{svc}:{key}": val})  # type: ignore[attr-defined]
        mock_keyring.get_password = lambda svc, key: store.get(f"{svc}:{key}")  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "keyring", mock_keyring)

        placeholder = store_token("telegram_bot_token", "secret123")
        assert placeholder == f"{KEYRING_PREFIX}{SERVICE_NAME}:telegram_bot_token"

        resolved = retrieve_token(placeholder)
        assert resolved == "secret123"

    def test_retrieve_nonexistent_returns_none(self, monkeypatch):
        """Retrieving a nonexistent key returns None."""
        import sys
        import types

        mock_keyring = types.ModuleType("keyring")
        mock_keyring.get_password = lambda svc, key: None  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "keyring", mock_keyring)

        result = retrieve_token("keyring:atlasbridge:nonexistent")
        assert result is None

    def test_retrieve_non_placeholder_returns_none(self):
        result = retrieve_token("not-a-keyring-placeholder")
        assert result is None


class TestConstants:
    def test_service_name(self):
        assert SERVICE_NAME == "atlasbridge"

    def test_prefix(self):
        assert KEYRING_PREFIX == "keyring:"
