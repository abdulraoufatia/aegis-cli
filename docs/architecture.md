# Aegis Architecture Design

**Version:** 0.1.0
**Status:** Design
**Last updated:** 2026-02-20

---

## Overview

Aegis is a local-first, CLI-native security layer. It operates as a lightweight daemon that wraps AI coding agents, intercepts their tool calls, evaluates them against a policy engine, and routes high-risk operations to an approval channel (Telegram MVP, WhatsApp Phase 3).

### Core Design Constraints

- **Local-first**: No data leaves the machine except approval notifications to Telegram
- **No cloud dependency**: SQLite for state, no external DB required
- **Fail-safe**: Default action on any error is `deny`
- **Vendor-neutral**: Works with any AI CLI tool
- **Single binary**: `pip install aegis-cli` installs everything

---

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User's Machine                              │
│                                                                     │
│  ┌──────────────┐    PTY/pipe    ┌─────────────────────────────┐   │
│  │  AI Agent    │◄──────────────►│      Aegis Daemon           │   │
│  │ (claude CLI) │    tool calls  │                             │   │
│  └──────────────┘                │  ┌─────────┐  ┌──────────┐ │   │
│                                  │  │ Bridge  │  │  Policy  │ │   │
│  ┌──────────────┐                │  │ Layer   │─►│  Engine  │ │   │
│  │   User CLI   │◄──────────────►│  └─────────┘  └──────────┘ │   │
│  │ (aegis wrap) │   Unix socket  │       │              │       │   │
│  └──────────────┘                │       ▼              ▼       │   │
│                                  │  ┌─────────┐  ┌──────────┐ │   │
│                                  │  │  Store  │  │  Agents  │ │   │
│                                  │  │(SQLite) │  │ Pipeline │ │   │
│                                  │  └─────────┘  └──────────┘ │   │
│                                  │       │              │       │   │
│                                  │       ▼              ▼       │   │
│                                  │  ┌─────────┐  ┌──────────┐ │   │
│                                  │  │  Audit  │  │ Channels │ │   │
│                                  │  │   Log   │  │(Telegram)│ │   │
│                                  │  └─────────┘  └──────────┘ │   │
│                                  └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                              │
                                    HTTPS (Telegram API)
                                              │
                                    ┌─────────────────┐
                                    │   User's Phone   │
                                    │    (Telegram)    │
                                    └─────────────────┘
```

---

## Module Structure

```
aegis/
├── __init__.py
├── cli/                    # CLI entry point
│   ├── __init__.py
│   ├── main.py             # Click application root
│   ├── commands/           # One file per command
│   │   ├── setup.py
│   │   ├── start.py
│   │   ├── stop.py
│   │   ├── wrap.py
│   │   ├── status.py
│   │   ├── approvals.py
│   │   ├── logs.py
│   │   ├── doctor.py
│   │   ├── config_cmd.py
│   │   └── version.py
│   └── output.py           # Formatters (text, JSON, rich)
│
├── core/                   # Daemon and core infrastructure
│   ├── __init__.py
│   ├── daemon.py           # Daemon lifecycle (start/stop/signal handling)
│   ├── config.py           # Config loading (TOML + env vars)
│   ├── events.py           # Event bus (tool call events)
│   ├── exceptions.py       # Aegis-specific exceptions
│   ├── logging.py          # structlog configuration
│   └── constants.py        # Exit codes, defaults
│
├── policy/                 # Policy engine
│   ├── __init__.py
│   ├── engine.py           # Rule evaluation loop
│   ├── loader.py           # TOML policy file parser
│   ├── models.py           # Policy rule data models
│   ├── risk.py             # Risk scoring
│   └── defaults.py         # Built-in default policy rules
│
├── bridge/                 # Tool interception adapters
│   ├── __init__.py
│   ├── base.py             # Abstract adapter interface
│   ├── pty_adapter.py      # PTY-based wrapper (primary)
│   ├── pipe_adapter.py     # Pipe-based wrapper (fallback)
│   └── interceptor.py      # Tool call event parser/router
│
├── store/                  # SQLite persistence
│   ├── __init__.py
│   ├── database.py         # Connection pool, migrations
│   ├── migrations/         # SQL migration files
│   │   ├── 001_initial.sql
│   │   └── 002_audit_log.sql
│   ├── repositories/
│   │   ├── approval_repo.py
│   │   ├── session_repo.py
│   │   └── audit_repo.py
│   └── models.py           # SQLAlchemy-free dataclasses
│
├── audit/                  # Append-only audit log
│   ├── __init__.py
│   ├── writer.py           # Append-only log writer
│   ├── reader.py           # Log reader and query
│   └── integrity.py        # Hash chain verification
│
├── agents/                 # Agentic pipeline
│   ├── __init__.py
│   ├── planner.py          # Decomposes tool calls into decisions
│   ├── policy_agent.py     # Applies policy rules
│   ├── execution_agent.py  # Executes approved tool calls
│   ├── observer.py         # Monitors and logs outcomes
│   └── critic.py           # Validates safety of decisions
│
└── channels/               # Approval routing channels
    ├── __init__.py
    ├── base.py             # Abstract channel interface
    └── telegram/
        ├── __init__.py
        ├── bot.py          # Long-polling Telegram bot
        ├── formatter.py    # Message formatting
        ├── handler.py      # Callback query handler
        └── auth.py         # User whitelist enforcement
