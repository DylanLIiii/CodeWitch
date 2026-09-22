"""Configuration loading for CodeWitch."""

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

import yaml
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


TOOL_ALIASES = {
    "claude": "claude-code",
    "claude-code": "claude-code",
    "claude_code": "claude-code",
    "codex": "codex",
}

CLAUDE_MODEL_FAMILIES = ("opus", "sonnet", "haiku", "fable")

CLAUDE_MODEL_ALIASES = {
    "default",
    "best",
    "fable",
    "fable[1m]",
    "sonnet",
    "sonnet[1m]",
    "opus",
    "opus[1m]",
    "haiku",
    "opusplan",
}

CLAUDE_CAPABILITY_ENV_VARS = {
    "opus": "ANTHROPIC_DEFAULT_OPUS_MODEL_SUPPORTED_CAPABILITIES",
    "sonnet": "ANTHROPIC_DEFAULT_SONNET_MODEL_SUPPORTED_CAPABILITIES",
    "haiku": "ANTHROPIC_DEFAULT_HAIKU_MODEL_SUPPORTED_CAPABILITIES",
    "fable": "ANTHROPIC_DEFAULT_FABLE_MODEL_SUPPORTED_CAPABILITIES",
    "custom": "ANTHROPIC_CUSTOM_MODEL_OPTION_SUPPORTED_CAPABILITIES",
}

# Every env var CodeWitch may emit for Claude Code. Used to merge into
# settings.json without clobbering variables the user manages by hand.
CLAUDE_MANAGED_ENV_VARS = {
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_DEFAULT_FABLE_MODEL",
    "ANTHROPIC_SMALL_FAST_MODEL",
    "ANTHROPIC_CUSTOM_MODEL_OPTION",
    "ANTHROPIC_CUSTOM_MODEL_OPTION_NAME",
    "ANTHROPIC_CUSTOM_MODEL_OPTION_DESCRIPTION",
    "BASH_DEFAULT_TIMEOUT_MS",
    "CLAUDE_CODE_MAX_OUTPUT_TOKENS",
    "CLAUDE_CODE_MAX_CONTEXT_TOKENS",
    "CLAUDE_CODE_SUBAGENT_MODEL",
    "CLAUDE_CODE_EFFORT_LEVEL",
    "CLAUDE_CODE_AUTO_MODE_SERVER",
    *CLAUDE_CAPABILITY_ENV_VARS.values(),
}


def is_recognizable_claude_model_id(model: str) -> bool:
    """Check whether Claude Code can resolve a model ID to a known model."""
    normalized = model.strip().lower()
    if normalized in CLAUDE_MODEL_ALIASES:
        return True
    return "claude-" in normalized


