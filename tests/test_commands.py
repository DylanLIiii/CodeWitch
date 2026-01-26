"""Tests for commands.py."""

from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from src.commands import app

runner = CliRunner()


@pytest.fixture
def mock_config_manager():
    with patch('src.commands.config_manager') as mock:
        yield mock


@pytest.fixture
def mock_env_manager():
    with patch('src.commands.env_manager') as mock:
        yield mock


def test_list_command_empty(mock_config_manager):
    """Test list command with no environments."""
    mock_config_manager.load_environments.return_value = {}

    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "No environments found" in result.output


def test_list_command_with_environments(mock_config_manager):
    """Test list command with environments."""
    from src.config import EnvironmentConfig

    env1 = EnvironmentConfig(
        url="https://example1.com",
        token="token1",
        model="model1",
        fast="fast1",
    )
    env2 = EnvironmentConfig(
        url="https://example2.com",
        token="token2",
        model=None,
        fast=None,
    )

    mock_config_manager.load_environments.return_value = {
        "env1": env1,
        "env2": env2,
    }

    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "env1" in result.output
    assert "env2" in result.output
    assert "https://example1.com" in result.output


def test_use_command_local(mock_env_manager):
    """Test use command in local mode."""
    mock_env_manager.set_local_env.return_value = (
        {"ANTHROPIC_BASE_URL": "https://example.com"},
        "export ANTHROPIC_BASE_URL='https://example.com'"
    )

    # Mock isatty to return True so we get full output
    with patch('sys.stdout.isatty', return_value=True):
        result = runner.invoke(app, ["use", "testenv"])

    assert result.exit_code == 0
    assert "set locally" in result.output
    mock_env_manager.set_local_env.assert_called_once_with("testenv")


def test_use_command_global(mock_env_manager):
    """Test use command in global mode."""
    mock_env_manager.set_global_env.return_value = (
        {"ANTHROPIC_BASE_URL": "https://example.com"},
        "export ANTHROPIC_BASE_URL='https://example.com'"
    )

    # Mock isatty to return True so we get full output
    with patch('sys.stdout.isatty', return_value=True):
        result = runner.invoke(app, ["use", "--global", "testenv"])

    assert result.exit_code == 0
    assert "set globally" in result.output
    mock_env_manager.set_global_env.assert_called_once_with("testenv")


def test_use_command_env_not_found(mock_env_manager):
    """Test use command with non-existent environment."""
    mock_env_manager.set_local_env.side_effect = ValueError("Environment 'bad' not found")

    result = runner.invoke(app, ["use", "bad"])

    assert result.exit_code == 1
    assert "Error" in result.output


def test_current_command_no_env(mock_env_manager):
    """Test current command with no active environment."""
    mock_env_manager.get_current_env.return_value = None

    result = runner.invoke(app, ["current"])

    assert result.exit_code == 0
    assert "No active environment" in result.output


def test_current_command_local(mock_env_manager):
    """Test current command with local environment."""
    mock_env_manager.get_current_env.return_value = {
        "env_name": "testenv",
        "env_vars": {"ANTHROPIC_BASE_URL": "https://example.com"},
        "mode": "local"
    }

    result = runner.invoke(app, ["current"])

    assert result.exit_code == 0
    assert "testenv" in result.output
    assert "local" in result.output


def test_unset_command_local(mock_env_manager):
    """Test unset command in local mode."""
    result = runner.invoke(app, ["unset"])

    assert result.exit_code == 0
    assert "Local environment cleared" in result.output
    mock_env_manager.unset_local.assert_called_once()


def test_unset_command_global(mock_env_manager):
    """Test unset command in global mode."""
    result = runner.invoke(app, ["unset", "--global"])

    assert result.exit_code == 0
    assert "Global environment cleared" in result.output
    mock_env_manager.unset_global.assert_called_once()


def test_info_command_found(mock_env_manager):
    """Test info command with existing environment."""
    mock_env_manager.get_env_info.return_value = {
        "name": "testenv",
        "config": {
            "url": "https://example.com",
            "token": "token123",
            "model": "model1",
        },
        "env_vars": {
            "ANTHROPIC_BASE_URL": "https://example.com",
            "ANTHROPIC_AUTH_TOKEN": "token123",
        }
    }

    result = runner.invoke(app, ["info", "testenv"])

    assert result.exit_code == 0
    assert "testenv" in result.output
    assert "Configuration" in result.output


def test_info_command_not_found(mock_env_manager):
    """Test info command with non-existent environment."""
    mock_env_manager.get_env_info.return_value = None

    result = runner.invoke(app, ["info", "bad"])

    assert result.exit_code == 1
    assert "not found" in result.output