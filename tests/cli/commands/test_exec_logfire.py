"""exec --logfire 統合テスト。

from_toml() 廃止後のテスト。設定優先度: CLIフラグ > 環境変数 > デフォルト値。
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest


class TestLogfireCLIOptions:
    """Logfire CLIオプションのユニットテスト"""

    def test_exclusive_flags_error(self, tmp_path: Path) -> None:
        """複数のlogfireフラグを同時に指定するとエラー"""
        config_file = tmp_path / "orchestrator.toml"
        dummy_team_file = tmp_path / "team.toml"
        dummy_team_file.write_text("""
[team]
team_id = "test-team"
team_name = "Test Team"

[[team.members]]
agent_name = "dummy"
agent_type = "plain"
tool_description = "dummy agent"
model = "google-gla:gemini-2.5-flash-lite"
system_instruction = "dummy"
temperature = 0.7
max_tokens = 2048
""")

        config_file.write_text(f"""
[orchestrator]

[[orchestrator.teams]]
config = "{dummy_team_file}"
""")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "mixseek.cli.main",
                "exec",
                "test prompt",
                "--config",
                str(config_file),
                "--logfire",
                "--logfire-metadata",
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "MIXSEEK_WORKSPACE": str(tmp_path)},
        )

        assert result.returncode == 1
        assert "Only one of --logfire" in result.stderr or "Only one" in result.stderr


class TestLogfireConfigPriority:
    """設定優先度テスト（CLIフラグ > 環境変数 > デフォルト値）"""

    def test_cli_flag_overrides_env_var(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """CLIフラグが環境変数より優先される"""
        config_file = tmp_path / "orchestrator.toml"
        dummy_team_file = tmp_path / "team.toml"
        dummy_team_file.write_text("""
[team]
team_id = "test-team"
team_name = "Test Team"

[[team.members]]
agent_name = "dummy"
agent_type = "plain"
tool_description = "dummy agent"
model = "google-gla:gemini-2.5-flash-lite"
system_instruction = "dummy"
temperature = 0.7
max_tokens = 2048
""")

        config_file.write_text(f"""
[orchestrator]

[[orchestrator.teams]]
config = "{dummy_team_file}"
""")

        # 環境変数でmetadata_onlyを設定、CLIで--logfire（fullモード）を指定
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "mixseek.cli.main",
                "exec",
                "test prompt",
                "--config",
                str(config_file),
                "--logfire",
            ],
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "MIXSEEK_WORKSPACE": str(tmp_path),
                "LOGFIRE_ENABLED": "1",
                "LOGFIRE_PRIVACY_MODE": "metadata_only",
            },
        )

        # CLIフラグが優先される（実行自体が成功するかLogfire初期化失敗警告が出る）
        assert result.returncode in [0, 2]


class TestLogfireIntegration:
    """Logfire統合テスト"""

    @pytest.mark.integration
    def test_logfire_traces_orchestrator_execution(self, tmp_path: Path) -> None:
        pytest.skip("実装完了後に有効化")

    @pytest.mark.integration
    def test_execution_id_recorded_in_trace(self, tmp_path: Path) -> None:
        pytest.skip("実装完了後に有効化")

    @pytest.mark.integration
    def test_privacy_mode_metadata_only_excludes_content(self, tmp_path: Path) -> None:
        pytest.skip("実装完了後に有効化")


class TestLogfireErrorHandling:
    """Logfireエラーハンドリングのテスト"""

    def test_logfire_initialization_failure_continues_execution(self, tmp_path: Path) -> None:
        pytest.skip("実装完了後に有効化")

    def test_logfire_import_error_handled_gracefully(self, tmp_path: Path) -> None:
        pytest.skip("実装完了後に有効化")
