"""CLI argument source for Pydantic Settings."""

from typing import Any

from pydantic.fields import FieldInfo
from pydantic_settings import PydanticBaseSettingsSource


class CLISource(PydanticBaseSettingsSource):
    """CLI引数から設定を読み込むカスタム設定ソース。

    pydantic-settingsの`PydanticBaseSettingsSource`を継承し、typerなどの
    CLIフレームワークとの統合を実現します。

    Attributes:
        cli_args: CLI引数（typerから渡される辞書）
    """

    def __init__(
        self,
        settings_cls: type,
        cli_args: dict[str, Any] | None = None,
    ) -> None:
        """初期化。

        Args:
            settings_cls: 設定クラス
            cli_args: CLI引数の辞書。Noneの場合は空辞書として扱う。
        """
        super().__init__(settings_cls)
        self.cli_args = cli_args or {}

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        """CLI引数から値を取得。

        CLI引数名のマッピング（例: timeout_seconds → timeout）をサポート。

        Args:
            field: フィールド情報
            field_name: フィールド名

        Returns:
            (値, キー, 値が見つかったかどうか) のタプル
        """
        # CLI引数名のマッピング（アンダースコア→ハイフン）
        cli_name = field_name.replace("_", "-")

        # 値を検索（フィールド名とCLI名の両方を確認）
        if field_name in self.cli_args:
            value = self.cli_args[field_name]
            return value, field_name, True
        elif cli_name in self.cli_args:
            value = self.cli_args[cli_name]
            return value, field_name, True

        return None, field_name, False

    def prepare_field_value(
        self,
        field_name: str,
        field_info: Any,
        value: Any,
        value_is_complex: bool,
    ) -> Any:
        """値の前処理。

        Args:
            field_name: フィールド名
            field_info: フィールド情報
            value: 値
            value_is_complex: 複雑な値かどうか

        Returns:
            処理済みの値
        """
        if value is None:
            return None
        return value

    def __call__(self) -> dict[str, Any]:
        """すべてのフィールドの値を取得。

        Returns:
            CLI引数から読み込んだ値の辞書
        """
        d: dict[str, Any] = {}
        for field_name, field_info in self.settings_cls.model_fields.items():
            value, key, value_is_set = self.get_field_value(field_info, field_name)
            if value_is_set and value is not None:
                d[key] = value
        return d

    def __repr__(self) -> str:
        """文字列表現。

        Returns:
            CLISourceの文字列表現
        """
        return f"CLISource(args={len(self.cli_args)} items)"
