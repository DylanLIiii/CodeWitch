"""CLI commands for CodeWitch."""

import sys
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .config import EnvironmentConfig
from .env_manager import ClaudeEnvManager, CodexEnvManager
from .utils import (
    detect_shell,
    format_env_vars_for_display,
    generate_shell_guidance,
    validate_env_vars_applied,
)

app = typer.Typer(help="Claude Code and Codex environment switcher")
claude_code_app = typer.Typer(help="Manage Claude Code environments")
codex_app = typer.Typer(help="Manage Codex environments")
app.add_typer(claude_code_app, name="claude-code")
app.add_typer(codex_app, name="codex")


@app.callback()
def version_callback(version: bool = typer.Option(False, "--version", "-v", help="Show version and exit")) -> None:
    """CodeWitch CLI callback."""
    if version:
        print(f"CodeWitch version {__version__}")
        raise typer.Exit()


claude_env_manager = ClaudeEnvManager()
codex_env_manager = CodexEnvManager()
console = Console()


def _config_path_hint(tool_slug: str) -> str:
    """Return the config path hint for the tool."""
    if tool_slug == "claude-code":
        return "~/.claude/cc.yaml"
    return "~/.codex/cw.yaml"


def _global_files_hint(tool_slug: str) -> str:
    """Return the global files touched by apply."""
    if tool_slug == "claude-code":
        return "~/.claude/settings.json"
    return "~/.codex/config.toml, ~/.codex/auth.json"


def _runtime_label(tool_slug: str) -> str:
    """Return the display label for runtime values."""
    if tool_slug == "codex":
        return "Codex Runtime Preview"
    return "Environment Variables"


def _get_endpoint_display(tool_slug: str, env_config: EnvironmentConfig) -> str:
    """Return the endpoint/base URL shown in `list`."""
    if tool_slug == "claude-code":
        return env_config.url or "-"
    if env_config.normalized_auth_mode == "login":
        return "official login"
    return env_config.codex_base_url or "openai"


def _print_missing_environment_help(error: ValueError) -> None:
    """Print common error guidance."""
    console.print(f"[red]Error: {error}[/red]")
    if "environment" in str(error).lower() and "not found" in str(error).lower():
        console.print("[yellow]Run the matching `list` command to see available environments.[/yellow]")


def _load_env_config(tool_slug: str, manager: Any, env_name: str) -> EnvironmentConfig:
    """Load a single environment config."""
    environments = manager.config_manager.load_environments(tool_slug)
    if env_name not in environments:
        raise ValueError(f"Environment '{env_name}' not found")
    return environments[env_name]


def _render_list(tool_slug: str, manager: Any) -> None:
    """Render the environment list for a tool."""
    environments = manager.config_manager.load_environments(tool_slug)
    if not environments:
        console.print(f"[yellow]No environments found in {_config_path_hint(tool_slug)}[/yellow]")
        return

    table = Table(title=f"{manager.tool_label} Environments")
    table.add_column("Name", style="cyan")
    if tool_slug == "codex":
        table.add_column("Auth", style="yellow")
    table.add_column("Endpoint", style="green")
    table.add_column("Model", style="magenta")
    if tool_slug == "claude-code":
        table.add_column("Fast Model", style="blue")
        table.add_column("Opus", style="magenta")
        table.add_column("Sonnet", style="magenta")
        table.add_column("Haiku", style="magenta")

    for name, config in environments.items():
        endpoint = _get_endpoint_display(tool_slug, config)
        if len(endpoint) > 40:
            endpoint = endpoint[:37] + "..."

        row = [name]
        if tool_slug == "codex":
            row.append(config.normalized_auth_mode or "-")
        row.append(endpoint)
        row.append(config.model or "-")
        if tool_slug == "claude-code":
            model_mappings = config.claude_model_mappings
            row.append(config.fast or model_mappings.get("haiku") or "-")
            row.append(model_mappings.get("opus") or "-")
            row.append(model_mappings.get("sonnet") or "-")
            row.append(model_mappings.get("haiku") or "-")
        table.add_row(*row)

    console.print(table)


def _render_use(tool_slug: str, manager: Any, env_name: str, export_only: bool) -> None:
    """Handle local `use` for a tool."""
    try:
        env_config = _load_env_config(tool_slug, manager, env_name)
        env_vars, export_commands = manager.set_local_env(env_name)

        if export_only:
            print(export_commands)
            return

        console.print(f"[green]✓ {manager.tool_label} environment '{env_name}' prepared for this terminal[/green]")

        env_applied = validate_env_vars_applied(env_vars)
        if env_applied:
            console.print("[yellow]⚠ Environment variables are already applied.[/yellow]")
        else:
            console.print("[bold yellow]⚠ IMPORTANT: Environment variables are NOT yet applied to your shell.[/bold yellow]")
            console.print("[dim]Run the eval command below in your current shell to activate it.[/dim]")

        shell = detect_shell()
        if shell:
            console.print(f"[bold]Detected shell:[/bold] {shell}")

        console.print("[bold cyan]To apply it now, copy and run:[/bold cyan]")
        console.print(f"[bold white]{generate_shell_guidance(tool_slug, env_name)}[/bold white]")

        if export_commands:
            console.print("[bold]Or manually copy these shell commands:[/bold]")
            console.print(export_commands)

        if tool_slug == "codex" and env_config.normalized_auth_mode == "login":
            console.print("[dim]This unsets OPENAI_API_KEY and points Codex at a generated CODEX_HOME.[/dim]")
    except ValueError as error:
        if export_only:
            print(f"Error: {error}", file=sys.stderr)
        else:
            _print_missing_environment_help(error)
        sys.exit(1)


