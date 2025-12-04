"""Tests for Member Agent settings loading via ConfigurationManager.

T079実装のテスト: ConfigurationManager.load_member_settings()
"""

from pathlib import Path

import pytest

from mixseek.config.manager import ConfigurationManager
from mixseek.config.schema import MemberAgentSettings


class TestLoadMemberSettings:
    """ConfigurationManager.load_member_settings()のテスト。"""

    def test_load_plain_agent_toml(self) -> None:
        """examples/agents/plain_agent.tomlの読み込み。"""
        # Arrange
        manager = ConfigurationManager(workspace=Path.cwd())
        toml_file = Path("examples/agents/plain_agent.toml")

        # Act
        member_settings = manager.load_member_settings(toml_file)

        # Assert
        assert isinstance(member_settings, MemberAgentSettings)
        assert member_settings.agent_name == "plain-agent"
        assert member_settings.agent_type == "plain"
        assert member_settings.model == "google-gla:gemini-2.5-flash-lite"
        assert member_settings.temperature == 0.2
        assert member_settings.max_tokens == 4096
        assert member_settings.system_instruction is not None
        assert "高性能なAIアシスタント" in member_settings.system_instruction
        assert member_settings.timeout_seconds == 45  # max_execution_time_seconds

    def test_load_member_settings_with_tracing(self) -> None:
        """トレーシング機能の検証。"""
        # Arrange
        manager = ConfigurationManager(workspace=Path.cwd())
        toml_file = Path("examples/agents/plain_agent.toml")

        # Act
        member_settings = manager.load_member_settings(toml_file)

        # Assert: トレース情報の存在確認
        assert hasattr(member_settings, "__source_traces__")
        traces = getattr(member_settings, "__source_traces__")
        assert isinstance(traces, dict)

        # agent_nameフィールドのトレース情報を確認
        # Phase 2-4: トレース情報が存在することを確認（ソースタイプは優先順位による）
        if "agent_name" in traces:
            trace = traces["agent_name"]
            assert trace.source_type in ("cli", "toml", "env"), "Valid source type"
            assert trace.value == "plain-agent"
            assert trace.source_name in ("CLI", "TOML", "plain_agent.toml", "environment_variables")

    def test_load_code_execution_agent_toml(self) -> None:
        """examples/agents/code_execution_agent.tomlの読み込み。"""
        # Arrange
        manager = ConfigurationManager(workspace=Path.cwd())
        toml_file = Path("examples/agents/code_execution_agent.toml")

        # Act
        member_settings = manager.load_member_settings(toml_file)

        # Assert
        assert isinstance(member_settings, MemberAgentSettings)
        assert member_settings.agent_name == "claude-code-execution-agent"  # 実際のファイルに合わせて修正
        assert member_settings.agent_type == "code_execution"

    def test_load_member_settings_file_not_found(self) -> None:
        """存在しないファイルの読み込みエラー。"""
        # Arrange
        manager = ConfigurationManager(workspace=Path.cwd())
        toml_file = Path("nonexistent.toml")

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Member Agent config file not found"):
            manager.load_member_settings(toml_file)

    def test_load_member_settings_with_cli_override(self) -> None:
        """CLI引数による上書き。"""
        # Arrange
        manager = ConfigurationManager(
            workspace=Path.cwd(),
            cli_args={"temperature": 0.9, "max_tokens": 8000},
        )
        toml_file = Path("examples/agents/plain_agent.toml")

        # Act
        member_settings = manager.load_member_settings(toml_file)

        # Assert: CLI引数が優先される
        assert member_settings.temperature == 0.9  # CLI override
        assert member_settings.max_tokens == 8000  # CLI override
        assert member_settings.agent_name == "plain-agent"  # TOML value

    def test_load_member_settings_with_extra_kwargs(self) -> None:
        """追加引数による設定。"""
        # Arrange
        manager = ConfigurationManager(workspace=Path.cwd())
        toml_file = Path("examples/agents/plain_agent.toml")

        # Act
        member_settings = manager.load_member_settings(
            toml_file,
            temperature=0.5,  # extra_kwargs
        )

        # Assert
        assert member_settings.temperature == 0.5  # extra_kwargs override

    def test_multiple_agent_files(self) -> None:
        """複数のAgent設定ファイルを順次読み込み。"""
        # Arrange
        manager = ConfigurationManager(workspace=Path.cwd())
        agent_files = [
            Path("examples/agents/plain_agent.toml"),
            Path("examples/agents/code_execution_agent.toml"),
        ]

        # Act & Assert
        for toml_file in agent_files:
            member_settings = manager.load_member_settings(toml_file)
            assert isinstance(member_settings, MemberAgentSettings)
            assert member_settings.agent_name is not None
            assert member_settings.agent_type is not None

    def test_load_member_settings_with_relative_path(self) -> None:
        """相対パスの読み込み（workspace対応）。"""
        # Arrange
        manager = ConfigurationManager(workspace=Path.cwd())
        # 相対パスで指定
        toml_file = Path("examples/agents/plain_agent.toml")

        # Act
        member_settings = manager.load_member_settings(toml_file)

        # Assert: 正しく読み込める
        assert member_settings.agent_name == "plain-agent"
        assert member_settings.model == "google-gla:gemini-2.5-flash-lite"

    def test_tool_description_default_generation(self) -> None:
        """descriptionフィールドがない場合のtool_descriptionデフォルト生成。"""
        import tempfile

        # Arrange: descriptionフィールドのないTOMLファイルを作成
        toml_content = """
[agent]
name = "test-agent-no-desc"
type = "plain"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.7
max_tokens = 2048

[agent.system_instruction]
text = "Test agent without description field"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as tf:
            tf.write(toml_content)
            toml_path = Path(tf.name)

        try:
            # Act
            manager = ConfigurationManager(workspace=Path.cwd())
            member_settings = manager.load_member_settings(toml_path)

            # Assert: tool_descriptionがデフォルト生成されている
            assert member_settings.tool_description == "Delegate task to test-agent-no-desc"
            assert member_settings.agent_name == "test-agent-no-desc"

        finally:
            # Cleanup
            toml_path.unlink()
