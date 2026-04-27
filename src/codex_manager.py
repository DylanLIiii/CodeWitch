"""Codex configuration management for CodeWitch."""

import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from tomlkit import document, dumps, parse, table

from .config import EnvironmentConfig


def _sanitize_env_name(env_name: str) -> str:
    """Sanitize environment name to a safe directory name.

    Only allows alphanumeric characters, underscores, hyphens, and periods.
    Rejects dangerous names like '.' and '..'.
    """
    # Reject dangerous names
    if env_name in (".", ".."):
        raise ValueError(f"Invalid environment name: {env_name}")

    # Replace any character not in the allowed set with underscore
    sanitized = re.sub(r"[^A-Za-z0-9._-]", "_", env_name)

    # Ensure the result doesn't start with dangerous prefixes
    if sanitized.startswith(".") or sanitized.startswith("-"):
        sanitized = "_" + sanitized[1:]

    return sanitized


def _is_path_inside(base: Path, path: Path) -> bool:
    """Check if path is inside base directory (using resolved paths)."""
    try:
        resolved_base = base.resolve()
        resolved_path = path.resolve()
        # Use os.path.commonpath or string comparison for containment
        return str(resolved_path).startswith(str(resolved_base) + str(Path("/")))
    except (OSError, ValueError):
        return False