def _render_apply(tool_slug: str, manager: Any, env_name: str) -> None:
    """Handle global `apply` for a tool."""
    try:
        _load_env_config(tool_slug, manager, env_name)
        manager.set_global_env(env_name)
        console.print(f"[green]✓ {manager.tool_label} environment '{env_name}' applied globally[/green]")
        console.print(f"[bold cyan]Updated file(s):[/bold cyan] {_global_files_hint(tool_slug)}")
    except ValueError as error:
        _print_missing_environment_help(error)
        sys.exit(1)


def _render_current(tool_slug: str, manager: Any) -> None:
    """Show the current active environment for a tool."""
    current_env = manager.get_current_env()
    if not current_env:
        console.print("[yellow]No active environment[/yellow]")
        return

    console.print(
        f"[bold cyan]Active Environment:[/bold cyan] {current_env['env_name']} ({current_env['mode']})"
    )
    console.print(f"[bold]{_runtime_label(tool_slug)}:[/bold]")
    console.print(format_env_vars_for_display(current_env["env_vars"]))


def _render_unset(manager: Any, global_mode: bool) -> None:
    """Clear local or global state for a tool."""
    if global_mode:
        manager.unset_global()
        console.print("[green]✓ Global environment cleared[/green]")
    else:
        manager.unset_local()
        console.print("[green]✓ Local environment cleared[/green]")


def _render_info(tool_slug: str, manager: Any, env_name: str) -> None:
    """Show detailed environment info."""
    env_info = manager.get_env_info(env_name)
    if not env_info:
        console.print(f"[red]Environment '{env_name}' not found[/red]")
        sys.exit(1)

    console.print(f"[bold cyan]Environment:[/bold cyan] {env_info['name']}")
    console.print(f"[bold]Tool:[/bold] {manager.tool_label}")
    console.print("[bold]Configuration:[/bold]")
    for key, value in env_info["config"].items():
        if value is None:
            continue
        if ("token" in key.lower() or "key" in key.lower()) and isinstance(value, str):
            masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
            console.print(f"  {key}: {masked}")
        else:
            console.print(f"  {key}: {value}")

    console.print(f"[bold]{_runtime_label(tool_slug)}:[/bold]")
    console.print(format_env_vars_for_display(env_info["env_vars"]))


@claude_code_app.command("list")
def claude_list():
    """List Claude Code environments."""
    _render_list("claude-code", claude_env_manager)


@claude_code_app.command("use")
def claude_use(
    env_name: str,
    export_only: bool = typer.Option(False, "--export", "-e", help="Only print export commands (for eval)"),
):
    """Prepare a Claude Code environment for the current shell."""
    _render_use("claude-code", claude_env_manager, env_name, export_only)


@claude_code_app.command("apply")
def claude_apply(env_name: str):
    """Apply a Claude Code environment globally."""
    _render_apply("claude-code", claude_env_manager, env_name)


@claude_code_app.command("current")
def claude_current():
    """Show the current Claude Code environment."""
    _render_current("claude-code", claude_env_manager)


@claude_code_app.command("unset")
def claude_unset(
    global_mode: bool = typer.Option(False, "--global", "-g", help="Clear global environment"),
):
    """Clear Claude Code environment state."""
    _render_unset(claude_env_manager, global_mode)


@claude_code_app.command("info")
def claude_info(env_name: str):
    """Show detailed Claude Code environment information."""
    _render_info("claude-code", claude_env_manager, env_name)


@codex_app.command("list")
def codex_list():
    """List Codex environments."""
    _render_list("codex", codex_env_manager)


@codex_app.command("use")
def codex_use(
    env_name: str,
    export_only: bool = typer.Option(False, "--export", "-e", help="Only print export commands (for eval)"),
):
    """Prepare a Codex environment for the current shell."""
    _render_use("codex", codex_env_manager, env_name, export_only)


@codex_app.command("apply")
def codex_apply(env_name: str):
    """Apply a Codex environment globally."""
    _render_apply("codex", codex_env_manager, env_name)


@codex_app.command("current")
def codex_current():
    """Show the current Codex environment."""
    _render_current("codex", codex_env_manager)


@codex_app.command("unset")
def codex_unset(
    global_mode: bool = typer.Option(False, "--global", "-g", help="Clear global environment"),
):
    """Clear Codex environment state."""
    _render_unset(codex_env_manager, global_mode)


@codex_app.command("info")
def codex_info(env_name: str):
    """Show detailed Codex environment information."""
    _render_info("codex", codex_env_manager, env_name)


if __name__ == "__main__":
    app()
