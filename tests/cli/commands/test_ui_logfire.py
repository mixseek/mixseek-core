"""Tests for mixseek ui command with Logfire integration.

Test strategy:
- Mock subprocess.run to prevent actual Streamlit launch
- Verify environment variables are set correctly
- Test CLI flag exclusivity
- Test all privacy modes
"""

import os
from unittest.mock import MagicMock, patch

import pytest
import typer

from mixseek.cli.commands.ui import ui


@pytest.fixture
def mock_workspace(tmp_path, monkeypatch):
    """Create a mock workspace with configs directory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "configs").mkdir()
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))
    return workspace


@pytest.fixture(autouse=True)
def clear_logfire_env_vars():
    """Clear Logfire and logging environment variables before each test."""
    env_vars = [
        "LOGFIRE_ENABLED",
        "LOGFIRE_PRIVACY_MODE",
        "LOGFIRE_CAPTURE_HTTP",
        "LOGFIRE_PROJECT",
        "LOGFIRE_SEND_TO_LOGFIRE",
        "MIXSEEK_LOG_LEVEL",
        "MIXSEEK_LOG_CONSOLE",
        "MIXSEEK_LOG_FILE",
    ]
    for var in env_vars:
        os.environ.pop(var, None)
    yield
    # Cleanup after test
    for var in env_vars:
        os.environ.pop(var, None)


def test_ui_command_with_logfire_flag(mock_workspace):
    """--logfire フラグでLOGFIRE_ENABLED=1が設定される."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        # Execute
        try:
            ui(
                port=None,
                workspace=mock_workspace,
                logfire=True,
                logfire_metadata=False,
                logfire_http=False,
                log_level="info",
                no_log_console=False,
                no_log_file=False,
            )
        except (typer.Exit, KeyboardInterrupt):
            pass

        # Verify: 環境変数が設定されている
        assert os.getenv("LOGFIRE_ENABLED") == "1"
        assert os.getenv("LOGFIRE_PRIVACY_MODE") == "full"
        # LOGFIRE_CAPTURE_HTTPは設定されないか、"1"ではない
        assert os.getenv("LOGFIRE_CAPTURE_HTTP") != "1"


def test_ui_command_with_logfire_metadata_flag(mock_workspace):
    """--logfire-metadata フラグでmetadata_onlyモードが設定される."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        # Execute
        try:
            ui(
                port=None,
                workspace=mock_workspace,
                logfire=False,
                logfire_metadata=True,
                logfire_http=False,
                log_level="info",
                no_log_console=False,
                no_log_file=False,
            )
        except (typer.Exit, KeyboardInterrupt):
            pass

        # Verify
        assert os.getenv("LOGFIRE_ENABLED") == "1"
        assert os.getenv("LOGFIRE_PRIVACY_MODE") == "metadata_only"
        assert os.getenv("LOGFIRE_CAPTURE_HTTP") != "1"


def test_ui_command_with_logfire_http_flag(mock_workspace):
    """--logfire-http フラグでHTTPキャプチャが有効化される."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        # Execute
        try:
            ui(
                port=None,
                workspace=mock_workspace,
                logfire=False,
                logfire_metadata=False,
                logfire_http=True,
                log_level="info",
                no_log_console=False,
                no_log_file=False,
            )
        except (typer.Exit, KeyboardInterrupt):
            pass

        # Verify
        assert os.getenv("LOGFIRE_ENABLED") == "1"
        assert os.getenv("LOGFIRE_PRIVACY_MODE") == "full"
        assert os.getenv("LOGFIRE_CAPTURE_HTTP") == "1"


def test_ui_command_exclusive_flags(mock_workspace):
    """複数のlogfireフラグ指定時にエラーが発生する."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        # Execute: --logfire と --logfire-metadata を同時指定
        with pytest.raises(typer.Exit) as exc_info:
            ui(
                port=None,
                workspace=mock_workspace,
                logfire=True,
                logfire_metadata=True,
                logfire_http=False,
                log_level="info",
                no_log_console=False,
                no_log_file=False,
            )

        # Verify: Exit code 1
        assert exc_info.value.exit_code == 1


def test_ui_command_without_logfire(mock_workspace):
    """Logfireフラグなしでは環境変数が設定されない."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        # Execute
        try:
            ui(
                port=None,
                workspace=mock_workspace,
                logfire=False,
                logfire_metadata=False,
                logfire_http=False,
                log_level="info",
                no_log_console=False,
                no_log_file=False,
            )
        except (typer.Exit, KeyboardInterrupt):
            pass

        # Verify: LOGFIRE_ENABLEDが設定されていない
        assert os.getenv("LOGFIRE_ENABLED") is None


def test_ui_command_logfire_with_env_project(mock_workspace, monkeypatch):
    """LOGFIRE_PROJECT環境変数が継承される."""
    monkeypatch.setenv("LOGFIRE_PROJECT", "test-project")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        # Execute
        try:
            ui(
                port=None,
                workspace=mock_workspace,
                logfire=True,
                logfire_metadata=False,
                logfire_http=False,
                log_level="info",
                no_log_console=False,
                no_log_file=False,
            )
        except (typer.Exit, KeyboardInterrupt):
            pass

        # Verify: LOGFIRE_PROJECTが継承されている
        assert os.getenv("LOGFIRE_PROJECT") == "test-project"


def test_ui_command_subprocess_called_correctly(mock_workspace):
    """subprocess.runが正しいパラメータで呼ばれる."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        # Execute
        try:
            ui(
                port=8080,
                workspace=mock_workspace,
                logfire=False,
                logfire_metadata=False,
                logfire_http=False,
                log_level="info",
                no_log_console=False,
                no_log_file=False,
            )
        except (typer.Exit, KeyboardInterrupt):
            pass

        # Verify: subprocess.runが呼ばれた
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert "streamlit" in call_args
        assert "run" in call_args
        assert "--server.port" in call_args
        assert "8080" in call_args
