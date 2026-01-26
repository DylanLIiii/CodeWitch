"""Tests for env_manager.py."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.config import EnvironmentConfig
from src.env_manager import EnvManager


@pytest.fixture
def temp_claude_dir():
    """Create a temporary .claude directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        claude_dir = Path(tmpdir) / ".claude"
        claude_dir.mkdir()
        yield claude_dir


@pytest.fixture
def env_manager(temp_claude_dir):
    """Create an EnvManager with temporary directory."""
    manager = EnvManager()
    # Override config manager's claude_dir
    manager.config_manager.claude_dir = temp_claude_dir
    manager.config_manager.cc_yaml_path = temp_claude_dir / "cc.yaml"
    manager.config_manager.settings_json_path = temp_claude_dir / "settings.json"
    manager.local_state_path = temp_claude_dir / "cw_current.json"
    return manager


def test_set_local_env(env_manager):
    """Test setting local environment."""
    # Mock environments
    env_config = EnvironmentConfig(
        url="https://example.com",
        token="token123",
        model="model1",
        fast="fast1",
        timeout=5000,
        tokens=10000,
    )
    env_manager.config_manager.load_environments = Mock(return_value={
        "testenv": env_config
    })
    env_manager.config_manager.clear_env_from_settings = Mock()

    env_vars, export_commands = env_manager.set_local_env("testenv")

    # Check returned values
    assert env_vars["ANTHROPIC_BASE_URL"] == "https://example.com"
    assert env_vars["ANTHROPIC_AUTH_TOKEN"] == "token123"
    assert env_vars["ANTHROPIC_MODEL"] == "model1"
    assert env_vars["ANTHROPIC_SMALL_FAST_MODEL"] == "fast1"
    assert env_vars["BASH_DEFAULT_TIMEOUT_MS"] == "5000"
    assert env_vars["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == "10000"

    assert "export ANTHROPIC_BASE_URL=" in export_commands

    # Check that local state file was created
    assert env_manager.local_state_path.exists()
    with open(env_manager.local_state_path, 'r') as f:
        local_state = json.load(f)
        assert local_state["env_name"] == "testenv"
        assert local_state["env_vars"] == env_vars

    # Check that global env was cleared
    env_manager.config_manager.clear_env_from_settings.assert_called_once()


def test_set_local_env_not_found(env_manager):
    """Test setting non-existent environment."""
    env_manager.config_manager.load_environments = Mock(return_value={})

    with pytest.raises(ValueError, match="Environment 'nonexistent' not found"):
        env_manager.set_local_env("nonexistent")


def test_set_global_env(env_manager):
    """Test setting global environment."""
    env_config = EnvironmentConfig(
        url="https://example.com",
        token="token123",
        model="model1",
    )
    env_manager.config_manager.load_environments = Mock(return_value={
        "testenv": env_config
    })
    env_manager.config_manager.update_env_in_settings = Mock()

    env_vars, export_commands = env_manager.set_global_env("testenv")

    # Check returned values
    assert env_vars["ANTHROPIC_BASE_URL"] == "https://example.com"
    assert env_vars["ANTHROPIC_AUTH_TOKEN"] == "token123"
    assert env_vars["ANTHROPIC_MODEL"] == "model1"

    assert "export ANTHROPIC_BASE_URL=" in export_commands

    # Check that local state file was created
    assert env_manager.local_state_path.exists()

    # Check that settings were updated
    env_manager.config_manager.update_env_in_settings.assert_called_once_with("testenv", env_config)


def test_unset_local(env_manager):
    """Test clearing local environment."""
    # Create local state file
    env_manager.local_state_path.parent.mkdir(exist_ok=True)
    with open(env_manager.local_state_path, 'w') as f:
        json.dump({"env_name": "test"}, f)

    assert env_manager.local_state_path.exists()

    env_manager.unset_local()

    assert not env_manager.local_state_path.exists()


def test_unset_global(env_manager):
    """Test clearing global environment."""
    env_manager.config_manager.clear_env_from_settings = Mock()

    # Create local state file
    env_manager.local_state_path.parent.mkdir(exist_ok=True)
    with open(env_manager.local_state_path, 'w') as f:
        json.dump({"env_name": "test"}, f)

    env_manager.unset_global()

    env_manager.config_manager.clear_env_from_settings.assert_called_once()
    assert not env_manager.local_state_path.exists()


def test_get_current_env_local(env_manager):
    """Test getting current environment (local)."""
    # Create local state file
    env_config = EnvironmentConfig(
        url="https://example.com",
        token="token123",
    )
    env_manager.config_manager.load_environments = Mock(return_value={
        "testenv": env_config
    })

    local_state = {
        "env_name": "testenv",
        "env_vars": {"ANTHROPIC_BASE_URL": "https://example.com"}
    }
    env_manager.local_state_path.parent.mkdir(exist_ok=True)
    with open(env_manager.local_state_path, 'w') as f:
        json.dump(local_state, f)

    current = env_manager.get_current_env()

    assert current is not None
    assert current["env_name"] == "testenv"
    assert current["mode"] == "local"
    assert "env_vars" in current


def test_get_current_env_global(env_manager):
    """Test getting current environment (global)."""
    # No local state
    env_config = EnvironmentConfig(
        url="https://example.com",
        token="token123",
    )
    env_manager.config_manager.load_environments = Mock(return_value={
        "testenv": env_config
    })
    env_manager.config_manager.get_current_env_from_settings = Mock(return_value="testenv")

    current = env_manager.get_current_env()

    assert current is not None
    assert current["env_name"] == "testenv"
    assert current["mode"] == "global"
    assert "env_vars" in current


def test_get_current_env_none(env_manager):
    """Test getting current environment when none is active."""
    # No local state, no global env
    env_manager.config_manager.get_current_env_from_settings = Mock(return_value=None)

    current = env_manager.get_current_env()

    assert current is None


def test_get_env_info(env_manager):
    """Test getting environment info."""
    env_config = EnvironmentConfig(
        url="https://example.com",
        token="token123",
        model="model1",
    )
    env_manager.config_manager.load_environments = Mock(return_value={
        "testenv": env_config
    })

    info = env_manager.get_env_info("testenv")

    assert info is not None
    assert info["name"] == "testenv"
    assert "config" in info
    assert "env_vars" in info


def test_get_env_info_not_found(env_manager):
    """Test getting info for non-existent environment."""
    env_manager.config_manager.load_environments = Mock(return_value={})

    info = env_manager.get_env_info("nonexistent")

    assert info is None