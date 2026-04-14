"""Member Agent ロギング。

統一ロガー "mixseek.member_agents" を使用する構造化ロギングヘルパー。
独自ハンドラは持たず、親 "mixseek" ロガーに伝搬する。
"""

import logging
import uuid
from pathlib import Path
from typing import Any


class MemberAgentLogger:
    """Member Agent 実行時の構造化ロギング（FR-011準拠）。

    統一ロガー "mixseek.member_agents" を使用し、extra dict 方式で構造化データを渡す。
    フォーマッタ（TextFormatter/JsonFormatter）が出力形式を決定する。
    """

    def __init__(self) -> None:
        """引数なしで初期化。統一ロガーに委譲。"""
        self.logger = logging.getLogger("mixseek.member_agents")

    def log_execution_start(self, agent_name: str, agent_type: str, task: str, model_id: str, **kwargs: Any) -> str:
        """実行開始ログ。execution_id を返す。"""
        execution_id = str(uuid.uuid4())[:8]

        self.logger.info(
            "Execution started",
            extra={
                "event": "execution_start",
                "execution_id": execution_id,
                "agent_name": agent_name,
                "agent_type": agent_type,
                "task_preview": task[:100] + "..." if len(task) > 100 else task,
                "model_id": model_id,
                **kwargs,
            },
        )
        return execution_id

    def log_execution_complete(
        self,
        execution_id: str,
        result: Any,
        usage_info: dict[str, Any] | None = None,
        retry_count: int = 0,
    ) -> None:
        """実行完了ログ。ステータスに応じてログレベルを変更。"""
        extra: dict[str, Any] = {
            "event": "execution_complete",
            "execution_id": execution_id,
            "status": result.status,
            "agent_name": result.agent_name,
            "agent_type": result.agent_type,
            "execution_time_ms": result.execution_time_ms,
            "retry_count": retry_count,
        }

        if usage_info:
            extra["usage"] = usage_info

        if result.error_message:
            extra["error_message"] = result.error_message
            extra["error_code"] = result.error_code

        if result.status == "success":
            self.logger.info("Execution completed", extra=extra)
        elif result.status == "error":
            self.logger.error("Execution failed", extra=extra)
        else:
            self.logger.warning("Execution completed with warnings", extra=extra)

    def log_tool_invocation(
        self, execution_id: str, tool_name: str, parameters: dict[str, Any], execution_time_ms: int, status: str
    ) -> None:
        """ツール使用ログ。"""
        extra: dict[str, Any] = {
            "event": "tool_invocation",
            "execution_id": execution_id,
            "tool_name": tool_name,
            "parameters": self._sanitize_parameters(parameters),
            "execution_time_ms": execution_time_ms,
            "status": status,
        }

        if status == "success":
            self.logger.debug("Tool invoked", extra=extra)
        else:
            self.logger.warning("Tool invocation failed", extra=extra)

    def log_configuration_loaded(
        self, config_path: Path | None, agent_name: str, agent_type: str, model_id: str
    ) -> None:
        """設定ロード完了ログ。"""
        self.logger.debug(
            "Configuration loaded",
            extra={
                "event": "configuration_loaded",
                "config_path": str(config_path) if config_path else None,
                "agent_name": agent_name,
                "agent_type": agent_type,
                "model_id": model_id,
            },
        )

    def log_error(self, execution_id: str, error: Exception, context: dict[str, Any] | None = None) -> None:
        """エラーログ。"""
        extra: dict[str, Any] = {
            "event": "error",
            "execution_id": execution_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
        }

        if context:
            extra["context"] = context

        self.logger.error("Error occurred", extra=extra)

    def _sanitize_parameters(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """パラメータのサニタイズ（センシティブデータをマスク）。"""
        sanitized = {}

        for key, value in parameters.items():
            if any(sensitive in key.lower() for sensitive in ["key", "token", "password", "secret"]):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str) and len(value) > 100:
                sanitized[key] = value[:100] + "..."
            else:
                sanitized[key] = value

        return sanitized
