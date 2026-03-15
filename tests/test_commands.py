"""Tests for commands.py."""

from unittest.mock import Mock, patch

from typer.testing import CliRunner

from src.commands import app
from src.config import EnvironmentConfig

runner = CliRunner()


def test_claude_list_command_empty():
    """Claude list should show the empty state."""
    manager = Mock()
    manager.tool_label = "Claude Code"
    manager.config_manager.load_environments.return_value = {}

    with patch("src.commands.claude_env_manager", manager):
        result = runner.invoke(app, ["claude-code", "list"])

    assert result.exit_code == 0
    assert "No environments found" in result.output


def test_codex_list_command_with_environment():
    """Codex list should render auth mode and environment name."""
    manager = Mock()
    manager.tool_label = "Codex"
    manager.config_manager.load_environments.return_value = {
        "official": EnvironmentConfig(tool="codex", auth_mode="login", model="gpt-5.4"),
    }

    with patch("src.commands.codex_env_manager", manager):
        result = runner.invoke(app, ["codex", "list"])

    assert result.exit_code == 0
    assert "official" in result.output
    assert "login" in result.output


def test_claude_use_command_local():
    """Claude use should prepare a terminal-local switch."""
    manager = Mock()
    manager.tool_label = "Claude Code"
    manager.config_manager.load_environments.return_value = {
        "testenv": EnvironmentConfig(url="https://example.com", token="token123"),
    }
    manager.set_local_env.return_value = (
        {"ANTHROPIC_BASE_URL": "https://example.com"},
        "export ANTHROPIC_BASE_URL='https://example.com'",
    )

    with patch("src.commands.claude_env_manager", manager):
        result = runner.invoke(app, ["claude-code", "use", "testenv"])

    assert result.exit_code == 0
    assert "prepared for this terminal" in result.output
    manager.set_local_env.assert_called_once_with("testenv")


def test_codex_apply_command_global():
    """Codex apply should report global files."""
    manager = Mock()
    manager.tool_label = "Codex"
    manager.config_manager.load_environments.return_value = {
        "official": EnvironmentConfig(tool="codex", auth_mode="login", model="gpt-5.4"),
    }

    with patch("src.commands.codex_env_manager", manager):
        result = runner.invoke(app, ["codex", "apply", "official"])

    assert result.exit_code == 0
    assert "applied globally" in result.output
    assert "~/.codex/config.toml" in result.output
    manager.set_global_env.assert_called_once_with("official")


def test_use_command_env_not_found():
    """Missing environments should exit with an error."""
    manager = Mock()
    manager.tool_label = "Claude Code"
    manager.config_manager.load_environments.return_value = {}

    with patch("src.commands.claude_env_manager", manager):
        result = runner.invoke(app, ["claude-code", "use", "bad"])

    assert result.exit_code == 1
    assert "Error" in result.output
    manager.set_local_env.assert_not_called()


def test_current_command_no_env():
    """Current should show the empty state."""
    manager = Mock()
    manager.get_current_env.return_value = None

    with patch("src.commands.codex_env_manager", manager):
        result = runner.invoke(app, ["codex", "current"])

    assert result.exit_code == 0
    assert "No active environment" in result.output


def test_current_command_codex():
    """Current should show the active Codex environment."""
    manager = Mock()
    manager.get_current_env.return_value = {
        "env_name": "official",
        "env_vars": {"CODEX_AUTH_MODE": "login"},
        "mode": "global",
        "tool": "codex",
    }

    with patch("src.commands.codex_env_manager", manager):
        result = runner.invoke(app, ["codex", "current"])

    assert result.exit_code == 0
    assert "official" in result.output
    assert "global" in result.output
    assert "Codex Runtime Preview" in result.output


def test_unset_command_local():
    """Unset should clear tool-local state."""
    manager = Mock()

    with patch("src.commands.claude_env_manager", manager):
        result = runner.invoke(app, ["claude-code", "unset"])

    assert result.exit_code == 0
    assert "Local environment cleared" in result.output
    manager.unset_local.assert_called_once()


def test_unset_command_global():
    """Unset global should clear persistent state."""
    manager = Mock()

    with patch("src.commands.codex_env_manager", manager):
        result = runner.invoke(app, ["codex", "unset", "--global"])

    assert result.exit_code == 0
    assert "Global environment cleared" in result.output
    manager.unset_global.assert_called_once()


def test_info_command_found():
    """Info should render environment details."""
    manager = Mock()
    manager.tool_label = "Claude Code"
    manager.get_env_info.return_value = {
        "name": "testenv",
        "tool": "claude-code",
        "config": {
            "url": "https://example.com",
            "token": "token123",
            "model": "sonnet",
        },
        "env_vars": {
            "ANTHROPIC_BASE_URL": "https://example.com",
            "ANTHROPIC_AUTH_TOKEN": "token123",
        },
    }

    with patch("src.commands.claude_env_manager", manager):
        result = runner.invoke(app, ["claude-code", "info", "testenv"])

    assert result.exit_code == 0
    assert "testenv" in result.output
    assert "Configuration" in result.output


def test_info_command_not_found():
    """Missing info lookups should exit non-zero."""
    manager = Mock()
    manager.get_env_info.return_value = None

    with patch("src.commands.codex_env_manager", manager):
        result = runner.invoke(app, ["codex", "info", "bad"])

    assert result.exit_code == 1
    assert "not found" in result.output
