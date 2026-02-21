"""aegis run — launch a CLI tool under Aegis supervision."""

from __future__ import annotations

import asyncio
import sys

from rich.console import Console


def cmd_run(tool: str, command: list[str], label: str, cwd: str, console: Console) -> None:
    """Load config and run the tool under Aegis supervision (foreground)."""
    from aegis.core.config import load_config
    from aegis.core.exceptions import ConfigError, ConfigNotFoundError

    try:
        config = load_config()
    except ConfigNotFoundError as exc:
        console.print(f"[red]Not configured:[/red] {exc}")
        console.print("Run [cyan]aegis setup[/cyan] first.")
        sys.exit(1)
    except ConfigError as exc:
        console.print(f"[red]Config error:[/red] {exc}")
        sys.exit(1)

    console.print(f"[bold]Aegis[/bold] supervising: [cyan]{' '.join(command)}[/cyan]")
    console.print(
        f"Session will forward prompts to Telegram ({len(config.telegram.allowed_users)} user(s))"
    )
    console.print("Press Ctrl+C to stop.\n")

    try:
        asyncio.run(_run_async(tool=tool, command=command, label=label, cwd=cwd, config=config))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        sys.exit(0)


async def _run_async(tool: str, command: list[str], label: str, cwd: str, config: object) -> None:
    from aegis.core.daemon.manager import DaemonManager

    # Convert AegisConfig to the dict format DaemonManager expects
    cfg_dict = _config_to_dict(tool=tool, command=command, label=label, cwd=cwd, config=config)

    manager = DaemonManager(cfg_dict)
    await manager.start()


def _config_to_dict(tool: str, command: list[str], label: str, cwd: str, config: object) -> dict:
    """Convert AegisConfig + run params into the DaemonManager config dict."""
    from pathlib import Path

    bot_token = config.telegram.bot_token.get_secret_value()  # type: ignore[union-attr]
    allowed_users = config.telegram.allowed_users  # type: ignore[union-attr]
    db_path = config.db_path  # type: ignore[union-attr]

    return {
        "data_dir": str(db_path.parent),
        "tool": tool,
        "command": command,
        "label": label,
        "cwd": cwd or str(Path.cwd()),
        "channels": {
            "telegram": {
                "bot_token": bot_token,
                "allowed_user_ids": allowed_users,
            }
        },
        "prompts": {
            "timeout_seconds": config.prompts.timeout_seconds,  # type: ignore[union-attr]
            "stuck_timeout_seconds": config.prompts.stuck_timeout_seconds,  # type: ignore[union-attr]
        },
    }
