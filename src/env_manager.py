"""Environment state management for CodeWitch."""

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .codex_manager import CodexManager
from .config import (
    EnvironmentConfig,
    build_claude_config_manager,
    build_codex_config_manager,
    map_claude_config_to_env_vars,
)
from .utils import format_env_vars_for_export


class ClaudeEnvManager:
    """Manage Claude Code environment switching."""

    tool_slug = "claude-code"
    tool_label = "Claude Code"

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        config_manager: Optional[Any] = None,
    ) -> None:
        self.config_manager = config_manager or build_claude_config_manager(base_dir)
        self.local_state_path = self.config_manager.base_dir / "cw_current.json"

    def set_local_env(self, env_name: str) -> Tuple[Dict[str, Optional[str]], str]:
        """Prepare terminal-local environment variables for Claude Code."""
        env_config = self._get_env_config(env_name)
        env_vars = map_claude_config_to_env_vars(env_config)
        self.config_manager.clear_env_from_settings()
        self._write_local_state(env_name, env_vars)
        return env_vars, format_env_vars_for_export(env_vars)

    def set_global_env(self, env_name: str) -> Tuple[Dict[str, Optional[str]], str]:
        """Apply a persistent Claude Code environment."""
        env_config = self._get_env_config(env_name)
        env_vars = map_claude_config_to_env_vars(env_config)
        self.config_manager.update_env_in_settings(env_name, env_config)
        self.unset_local()
        return env_vars, ""

    def unset_local(self) -> None:
        """Clear terminal-local Claude Code state."""
        if self.local_state_path.exists():
            self.local_state_path.unlink()

    def unset_global(self) -> None:
        """Clear persistent Claude Code state."""
        self.config_manager.clear_env_from_settings()
        self.unset_local()

    def get_current_env(self) -> Optional[Dict[str, Any]]:
        """Return the active Claude Code environment."""
        local_state = self._read_local_state()
        if local_state is not None:
            return local_state

        environments = self.config_manager.load_environments()
        env_name = self.config_manager.get_current_env_from_settings(environments)
        if not env_name:
            return None

        env_config = environments.get(env_name)
        if env_config is None:
            return None

        return {
            "env_name": env_name,
            "env_vars": map_claude_config_to_env_vars(env_config),
            "mode": "global",
            "tool": self.tool_slug,
        }

    def get_env_info(self, env_name: str) -> Optional[Dict[str, Any]]:
        """Return detailed Claude Code environment information."""
        environments = self.config_manager.load_environments()
        env_config = environments.get(env_name)
        if env_config is None:
            return None

        return {
            "name": env_name,
            "tool": self.tool_slug,
            "config": env_config.model_dump(),
            "env_vars": map_claude_config_to_env_vars(env_config),
        }

    def _get_env_config(self, env_name: str) -> EnvironmentConfig:
        environments = self.config_manager.load_environments()
        env_config = environments.get(env_name)
        if env_config is None:
            raise ValueError(f"Environment '{env_name}' not found")
        return env_config

    def _write_local_state(self, env_name: str, env_vars: Dict[str, Optional[str]]) -> None:
        self.local_state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.local_state_path, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "env_name": env_name,
                    "env_vars": env_vars,
                    "mode": "local",
                    "tool": self.tool_slug,
                },
                file,
                indent=2,
            )

    def _read_local_state(self) -> Optional[Dict[str, Any]]:
        if not self.local_state_path.exists():
            return None

        try:
            with open(self.local_state_path, "r", encoding="utf-8") as file:
                local_state = json.load(file)
        except (json.JSONDecodeError, OSError):
            return None

        if not isinstance(local_state, dict):
            return None

        env_name = local_state.get("env_name")
        environments = self.config_manager.load_environments()
        if env_name not in environments:
            return None

        return {
            "env_name": env_name,
            "env_vars": local_state.get("env_vars", {}),
            "mode": "local",
            "tool": self.tool_slug,
        }


