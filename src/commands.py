"""CLI commands for CodeWitch."""

import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .config import ConfigManager
from .env_manager import EnvManager
from .utils import (
    format_env_vars_for_display,
    format_env_vars_for_export,
    detect_shell,
    generate_shell_guidance,
    validate_env_vars_applied,
    get_missing_env_vars,
)

from . import __version__

app = typer.Typer(help="Claude Code environment switcher")

@app.callback()
def version_callback(version: bool = typer.Option(None, "--version", "-v", help="Show version and exit")) -> None:
    """CodeWitch CLI callback."""
    if version:
        print(f"CodeWitch version {__version__}")
        raise typer.Exit()

config_manager = ConfigManager()
env_manager = EnvManager()
console = Console()


@app.command()
def list():
    """List all available environments."""
    environments = config_manager.load_environments()

    if not environments:
        console.print("[yellow]No environments found in ~/.claude/cc.yaml[/yellow]")
        return

    table = Table(title="Available Environments")
    table.add_column("Name", style="cyan")
    table.add_column("URL", style="green")
    table.add_column("Model", style="magenta")
    table.add_column("Fast Model", style="blue")

    for name, config in environments.items():
        model = config.model or "-"
        fast = config.fast or "-"
        # Truncate long URLs for display
        url = config.url
        if len(url) > 40:
            url = url[:37] + "..."

        table.add_row(name, url, model, fast)

    console.print(table)


@app.command()
def use(
    env_name: str,
    global_mode: bool = typer.Option(
        False, "--global", "-g", help="Set environment globally (persistent)"
    ),
    export_only: bool = typer.Option(
        False, "--export", "-e", help="Only print export commands (for eval)"
    ),
):
    """Activate an environment locally or globally."""
    try:
        if global_mode:
            env_vars, export_commands = env_manager.set_global_env(env_name)
            success_message = f"[green]✓ Environment '{env_name}' set globally[/green]"
        else:
            env_vars, export_commands = env_manager.set_local_env(env_name)
            success_message = f"[green]✓ Environment '{env_name}' set locally[/green]"

        if export_only:
            # Only print export commands (for eval)
            print(export_commands)
        else:
            # Show full output with enhanced guidance
            console.print(success_message)

            # Check if environment variables are already applied
            env_applied = validate_env_vars_applied(env_vars)

            if env_applied:
                console.print("\n[yellow]⚠ Environment variables are already applied.[/yellow]")
                console.print("[dim]You can still run the command below to re-apply them if needed.[/dim]")
            else:
                # Show prominent warning
                console.print("\n[bold yellow]⚠ IMPORTANT: Environment variables are NOT yet applied to your shell![/bold yellow]")
                console.print("[dim]This command only prepares the environment. To actually use it,[/dim]")
                console.print("[dim]you must run the eval command below in your current shell.[/dim]")

            # Generate shell-specific guidance
            shell = detect_shell()
            if shell:
                console.print(f"\n[bold]Detected shell:[/bold] {shell}")

            # Show the exact command to run
            console.print("\n[bold cyan]To apply environment variables, copy and run:[/bold cyan]")

            guidance_cmd = generate_shell_guidance(env_name, global_mode)
            console.print(f"[bold white]{guidance_cmd}[/bold white]")

            # Also show the manual export option
            console.print("\n[bold]Or manually copy these export commands:[/bold]")
            console.print(export_commands)

            # Provide additional tips
            console.print("\n[dim]Tip: After running the command above, verify with 'cw current'[/dim]")

    except ValueError as e:
        if export_only:
            # Print error to stderr and exit with non-zero
            print(f"Error: {e}", file=sys.stderr)
        else:
            console.print(f"[red]Error: {e}[/red]")
            # Provide helpful suggestions based on error
            error_msg = str(e).lower()
            if "environment" in error_msg and "not found" in error_msg:
                console.print("\n[yellow]Run 'cw list' to see available environments.[/yellow]")
        sys.exit(1)


