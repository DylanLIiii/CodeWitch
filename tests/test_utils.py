"""Tests for utils.py."""

from src.config import ConfigManager, EnvironmentConfig
from src.utils import format_env_vars_for_display, format_env_vars_for_export


def test_map_config_to_env_vars_full():
    """Test mapping with all Claude fields present."""
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
    assert env_vars["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == "fast1"
    assert env_vars["BASH_DEFAULT_TIMEOUT_MS"] == "5000"
    assert env_vars["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == "10000"


def test_map_config_to_env_vars_with_model_aliases():
    """Alias mappings should emit the three default model environment variables."""
    env_config = EnvironmentConfig(
        models={
            "opus": "claude-opus-4-6",
            "sonnet": "claude-sonnet-4-6",
            "haiku": "claude-haiku-4-5",
        },
    )

    env_vars = ConfigManager._map_config_to_env_vars(env_config)

    assert env_vars["ANTHROPIC_DEFAULT_OPUS_MODEL"] == "claude-opus-4-6"
    assert env_vars["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "claude-sonnet-4-6"
    assert env_vars["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == "claude-haiku-4-5"
    assert env_vars["ANTHROPIC_SMALL_FAST_MODEL"] == "claude-haiku-4-5"


def test_format_env_vars_for_display_masks_tokens_and_api_keys():
    """Display formatting should mask secrets and show unset values."""
    env_vars = {
        "ANTHROPIC_AUTH_TOKEN": "sk-ant-api03-abcdefghijklmnop",
        "OPENAI_API_KEY": "sk-openai-abcdefghijklmnop",
        "CODEX_HOME": "/tmp/codex-home",
        "OPENAI_UNUSED": None,
    }

    formatted = format_env_vars_for_display(env_vars)

    assert "sk-ant-api03-abcdefghijklmnop" not in formatted
    assert "sk-openai-abcdefghijklmnop" not in formatted
    assert "CODEX_HOME=/tmp/codex-home" in formatted
    assert "OPENAI_UNUSED=<unset>" in formatted


def test_format_env_vars_for_export_supports_unset():
    """Shell export formatting should emit unset commands for None values."""
    env_vars = {
        "CODEX_HOME": "/tmp/codex-home",
        "OPENAI_API_KEY": None,
    }

    formatted = format_env_vars_for_export(env_vars)

    assert "export CODEX_HOME='/tmp/codex-home'" in formatted
    assert "unset OPENAI_API_KEY" in formatted


def test_format_env_vars_for_export_escapes_single_quotes():
    """Shell export formatting should escape single quotes safely."""
    formatted = format_env_vars_for_export({"TEST": "value'with'quote"})
    assert "export TEST='value'\"'\"'with'\"'\"'quote'" in formatted
