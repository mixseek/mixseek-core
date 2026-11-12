"""Logfire Observability設定。

環境変数から設定を読み込み、from_toml() は廃止。
file_output フィールドは削除（ファイル出力は LoggingConfig.file_enabled で一元管理）。
"""

import logging
import os
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class LogfirePrivacyMode(str, Enum):
    """Logfireプライバシーモード。

    Attributes:
        FULL: すべてキャプチャ（開発用）- プロンプト、応答、HTTPリクエストを含む
        METADATA_ONLY: メトリクスのみ（本番推奨）- プロンプト/応答を除外
        DISABLED: Logfire無効
    """

    FULL = "full"
    METADATA_ONLY = "metadata_only"
    DISABLED = "disabled"


class LogfireConfig(BaseModel):
    """Logfire設定。

    Attributes:
        enabled: Logfire有効化フラグ
        privacy_mode: プライバシーモード
        capture_http: HTTPリクエスト/レスポンスキャプチャ有効化
        project_name: Logfireプロジェクト名（オプション）
        send_to_logfire: Logfireクラウドへの送信有効化
        console_output: Logfireスパンのコンソール出力有効化（text モードの ConsoleOptions 制御）
        json_span_log: json モードでスパンを JsonSpanProcessor 経由でログ出力するか
            （text モードでは無視）
    """

    enabled: bool
    privacy_mode: LogfirePrivacyMode
    capture_http: bool
    project_name: str | None
    send_to_logfire: bool
    console_output: bool = Field(default=True)
    json_span_log: bool = Field(default=True)

    @classmethod
    def from_env(cls) -> "LogfireConfig":
        """環境変数から設定を読み込み。

        環境変数:
            LOGFIRE_ENABLED: "1"で有効化
            LOGFIRE_PRIVACY_MODE: "full", "metadata_only", "disabled"
            LOGFIRE_CAPTURE_HTTP: "1"で有効化
            LOGFIRE_PROJECT: プロジェクト名
            LOGFIRE_SEND_TO_LOGFIRE: "1"で有効化（デフォルト: "1"）
            MIXSEEK_LOG_CONSOLE: コンソール出力有効化（true/false/1/0）
            MIXSEEK_JSON_SPAN_LOG: json モードのスパンJSON出力有効化（true/false/1/0、デフォルト: true）
        """
        enabled = os.getenv("LOGFIRE_ENABLED") == "1"
        privacy_str = os.getenv("LOGFIRE_PRIVACY_MODE", "metadata_only")
        privacy_mode = LogfirePrivacyMode(privacy_str)
        capture_http = os.getenv("LOGFIRE_CAPTURE_HTTP") == "1"
        project_name = os.getenv("LOGFIRE_PROJECT")
        send_to_logfire_str = os.getenv("LOGFIRE_SEND_TO_LOGFIRE", "1")
        send_to_logfire = send_to_logfire_str == "1"

        # コンソール出力設定（LoggingConfigと共通の環境変数）
        console_str = os.getenv("MIXSEEK_LOG_CONSOLE", "true").lower()
        console_output = console_str in ("true", "1")

        return cls(
            enabled=enabled,
            privacy_mode=privacy_mode,
            capture_http=capture_http,
            project_name=project_name,
            send_to_logfire=send_to_logfire,
            console_output=console_output,
            json_span_log=json_span_log_from_env(),
        )


def json_span_log_from_env() -> bool:
    """MIXSEEK_JSON_SPAN_LOG を読み取る。未設定・空文字は true（後方互換）。

    不正値は警告を出して true（現状維持）にフォールバックする。
    観測設定の書き間違いで CLI 本体を停止させず、かつ黙って無効化もしないため。
    """
    raw = os.getenv("MIXSEEK_JSON_SPAN_LOG", "")
    value = raw.strip().lower()
    if value in ("", "true", "1"):
        return True
    if value in ("false", "0"):
        return False
    # 構造化ログ: 環境変数名と不正値を extra で明示し、JsonFormatter でフィールド化する
    logger.warning(
        "Invalid MIXSEEK_JSON_SPAN_LOG value; falling back to true. Valid values: true, false, 1, 0",
        extra={"env_var": "MIXSEEK_JSON_SPAN_LOG", "value": raw},
    )
    return True
