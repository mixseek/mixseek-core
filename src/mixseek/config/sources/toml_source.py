"""Custom TOML configuration source for Pydantic Settings.

.. note:: T089移行完了
    環境変数アクセスは呼び出し側（MixSeekBaseSettings.settings_customise_sources）に移動しました。
"""

import tomllib
from pathlib import Path
from typing import Any

from pydantic.fields import FieldInfo
from pydantic_settings import PydanticBaseSettingsSource


def _validate_safe_path(path: Path) -> None:
    """Validate that a path is safe and prevent path traversal attacks.

    Args:
        path: Path to validate

    Raises:
        ValueError: If path is unsafe (contains path traversal sequences)
    """
    # Resolve to absolute path to detect traversal attempts
    try:
        path.resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError("Invalid file path: cannot resolve path") from e

    # Ensure the path doesn't contain dangerous sequences
    if ".." in path.parts:
        raise ValueError("Invalid file path: path traversal detected")

    # Security check: ensure path is within reasonable bounds
    # (Optional: add workspace boundary checks if needed)


def _sanitize_error_message(message: str) -> str:
    """Sanitize error messages to avoid leaking sensitive information.

    Args:
        message: Original error message

    Returns:
        Sanitized error message
    """
    # Remove full file paths from error messages
    import re

    # Replace absolute paths with generic indicator
    sanitized = re.sub(r"/[a-z0-9/_.-]+", "<path>", message)

    # Remove home directory paths
    home = str(Path.home())
    sanitized = sanitized.replace(home, "<home>")

    # Remove temporary directory paths
    import tempfile

    temp_dir = tempfile.gettempdir()
    sanitized = sanitized.replace(temp_dir, "<temp>")

    return sanitized


class CustomTomlConfigSettingsSource(PydanticBaseSettingsSource):
    """カスタム TOML ファイル設定ソース。

    config.toml ファイルから設定を読み込みます。
    Pydantic の TomlConfigSettingsSource の代わりに使用します。

    .. note:: T089移行完了
        環境変数アクセスは呼び出し側（MixSeekBaseSettings.settings_customise_sources）に移動しました。
        ソースは渡されたconfig_file_pathパラメータのみを使用します。
    """

    def __init__(self, settings_cls: type, config_file_path: Path | str | None = None) -> None:
        """初期化。

        Args:
            settings_cls: 設定クラス
            config_file_path: TOMLファイルパス（Path or str）（T089: 環境変数アクセスは呼び出し側で実施）

        Note:
            config_file_pathが未指定の場合、後方互換性のため環境変数MIXSEEK_CONFIG_FILEを
            フォールバックとして読み込みます。通常の使用（MixSeekBaseSettingsから呼び出される）
            では、環境変数は既に読み込まれてconfig_file_pathとして渡されます。
            文字列が渡された場合は自動的にPathオブジェクトに変換されます（T089 fix）。
        """
        super().__init__(settings_cls)

        # T089: 後方互換性のためのフォールバック（直接インスタンス化時のテスト等）
        if config_file_path is None:
            import os

            config_file_env = os.environ.get("MIXSEEK_CONFIG_FILE")
            self.config_file_path = Path(config_file_env) if config_file_env else None
        else:
            # T089 fix: 文字列もPathオブジェクトに変換（型安全性）
            self.config_file_path = Path(config_file_path)

        self.toml_data: dict[str, Any] = {}
        self._load_toml()

    def _load_toml(self) -> None:
        """TOML ファイルを読み込み。

        コンストラクタで渡されたconfig_file_path、または
        デフォルトの config.toml ファイルを読み込みます。
        ファイルが存在しない場合は何もしません。

        .. note:: T089移行完了
            環境変数 MIXSEEK_CONFIG_FILE の読み込みは呼び出し側（MixSeekBaseSettings）で実施されます。
            このメソッドは渡されたパスのみを使用します。

        優先順位（呼び出し側で決定）:
        1. MIXSEEK_CONFIG_FILE 環境変数で明示的に指定されたファイル
        2. カレントディレクトリの config.toml

        Raises:
            ValueError: パス検証エラー（パストラバーサル検出）
            Exception: TOML ファイルの構文エラー
        """
        # T089: config_file_pathパラメータを使用（環境変数アクセスは呼び出し側で実施済み）
        if self.config_file_path is not None:
            config_file = self.config_file_path
        else:
            # デフォルトは config.toml（spec.md:258）
            config_file = Path("config.toml")

        # セキュリティ: パス検証（パストラバーサル攻撃の防止）
        try:
            _validate_safe_path(config_file)
        except ValueError as e:
            raise ValueError(_sanitize_error_message(str(e))) from e

        # ファイルが存在しない場合は何もしない
        if not config_file.exists():
            return

        # TOML ファイルを読み込み
        try:
            with open(config_file, "rb") as f:
                toml_data = tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError) as e:
            # エラーメッセージをサニタイズしてから例外を発生
            raise type(e)(_sanitize_error_message(str(e))) from e

        # 設定クラス名でセクションを探す
        section_name = self.settings_cls.__name__
        self.toml_data = toml_data.get(section_name, {})

        # フォールバック: 小文字のセクション名も試す
        # 例: OrchestratorSettings -> orchestrator
        if not self.toml_data and section_name.endswith("Settings"):
            lowercase_section = section_name.replace("Settings", "").lower()
            self.toml_data = toml_data.get(lowercase_section, {})

        # 公式TOMLキー 'workspace' を内部フィールド 'workspace_path' にマッピング
        #
        # 設計思想:
        #   - ユーザー向けAPI: TOMLキー 'workspace' (公式キー)
        #   - 内部Pydanticフィールド: 'workspace_path' (実装詳細)
        #
        # このマッピングにより、ユーザーはTOMLファイルで直感的な 'workspace' キーを使用でき、
        # 内部的にはPydanticのフィールド名 'workspace_path' に正規化されます。
        if section_name in ("OrchestratorSettings", "UISettings"):
            if "workspace" in self.toml_data and "workspace_path" not in self.toml_data:
                self.toml_data["workspace_path"] = self.toml_data["workspace"]
                # extra="forbid"対策: 元のキーを削除（Pydanticは'workspace'を認識しないため）
                del self.toml_data["workspace"]

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        """フィールド値を取得。

        Args:
            field: フィールド情報
            field_name: フィールド名

        Returns:
            (値, キー, 値が見つかったかどうか) のタプル
        """
        value = self.toml_data.get(field_name)
        return value, field_name, value is not None

    def prepare_field_value(
        self,
        field_name: str,
        field: FieldInfo,
        value: Any,
        value_is_complex: bool,
    ) -> Any:
        """値の前処理。

        Args:
            field_name: フィールド名
            field: フィールド情報
            value: 値
            value_is_complex: 複雑な値かどうか

        Returns:
            処理済みの値
        """
        return value

    def __call__(self) -> dict[str, Any]:
        """すべてのフィールド値を取得。

        Returns:
            TOML から読み込んだ値の辞書
        """
        return self.toml_data