class CodexManager:
    """Manage global and local Codex configuration."""

    SHARED_ENTRY_NAMES = (
        "skills",
        "memories",
        "models_cache.json",
        "version.json",
        ".personality_migration",
    )

    def __init__(
        self,
        codex_dir: Optional[Path] = None,
        managed_homes_dir: Optional[Path] = None,
    ) -> None:
        self.codex_dir = codex_dir or Path.home() / ".codex"
        self.config_path = self.codex_dir / "config.toml"
        self.auth_path = self.codex_dir / "auth.json"
        self.managed_homes_dir = managed_homes_dir or self.codex_dir / "codewitch" / "homes"

    def create_local_home(self, env_name: str, env_config: EnvironmentConfig) -> Path:
        """Create a terminal-local Codex home for the selected environment."""
        # Sanitize env_name to prevent path traversal
        safe_name = _sanitize_env_name(env_name)
        local_home = self.managed_homes_dir / safe_name

        # Verify the path is inside managed_homes_dir
        if not _is_path_inside(self.managed_homes_dir, local_home):
            raise ValueError(
                f"Invalid environment name '{env_name}': would escape managed directory"
            )

        if local_home.exists():
            shutil.rmtree(local_home)

        local_home.mkdir(parents=True, exist_ok=True)
        self._mirror_shared_entries(local_home)

        config_doc = self._load_config_document(self.config_path)
        self._apply_config_profile(config_doc, env_name, env_config)
        self._save_config_document(local_home / "config.toml", config_doc)

        auth_data = self._load_auth(self.auth_path)
        auth_data = self._apply_auth_profile(auth_data, env_config)
        self._save_auth(local_home / "auth.json", auth_data)

        return local_home

    def apply_global_env(self, env_name: str, env_config: EnvironmentConfig) -> None:
        """Apply a Codex environment to the real global Codex files."""
        self.codex_dir.mkdir(parents=True, exist_ok=True)

        config_doc = self._load_config_document(self.config_path)
        self._apply_config_profile(config_doc, env_name, env_config)
        self._save_config_document(self.config_path, config_doc)

        auth_data = self._load_auth(self.auth_path)
        auth_data = self._apply_auth_profile(auth_data, env_config)
        self._save_auth(self.auth_path, auth_data)

    def clear_global_env(self) -> None:
        """Clear CodeWitch-managed Codex global settings."""
        if self.config_path.exists():
            config_doc = self._load_config_document(self.config_path)
            self._clear_managed_provider_state(config_doc)
            self._save_config_document(self.config_path, config_doc)

        if not self.auth_path.exists():
            return

        auth_data = self._load_auth(self.auth_path)
        if auth_data.get("tokens"):
            auth_data["auth_mode"] = "chatgpt"
        auth_data["OPENAI_API_KEY"] = None
        self._save_auth(self.auth_path, auth_data)

    def get_current_env_name(self, environments: Dict[str, EnvironmentConfig]) -> Optional[str]:
        """Determine the active global Codex environment."""
        if not self.auth_path.exists():
            return None

        auth_data = self._load_auth(self.auth_path)
        config_doc = self._load_config_document(self.config_path)
        config_data = config_doc.unwrap() if hasattr(config_doc, "unwrap") else {}

        active_model_provider = config_data.get("model_provider", "openai")
        active_model = config_data.get("model")
        active_providers = config_data.get("model_providers", {})
        active_auth_mode = auth_data.get("auth_mode")
        active_api_key = auth_data.get("OPENAI_API_KEY")

        for env_name, env_config in environments.items():
            if env_config.normalized_tool != "codex":
                continue

            expected_provider = (
                env_config.codex_provider_id(env_name)
                if env_config.codex_base_url and env_config.normalized_auth_mode == "apikey"
                else "openai"
            )

            if active_model_provider != expected_provider:
                continue

            if env_config.model and active_model != env_config.model:
                continue

            if env_config.normalized_auth_mode == "login":
                if active_auth_mode != "chatgpt":
                    continue
            else:
                if active_auth_mode != "apikey":
                    continue
                if env_config.codex_api_key != active_api_key:
                    continue

            if env_config.codex_base_url and env_config.normalized_auth_mode == "apikey":
                provider_config = active_providers.get(expected_provider, {})
                if provider_config.get("base_url") != env_config.codex_base_url:
                    continue

            return env_name

        return None

    def build_local_env_vars(self, local_home: Path, env_config: EnvironmentConfig) -> Dict[str, Optional[str]]:
        """Build shell variables for terminal-local Codex switching."""
        env_vars: Dict[str, Optional[str]] = {"CODEX_HOME": str(local_home)}

        if env_config.normalized_auth_mode == "login":
            env_vars["OPENAI_API_KEY"] = None
        elif env_config.codex_api_key:
            env_vars["OPENAI_API_KEY"] = env_config.codex_api_key
        elif env_config.normalized_auth_mode == "apikey":
            # This should not happen if validation in _apply_auth_profile works,
            # but we keep it as defense in depth
            raise ValueError(
                "Codex auth_mode=apikey requires api_key to be configured in the environment"
            )

        return env_vars

    def build_runtime_preview(self, env_name: str, env_config: EnvironmentConfig) -> Dict[str, str]:
        """Return a display-friendly preview of the Codex runtime settings."""
        preview: Dict[str, str] = {
            "CODEX_AUTH_MODE": env_config.normalized_auth_mode or "unknown",
            "CODEX_MODEL_PROVIDER": "openai",
        }

        if env_config.model:
            preview["CODEX_MODEL"] = env_config.model
        if env_config.model_reasoning_effort:
            preview["model_reasoning_effort"] = env_config.model_reasoning_effort
        if env_config.plan_mode_reasoning_effort:
            preview["plan_mode_reasoning_effort"] = env_config.plan_mode_reasoning_effort
        if env_config.model_reasoning_summary:
            preview["model_reasoning_summary"] = env_config.model_reasoning_summary

        if env_config.normalized_auth_mode == "apikey" and env_config.codex_api_key:
            preview["OPENAI_API_KEY"] = env_config.codex_api_key

        if env_config.codex_base_url and env_config.normalized_auth_mode == "apikey":
            preview["CODEX_MODEL_PROVIDER"] = env_config.codex_provider_id(env_name)
            preview["CODEX_BASE_URL"] = env_config.codex_base_url

        return preview

    def _load_config_document(self, path: Path):
        """Load a TOML document."""
        if not path.exists():
            return document()

        content = path.read_text(encoding="utf-8")
        if not content.strip():
            return document()

        return parse(content)

    def _save_config_document(self, path: Path, config_doc) -> None:
        """Save a TOML document."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dumps(config_doc), encoding="utf-8")

    def _load_auth(self, path: Path) -> Dict[str, Any]:
        """Load a Codex auth file."""
        if not path.exists():
            return {}

        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    def _save_auth(self, path: Path, auth_data: Dict[str, Any]) -> None:
        """Save a Codex auth file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as file:
            json.dump(auth_data, file, indent=2)

    def _apply_auth_profile(
        self,
        auth_data: Dict[str, Any],
        env_config: EnvironmentConfig,
    ) -> Dict[str, Any]:
        """Apply the selected auth profile to auth.json content."""
        updated_auth = dict(auth_data)

        if env_config.normalized_auth_mode == "login":
            tokens = updated_auth.get("tokens")
            if not isinstance(tokens, dict) or not tokens:
                raise ValueError("No Codex ChatGPT login found. Run `codex login` first.")
            updated_auth["auth_mode"] = "chatgpt"
            updated_auth["OPENAI_API_KEY"] = None
            return updated_auth

        # Validate that api_key is present for apikey mode
        if not env_config.codex_api_key:
            raise ValueError(
                "Codex auth_mode=apikey requires api_key to be configured in the environment"
            )

        updated_auth["auth_mode"] = "apikey"
        updated_auth["OPENAI_API_KEY"] = env_config.codex_api_key
        return updated_auth

    def _apply_config_profile(self, config_doc, env_name: str, env_config: EnvironmentConfig) -> None:
        """Apply the selected profile to a Codex config document."""
        self._clear_managed_provider_state(config_doc)

        if env_config.model:
            config_doc["model"] = env_config.model

        self._apply_reasoning_to_config(config_doc, env_config)

        if env_config.normalized_auth_mode == "apikey" and env_config.codex_base_url:
            provider_id = env_config.codex_provider_id(env_name)
            providers = config_doc.get("model_providers")
            if providers is None:
                config_doc["model_providers"] = table()
                providers = config_doc["model_providers"]

            provider_table = table()
            provider_table["name"] = env_config.codex_provider_name(env_name)
            provider_table["base_url"] = env_config.codex_base_url
            provider_table["requires_openai_auth"] = True
            provider_table["wire_api"] = "responses"
            providers[provider_id] = provider_table
            config_doc["model_provider"] = provider_id
            return

        config_doc["model_provider"] = "openai"

    @staticmethod
    def _apply_reasoning_to_config(config_doc, env_config: EnvironmentConfig) -> None:
        """Set Codex CLI reasoning options on config when present in cw.yaml."""
        if env_config.model_reasoning_effort is not None:
            config_doc["model_reasoning_effort"] = env_config.model_reasoning_effort
        if env_config.plan_mode_reasoning_effort is not None:
            config_doc["plan_mode_reasoning_effort"] = env_config.plan_mode_reasoning_effort
        if env_config.model_reasoning_summary is not None:
            config_doc["model_reasoning_summary"] = env_config.model_reasoning_summary

    def _clear_managed_provider_state(self, config_doc) -> None:
        """Remove CodeWitch-managed providers from config.toml."""
        providers = config_doc.get("model_providers")
        if providers is not None:
            managed_keys = [
                key
                for key in list(providers.keys())
                if isinstance(key, str) and key.startswith("codewitch_")
            ]
            for key in managed_keys:
                del providers[key]

            if len(list(providers.keys())) == 0:
                del config_doc["model_providers"]

        model_provider = config_doc.get("model_provider")
        if isinstance(model_provider, str) and model_provider.startswith("codewitch_"):
            config_doc["model_provider"] = "openai"

    def _mirror_shared_entries(self, local_home: Path) -> None:
        """Share non-auth Codex assets with the generated local home."""
        for entry_name in self.SHARED_ENTRY_NAMES:
            source = self.codex_dir / entry_name
            if not source.exists():
                continue

            target = local_home / entry_name
            if target.exists() or target.is_symlink():
                if target.is_dir() and not target.is_symlink():
                    shutil.rmtree(target)
                else:
                    target.unlink()

            target.symlink_to(source, target_is_directory=source.is_dir())
