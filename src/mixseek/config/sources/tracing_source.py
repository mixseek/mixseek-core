"""Tracing and source tracking for configuration values."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic.fields import FieldInfo
from pydantic_settings import PydanticBaseSettingsSource


@dataclass(frozen=True)
class SourceTrace:
    """設定値のトレース情報を保持するデータクラス。

    どのソースから値が読み込まれたか、いつ読み込まれたかを記録します。
    イミュータブル（frozen=True）であり、一度作成されたら変更不可です。

    Attributes:
        value: 設定値（読み込まれた値）
        source_name: ソース名（例: "config.toml", "environment_variables", "init"）
        source_type: ソースタイプ（"cli", "env", "toml", "dotenv", "secrets"）
        field_name: フィールド名（例: "model", "timeout_seconds"）
        timestamp: 読み込み日時（UTC）
    """

    value: Any
    source_name: str
    source_type: str
    field_name: str
    timestamp: datetime

    def __post_init__(self) -> None:
        """バリデーション後の処理。タイムスタンプがUTCであることを確認します。"""
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware (use datetime.now(UTC))")


class TracingSourceWrapper(PydanticBaseSettingsSource):
    """既存の設定ソースをラップし、トレース情報を記録するカスタム設定ソース。

    すべての設定値の出所を追跡可能にします。

    Attributes:
        wrapped_source: ラップ対象のソース
        source_name: ソース名（例: "config.toml", "environment_variables"）
        source_type: ソースタイプ（"cli", "env", "toml", "dotenv", "secrets"）
        trace_storage: トレース情報を保存する辞書
    """

    def __init__(
        self,
        settings_cls: type,
        wrapped_source: PydanticBaseSettingsSource,
        source_name: str,
        source_type: str,
        trace_storage: dict[str, SourceTrace] | None = None,
    ) -> None:
        """初期化。

        Args:
            settings_cls: 設定クラス
            wrapped_source: ラップ対象のソース
            source_name: ソース名
            source_type: ソースタイプ
            trace_storage: トレース情報を保存する辞書。Noneの場合は新規作成。
        """
        super().__init__(settings_cls)
        self.wrapped_source = wrapped_source
        self.source_name = source_name
        self.source_type = source_type
        self.trace_storage = trace_storage if trace_storage is not None else {}

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        """ラップされたソースから値を取得し、トレース情報を記録。

        Args:
            field: フィールド情報
            field_name: フィールド名

        Returns:
            (値, キー, 値が見つかったかどうか) のタプル
        """
        value, key, value_is_set = self.wrapped_source.get_field_value(field, field_name)

        if value_is_set:
            # トレース情報を記録
            self.trace_storage[field_name] = SourceTrace(
                value=value,
                source_name=self.source_name,
                source_type=self.source_type,
                field_name=field_name,
                timestamp=datetime.now(UTC),
            )

        return value, key, value_is_set

    def prepare_field_value(
        self,
        field_name: str,
        field_info: Any,
        value: Any,
        value_is_complex: bool,
    ) -> Any:
        """値の前処理。ラップされたソースに委譲。

        Args:
            field_name: フィールド名
            field_info: フィールド情報
            value: 値
            value_is_complex: 複雑な値かどうか

        Returns:
            処理済みの値
        """
        return self.wrapped_source.prepare_field_value(field_name, field_info, value, value_is_complex)

    def __call__(self) -> dict[str, Any]:
        """すべてのフィールドの値を取得。

        ラップされたソースから値を取得し、トレース情報を記録します。
        優先順位チェーンに従い、最初に値を提供したソースのみをトレース記録します。
        つまり、すでにトレース記録されたフィールドは上書きしません。

        Returns:
            ラップされたソースから読み込んだ値の辞書
        """
        data = self.wrapped_source()

        # ラップされたソースから返された値のトレース情報を記録
        # 優先順位: すでにトレース記録されたフィールドは上書きしない
        for field_name, value in data.items():
            # この値が実際に使用される場合のみトレース記録
            # （優先順位で先行するソースがすでに値を提供していれば、
            # このソースの値は無視されるため、トレース記録する必要がない）
            if field_name not in self.trace_storage:
                self.trace_storage[field_name] = SourceTrace(
                    value=value,
                    source_name=self.source_name,
                    source_type=self.source_type,
                    field_name=field_name,
                    timestamp=datetime.now(UTC),
                )

        return data

    def __repr__(self) -> str:
        """文字列表現。

        Returns:
            TracingSourceWrapperの文字列表現
        """
        return f"TracingSourceWrapper({self.source_name}, wrapped={self.wrapped_source})"
