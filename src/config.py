"""Configuration loading for CodeWitch."""

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

import yaml
from pydantic import BaseModel, ConfigDict, field_validator


TOOL_ALIASES = {
    "claude": "claude-code",
    "claude-code": "claude-code",
    "claude_code": "claude-code",
    "codex": "codex",
}


class EnvironmentConfig(BaseModel):
    """Environment configuration for Claude Code or Codex."""

    model_config = ConfigDict(extra="allow")

    tool: str = "claude-code"
    url: Optional[str] = None
    token: Optional[str] = None
    model: Optional[str] = None
    fast: Optional[str] = None
    timeout: Optional[int] = None
    tokens: Optional[int] = None
    auth_mode: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None

    @field_validator("tool", mode="before")
    @classmethod
    def _normalize_tool_field(cls, value: Optional[str]) -> str:
        if value is None:
            return "claude-code"
        return TOOL_ALIASES.get(str(value).strip().lower(), str(value).strip().lower())

    @field_validator("token", "api_key", mode="before")
    @classmethod
    def _coerce_secret(cls, value: Any) -> Optional[str]:
        if isinstance(value, list):
            return value[0] if value else None
        return value

    @field_validator("auth_mode", mode="before")
    @classmethod
    def _normalize_auth_mode_field(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        normalized = str(value).strip().lower().replace("-", "").replace("_", "")
        if normalized == "apikey":
            return "apikey"
        if normalized == "login":
            return "login"
        return str(value).strip().lower()

    @property
    def normalized_tool(self) -> str:
        """Return the canonical tool key."""
        return TOOL_ALIASES.get(self.tool, self.tool)

    @property
    def normalized_auth_mode(self) -> Optional[str]:
        """Return the canonical Codex auth mode."""
        if self.normalized_tool != "codex":
            return None
        if self.auth_mode:
            return self.auth_mode
        if self.api_key:
            return "apikey"
        return "login"

    @property
    def codex_base_url(self) -> Optional[str]:
        """Backward-compatible alias for Codex base URL."""
        return self.base_url

    @property
    def codex_api_key(self) -> Optional[str]:
        """Backward-compatible alias for Codex API key."""
        return self.api_key

    def codex_provider_id(self, env_name: str) -> str:
        """Return the managed provider identifier for Codex."""
        provider_suffix = "".join(
            character.lower() if character.isalnum() else "_"
            for character in env_name
        ).strip("_") or "env"
        return f"codewitch_{provider_suffix}"

    def codex_provider_name(self, env_name: str) -> str:
        """Return the managed provider name for Codex."""
        return f"CodeWitch {env_name}"


def map_claude_config_to_env_vars(env_config: EnvironmentConfig) -> Dict[str, str]:
    """Map a Claude Code environment config to shell env vars."""
    env_vars: Dict[str, str] = {}

    if env_config.url:
        env_vars["ANTHROPIC_BASE_URL"] = env_config.url
    if env_config.token:
        env_vars["ANTHROPIC_AUTH_TOKEN"] = env_config.token
    if env_config.model:
        env_vars["ANTHROPIC_MODEL"] = env_config.model
    if env_config.fast:
        env_vars["ANTHROPIC_SMALL_FAST_MODEL"] = env_config.fast
    if env_config.timeout is not None:
        env_vars["BASH_DEFAULT_TIMEOUT_MS"] = str(env_config.timeout)
    if env_config.tokens is not None:
        env_vars["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = str(env_config.tokens)

    return env_vars


class ConfigManager:
    """Manage a tool-specific CodeWitch configuration file."""

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        config_filename: Optional[str] = None,
        default_tool: str = "claude-code",
        settings_filename: Optional[str] = None,
    ) -> None:
        self.default_tool = TOOL_ALIASES.get(default_tool, default_tool)

        if base_dir is None:
            base_dir = Path.home() / (".codex" if self.default_tool == "codex" else ".claude")
        self.base_dir = Path(base_dir)

        if config_filename is None:
            config_filename = "cw.yaml" if self.default_tool == "codex" else "cc.yaml"
        self.config_path = self.base_dir / config_filename
        self.cc_yaml_path = self.config_path

        # Backward-compatible alias used in tests and older modules.
        self.claude_dir = self.base_dir

        if settings_filename is None and self.default_tool == "claude-code":
            settings_filename = "settings.json"
        self.settings_path = self.base_dir / settings_filename if settings_filename else None
        self.settings_json_path = self.settings_path

    def load_environments(self, tool: Optional[str] = None) -> Dict[str, EnvironmentConfig]:
        """Load environments from the tool's YAML config file."""
        selected_tool = None
        if tool:
            normalized = str(tool).strip().lower().replace("_", "-")
            selected_tool = TOOL_ALIASES.get(normalized, normalized)
        else:
            selected_tool = self.default_tool

        raw_data, from_legacy = self._load_environment_yaml()
        if not isinstance(raw_data, dict):
            return {}

        default_tool_for_untagged = "claude-code" if from_legacy else self.default_tool
        environments: Dict[str, EnvironmentConfig] = {}
        for env_name, env_data, section_tool in self._iter_environment_entries(raw_data):
            payload = dict(env_data)
            payload["tool"] = section_tool or payload.get("tool") or default_tool_for_untagged
            env_config = EnvironmentConfig.model_validate(payload)
            if selected_tool and env_config.normalized_tool != selected_tool:
                continue
            environments[env_name] = env_config

        return environments

    def load_settings(self) -> Dict[str, Any]:
        """Load the tool-specific settings file when supported."""
        if self.settings_json_path is None or not self.settings_json_path.exists():
            return {}

        with open(self.settings_json_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def save_settings(self, settings: Dict[str, Any]) -> None:
        """Persist the tool-specific settings file when supported."""
        if self.settings_json_path is None:
            return

        self.settings_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.settings_json_path, "w", encoding="utf-8") as file:
            json.dump(settings, file, indent=2)

    def update_env_in_settings(self, env_name: str, env_config: EnvironmentConfig) -> None:
        """Write the selected Claude Code environment into settings.json."""
        if self.settings_json_path is None:
            return

        settings = self.load_settings()
        settings["env"] = map_claude_config_to_env_vars(env_config)
        codewitch_state = settings.get("codewitch")
        if not isinstance(codewitch_state, dict):
            codewitch_state = {}
        codewitch_state[self.default_tool] = env_name
        settings["codewitch"] = codewitch_state
        self.save_settings(settings)

    def clear_env_from_settings(self) -> None:
        """Remove the managed Claude Code environment from settings.json."""
        if self.settings_json_path is None:
            return

        settings = self.load_settings()
        settings.pop("env", None)

        codewitch_state = settings.get("codewitch")
        if isinstance(codewitch_state, dict):
            codewitch_state.pop(self.default_tool, None)
            if codewitch_state:
                settings["codewitch"] = codewitch_state
            else:
                settings.pop("codewitch", None)

        self.save_settings(settings)

    def get_current_env_from_settings(
        self,
        environments: Optional[Dict[str, EnvironmentConfig]] = None,
    ) -> Optional[str]:
        """Determine the active Claude Code environment from settings.json."""
        if self.settings_json_path is None:
            return None

        settings = self.load_settings()
        env_vars = settings.get("env")
        if not isinstance(env_vars, dict):
            return None

        available_envs = environments or self.load_environments()
        for env_name, env_config in available_envs.items():
            expected = map_claude_config_to_env_vars(env_config)
            if all(env_vars.get(key) == value for key, value in expected.items()):
                return env_name

        return None

    def get_current_claude_env_from_settings(
        self,
        environments: Optional[Dict[str, EnvironmentConfig]] = None,
    ) -> Optional[str]:
        """Backward-compatible alias for Claude settings lookup."""
        return self.get_current_env_from_settings(environments)

    @staticmethod
    def map_claude_config_to_env_vars(env_config: EnvironmentConfig) -> Dict[str, str]:
        """Public alias for mapping Claude config to env vars."""
        return map_claude_config_to_env_vars(env_config)

    @staticmethod
    def _map_config_to_env_vars(env_config: EnvironmentConfig) -> Dict[str, str]:
        """Backward-compatible alias used by older tests and modules."""
        return map_claude_config_to_env_vars(env_config)

    @staticmethod
    def _iter_environment_entries(
        raw_data: Dict[str, Any],
    ) -> Iterable[Tuple[str, Dict[str, Any], Optional[str]]]:
        """Yield environment entries from flat or namespaced YAML shapes."""
        for key, value in raw_data.items():
            section_tool = TOOL_ALIASES.get(str(key).strip().lower())
            if (
                section_tool in {"claude-code", "codex"}
                and isinstance(value, dict)
                and value
                and all(isinstance(item, dict) for item in value.values())
            ):
                for env_name, env_data in value.items():
                    if isinstance(env_data, dict):
                        yield env_name, env_data, section_tool
                continue

            if isinstance(value, dict):
                yield key, value, None

    def _load_environment_yaml(self) -> Tuple[Dict[str, Any], bool]:
        """Load the active environment YAML with codex legacy fallback."""
        if self.cc_yaml_path.exists():
            with open(self.cc_yaml_path, "r", encoding="utf-8") as file:
                return yaml.safe_load(file) or {}, False

        if self.default_tool == "codex":
            legacy_path = Path.home() / ".claude" / "cc.yaml"
            if legacy_path.exists():
                with open(legacy_path, "r", encoding="utf-8") as file:
                    return yaml.safe_load(file) or {}, True

        return {}, False


def build_claude_config_manager(base_dir: Optional[Path] = None) -> ConfigManager:
    """Build the Claude Code config manager."""
    return ConfigManager(
        base_dir=base_dir or Path.home() / ".claude",
        config_filename="cc.yaml",
        default_tool="claude-code",
        settings_filename="settings.json",
    )


def build_codex_config_manager(base_dir: Optional[Path] = None) -> ConfigManager:
    """Build the Codex config manager."""
    return ConfigManager(
        base_dir=base_dir or Path.home() / ".codex",
        config_filename="cw.yaml",
        default_tool="codex",
    )
