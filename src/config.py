"""Configuration management for CodeWitch."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, Field, ConfigDict



class EnvironmentConfig(BaseModel):
    """Configuration for a single environment."""

    url: str
    token: Union[str, List[str]]
    model: Optional[str] = None
    fast: Optional[str] = None
    timeout: Optional[int] = None
    tokens: Optional[int] = None

    model_config = ConfigDict(extra="ignore")  # Ignore extra fields in YAML


class ConfigManager:
    """Manage Claude Code configuration files."""

    def __init__(self):
        self.claude_dir = Path.home() / ".claude"
        self.cc_yaml_path = self.claude_dir / "cc.yaml"
        self.settings_json_path = self.claude_dir / "settings.json"

    def load_environments(self) -> Dict[str, EnvironmentConfig]:
        """Load and parse environments from cc.yaml."""
        if not self.cc_yaml_path.exists():
            return {}

        with open(self.cc_yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Invalid cc.yaml format: expected dict, got {type(data)}")

        environments = {}
        for name, config in data.items():
            if not isinstance(config, dict):
                raise ValueError(f"Invalid config for environment '{name}': expected dict, got {type(config)}")

            # Handle token field which might be a list or string
            # If it's a list, we'll use it as-is
            token = config.get('token')
            if isinstance(token, list) and len(token) > 0:
                # Use the first token if it's a list
                config['token'] = token[0]

            environments[name] = EnvironmentConfig(**config)

        return environments

    def load_settings(self) -> Dict[str, Any]:
        """Load settings.json."""
        if not self.settings_json_path.exists():
            return {}

        with open(self.settings_json_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_settings(self, settings: Dict[str, Any]) -> None:
        """Save settings.json."""
        self.claude_dir.mkdir(exist_ok=True)

        with open(self.settings_json_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)

    @staticmethod
    def _map_config_to_env_vars(env_config: EnvironmentConfig) -> Dict[str, str]:
        """Map environment configuration to Claude Code environment variables."""
        env_vars = {}

        # Required fields
        env_vars['ANTHROPIC_BASE_URL'] = env_config.url
        env_vars['ANTHROPIC_AUTH_TOKEN'] = env_config.token

        # Optional fields with mappings
        if env_config.model:
            env_vars['ANTHROPIC_MODEL'] = env_config.model
            # Set backward compatibility fields
            env_vars['ANTHROPIC_DEFAULT_OPUS_MODEL'] = env_config.model
            env_vars['ANTHROPIC_DEFAULT_SONNET_MODEL'] = env_config.model

        if env_config.fast:
            env_vars['ANTHROPIC_SMALL_FAST_MODEL'] = env_config.fast
            env_vars['ANTHROPIC_DEFAULT_HAIKU_MODEL'] = env_config.fast

        if env_config.timeout:
            # Use timeout as-is (assuming milliseconds)
            env_vars['BASH_DEFAULT_TIMEOUT_MS'] = str(env_config.timeout)

        if env_config.tokens:
            env_vars['CLAUDE_CODE_MAX_OUTPUT_TOKENS'] = str(env_config.tokens)
        else:
            # Default value from Claude Code documentation
            env_vars['CLAUDE_CODE_MAX_OUTPUT_TOKENS'] = '48000'

        return env_vars

    def update_env_in_settings(self, env_name: str, env_config: EnvironmentConfig) -> None:
        """Update the env object in settings.json with environment variables."""
        settings = self.load_settings()

        # Ensure env object exists
        if 'env' not in settings:
            settings['env'] = {}

        # Map environment config to Claude Code environment variables
        env_vars = self._map_config_to_env_vars(env_config)

        # Update the env object
        settings['env'] = env_vars

        self.save_settings(settings)

    def clear_env_from_settings(self) -> None:
        """Remove the env object from settings.json."""
        settings = self.load_settings()

        if 'env' in settings:
            del settings['env']
            self.save_settings(settings)

    def get_current_env_from_settings(self) -> Optional[str]:
        """Try to determine which environment is currently active from settings.json."""
        settings = self.load_settings()

        if 'env' not in settings:
            return None

        env_vars = settings['env']
        url = env_vars.get('ANTHROPIC_BASE_URL')

        if not url:
            return None

        # Try to match against known environments
        environments = self.load_environments()
        for name, config in environments.items():
            if config.url == url:
                return name

        return None