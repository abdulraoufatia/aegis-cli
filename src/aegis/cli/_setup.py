"""aegis setup — interactive first-time configuration wizard."""

from __future__ import annotations

import re
import sys

from rich.console import Console
from rich.prompt import Prompt

_TOKEN_RE = re.compile(r"\d{8,12}:[A-Za-z0-9_\-]{35,}")


def _validate_token(token: str) -> bool:
    return bool(_TOKEN_RE.fullmatch(token.strip()))


def _validate_users(users_str: str) -> list[int] | None:
    try:
        return [int(u.strip()) for u in users_str.split(",") if u.strip()]
    except ValueError:
        return None


def run_setup(
    channel: str,
    non_interactive: bool,
    console: Console,
    token: str = "",  # nosec B107 — empty default, not a hardcoded credential
    users: str = "",
) -> None:
    """Run the Aegis setup wizard."""
    import os

    from aegis.core.config import aegis_dir, save_config
    from aegis.core.exceptions import ConfigError

    console.print("[bold]Aegis Setup[/bold]")
    console.print(f"\nConfiguring channel: [cyan]{channel}[/cyan]\n")

    if channel != "telegram":
        console.print(f"[red]Channel '{channel}' is not yet implemented.[/red]")
        console.print("Only 'telegram' is supported in v0.2.0.")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Collect bot token
    # -----------------------------------------------------------------------
    if not token:
        token = os.environ.get("AEGIS_TELEGRAM_BOT_TOKEN", "")

    if not token and not non_interactive:
        console.print("Get your bot token from @BotFather on Telegram.\n")
        while True:
            token = Prompt.ask("[bold]Telegram bot token[/bold]").strip()
            if _validate_token(token):
                break
            console.print(
                "[red]Invalid token format.[/red] Expected: [dim]12345678:ABCDEFGHIJKLMNOPQRSTUVWXYZabcde...[/dim]"
            )

    if not token:
        console.print(
            "[red]No bot token provided. Set AEGIS_TELEGRAM_BOT_TOKEN or run interactively.[/red]"
        )
        sys.exit(1)

    if not _validate_token(token):
        console.print("[red]Invalid bot token format.[/red]")
        console.print("Expected format: [dim]<8-12 digits>:<35+ alphanumeric chars>[/dim]")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Collect allowed user IDs
    # -----------------------------------------------------------------------
    if not users:
        users = os.environ.get("AEGIS_TELEGRAM_ALLOWED_USERS", "")

    if not users and not non_interactive:
        console.print("\nYour Telegram user ID (find it by messaging @userinfobot).\n")
        while True:
            users = Prompt.ask("[bold]Allowed Telegram user ID(s)[/bold] (comma-separated)").strip()
            parsed = _validate_users(users)
            if parsed:
                break
            console.print("[red]Please enter numeric user IDs separated by commas.[/red]")

    if not users:
        console.print(
            "[red]No user IDs provided. Set AEGIS_TELEGRAM_ALLOWED_USERS or run interactively.[/red]"
        )
        sys.exit(1)

    parsed_users = _validate_users(users)
    if not parsed_users:
        console.print(f"[red]Invalid user IDs: {users!r}[/red]")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Write config
    # -----------------------------------------------------------------------
    config_data = {
        "telegram": {
            "bot_token": token,
            "allowed_users": parsed_users,
        }
    }

    try:
        cfg_path = save_config(config_data)
    except ConfigError as exc:
        console.print(f"[red]Failed to save config: {exc}[/red]")
        sys.exit(1)

    console.print(f"\n[green]Config saved:[/green] {cfg_path}")
    console.print(f"Aegis dir:    {aegis_dir()}")
    console.print("\n[green]Setup complete.[/green]")
    console.print("Run [cyan]aegis run claude[/cyan] to start supervising Claude Code.")
