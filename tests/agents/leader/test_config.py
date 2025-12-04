"""Leader Agent TOML設定のテスト

Article 3: Test-First Imperative準拠

Tests:
    - LeaderAgentConfig: Leader Agent設定モデル
    - TeamMemberAgentConfig: Member Agent設定モデル（Tool定義含む）
    - TeamConfig: チーム設定モデル
    - load_team_config: TOML読み込み（参照形式サポート）
"""

import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from mixseek.agents.leader.config import LeaderAgentConfig, TeamConfig, TeamMemberAgentConfig, load_team_config


class TestLeaderAgentConfig:
    """LeaderAgentConfig モデルのテスト（data-model.md Section 3）"""

    def test_create_with_system_prompt(self) -> None:
        """system_prompt設定あり"""
        # Act
        config = LeaderAgentConfig(system_instruction="あなたはリーダーエージェントです。")

        # Assert
        assert config.system_instruction == "あなたはリーダーエージェントです。"
        assert config.model == "google-gla:gemini-2.5-flash-lite"  # デフォルト
        assert config.temperature is None  # デフォルト (uses model default)

    def test_create_without_system_prompt(self) -> None:
        """system_prompt未設定（None、デフォルトプロンプト使用）"""
        # Act
        config = LeaderAgentConfig()

        # Assert
        assert config.system_instruction is None

    def test_empty_system_prompt_allowed(self) -> None:
        """system_prompt空文字列明示でデフォルト無効化"""
        config = LeaderAgentConfig(system_instruction="")
        assert config.system_instruction == ""

    def test_whitespace_system_prompt_warns_and_empties(self) -> None:
        """system_instruction空白のみは警告して空文字扱い"""
        with pytest.warns(UserWarning, match="system_instruction is whitespace-only"):
            config = LeaderAgentConfig(system_instruction="   ")

        assert config.system_instruction == ""


class TestTeamMemberAgentConfig:
    """TeamMemberAgentConfig モデルのテスト（Agent Delegation Tool設定）"""

    def test_create_with_tool_name(self) -> None:
        """tool_name明示的設定"""
        # Act
        config = TeamMemberAgentConfig(
            agent_name="analyst",
            agent_type="plain",
            tool_name="delegate_to_analyst",
            tool_description="論理的な分析を実行します",
            model="gemini-2.5-flash-lite",
            system_instruction="あなたはアナリストです",
            temperature=0.7,
            max_tokens=2048,
        )

        # Assert
        assert config.tool_name == "delegate_to_analyst"
        assert config.get_tool_name() == "delegate_to_analyst"

    def test_tool_name_auto_generation(self) -> None:
        """tool_name自動生成（Edge Case: 未設定時）"""
        # Act
        config = TeamMemberAgentConfig(
            agent_name="analyst",
            agent_type="plain",
            tool_description="論理的な分析を実行します",
            model="gemini-2.5-flash-lite",
            system_instruction="あなたはアナリストです",
            temperature=0.7,
            max_tokens=2048,
        )

        # Assert
        assert config.tool_name is None
        assert config.get_tool_name() == "delegate_to_analyst"  # 自動生成

    def test_tool_description_required(self) -> None:
        """tool_description必須"""
        # tool_description空文字列エラー
        with pytest.raises(ValidationError) as exc_info:
            TeamMemberAgentConfig(
                agent_name="analyst",
                agent_type="plain",
                tool_description="",  # 空文字列不可
                model="gemini-2.5-flash-lite",
                system_instruction="test",
                temperature=0.7,
                max_tokens=2048,
            )

        assert "tool_description" in str(exc_info.value)


