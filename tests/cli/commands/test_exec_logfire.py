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

    def test_cli_flag_overrides_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """CLIフラグが環境変数より優先される（setup_logfire_from_cli ユニットテスト）"""
        from unittest.mock import patch

        # 環境変数で metadata_only を設定
        monkeypatch.setenv("LOGFIRE_ENABLED", "1")
        monkeypatch.setenv("LOGFIRE_PRIVACY_MODE", "metadata_only")

        with patch("mixseek.cli.utils.setup_logfire") as mock_setup:
            from mixseek.cli.utils import setup_logfire_from_cli

            # CLIフラグ --logfire（full モード）を指定
            setup_logfire_from_cli(
                logfire=True,
                logfire_metadata=False,
                logfire_http=False,
                verbose=False,
            )

            # setup_logfire が呼ばれ、CLI指定の full モードが優先される
            mock_setup.assert_called_once()
            config = mock_setup.call_args[0][0]
            assert config.privacy_mode.value == "full"
            assert config.enabled is True

    def test_env_var_used_when_no_cli_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """CLIフラグなしでは環境変数が使われる"""
        from unittest.mock import patch

        monkeypatch.setenv("LOGFIRE_ENABLED", "1")
        monkeypatch.setenv("LOGFIRE_PRIVACY_MODE", "metadata_only")

        with patch("mixseek.cli.utils.setup_logfire") as mock_setup:
            from mixseek.cli.utils import setup_logfire_from_cli

            setup_logfire_from_cli(
                logfire=False,
                logfire_metadata=False,
                logfire_http=False,
                verbose=False,
            )

            mock_setup.assert_called_once()
            config = mock_setup.call_args[0][0]
            assert config.privacy_mode.value == "metadata_only"
            assert config.enabled is True

    def test_cli_logfire_metadata_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """--logfire-metadata フラグで metadata_only モードが設定される"""
        from unittest.mock import patch

        monkeypatch.delenv("LOGFIRE_ENABLED", raising=False)

        with patch("mixseek.cli.utils.setup_logfire") as mock_setup:
            from mixseek.cli.utils import setup_logfire_from_cli

            setup_logfire_from_cli(
                logfire=False,
                logfire_metadata=True,
                logfire_http=False,
                verbose=False,
            )

            mock_setup.assert_called_once()
            config = mock_setup.call_args[0][0]
            assert config.privacy_mode.value == "metadata_only"
            assert config.capture_http is False
            assert config.enabled is True

    def test_cli_logfire_http_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """--logfire-http フラグで full + capture_http が設定される"""
        from unittest.mock import patch

        monkeypatch.delenv("LOGFIRE_ENABLED", raising=False)

        with patch("mixseek.cli.utils.setup_logfire") as mock_setup:
            from mixseek.cli.utils import setup_logfire_from_cli

            setup_logfire_from_cli(
                logfire=False,
                logfire_metadata=False,
                logfire_http=True,
                verbose=False,
            )

            mock_setup.assert_called_once()
            config = mock_setup.call_args[0][0]
            assert config.privacy_mode.value == "full"
            assert config.capture_http is True
            assert config.enabled is True

    def test_setup_logfire_from_cli_error_handling(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Logfire初期化失敗時にグレースフルに警告を出力して継続する"""
        from unittest.mock import patch

        monkeypatch.delenv("LOGFIRE_ENABLED", raising=False)

        with (
            patch("mixseek.cli.utils.setup_logfire", side_effect=RuntimeError("init failed")),
            patch("mixseek.cli.utils.typer.secho") as mock_secho,
        ):
            from mixseek.cli.utils import setup_logfire_from_cli

            # 例外が外に漏れないことを検証
            setup_logfire_from_cli(
                logfire=True,
                logfire_metadata=False,
                logfire_http=False,
                verbose=False,
            )

            # 警告メッセージがstderrに出力されることを検証
            mock_secho.assert_called_once()
            warning_msg = mock_secho.call_args[0][0]
            assert "WARNING" in warning_msg
            assert "init failed" in warning_msg
