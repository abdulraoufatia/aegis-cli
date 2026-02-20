    # Aegis (AegisCLI)

> **A secure, vendor-neutral, open-source CLI firewall and approval layer for AI coding agents.**

[![CI](https://github.com/aegis-cli/aegis-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/aegis-cli/aegis-cli/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-0.1.0-green.svg)](CHANGELOG.md)

---

Aegis sits between you and your AI coding agent. Every destructive, sensitive, or high-risk operation — file deletion, git force-push, package installation, secret access — requires your explicit approval before it executes. Approvals are sent to you via Telegram (WhatsApp coming in Phase 3). You decide. Aegis enforces.

```
┌──────────────┐        ┌───────────────┐        ┌─────────────────┐
│  AI Agent    │──────► │     Aegis     │──────► │   Your Phone    │
│ (Claude CLI) │        │   Firewall    │        │   (Telegram)    │
│              │◄────── │   + Policy    │◄────── │                 │
└──────────────┘        └───────────────┘        └─────────────────┘
      executes                blocks /                approve /
      tool calls              intercepts              deny / timeout
```

---

## Table of Contents

- [Why Aegis?](#why-aegis)
- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Requirements](#requirements)
- [Installation](#installation)
- [Setting Up the Repository](#setting-up-the-repository)
- [Quick Start](#quick-start)
- [Commands Reference](#commands-reference)
- [Exit Codes](#exit-codes)
- [Configuration](#configuration)
- [Policy Engine](#policy-engine)
- [Security Model](#security-model)
- [Docs](#docs)
- [Development](#development)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [License](#license)

---

## Why Aegis?

AI coding agents are powerful — and that power is the problem. A single misbehaving prompt can:

- Delete your entire working tree
- Force-push over protected branches
- Leak secrets from `.env` files
- Install malicious packages
- Execute arbitrary shell commands

**Aegis makes every dangerous operation require a human decision.** It wraps your AI CLI, intercepts tool calls, evaluates them against a policy, and routes high-risk operations to your phone for approval — all without modifying the AI tool itself.

### What Aegis is NOT

- Not a proxy that reads your prompts
- Not a cloud service that sees your data
- Not a replacement for your AI CLI
- Not dependent on any paid API

Everything runs locally. Approval routing goes only to Telegram (your bot, your chat).

---

## Features

- **Universal wrapper** — works with Claude Code, OpenAI CLI, and any future tool
- **Telegram approval** — approve or deny from your phone in seconds
- **Policy engine** — TOML-based rules: allowlist, denylist, regex patterns, risk tiers
- **RBAC** — role-based access control per Telegram user
- **Append-only audit log** — every decision recorded, tamper-evident
- **Doctor command** — self-diagnostic with auto-fix
- **Local-first** — SQLite state, no cloud dependency
- **Zero token cost** — no Aegis API, no subscription
- **Open source** — MIT license, fully auditable

---

## Architecture Overview

```
aegis/
├── cli/        # Click-based CLI entry point and command handlers
├── core/       # Daemon, config, event bus, lifecycle management
├── policy/     # Policy engine, rule evaluation, risk scoring
├── bridge/     # Tool interception layer (wrapper / PTY adapters)
├── store/      # SQLite persistence, migrations, repositories
├── audit/      # Append-only audit log writer and reader
├── agents/     # Planner, Policy, Execution, Observer, Critic agents
└── channels/   # Telegram (MVP), WhatsApp (Phase 3) approval channels
```

**Approval pipeline:**

```
Tool Call Event
      │
      ▼
  Policy Engine ──► allowlisted? ──► Execute directly
      │
      ▼ (needs review)
  Channel Router
      │
      ▼
  Telegram Bot ──► User approves ──► Execute
                └─► User denies  ──► Block + log
                └─► Timeout      ──► Auto-deny + log
```

See [docs/architecture.md](docs/architecture.md) for full design.

---

## Requirements

- Python 3.11 or 3.12
- SQLite 3.35+ (included in Python standard library)
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- Your Telegram user ID (from [@userinfobot](https://t.me/userinfobot))
- The AI CLI tool you want to wrap (Claude Code, OpenAI CLI, etc.)

---

## Installation

### From PyPI (once published)

```bash
pip install aegis-cli
```

### From source

```bash
git clone https://github.com/aegis-cli/aegis-cli.git
cd aegis-cli
pip install -e ".[dev]"
```

### Verify installation

```bash
aegis version
aegis doctor
```

---

## Setting Up the Repository

If you are contributing or forking Aegis, follow these steps to set up the repository correctly.

### 1. Clone and initialize

```bash
git clone https://github.com/aegis-cli/aegis-cli.git
cd aegis-cli
git checkout -b main
```

### 2. Configure branch protection (GitHub)

Via GitHub UI → Settings → Branches → Add rule for `main`:

- [x] Require a pull request before merging
- [x] Require status checks to pass before merging
  - Required checks: `CI / Lint & Type Check`, `CI / Tests`, `CI / Security Scan`
- [x] Require branches to be up to date before merging
- [x] Require linear history
- [x] Do not allow bypassing the above settings
- [x] Restrict force pushes

### 3. Enable GitHub Actions

Actions are automatically enabled. The CI workflow runs on every PR targeting `main`.

### 4. Configure Dependabot

Already configured in `.github/dependabot.yml` — checks Python dependencies weekly.

### 5. Create your `.env`

```bash
cp .env.example .env
# Edit .env — fill in AEGIS_TELEGRAM_BOT_TOKEN and AEGIS_TELEGRAM_ALLOWED_USERS
```

### 6. Install development dependencies

```bash
pip install -e ".[dev]"
```

### 7. Run the test suite

```bash
pytest
```

### 8. Tag the design release

```bash
git tag -a v0.1.0 -m "chore: design release v0.1.0"
git push origin v0.1.0
```

---

## Quick Start

### 1. Set up Aegis

```bash
aegis setup
```

This interactive wizard:
- Creates `~/.aegis/` config directory
- Validates your Telegram bot token
- Sends a test message to confirm connectivity
- Writes `~/.aegis/config.toml`
- Creates the SQLite database
- Installs default policy

### 2. Start the Aegis daemon

```bash
aegis start
```

### 3. Wrap your AI CLI

```bash
# Instead of running this:
claude

# Run this:
aegis wrap claude
```

Aegis now intercepts all tool calls from Claude Code. Risky operations will pause and notify you on Telegram.

### 4. Check status

```bash
aegis status
```

### 5. View pending approvals

```bash
aegis approvals
```

---

## Commands Reference

### `aegis setup`

Interactive first-run wizard. Configures Aegis from scratch.

```
aegis setup [--non-interactive] [--telegram-token TOKEN] [--allowed-users IDS]
```

| Flag | Description |
|------|-------------|
| `--non-interactive` | Skip prompts; use flags and env vars |
| `--telegram-token` | Telegram bot token |
| `--allowed-users` | Comma-separated Telegram user IDs |
| `--config-path` | Custom config file path |
| `--json` | Output results as JSON |

---

### `aegis start`

Start the Aegis background daemon.

```
aegis start [--foreground] [--port PORT] [--log-level LEVEL]
```

| Flag | Description |
|------|-------------|
| `--foreground` | Run in foreground (don't daemonize) |
| `--port` | Override daemon port (default: 39000) |
| `--log-level` | DEBUG, INFO, WARNING, ERROR |

---

### `aegis stop`

Stop the running Aegis daemon.

```
aegis stop [--force] [--timeout SECONDS]
```

---

### `aegis wrap <tool>`

Wrap an AI CLI tool through the Aegis interception layer.

```
aegis wrap <tool> [tool-args...]
aegis wrap claude -- --no-cache
aegis wrap openai -- api chat.completions.create
```

| Flag | Description |
|------|-------------|
| `--dry-run` | Show what would be intercepted; don't execute |
| `--log-level` | Override log level for this session |
| `--timeout` | Approval timeout override (seconds) |

---

### `aegis status`

Show current daemon status and system health.

```
aegis status [--json] [--watch]
```

Output includes:
- Daemon running state and PID
- Telegram bot connectivity
- Pending approval count
- Recent activity summary
- Database size and health

---

### `aegis approvals`

Manage pending and historical approvals.

```
aegis approvals [list|show|approve|deny|history]
```

**Subcommands:**

```bash
aegis approvals list                    # List pending approvals
aegis approvals list --all              # Include resolved
aegis approvals show <id>               # Show approval detail
aegis approvals approve <id>            # Approve from CLI
aegis approvals deny <id> [--reason]    # Deny from CLI
aegis approvals history [--limit N]     # Show approval history
```

---

### `aegis logs`

View Aegis daemon and audit logs.

```
aegis logs [--follow] [--lines N] [--level LEVEL] [--json] [--since DATETIME]
```

| Flag | Description |
|------|-------------|
| `--follow` | Stream new log lines (like `tail -f`) |
| `--lines N` | Show last N lines (default: 50) |
| `--level` | Filter by log level |
| `--json` | Output as JSON Lines |
| `--since` | Show logs since timestamp |

---

### `aegis doctor`

Run system diagnostics.

```
aegis doctor [--fix] [--json] [--verbose]
```

| Flag | Description |
|------|-------------|
| `--fix` | Attempt safe automatic fixes |
| `--json` | Output as JSON |
| `--verbose` | Show details for passing checks too |

Checks performed:

**Environment:**
- Python version (3.11+)
- Required dependencies installed
- SQLite accessibility
- Config file existence and validity
- Telegram token format
- Telegram API connectivity
- CLI tool availability on PATH
- Subprocess execution permissions

**Security:**
- `.env` file not committed
- Config file permissions (should be 0600)
- No secrets in environment variables visible to child processes
- Audit log integrity

**Runtime:**
- Daemon running state
- Lock file validity
- Stuck or expired approvals
- Database schema version
- Disk space for DB

---

### `aegis config`

Read and write Aegis configuration.

```
aegis config get <key>
aegis config set <key> <value>
aegis config list
aegis config validate
aegis config path
```

---

### `aegis help`

```
aegis help
aegis help <command>
aegis --help
aegis <command> --help
```

---

### `aegis version`

```
aegis version
aegis version --json
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General / unhandled error |
| `2` | Configuration error |
| `3` | Environment error (Python version, missing deps) |
| `4` | Network error (Telegram unreachable) |
| `5` | Permission error (file permissions, access denied) |
| `6` | Security violation (policy block, unauthorized user) |
| `7` | Dependency missing |
| `8` | State corruption (DB, lock file, audit log) |

All error output goes to `stderr`. Exit codes are consistent across all commands.

---

## Configuration

Aegis configuration lives in `~/.aegis/config.toml`.

```toml
[telegram]
bot_token = "YOUR_BOT_TOKEN"   # or set AEGIS_TELEGRAM_BOT_TOKEN
allowed_users = [123456789]    # Telegram user IDs (whitelist)

[approvals]
timeout_seconds = 300          # Auto-deny after this many seconds
default_action = "deny"        # "deny" or "approve" on timeout

[policy]
path = "~/.aegis/policy.toml"  # Path to policy rules

[daemon]
port = 39000                   # Local daemon socket port

[logging]
level = "INFO"                 # DEBUG, INFO, WARNING, ERROR
format = "text"                # "text" or "json"

[database]
path = "~/.aegis/aegis.db"     # SQLite database path
```

Environment variables (prefixed `AEGIS_`) override config file values. See [.env.example](.env.example).

---

## Policy Engine

Policy lives in `~/.aegis/policy.toml`. Example:

```toml
[policy]
default_action = "require_approval"   # Fail-safe default

[[policy.rules]]
name = "allow-safe-reads"
match = { tool = "read_file", path_pattern = "^/home/.*" }
action = "allow"
priority = 100

[[policy.rules]]
name = "block-secret-reads"
match = { tool = "read_file", path_pattern = ".*\\.env.*|.*secret.*|.*credentials.*" }
action = "deny"
reason = "Secret file access blocked"
priority = 10

[[policy.rules]]
name = "require-approval-for-writes"
match = { tool = "write_file" }
action = "require_approval"
priority = 50

[[policy.rules]]
name = "block-force-push"
match = { tool = "bash", command_pattern = "git push.*--force|git push.*-f" }
action = "deny"
reason = "Force push to remote is prohibited"
priority = 5
```

See [docs/policy-engine.md](docs/policy-engine.md) for full policy reference.

---

## Security Model

- **Local-first**: No data leaves your machine except approval notifications to Telegram
- **Telegram whitelist**: Only your approved user IDs can respond to approvals
- **RBAC**: Roles (`admin`, `approver`, `viewer`) control what each Telegram user can do
- **Append-only audit log**: Every event is recorded; the log cannot be modified
- **Fail-safe defaults**: Unknown operations require approval; errors default to deny
- **No shell-from-phone**: Aegis never executes arbitrary commands from Telegram messages
- **Config protection**: Config files should be `0600`; doctor checks and warns

See [docs/threat-model.md](docs/threat-model.md) and [docs/red-team-report.md](docs/red-team-report.md) for full analysis.

See [SECURITY.md](SECURITY.md) for vulnerability disclosure.

---

## Docs

| Document | Description |
|----------|-------------|
| [docs/cli-ux.md](docs/cli-ux.md) | Full CLI UX design and command specification |
| [docs/architecture.md](docs/architecture.md) | System architecture and module design |
| [docs/threat-model.md](docs/threat-model.md) | STRIDE threat model |
| [docs/red-team-report.md](docs/red-team-report.md) | Red team attack analysis |
| [docs/tool-interception-design.md](docs/tool-interception-design.md) | Tool interception with sequence diagrams |
| [docs/policy-engine.md](docs/policy-engine.md) | Policy engine design and rule reference |
| [docs/data-model.md](docs/data-model.md) | Database schema and data model |
| [docs/approval-lifecycle.md](docs/approval-lifecycle.md) | Approval state machine |
| [docs/setup-flow.md](docs/setup-flow.md) | First-run setup flow design |
| [docs/tool-adapter.md](docs/tool-adapter.md) | Tool adapter abstraction design |

---

## Development

### Setup

```bash
git clone https://github.com/aegis-cli/aegis-cli.git
cd aegis-cli
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Running tests

```bash
pytest                          # All tests
pytest -v                       # Verbose
pytest --cov=aegis              # With coverage
pytest tests/unit/              # Unit tests only
pytest tests/integration/       # Integration tests only
```

### Linting and formatting

```bash
ruff check .                    # Lint
ruff format .                   # Format
mypy aegis/                     # Type check
bandit -r aegis/                # Security scan
```

### Branch conventions

| Branch prefix | Purpose |
|---------------|---------|
| `feature/` | New features |
| `fix/` | Bug fixes |
| `docs/` | Documentation only |
| `chore/` | Tooling, CI, deps |
| `security/` | Security patches |

### Commit conventions

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(policy): add regex path matching to rule engine
fix(telegram): handle rate limit with exponential backoff
docs(cli-ux): document aegis wrap subcommand flags
chore(ci): add Python 3.12 to test matrix
security(bridge): sanitize tool call arguments before logging
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines.

Short version:

1. Fork and clone
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Write code + tests
4. Ensure `pytest` and `ruff check .` pass
5. Open a PR against `main`
6. PR must pass CI before merge

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

---

## License

[MIT](LICENSE) — Copyright (c) 2026 Aegis Contributors
