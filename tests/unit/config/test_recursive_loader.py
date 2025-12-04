"""Unit tests for RecursiveConfigLoader.

Article 3準拠: リファクタリング前にテストファーストで実装動作を保証。
Phase 2-1: RecursiveConfigLoaderの循環参照チェック処理のテスト。
"""

from pathlib import Path
from typing import Any

import pytest

from mixseek.config.constants import MAX_CONFIG_RECURSION_DEPTH
from mixseek.config.recursive_loader import RecursiveConfigLoader

# ==========================================
# Fixtures
# ==========================================


@pytest.fixture
def orchestrator_toml_content() -> str:
    """Valid orchestrator.toml content for testing."""
    return """
[orchestrator]
timeout_per_team_seconds = 600
max_concurrent_teams = 2

[[orchestrator.teams]]
config = "configs/team1.toml"

[[orchestrator.teams]]
config = "configs/team2.toml"
"""


@pytest.fixture
def team_toml_content() -> str:
    """Valid team.toml content for testing."""
    return """
[team]
team_id = "test-team"
team_name = "Test Team"
max_concurrent_members = 5

[team.leader]
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.7
timeout_seconds = 300

[[team.members]]
agent_name = "member1"
agent_type = "plain"
tool_description = "Test member"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.5
max_tokens = 4096
"""


@pytest.fixture
def workspace_with_nested_configs(tmp_path: Path) -> Path:
    """Create a temporary workspace with nested config structure."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    configs_dir = workspace / "configs"
    configs_dir.mkdir()
    return workspace


# ==========================================
# TestRecursiveConfigLoaderBasic
# ==========================================


class TestRecursiveConfigLoaderBasic:
    """RecursiveConfigLoaderの基本機能テスト（正常系）。"""

    def test_load_orchestrator_with_references_returns_correct_structure(
        self,
        workspace_with_nested_configs: Path,
        orchestrator_toml_content: str,
        team_toml_content: str,
        monkeypatch: Any,
    ) -> None:
        """load_orchestrator_with_references()が正しいデータ構造を返すことを確認。"""
        # Arrange: ファイル構造を作成
        configs_dir = workspace_with_nested_configs / "configs"
        orchestrator_toml = configs_dir / "orchestrator.toml"
        orchestrator_toml.write_text(orchestrator_toml_content)

        team1_toml = configs_dir / "team1.toml"
        team1_toml.write_text(team_toml_content)

        team2_toml = configs_dir / "team2.toml"
        team2_toml.write_text(team_toml_content.replace("test-team", "test-team-2"))

        # 環境変数を設定
        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(workspace_with_nested_configs))

        # Act
        loader = RecursiveConfigLoader(workspace=workspace_with_nested_configs)
        result = loader.load_orchestrator_with_references(orchestrator_toml)

        # Assert: 構造を確認
        assert "orchestrator" in result
        assert "teams" in result
        assert "source_file" in result
        assert len(result["teams"]) == 2

        # Orchestrator設定を確認
        from mixseek.config.schema import OrchestratorSettings

        assert isinstance(result["orchestrator"], OrchestratorSettings)
        assert result["orchestrator"].timeout_per_team_seconds == 600

        # Team構造を確認
        team1_data = result["teams"][0]
        assert "team_settings" in team1_data
        assert "source_file" in team1_data
        assert "members" in team1_data

        from mixseek.config.schema import TeamSettings

        assert isinstance(team1_data["team_settings"], TeamSettings)
        assert len(team1_data["members"]) > 0

    def test_workspace_auto_detection_from_configs_directory(
        self,
        workspace_with_nested_configs: Path,
        orchestrator_toml_content: str,
        team_toml_content: str,
        monkeypatch: Any,
    ) -> None:
        """configsディレクトリから自動的にworkspaceが設定されることを確認。"""
        # Arrange: ファイル構造を作成
        configs_dir = workspace_with_nested_configs / "configs"
        orchestrator_toml = configs_dir / "orchestrator.toml"
        orchestrator_toml.write_text(orchestrator_toml_content)

        team1_toml = configs_dir / "team1.toml"
        team1_toml.write_text(team_toml_content)

        team2_toml = configs_dir / "team2.toml"
        team2_toml.write_text(team_toml_content)

        # 環境変数を設定
        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(workspace_with_nested_configs))

        # Act: workspaceをNoneで初期化
        loader = RecursiveConfigLoader(workspace=None)
        result = loader.load_orchestrator_with_references(orchestrator_toml)

        # Assert: workspaceが自動設定された
        assert loader.workspace == workspace_with_nested_configs
        assert "orchestrator" in result

    def test_state_resets_between_loading_sessions(
        self,
        workspace_with_nested_configs: Path,
        orchestrator_toml_content: str,
        team_toml_content: str,
        monkeypatch: Any,
    ) -> None:
        """複数回のロード操作で状態がリセットされることを確認。"""
        # Arrange: ファイル構造を作成
        configs_dir = workspace_with_nested_configs / "configs"
        orchestrator_toml = configs_dir / "orchestrator.toml"
        orchestrator_toml.write_text(orchestrator_toml_content)

        team1_toml = configs_dir / "team1.toml"
        team1_toml.write_text(team_toml_content)

        team2_toml = configs_dir / "team2.toml"
        team2_toml.write_text(team_toml_content)

        # 環境変数を設定
        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(workspace_with_nested_configs))

        loader = RecursiveConfigLoader(workspace=workspace_with_nested_configs)

        # Act: 1回目のロード
        result1 = loader.load_orchestrator_with_references(orchestrator_toml)

        # Assert: 1回目成功
        assert "orchestrator" in result1

        # Act: 2回目のロード（同じファイル）
        result2 = loader.load_orchestrator_with_references(orchestrator_toml)

        # Assert: 2回目も成功（状態がリセットされているため）
        assert "orchestrator" in result2
        assert loader._current_depth == 0
        assert len(loader._visited_files) == 0
        assert len(loader._reference_path) == 0


# ==========================================
# TestCircularReferenceDetection
# ==========================================


class TestCircularReferenceDetection:
    """循環参照検出テスト（T106, FR-042）。"""

    def test_circular_reference_raises_value_error(
        self,
        tmp_path: Path,
        monkeypatch: Any,
    ) -> None:
        """循環参照が検出されるとValueErrorが発生することを確認。"""
        # Arrange: 循環参照を含むファイル構造を作成
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        configs_dir = workspace / "configs"
        configs_dir.mkdir()

        # Orchestrator → Team A → Team B → Team A (循環)
        orchestrator_content = """
