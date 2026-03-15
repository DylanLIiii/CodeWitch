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
        )

        local_home = manager.create_local_home("relay-env", env_config)

        auth_data = json.loads((local_home / "auth.json").read_text(encoding="utf-8"))
        config_data = parse((local_home / "config.toml").read_text(encoding="utf-8")).unwrap()

        assert auth_data["auth_mode"] == "apikey"
        assert auth_data["OPENAI_API_KEY"] == "sk-test-123"
        assert "tokens" in auth_data
        assert config_data["model_provider"] == "codewitch_relay_env"
        assert config_data["model_providers"]["codewitch_relay_env"]["base_url"] == "https://relay.example.com/v1"
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
        env_config = EnvironmentConfig(tool="codex", auth_mode="login", model="gpt-5.4")

        manager.apply_global_env("official", env_config)

        auth_data = json.loads((codex_dir / "auth.json").read_text(encoding="utf-8"))
        config_data = parse((codex_dir / "config.toml").read_text(encoding="utf-8")).unwrap()

        assert auth_data["auth_mode"] == "chatgpt"
        assert auth_data["OPENAI_API_KEY"] is None
        assert config_data["model_provider"] == "openai"
        assert config_data["model"] == "gpt-5.4"
        assert "codewitch_old" not in config_data.get("model_providers", {})
