"""MemberAgentLogger テスト。

extra dict 方式で構造化データを渡すことを検証。
JSON二重エンコードが発生しないことを確認。
"""

import logging
from collections.abc import Generator
from unittest.mock import MagicMock

import pytest

from mixseek.agents.member.logging import MemberAgentLogger


@pytest.fixture(autouse=True)
def reset_logger() -> Generator[None]:
    """テスト後にロガーをリセット"""
    yield
    logger = logging.getLogger("mixseek.member_agents")
    logger.handlers.clear()


class TestMemberAgentLoggerInit:
    """初期化テスト"""

    def test_no_args_constructor(self) -> None:
        """引数なしで初期化できる"""
        mal = MemberAgentLogger()
        assert mal.logger.name == "mixseek.member_agents"

    def test_no_own_handlers(self) -> None:
        """独自ハンドラを追加しない（統一ロガーに委譲）"""
        # 事前にハンドラをクリア
        logger = logging.getLogger("mixseek.member_agents")
        logger.handlers.clear()

        mal = MemberAgentLogger()
        # MemberAgentLogger 自身はハンドラを追加しない
        assert len(mal.logger.handlers) == 0


class TestLogExecutionStart:
    """log_execution_start テスト"""

    def test_returns_execution_id(self) -> None:
        mal = MemberAgentLogger()
        eid = mal.log_execution_start("agent1", "plain", "task", "model1")
        assert isinstance(eid, str)
        assert len(eid) == 8

    def test_uses_extra_dict(self) -> None:
        """extra dict 方式で構造化データを渡す（JSON文字列埋め込みではない）"""
        mal = MemberAgentLogger()
        handler = logging.Handler()
        handler.setLevel(logging.DEBUG)
        records: list[logging.LogRecord] = []
        handler.emit = lambda record: records.append(record)  # type: ignore[method-assign]
        mal.logger.addHandler(handler)
        mal.logger.setLevel(logging.DEBUG)

        mal.log_execution_start("agent1", "plain", "test task", "model1")

        assert len(records) == 1
        record = records[0]
        # メッセージに { を含まない（JSON二重エンコード防止）
        assert "{" not in record.getMessage()
        # extra fields がレコードに設定されている
        assert hasattr(record, "execution_id")


class TestLogExecutionComplete:
    """log_execution_complete テスト"""

    def test_success_logs_info(self) -> None:
        mal = MemberAgentLogger()
        records: list[logging.LogRecord] = []
        handler = logging.Handler()
        handler.setLevel(logging.DEBUG)
        handler.emit = lambda record: records.append(record)  # type: ignore[method-assign]
        mal.logger.addHandler(handler)
        mal.logger.setLevel(logging.DEBUG)

        result = MagicMock()
        result.status = "success"
        result.agent_name = "agent1"
        result.agent_type = "plain"
        result.execution_time_ms = 1000
        result.error_message = None
        result.error_code = None

        mal.log_execution_complete("abc123", result)

        assert len(records) == 1
        assert records[0].levelno == logging.INFO

    def test_error_logs_error(self) -> None:
        mal = MemberAgentLogger()
        records: list[logging.LogRecord] = []
        handler = logging.Handler()
        handler.setLevel(logging.DEBUG)
        handler.emit = lambda record: records.append(record)  # type: ignore[method-assign]
        mal.logger.addHandler(handler)
        mal.logger.setLevel(logging.DEBUG)

        result = MagicMock()
        result.status = "error"
        result.agent_name = "agent1"
        result.agent_type = "plain"
        result.execution_time_ms = 500
        result.error_message = "something failed"
        result.error_code = "ERR001"

        mal.log_execution_complete("abc123", result)

        assert len(records) == 1
        assert records[0].levelno == logging.ERROR


class TestSanitizeParameters:
    """_sanitize_parameters テスト"""

    def test_redacts_sensitive_keys(self) -> None:
        mal = MemberAgentLogger()
        result = mal._sanitize_parameters({"api_key": "secret123", "name": "test"})
        assert result["api_key"] == "[REDACTED]"
        assert result["name"] == "test"

    def test_truncates_long_values(self) -> None:
        mal = MemberAgentLogger()
        long_value = "x" * 200
        result = mal._sanitize_parameters({"data": long_value})
        assert result["data"].endswith("...")
        assert len(result["data"]) == 103  # 100 + "..."