class TestTeamConfig:
    """TeamConfig モデルのテスト"""

    def test_create_basic_team(self) -> None:
        """基本的なチーム設定"""
        # Act
        config = TeamConfig(
            team_id="team-001",
            team_name="Test Team",
            members=[
                TeamMemberAgentConfig(
                    agent_name="analyst",
                    agent_type="plain",
                    tool_description="分析",
                    model="gemini-2.5-flash-lite",
                    system_instruction="test",
                    temperature=0.7,
                    max_tokens=2048,
                )
            ],
        )

        # Assert
        assert config.team_id == "team-001"
        assert config.team_name == "Test Team"
        assert len(config.members) == 1
        assert config.max_concurrent_members == 15  # デフォルト
        assert config.leader is not None  # デフォルトインスタンスが作成される
        assert isinstance(config.leader, LeaderAgentConfig)

    def test_create_with_leader_config(self) -> None:
        """Leader Agent設定あり"""
        # Act
        config = TeamConfig(
            team_id="team-001",
            team_name="Test Team",
            leader=LeaderAgentConfig(system_instruction="リーダーです"),
            members=[
                TeamMemberAgentConfig(
                    agent_name="analyst",
                    agent_type="plain",
                    tool_description="分析",
                    model="gemini-2.5-flash-lite",
                    system_instruction="test",
                    temperature=0.7,
                    max_tokens=2048,
                )
            ],
        )

        # Assert
        assert config.leader is not None
        assert config.leader.system_instruction == "リーダーです"

    def test_members_maximum_limit(self) -> None:
        """members最大15（デフォルト上限）"""
        # 16個のMember Agentを作成
        members = [
            TeamMemberAgentConfig(
                agent_name=f"agent-{i}",
                agent_type="plain",
                tool_description=f"Agent {i}",
                model="gemini-2.5-flash-lite",
                system_instruction="test",
                temperature=0.7,
                max_tokens=2048,
            )
            for i in range(16)
        ]

        # 上限超過エラー
        with pytest.raises(ValidationError) as exc_info:
            TeamConfig(team_id="team-001", team_name="Test Team", members=members)

        assert "Too many members" in str(exc_info.value)

    def test_duplicate_agent_name_error(self) -> None:
        """agent_name重複エラー"""
        # 同じagent_nameのMember Agent
        members = [
            TeamMemberAgentConfig(
                agent_name="analyst",
                agent_type="plain",
                tool_description="分析1",
                model="gemini-2.5-flash-lite",
                system_instruction="test",
                temperature=0.7,
                max_tokens=2048,
            ),
            TeamMemberAgentConfig(
                agent_name="analyst",  # 重複
                agent_type="plain",
                tool_description="分析2",
                model="gemini-2.5-flash-lite",
                system_instruction="test",
                temperature=0.7,
                max_tokens=2048,
            ),
        ]

        # 重複エラー
        with pytest.raises(ValidationError) as exc_info:
            TeamConfig(team_id="team-001", team_name="Test Team", members=members)

        assert "Duplicate agent_name" in str(exc_info.value)

    def test_duplicate_tool_name_error(self) -> None:
        """tool_name重複エラー（Edge Case）"""
        # 同じtool_nameのMember Agent
        members = [
            TeamMemberAgentConfig(
                agent_name="analyst1",
                agent_type="plain",
                tool_name="delegate_to_analyst",  # 明示的tool_name
                tool_description="分析1",
                model="gemini-2.5-flash-lite",
                system_instruction="test",
                temperature=0.7,
                max_tokens=2048,
            ),
            TeamMemberAgentConfig(
                agent_name="analyst2",
                agent_type="plain",
                tool_name="delegate_to_analyst",  # 重複
                tool_description="分析2",
                model="gemini-2.5-flash-lite",
                system_instruction="test",
                temperature=0.7,
                max_tokens=2048,
            ),
        ]

        # 重複エラー
        with pytest.raises(ValidationError) as exc_info:
            TeamConfig(team_id="team-001", team_name="Test Team", members=members)

        assert "Duplicate tool_name" in str(exc_info.value)

    def test_tool_name_auto_generation_duplicate(self) -> None:
        """tool_name自動生成でも重複チェック（Edge Case）"""
        # tool_name未設定で、自動生成されたtool_nameが重複
        members = [
            TeamMemberAgentConfig(
                agent_name="analyst",
                agent_type="plain",
                # tool_name未設定 → "delegate_to_analyst"に自動生成
                tool_description="分析1",
                model="gemini-2.5-flash-lite",
                system_instruction="test",
                temperature=0.7,
                max_tokens=2048,
            ),
            TeamMemberAgentConfig(
                agent_name="other",
                agent_type="plain",
                tool_name="delegate_to_analyst",  # 明示的に設定、自動生成と重複
                tool_description="分析2",
                model="gemini-2.5-flash-lite",
                system_instruction="test",
                temperature=0.7,
                max_tokens=2048,
            ),
        ]

        # 重複エラー
        with pytest.raises(ValidationError) as exc_info:
            TeamConfig(team_id="team-001", team_name="Test Team", members=members)

        assert "Duplicate tool_name" in str(exc_info.value)


