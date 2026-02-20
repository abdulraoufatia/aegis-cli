# Aegis Setup Flow Design

**Version:** 0.1.0
**Status:** Design
**Last updated:** 2026-02-20

---

## Overview

The `aegis setup` command provides the first-run experience. It must be:
- **Easy**: completable in under 2 minutes with no prior knowledge
- **Safe**: validates everything before writing any state
- **Recoverable**: can be re-run safely (`--force` re-initializes)
- **Scriptable**: `--non-interactive` mode for CI/CD and automation

---

## Setup Flow Diagram

```
aegis setup
     │
     ▼
┌───────────────────────────────────────────────────────────────┐
│  1. Pre-flight checks                                         │
│     ✓ Python version                                          │
│     ✓ Required dependencies installed                         │
│     ✓ SQLite accessible                                       │
│     ✗ → exit 3 with install instructions                      │
└───────────────────────────────────────────────────────────────┘
     │
     ▼
┌───────────────────────────────────────────────────────────────┐
│  2. Check existing config                                     │
│     If ~/.aegis/config.toml exists:                           │
│       "Aegis is already configured. Use --force to re-run."   │
│       → exit 0 (unless --force)                               │
└───────────────────────────────────────────────────────────────┘
     │
     ▼
┌───────────────────────────────────────────────────────────────┐
│  3. Welcome banner                                            │
│     (skipped in --quiet or --non-interactive)                 │
└───────────────────────────────────────────────────────────────┘
     │
     ▼
┌───────────────────────────────────────────────────────────────┐
│  4. Collect Telegram bot token                                │
│     a. Check --telegram-token flag                            │
│     b. Check AEGIS_TELEGRAM_BOT_TOKEN env var                 │
│     c. Prompt user (interactive mode)                         │
│     d. Validate format: /^\d+:[A-Za-z0-9_-]{35,}$/           │
│     e. ✗ → error message + re-prompt (max 3 attempts)         │
└───────────────────────────────────────────────────────────────┘
     │
     ▼
┌───────────────────────────────────────────────────────────────┐
│  5. Collect allowed user IDs                                  │
│     a. Check --allowed-users flag                             │
│     b. Check AEGIS_TELEGRAM_ALLOWED_USERS env var             │
│     c. Prompt user (interactive mode)                         │
│     d. Validate: comma-separated integers                     │
│     e. ✗ → error + re-prompt                                  │
└───────────────────────────────────────────────────────────────┘
     │
     ▼
┌───────────────────────────────────────────────────────────────┐
│  6. Test Telegram connectivity                                │
│     a. GET https://api.telegram.org/bot{token}/getMe          │
│     b. ✓ → show bot username                                  │
│     c. ✗ network error → exit 4                               │
│     d. ✗ 401 Unauthorized → token invalid, re-prompt         │
└───────────────────────────────────────────────────────────────┘
     │
     ▼
┌───────────────────────────────────────────────────────────────┐
│  7. Send test Telegram message                                │
│     a. POST sendMessage to each allowed user ID               │
│     b. "✅ Aegis is connecting. This is a test message."       │
│     c. Prompt user: "Did you receive it? [Y/n]"               │
│        (skipped in --non-interactive)                         │
│     d. ✗ user says no → troubleshooting tips                  │
└───────────────────────────────────────────────────────────────┘
     │
     ▼
┌───────────────────────────────────────────────────────────────┐
│  8. Select default policy                                     │
│     a. Show options: Strict | Balanced | Custom               │
│     b. Write selected policy to ~/.aegis/policy.toml          │
│     (skipped in --non-interactive; defaults to Strict)        │
└───────────────────────────────────────────────────────────────┘
     │
     ▼
┌───────────────────────────────────────────────────────────────┐
│  9. Write configuration                                       │
│     a. Create ~/.aegis/ directory (0700)                      │
│     b. Write ~/.aegis/config.toml (0600)                      │
│     c. Initialize ~/.aegis/aegis.db (WAL mode)                │
│     d. Run schema migrations                                  │
│     e. Write ~/.aegis/policy.toml (0600)                      │
└───────────────────────────────────────────────────────────────┘
     │
     ▼
┌───────────────────────────────────────────────────────────────┐
│  10. Post-setup doctor check                                  │
│      Run lightweight doctor (skip Telegram re-test)           │
│      ✗ any fail → warn but don't block (setup still complete) │
└───────────────────────────────────────────────────────────────┘
     │
     ▼
┌───────────────────────────────────────────────────────────────┐
│  11. Success output                                           │
│      Show summary and next steps                              │
│      exit 0                                                   │
└───────────────────────────────────────────────────────────────┘
```