```

---

## Approval Pipeline

The core pipeline processes every tool call event:

```
Tool Call Intercepted
         │
         ▼
   ┌───────────┐
   │  Planner  │  Decomposes compound tool calls
   └───────────┘
         │
         ▼
   ┌───────────┐
   │  Policy   │  Evaluates rules in priority order
   │  Agent    │
   └───────────┘
         │
    ┌────┴────┐
    │         │
  allow     deny    require_approval
    │         │           │
    ▼         ▼           ▼
 Execute    Block     Channel
            + log     Router
              │           │
              │           ▼
              │      ┌─────────┐
              │      │Telegram │
              │      │  Bot    │
              │      └─────────┘
              │           │
              │    ┌──────┴──────┐
              │    │             │
              │  approve       deny/timeout
              │    │             │
              ▼    ▼             ▼
           ┌──────────┐    ┌──────────┐
           │ Execute  │    │  Block   │
           │  Agent   │    │  + log   │
           └──────────┘    └──────────┘
                │                │
                ▼                ▼
           ┌──────────────────────────┐
           │       Observer           │
           │   (logs outcome,         │
           │    updates store,        │
           │    writes audit log)     │
           └──────────────────────────┘
                        │
                        ▼
           ┌──────────────────────────┐
           │       Critic             │
           │  (validates safety,      │
           │   flags anomalies)       │
           └──────────────────────────┘
```

---

## Agentic Design Patterns

### Routing

The agent pipeline routes events to different handlers:

| Event type | Handler |
|------------|---------|
| Tool call | Planner → Policy → Channel/Execute |
| Approval response | Approval handler → Execute/Block |
| Admin command (Telegram) | Admin handler |
| Help request (Telegram) | Help handler |
| Status request (Telegram) | Status handler |

### Parallelization

Safe concurrent tasks run in parallel:
- Multiple tool calls from the same agent session (if policy allows)
- Audit log writes (async, non-blocking)
- Telegram polling (independent of tool call processing)

Mutually exclusive:
- Approvals for the same tool call (only one decision wins)
- DB writes (serialized via SQLite WAL mode)

### Reflection (Critic Agent)

The Critic agent runs after each execution cycle:
- Validates that the policy decision was correct
- Checks for anomalous patterns (many denies, rapid-fire tool calls)
- Flags potential injection attempts (tool calls with unusual argument shapes)
- Logs warnings to audit log

### Memory (State Persistence)

Persistent state in SQLite:
- `sessions` — active AI agent sessions
- `approvals` — approval requests and decisions
- `audit_log` — append-only event log
- `policy_cache` — cached policy evaluation results (TTL: 60s)

---

## Daemon Architecture

The Aegis daemon is a single Python process using `asyncio`:

```python
async def main():
    config = load_config()
    db = await Database.connect(config.db_path)
    audit = AuditWriter(db)
    policy = PolicyEngine(config.policy_path)

    telegram = TelegramChannel(config.telegram)
    bridge = PTYAdapter(policy, telegram, audit)

    await asyncio.gather(
        telegram.start_polling(),
        bridge.start_listening(),
        run_expiry_loop(db),        # expire timed-out approvals
    )
