"""CLI commands for the local dashboard."""

from __future__ import annotations

import socket

import click


@click.group("dashboard")
def dashboard_group() -> None:
    """Local read-only governance dashboard."""


@dashboard_group.command("start")
@click.option(
    "--host",
    default="127.0.0.1",
    show_default=True,
    help="Bind address (default: loopback only)",
)
@click.option("--port", default=8787, show_default=True, help="Port to listen on")
@click.option(
    "--no-browser",
    is_flag=True,
    default=False,
    help="Do not open browser automatically",
)
@click.option(
    "--i-understand-risk",
    is_flag=True,
    default=False,
    hidden=True,
    help="Allow binding to non-loopback addresses (DANGEROUS)",
)
def dashboard_start(
    host: str, port: int, no_browser: bool, i_understand_risk: bool
) -> None:
    """Start the local dashboard server."""
    # Guard: fastapi must be installed
    try:
        import fastapi  # noqa: F401
    except ImportError as exc:
        click.echo(
            "Error: Dashboard dependencies not installed.\n"
            "Install them with:\n\n"
            "  pip install 'atlasbridge[dashboard]'\n",
            err=True,
        )
        raise SystemExit(1) from exc

    # Guard: host must be loopback unless risk is explicitly acknowledged
    from atlasbridge.dashboard.sanitize import is_loopback

    if not is_loopback(host) and not i_understand_risk:
        click.echo(
            "Error: Binding to a non-loopback address exposes the dashboard "
            "to your network.\n"
            "The dashboard has NO authentication — anyone on the network can view "
            "session data.\n\n"
            "If you understand the risk and want to proceed, add:\n\n"
            "  --i-understand-risk\n\n"
            f"Got: --host {host!r}. Without the flag, only loopback "
            "(127.0.0.1, ::1, localhost) is allowed.",
            err=True,
        )
        raise SystemExit(1)

    from atlasbridge.dashboard.app import start_server

    click.echo(f"Starting dashboard at http://{host}:{port}")
    start_server(
        host=host,
        port=port,
        open_browser=not no_browser,
        allow_non_loopback=i_understand_risk,
    )


@dashboard_group.command("status")
@click.option("--port", default=8787, show_default=True, help="Port to check")
def dashboard_status(port: int) -> None:
    """Check if the dashboard server is running."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        result = sock.connect_ex(("127.0.0.1", port))
        if result == 0:
            click.echo(f"Dashboard is running on port {port}")
        else:
            click.echo(f"Dashboard is not running on port {port}")
    finally:
        sock.close()