class CodexEnvManager:
    """Manage Codex environment switching."""

    tool_slug = "codex"
    tool_label = "Codex"

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        config_manager: Optional[Any] = None,
        codex_manager: Optional[Any] = None,
    ) -> None:
        self.config_manager = config_manager or build_codex_config_manager(base_dir)
        self.local_state_path = self.config_manager.base_dir / "cw_current.json"
        self.codex_manager = codex_manager or CodexManager(codex_dir=self.config_manager.base_dir)

    def set_local_env(self, env_name: str) -> Tuple[Dict[str, Optional[str]], str]:
        """Prepare terminal-local environment variables for Codex."""
        env_config = self._get_env_config(env_name)
        local_home = self.codex_manager.create_local_home(env_name, env_config)
        env_vars = self.codex_manager.build_local_env_vars(local_home, env_config)
        self._write_local_state(env_name, env_vars)
        return env_vars, format_env_vars_for_export(env_vars)

    def set_global_env(self, env_name: str) -> Tuple[Dict[str, Optional[str]], str]:
        """Apply a persistent Codex environment."""
        env_config = self._get_env_config(env_name)
        self.codex_manager.apply_global_env(env_name, env_config)
        self.unset_local()
        return self.codex_manager.build_runtime_preview(env_name, env_config), ""

    def unset_local(self) -> None:
        """Clear terminal-local Codex state and generated home."""
        state = self._read_local_state()
        if state:
            codex_home = state.get("env_vars", {}).get("CODEX_HOME")
            if isinstance(codex_home, str):
                home_path = Path(codex_home)
                if home_path.exists() and self.codex_manager.managed_homes_dir in home_path.parents:
                    shutil.rmtree(home_path)

        if self.local_state_path.exists():
            self.local_state_path.unlink()

    def unset_global(self) -> None:
        """Clear persistent Codex state."""
        self.codex_manager.clear_global_env()
        self.unset_local()

    def get_current_env(self) -> Optional[Dict[str, Any]]:
        """Return the active Codex environment."""
        local_state = self._read_local_state()
        if local_state is not None:
            return local_state

        environments = self.config_manager.load_environments()
        env_name = self.codex_manager.get_current_env_name(environments)
        if not env_name:
            return None

        env_config = environments.get(env_name)
        if env_config is None:
            return None

        return {
            "env_name": env_name,
            "env_vars": self.codex_manager.build_runtime_preview(env_name, env_config),
            "mode": "global",
            "tool": self.tool_slug,
        }

    def get_env_info(self, env_name: str) -> Optional[Dict[str, Any]]:
        """Return detailed Codex environment information."""
        environments = self.config_manager.load_environments()
        env_config = environments.get(env_name)
        if env_config is None:
            return None

        return {
            "name": env_name,
            "tool": self.tool_slug,
            "config": env_config.model_dump(),
            "env_vars": self.codex_manager.build_runtime_preview(env_name, env_config),
        }

    def _get_env_config(self, env_name: str) -> EnvironmentConfig:
        environments = self.config_manager.load_environments()
        env_config = environments.get(env_name)
        if env_config is None:
            raise ValueError(f"Environment '{env_name}' not found")
        return env_config

    def _write_local_state(self, env_name: str, env_vars: Dict[str, Optional[str]]) -> None:
        self.local_state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.local_state_path, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "env_name": env_name,
                    "env_vars": env_vars,
                    "mode": "local",
                    "tool": self.tool_slug,
                },
                file,
                indent=2,
            )

    def _read_local_state(self) -> Optional[Dict[str, Any]]:
        if not self.local_state_path.exists():
            return None

        try:
            with open(self.local_state_path, "r", encoding="utf-8") as file:
                local_state = json.load(file)
        except (json.JSONDecodeError, OSError):
            return None

        if not isinstance(local_state, dict):
            return None

        env_name = local_state.get("env_name")
        environments = self.config_manager.load_environments()
        if env_name not in environments:
            return None

        return {
            "env_name": env_name,
            "env_vars": local_state.get("env_vars", {}),
            "mode": "local",
            "tool": self.tool_slug,
        }