```

**Signal handling:**
- `SIGTERM` — graceful shutdown: drain pending approvals (or deny on timeout), close DB, remove PID file
- `SIGINT` — same as SIGTERM
- `SIGHUP` — reload config without restart

---

## Configuration Model

```
~/.aegis/
├── config.toml       # Main configuration (0600)
├── policy.toml       # Policy rules (0600)
├── aegis.db          # SQLite database
├── aegis.log         # Daemon log (rotated)
├── aegis.pid         # Daemon PID file
└── audit.log         # Append-only audit log
```

Config is loaded in this priority order (highest to lowest):
1. CLI flags (e.g., `--telegram-token`)
2. Environment variables (e.g., `AEGIS_TELEGRAM_BOT_TOKEN`)
3. Config file (`~/.aegis/config.toml`)
4. Built-in defaults

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| CLI | [Click](https://click.palletsprojects.com/) 8.x |
| Terminal output | [Rich](https://rich.readthedocs.io/) |
| Config/validation | [Pydantic](https://docs.pydantic.dev/) 2.x + [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) |
| HTTP (Telegram) | [httpx](https://www.python-httpx.org/) async |
| Async runtime | [asyncio](https://docs.python.org/3/library/asyncio.html) (stdlib) |
| PTY wrapping | [ptyprocess](https://ptyprocess.readthedocs.io/) |
| Database | SQLite via [sqlite3](https://docs.python.org/3/library/sqlite3.html) (stdlib) |
| TOML | [tomllib](https://docs.python.org/3/library/tomllib.html) (stdlib, read) + [tomli-w](https://pypi.org/project/tomli-w/) (write) |
| Logging | [structlog](https://www.structlog.org/) |
| Process management | [psutil](https://psutil.readthedocs.io/) |
| Linting | [ruff](https://docs.astral.sh/ruff/) |
| Type checking | [mypy](https://mypy.readthedocs.io/) |
| Testing | [pytest](https://docs.pytest.org/) + [pytest-asyncio](https://pytest-asyncio.readthedocs.io/) |

**Rationale for no FastAPI:** The MVP requires no HTTP server. The daemon communicates via:
- Unix socket (local IPC between `aegis wrap` and daemon)
- Telegram long polling (outbound only)

FastAPI may be added in Phase 4 for a local REST API.

---

## Separation of Concerns

| Module | Responsibility | Does NOT do |
|--------|---------------|-------------|
| `cli/` | Parse args, format output, call services | Business logic |
| `core/` | Config, lifecycle, event bus | Policy, storage |
| `policy/` | Rule evaluation, risk scoring | I/O, storage |
| `bridge/` | Tool interception, PTY management | Policy, approval routing |
| `store/` | SQLite read/write | Business logic |
| `audit/` | Append-only log write/read | Other storage |
| `agents/` | Pipeline orchestration | Direct I/O |
| `channels/` | Telegram/WhatsApp messaging | Policy, business logic |

---

## Phased Architecture

### Phase 1 (v0.1.0) — Design
All design docs. No runnable code.

### Phase 2 (v0.2.0) — MVP
- `aegis setup`, `aegis start`, `aegis stop`, `aegis wrap`
- Policy engine with TOML rules
- SQLite store
- Telegram approval channel
- `aegis doctor`, `aegis status`, `aegis logs`
- Audit log

### Phase 3 (v0.3.0) — WhatsApp Adapter
- `channels/whatsapp/` implementing the base channel interface

### Phase 4 (v0.4.0) — Hardening
- Local REST API (FastAPI)
- Rate limiting
- Enhanced RBAC
- Pluggable secret backends

### Phase 5 (v1.0.0) — Stable
- Stable public API
- Plugin system for tool adapters
- Distribution on PyPI