class TestLoadTeamConfig:
    """load_team_config関数のテスト（TOML読み込み）"""

    def test_load_inline_definition(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """インライン定義読み込み"""
        # Article 9準拠: workspace環境変数を明示的に設定
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))

        # Arrange
        toml_content = """
[team]
team_id = "test-team-001"
team_name = "Test Team"

[[team.members]]
agent_name = "analyst"
agent_type = "plain"
tool_description = "論理的な分析"
model = "google-gla:gemini-2.5-flash-lite"
system_instruction = "あなたはアナリストです"
temperature = 0.7
max_tokens = 2048
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            toml_path = Path(f.name)

        try:
            # Act
            config = load_team_config(toml_path)

            # Assert
            assert config.team_id == "test-team-001"
            assert len(config.members) == 1
            assert config.members[0].agent_name == "analyst"
            assert config.members[0].get_tool_name() == "delegate_to_analyst"  # 自動生成
        finally:
            toml_path.unlink()

    def test_load_with_leader_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """[team.leader]セクション読み込み"""
        # Article 9準拠: workspace環境変数を明示的に設定
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))

        # Arrange
        toml_content = """
[team]
team_id = "test-team-001"
team_name = "Test Team"

[team.leader]
system_instruction = "あなたはリーダーです"

[[team.members]]
agent_name = "analyst"
agent_type = "plain"
tool_description = "分析"
model = "google-gla:gemini-2.5-flash-lite"
system_instruction = "test"
temperature = 0.7
max_tokens = 2048
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            toml_path = Path(f.name)

        try:
            # Act
            config = load_team_config(toml_path)

            # Assert
            assert config.leader is not None
            assert config.leader.system_instruction == "あなたはリーダーです"
        finally:
            toml_path.unlink()

    def test_load_reference_format(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """参照形式読み込み（FR-025: DRY Article 10）"""
        # Article 9準拠: workspace環境変数を明示的に設定
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))

        # Arrange: Member Agent TOML作成（Feature 027形式）
        member_toml_content = """
[agent]
name = "web-searcher"
type = "web_search"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.5
max_tokens = 4096

[agent.system_instruction]
text = "あなたはWeb検索エージェントです"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as mf:
            mf.write(member_toml_content)
            member_toml_path = Path(mf.name)

        # Team TOML作成（参照形式）
        team_toml_content = f"""
[team]
team_id = "test-team-001"
team_name = "Test Team"

[[team.members]]
config = "{member_toml_path}"
tool_description = "Web検索で最新情報を収集します"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as tf:
            tf.write(team_toml_content)
            team_toml_path = Path(tf.name)

        try:
            # Act
            config = load_team_config(team_toml_path)

            # Assert
            assert len(config.members) == 1
            assert config.members[0].agent_name == "web-searcher"
            assert config.members[0].agent_type == "web_search"  # web-search → web_search
            assert config.members[0].system_instruction == "あなたはWeb検索エージェントです"
            assert config.members[0].tool_description == "Web検索で最新情報を収集します"
        finally:
            team_toml_path.unlink()
            member_toml_path.unlink()

    def test_reference_file_not_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """参照先ファイル不存在エラー（Edge Case）"""
        # Article 9準拠: workspace環境変数を明示的に設定
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))

        # Arrange
        toml_content = """
[team]
team_id = "test-team-001"
team_name = "Test Team"

[[team.members]]
config = "/nonexistent/path/agent.toml"
tool_description = "test"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            toml_path = Path(f.name)

        try:
            # Act & Assert
            with pytest.raises(FileNotFoundError) as exc_info:
                load_team_config(toml_path)

            assert "/nonexistent/path/agent.toml" in str(exc_info.value)
        finally:
            toml_path.unlink()

    def test_tool_name_override_in_reference(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """参照形式でtool_name上書き"""
        # Article 9準拠: workspace環境変数を明示的に設定
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))

        # Arrange: Member Agent TOML（Feature 027形式）
        member_toml_content = """
[agent]
name = "analyzer"
type = "plain"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.7
max_tokens = 2048

[agent.system_instruction]
text = "test"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as mf:
            mf.write(member_toml_content)
            member_toml_path = Path(mf.name)

        # Team TOML（tool_name/description上書き）
        team_toml_content = f"""
[team]
team_id = "test-team-001"
team_name = "Test Team"

[[team.members]]
config = "{member_toml_path}"
tool_name = "custom_analyzer"
tool_description = "カスタム分析"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as tf:
            tf.write(team_toml_content)
            team_toml_path = Path(tf.name)

        try:
            # Act
            config = load_team_config(team_toml_path)

            # Assert
            assert config.members[0].tool_name == "custom_analyzer"  # 上書き
            assert config.members[0].tool_description == "カスタム分析"  # 上書き
        finally:
            team_toml_path.unlink()
            member_toml_path.unlink()

    def test_load_reference_with_workspace_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """MIXSEEK_WORKSPACE設定時の相対パス解釈"""
        # Arrange: ワークスペースディレクトリを作成
        with tempfile.TemporaryDirectory() as workspace_dir:
            workspace_path = Path(workspace_dir)
            agents_dir = workspace_path / "agents"
            agents_dir.mkdir()

            # Member Agent TOML作成
            member_toml_path = agents_dir / "test-agent.toml"
            member_toml_content = """
