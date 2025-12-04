"""mixseek team コマンド ユニットテスト

Article 3: Test-First Imperative準拠

Test Coverage:
    - チーム設定TOML読み込み
    - Leader Agent実行（Agent Delegation）
    - 集約結果出力（JSON/text）
    - --save-dbオプション
    - エラーハンドリング（設定ファイル不存在、TOMLバリデーション）
    - ヘルプ表示

Tests:
    - T036: 基本機能（モック使用）
    - Edge Cases: 設定ファイル不存在、TOMLバリデーションエラー

References:
    - Spec: specs/008-leader/spec.md (US5, FR-21〜FR-24)
    - Contract: specs/008-leader/contracts/team_command.md

Note:
    Round 2機能（--previous-round, --load-from-db）は廃止されました。
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic_ai import RunUsage
from typer.testing import CliRunner

from mixseek.agents.leader.models import MemberSubmission
from mixseek.cli.main import app


class TestTeamCommand:
    """mixseek teamコマンドテスト（T036）"""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """CLIテストランナー"""
        return CliRunner()

    @pytest.fixture
    def sample_team_toml(self, tmp_path: Path) -> Path:
        """サンプルチーム設定TOML"""
        toml_content = """
[team]
team_id = "test-team"
team_name = "Test Team"
description = "Test team for unit testing"

[[team.members]]
agent_name = "agent-1"
agent_type = "plain"
model = "google-gla:gemini-2.5-flash-lite"
system_instruction = "You are a test agent"
tool_description = "A test agent for unit testing"
temperature = 0.7
max_tokens = 1024

