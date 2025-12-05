"""Unit tests for environment variable mapping (Phase 3).

Article 3準拠: リファクタリング前にテストファーストで既存動作を保証。
Phase 3-1: 環境変数マッピングのStrategy + Factoryパターン化のテスト。
"""

from pathlib import Path
from typing import Any

import pytest

from mixseek.config.schema import MappedEnvSettingsSource, OrchestratorSettings, UISettings

# ==========================================
# TestMappedEnvSettingsSourceExistingBehavior
# ==========================================


class TestMappedEnvSettingsSourceExistingBehavior:
    """MappedEnvSettingsSourceの既存動作テスト（リファクタリング前の動作保証）。"""

    def test_orchestrator_settings_maps_mixseek_workspace(
        self,
        tmp_path: Path,
        monkeypatch: Any,
    ) -> None:
        """OrchestratorSettingsでMIXSEEK_WORKSPACEがworkspace_pathにマッピングされることを確認。"""
        # Arrange
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))

        # Act
        source = MappedEnvSettingsSource(OrchestratorSettings, case_sensitive=False)
        data = source()

        # Assert
        assert "workspace_path" in data
        assert data["workspace_path"] == str(workspace)

    def test_orchestrator_settings_no_mapping_if_workspace_path_already_set(
        self,
        tmp_path: Path,
        monkeypatch: Any,
    ) -> None:
        """workspace_pathが既に設定されている場合、マッピングしないことを確認。"""
        # Arrange
        workspace1 = tmp_path / "workspace1"
        workspace1.mkdir()
        workspace2 = tmp_path / "workspace2"
        workspace2.mkdir()

        # workspace_pathが既に設定されている状態をシミュレート
        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(workspace1))
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace2))

        # Act
        source = MappedEnvSettingsSource(OrchestratorSettings, case_sensitive=False)
        data = source()

        # Assert: MIXSEEK_WORKSPACE_PATHが優先される（マッピングされない）
        assert data["workspace_path"] == str(workspace1)

    def test_ui_settings_maps_mixseek_ui_workspace_with_priority(
        self,
        tmp_path: Path,
        monkeypatch: Any,
    ) -> None:
        """UISettingsでMIXSEEK_UI__WORKSPACEとMIXSEEK_WORKSPACEの優先順位を確認。"""
        # Arrange
        workspace_common = tmp_path / "workspace_common"
        workspace_common.mkdir()
        workspace_ui = tmp_path / "workspace_ui"
        workspace_ui.mkdir()

        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace_common))
        monkeypatch.setenv("MIXSEEK_UI__WORKSPACE", str(workspace_ui))

        # Act
        source = MappedEnvSettingsSource(UISettings, case_sensitive=False)
        data = source()

        # Assert: UI固有の環境変数が優先される
        assert "workspace_path" in data
        assert data["workspace_path"] == str(workspace_ui)

    def test_ui_settings_fallback_to_mixseek_workspace(
        self,
        tmp_path: Path,
        monkeypatch: Any,
    ) -> None:
        """UISettingsでMIXSEEK_UI__WORKSPACEがない場合、MIXSEEK_WORKSPACEにフォールバックすることを確認。"""
        # Arrange
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))

        # Act
        source = MappedEnvSettingsSource(UISettings, case_sensitive=False)
        data = source()

        # Assert
        assert "workspace_path" in data
        assert data["workspace_path"] == str(workspace)

    def test_no_mapping_for_unknown_settings_class(
        self,
        tmp_path: Path,
        monkeypatch: Any,
    ) -> None:
        """未知の設定クラスでは環境変数マッピングが行われないことを確認。"""
        # Arrange
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))

        # LeaderAgentSettingsなど、workspace_pathを持たない設定クラス
        from mixseek.config.schema import LeaderAgentSettings

        # Act
        source = MappedEnvSettingsSource(LeaderAgentSettings, case_sensitive=False)
        data = source()

        # Assert: workspace_pathが追加されていない
        assert "workspace_path" not in data

    def test_mapping_preserves_other_env_vars(
        self,
        tmp_path: Path,
        monkeypatch: Any,
    ) -> None:
        """環境変数マッピングが他の環境変数を保持することを確認。"""
        # Arrange
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))
        monkeypatch.setenv("MIXSEEK_TIMEOUT_PER_TEAM_SECONDS", "999")

        # Act
        source = MappedEnvSettingsSource(OrchestratorSettings, case_sensitive=False)
        data = source()

        # Assert: 両方の環境変数が取得される
        assert "workspace_path" in data
        assert data["workspace_path"] == str(workspace)
        assert "timeout_per_team_seconds" in data
        assert data["timeout_per_team_seconds"] == "999"

    def test_empty_env_var_not_mapped(
        self,
        monkeypatch: Any,
    ) -> None:
        """空文字列の環境変数がマッピングされないことを確認。"""
        # Arrange: 環境変数を空文字列に設定
        monkeypatch.setenv("MIXSEEK_WORKSPACE", "")

        # Act
        source = MappedEnvSettingsSource(OrchestratorSettings, case_sensitive=False)
        data = source()

        # Assert: 空文字列はマッピングされない
        assert "workspace_path" not in data or data["workspace_path"] == ""