[agent]
name = "test-agent"
type = "plain"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.7
max_tokens = 2048

[agent.system_instruction]
text = "テストエージェント"
"""
            member_toml_path.write_text(member_toml_content)

            # Team TOML作成（相対パス）
            team_toml_content = """
[team]
team_id = "test-team-001"
team_name = "Test Team"

[[team.members]]
config = "agents/test-agent.toml"
tool_description = "テスト"
"""
            with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as tf:
                tf.write(team_toml_content)
                team_toml_path = Path(tf.name)

            try:
                # 環境変数設定
                monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace_path))

                # Act
                config = load_team_config(team_toml_path)

                # Assert
                assert len(config.members) == 1
                assert config.members[0].agent_name == "test-agent"
                assert config.members[0].system_instruction == "テストエージェント"
            finally:
                team_toml_path.unlink()

    def test_load_reference_without_workspace_env(
        self, monkeypatch: pytest.MonkeyPatch, isolate_from_project_dotenv: None
    ) -> None:
        """MIXSEEK_WORKSPACE未設定時はArticle 9準拠でエラー"""
        # Article 9準拠: 暗黙的フォールバック禁止
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

        # Arrange: 一時ファイル作成
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("""
[team]
team_id = "test-team-001"
team_name = "Test Team"

[[team.members]]
agent_name = "analyst"
agent_type = "plain"
tool_description = "分析"
model = "google-gla:gemini-2.5-flash-lite"
system_instruction = "test"
temperature = 0.7
max_tokens = 2048
""")
            toml_path = Path(f.name)

        try:
            # Act & Assert: Article 9準拠で明示的エラー
            with pytest.raises(Exception) as exc_info:  # WorkspacePathNotSpecifiedError or broader Exception
                load_team_config(toml_path)

            # エラーメッセージに「MIXSEEK_WORKSPACE」が含まれることを確認
            assert "MIXSEEK_WORKSPACE" in str(exc_info.value) or "Workspace path not specified" in str(exc_info.value)
        finally:
            toml_path.unlink()

    def test_load_reference_with_absolute_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """絶対パスは常にそのまま使用される"""
        # Article 9準拠: workspace環境変数を明示的に設定
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))

        # Arrange: Member Agent TOML作成
        member_toml_content = """
[agent]
name = "test-agent"
type = "plain"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.7
max_tokens = 2048

