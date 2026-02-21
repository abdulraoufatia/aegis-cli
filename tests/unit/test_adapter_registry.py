"""
Unit tests for the adapter registry and built-in adapter discovery.

Regression coverage for:
- Registry is non-empty in a clean import (no manual imports required)
- "claude" and "claude-code" both resolve to ClaudeCodeAdapter
- "openai", "gemini", "custom" are present
- Unknown adapter error includes available adapter ids
- `adapter list` CLI command output includes "claude"
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

# ---------------------------------------------------------------------------
# Registry bootstrap — importing atlasbridge.adapters fills the registry
# ---------------------------------------------------------------------------


class TestRegistryBootstrap:
    def test_registry_is_non_empty_after_package_import(self) -> None:
        """Importing atlasbridge.adapters must populate the registry."""
        import atlasbridge.adapters  # noqa: F401
        from atlasbridge.adapters.base import AdapterRegistry

        assert len(AdapterRegistry.list_all()) > 0, "Registry must not be empty"

    def test_claude_is_registered(self) -> None:
        """'claude' must be discoverable without manual module imports."""
        import atlasbridge.adapters  # noqa: F401
        from atlasbridge.adapters.base import AdapterRegistry

        assert "claude" in AdapterRegistry.list_all()

    def test_claude_code_alias_is_registered(self) -> None:
        """'claude-code' must resolve to the same adapter as 'claude'."""
        import atlasbridge.adapters  # noqa: F401
        from atlasbridge.adapters.base import AdapterRegistry

        assert "claude-code" in AdapterRegistry.list_all()

    def test_all_builtin_adapters_present(self) -> None:
        """All four built-in adapters must be registered."""
        import atlasbridge.adapters  # noqa: F401
        from atlasbridge.adapters.base import AdapterRegistry

        registered = AdapterRegistry.list_all()
        for expected in ("claude", "claude-code", "openai", "gemini", "custom"):
            assert expected in registered, f"Expected adapter {expected!r} to be registered"


# ---------------------------------------------------------------------------
# Adapter resolution
# ---------------------------------------------------------------------------


class TestAdapterResolution:
    def test_get_claude_returns_claude_code_adapter(self) -> None:
        """AdapterRegistry.get('claude') returns ClaudeCodeAdapter."""
        import atlasbridge.adapters  # noqa: F401
        from atlasbridge.adapters.base import AdapterRegistry
        from atlasbridge.adapters.claude_code import ClaudeCodeAdapter

        assert AdapterRegistry.get("claude") is ClaudeCodeAdapter

    def test_get_claude_code_alias_returns_same_class(self) -> None:
        """'claude-code' alias resolves to the same class as 'claude'."""
        import atlasbridge.adapters  # noqa: F401
        from atlasbridge.adapters.base import AdapterRegistry

        assert AdapterRegistry.get("claude-code") is AdapterRegistry.get("claude")

    def test_unknown_adapter_raises_key_error(self) -> None:
        """Unknown adapter name raises KeyError."""
        import atlasbridge.adapters  # noqa: F401
        from atlasbridge.adapters.base import AdapterRegistry

        with pytest.raises(KeyError):
            AdapterRegistry.get("nonexistent-tool-xyz")

    def test_unknown_adapter_error_includes_available(self) -> None:
        """KeyError message includes the list of registered adapters."""
        import atlasbridge.adapters  # noqa: F401
        from atlasbridge.adapters.base import AdapterRegistry

        with pytest.raises(KeyError, match="claude"):
            AdapterRegistry.get("nonexistent-tool-xyz")

    def test_unknown_adapter_error_mentions_unknown_name(self) -> None:
        """KeyError message includes the unknown name that was requested."""
        import atlasbridge.adapters  # noqa: F401
        from atlasbridge.adapters.base import AdapterRegistry

        with pytest.raises(KeyError, match="nonexistent-tool-xyz"):
            AdapterRegistry.get("nonexistent-tool-xyz")


# ---------------------------------------------------------------------------
# CLI: adapter list
# ---------------------------------------------------------------------------


class TestAdapterListCommand:
    def test_adapter_list_exits_zero(self) -> None:
        """atlasbridge adapter list exits with code 0."""
        from atlasbridge.cli.main import cli

        result = CliRunner().invoke(cli, ["adapter", "list"])
        assert result.exit_code == 0, result.output

    def test_adapter_list_contains_claude(self) -> None:
        """adapter list output includes the 'claude' adapter."""
        from atlasbridge.cli.main import cli

        result = CliRunner().invoke(cli, ["adapter", "list"])
        assert "claude" in result.output

    def test_adapter_list_json_includes_claude(self) -> None:
        """adapter list --json output includes claude entry."""
        from atlasbridge.cli.main import cli

        result = CliRunner().invoke(cli, ["adapter", "list", "--json"])
        assert result.exit_code == 0, result.output
        rows = json.loads(result.output)
        names = [r["name"] for r in rows]
        assert "claude" in names


# ---------------------------------------------------------------------------
# CLI: run — unknown adapter shows helpful error
# ---------------------------------------------------------------------------


class TestRunUnknownAdapter:
    def test_run_unknown_adapter_exits_nonzero(self) -> None:
        """atlasbridge run <unknown> exits non-zero without crashing."""
        from atlasbridge.cli.main import cli

        result = CliRunner().invoke(cli, ["run", "nonexistent-tool-xyz"])
        assert result.exit_code != 0

    def test_run_unknown_adapter_mentions_unknown_name(self) -> None:
        """Error output names the unknown tool."""
        from atlasbridge.cli.main import cli

        result = CliRunner().invoke(cli, ["run", "nonexistent-tool-xyz"])
        assert "nonexistent-tool-xyz" in result.output

    def test_run_unknown_adapter_lists_available(self) -> None:
        """Error output lists at least one available adapter."""
        from atlasbridge.cli.main import cli

        result = CliRunner().invoke(cli, ["run", "nonexistent-tool-xyz"])
        assert "claude" in result.output