# ==========================================
# TestEnvMappingStrategyPattern (Phase 3-2後にアクティブ化)
# ==========================================


class TestEnvMappingStrategyPattern:
    """EnvMappingStrategyパターンのテスト（Phase 3-2実装後）。

    Note: このテストクラスはPhase 3-2でenv_mappers.py実装後にアクティブ化されます。
    """

    @pytest.mark.skip(reason="Phase 3-2: env_mappers.py implementation pending")
    def test_orchestrator_env_mapper_maps_workspace(
        self,
        tmp_path: Path,
    ) -> None:
        """OrchestratorEnvMapperがworkspace_pathをマッピングすることを確認。"""
        # このテストはPhase 3-2で実装されます
        pass

    @pytest.mark.skip(reason="Phase 3-2: env_mappers.py implementation pending")
    def test_ui_env_mapper_priority(
        self,
        tmp_path: Path,
    ) -> None:
        """UIEnvMapperが優先順位を正しく処理することを確認。"""
        # このテストはPhase 3-2で実装されます
        pass

    @pytest.mark.skip(reason="Phase 3-2: env_mappers.py implementation pending")
    def test_env_mapper_factory_returns_correct_mapper(self) -> None:
        """EnvMapperFactoryが正しいマッパーを返すことを確認。"""
        # このテストはPhase 3-2で実装されます
        pass

    @pytest.mark.skip(reason="Phase 3-2: env_mappers.py implementation pending")
    def test_env_mapper_factory_returns_none_for_unknown_class(self) -> None:
        """EnvMapperFactoryが未知のクラスに対してNoneを返すことを確認。"""
        # このテストはPhase 3-2で実装されます
        pass


# ==========================================
# TestMappedEnvSettingsSourceRefactored (Phase 3-2後にアクティブ化)
# ==========================================


class TestMappedEnvSettingsSourceRefactored:
    """リファクタリング後のMappedEnvSettingsSourceテスト（Phase 3-2実装後）。

    Note: Phase 3-2でenv_mappers.py実装後、MappedEnvSettingsSourceは
    Factoryパターンを使用するようにリファクタリングされます。
    """

    @pytest.mark.skip(reason="Phase 3-2: Refactoring pending")
    def test_uses_factory_for_mapping(
        self,
        tmp_path: Path,
        monkeypatch: Any,
    ) -> None:
        """MappedEnvSettingsSourceがFactoryを使用してマッピングすることを確認。"""
        # このテストはPhase 3-2で実装されます
        pass


# ==========================================
# TestMappedDotEnvSettingsSourceBehavior (Issue #251)
# ==========================================


