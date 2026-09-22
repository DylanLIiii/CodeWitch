"""Tests for config.py."""

import json

import yaml

from src.config import (
    EnvironmentConfig,
    build_claude_config_manager,
    build_codex_config_manager,
    map_claude_config_to_env_vars,
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
    assert settings["env"]["ANTHROPIC_MODEL"] == "sonnet"
    assert settings["env"]["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "model1"
    assert settings["env"]["ANTHROPIC_SMALL_FAST_MODEL"] == "fast1"
    assert settings["env"]["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == "fast1"
    assert settings["env"]["BASH_DEFAULT_TIMEOUT_MS"] == "5000"
    assert settings["env"]["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == "10000"
    assert settings["codewitch"]["claude-code"] == "env1"


def test_map_claude_model_aliases():
    """Claude alias mappings should map to official environment variables."""
    env_config = EnvironmentConfig(
        model="sonnet",
        models={
            "opus": "claude-opus-4-6",
            "sonnet": "claude-sonnet-4-6",
            "haiku": "claude-haiku-4-5",
        },
    )

    env_vars = map_claude_config_to_env_vars(env_config)

    assert env_vars["ANTHROPIC_MODEL"] == "sonnet"
    assert env_vars["ANTHROPIC_DEFAULT_OPUS_MODEL"] == "claude-opus-4-6"
    assert env_vars["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "claude-sonnet-4-6"
    assert env_vars["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == "claude-haiku-4-5"
    assert env_vars["ANTHROPIC_SMALL_FAST_MODEL"] == "claude-haiku-4-5"


def test_map_claude_model_alias_field_override():
    """Top-level alias fields should override values from `models`."""
    env_config = EnvironmentConfig(
        models={"haiku": "haiku-from-models"},
        haiku="haiku-top-level",
        fast="fast-top-level",
    )

    env_vars = map_claude_config_to_env_vars(env_config)

    assert env_vars["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == "haiku-top-level"
    assert env_vars["ANTHROPIC_SMALL_FAST_MODEL"] == "fast-top-level"


def test_map_claude_subagent_and_effort_env_vars():
    """Claude Code session env vars for subagent model and effort level."""
    env_config = EnvironmentConfig(
        subagent_model="deepseek-v4-flash",
        effort_level="max",
    )
    env_vars = map_claude_config_to_env_vars(env_config)
    assert env_vars["CLAUDE_CODE_SUBAGENT_MODEL"] == "deepseek-v4-flash"
    assert env_vars["CLAUDE_CODE_EFFORT_LEVEL"] == "max"


def test_map_claude_subagent_and_effort_yaml_aliases():
    """cw.yaml-style alternate keys should populate subagent and effort fields."""
    env_config = EnvironmentConfig.model_validate(
        {
            "tool": "claude-code",
            "claude_code_subagent_model": "custom-id",
            "claude_code_effort_level": "auto",
        }
    )
    env_vars = map_claude_config_to_env_vars(env_config)
    assert env_vars["CLAUDE_CODE_SUBAGENT_MODEL"] == "custom-id"
    assert env_vars["CLAUDE_CODE_EFFORT_LEVEL"] == "auto"


def test_clear_env_from_settings(tmp_path):
    """Clearing settings should keep unmanaged env vars and unrelated fields."""
    manager = build_claude_config_manager(tmp_path / ".claude")
    manager.save_settings(
        {
            "env": {"KEY": "value", "ANTHROPIC_MODEL": "sonnet"},
            "model": "opus",
            "codewitch": {"claude-code": "env1", "codex": "official"},
        }
    )

    manager.clear_env_from_settings()
    settings = manager.load_settings()

    assert settings["env"] == {"KEY": "value"}
    assert settings["model"] == "opus"
    assert settings["codewitch"] == {"codex": "official"}


def test_update_env_in_settings_merges_env(tmp_path):
    """Applying an environment should merge over user-managed env vars."""
    manager = build_claude_config_manager(tmp_path / ".claude")
    manager.save_settings(
        {
            "env": {
                "KEY": "value",
                "ANTHROPIC_MODEL": "stale-model",
            }
        }
    )

    env_config = EnvironmentConfig(url="https://example.com", token="token123")
    manager.update_env_in_settings("env1", env_config)
    settings = manager.load_settings()

    assert settings["env"]["KEY"] == "value"
    assert settings["env"]["ANTHROPIC_BASE_URL"] == "https://example.com"
    assert "ANTHROPIC_MODEL" not in settings["env"]


def test_opaque_model_id_pins_to_sonnet():
    """Unrecognized provider IDs should ride on the sonnet alias."""
    env_vars = map_claude_config_to_env_vars(EnvironmentConfig(model="glm-4.7"))

    assert env_vars["ANTHROPIC_MODEL"] == "sonnet"
    assert env_vars["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "glm-4.7"


def test_opaque_model_id_respects_existing_sonnet_pin():
    """An opaque model takes the next free alias slot when sonnet is taken."""
    env_vars = map_claude_config_to_env_vars(
        EnvironmentConfig(model="glm-4.7", models={"sonnet": "other-model"})
    )

    assert env_vars["ANTHROPIC_MODEL"] == "opus"
    assert env_vars["ANTHROPIC_DEFAULT_OPUS_MODEL"] == "glm-4.7"
    assert env_vars["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "other-model"


def test_opaque_model_id_pins_when_sonnet_pin_is_same():
    """A sonnet pin holding the same wire ID should not block pinning."""
    env_vars = map_claude_config_to_env_vars(
        EnvironmentConfig(
            model="kimi-for-coding",
            models={"sonnet": "kimi-for-coding", "haiku": "kimi-for-coding"},
        )
    )

    assert env_vars["ANTHROPIC_MODEL"] == "sonnet"
    assert env_vars["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "kimi-for-coding"


def test_sonnet_pin_without_model_defaults_to_sonnet():
    """A sonnet pin alone should set ANTHROPIC_MODEL to the sonnet alias."""
    env_vars = map_claude_config_to_env_vars(
        EnvironmentConfig(models={"sonnet": "glm-5.2[1m]", "haiku": "glm-4.5-air"})
    )

    assert env_vars["ANTHROPIC_MODEL"] == "sonnet"
    assert env_vars["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "glm-5.2[1m]"


def test_classifier_via_fast_routes_sonnet_pin():
    """classifier_via: fast should aim the sonnet pin at the haiku/fast model."""
    env_vars = map_claude_config_to_env_vars(
        EnvironmentConfig(
            fast="glm-4.5-air",
            classifier_via="fast",
            models={"opus": "glm-5.3", "haiku": "glm-4.5-air"},
        )
    )

    assert env_vars["ANTHROPIC_MODEL"] == "opus"
    assert env_vars["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "glm-4.5-air"
    assert env_vars["ANTHROPIC_DEFAULT_OPUS_MODEL"] == "glm-5.3"


def test_classifier_via_explicit_sonnet_wins():
    """An explicit models.sonnet pin takes precedence over classifier_via."""
    env_vars = map_claude_config_to_env_vars(
        EnvironmentConfig(
            classifier_via="fast",
            models={"sonnet": "glm-5.3", "haiku": "glm-4.5-air"},
        )
    )

    assert env_vars["ANTHROPIC_MODEL"] == "sonnet"
    assert env_vars["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "glm-5.3"


def test_classifier_via_literal_model_id():
    """classifier_via should accept a literal provider model ID."""
    env_vars = map_claude_config_to_env_vars(
        EnvironmentConfig(
            classifier_via="cheap-judge",
            models={"opus": "glm-5.3"},
        )
    )

    assert env_vars["ANTHROPIC_MODEL"] == "opus"
    assert env_vars["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "cheap-judge"


def test_opaque_model_pins_to_opus_when_sonnet_holds_classifier():
    """An opaque model should take the opus slot when sonnet is repurposed."""
    env_vars = map_claude_config_to_env_vars(
        EnvironmentConfig(
            model="glm-5.3",
            classifier_via="fast",
            fast="glm-4.5-air",
        )
    )

    assert env_vars["ANTHROPIC_MODEL"] == "opus"
    assert env_vars["ANTHROPIC_DEFAULT_OPUS_MODEL"] == "glm-5.3"
    assert env_vars["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "glm-4.5-air"


def test_recognizable_model_id_not_rewritten():
    """Aliases and IDs containing a known model name pass through unchanged."""
    for model in ("opus", "my-gateway/claude-opus-5", "claude-sonnet-4-5@20250929"):
        env_vars = map_claude_config_to_env_vars(EnvironmentConfig(model=model))
        assert env_vars["ANTHROPIC_MODEL"] == model
        assert "ANTHROPIC_DEFAULT_SONNET_MODEL" not in env_vars


def test_map_claude_fable_model():
    """The fable family should map to its pin env var."""
    env_vars = map_claude_config_to_env_vars(
        EnvironmentConfig(models={"fable": "my-fable-deployment"})
    )
    assert env_vars["ANTHROPIC_DEFAULT_FABLE_MODEL"] == "my-fable-deployment"

    env_vars = map_claude_config_to_env_vars(EnvironmentConfig(fable="fable-top-level"))
    assert env_vars["ANTHROPIC_DEFAULT_FABLE_MODEL"] == "fable-top-level"


def test_map_claude_auto_mode_and_context_env_vars():
    """New env mappings for context window and classifier routing."""
    env_vars = map_claude_config_to_env_vars(
        EnvironmentConfig(max_context_tokens=256000, auto_mode_server=False)
    )
    assert env_vars["CLAUDE_CODE_MAX_CONTEXT_TOKENS"] == "256000"
    assert env_vars["CLAUDE_CODE_AUTO_MODE_SERVER"] == "0"

    env_vars = map_claude_config_to_env_vars(EnvironmentConfig(auto_mode_server=True))
    assert env_vars["CLAUDE_CODE_AUTO_MODE_SERVER"] == "1"


def test_map_claude_custom_model_option():
    """Custom model option fields should map to their env vars."""
    env_vars = map_claude_config_to_env_vars(
        EnvironmentConfig(
            custom_model="my-gateway/claude-opus-5",
            custom_model_name="Opus via Gateway",
            custom_model_description="Custom deployment",
            custom_model_capabilities=["effort", "thinking"],
        )
    )
    assert env_vars["ANTHROPIC_CUSTOM_MODEL_OPTION"] == "my-gateway/claude-opus-5"
    assert env_vars["ANTHROPIC_CUSTOM_MODEL_OPTION_NAME"] == "Opus via Gateway"
    assert (
        env_vars["ANTHROPIC_CUSTOM_MODEL_OPTION_DESCRIPTION"] == "Custom deployment"
    )
    assert (
        env_vars["ANTHROPIC_CUSTOM_MODEL_OPTION_SUPPORTED_CAPABILITIES"]
        == "effort,thinking"
    )


def test_map_claude_capabilities():
    """Per-family capabilities should map to SUPPORTED_CAPABILITIES env vars."""
    env_vars = map_claude_config_to_env_vars(
        EnvironmentConfig(
            capabilities={
                "sonnet": ["effort", "interleaved_thinking"],
                "custom": "effort,thinking",
                "bogus": "ignored",
            }
        )
    )
    assert (
        env_vars["ANTHROPIC_DEFAULT_SONNET_MODEL_SUPPORTED_CAPABILITIES"]
        == "effort,interleaved_thinking"
    )
    assert (
        env_vars["ANTHROPIC_CUSTOM_MODEL_OPTION_SUPPORTED_CAPABILITIES"]
        == "effort,thinking"
    )
    assert len(env_vars) == 2


def test_model_overrides_round_trip(tmp_path):
    """model_overrides should merge into modelOverrides and clear cleanly."""
    manager = build_claude_config_manager(tmp_path / ".claude")
    manager.save_settings(
        {"modelOverrides": {"claude-opus-4-7": "user-override"}}
    )

    env_config = EnvironmentConfig(
        model_overrides={"claude-sonnet-5": "my-gateway/sonnet"}
    )
    manager.update_env_in_settings("env1", env_config)
    settings = manager.load_settings()

    assert settings["modelOverrides"] == {
        "claude-opus-4-7": "user-override",
        "claude-sonnet-5": "my-gateway/sonnet",
    }

    manager.clear_env_from_settings()
    settings = manager.load_settings()
    assert settings["modelOverrides"] == {"claude-opus-4-7": "user-override"}


def test_auto_mode_default_mode_round_trip(tmp_path):
    """auto_mode should write defaultMode and restore the previous value."""
    manager = build_claude_config_manager(tmp_path / ".claude")
    manager.save_settings({"permissions": {"defaultMode": "plan", "allow": ["Bash(ls)"]}})

    manager.update_env_in_settings("env1", EnvironmentConfig(auto_mode=True))
    settings = manager.load_settings()
    assert settings["permissions"]["defaultMode"] == "auto"
    assert settings["permissions"]["allow"] == ["Bash(ls)"]

    manager.clear_env_from_settings()
    settings = manager.load_settings()
    assert settings["permissions"]["defaultMode"] == "plan"


def test_auto_mode_removed_on_next_apply_without_it(tmp_path):
    """Applying an env without auto_mode should undo a managed defaultMode."""
    manager = build_claude_config_manager(tmp_path / ".claude")

    manager.update_env_in_settings("env1", EnvironmentConfig(auto_mode=True))
    manager.update_env_in_settings("env2", EnvironmentConfig(url="https://x.com"))
    settings = manager.load_settings()

    assert "permissions" not in settings


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