[agent.system_instruction]
text = "テストエージェント"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as mf:
            mf.write(member_toml_content)
            member_toml_path = Path(mf.name)

        # Team TOML作成（絶対パス）
        team_toml_content = f"""
[team]
team_id = "test-team-001"
team_name = "Test Team"

[[team.members]]
config = "{member_toml_path}"
tool_description = "テスト"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as tf:
            tf.write(team_toml_content)
            team_toml_path = Path(tf.name)

        try:
            # Act（環境変数に関係なく絶対パスで解決される）
            config = load_team_config(team_toml_path)

            # Assert
            assert len(config.members) == 1
            assert config.members[0].agent_name == "test-agent"
        finally:
            team_toml_path.unlink()
            member_toml_path.unlink()

    def test_team_config_with_zero_members(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Member Agent 0件のチーム設定を受理（FR-033）

        Given: Member Agentが0件のTOML
        When: load_team_config で読み込み
        Then: 正常に読み込まれ、membersが空リスト
        """
        # Article 9準拠: workspace環境変数を明示的に設定
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))

        # TOML作成
        toml_content = """
[team]
team_id = "solo-team-001"
team_name = "Solo Leader Team"
max_concurrent_members = 15

[team.leader]
model = "openai:gpt-4o"
system_instruction = \"\"\"
あなたは単独で動作するLeader Agentです。
Member Agentを使用せず、自分自身でタスクを完遂してください。
\"\"\"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as tf:
            tf.write(toml_content)
            toml_path = Path(tf.name)

        try:
            # Act: TOML読み込み
            config = load_team_config(toml_path)

            # Assert
            assert config.team_id == "solo-team-001"
            assert config.team_name == "Solo Leader Team"
            assert len(config.members) == 0  # ✅ 空リスト
            assert config.leader is not None
            assert config.leader.system_instruction is not None
            assert "単独で動作する" in config.leader.system_instruction
        finally:
            toml_path.unlink()


class TestTeamSettingsToTeamConfig:
    """team_settings_to_team_config()変換関数のテスト（T078移行機能）"""

    def test_basic_conversion(self) -> None:
        """基本的な変換（leader + members）"""
        # Arrange: TeamSettingsをモック
        from unittest.mock import Mock

        from mixseek.agents.leader.config import team_settings_to_team_config
        from mixseek.config.schema import MemberAgentSettings

        # MemberAgentSettingsを直接構築
        member_settings = MemberAgentSettings(
            agent_name="member1",
            agent_type="web_search",
            tool_description="Web search tool",
            model="openai:gpt-4o-mini",
            temperature=0.5,
            max_tokens=2048,
            timeout_seconds=60,
        )

        team_settings = Mock()
        team_settings.team_id = "test-team-001"
        team_settings.team_name = "Test Team"
        team_settings.max_concurrent_members = 10
        team_settings.leader = {
            "model": "openai:gpt-4o",
            "temperature": 0.7,
            "timeout_seconds": 300,
            "system_instruction": "You are a leader agent",
        }
        team_settings.members = [member_settings]  # list[MemberAgentSettings]に変更

        # Act
        team_config = team_settings_to_team_config(team_settings)

        # Assert
        assert team_config.team_id == "test-team-001"
        assert team_config.team_name == "Test Team"
        assert team_config.max_concurrent_members == 10
        assert team_config.leader is not None
        assert team_config.leader.model == "openai:gpt-4o"
        assert team_config.leader.temperature == 0.7
        assert len(team_config.members) == 1
        assert team_config.members[0].agent_name == "member1"
        assert team_config.members[0].agent_type == "web_search"

    def test_conversion_with_empty_members(self) -> None:
        """Member Agentなしの変換（Leader単独）"""
        # Arrange
        from unittest.mock import Mock

        from mixseek.agents.leader.config import team_settings_to_team_config

        team_settings = Mock()
        team_settings.team_id = "solo-team"
        team_settings.team_name = "Solo Team"
        team_settings.max_concurrent_members = 5
        team_settings.leader = {
            "model": "google-gla:gemini-2.5-flash-lite",
            "timeout_seconds": 450,
        }
        team_settings.members = []

        # Act
        team_config = team_settings_to_team_config(team_settings)

        # Assert
        assert team_config.team_id == "solo-team"
        assert len(team_config.members) == 0
        assert team_config.leader is not None
        assert team_config.leader.model == "google-gla:gemini-2.5-flash-lite"

    def test_integration_with_configuration_manager(self) -> None:
        """ConfigurationManager経由の変換（統合テスト）"""
        # Arrange: Team TOMLファイル作成
        team_toml_content = """
[team]
team_id = "integration-test-team"
team_name = "Integration Test Team"
max_concurrent_members = 3

[team.leader]
model = "openai:gpt-4o"
temperature = 0.8
timeout_seconds = 300

[[team.members]]
agent_name = "test_agent"
agent_type = "plain"
tool_description = "Test agent"
model = "openai:gpt-4o-mini"
temperature = 0.5
max_tokens = 1024
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as tf:
            tf.write(team_toml_content)
            toml_path = Path(tf.name)

        try:
            # Act: ConfigurationManager経由で読み込み、変換
            from mixseek.agents.leader.config import team_settings_to_team_config
            from mixseek.config.manager import ConfigurationManager

            manager = ConfigurationManager(workspace=Path.cwd())
            team_settings = manager.load_team_settings(toml_path)
            team_config = team_settings_to_team_config(team_settings)

            # Assert: TeamConfig型の検証
            assert isinstance(team_config, TeamConfig)
            assert team_config.team_id == "integration-test-team"
            assert team_config.team_name == "Integration Test Team"
            assert team_config.max_concurrent_members == 3

            # Leader設定の検証
            assert team_config.leader is not None
            assert team_config.leader.model == "openai:gpt-4o"
            assert team_config.leader.temperature == 0.8
            assert team_config.leader.timeout_seconds == 300

            # Member設定の検証
            assert len(team_config.members) == 1
            assert team_config.members[0].agent_name == "test_agent"
            assert team_config.members[0].agent_type == "plain"
            assert team_config.members[0].model == "openai:gpt-4o-mini"

            # T078追加: トレーシング機能の検証
            assert hasattr(team_settings, "__source_traces__")
            traces = getattr(team_settings, "__source_traces__")
            assert isinstance(traces, dict)
            # team_idフィールドのトレース情報を確認
            if "team_id" in traces:
                trace = traces["team_id"]
                assert trace.source_type == "toml"
                assert trace.value == "integration-test-team"

        finally:
            # Cleanup
            toml_path.unlink()
