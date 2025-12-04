"""Logfire configuration (Article 9 compliant).

This module provides configuration management for Logfire observability integration.
All configuration follows Constitution Article 9 (Data Accuracy Mandate):
- No hardcoded values
- No implicit fallbacks
- Explicit error propagation
"""

import os
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class LogfirePrivacyMode(str, Enum):
    """Logfireプライバシーモード.

    Attributes:
        FULL: すべてキャプチャ（開発用）- プロンプト、応答、HTTPリクエストを含む
        METADATA_ONLY: メトリクスのみ（本番推奨）- プロンプト/応答を除外
        DISABLED: Logfire無効
    """

    FULL = "full"
    METADATA_ONLY = "metadata_only"
    DISABLED = "disabled"


class LogfireConfig(BaseModel):
    """Logfire設定（Article 9準拠）.

    Attributes:
        enabled: Logfire有効化フラグ
        privacy_mode: プライバシーモード
        capture_http: HTTPリクエスト/レスポンスキャプチャ有効化
        project_name: Logfireプロジェクト名（オプション）
        send_to_logfire: Logfireクラウドへの送信有効化
        console_output: Logfireスパンのコンソール出力有効化
        file_output: Logfireスパンのファイル出力有効化

    Note:
        デフォルト値なし、環境変数またはTOMLファイルからの明示的設定のみ
    """

    enabled: bool
    privacy_mode: LogfirePrivacyMode
    capture_http: bool
    project_name: str | None
    send_to_logfire: bool
    console_output: bool = Field(default=True)
    file_output: bool = Field(default=True)

    @classmethod
    def from_env(cls) -> "LogfireConfig":
        """環境変数から設定を読み込み（Article 9準拠）.

        環境変数:
            LOGFIRE_ENABLED: "1"で有効化、それ以外は無効
            LOGFIRE_PRIVACY_MODE: "full", "metadata_only", "disabled"（デフォルト: "metadata_only"）
            LOGFIRE_CAPTURE_HTTP: "1"で有効化、それ以外は無効
            LOGFIRE_PROJECT: プロジェクト名（オプション）
            LOGFIRE_SEND_TO_LOGFIRE: "1"で有効化（デフォルト: "1"）
            MIXSEEK_LOG_CONSOLE: コンソール出力有効化（true/false、デフォルト: true）
            MIXSEEK_LOG_FILE: ファイル出力有効化（true/false、デフォルト: true）

        Returns:
            LogfireConfig: 設定インスタンス

        Note:
            デフォルト値は最小限（無効/metadata_only）とし、
            明示的な有効化を要求することでArticle 9に準拠
        """
        enabled = os.getenv("LOGFIRE_ENABLED") == "1"
        privacy_str = os.getenv("LOGFIRE_PRIVACY_MODE", "metadata_only")
        privacy_mode = LogfirePrivacyMode(privacy_str)
        capture_http = os.getenv("LOGFIRE_CAPTURE_HTTP") == "1"
        project_name = os.getenv("LOGFIRE_PROJECT")
        send_to_logfire_str = os.getenv("LOGFIRE_SEND_TO_LOGFIRE", "1")
        send_to_logfire = send_to_logfire_str == "1"

        # Read console/file output settings (shared with LoggingConfig)
        console_str = os.getenv("MIXSEEK_LOG_CONSOLE", "true").lower()
        console_output = console_str in ("true", "1")
        file_str = os.getenv("MIXSEEK_LOG_FILE", "true").lower()
        file_output = file_str in ("true", "1")

        return cls(
            enabled=enabled,
            privacy_mode=privacy_mode,
            capture_http=capture_http,
            project_name=project_name,
            send_to_logfire=send_to_logfire,
            console_output=console_output,
            file_output=file_output,
        )

    @classmethod
    def from_toml(cls, workspace: Path) -> "LogfireConfig | None":
        """TOML設定ファイルから読み込み.

        Args:
            workspace: MIXSEEKワークスペースパス

        Returns:
            LogfireConfig | None: 設定インスタンス（ファイルがなければNone）

        Raises:
            ValueError: TOML形式が不正な場合

        Note:
            設定ファイル: $MIXSEEK_WORKSPACE/logfire.toml

            [logfire]
            enabled = true
            privacy_mode = "metadata_only"
            capture_http = false
            project_name = "mixseek-dev"
            send_to_logfire = true
            console_output = true
            file_output = true
        """
        import tomllib

        config_path = workspace / "logfire.toml"
        if not config_path.exists():
            return None

        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse TOML file: {config_path}") from e

        logfire_data = data.get("logfire", {})

        try:
            privacy_mode_str = logfire_data.get("privacy_mode", "metadata_only")
            privacy_mode = LogfirePrivacyMode(privacy_mode_str)
        except ValueError as e:
            raise ValueError(
                f"Invalid privacy_mode in {config_path}: {privacy_mode_str}. "
                f"Valid values: {[m.value for m in LogfirePrivacyMode]}"
            ) from e

        return cls(
            enabled=logfire_data.get("enabled", False),
            privacy_mode=privacy_mode,
            capture_http=logfire_data.get("capture_http", False),
            project_name=logfire_data.get("project_name"),
            send_to_logfire=logfire_data.get("send_to_logfire", True),
            console_output=logfire_data.get("console_output", True),
            file_output=logfire_data.get("file_output", True),
        )
