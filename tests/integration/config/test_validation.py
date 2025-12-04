"""Integration tests for User Story 4: Required field validation (T036)."""

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from mixseek.config import OrchestratorSettings


class TestUserStory4Integration:
    """User Story 4のAcceptance Scenarios (T036)。

    必須設定の未設定を検知し、明確なエラーメッセージを提供する
    """

    def test_as1_prod_required_field_missing(self, monkeypatch: Any, isolate_from_project_dotenv: None) -> None:
        """AS1: 本番環境で必須設定（workspace_path）が未設定時にエラー"""
        # Clear environment variables
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

        with pytest.raises(ValidationError) as exc_info:
            OrchestratorSettings(environment="prod")

        error_msg = str(exc_info.value)
        # 必須フィールドエラーが表示される（NFR-003: Field required）
        assert "workspace_path" in error_msg
        assert "Field required" in error_msg

    def test_as2_dev_required_field_missing(self, monkeypatch: Any, isolate_from_project_dotenv: None) -> None:
        """AS2: 開発環境でも同じ必須設定が未設定時にエラー"""
        # Clear environment variables
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

        with pytest.raises(ValidationError) as exc_info:
            OrchestratorSettings(environment="dev")

        error_msg = str(exc_info.value)
        # 必須フィールドエラーが表示される（NFR-003: Field required）
        assert "workspace_path" in error_msg
        assert "Field required" in error_msg

    def test_as3_error_message_includes_environment_variable_hint(
        self, monkeypatch: Any, isolate_from_project_dotenv: None
    ) -> None:
        """AS3: エラーメッセージにどの環境変数またはTOMLキーを設定すべきか明示"""
        # Clear environment variables
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

        with pytest.raises(ValidationError) as exc_info:
            OrchestratorSettings(environment="prod")

        error_msg = str(exc_info.value)
        # 必須フィールドエラーが表示される（NFR-003: Field identifier + Required status）
        assert "workspace_path" in error_msg
        assert "Field required" in error_msg

    def test_as4_optional_field_uses_default_in_dev(self, tmp_path: Path) -> None:
        """AS4: オプション設定がデフォルト値を使用して起動成功（dev環境）"""
        settings = OrchestratorSettings(workspace_path=tmp_path, environment="dev")
        assert settings.timeout_per_team_seconds == 300

    def test_as4_optional_field_uses_default_in_prod(self, tmp_path: Path) -> None:
        """AS4: オプション設定がデフォルト値を使用して起動成功（prod環境）"""
        settings = OrchestratorSettings(workspace_path=tmp_path, environment="prod")
        assert settings.timeout_per_team_seconds == 300

    def test_as4_environment_agnostic_defaults(self, tmp_path: Path) -> None:
        """AS4: デフォルト値がすべての環境で同一（FR-007準拠）"""
        dev_settings = OrchestratorSettings(workspace_path=tmp_path, environment="dev")
        prod_settings = OrchestratorSettings(workspace_path=tmp_path, environment="prod")
        assert dev_settings.timeout_per_team_seconds == prod_settings.timeout_per_team_seconds
        assert dev_settings.timeout_per_team_seconds == 300

    def test_as5_optional_field_can_be_overridden_via_cli(self, tmp_path: Path) -> None:
        """AS5: オプション設定がCLI引数で上書き可能"""
        settings = OrchestratorSettings(
            workspace_path=tmp_path,
            timeout_per_team_seconds=600,
            environment="dev",
        )
        assert settings.timeout_per_team_seconds == 600

    def test_as5_optional_field_can_be_overridden_via_env(self, monkeypatch: Any, tmp_path: Path) -> None:
        """AS5: オプション設定が環境変数で上書き可能"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(tmp_path))
        monkeypatch.setenv("MIXSEEK_TIMEOUT_PER_TEAM_SECONDS", "450")

        settings = OrchestratorSettings()
        assert settings.timeout_per_team_seconds == 450