class TestMappedDotEnvSettingsSourceBehavior:
    """MappedDotEnvSettingsSourceの動作テスト（Issue #251対応）。"""

    def test_orchestrator_settings_maps_mixseek_workspace_from_dotenv(
        self,
        tmp_path: Path,
        monkeypatch: Any,
    ) -> None:
        """OrchestratorSettingsで.envのMIXSEEK_WORKSPACEがworkspace_pathにマッピングされることを確認。"""
        from mixseek.config.schema import MappedDotEnvSettingsSource

        # Arrange
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # .envファイルを作成
        env_file = tmp_path / ".env"
        env_file.write_text(f"MIXSEEK_WORKSPACE={workspace}\n")

        # 環境変数をクリア（.envファイルのみをテスト）
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

        # Act
        source = MappedDotEnvSettingsSource(
            OrchestratorSettings,
            env_file=str(env_file),
            case_sensitive=False,
            env_prefix="MIXSEEK_",
            env_nested_delimiter="__",
        )
        data = source()

        # Assert
        assert "workspace_path" in data
        assert data["workspace_path"] == str(workspace)

    def test_ui_settings_maps_mixseek_ui_workspace_with_priority_from_dotenv(
        self,
        tmp_path: Path,
        monkeypatch: Any,
    ) -> None:
        """UISettingsで.envのMIXSEEK_UI__WORKSPACEが優先されることを確認。"""
        from mixseek.config.schema import MappedDotEnvSettingsSource

        # Arrange
        workspace_common = tmp_path / "workspace_common"
        workspace_common.mkdir()
        workspace_ui = tmp_path / "workspace_ui"
        workspace_ui.mkdir()

        # .envファイルを作成（両方の環境変数を設定）
        env_file = tmp_path / ".env"
        env_file.write_text(f"MIXSEEK_WORKSPACE={workspace_common}\nMIXSEEK_UI__WORKSPACE={workspace_ui}\n")

        # 環境変数をクリア
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
        monkeypatch.delenv("MIXSEEK_UI__WORKSPACE", raising=False)

        # Act
        source = MappedDotEnvSettingsSource(
            UISettings,
            env_file=str(env_file),
            case_sensitive=False,
            env_prefix="MIXSEEK_UI__",
            env_nested_delimiter="__",
        )
        data = source()

        # Assert: UI固有の環境変数が優先される
        assert "workspace_path" in data
        assert data["workspace_path"] == str(workspace_ui)

    def test_no_mapping_for_unknown_settings_class_from_dotenv(
        self,
        tmp_path: Path,
        monkeypatch: Any,
    ) -> None:
        """未知の設定クラスでは.envからのマッピングが行われないことを確認。"""
        from mixseek.config.schema import LeaderAgentSettings, MappedDotEnvSettingsSource

        # Arrange
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # .envファイルを作成
        env_file = tmp_path / ".env"
        env_file.write_text(f"MIXSEEK_WORKSPACE={workspace}\n")

        # 環境変数をクリア
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)

        # Act
        source = MappedDotEnvSettingsSource(
            LeaderAgentSettings,
            env_file=str(env_file),
            case_sensitive=False,
            env_prefix="MIXSEEK_LEADER__",
            env_nested_delimiter="__",
        )
        data = source()

        # Assert: workspace_pathが追加されていない
        assert "workspace_path" not in data

    def test_dotenv_filters_by_env_prefix(
        self,
        tmp_path: Path,
        monkeypatch: Any,
    ) -> None:
        """env_prefixにマッチしない変数がフィルタリングされることを確認（Issue #2）。"""
        from mixseek.config.schema import MappedDotEnvSettingsSource

        # Arrange
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # .envファイルを作成（複数の環境変数を設定）
        env_file = tmp_path / ".env"
        env_file.write_text(f"MIXSEEK_WORKSPACE={workspace}\nLOGFIRE_TOKEN=test_token\nAWS_ACCESS_KEY_ID=test_key\n")

        # 環境変数をクリア
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)

        # Act
        source = MappedDotEnvSettingsSource(
            OrchestratorSettings,
            env_file=str(env_file),
            case_sensitive=False,
            env_prefix="MIXSEEK_",
            env_nested_delimiter="__",
        )
        data = source()

        # Assert: MIXSEEK_プレフィックスの変数のみ含まれる
        assert "workspace_path" in data  # マッピング後の値
        assert "logfire_token" not in data  # フィルタリングで除外
        assert "aws_access_key_id" not in data  # フィルタリングで除外
