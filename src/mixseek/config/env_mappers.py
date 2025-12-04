"""Environment variable mapping strategies (Phase 3-2 - Article 10).

Provides Strategy + Factory pattern for environment variable mappings.

Article 10 (DRY) Compliance:
- Eliminates conditional branching duplication in MappedEnvSettingsSource
- Centralizes environment variable mapping logic
- Enables easy extension for new settings classes

Article 11 (Refactoring) Compliance:
- Replaces conditional logic with polymorphism
- No V2 classes created, existing code refactored directly
"""

import os
from abc import ABC, abstractmethod
from typing import Any


class EnvMappingStrategy(ABC):
    """環境変数マッピング戦略の抽象基底クラス。

    各設定クラスに固有の環境変数マッピングロジックを実装します。
    Strategy Patternにより、条件分岐をポリモーフィズムで置き換えます。
    """

    @abstractmethod
    def map(self, data: dict[str, Any]) -> dict[str, Any]:
        """環境変数をマッピング。

        Args:
            data: 既存の設定データ辞書

        Returns:
            マッピング適用後の設定データ辞書
        """
        pass


class OrchestratorEnvMapper(EnvMappingStrategy):
    """Orchestrator用の環境変数マッピング。

    MIXSEEK_WORKSPACE → workspace_path
    Issue #251対応: .envファイルからの読み込みもサポート
    """

    # クリーンアップ対象キー（extra="forbid"対策）
    _SOURCE_KEYS = ("workspace", "mixseek_workspace")

    def map(self, data: dict[str, Any]) -> dict[str, Any]:
        """MIXSEEK_WORKSPACEをworkspace_pathにマッピング。

        Args:
            data: 既存の設定データ辞書

        Returns:
            マッピング適用後の設定データ辞書
        """
        # 1. すべてのソースキーをpop（短絡評価を避け、確実にクリーンアップ）
        workspace_val = data.pop("workspace", None)
        mixseek_workspace_val = data.pop("mixseek_workspace", None)

        # 2. workspace_pathが未設定の場合のみマッピング適用
        if "workspace_path" not in data or data["workspace_path"] is None:
            env_val = workspace_val or mixseek_workspace_val
            # 環境変数から直接取得（環境変数として設定されている場合）
            if not env_val:
                env_val = os.environ.get("MIXSEEK_WORKSPACE")
            if env_val:
                data["workspace_path"] = env_val

        return data


class UIEnvMapper(EnvMappingStrategy):
    """UI用の環境変数マッピング（優先度付き）。

    優先順位: MIXSEEK_UI__WORKSPACE > MIXSEEK_WORKSPACE → workspace_path
    Issue #251対応: .envファイルからの読み込みもサポート
    """

    # クリーンアップ対象キー（extra="forbid"対策）
    _SOURCE_KEYS = ("workspace", "mixseek_workspace", "ui__workspace", "mixseek_ui__workspace")

    def map(self, data: dict[str, Any]) -> dict[str, Any]:
        """UI固有の環境変数を優先してworkspace_pathにマッピング。

        Args:
            data: 既存の設定データ辞書

        Returns:
            マッピング適用後の設定データ辞書
        """
        # 1. すべてのソースキーをpop（短絡評価を避け、確実にクリーンアップ）
        # env_prefix="MIXSEEK_UI__"の場合: MIXSEEK_UI__WORKSPACE → "workspace"
        # env_prefix=""の場合: MIXSEEK_UI__WORKSPACE → "mixseek_ui__workspace"
        workspace_val = data.pop("workspace", None)
        mixseek_ui_workspace_val = data.pop("mixseek_ui__workspace", None)
        ui_workspace_val = data.pop("ui__workspace", None)
        mixseek_workspace_val = data.pop("mixseek_workspace", None)

        # 2. workspace_pathが未設定の場合のみマッピング適用
        if "workspace_path" not in data or data["workspace_path"] is None:
            # 優先順位: UI固有 > 共通
            env_val = workspace_val or mixseek_ui_workspace_val or ui_workspace_val or mixseek_workspace_val
            # 環境変数から直接取得（環境変数として設定されている場合）
            if not env_val:
                env_val = os.environ.get("MIXSEEK_UI__WORKSPACE") or os.environ.get("MIXSEEK_WORKSPACE")
            if env_val:
                data["workspace_path"] = env_val

        return data


class EnvMapperFactory:
    """環境変数マッパーのファクトリー。

    設定クラス名に基づいて適切なマッピング戦略を返します。
    新しい設定クラスの追加は_mappersに登録するだけで完了します（Open/Closed Principle）。
    """

    _mappers: dict[str, EnvMappingStrategy] = {
        "OrchestratorSettings": OrchestratorEnvMapper(),
        "UISettings": UIEnvMapper(),
    }

    @classmethod
    def get_mapper(cls, settings_cls_name: str) -> EnvMappingStrategy | None:
        """設定クラス名に対応するマッパーを取得。

        Args:
            settings_cls_name: 設定クラス名（例: "OrchestratorSettings"）

        Returns:
            対応するマッパー、または未登録の場合はNone
        """
        return cls._mappers.get(settings_cls_name)
