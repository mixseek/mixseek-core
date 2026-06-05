"""CLI ログのレベル検証テスト。

``mixseek.cli`` ロガーへの出力が意図したレベルで記録されることを検証する。

ERROR レベル（処理継続不能・異常終了 → ログレベルフィルタで確実に拾う）:

    - evaluate: ユーザー中断 (evaluate.interrupted_by_user)
    - init:     初期化中止 / ユーザーキャンセル (init.aborted / init.cancelled_by_user)
    - member:   ユーザー中断 (member.interrupted_by_user)
    - team:     ワークスペース解決失敗の案内 (team.workspace_resolve_hint)

WARNING レベル（処理は継続できる劣化動作 → 警告にとどめる）:

    - utils:    ロギング / Logfire セットアップ失敗
                (logging.setup_failed*, logfire.init_failed*)

レベルが意図せず入れ替わる（例: 警告にとどめるべき箇所が error 化する等）退行を防ぐ
回帰テスト。
"""

import logging
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from mixseek.cli.main import app


@pytest.fixture
def runner() -> CliRunner:
    """CLIテストランナー"""
    return CliRunner()


@pytest.fixture
def capture_cli_logger(caplog: pytest.LogCaptureFixture) -> Iterator[pytest.LogCaptureFixture]:
    """``mixseek.cli`` ロガーのログを caplog で捕捉する。

    ``mixseek`` は root への leak 防止のため ``propagate=False`` に設定されるため、
    caplog の root handler では records が取れない。caplog.handler を直接 attach する。
    """
    cli_logger = logging.getLogger("mixseek.cli")
    cli_logger.addHandler(caplog.handler)
    # WARNING / ERROR 双方を捕捉できるよう閾値を WARNING に下げる。
    caplog.set_level(logging.WARNING, logger="mixseek.cli")
    try:
        yield caplog
    finally:
        cli_logger.removeHandler(caplog.handler)


def _events(caplog: pytest.LogCaptureFixture, event: str, level: int) -> list[logging.LogRecord]:
    """指定 event を持つ、指定レベルの LogRecord を返す。"""
    return [r for r in caplog.records if r.levelno == level and getattr(r, "event", None) == event]


def _error_events(caplog: pytest.LogCaptureFixture, event: str) -> list[logging.LogRecord]:
    """指定 event を持つ ERROR レベルの LogRecord を返す。"""
    return _events(caplog, event, logging.ERROR)


def _warning_events(caplog: pytest.LogCaptureFixture, event: str) -> list[logging.LogRecord]:
    """指定 event を持つ WARNING レベルの LogRecord を返す。"""
    return _events(caplog, event, logging.WARNING)


