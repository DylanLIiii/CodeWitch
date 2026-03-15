"""Tests for env_manager.py."""

import json
from pathlib import Path
from unittest.mock import Mock

import yaml

from src.config import EnvironmentConfig
from src.env_manager import ClaudeEnvManager, CodexEnvManager


def test_set_local_env_claude(tmp_path):
    """Claude local switching should write terminal-local state."""
    manager = ClaudeEnvManager(tmp_path / ".claude")
    manager.config_manager.config_path.parent.mkdir(parents=True, exist_ok=True)
    manager.config_manager.config_path.write_text(
        yaml.safe_dump(
            {
                "testenv": {
                    "url": "https://example.com",
                    "token": "token123",
                    "model": "model1",
                    "fast": "fast1",
                    "timeout": 5000,
                    "tokens": 10000,
                }
            }
        ),
        encoding="utf-8",
    )
    manager.config_manager.clear_env_from_settings = Mock()

    env_vars, export_commands = manager.set_local_env("testenv")

    assert env_vars["ANTHROPIC_BASE_URL"] == "https://example.com"
    assert env_vars["ANTHROPIC_AUTH_TOKEN"] == "token123"
    assert "export ANTHROPIC_BASE_URL=" in export_commands
    manager.config_manager.clear_env_from_settings.assert_called_once()

    local_state = json.loads(manager.local_state_path.read_text(encoding="utf-8"))
    assert local_state["tool"] == "claude-code"
    assert local_state["mode"] == "local"


def test_set_global_env_claude(tmp_path):
    """Claude global switching should update settings.json."""
    manager = ClaudeEnvManager(tmp_path / ".claude")
    manager.config_manager.config_path.parent.mkdir(parents=True, exist_ok=True)
    manager.config_manager.config_path.write_text(
        yaml.safe_dump({"testenv": {"url": "https://example.com", "token": "token123", "model": "model1"}}),
        encoding="utf-8",
    )
    manager.config_manager.update_env_in_settings = Mock()

    env_vars, export_commands = manager.set_global_env("testenv")

    assert env_vars["ANTHROPIC_BASE_URL"] == "https://example.com"
    assert export_commands == ""
    manager.config_manager.update_env_in_settings.assert_called_once()


def test_set_local_env_codex(tmp_path):
    """Codex local switching should generate a local CODEX_HOME."""
    manager = CodexEnvManager(tmp_path / ".codex")
    manager.config_manager.config_path.parent.mkdir(parents=True, exist_ok=True)
    manager.config_manager.config_path.write_text(
        yaml.safe_dump(
            {
                "codex": {
                    "auth_mode": "apikey",
                    "base_url": "https://relay.example.com/v1",
                    "api_key": "sk-test-123",
                    "model": "gpt-5",
                }
            }
        ),
        encoding="utf-8",
    )
    manager.codex_manager = Mock()
    manager.codex_manager.create_local_home.return_value = Path("/tmp/codex-home")
    manager.codex_manager.build_local_env_vars.return_value = {
        "CODEX_HOME": "/tmp/codex-home",
        "OPENAI_API_KEY": "sk-test-123",
    }

    env_vars, export_commands = manager.set_local_env("codex")

    assert env_vars["CODEX_HOME"] == "/tmp/codex-home"
    assert "export CODEX_HOME='/tmp/codex-home'" in export_commands
    manager.codex_manager.create_local_home.assert_called_once()

    local_state = json.loads(manager.local_state_path.read_text(encoding="utf-8"))
    assert local_state["tool"] == "codex"
    assert local_state["mode"] == "local"


def test_set_global_env_codex(tmp_path):
    """Codex global switching should delegate to CodexManager."""
    manager = CodexEnvManager(tmp_path / ".codex")
    manager.config_manager.config_path.parent.mkdir(parents=True, exist_ok=True)
    manager.config_manager.config_path.write_text(
        yaml.safe_dump({"official": {"auth_mode": "login", "model": "gpt-5.4"}}),
        encoding="utf-8",
    )
    manager.codex_manager = Mock()
    manager.codex_manager.build_runtime_preview.return_value = {
        "CODEX_AUTH_MODE": "login",
        "CODEX_MODEL_PROVIDER": "openai",
    }

    env_vars, export_commands = manager.set_global_env("official")

    assert env_vars["CODEX_AUTH_MODE"] == "login"
    assert export_commands == ""
    manager.codex_manager.apply_global_env.assert_called_once()