---

## Config Directory Structure Created by Setup

```
~/.aegis/                       (0700 — dir owner-only)
├── config.toml                 (0600 — owner read/write only)
├── policy.toml                 (0600)
├── aegis.db                    (0600)
├── aegis.log                   (0600, created on first start)
├── aegis.pid                   (0600, created on start)
└── audit.log                   (0600, created on first start)
```

---

## Config File Written by Setup

```toml
# ~/.aegis/config.toml
# Generated by: aegis setup
# Date: 2026-02-20T19:00:00Z
# DO NOT commit this file — it contains your bot token.

[telegram]
bot_token = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz_12345678"
allowed_users = [123456789]

[approvals]
timeout_seconds = 300
default_action = "deny"

[policy]
path = "~/.aegis/policy.toml"

[daemon]
port = 39000

[logging]
level = "INFO"
format = "text"

[database]
path = "~/.aegis/aegis.db"
```

---

## Policy Files Written by Setup

### Strict Policy (default)

```toml
# ~/.aegis/policy.toml — Strict preset
[policy]
default_action = "require_approval"

[[policy.rules]]
name = "block-secret-reads"
match = { tool = "read_file", path_pattern = ".*\\.env.*|.*\\.pem|.*\\.key|.*credentials.*|.*secret.*|\\.ssh/.*|\\.aws/.*" }
action = "deny"
priority = 5

[[policy.rules]]
name = "block-aegis-config"
match = { path_pattern = ".*\\.aegis/.*" }
action = "deny"
priority = 1

[[policy.rules]]
name = "block-force-push"
match = { tool = "bash", command_pattern = "git push.*(--force|-f)" }
action = "deny"
priority = 5

[[policy.rules]]
name = "block-rm-rf"
match = { tool = "bash", command_pattern = "rm\\s+-[a-zA-Z]*r" }
action = "require_approval"
priority = 10

[[policy.rules]]
name = "allow-safe-reads"
match = { tool = "read_file" }
action = "allow"
priority = 80
```

### Balanced Policy

```toml
# ~/.aegis/policy.toml — Balanced preset
[policy]
default_action = "require_approval"

[[policy.rules]]
name = "block-secret-reads"
match = { tool = "read_file", path_pattern = ".*\\.env.*|.*\\.pem|.*\\.key|.*credentials.*" }
action = "deny"
priority = 5

[[policy.rules]]
name = "allow-reads"
match = { tool = "read_file" }
action = "allow"
priority = 80

[[policy.rules]]
name = "allow-safe-list-commands"
match = { tool = "bash", command_pattern = "^(ls|cat|head|tail|grep|find|echo|pwd)\\s" }
action = "allow"
priority = 70
```

---

## Non-Interactive Mode

Used in CI/CD pipelines, Docker images, or remote provisioning:

```bash
aegis setup \
  --non-interactive \
  --telegram-token "$AEGIS_TELEGRAM_BOT_TOKEN" \
  --allowed-users "$AEGIS_TELEGRAM_ALLOWED_USERS" \
  --policy strict \
  --json
```

In non-interactive mode:
- No prompts
- No confirmation of test message
- Test message is still sent (unless `--skip-test`)
- Exits 0 on success, appropriate error code on failure
- JSON output only (on success and error)

---

## Re-run Behavior (`--force`)

When `--force` is passed and config already exists:

```
⚠️  Aegis is already configured. Re-running setup will:
    - Overwrite ~/.aegis/config.toml
    - Overwrite ~/.aegis/policy.toml
    - The database and audit log will NOT be modified.

Continue? [y/N]: █
```

---

## Error Scenarios and Recovery

| Error | Exit Code | User Action |
|-------|-----------|-------------|
| Python < 3.11 | 3 | Upgrade Python |
| Missing dependency | 7 | `pip install aegis-cli` |
| Invalid bot token format | 2 | Get correct token from @BotFather |
| Token invalid (API 401) | 2 | Re-create bot via @BotFather |
| Telegram unreachable | 4 | Check internet; retry |
| User reports no test message | 4 | Check user ID (must be numeric); check bot can message users |
| Cannot create ~/.aegis/ | 5 | Check disk space and home dir permissions |
| Setup aborted by user | 1 | Run `aegis setup` again |

---

## Idempotency

`aegis setup` is idempotent when run with `--force`:
- Re-running creates a new config but does NOT wipe the database
- All previous approval history is preserved
- New bot token takes effect on next `aegis start`