class TestInterruptLogsAreError:
    """KeyboardInterrupt 系の中断ログが ERROR レベルで出力されること。"""

    def test_evaluate_interrupted_by_user(
        self,
        runner: CliRunner,
        capture_cli_logger: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """evaluate 実行中の Ctrl-C が ERROR で記録され exit code 130 で終了する。"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        with (
            patch("mixseek.cli.commands.evaluate.initialize_observability"),
            patch("mixseek.cli.commands.evaluate.asyncio.run", side_effect=KeyboardInterrupt),
        ):
            result = runner.invoke(app, ["evaluate", "質問", "回答"])

        assert result.exit_code == 130
        assert _error_events(capture_cli_logger, "evaluate.interrupted_by_user"), (
            "evaluate.interrupted_by_user が ERROR レベルで記録されていない"
        )

    def test_member_interrupted_by_user(
        self,
        runner: CliRunner,
        capture_cli_logger: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """member 実行中の Ctrl-C が ERROR で記録され exit code 130 で終了する。"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        config_file = tmp_path / "member.toml"
        config_file.write_text("dummy = true\n")

        with (
            patch("mixseek.cli.commands.member.initialize_observability"),
            patch("mixseek.cli.commands.member.ConfigurationManager", side_effect=KeyboardInterrupt),
        ):
            result = runner.invoke(app, ["member", "質問", "--config", str(config_file)])

        assert result.exit_code == 130
        assert _error_events(capture_cli_logger, "member.interrupted_by_user"), (
            "member.interrupted_by_user が ERROR レベルで記録されていない"
        )

    def test_init_cancelled_by_user(
        self,
        runner: CliRunner,
        capture_cli_logger: pytest.LogCaptureFixture,
        tmp_path: Path,
    ) -> None:
        """init 実行中の Ctrl-C が ERROR で記録され exit code 130 で終了する。"""
        with (
            patch("mixseek.cli.commands.init.early_setup_logging_from_env"),
            patch("mixseek.cli.commands.init.get_workspace_path", side_effect=KeyboardInterrupt),
        ):
            result = runner.invoke(app, ["init", "--workspace", str(tmp_path / "ws")])

        assert result.exit_code == 130
        assert _error_events(capture_cli_logger, "init.cancelled_by_user"), (
            "init.cancelled_by_user が ERROR レベルで記録されていない"
        )


class TestAbortAndResolveLogsAreError:
    """中止・解決失敗の案内ログが ERROR レベルで出力されること。"""

    def test_init_aborted_on_overwrite_declined(
        self,
        runner: CliRunner,
        capture_cli_logger: pytest.LogCaptureFixture,
        tmp_path: Path,
    ) -> None:
        """既存ワークスペースの上書きを拒否した際の中止ログが ERROR で記録される。"""
        workspace = tmp_path / "existing-ws"
        workspace.mkdir()

        with (
            patch("mixseek.cli.commands.init.early_setup_logging_from_env"),
            patch("mixseek.cli.commands.init.typer.confirm", return_value=False),
        ):
            result = runner.invoke(app, ["init", "--workspace", str(workspace)])

        assert result.exit_code == 1
        assert _error_events(capture_cli_logger, "init.aborted"), "init.aborted が ERROR レベルで記録されていない"

    def test_team_workspace_resolve_hint(
        self,
        runner: CliRunner,
        capture_cli_logger: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """ワークスペース解決失敗時の案内ログが ERROR で記録される。"""
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
        # --config は必須だが、ワークスペース解決失敗が先行するため内容は参照されない。
        config_file = tmp_path / "team.toml"
        config_file.write_text("dummy = true\n")

        with patch(
            "mixseek.cli.commands.team.ConfigurationManager",
            side_effect=RuntimeError("resolve failed"),
        ):
            result = runner.invoke(app, ["team", "質問", "--config", str(config_file)])

        assert result.exit_code == 1
        assert _error_events(capture_cli_logger, "team.workspace_resolve_hint"), (
            "team.workspace_resolve_hint が ERROR レベルで記録されていない"
        )


class TestSetupFailureLogsAreWarning:
    """ロギング / Logfire セットアップ失敗ログが WARNING レベルで出力されること。

    これらは処理を継続できる劣化動作（観測性が落ちるだけ）であり、中断・中止のような
    異常終了とは異なるため、warning にとどめる。
    """

    def test_logging_setup_failed(self, capture_cli_logger: pytest.LogCaptureFixture) -> None:
        """setup_logging 失敗時に WARNING で記録され、例外は外に漏れない。"""
        from mixseek.cli.utils import setup_logging_from_cli

        with patch("mixseek.cli.utils.setup_logging", side_effect=RuntimeError("setup boom")):
            setup_logging_from_cli(
                log_level="info",
                no_log_console=True,
                no_log_file=True,
                logfire_enabled=False,
                workspace=None,
                verbose=False,
            )

        records = _warning_events(capture_cli_logger, "logging.setup_failed")
        assert records, "logging.setup_failed が WARNING レベルで記録されていない"
        assert "setup boom" in records[0].getMessage()

    def test_logging_setup_failed_traceback_verbose(self, capture_cli_logger: pytest.LogCaptureFixture) -> None:
        """verbose 指定時は traceback も WARNING で記録される。"""
        from mixseek.cli.utils import setup_logging_from_cli

        with patch("mixseek.cli.utils.setup_logging", side_effect=RuntimeError("setup boom")):
            setup_logging_from_cli(
                log_level="info",
                no_log_console=True,
                no_log_file=True,
                logfire_enabled=False,
                workspace=None,
                verbose=True,
            )

        assert _warning_events(capture_cli_logger, "logging.setup_failed"), (
            "logging.setup_failed が WARNING レベルで記録されていない"
        )
        assert _warning_events(capture_cli_logger, "logging.setup_failed_traceback"), (
            "logging.setup_failed_traceback が WARNING レベルで記録されていない"
        )

    def test_logfire_init_failed_traceback_verbose(
        self,
        capture_cli_logger: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """verbose 指定時は Logfire 初期化失敗の traceback も WARNING で記録される。"""
        from mixseek.cli.utils import setup_logfire_from_cli

        monkeypatch.delenv("LOGFIRE_ENABLED", raising=False)

        with patch("mixseek.cli.utils.setup_logfire", side_effect=RuntimeError("init failed")):
            setup_logfire_from_cli(
                logfire=True,
                logfire_metadata=False,
                logfire_http=False,
                verbose=True,
            )

        assert _warning_events(capture_cli_logger, "logfire.init_failed"), (
            "logfire.init_failed が WARNING レベルで記録されていない"
        )
        assert _warning_events(capture_cli_logger, "logfire.init_failed_traceback"), (
            "logfire.init_failed_traceback が WARNING レベルで記録されていない"
        )