def test_unset_local_claude(tmp_path):
    """Claude unset local should remove the state file."""
    manager = ClaudeEnvManager(tmp_path / ".claude")
    manager.local_state_path.parent.mkdir(parents=True, exist_ok=True)
    manager.local_state_path.write_text(json.dumps({"env_name": "test"}), encoding="utf-8")

    manager.unset_local()

    assert not manager.local_state_path.exists()


def test_unset_global_codex(tmp_path):
    """Codex unset global should clear both global and local state."""
    manager = CodexEnvManager(tmp_path / ".codex")
    manager.local_state_path.parent.mkdir(parents=True, exist_ok=True)
    manager.local_state_path.write_text(
        json.dumps({"env_name": "test", "env_vars": {"CODEX_HOME": "/tmp/not-managed"}}),
        encoding="utf-8",
    )
    manager.codex_manager = Mock()

    manager.unset_global()

    manager.codex_manager.clear_global_env.assert_called_once()
    assert not manager.local_state_path.exists()


def test_get_current_env_local_claude(tmp_path):
    """Claude current should prefer local state."""
    manager = ClaudeEnvManager(tmp_path / ".claude")
    manager.config_manager.config_path.parent.mkdir(parents=True, exist_ok=True)
    manager.config_manager.config_path.write_text(
        yaml.safe_dump({"testenv": {"url": "https://example.com", "token": "token123"}}),
        encoding="utf-8",
    )
    manager.local_state_path.parent.mkdir(parents=True, exist_ok=True)
    manager.local_state_path.write_text(
        json.dumps(
            {
                "env_name": "testenv",
                "env_vars": {"ANTHROPIC_BASE_URL": "https://example.com"},
                "mode": "local",
                "tool": "claude-code",
            }
        ),
        encoding="utf-8",
    )

    current = manager.get_current_env()

    assert current is not None
    assert current["env_name"] == "testenv"
    assert current["mode"] == "local"
    assert current["tool"] == "claude-code"


def test_get_current_env_global_codex(tmp_path):
    """Codex current should resolve through CodexManager."""
    manager = CodexEnvManager(tmp_path / ".codex")
    manager.config_manager.config_path.parent.mkdir(parents=True, exist_ok=True)
    manager.config_manager.config_path.write_text(
        yaml.safe_dump({"official": {"auth_mode": "login", "model": "gpt-5.4"}}),
        encoding="utf-8",
    )
    manager.codex_manager = Mock()
    manager.codex_manager.get_current_env_name.return_value = "official"
    manager.codex_manager.build_runtime_preview.return_value = {
        "CODEX_AUTH_MODE": "login",
        "CODEX_MODEL_PROVIDER": "openai",
    }

    current = manager.get_current_env()

    assert current is not None
    assert current["env_name"] == "official"
    assert current["mode"] == "global"
    assert current["tool"] == "codex"


def test_get_env_info_codex(tmp_path):
    """Codex info should include runtime preview."""
    manager = CodexEnvManager(tmp_path / ".codex")
    manager.config_manager.config_path.parent.mkdir(parents=True, exist_ok=True)
    manager.config_manager.config_path.write_text(
        yaml.safe_dump(
            {
                "codex": {
                    "auth_mode": "apikey",
                    "base_url": "https://relay.example.com/v1",
                    "api_key": "sk-test-123",
                    "model": "gpt-5",
                }
            }
        ),
        encoding="utf-8",
    )
    manager.codex_manager = Mock()
    manager.codex_manager.build_runtime_preview.return_value = {
        "CODEX_AUTH_MODE": "apikey",
        "CODEX_BASE_URL": "https://relay.example.com/v1",
    }

    info = manager.get_env_info("codex")

    assert info is not None
    assert info["name"] == "codex"
    assert info["tool"] == "codex"
    assert "env_vars" in info
