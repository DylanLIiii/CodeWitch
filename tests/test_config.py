"""Tests for config.py."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from src.config import ConfigManager, EnvironmentConfig


@pytest.fixture
def temp_claude_dir():
    """Create a temporary .claude directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        claude_dir = Path(tmpdir) / ".claude"
        claude_dir.mkdir()
        yield claude_dir


@pytest.fixture
def config_manager(temp_claude_dir):
    """Create a ConfigManager with temporary directory."""
    manager = ConfigManager()
    # Override the paths to use our temporary directory
    manager.claude_dir = temp_claude_dir
    manager.cc_yaml_path = temp_claude_dir / "cc.yaml"
    manager.settings_json_path = temp_claude_dir / "settings.json"
    return manager


def test_load_environments_empty(config_manager):
    """Test loading environments when cc.yaml doesn't exist."""
    environments = config_manager.load_environments()
    assert environments == {}


def test_load_environments_valid(config_manager):
    """Test loading valid environments from cc.yaml."""
    # Create a sample cc.yaml
    cc_yaml_content = {
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

    with open(config_manager.cc_yaml_path, 'w') as f:
        yaml.dump(cc_yaml_content, f)

    environments = config_manager.load_environments()

    assert len(environments) == 2
    assert "env1" in environments
    assert "env2" in environments

    env1 = environments["env1"]
    assert env1.url == "https://example.com"
    assert env1.token == "token123"
    assert env1.model == "model1"
    assert env1.timeout == 5000
    assert env1.tokens == 10000
    assert env1.fast is None

    env2 = environments["env2"]
    assert env2.url == "https://example2.com"
    assert env2.token == "token456"
    assert env2.model is None
    assert env2.fast == "fast-model"


def test_load_environments_token_list(config_manager):
    """Test loading environment with token as list."""
    cc_yaml_content = {
        "env1": {
            "url": "https://example.com",
            "token": ["token1", "token2"],
        },
    }

    with open(config_manager.cc_yaml_path, 'w') as f:
        yaml.dump(cc_yaml_content, f)

    environments = config_manager.load_environments()
    env1 = environments["env1"]

    # Should use first token from list
    assert env1.token == "token1"


def test_load_settings_empty(config_manager):
    """Test loading settings when settings.json doesn't exist."""
    settings = config_manager.load_settings()
    assert settings == {}


def test_load_settings_valid(config_manager):
    """Test loading valid settings.json."""
    settings_content = {
        "env": {"KEY": "value"},
        "model": "opus",
    }

    with open(config_manager.settings_json_path, 'w') as f:
        json.dump(settings_content, f)

    settings = config_manager.load_settings()
    assert settings == settings_content


def test_save_settings(config_manager):
    """Test saving settings.json."""
    settings_content = {"key": "value"}

    config_manager.save_settings(settings_content)

    with open(config_manager.settings_json_path, 'r') as f:
        loaded = json.load(f)

    assert loaded == settings_content


def test_update_env_in_settings(config_manager):
    """Test updating env object in settings.json."""
    # Create initial settings
    initial_settings = {
        "model": "opus",
        "statusLine": {"type": "command"},
    }
    config_manager.save_settings(initial_settings)

    # Create environment config
    env_config = EnvironmentConfig(
        url="https://example.com",
        token="token123",
        model="model1",
        fast="fast1",
        timeout=5000,
        tokens=10000,
    )

    config_manager.update_env_in_settings("env1", env_config)

    settings = config_manager.load_settings()

    # Should preserve existing fields
    assert "model" in settings
    assert "statusLine" in settings

    # Should have env object
    assert "env" in settings
    env_vars = settings["env"]

    # Check required fields
    assert env_vars["ANTHROPIC_BASE_URL"] == "https://example.com"
    assert env_vars["ANTHROPIC_AUTH_TOKEN"] == "token123"

    # Check optional fields
    assert env_vars["ANTHROPIC_MODEL"] == "model1"
    assert env_vars["ANTHROPIC_SMALL_FAST_MODEL"] == "fast1"
    assert env_vars["BASH_DEFAULT_TIMEOUT_MS"] == "5000"
    assert env_vars["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == "10000"


def test_clear_env_from_settings(config_manager):
    """Test clearing env object from settings.json."""
    # Create settings with env
    initial_settings = {
        "env": {"KEY": "value"},
        "model": "opus",
    }
    config_manager.save_settings(initial_settings)

    config_manager.clear_env_from_settings()

    settings = config_manager.load_settings()
    assert "env" not in settings
    assert "model" in settings


def test_get_current_env_from_settings(config_manager):
    """Test determining current environment from settings.json."""
    # Create cc.yaml
    cc_yaml_content = {
        "env1": {
            "url": "https://example1.com",
            "token": "token1",
        },
        "env2": {
            "url": "https://example2.com",
            "token": "token2",
        },
    }
    with open(config_manager.cc_yaml_path, 'w') as f:
        yaml.dump(cc_yaml_content, f)

    # Create settings with env from env1
    settings_content = {
        "env": {
            "ANTHROPIC_BASE_URL": "https://example1.com",
            "ANTHROPIC_AUTH_TOKEN": "token1",
        }
    }
    config_manager.save_settings(settings_content)

    current_env = config_manager.get_current_env_from_settings()
    assert current_env == "env1"

    # Test with no env object
    config_manager.clear_env_from_settings()
    current_env = config_manager.get_current_env_from_settings()
    assert current_env is None

    # Test with env but no matching URL
    settings_content = {
        "env": {
            "ANTHROPIC_BASE_URL": "https://unknown.com",
        }
    }
    config_manager.save_settings(settings_content)
    current_env = config_manager.get_current_env_from_settings()
    assert current_env is None