@app.command()
def current():
    """Show current active environment and variables."""
    current_env = env_manager.get_current_env()

    if not current_env:
        console.print("[yellow]No active environment[/yellow]")
        return

    env_name = current_env['env_name']
    mode = current_env['mode']
    env_vars = current_env['env_vars']

    console.print(f"[bold cyan]Active Environment:[/bold cyan] {env_name} ({mode})")
    console.print("\n[bold]Environment Variables:[/bold]")
    console.print(format_env_vars_for_display(env_vars))


@app.command()
def unset(
    global_mode: bool = typer.Option(
        False, "--global", "-g", help="Clear global environment"
    ),
):
    """Clear active environment."""
    if global_mode:
        env_manager.unset_global()
        console.print("[green]✓ Global environment cleared[/green]")
    else:
        env_manager.unset_local()
        console.print("[green]✓ Local environment cleared[/green]")


@app.command()
def info(env_name: str):
    """Show detailed information about an environment."""
    env_info = env_manager.get_env_info(env_name)

    if not env_info:
        console.print(f"[red]Environment '{env_name}' not found[/red]")
        sys.exit(1)

    console.print(f"[bold cyan]Environment:[/bold cyan] {env_info['name']}")
    console.print("\n[bold]Configuration (cc.yaml):[/bold]")

    config = env_info['config']
    for key, value in config.items():
        if key == 'token' and isinstance(value, str) and len(value) > 8:
            masked = value[:8] + '...' + value[-4:]
            console.print(f"  {key}: {masked}")
        else:
            console.print(f"  {key}: {value}")

    console.print("\n[bold]Mapped Environment Variables:[/bold]")
    console.print(format_env_vars_for_display(env_info['env_vars']))


@app.command()
def apply(
    env_name: str,
    global_mode: bool = typer.Option(
        False, "--global", "-g", help="Apply environment globally (persistent)"
    ),
):
    """Apply environment variables to current shell (convenience wrapper for 'use --export')."""
    try:
        if global_mode:
            env_vars, export_commands = env_manager.set_global_env(env_name)
            success_message = f"[green]✓ Environment '{env_name}' set globally[/green]"
        else:
            env_vars, export_commands = env_manager.set_local_env(env_name)
            success_message = f"[green]✓ Environment '{env_name}' set locally[/green]"

        console.print(success_message)
        console.print("\n[bold yellow]⚠ IMPORTANT: Environment variables are NOT yet applied to your shell[/bold yellow]")
        console.print("[dim]This command only prepares the environment. To actually use it, follow these steps:[/dim]")

        # Step-by-step instructions
        console.print("\n[bold cyan]Step 1: Copy and run this command in your current shell:[/bold cyan]")

        shell = detect_shell()
        if shell:
            console.print(f"[dim]Detected shell: {shell}[/dim]")

        guidance_cmd = generate_shell_guidance(env_name, global_mode)
        console.print(f"[bold white]{guidance_cmd}[/bold white]")

        console.print("\n[bold cyan]Step 2: Verify the environment is active:[/bold cyan]")
        console.print("[dim]Run 'cw current' to confirm environment variables are set.[/dim]")

        console.print("\n[bold cyan]Optional: Create a shell alias for easier use in the future:[/bold cyan]")
        if shell in ['bash', 'zsh']:
            console.print(f"[dim]Add this to your ~/.bashrc or ~/.zshrc:[/dim]")
            console.print(f"[dim]alias cw-{env_name.replace('-', '_')}='eval \"$(cw use {env_name}" + (" --global" if global_mode else "") + " --export)\"'[/dim]")
        elif shell == 'fish':
            console.print(f"[dim]Add this to your ~/.config/fish/config.fish:[/dim]")
            console.print(f"[dim]alias cw_{env_name.replace('-', '_')}='eval (cw use {env_name}" + (" --global" if global_mode else "") + " --export)'[/dim]")

        console.print("\n[dim]After running the eval command above, the environment will be active in your current shell.[/dim]")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        # Provide helpful suggestions based on error
        error_msg = str(e).lower()
        if "environment" in error_msg and "not found" in error_msg:
            console.print("\n[yellow]Run 'cw list' to see available environments.[/yellow]")
        sys.exit(1)


if __name__ == "__main__":
    app()