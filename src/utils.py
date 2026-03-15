"""Utility functions for CodeWitch."""

import os
from typing import Dict, Optional


def format_env_vars_for_display(env_vars: Dict[str, Optional[str]]) -> str:
    """Format environment variables for display."""
    lines = []
    for key, value in env_vars.items():
        if value is None:
            lines.append(f"{key}=<unset>")
        elif 'TOKEN' in key.upper() or 'API_KEY' in key.upper():
            masked = value[:8] + '...' + value[-4:] if len(value) > 12 else '***'
            lines.append(f"{key}={masked}")
        else:
            lines.append(f"{key}={value}")
    return '\n'.join(lines)


def format_env_vars_for_export(env_vars: Dict[str, Optional[str]]) -> str:
    """Format environment variables as shell export commands."""
    lines = []
    for key, value in env_vars.items():
        if value is None:
            lines.append(f"unset {key}")
            continue

        escaped_value = value.replace("'", "'\"'\"'")
        lines.append(f"export {key}='{escaped_value}'")
    return '\n'.join(lines)


def detect_shell() -> Optional[str]:
    """Detect user's shell for tailored instructions."""
    shell = os.environ.get('SHELL', '')
    if 'zsh' in shell:
        return 'zsh'
    if 'bash' in shell:
        return 'bash'
    if 'fish' in shell:
        return 'fish'
    return None


def generate_shell_guidance(tool: str, env_name: str) -> str:
    """Generate shell-specific guidance for applying environment variables."""
    shell = detect_shell()
    command_name = "cw"
    base_cmd = f"{command_name} {tool} use {env_name} --export"

    if shell in {'bash', 'zsh'}:
        return f"eval \"$({base_cmd})\""
    if shell == 'fish':
        return f"eval ({base_cmd})"
    return f"eval \"$({base_cmd})\""


def validate_env_vars_applied(env_vars: Dict[str, Optional[str]]) -> bool:
    """Check if environment variables are actually set in the current process."""
    if not env_vars:
        return True

    for key, value in env_vars.items():
        if value is None:
            if key in os.environ:
                return False
            continue
        if os.environ.get(key) != value:
            return False
    return True


def get_missing_env_vars(env_vars: Dict[str, Optional[str]]) -> list:
    """Get list of environment variables that are not set."""
    missing = []
    for key, value in env_vars.items():
        if value is None and key in os.environ:
            missing.append(key)
        elif value is not None and os.environ.get(key) != value:
            missing.append(key)
    return missing
