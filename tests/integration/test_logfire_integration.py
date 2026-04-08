"""Logfire統合テスト。

text/json 両モード対応。finalize_mode3_handlers テストを含む。
"""

import logging
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mixseek.config.logfire import LogfireConfig, LogfirePrivacyMode
from mixseek.config.logging import LoggingConfig
from mixseek.observability.logfire import (
    JsonSpanProcessor,
    finalize_mode3_handlers,
    setup_logfire,
)
from mixseek.observability.logging_setup import setup_logging


@pytest.fixture
def mock_logfire():
    """Logfireモジュールをモック"""
    mock = MagicMock()
    with patch.dict("sys.modules", {"logfire": mock}):
        yield mock


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "test_workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


@pytest.fixture(autouse=True)
def reset_logging() -> Generator[None]:
    """テスト後にロガーをリセット"""
    yield
    for name in ("mixseek", "mixseek.traces"):
        logger = logging.getLogger(name)
        for h in logger.handlers:
            h.close()
        logger.handlers.clear()
    root = logging.getLogger()
    root.handlers.clear()


def test_setup_logfire_disabled():
    """config.enabled=Falseの場合は何もしない"""
    config = LogfireConfig(
        enabled=False,
        privacy_mode=LogfirePrivacyMode.METADATA_ONLY,
        capture_http=False,
        project_name=None,
        send_to_logfire=True,
    )
    setup_logfire(config)


class TestTextMode:
    """text モード（Mode 3）テスト"""

    def test_console_options_with_tee_writer(self, mock_logfire, temp_workspace: Path):
        """ConsoleOptions(output=TeeWriter(...)) が設定される"""
        config = LogfireConfig(
            enabled=True,
            privacy_mode=LogfirePrivacyMode.METADATA_ONLY,
            capture_http=False,
            project_name=None,
            send_to_logfire=True,
            console_output=True,
        )

        setup_logfire(config, log_format="text", workspace=temp_workspace)

        mock_logfire.configure.assert_called_once()
        call_kwargs = mock_logfire.configure.call_args[1]
        assert call_kwargs["send_to_logfire"] is True
        # console は ConsoleOptions インスタンスであるべき
        assert "console" in call_kwargs

    def test_finalize_removes_handlers(self, temp_workspace: Path):
        """finalize_mode3_handlers() が StreamHandler/FileHandler を除去"""
        # まず setup_logging で全ハンドラを追加
        logging_config = LoggingConfig(logfire_enabled=True, log_format="text")
        setup_logging(logging_config, temp_workspace)

        logger = logging.getLogger("mixseek")
        # StreamHandler と FileHandler が存在
        stream_handlers = [h for h in logger.handlers if type(h) is logging.StreamHandler]
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(stream_handlers) > 0
        assert len(file_handlers) > 0

        finalize_mode3_handlers()

        # 除去後
        remaining = [
            h for h in logger.handlers if type(h) is logging.StreamHandler or isinstance(h, logging.FileHandler)
        ]
        assert len(remaining) == 0

    def test_finalize_closes_file_handler(self, temp_workspace: Path):
        """finalize_mode3_handlers() が FileHandler をクローズ（FDリーク防止）"""
        logging_config = LoggingConfig(logfire_enabled=True, log_format="text")
        setup_logging(logging_config, temp_workspace)

        logger = logging.getLogger("mixseek")
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) > 0

        # ストリームを事前に保持
        streams = [h.stream for h in file_handlers]
        assert all(s is not None for s in streams)

        finalize_mode3_handlers()

        for stream in streams:
            assert stream.closed


