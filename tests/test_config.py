"""Tests for config.py."""

import json

import yaml

from src.config import (
    EnvironmentConfig,
    build_claude_config_manager,
    build_codex_config_manager,
)


def test_load_environments_empty(tmp_path):
    """Missing config files should return no environments."""
    manager = build_claude_config_manager(tmp_path / ".claude")
    assert manager.load_environments() == {}


def test_load_claude_environments_valid(tmp_path):
    """Claude manager should load Claude entries from its own file."""
    manager = build_claude_config_manager(tmp_path / ".claude")
    manager.config_path.parent.mkdir(parents=True, exist_ok=True)
    manager.config_path.write_text(
        yaml.safe_dump(
            {
                "env1": {
                    "url": "https://example.com",
                    "token": "token123",
                    "model": "model1",
                    "timeout": 5000,
                    "tokens": 10000,
                },
                "env2": {
                    "url": "https://example2.com",
                    "token": "token456",
                    "fast": "fast-model",
                },
            }
        ),
        encoding="utf-8",
    )

    environments = manager.load_environments()

    assert len(environments) == 2
    assert environments["env1"].url == "https://example.com"
    assert environments["env1"].token == "token123"
    assert environments["env1"].model == "model1"
    assert environments["env1"].timeout == 5000
    assert environments["env1"].tokens == 10000
    assert environments["env2"].fast == "fast-model"


def test_load_environments_token_list(tmp_path):
    """Secret lists should use the first entry."""
    manager = build_claude_config_manager(tmp_path / ".claude")
    manager.config_path.parent.mkdir(parents=True, exist_ok=True)
    manager.config_path.write_text(
        yaml.safe_dump({"env1": {"url": "https://example.com", "token": ["token1", "token2"]}}),
        encoding="utf-8",
    )

    environments = manager.load_environments()
    assert environments["env1"].token == "token1"


def test_load_codex_environments_valid(tmp_path):
    """Codex manager should load Codex entries from `cw.yaml`."""
    manager = build_codex_config_manager(tmp_path / ".codex")
    manager.config_path.parent.mkdir(parents=True, exist_ok=True)
    manager.config_path.write_text(
        yaml.safe_dump(
            {
                "relay": {
                    "auth_mode": "apikey",
                    "base_url": "https://relay.example.com/v1",
                    "api_key": "sk-test-123",
                    "model": "gpt-5",
                },
                "official": {
                    "auth_mode": "login",
                    "model": "gpt-5.4",
                },
            }
        ),
        encoding="utf-8",
    )

    environments = manager.load_environments()

    relay = environments["relay"]
    assert relay.normalized_tool == "codex"
    assert relay.normalized_auth_mode == "apikey"
    assert relay.codex_base_url == "https://relay.example.com/v1"
    assert relay.codex_api_key == "sk-test-123"

    official = environments["official"]
    assert official.normalized_tool == "codex"
    assert official.normalized_auth_mode == "login"


def test_load_environments_ignore_wrong_tool_for_file(tmp_path):
    """Tool-specific config files should ignore entries for other tools."""
    manager = build_claude_config_manager(tmp_path / ".claude")
    manager.config_path.parent.mkdir(parents=True, exist_ok=True)
    manager.config_path.write_text(
        yaml.safe_dump(
            {
                "claude-env": {"url": "https://example.com", "token": "token123"},
                "codex-env": {"tool": "codex", "auth_mode": "login", "model": "gpt-5.4"},
            }
        ),
        encoding="utf-8",
    )

    environments = manager.load_environments()

    assert "claude-env" in environments
    assert "codex-env" not in environments


def test_load_settings_empty(tmp_path):
    """Missing settings.json should return an empty dict."""
    manager = build_claude_config_manager(tmp_path / ".claude")
    assert manager.load_settings() == {}


def test_load_settings_valid(tmp_path):
    """Settings should deserialize normally."""
    manager = build_claude_config_manager(tmp_path / ".claude")
    manager.settings_path.parent.mkdir(parents=True, exist_ok=True)
    manager.settings_path.write_text(
        json.dumps({"env": {"KEY": "value"}, "model": "opus"}),
        encoding="utf-8",
    )

    assert manager.load_settings() == {"env": {"KEY": "value"}, "model": "opus"}


def test_save_settings(tmp_path):
    """Saving settings should write JSON to disk."""
    manager = build_claude_config_manager(tmp_path / ".claude")

    manager.save_settings({"key": "value"})

    assert json.loads(manager.settings_path.read_text(encoding="utf-8")) == {"key": "value"}


def test_update_env_in_settings(tmp_path):
    """Updating settings should preserve unrelated fields."""
    manager = build_claude_config_manager(tmp_path / ".claude")
    manager.save_settings({"model": "opus", "statusLine": {"type": "command"}})

    env_config = EnvironmentConfig(
        url="https://example.com",
        token="token123",
        model="model1",
        fast="fast1",
        timeout=5000,
        tokens=10000,
    )

    manager.update_env_in_settings("env1", env_config)
    settings = manager.load_settings()

    assert settings["model"] == "opus"
    assert settings["statusLine"] == {"type": "command"}
    assert settings["env"]["ANTHROPIC_BASE_URL"] == "https://example.com"
    assert settings["env"]["ANTHROPIC_AUTH_TOKEN"] == "token123"
    assert settings["env"]["ANTHROPIC_MODEL"] == "model1"
    assert settings["env"]["ANTHROPIC_SMALL_FAST_MODEL"] == "fast1"
    assert settings["env"]["BASH_DEFAULT_TIMEOUT_MS"] == "5000"
    assert settings["env"]["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == "10000"
    assert settings["codewitch"]["claude-code"] == "env1"


def test_clear_env_from_settings(tmp_path):
    """Clearing settings should keep unrelated fields."""
    manager = build_claude_config_manager(tmp_path / ".claude")
    manager.save_settings(
        {
            "env": {"KEY": "value"},
            "model": "opus",
            "codewitch": {"claude-code": "env1", "codex": "official"},
        }
    )

    manager.clear_env_from_settings()
    settings = manager.load_settings()

    assert "env" not in settings
    assert settings["model"] == "opus"
    assert settings["codewitch"] == {"codex": "official"}


def test_get_current_env_from_settings(tmp_path):
    """Claude settings should resolve back to the active environment name."""
    manager = build_claude_config_manager(tmp_path / ".claude")
    manager.config_path.parent.mkdir(parents=True, exist_ok=True)
    manager.config_path.write_text(
        yaml.safe_dump(
            {
                "env1": {"url": "https://example1.com", "token": "token1"},
                "env2": {"url": "https://example2.com", "token": "token2"},
            }
        ),
        encoding="utf-8",
    )

    manager.save_settings(
        {
            "env": {
                "ANTHROPIC_BASE_URL": "https://example1.com",
                "ANTHROPIC_AUTH_TOKEN": "token1",
            }
        }
    )

    assert manager.get_current_env_from_settings() == "env1"

    manager.clear_env_from_settings()
    assert manager.get_current_env_from_settings() is None
