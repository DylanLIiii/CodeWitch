"""Utility functions for CodeWitch."""

import os
import sys
from typing import Dict, Any, Optional



def format_env_vars_for_display(env_vars: Dict[str, str]) -> str:
    """Format environment variables for display."""
    lines = []
    for key, value in env_vars.items():
        # Mask tokens for security
        if 'TOKEN' in key.upper():
            masked = value[:8] + '...' + value[-4:] if len(value) > 12 else '***'
            lines.append(f"{key}={masked}")
        else:
            lines.append(f"{key}={value}")
    return '\n'.join(lines)


def format_env_vars_for_export(env_vars: Dict[str, str]) -> str:
    """Format environment variables as shell export commands."""
    lines = []
    for key, value in env_vars.items():
        # Properly escape values for shell
        escaped_value = value.replace("'", "'\"'\"'")
        lines.append(f"export {key}='{escaped_value}'")
    return '\n'.join(lines)


def detect_shell() -> Optional[str]:
    """Detect user's shell for tailored instructions."""
    shell = os.environ.get('SHELL', '')
    if 'zsh' in shell:
        return 'zsh'
    elif 'bash' in shell:
        return 'bash'
    elif 'fish' in shell:
        return 'fish'
    return None


def generate_shell_guidance(env_name: str, global_mode: bool = False) -> str:
    """Generate shell-specific guidance for applying environment variables."""
    shell = detect_shell()
    command_name = "cw"

    # Base command
    if global_mode:
        base_cmd = f"{command_name} use --global {env_name} --export"
    else:
        base_cmd = f"{command_name} use {env_name} --export"

    if shell == 'bash' or shell == 'zsh':
        return f"eval \"$({base_cmd})\""
    elif shell == 'fish':
        return f"eval ({base_cmd})"
    else:
        # Generic fallback
        return f"eval \"$({base_cmd})\""


def validate_env_vars_applied(env_vars: Dict[str, str]) -> bool:
    """Check if environment variables are actually set in the current process."""
    if not env_vars:
        return True

    for key in env_vars:
        if key not in os.environ:
            return False
    return True


def get_missing_env_vars(env_vars: Dict[str, str]) -> list:
    """Get list of environment variables that are not set."""
    missing = []
    for key in env_vars:
        if key not in os.environ:
            missing.append(key)
    return missing