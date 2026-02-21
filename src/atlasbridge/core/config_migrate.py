"""Config schema migration: version detection and upgrade chain."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from atlasbridge.core.exceptions import ConfigError

CURRENT_CONFIG_VERSION = 1

# Registry of migration functions: from_version -> callable(dict) -> dict
_MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {}


def _register(from_ver: int) -> Callable[..., Any]:
    """Decorator to register a migration step."""

    def decorator(
        fn: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> Callable[[dict[str, Any]], dict[str, Any]]:
        _MIGRATIONS[from_ver] = fn
        return fn

    return decorator


@_register(0)
def _migrate_v0_to_v1(data: dict[str, Any]) -> dict[str, Any]:
    """v0 -> v1: stamp config_version field.

    v0 configs (all configs written before this feature) have no
    config_version key.  This migration simply adds the field.
    Future migrations (v1->v2, etc.) will handle structural changes.
    """
    data["config_version"] = 1
    return data


def detect_version(data: dict[str, Any]) -> int:
    """Return the config_version from *data*, defaulting to 0 if absent."""
    return int(data.get("config_version", 0))


def upgrade_config(data: dict[str, Any], from_version: int, to_version: int) -> dict[str, Any]:
    """Apply sequential migration steps from *from_version* to *to_version*.

    Raises :class:`ConfigError` if any step in the chain is missing or
    a downgrade is attempted.
    """
    if from_version == to_version:
        return data
    if from_version > to_version:
        raise ConfigError(f"Cannot downgrade config from v{from_version} to v{to_version}")

    current = from_version
    while current < to_version:
        migrator = _MIGRATIONS.get(current)
        if migrator is None:
            raise ConfigError(f"No migration path from config v{current} to v{current + 1}")
        data = migrator(data)
        current += 1

    return data