[orchestrator]
timeout_per_team_seconds = 600

[[orchestrator.teams]]
config = "configs/team_a.toml"
"""

        # Team Aがteam_bを参照するが、実際には循環を作るのは難しいため、
        # 直接同じファイルを2回訪問するシナリオをテスト
        orchestrator_toml = configs_dir / "orchestrator.toml"
        orchestrator_toml.write_text(orchestrator_content)

        team_a_content = """
[team]
team_id = "team-a"
team_name = "Team A"
max_concurrent_members = 5

[team.leader]
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.7
timeout_seconds = 300
"""

        team_a_toml = configs_dir / "team_a.toml"
        team_a_toml.write_text(team_a_content)

        # 環境変数を設定
        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(workspace))

        # Act & Assert: 循環参照を直接テスト（内部メソッドを使用）
        loader = RecursiveConfigLoader(workspace=workspace)

        # 手動でトラッキング状態を設定して循環参照をシミュレート
        loader._visited_files = set()
        loader._current_depth = 0
        loader._reference_path = []

        # 1回目のロード開始
        resolved_path = team_a_toml.resolve()
        loader._visited_files.add(resolved_path)
        loader._reference_path.append(team_a_toml)

        # 2回目の同じファイルへのアクセス試行
        with pytest.raises(ValueError, match="Circular reference detected"):
            loader._load_team_with_members(team_a_toml)

    def test_circular_reference_error_includes_reference_chain(
        self,
        tmp_path: Path,
        monkeypatch: Any,
    ) -> None:
        """循環参照エラーメッセージに参照チェーンが含まれることを確認。"""
        # Arrange
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        configs_dir = workspace / "configs"
        configs_dir.mkdir()

        team_toml = configs_dir / "team.toml"
        team_toml.write_text(
            """
[team]
team_id = "test-team"
team_name = "Test Team"
max_concurrent_members = 5

[team.leader]
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.7
timeout_seconds = 300
"""
        )

        # 環境変数を設定
        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(workspace))

        loader = RecursiveConfigLoader(workspace=workspace)

        # 手動でトラッキング状態を設定
        orchestrator_file = configs_dir / "orchestrator.toml"
        loader._visited_files = {team_toml.resolve()}
        loader._reference_path = [orchestrator_file, team_toml]
        loader._current_depth = 1

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            loader._load_team_with_members(team_toml)

        # エラーメッセージに参照チェーンが含まれていることを確認
        error_message = str(exc_info.value)
        assert "Circular reference detected" in error_message
        assert "→" in error_message
        assert str(team_toml.name) in error_message


# ==========================================
# TestMaxRecursionDepthLimit
# ==========================================


class TestMaxRecursionDepthLimit:
    """最大再帰深度制限テスト（T107, FR-043）。"""

    def test_max_recursion_depth_raises_value_error(
        self,
        tmp_path: Path,
        monkeypatch: Any,
    ) -> None:
        """最大再帰深度を超えるとValueErrorが発生することを確認。"""
        # Arrange
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        configs_dir = workspace / "configs"
        configs_dir.mkdir()

        team_toml = configs_dir / "team.toml"
        team_toml.write_text(
            """
