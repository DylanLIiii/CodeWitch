"""Tests for codex_manager.py."""

import json
import tempfile
from pathlib import Path

from tomlkit import parse

from src.codex_manager import CodexManager
from src.config import EnvironmentConfig


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, content: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(content, file, indent=2)


def test_create_local_home_for_codex_apikey():
    """Local Codex switching should generate an isolated CODEX_HOME."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        codex_dir = base / ".codex"
        codex_dir.mkdir()
        _write_text(
            codex_dir / "config.toml",
            'model = "gpt-5"\n\n[projects."/tmp/project"]\ntrust_level = "trusted"\n',
        )
        _write_json(
            codex_dir / "auth.json",
            {
                "auth_mode": "chatgpt",
                "OPENAI_API_KEY": None,
                "tokens": {"access_token": "token"},
            },
        )
        (codex_dir / "skills").mkdir()

        manager = CodexManager(codex_dir=codex_dir, managed_homes_dir=base / "profiles")
        env_config = EnvironmentConfig(
            tool="codex",
            auth_mode="apikey",
            base_url="https://relay.example.com/v1",
            api_key="sk-test-123",
            model="gpt-5",
            model_reasoning_effort="high",
            plan_mode_reasoning_effort="medium",
            model_reasoning_summary="auto",
        )

        local_home = manager.create_local_home("relay-env", env_config)

        auth_data = json.loads((local_home / "auth.json").read_text(encoding="utf-8"))
        config_data = parse((local_home / "config.toml").read_text(encoding="utf-8")).unwrap()

        assert auth_data["auth_mode"] == "apikey"
        assert auth_data["OPENAI_API_KEY"] == "sk-test-123"
        assert "tokens" in auth_data
        assert config_data["model_provider"] == "codewitch_relay_env"
        assert config_data["model_providers"]["codewitch_relay_env"]["base_url"] == "https://relay.example.com/v1"
        assert config_data["model_reasoning_effort"] == "high"
        assert config_data["plan_mode_reasoning_effort"] == "medium"
        assert config_data["model_reasoning_summary"] == "auto"
        assert config_data["projects"]["/tmp/project"]["trust_level"] == "trusted"
        assert (local_home / "skills").is_symlink()


def test_apply_global_env_for_codex_login():
    """Global Codex switching should update config.toml and auth.json in place."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        codex_dir = base / ".codex"
        codex_dir.mkdir()
        _write_text(
            codex_dir / "config.toml",
            'model = "gpt-5"\nmodel_provider = "codewitch_old"\n\n[model_providers.codewitch_old]\nname = "Old"\nbase_url = "https://old.example.com/v1"\nrequires_openai_auth = true\nwire_api = "responses"\n',
        )
        _write_json(
            codex_dir / "auth.json",
            {
                "auth_mode": "apikey",
                "OPENAI_API_KEY": "sk-old",
                "tokens": {"access_token": "token"},
            },
        )

        manager = CodexManager(codex_dir=codex_dir, managed_homes_dir=base / "profiles")
        env_config = EnvironmentConfig(
            tool="codex",
            auth_mode="login",
            model="gpt-5.4",
            model_reasoning_effort="xhigh",
            plan_mode_reasoning_effort="low",
        )

        manager.apply_global_env("official", env_config)

        auth_data = json.loads((codex_dir / "auth.json").read_text(encoding="utf-8"))
        config_data = parse((codex_dir / "config.toml").read_text(encoding="utf-8")).unwrap()

        assert auth_data["auth_mode"] == "chatgpt"
        assert auth_data["OPENAI_API_KEY"] is None
        assert config_data["model_provider"] == "openai"
        assert config_data["model"] == "gpt-5.4"
        assert config_data["model_reasoning_effort"] == "xhigh"
        assert config_data["plan_mode_reasoning_effort"] == "low"
        assert "codewitch_old" not in config_data.get("model_providers", {})


def test_apply_global_env_clears_reasoning_when_next_env_omits():
    """Reasoning TOML keys from a previous apply must not persist when the new env omits them."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        codex_dir = base / ".codex"
        codex_dir.mkdir()
        _write_text(codex_dir / "config.toml", 'model = "gpt-5"\n')
        _write_json(
            codex_dir / "auth.json",
            {
                "auth_mode": "chatgpt",
                "OPENAI_API_KEY": None,
                "tokens": {"access_token": "token"},
            },
        )

        manager = CodexManager(codex_dir=codex_dir, managed_homes_dir=base / "profiles")
        with_reasoning = EnvironmentConfig(
            tool="codex",
            auth_mode="login",
            model="gpt-5",
            model_reasoning_effort="high",
            plan_mode_reasoning_effort="low",
            model_reasoning_summary="auto",
        )
        manager.apply_global_env("with-r", with_reasoning)
        after_first = parse((codex_dir / "config.toml").read_text(encoding="utf-8")).unwrap()
        assert after_first["model_reasoning_effort"] == "high"
        assert after_first["plan_mode_reasoning_effort"] == "low"
        assert after_first["model_reasoning_summary"] == "auto"

        without_reasoning = EnvironmentConfig(
            tool="codex",
            auth_mode="login",
            model="gpt-5.4",
        )
        manager.apply_global_env("plain", without_reasoning)
        after_second = parse((codex_dir / "config.toml").read_text(encoding="utf-8")).unwrap()
        assert after_second["model"] == "gpt-5.4"
        assert "model_reasoning_effort" not in after_second
        assert "plan_mode_reasoning_effort" not in after_second
        assert "model_reasoning_summary" not in after_second


def test_build_runtime_preview_includes_reasoning():
    """Runtime preview should surface reasoning fields when set."""
    manager = CodexManager(codex_dir=Path("/tmp"), managed_homes_dir=Path("/tmp"))
    env_config = EnvironmentConfig(
        tool="codex",
        auth_mode="login",
        model="gpt-5.1-codex",
        model_reasoning_effort="high",
        plan_mode_reasoning_effort="none",
        model_reasoning_summary="detailed",
    )
    preview = manager.build_runtime_preview("dev", env_config)
    assert preview["CODEX_MODEL_REASONING_EFFORT"] == "high"
    assert preview["CODEX_PLAN_MODE_REASONING_EFFORT"] == "none"
    assert preview["CODEX_MODEL_REASONING_SUMMARY"] == "detailed"
