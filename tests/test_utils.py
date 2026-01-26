"""Tests for utils.py."""

from src.config import EnvironmentConfig, ConfigManager
from src.utils import (
    format_env_vars_for_display,
    format_env_vars_for_export,
)


def test_map_config_to_env_vars_full():
    """Test mapping with all fields present."""
    env_config = EnvironmentConfig(
        url="https://example.com",
        token="token123",
        model="model1",
        fast="fast1",
        timeout=5000,
        tokens=10000,
    )

    env_vars = ConfigManager._map_config_to_env_vars(env_config)

    assert env_vars["ANTHROPIC_BASE_URL"] == "https://example.com"
    assert env_vars["ANTHROPIC_AUTH_TOKEN"] == "token123"
    assert env_vars["ANTHROPIC_MODEL"] == "model1"
    assert env_vars["ANTHROPIC_SMALL_FAST_MODEL"] == "fast1"
    assert env_vars["BASH_DEFAULT_TIMEOUT_MS"] == "5000"
    assert env_vars["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == "10000"

    # Check backward compatibility fields
    assert env_vars["ANTHROPIC_DEFAULT_OPUS_MODEL"] == "model1"
    assert env_vars["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "model1"
    assert env_vars["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == "fast1"


def test_map_config_to_env_vars_minimal():
    """Test mapping with only required fields."""
    env_config = EnvironmentConfig(
        url="https://example.com",
        token="token123",
    )

    env_vars = ConfigManager._map_config_to_env_vars(env_config)

    assert env_vars["ANTHROPIC_BASE_URL"] == "https://example.com"
    assert env_vars["ANTHROPIC_AUTH_TOKEN"] == "token123"
    assert "ANTHROPIC_MODEL" not in env_vars
    assert "ANTHROPIC_SMALL_FAST_MODEL" not in env_vars
    assert "BASH_DEFAULT_TIMEOUT_MS" not in env_vars
    assert env_vars["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == "48000"  # default


def test_map_config_to_env_vars_partial():
    """Test mapping with some optional fields."""
    env_config = EnvironmentConfig(
        url="https://example.com",
        token="token123",
        model="model1",
        timeout=30000,
    )

    env_vars = ConfigManager._map_config_to_env_vars(env_config)

    assert env_vars["ANTHROPIC_BASE_URL"] == "https://example.com"
    assert env_vars["ANTHROPIC_AUTH_TOKEN"] == "token123"
    assert env_vars["ANTHROPIC_MODEL"] == "model1"
    assert "ANTHROPIC_SMALL_FAST_MODEL" not in env_vars
    assert env_vars["BASH_DEFAULT_TIMEOUT_MS"] == "30000"
    assert env_vars["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == "48000"


def test_format_env_vars_for_display():
    """Test formatting for display with token masking."""
    env_vars = {
        "ANTHROPIC_BASE_URL": "https://example.com",
        "ANTHROPIC_AUTH_TOKEN": "sk-ant-api03-abcdefghijklmnop",
        "OTHER_VAR": "value",
    }

    formatted = format_env_vars_for_display(env_vars)

    assert "ANTHROPIC_BASE_URL=https://example.com" in formatted
    assert "sk-ant-api03-abcdefghijklmnop" not in formatted  # Should be masked
    assert "sk-ant-a...mnop" in formatted
    assert "OTHER_VAR=value" in formatted


def test_format_env_vars_for_export():
    """Test formatting as shell export commands."""
    env_vars = {
        "ANTHROPIC_BASE_URL": "https://example.com",
        "ANTHROPIC_AUTH_TOKEN": "token123",
    }

    formatted = format_env_vars_for_export(env_vars)

    assert "export ANTHROPIC_BASE_URL='https://example.com'" in formatted
    assert "export ANTHROPIC_AUTH_TOKEN='token123'" in formatted

    # Test escaping single quotes
    env_vars_with_quote = {"TEST": "value'with'quote"}
    formatted = format_env_vars_for_export(env_vars_with_quote)
    assert "export TEST='value'\"'\"'with'\"'\"'quote'" in formatted