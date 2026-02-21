"""Aegis constants: filesystem layout, timeouts, and limits."""

from __future__ import annotations

from enum import IntEnum

# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------


class ExitCode(IntEnum):
    SUCCESS = 0
    ERROR = 1
    CONFIG_ERROR = 2
    ENV_ERROR = 3
    NETWORK_ERROR = 4
    PERMISSION_ERROR = 5
    DEPENDENCY_MISSING = 7


# ---------------------------------------------------------------------------
# Filesystem layout
# ---------------------------------------------------------------------------

AEGIS_DIR_NAME = ".aegis"
CONFIG_FILENAME = "config.toml"
DB_FILENAME = "aegis.db"
AUDIT_FILENAME = "audit.log"
PID_FILENAME = "aegis.pid"
LOG_FILENAME = "aegis.log"

# ---------------------------------------------------------------------------
# Timeouts and limits
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT_SECONDS = 300  # 5 minutes — prompt TTL
DEFAULT_REMINDER_SECONDS: int | None = None  # reminder before TTL (None = disabled)
STUCK_TIMEOUT_SECONDS = 5.0  # silence threshold for Signal 3
MAX_BUFFER_BYTES = 4096  # rolling PTY output buffer
ECHO_SUPPRESS_MS = 500  # ms to suppress detection after injection
DEFAULT_DETECTION_THRESHOLD = 0.65  # confidence threshold for routing

# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

DEFAULT_TELEGRAM_POLL_TIMEOUT = 30  # long-poll timeout (seconds)
DEFAULT_TELEGRAM_MAX_RETRIES = 5