[team]
team_id = "test-team"
team_name = "Test Team"
max_concurrent_members = 5

[team.leader]
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.7
timeout_seconds = 300
"""
        )

        # 環境変数を設定
        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(workspace))

        loader = RecursiveConfigLoader(workspace=workspace)

        # 手動で最大深度に設定
        loader._current_depth = MAX_CONFIG_RECURSION_DEPTH
        loader._reference_path = [Path(f"file{i}.toml") for i in range(MAX_CONFIG_RECURSION_DEPTH)]

        # Act & Assert
        with pytest.raises(ValueError, match="Maximum recursion depth"):
            loader._load_team_with_members(team_toml)

    def test_max_recursion_depth_error_includes_depth_info(
        self,
        tmp_path: Path,
        monkeypatch: Any,
    ) -> None:
        """最大深度超過エラーメッセージに深度情報が含まれることを確認。"""
        # Arrange
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        configs_dir = workspace / "configs"
        configs_dir.mkdir()

        team_toml = configs_dir / "team.toml"
        team_toml.write_text(
            """
[team]
team_id = "test-team"
team_name = "Test Team"
max_concurrent_members = 5

[team.leader]
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.7
timeout_seconds = 300
"""
        )

        # 環境変数を設定
        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(workspace))

        loader = RecursiveConfigLoader(workspace=workspace)

        # 手動で最大深度に設定
        loader._current_depth = MAX_CONFIG_RECURSION_DEPTH
        loader._reference_path = [Path(f"file{i}.toml") for i in range(MAX_CONFIG_RECURSION_DEPTH)]

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            loader._load_team_with_members(team_toml)

        error_message = str(exc_info.value)
        assert "Maximum recursion depth" in error_message
        assert str(MAX_CONFIG_RECURSION_DEPTH) in error_message
        assert "Current depth:" in error_message
        assert "Reference path:" in error_message


# ==========================================
# TestTrackingAndCleanup
# ==========================================


class TestTrackingAndCleanup:
    """トラッキング・クリーンアップテスト。"""

    def test_tracking_state_is_cleaned_up_after_loading(
        self,
        workspace_with_nested_configs: Path,
        orchestrator_toml_content: str,
        team_toml_content: str,
        monkeypatch: Any,
    ) -> None:
        """ロード完了後にトラッキング状態がクリーンアップされることを確認。"""
        # Arrange: ファイル構造を作成
        configs_dir = workspace_with_nested_configs / "configs"
        orchestrator_toml = configs_dir / "orchestrator.toml"
        orchestrator_toml.write_text(orchestrator_toml_content)

        team1_toml = configs_dir / "team1.toml"
        team1_toml.write_text(team_toml_content)

        team2_toml = configs_dir / "team2.toml"
        team2_toml.write_text(team_toml_content)

        # 環境変数を設定
        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(workspace_with_nested_configs))

        loader = RecursiveConfigLoader(workspace=workspace_with_nested_configs)

        # Act
        loader.load_orchestrator_with_references(orchestrator_toml)

        # Assert: トラッキング状態がクリーンアップされている
        assert loader._current_depth == 0
        assert len(loader._visited_files) == 0
        assert len(loader._reference_path) == 0

    def test_cleanup_allows_file_reuse_in_different_branches(
        self,
        workspace_with_nested_configs: Path,
        team_toml_content: str,
        monkeypatch: Any,
    ) -> None:
        """クリーンアップにより、別ブランチでファイルが再利用可能であることを確認。"""
        # Arrange: 同じteamファイルを2つのorchestratorチームが参照
        configs_dir = workspace_with_nested_configs / "configs"

        shared_team_toml = configs_dir / "shared_team.toml"
        shared_team_toml.write_text(team_toml_content)

        orchestrator_content = """
[orchestrator]
timeout_per_team_seconds = 600

[[orchestrator.teams]]
config = "configs/shared_team.toml"

[[orchestrator.teams]]
config = "configs/shared_team.toml"
"""

        orchestrator_toml = configs_dir / "orchestrator.toml"
        orchestrator_toml.write_text(orchestrator_content)

        # 環境変数を設定
        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(workspace_with_nested_configs))

        loader = RecursiveConfigLoader(workspace=workspace_with_nested_configs)

        # Act: 同じファイルを別ブランチで2回ロード
        result = loader.load_orchestrator_with_references(orchestrator_toml)

        # Assert: 両方のチームが正常にロードされた（循環参照エラーなし）
        assert len(result["teams"]) == 2
        assert result["teams"][0]["source_file"] == shared_team_toml
        assert result["teams"][1]["source_file"] == shared_team_toml