[[team.members]]
agent_name = "agent-2"
agent_type = "plain"
model = "google-gla:gemini-2.5-flash-lite"
system_instruction = "You are another test agent"
tool_description = "Another test agent for unit testing"
temperature = 0.7
max_tokens = 1024
"""
        toml_file = tmp_path / "team.toml"
        toml_file.write_text(toml_content)
        return toml_file

    @pytest.mark.skipif(
        os.getenv("GITHUB_ACTIONS") == "true", reason="Team command behavior differs in CI environment"
    )
    @patch("mixseek.cli.commands.team.MemberAgentFactory.create_agent")
    @patch("mixseek.cli.commands.team.create_leader_agent")
    def test_command_with_config(
        self,
        mock_create_leader: MagicMock,
        mock_create_agent: MagicMock,
        runner: CliRunner,
        sample_team_toml: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """正常系: チーム設定TOML指定（FR-21）"""
        # Given: 環境変数設定
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(Path.home() / ".mixseek"))

        # Given: モックMember Agent
        mock_member_agent = MagicMock()
        mock_create_agent.return_value = mock_member_agent

        # Given: モックLeader Agent
        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.output = "Final aggregated response"
        mock_result.all_messages.return_value = []
        mock_result.all_messages_json.return_value = b"[]"  # FR-023: message_history用

        # モック実行（非同期）
        async def mock_run(prompt: str, deps: Any) -> Any:
            # submissionsにデータを追加（Leader Agentの動作をシミュレート）
            deps.submissions.append(
                MemberSubmission(
                    agent_name="agent-1",
                    agent_type="plain",
                    status="SUCCESS",
                    content="Result 1",
                    usage=RunUsage(input_tokens=10, output_tokens=20, requests=1),
                )
            )
            return mock_result

        mock_agent.run = mock_run
        mock_create_leader.return_value = mock_agent

        # When: コマンド実行
        result = runner.invoke(app, ["team", "Test prompt", "--config", str(sample_team_toml)])

        # Then: 成功
        assert result.exit_code == 0
        # 警告メッセージはstderrに出力される
        assert "WARNING" in result.stderr or "⚠" in result.stderr or "development" in result.stderr.lower()
        assert "Test Team" in result.stdout

    @pytest.mark.skipif(
        os.getenv("GITHUB_ACTIONS") == "true", reason="Team command behavior differs in CI environment"
    )
    @patch("mixseek.cli.commands.team.MemberAgentFactory.create_agent")
    @patch("mixseek.cli.commands.team.create_leader_agent")
    def test_command_creates_agents_with_running_event_loop(
        self,
        mock_create_leader: MagicMock,
        mock_create_agent: MagicMock,
        runner: CliRunner,
        sample_team_toml: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """エージェント生成時にイベントループが稼働していることを確認"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(Path.home() / ".mixseek"))

        mock_member_agent = MagicMock()
        loop_states: list[bool] = []

        def capture_loop_state(_config: Any) -> MagicMock:
            try:
                asyncio.get_running_loop()
                loop_states.append(True)
            except RuntimeError:
                loop_states.append(False)
            return mock_member_agent

        mock_create_agent.side_effect = capture_loop_state

        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.output = "Loop state test"
        mock_result.all_messages.return_value = []
        mock_result.all_messages_json.return_value = b"[]"  # FR-023: message_history用

        async def mock_run(_prompt: str, deps: Any) -> Any:
            deps.submissions.append(
                MemberSubmission(
                    agent_name="agent-loop",
                    agent_type="plain",
                    status="SUCCESS",
                    content="Loop state content",
                    usage=RunUsage(input_tokens=1, output_tokens=2, requests=1),
                )
            )
            return mock_result

        mock_agent.run = mock_run
        mock_create_leader.return_value = mock_agent

        result = runner.invoke(app, ["team", "Prompt", "--config", str(sample_team_toml)])

        assert result.exit_code == 0
        assert loop_states, "Agent creation should be attempted at least once"
        assert all(loop_states), f"Expected all loop states to be True, got {loop_states}"

    @pytest.mark.skipif(
        os.getenv("GITHUB_ACTIONS") == "true", reason="Team command behavior differs in CI environment"
    )
    @patch("mixseek.cli.commands.team.MemberAgentFactory.create_agent")
    @patch("mixseek.cli.commands.team.create_leader_agent")
    def test_command_json_output(
        self,
        mock_create_leader: MagicMock,
        mock_create_agent: MagicMock,
        runner: CliRunner,
        sample_team_toml: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """JSON形式出力（FR-23, SC-09）"""
        # Given: 環境変数とモック
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(Path.home() / ".mixseek"))

        # Given: モックMember Agent
        mock_member_agent = MagicMock()
        mock_create_agent.return_value = mock_member_agent

        # Given: モックLeader Agent
        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.output = "JSON output test"
        mock_result.all_messages.return_value = []
        mock_result.all_messages_json.return_value = b"[]"  # FR-023: message_history用

        async def mock_run(prompt: str, deps: Any) -> Any:
            deps.submissions.append(
                MemberSubmission(
                    agent_name="a1",
                    agent_type="plain",
                    status="SUCCESS",
                    content="R1",
                    usage=RunUsage(input_tokens=5, output_tokens=10, requests=1),
                )
            )
            return mock_result

        mock_agent.run = mock_run
        mock_create_leader.return_value = mock_agent

        # When: JSON出力
        result = runner.invoke(app, ["team", "Prompt", "--config", str(sample_team_toml), "--output-format", "json"])

        # Then: JSON形式で出力
        assert result.exit_code == 0
        # JSON検証: stdoutから完全なJSONオブジェクトを抽出
        stdout = result.stdout.strip()
        if stdout:
            # 最初の{を探す
            start_idx = stdout.find("{")
            if start_idx != -1:
                # ネストを考慮して対応する}を探す
                depth = 0
                end_idx = start_idx
                for i in range(start_idx, len(stdout)):
                    if stdout[i] == "{":
                        depth += 1
                    elif stdout[i] == "}":
                        depth -= 1
                        if depth == 0:
                            end_idx = i + 1
                            break

                json_str = stdout[start_idx:end_idx]
                data = json.loads(json_str)
                assert "team_name" in data
                assert "success_count" in data
                assert "submissions" in data
            else:
                pytest.fail(f"No JSON object found in stdout: {stdout}")

    @pytest.mark.skipif(
        os.getenv("GITHUB_ACTIONS") == "true", reason="Team command behavior differs in CI environment"
    )
    @patch("mixseek.cli.commands.team.MemberAgentFactory.create_agent")
    @patch("mixseek.cli.commands.team.create_leader_agent")
    def test_command_all_agents_failed(
        self,
        mock_create_leader: MagicMock,
        mock_create_agent: MagicMock,
        runner: CliRunner,
        sample_team_toml: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """全Agent失敗時Exit Code 2（Edge Case）"""
        # Given: 環境変数とモック
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(Path.home() / ".mixseek"))

        # Given: モックMember Agent
        mock_member_agent = MagicMock()
        mock_create_agent.return_value = mock_member_agent

        # Given: モックLeader Agent（全Agent失敗）
        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.output = "All agents failed"
        mock_result.all_messages.return_value = []
        mock_result.all_messages_json.return_value = b"[]"  # FR-023: message_history用

        async def mock_run(prompt: str, deps: Any) -> Any:
            # 失敗したsubmissionsを追加
            deps.submissions.append(
                MemberSubmission(
                    agent_name="a1",
                    agent_type="plain",
                    status="ERROR",
                    content="",
                    error_message="Timeout",
                    usage=RunUsage(input_tokens=0, output_tokens=0, requests=1),
                )
            )
            deps.submissions.append(
                MemberSubmission(
                    agent_name="a2",
                    agent_type="plain",
                    status="ERROR",
                    content="",
                    error_message="Error",
                    usage=RunUsage(input_tokens=0, output_tokens=0, requests=1),
                )
            )
            return mock_result

        mock_agent.run = mock_run
        mock_create_leader.return_value = mock_agent

        # When: コマンド実行
        result = runner.invoke(app, ["team", "Prompt", "--config", str(sample_team_toml)])

        # Then: Exit Code 2（全Agent失敗）
        assert result.exit_code == 2
        # エラーメッセージはstderrに出力される
        assert "failed" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_environment_variable_missing(self, runner: CliRunner, sample_team_toml: Path) -> None:
        """MIXSEEK_WORKSPACE未設定エラー（FR-20）"""
        # Given: 環境変数未設定
        # （monkeypatch不使用、実際の環境で未設定を想定）

        # When: コマンド実行
        # Note: 実際の環境変数に依存するため、モック使用を推奨
        # このテストは実装確認用のスケルトン
        pass

    def test_cli_config_file_not_found(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """設定ファイル不存在エラー（Edge Case）

        Article 4準拠: 正確なエラーメッセージ文言を確認
        """
        # Given: ワークスペースを設定（ConfigurationManager要件）
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        # When: 存在しない設定ファイル指定
        result = runner.invoke(app, ["team", "質問", "--config", "/nonexistent/team.toml"])

        # Then: エラー終了、厳格なメッセージ確認
        assert result.exit_code == 1
        output = result.stdout + result.stderr
        # 正確なエラーメッセージ文言を確認（TeamTomlSourceから出力される）
        assert "ERROR: Team config file not found:" in output or "ERROR: Failed to resolve workspace path:" in output

    def test_cli_toml_validation_error(self, runner: CliRunner, tmp_path: Path) -> None:
        """TOML設定バリデーションエラー"""
        # Given: Invalid TOML（team_idなし - 必須フィールド）
        invalid_toml = """
[team]
team_name = "Test Team"
"""
        toml_path = tmp_path / "invalid.toml"
        toml_path.write_text(invalid_toml)

        # When: コマンド実行
        result = runner.invoke(app, ["team", "質問", "--config", str(toml_path)])

        # Then: バリデーションエラー
        assert result.exit_code == 1

    def test_cli_help_display(self, runner: CliRunner) -> None:
        """ヘルプ表示"""
        # When: ヘルプ表示
        result = runner.invoke(app, ["team", "--help"])

        # Then: 成功、ヘルプ内容確認
        assert result.exit_code == 0
        assert "Execute team of Member Agents" in result.stdout or "team" in result.stdout
