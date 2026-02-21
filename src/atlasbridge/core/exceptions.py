"""Aegis exception hierarchy."""

from __future__ import annotations


class AegisError(Exception):
    """Base exception for all Aegis errors."""


class ConfigError(AegisError):
    """Raised when the configuration is invalid or cannot be read."""


class ConfigNotFoundError(ConfigError):
    """Raised when the configuration file does not exist."""


class ChannelError(AegisError):
    """Raised when a notification channel fails."""


class AdapterError(AegisError):
    """Raised when a tool adapter fails."""


class SessionError(AegisError):
    """Raised when session management fails."""
