"""
aegis.core — Daemon lifecycle, configuration, event bus, and shared infrastructure.

Modules:
    daemon      Daemon start/stop/signal handling
    config      Configuration loading (TOML + env vars + flags)
    events      Internal event bus for tool call events
    exceptions  Aegis-specific exception hierarchy
    logging     structlog configuration
    constants   Exit codes, defaults, enumerations
"""