class EnvironmentConfig(BaseModel):
    """Environment configuration for Claude Code or Codex."""

    model_config = ConfigDict(extra="allow")

    tool: str = "claude-code"
    url: Optional[str] = None
    token: Optional[str] = None
    model: Optional[str] = None
    fast: Optional[str] = None
    models: Optional[Dict[str, str]] = None
    opus: Optional[str] = None
    sonnet: Optional[str] = None
    haiku: Optional[str] = None
    fable: Optional[str] = None
    timeout: Optional[int] = None
    tokens: Optional[int] = None
    max_context_tokens: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("max_context_tokens", "claude_code_max_context_tokens"),
    )
    auth_mode: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    subagent_model: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("subagent_model", "claude_code_subagent_model"),
    )
    effort_level: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("effort_level", "claude_code_effort_level"),
    )
    auto_mode: Optional[bool] = None
    auto_mode_server: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("auto_mode_server", "claude_code_auto_mode_server"),
    )
    custom_model: Optional[str] = None
    custom_model_name: Optional[str] = None
    custom_model_description: Optional[str] = None
    custom_model_capabilities: Optional[str] = None
    capabilities: Optional[Dict[str, str]] = None
    model_overrides: Optional[Dict[str, str]] = None
    model_reasoning_effort: Optional[str] = None
    plan_mode_reasoning_effort: Optional[str] = None
    model_reasoning_summary: Optional[str] = None

    @field_validator("tool", mode="before")
    @classmethod
    def _normalize_tool_field(cls, value: Optional[str]) -> str:
        if value is None:
            return "claude-code"
        return TOOL_ALIASES.get(str(value).strip().lower(), str(value).strip().lower())

    @field_validator(
        "subagent_model",
        "effort_level",
        "fable",
        "custom_model",
        "custom_model_name",
        "custom_model_description",
        "model_reasoning_effort",
        "plan_mode_reasoning_effort",
        "model_reasoning_summary",
        mode="before",
    )
    @classmethod
    def _strip_optional_string_fields(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        stripped = str(value).strip()
        return stripped or None

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

    @field_validator("models", mode="before")
    @classmethod
    def _normalize_models_field(cls, value: Any) -> Optional[Dict[str, str]]:
        if value is None:
            return None
        if not isinstance(value, dict):
            return None

        normalized: Dict[str, str] = {}
        for alias, model_name in value.items():
            alias_key = str(alias).strip().lower()
            if alias_key not in CLAUDE_MODEL_FAMILIES:
                continue
            if model_name is None:
                continue
            normalized_model = str(model_name).strip()
            if normalized_model:
                normalized[alias_key] = normalized_model
        return normalized or None

    @field_validator("auto_mode", "auto_mode_server", mode="before")
    @classmethod
    def _normalize_bool_field(cls, value: Any) -> Optional[bool]:
        if value is None or isinstance(value, bool):
            return value
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        return None

    @field_validator("custom_model_capabilities", mode="before")
    @classmethod
    def _normalize_capability_list(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, (list, tuple)):
            joined = ",".join(str(item).strip() for item in value if str(item).strip())
            return joined or None
        normalized = str(value).strip()
        return normalized or None

    @field_validator("capabilities", mode="before")
    @classmethod
    def _normalize_capabilities_field(cls, value: Any) -> Optional[Dict[str, str]]:
        if value is None:
            return None
        if not isinstance(value, dict):
            return None

        normalized: Dict[str, str] = {}
        for key, capability_list in value.items():
            capability_key = str(key).strip().lower()
            if capability_key not in CLAUDE_CAPABILITY_ENV_VARS:
                continue
            if isinstance(capability_list, (list, tuple)):
                joined = ",".join(
                    str(item).strip() for item in capability_list if str(item).strip()
                )
            else:
                joined = str(capability_list).strip()
            if joined:
                normalized[capability_key] = joined
        return normalized or None

    @field_validator("model_overrides", mode="before")
    @classmethod
    def _normalize_model_overrides_field(cls, value: Any) -> Optional[Dict[str, str]]:
        if value is None:
            return None
        if not isinstance(value, dict):
            return None

        normalized: Dict[str, str] = {}
        for model_id, provider_id in value.items():
            if provider_id is None:
                continue
            normalized_key = str(model_id).strip()
            normalized_value = str(provider_id).strip()
            if normalized_key and normalized_value:
                normalized[normalized_key] = normalized_value
        return normalized or None

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

    @property
    def claude_model_mappings(self) -> Dict[str, str]:
        """Return normalized Claude model alias mappings."""
        mappings: Dict[str, str] = {}

        if self.models:
            mappings.update(self.models)

        for alias in CLAUDE_MODEL_FAMILIES:
            alias_model = getattr(self, alias)
            if alias_model:
                mappings[alias] = alias_model

        if "haiku" not in mappings and self.fast:
            mappings["haiku"] = self.fast

        return mappings


def map_claude_config_to_env_vars(env_config: EnvironmentConfig) -> Dict[str, str]:
    """Map a Claude Code environment config to shell env vars."""
    env_vars: Dict[str, str] = {}

    if env_config.url:
        env_vars["ANTHROPIC_BASE_URL"] = env_config.url
    if env_config.token:
        env_vars["ANTHROPIC_AUTH_TOKEN"] = env_config.token

    model_mappings = dict(env_config.claude_model_mappings)
    sonnet_pin = model_mappings.get("sonnet")
    if env_config.model:
        # Claude Code enables features such as auto mode by resolving the
        # session model to a model it recognizes. An opaque provider ID like
        # "glm-4.7" resolves to nothing, so pin it behind the sonnet alias
        # instead; the wire ID stays the same while the session keeps a
        # recognized identity. An existing sonnet pin only blocks this when
        # it maps to a different wire ID.
        if not is_recognizable_claude_model_id(env_config.model) and (
            sonnet_pin is None or sonnet_pin == env_config.model
        ):
            env_vars["ANTHROPIC_MODEL"] = "sonnet"
            model_mappings["sonnet"] = env_config.model
        else:
            env_vars["ANTHROPIC_MODEL"] = env_config.model
    elif sonnet_pin:
        # No explicit model: default the session to the sonnet alias so the
        # session model identity is recognized instead of depending on how
        # the account default resolves.
        env_vars["ANTHROPIC_MODEL"] = "sonnet"

    model_env_map = {
        "opus": "ANTHROPIC_DEFAULT_OPUS_MODEL",
        "sonnet": "ANTHROPIC_DEFAULT_SONNET_MODEL",
        "haiku": "ANTHROPIC_DEFAULT_HAIKU_MODEL",
        "fable": "ANTHROPIC_DEFAULT_FABLE_MODEL",
    }
    for alias, env_var_name in model_env_map.items():
        model_name = model_mappings.get(alias)
        if model_name:
            env_vars[env_var_name] = model_name

    fast_model = env_config.fast or model_mappings.get("haiku")
    if fast_model:
        env_vars["ANTHROPIC_SMALL_FAST_MODEL"] = fast_model
    if env_config.timeout is not None:
        env_vars["BASH_DEFAULT_TIMEOUT_MS"] = str(env_config.timeout)
    if env_config.tokens is not None:
        env_vars["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = str(env_config.tokens)
    if env_config.max_context_tokens is not None:
        env_vars["CLAUDE_CODE_MAX_CONTEXT_TOKENS"] = str(env_config.max_context_tokens)
    if env_config.subagent_model:
        env_vars["CLAUDE_CODE_SUBAGENT_MODEL"] = env_config.subagent_model
    if env_config.effort_level:
        env_vars["CLAUDE_CODE_EFFORT_LEVEL"] = env_config.effort_level
    if env_config.auto_mode_server is not None:
        env_vars["CLAUDE_CODE_AUTO_MODE_SERVER"] = (
            "1" if env_config.auto_mode_server else "0"
        )
    if env_config.custom_model:
        env_vars["ANTHROPIC_CUSTOM_MODEL_OPTION"] = env_config.custom_model
        if env_config.custom_model_name:
            env_vars["ANTHROPIC_CUSTOM_MODEL_OPTION_NAME"] = env_config.custom_model_name
        if env_config.custom_model_description:
            env_vars["ANTHROPIC_CUSTOM_MODEL_OPTION_DESCRIPTION"] = (
                env_config.custom_model_description
            )
        if env_config.custom_model_capabilities:
            env_vars["ANTHROPIC_CUSTOM_MODEL_OPTION_SUPPORTED_CAPABILITIES"] = (
                env_config.custom_model_capabilities
            )

    for capability_key, capability_env_var in CLAUDE_CAPABILITY_ENV_VARS.items():
        capability_value = (env_config.capabilities or {}).get(capability_key)
        if capability_value:
            env_vars[capability_env_var] = capability_value

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
        codewitch_state = settings.get("codewitch")
        if not isinstance(codewitch_state, dict):
            codewitch_state = {}
        meta = codewitch_state.get(f"{self.default_tool}_meta")
        if not isinstance(meta, dict):
            meta = {}

        existing_env = settings.get("env")
        if not isinstance(existing_env, dict):
            existing_env = {}
        merged_env = {
            key: value
            for key, value in existing_env.items()
            if key not in CLAUDE_MANAGED_ENV_VARS
        }
        merged_env.update(map_claude_config_to_env_vars(env_config))
        settings["env"] = merged_env

        self._apply_model_overrides(settings, env_config, meta)
        self._apply_auto_mode(settings, env_config, meta)
        if not meta.get("model_override_keys"):
            meta.pop("model_override_keys", None)

        codewitch_state[self.default_tool] = env_name
        if meta:
            codewitch_state[f"{self.default_tool}_meta"] = meta
        else:
            codewitch_state.pop(f"{self.default_tool}_meta", None)
        settings["codewitch"] = codewitch_state
        self.save_settings(settings)

    def clear_env_from_settings(self) -> None:
        """Remove the managed Claude Code environment from settings.json."""
        if self.settings_json_path is None:
            return

        settings = self.load_settings()

        env = settings.get("env")
        if isinstance(env, dict):
            remaining_env = {
                key: value
                for key, value in env.items()
                if key not in CLAUDE_MANAGED_ENV_VARS
            }
            if remaining_env:
                settings["env"] = remaining_env
            else:
                settings.pop("env", None)

        codewitch_state = settings.get("codewitch")
        meta: Dict[str, Any] = {}
        if isinstance(codewitch_state, dict):
            codewitch_state.pop(self.default_tool, None)
            stored_meta = codewitch_state.pop(f"{self.default_tool}_meta", None)
            if isinstance(stored_meta, dict):
                meta = stored_meta

        managed_override_keys = meta.get("model_override_keys")
        if managed_override_keys:
            overrides = settings.get("modelOverrides")
            if isinstance(overrides, dict):
                for key in managed_override_keys:
                    overrides.pop(key, None)
                if overrides:
                    settings["modelOverrides"] = overrides
                else:
                    settings.pop("modelOverrides", None)

        if meta.get("default_mode_managed"):
            permissions = settings.get("permissions")
            if isinstance(permissions, dict):
                previous = meta.get("default_mode_prev")
                if previous is None:
                    permissions.pop("defaultMode", None)
                else:
                    permissions["defaultMode"] = previous
                if permissions:
                    settings["permissions"] = permissions
                else:
                    settings.pop("permissions", None)

        if isinstance(codewitch_state, dict):
            if codewitch_state:
                settings["codewitch"] = codewitch_state
            else:
                settings.pop("codewitch", None)

        self.save_settings(settings)

    def _apply_model_overrides(
        self,
        settings: Dict[str, Any],
        env_config: EnvironmentConfig,
        meta: Dict[str, Any],
    ) -> None:
        """Merge `model_overrides` into settings.json and track managed keys."""
        managed_keys = meta.get("model_override_keys") or []
        overrides = settings.get("modelOverrides")
        if not isinstance(overrides, dict):
            overrides = {}
        for key in managed_keys:
            overrides.pop(key, None)

        new_overrides = env_config.model_overrides or {}
        overrides.update(new_overrides)
        if overrides:
            settings["modelOverrides"] = overrides
        else:
            settings.pop("modelOverrides", None)
        meta["model_override_keys"] = sorted(new_overrides)

    def _apply_auto_mode(
        self,
        settings: Dict[str, Any],
        env_config: EnvironmentConfig,
        meta: Dict[str, Any],
    ) -> None:
        """Write `permissions.defaultMode` and remember the value it replaced."""
        permissions = settings.get("permissions")
        if not isinstance(permissions, dict):
            permissions = {}

        if env_config.auto_mode:
            if not meta.get("default_mode_managed"):
                meta["default_mode_prev"] = permissions.get("defaultMode")
                meta["default_mode_managed"] = True
            permissions["defaultMode"] = "auto"
            settings["permissions"] = permissions
        elif meta.get("default_mode_managed"):
            previous = meta.get("default_mode_prev")
            if previous is None:
                permissions.pop("defaultMode", None)
            else:
                permissions["defaultMode"] = previous
            if permissions:
                settings["permissions"] = permissions
            else:
                settings.pop("permissions", None)
            meta.pop("default_mode_managed", None)
            meta.pop("default_mode_prev", None)

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
