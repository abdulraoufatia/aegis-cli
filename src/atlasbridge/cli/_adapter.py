"""Adapter management CLI commands."""

from __future__ import annotations

import click
from rich.console import Console

console = Console()
err_console = Console(stderr=True)


@click.group()
def adapter_group() -> None:
    """Tool adapter management."""


@adapter_group.command("list")
@click.option("--json", "as_json", is_flag=True, default=False)
def adapter_list(as_json: bool) -> None:
    """Show available tool adapters."""
    import atlasbridge.adapters  # noqa: F401 — registers all built-in adapters
    from atlasbridge.adapters.base import AdapterRegistry

    adapters = AdapterRegistry.list_all()
    if as_json:
        import json

        rows = [
            {
                "name": name,
                "tool_name": cls.tool_name,
                "description": cls.description,
                "min_version": cls.min_tool_version,
            }
            for name, cls in adapters.items()
        ]
        click.echo(json.dumps(rows, indent=2))
    else:
        console.print("\n[bold]Available Adapters[/bold]\n")
        for name, cls in adapters.items():
            console.print(
                f"  [cyan]{name:<12}[/cyan] {cls.description or '—'}"
                + (f"  (min: {cls.min_tool_version})" if cls.min_tool_version else "")
            )
        console.print()


@click.command("adapters")
@click.option("--json", "as_json", is_flag=True, default=False, help="Machine-readable JSON output")
def adapters_cmd(as_json: bool) -> None:
    """List installed tool adapters."""
    import shutil

    import atlasbridge.adapters  # noqa: F401 — registers all built-in adapters
    from atlasbridge.adapters.base import AdapterRegistry

    registry = AdapterRegistry.list_all()

    if not registry:
        err_console.print(
            "[red]Error:[/red] No adapters found. Reinstall: pip install -U atlasbridge"
        )
        raise SystemExit(1)

    if as_json:
        import json

        rows = []
        for name, cls in sorted(registry.items()):
            rows.append(
                {
                    "name": name,
                    "kind": "llm",
                    "enabled": bool(shutil.which(cls.tool_name) if cls.tool_name else False),
                    "source": "builtin",
                    "tool_name": cls.tool_name,
                    "description": cls.description,
                    "min_version": cls.min_tool_version,
                }
            )
        click.echo(json.dumps({"adapters": rows, "count": len(rows)}, indent=2))
    else:
        console.print("\n[bold]Installed Adapters[/bold]\n")
        for name, cls in sorted(registry.items()):
            on_path = bool(shutil.which(cls.tool_name)) if cls.tool_name else False
            status = "[green]on PATH[/green]" if on_path else "[dim]not on PATH[/dim]"
            desc = cls.description or "—"
            ver = f"  (min: {cls.min_tool_version})" if cls.min_tool_version else ""
            console.print(f"  [cyan]{name:<14}[/cyan] {desc}{ver}  {status}")
        console.print(f"\n  {len(registry)} adapter(s) registered.\n")
