"""標準ロギング設定。

CLIフラグ > 環境変数 > デフォルト値の優先度で設定を解決する。
"""

import os
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# 有効なログレベル
LevelName = Literal["debug", "info", "warning", "error", "critical"]

VALID_LOG_LEVELS: tuple[LevelName, ...] = ("debug", "info", "warning", "error", "critical")

# ログ出力形式
LogFormatType = Literal["text", "json"]


class LoggingConfig(BaseModel):
    """標準ロギング設定。

    Attributes:
        logfire_enabled: Logfire転送有効化（--logfireフラグで制御）
        console_enabled: コンソール出力（stderr）の有効化
        file_enabled: ファイル出力（$MIXSEEK_WORKSPACE/logs/mixseek.log）の有効化
        log_level: グローバルログレベル
        log_format: ログ出力形式（text/json）
    """

    logfire_enabled: bool = Field(default=False)
    console_enabled: bool = Field(default=True)
    file_enabled: bool = Field(default=True)
    log_level: LevelName = Field(default="info")
    log_format: LogFormatType = Field(default="text")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """ログレベルのバリデーション。"""
        if v not in VALID_LOG_LEVELS:
            raise ValueError(f"Invalid log level: '{v}'. Valid values: {list(VALID_LOG_LEVELS)}")
        return v

    @classmethod
    def from_env(cls) -> "LoggingConfig":
        """環境変数から設定を読み込み。

        環境変数:
            MIXSEEK_LOG_LEVEL: ログレベル（debug/info/warning/error/critical）
            MIXSEEK_LOG_CONSOLE: コンソール出力（true/false/1/0）
            MIXSEEK_LOG_FILE: ファイル出力（true/false/1/0）
            MIXSEEK_LOG_FORMAT: ログ出力形式（text/json）
        """
        # ログレベル
        log_level_str = os.getenv("MIXSEEK_LOG_LEVEL", "info").lower()
        if log_level_str not in VALID_LOG_LEVELS:
            raise ValueError(f"Invalid log level: '{log_level_str}'. Valid values: {list(VALID_LOG_LEVELS)}")
        log_level: LevelName = log_level_str  # type: ignore[assignment]

        # ブール値
        console_str = os.getenv("MIXSEEK_LOG_CONSOLE", "true").lower()
        console_enabled = console_str in ("true", "1")

        file_str = os.getenv("MIXSEEK_LOG_FILE", "true").lower()
        file_enabled = file_str in ("true", "1")

        # ログ出力形式
        log_format_str = os.getenv("MIXSEEK_LOG_FORMAT", "text").lower()
        log_format: LogFormatType = log_format_str if log_format_str in ("text", "json") else "text"  # type: ignore[assignment]

        return cls(
            logfire_enabled=False,  # CLIフラグでのみ設定
            console_enabled=console_enabled,
            file_enabled=file_enabled,
            log_level=log_level,
            log_format=log_format,
        )
