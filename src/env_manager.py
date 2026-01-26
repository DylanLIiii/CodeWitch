"""Environment variable management for CodeWitch."""

import json
import os
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

from .config import ConfigManager, EnvironmentConfig
from .utils import format_env_vars_for_export


class EnvManager:
    """Manage local and global environment variables."""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.local_state_path = self.config_manager.claude_dir / "cw_current.json"

    def set_local_env(self, env_name: str) -> Tuple[Dict[str, str], str]:
        """Set local environment variables for the current session.

        Returns:
            Tuple containing (env_vars_dict, export_commands)
        """
        environments = self.config_manager.load_environments()
        if env_name not in environments:
            raise ValueError(f"Environment '{env_name}' not found")

        env_config = environments[env_name]
        env_vars = self.config_manager._map_config_to_env_vars(env_config)

        # Save to local state file
        local_state = {
            'env_name': env_name,
            'env_vars': env_vars
        }
        self.config_manager.claude_dir.mkdir(exist_ok=True)
        with open(self.local_state_path, 'w', encoding='utf-8') as f:
            json.dump(local_state, f, indent=2)

        # Clear global env vars from settings.json (as per plan)
        self.config_manager.clear_env_from_settings()

        return env_vars, format_env_vars_for_export(env_vars)

    def set_global_env(self, env_name: str) -> Tuple[Dict[str, str], str]:
        """Set global environment variables in settings.json.

        Returns:
            Tuple containing (env_vars_dict, export_commands)
        """
        environments = self.config_manager.load_environments()
        if env_name not in environments:
            raise ValueError(f"Environment '{env_name}' not found")

        env_config = environments[env_name]

        # Update settings.json
        self.config_manager.update_env_in_settings(env_name, env_config)

        # Also set local environment variables for immediate use
        env_vars = self.config_manager._map_config_to_env_vars(env_config)

        # Save to local state file as well
        local_state = {
            'env_name': env_name,
            'env_vars': env_vars
        }
        self.config_manager.claude_dir.mkdir(exist_ok=True)
        with open(self.local_state_path, 'w', encoding='utf-8') as f:
            json.dump(local_state, f, indent=2)

        return env_vars, format_env_vars_for_export(env_vars)

    def unset_local(self) -> None:
        """Clear local environment variables."""
        if self.local_state_path.exists():
            self.local_state_path.unlink()

    def unset_global(self) -> None:
        """Clear global environment variables."""
        self.config_manager.clear_env_from_settings()
        # Also clear local state
        self.unset_local()

    def get_current_env(self) -> Optional[Dict[str, Any]]:
        """Get current active environment (local first, then global).

        Returns:
            Dict with keys 'env_name', 'env_vars', 'mode' ('local' or 'global')
            or None if no environment is active
        """
        # Check local state first
        if self.local_state_path.exists():
            try:
                with open(self.local_state_path, 'r', encoding='utf-8') as f:
                    local_state = json.load(f)

                # Verify that the environment still exists
                environments = self.config_manager.load_environments()
                env_name = local_state.get('env_name')

                if env_name in environments:
                    return {
                        'env_name': env_name,
                        'env_vars': local_state.get('env_vars', {}),
                        'mode': 'local'
                    }
            except (json.JSONDecodeError, KeyError):
                pass

        # Check global settings
        env_name = self.config_manager.get_current_env_from_settings()
        if env_name:
            environments = self.config_manager.load_environments()
            if env_name in environments:
                env_config = environments[env_name]
                env_vars = self.config_manager._map_config_to_env_vars(env_config)
                return {
                    'env_name': env_name,
                    'env_vars': env_vars,
                    'mode': 'global'
                }

        return None

    def get_env_info(self, env_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about an environment."""
        environments = self.config_manager.load_environments()
        if env_name not in environments:
            return None

        env_config = environments[env_name]
        env_vars = self.config_manager._map_config_to_env_vars(env_config)

        return {
            'name': env_name,
            'config': env_config.model_dump(),
            'env_vars': env_vars
        }