class TestJsonMode:
    """json モード（Mode 4）テスト"""

    def test_console_false(self, mock_logfire, temp_workspace: Path):
        """ConsoleOptions が False に設定される"""
        config = LogfireConfig(
            enabled=True,
            privacy_mode=LogfirePrivacyMode.METADATA_ONLY,
            capture_http=False,
            project_name=None,
            send_to_logfire=True,
        )

        setup_logfire(config, log_format="json", workspace=temp_workspace)

        call_kwargs = mock_logfire.configure.call_args[1]
        assert call_kwargs["console"] is False

    def test_json_span_processor_added(self, mock_logfire, temp_workspace: Path):
        """additional_span_processors に JsonSpanProcessor が含まれる"""
        config = LogfireConfig(
            enabled=True,
            privacy_mode=LogfirePrivacyMode.METADATA_ONLY,
            capture_http=False,
            project_name=None,
            send_to_logfire=True,
        )

        setup_logfire(config, log_format="json", workspace=temp_workspace)

        call_kwargs = mock_logfire.configure.call_args[1]
        processors = call_kwargs.get("additional_span_processors")
        assert processors is not None
        assert any(isinstance(p, JsonSpanProcessor) for p in processors)


class TestJsonSpanProcessor:
    """JsonSpanProcessor ユニットテスト"""

    def test_on_start_logs_span_start(self):
        """on_start が "span_start" イベントを出力"""
        processor = JsonSpanProcessor()

        span = MagicMock()
        span.name = "test.span"
        span.context.span_id = 0x123456
        span.parent = None
        span.attributes = {"key": "value"}

        with patch.object(processor._traces_logger, "info") as mock_info:
            processor.on_start(span)
            mock_info.assert_called_once()
            call_kwargs = mock_info.call_args[1]
            assert call_kwargs["extra"]["type"] == "span_start"
            assert call_kwargs["extra"]["span_name"] == "test.span"

    def test_on_end_logs_span_end(self):
        """on_end が "span_end" イベントを出力"""
        processor = JsonSpanProcessor()

        span = MagicMock()
        span.name = "test.span"
        span.context.span_id = 0x123456
        span.parent = None
        span.start_time = 1000000000
        span.end_time = 3000000000
        span.status.status_code.name = "OK"
        span.attributes = {}

        with patch.object(processor._traces_logger, "info") as mock_info:
            processor.on_end(span)
            mock_info.assert_called_once()
            call_kwargs = mock_info.call_args[1]
            assert call_kwargs["extra"]["type"] == "span_end"
            assert call_kwargs["extra"]["duration_ms"] == 2000.0


class TestExistingBehavior:
    """既存の動作互換性テスト"""

    def test_metadata_only_mode(self, mock_logfire):
        """metadata_onlyモードで instrument_pydantic_ai(include_content=False)"""
        config = LogfireConfig(
            enabled=True,
            privacy_mode=LogfirePrivacyMode.METADATA_ONLY,
            capture_http=False,
            project_name=None,
            send_to_logfire=True,
        )

        setup_logfire(config)

        mock_logfire.instrument_pydantic_ai.assert_called_once()
        call_kwargs = mock_logfire.instrument_pydantic_ai.call_args[1]
        assert call_kwargs["include_content"] is False

    def test_full_mode(self, mock_logfire):
        """fullモードで instrument_pydantic_ai() が引数なし"""
        config = LogfireConfig(
            enabled=True,
            privacy_mode=LogfirePrivacyMode.FULL,
            capture_http=False,
            project_name=None,
            send_to_logfire=True,
        )

        setup_logfire(config)

        mock_logfire.instrument_pydantic_ai.assert_called_once_with()

    def test_capture_http(self, mock_logfire):
        """capture_http=True で instrument_httpx() が呼ばれる"""
        config = LogfireConfig(
            enabled=True,
            privacy_mode=LogfirePrivacyMode.METADATA_ONLY,
            capture_http=True,
            project_name=None,
            send_to_logfire=True,
        )

        setup_logfire(config)

        mock_logfire.instrument_httpx.assert_called_once_with(capture_all=True)

    def test_import_error(self):
        """logfire未インストール時のImportError"""
        config = LogfireConfig(
            enabled=True,
            privacy_mode=LogfirePrivacyMode.METADATA_ONLY,
            capture_http=False,
            project_name=None,
            send_to_logfire=True,
        )

        import sys

        logfire_backup = sys.modules.pop("logfire", None)

        try:
            sys.modules["logfire"] = None  # type: ignore
            with pytest.raises(ImportError, match="Logfire not installed"):
                setup_logfire(config)
        finally:
            sys.modules.pop("logfire", None)
            if logfire_backup is not None:
                sys.modules["logfire"] = logfire_backup
