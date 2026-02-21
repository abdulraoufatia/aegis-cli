# Non-Interactive Setup Guide

This guide covers headless, CI/CD, and Docker deployment of AtlasBridge using environment variables.

---

## Environment Variable Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `ATLASBRIDGE_TELEGRAM_BOT_TOKEN` | Telegram bot token from @BotFather | `123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi` |
| `ATLASBRIDGE_TELEGRAM_ALLOWED_USERS` | Comma-separated Telegram user IDs | `12345678,87654321` |
| `ATLASBRIDGE_SLACK_BOT_TOKEN` | Slack Bot User OAuth Token (`xoxb-*`) | `xoxb-111-222-AAABBBCCC` |
| `ATLASBRIDGE_SLACK_APP_TOKEN` | Slack App-Level Token (`xapp-*`) | `xapp-1-A111-222-BBBCCC` |
| `ATLASBRIDGE_SLACK_ALLOWED_USERS` | Comma-separated Slack user IDs | `U1234567890,U9876543210` |
| `ATLASBRIDGE_LOG_LEVEL` | Log level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `ATLASBRIDGE_DB_PATH` | Custom database path | `/data/atlasbridge.db` |
| `ATLASBRIDGE_APPROVAL_TIMEOUT_SECONDS` | Prompt timeout (60-3600) | `300` |
| `ATLASBRIDGE_CONFIG` | Override config file path | `/etc/atlasbridge/config.toml` |

Legacy `AEGIS_*` prefixed variables are also supported as fallbacks.

---

## Quick Start

### `--from-env` (recommended for automation)

```bash
export ATLASBRIDGE_TELEGRAM_BOT_TOKEN="123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"
export ATLASBRIDGE_TELEGRAM_ALLOWED_USERS="12345678"
atlasbridge setup --from-env
```

This reads all `ATLASBRIDGE_*` env vars, validates them, and writes `config.toml` in one shot. Supports both Telegram and Slack simultaneously.

### `doctor --fix` (auto-repair)

```bash
atlasbridge doctor --fix
```

When env vars are set, `doctor --fix` generates a valid config file (not just a skeleton template). When no env vars are present, it creates a commented skeleton for manual editing.

---

## Docker Example

```dockerfile
FROM python:3.11-slim

RUN pip install atlasbridge

# Set at build time or pass at runtime
ENV ATLASBRIDGE_TELEGRAM_BOT_TOKEN=""
ENV ATLASBRIDGE_TELEGRAM_ALLOWED_USERS=""

# Generate config on container start
CMD atlasbridge setup --from-env && atlasbridge run claude
```

Run:

```bash
docker run \
  -e ATLASBRIDGE_TELEGRAM_BOT_TOKEN="123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi" \
  -e ATLASBRIDGE_TELEGRAM_ALLOWED_USERS="12345678" \
  my-atlasbridge-image
```

---

## GitHub Actions Example

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install AtlasBridge
        run: pip install atlasbridge

      - name: Configure AtlasBridge
        env:
          ATLASBRIDGE_TELEGRAM_BOT_TOKEN: ${{ secrets.ATLASBRIDGE_TELEGRAM_BOT_TOKEN }}
          ATLASBRIDGE_TELEGRAM_ALLOWED_USERS: ${{ secrets.ATLASBRIDGE_TELEGRAM_ALLOWED_USERS }}
        run: atlasbridge setup --from-env

      - name: Verify configuration
        run: atlasbridge config validate
```

---

## Slack Setup

```bash
export ATLASBRIDGE_SLACK_BOT_TOKEN="xoxb-111-222-AAABBBCCC"
export ATLASBRIDGE_SLACK_APP_TOKEN="xapp-1-A111-222-BBBCCC"
export ATLASBRIDGE_SLACK_ALLOWED_USERS="U1234567890"
atlasbridge setup --from-env
```

Requires `pip install "atlasbridge[slack]"` for the Slack SDK dependency.

---

## Multi-Channel Setup

Set env vars for both channels simultaneously:

```bash
export ATLASBRIDGE_TELEGRAM_BOT_TOKEN="123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"
export ATLASBRIDGE_TELEGRAM_ALLOWED_USERS="12345678"
export ATLASBRIDGE_SLACK_BOT_TOKEN="xoxb-111-222-AAABBBCCC"
export ATLASBRIDGE_SLACK_APP_TOKEN="xapp-1-A111-222-BBBCCC"
export ATLASBRIDGE_SLACK_ALLOWED_USERS="U1234567890"
atlasbridge setup --from-env
```

AtlasBridge will configure both channels and broadcast prompts to all of them.

---

## Optional: Keyring Secure Token Storage

AtlasBridge can store tokens in your OS keychain instead of the config file.

### Install

```bash
pip install "atlasbridge[keyring]"
```

### How it works

When the keyring extra is installed and a supported backend is available (macOS Keychain, Linux Secret Service), tokens are stored in the OS keychain. The config file contains a placeholder like `keyring:atlasbridge:telegram_bot_token` instead of the actual secret.

- **macOS**: Uses Keychain Access automatically
- **Linux**: Requires a Secret Service provider (GNOME Keyring, KDE Wallet)
- **Headless/CI**: Keyring is not available — tokens stay in the TOML file (secured with `0600` permissions)

### Verify

```bash
atlasbridge config show          # shows masked tokens
atlasbridge config show --no-redact  # shows full tokens (resolved from keyring)
```

---

## Config Management Commands

```bash
atlasbridge config show              # display config (secrets redacted)
atlasbridge config show --json       # JSON output
atlasbridge config show --no-redact  # show full secrets
atlasbridge config validate          # validate config against schema
atlasbridge config migrate           # migrate old config to latest version
atlasbridge config migrate --dry-run # preview migration without writing
```

---

## Config Versioning

AtlasBridge configs include a `config_version` field (currently version 1). Configs from older versions are automatically migrated on load. You can also trigger migration explicitly:

```bash
atlasbridge config migrate
```

---

## Legacy Migration

If you previously used Aegis (the old name), AtlasBridge automatically migrates `~/.aegis/config.toml` on first run. Legacy `AEGIS_*` environment variables are also supported as fallbacks.
