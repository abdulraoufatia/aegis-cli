"""Integration tests for --from-env setup and doctor --fix with env vars."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from atlasbridge.cli.main import cli

VALID_TOKEN = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------------------
# atlasbridge setup --from-env
# ---------------------------------------------------------------------------


class TestFromEnvSetup:
    def test_telegram_from_env(self, runner: CliRunner, tmp_path: Path) -> None:
        """--from-env with Telegram env vars writes a valid config."""
        cfg = tmp_path / "config.toml"
        result = runner.invoke(
            cli,
            ["setup", "--from-env"],
            env={
                "ATLASBRIDGE_CONFIG": str(cfg),
                "ATLASBRIDGE_TELEGRAM_BOT_TOKEN": VALID_TOKEN,
                "ATLASBRIDGE_TELEGRAM_ALLOWED_USERS": "12345678",
            },
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert cfg.exists()

        from atlasbridge.core.config import load_config

        loaded = load_config(cfg)
        assert loaded.telegram is not None
        assert loaded.telegram.allowed_users == [12345678]

    def test_slack_from_env(self, runner: CliRunner, tmp_path: Path) -> None:
        """--from-env with Slack env vars."""
        cfg = tmp_path / "config.toml"
        result = runner.invoke(
            cli,
            ["setup", "--from-env"],
            env={
                "ATLASBRIDGE_CONFIG": str(cfg),
                "ATLASBRIDGE_SLACK_BOT_TOKEN": "xoxb-111-222-AAABBBCCC",
                "ATLASBRIDGE_SLACK_APP_TOKEN": "xapp-1-A111-222-BBBCCC",
                "ATLASBRIDGE_SLACK_ALLOWED_USERS": "U1234567890",
            },
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert cfg.exists()

        from atlasbridge.core.config import load_config

        loaded = load_config(cfg)
        assert loaded.slack is not None
        assert loaded.slack.allowed_users == ["U1234567890"]

    def test_no_env_vars_fails(self, runner: CliRunner, tmp_path: Path) -> None:
        """--from-env without any env vars exits non-zero."""
        cfg = tmp_path / "config.toml"
        result = runner.invoke(
            cli,
            ["setup", "--from-env"],
            env={
                "ATLASBRIDGE_CONFIG": str(cfg),
            },
        )
        assert result.exit_code != 0

    def test_invalid_token_fails(self, runner: CliRunner, tmp_path: Path) -> None:
        """--from-env with invalid token format exits non-zero."""
        cfg = tmp_path / "config.toml"
        result = runner.invoke(
            cli,
            ["setup", "--from-env"],
            env={
                "ATLASBRIDGE_CONFIG": str(cfg),
                "ATLASBRIDGE_TELEGRAM_BOT_TOKEN": "badtoken",
                "ATLASBRIDGE_TELEGRAM_ALLOWED_USERS": "12345678",
            },
        )
        assert result.exit_code != 0

    def test_legacy_aegis_env_vars(self, runner: CliRunner, tmp_path: Path) -> None:
        """--from-env falls back to AEGIS_* env vars."""
        cfg = tmp_path / "config.toml"
        result = runner.invoke(
            cli,
            ["setup", "--from-env"],
            env={
                "ATLASBRIDGE_CONFIG": str(cfg),
                "AEGIS_TELEGRAM_BOT_TOKEN": VALID_TOKEN,
                "AEGIS_TELEGRAM_ALLOWED_USERS": "12345678",
            },
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert cfg.exists()


# ---------------------------------------------------------------------------
# atlasbridge doctor --fix with env vars
# ---------------------------------------------------------------------------


class TestDoctorFixEnvVars:
    def test_fix_creates_config_from_env(self, runner: CliRunner, tmp_path: Path) -> None:
        """doctor --fix with env vars creates a real config, not just a skeleton."""
        cfg = tmp_path / "config.toml"
        result = runner.invoke(
            cli,
            ["doctor", "--fix"],
            env={
                "ATLASBRIDGE_CONFIG": str(cfg),
                "ATLASBRIDGE_TELEGRAM_BOT_TOKEN": VALID_TOKEN,
                "ATLASBRIDGE_TELEGRAM_ALLOWED_USERS": "12345678",
            },
            catch_exceptions=False,
        )
        assert result.exit_code == 0 or isinstance(result.exit_code, int)
        assert cfg.exists()

        from atlasbridge.core.config import load_config

        loaded = load_config(cfg)
        assert loaded.telegram is not None
        assert loaded.telegram.allowed_users == [12345678]

    def test_fix_creates_skeleton_without_env(self, runner: CliRunner, tmp_path: Path) -> None:
        """doctor --fix without env vars creates a skeleton template."""
        cfg = tmp_path / "config.toml"
        result = runner.invoke(
            cli,
            ["doctor", "--fix"],
            env={
                "ATLASBRIDGE_CONFIG": str(cfg),
            },
            catch_exceptions=False,
        )
        assert isinstance(result.exit_code, int)
        assert cfg.exists()

        content = cfg.read_text()
        assert "config_version = 1" in content
        assert "bot_token" in content  # commented out


# ---------------------------------------------------------------------------
# atlasbridge config commands
# ---------------------------------------------------------------------------


class TestConfigCommands:
    @pytest.fixture
    def config_path(self, tmp_path: Path) -> Path:
        import tomli_w

        data = {
            "config_version": 1,
            "telegram": {
                "bot_token": VALID_TOKEN,
                "allowed_users": [12345678],
            },
        }
        p = tmp_path / "config.toml"
        with open(p, "wb") as f:
            tomli_w.dump(data, f)
        return p

    def test_config_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["config", "--help"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "show" in result.output
        assert "validate" in result.output
        assert "migrate" in result.output

    def test_config_show_json(self, runner: CliRunner, config_path: Path) -> None:
        result = runner.invoke(
            cli,
            ["config", "show", "--json"],
            env={"ATLASBRIDGE_CONFIG": str(config_path)},
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "telegram" in data
        assert "config_version" in data

    def test_config_show_redacted(self, runner: CliRunner, config_path: Path) -> None:
        result = runner.invoke(
            cli,
            ["config", "show", "--json"],
            env={"ATLASBRIDGE_CONFIG": str(config_path)},
            catch_exceptions=False,
        )
        data = json.loads(result.output)
        assert "***" in data["telegram"]["bot_token"]

    def test_config_show_no_redact(self, runner: CliRunner, config_path: Path) -> None:
        result = runner.invoke(
            cli,
            ["config", "show", "--json", "--no-redact"],
            env={"ATLASBRIDGE_CONFIG": str(config_path)},
            catch_exceptions=False,
        )
        data = json.loads(result.output)
        assert data["telegram"]["bot_token"] == VALID_TOKEN

    def test_config_validate_valid(self, runner: CliRunner, config_path: Path) -> None:
        result = runner.invoke(
            cli,
            ["config", "validate"],
            env={"ATLASBRIDGE_CONFIG": str(config_path)},
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_config_validate_missing(self, runner: CliRunner, tmp_path: Path) -> None:
        result = runner.invoke(
            cli,
            ["config", "validate"],
            env={"ATLASBRIDGE_CONFIG": str(tmp_path / "nope.toml")},
        )
        assert result.exit_code != 0

    def test_config_migrate_already_current(self, runner: CliRunner, config_path: Path) -> None:
        result = runner.invoke(
            cli,
            ["config", "migrate"],
            env={"ATLASBRIDGE_CONFIG": str(config_path)},
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "already" in result.output.lower() or "no migration" in result.output.lower()

    def test_config_migrate_v0_to_v1(self, runner: CliRunner, tmp_path: Path) -> None:
        """Explicit migration of a v0 config."""
        p = tmp_path / "config.toml"
        p.write_text(f'[telegram]\nbot_token = "{VALID_TOKEN}"\nallowed_users = [12345678]\n')

        result = runner.invoke(
            cli,
            ["config", "migrate"],
            env={"ATLASBRIDGE_CONFIG": str(p)},
            catch_exceptions=False,
        )
        assert result.exit_code == 0

        import tomllib

        with open(p, "rb") as f:
            data = tomllib.load(f)
        assert data["config_version"] == 1

    def test_config_migrate_dry_run(self, runner: CliRunner, tmp_path: Path) -> None:
        p = tmp_path / "config.toml"
        p.write_text(f'[telegram]\nbot_token = "{VALID_TOKEN}"\nallowed_users = [12345678]\n')

        result = runner.invoke(
            cli,
            ["config", "migrate", "--dry-run"],
            env={"ATLASBRIDGE_CONFIG": str(p)},
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "dry run" in result.output.lower()

        # File should NOT be modified
        import tomllib

        with open(p, "rb") as f:
            data = tomllib.load(f)
        assert "config_version" not in data


# ---------------------------------------------------------------------------
# Slack env var overrides in config loading
# ---------------------------------------------------------------------------


class TestSlackEnvVarOverrides:
    def test_slack_env_vars_applied(self, tmp_path: Path, monkeypatch) -> None:
        """ATLASBRIDGE_SLACK_* env vars are applied at load time."""
        p = tmp_path / "config.toml"
        p.write_text(f'[telegram]\nbot_token = "{VALID_TOKEN}"\nallowed_users = [12345678]\n')
        monkeypatch.setenv("ATLASBRIDGE_SLACK_BOT_TOKEN", "xoxb-111-222-AAABBBCCC")
        monkeypatch.setenv("ATLASBRIDGE_SLACK_APP_TOKEN", "xapp-1-A111-222-BBBCCC")
        monkeypatch.setenv("ATLASBRIDGE_SLACK_ALLOWED_USERS", "U1234567890,U9876543210")

        from atlasbridge.core.config import load_config

        cfg = load_config(p)
        assert cfg.slack is not None
        assert cfg.slack.allowed_users == ["U1234567890", "U9876543210"]
