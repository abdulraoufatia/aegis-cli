"""Database inspection and management CLI commands."""

from __future__ import annotations

import click
from rich.console import Console

console = Console()


@click.group()
def db_group() -> None:
    """Database inspection and management."""


@db_group.command("info")
@click.option("--json", "as_json", is_flag=True, default=False)
def db_info(as_json: bool) -> None:
    """Show database path, schema version, and table stats."""
    from atlasbridge.core.config import atlasbridge_dir
    from atlasbridge.core.constants import DB_FILENAME

    db_path = atlasbridge_dir() / DB_FILENAME

    if not db_path.exists():
        if as_json:
            import json as _json

            click.echo(_json.dumps({"exists": False, "path": str(db_path)}))
        else:
            console.print(f"Database does not exist yet: {db_path}")
            console.print("It will be created on the first [cyan]atlasbridge run[/cyan].")
        return

    import sqlite3

    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    try:
        from atlasbridge.core.store.migrations import LATEST_SCHEMA_VERSION, get_user_version

        version = get_user_version(conn)
        tables = {}
        for table in ("sessions", "prompts", "replies", "audit_events"):
            try:
                row = conn.execute(f"SELECT count(*) FROM {table}").fetchone()  # noqa: S608
                tables[table] = row[0] if row else 0
            except Exception:  # noqa: BLE001
                tables[table] = -1  # table missing

        size_kb = db_path.stat().st_size / 1024

        if as_json:
            import json as _json

            click.echo(
                _json.dumps(
                    {
                        "exists": True,
                        "path": str(db_path),
                        "schema_version": version,
                        "latest_version": LATEST_SCHEMA_VERSION,
                        "size_kb": round(size_kb, 1),
                        "tables": tables,
                    },
                    indent=2,
                )
            )
        else:
            console.print(f"[bold]Database[/bold]: {db_path}")
            console.print(f"Schema version: {version} (latest: {LATEST_SCHEMA_VERSION})")
            console.print(f"Size: {size_kb:.1f} KB")
            console.print("\nTable row counts:")
            for table, count in tables.items():
                status = f"{count}" if count >= 0 else "[red]missing[/red]"
                console.print(f"  {table:<16} {status}")
    finally:
        conn.close()


@db_group.command("migrate")
@click.option(
    "--dry-run", is_flag=True, default=False, help="Show pending migrations without applying them."
)
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="Machine-readable JSON output."
)
def db_migrate(dry_run: bool, as_json: bool) -> None:
    """Run (or preview) pending schema migrations."""
    from atlasbridge.core.config import atlasbridge_dir
    from atlasbridge.core.constants import DB_FILENAME

    db_path = atlasbridge_dir() / DB_FILENAME

    if not db_path.exists():
        if as_json:
            import json as _json

            click.echo(_json.dumps({"status": "no_database", "path": str(db_path)}))
        else:
            console.print(f"Database does not exist yet: {db_path}")
            console.print("It will be created on the first [cyan]atlasbridge run[/cyan].")
        return

    import sqlite3

    from atlasbridge.core.store.migrations import LATEST_SCHEMA_VERSION, get_user_version

    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    try:
        current = get_user_version(conn)
        pending = list(range(current, LATEST_SCHEMA_VERSION))

        if as_json:
            import json as _json

            click.echo(
                _json.dumps(
                    {
                        "path": str(db_path),
                        "current_version": current,
                        "latest_version": LATEST_SCHEMA_VERSION,
                        "pending_migrations": [f"v{v} -> v{v + 1}" for v in pending],
                        "dry_run": dry_run,
                        "status": "up_to_date"
                        if not pending
                        else ("dry_run" if dry_run else "applied"),
                    },
                    indent=2,
                )
            )
            if not pending or dry_run:
                return

        if not pending:
            if not as_json:
                console.print(f"[green]Database is up to date[/green] (v{current}).")
            return

        if dry_run:
            if not as_json:
                console.print(f"[bold]Database[/bold]: {db_path}")
                console.print(f"Current schema version: {current}")
                console.print(f"Latest schema version:  {LATEST_SCHEMA_VERSION}")
                console.print(f"\n[yellow]Pending migrations ({len(pending)}):[/yellow]")
                for v in pending:
                    console.print(f"  v{v} -> v{v + 1}")
                console.print("\nRun without [cyan]--dry-run[/cyan] to apply.")
            return

        # Apply migrations
        conn.close()
        conn = None  # type: ignore[assignment]

        from atlasbridge.core.store.database import Database

        database = Database(db_path)
        database.connect()
        database.close()
        console.print(
            f"[green]Migrations applied successfully[/green] (v{current} -> v{LATEST_SCHEMA_VERSION})."
        )
    finally:
        if conn is not None:
            conn.close()
