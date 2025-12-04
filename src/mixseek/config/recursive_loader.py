"""Recursive configuration loader with circular reference detection (Phase 13 T104, T106, T107).

Provides recursive loading of orchestrator → team → member configuration hierarchies
with built-in circular reference detection and maximum depth limit.

Article 9 Compliance:
- Explicit error messages with reference paths
- No implicit defaults or assumptions
- Proper error propagation

Requirements:
- FR-040: Recursive loading of orchestrator/team/member configs
- FR-042: Circular reference detection
- FR-043: Maximum recursion depth limit (10 levels)
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from mixseek.config.constants import MAX_CONFIG_RECURSION_DEPTH


class RecursiveConfigLoader:
    """Loads configuration files recursively with circular reference detection.

    This class tracks visited files and recursion depth to prevent infinite loops
    and stack overflow in nested configuration references.

    Attributes:
        workspace: Workspace directory for resolving relative paths
        _visited_files: Set of already-visited file paths (for circular reference detection)
        _current_depth: Current recursion depth (for max depth limit)
        _reference_path: List of file paths in the current reference chain (for error messages)

    Examples:
        >>> loader = RecursiveConfigLoader(workspace=Path("/workspace"))
        >>> data = loader.load_orchestrator_with_references(Path("orchestrator.toml"))
        >>> print(data["orchestrator"].timeout_per_team_seconds)
        600
    """

    def __init__(self, workspace: Path | None = None) -> None:
        """Initialize the recursive config loader.

        Args:
            workspace: Workspace directory for resolving relative paths.
                      If None, workspace will be set from orchestrator file's directory.
        """
        self.workspace = workspace
        self._visited_files: set[Path] = set()
        self._current_depth: int = 0
        self._reference_path: list[Path] = []

    def load_orchestrator_with_references(
        self,
        file_path: Path,
    ) -> dict[str, Any]:
        """Load orchestrator TOML with all referenced team and member configs.

        This method recursively loads orchestrator → team → member configurations,
        detecting circular references and enforcing maximum recursion depth.

        Args:
            file_path: Path to orchestrator TOML file

        Returns:
            Dictionary containing:
            - "orchestrator": OrchestratorSettings instance
            - "teams": List of team data with members
            - "source_file": Path to the orchestrator TOML file

        Raises:
            FileNotFoundError: If any config file is not found
            ValueError: If circular reference or max depth exceeded
            tomllib.TOMLDecodeError: If TOML syntax is invalid

        Phase 13 T104, T106, T107: FR-040, FR-042, FR-043
        """
        # Reset state for new loading session
        self._visited_files = set()
        self._current_depth = 0
        self._reference_path = []

        # Load orchestrator with tracking
        return self._load_orchestrator_internal(file_path)

    def _load_with_recursion_protection(
        self,
        file_path: Path,
        load_callback: Callable[[Path], dict[str, Any]],
    ) -> dict[str, Any]:
        """循環参照・最大深度チェック付きで設定を読み込む（Template Method）。

        Article 10（DRY原則）準拠：循環参照チェックロジックの重複を排除。
        Article 11（Refactoring Policy）準拠：既存クラスを直接改善（V2クラス作成なし）。

        Args:
            file_path: 読み込む設定ファイルパス
            load_callback: 実際のロード処理を行うコールバック関数

        Returns:
            読み込まれた設定データ

        Raises:
            ValueError: 循環参照または最大深度超過の場合
        """
        # Check circular reference (T106: FR-042)
        resolved_path = file_path.resolve()
        if resolved_path in self._visited_files:
            reference_chain = " → ".join(str(p) for p in self._reference_path)
            raise ValueError(f"Circular reference detected in configuration files:\n{reference_chain} → {file_path}")

        # Check maximum depth (T107: FR-043)
        if self._current_depth >= MAX_CONFIG_RECURSION_DEPTH:
            reference_chain = " → ".join(str(p) for p in self._reference_path)
            raise ValueError(
                f"Maximum recursion depth ({MAX_CONFIG_RECURSION_DEPTH}) exceeded "
                f"while loading configuration files.\n"
                f"Current depth: {self._current_depth + 1}\n"
                f"Reference path: {reference_chain} → {file_path}"
            )

        # Track this file
        self._visited_files.add(resolved_path)
        self._reference_path.append(file_path)
        self._current_depth += 1

        try:
            # 実際のロード処理（コールバックに委譲）
            return load_callback(file_path)
        finally:
            # Cleanup tracking (allow revisiting in different branches)
            self._current_depth -= 1
            self._reference_path.pop()
            # Remove from visited files to allow reuse in different branches
            self._visited_files.discard(resolved_path)

    def _load_orchestrator_internal(self, file_path: Path) -> dict[str, Any]:
        """Internal method to load orchestrator config with recursion tracking."""

        def load_orchestrator(path: Path) -> dict[str, Any]:
            # Set workspace from orchestrator file's directory if not already set
            if self.workspace is None:
                # If orchestrator is in a 'configs' directory, use its parent as workspace
                # Otherwise, use orchestrator file's directory as workspace
                orchestrator_dir = path.resolve().parent
                if orchestrator_dir.name == "configs":
                    self.workspace = orchestrator_dir.parent
                else:
                    self.workspace = orchestrator_dir

            # Load orchestrator settings
            from mixseek.config import ConfigurationManager

            manager = ConfigurationManager(workspace=self.workspace)
            orchestrator_settings = manager.load_orchestrator_settings(path)

            # Load teams recursively
            teams_data = []
            for team_entry in orchestrator_settings.teams:
                team_config_path = team_entry.get("config")
                if not team_config_path:
                    continue

                # Resolve relative path relative to workspace
                # Team config paths in orchestrator.toml are workspace-relative
                team_path = Path(team_config_path)
                if not team_path.is_absolute():
                    team_path = self.workspace / team_path

                # Load team with members (uses existing ConfigurationManager)
                team_data = self._load_team_with_members(team_path)
                teams_data.append(team_data)

            result = {
                "orchestrator": orchestrator_settings,
                "teams": teams_data,
                "source_file": path,
            }

            # Load standalone settings at the same level as orchestrator/teams
            # Always load these settings (even if using defaults)

            # Evaluator settings
            evaluator_settings = manager.get_evaluator_settings(orchestrator_settings.evaluator_config)
            evaluator_path = None
            if orchestrator_settings.evaluator_config:
                path_candidate = Path(orchestrator_settings.evaluator_config)
                if not path_candidate.is_absolute():
                    path_candidate = self.workspace / path_candidate
                evaluator_path = path_candidate
            else:
                default_path = self.workspace / "configs" / "evaluator.toml"
                if default_path.exists():
                    evaluator_path = default_path
            result["evaluator"] = {
                "settings": evaluator_settings,
                "source_file": evaluator_path,
            }

            # Judgment settings
            judgment_settings = manager.get_judgment_settings(orchestrator_settings.judgment_config)
            judgment_path = None
            if orchestrator_settings.judgment_config:
                path_candidate = Path(orchestrator_settings.judgment_config)
                if not path_candidate.is_absolute():
                    path_candidate = self.workspace / path_candidate
                judgment_path = path_candidate
            else:
                default_path = self.workspace / "configs" / "judgment.toml"
                if default_path.exists():
                    judgment_path = default_path
            result["judgment"] = {
                "settings": judgment_settings,
                "source_file": judgment_path,
            }

            # PromptBuilder settings
            prompt_builder_settings = manager.get_prompt_builder_settings(orchestrator_settings.prompt_builder_config)
            prompt_builder_path = None
            if orchestrator_settings.prompt_builder_config:
                path_candidate = Path(orchestrator_settings.prompt_builder_config)
                if not path_candidate.is_absolute():
                    path_candidate = self.workspace / path_candidate
                prompt_builder_path = path_candidate
            else:
                default_path = self.workspace / "configs" / "prompt_builder.toml"
                if default_path.exists():
                    prompt_builder_path = default_path
            result["prompt_builder"] = {
                "settings": prompt_builder_settings,
                "source_file": prompt_builder_path,
            }

            return result

        return self._load_with_recursion_protection(file_path, load_orchestrator)

    def _load_team_with_members(self, team_path: Path) -> dict[str, Any]:
        """Load team config with all referenced member configs."""

        def load_team(path: Path) -> dict[str, Any]:
            # Load team settings (automatically loads referenced members)
            from mixseek.config import ConfigurationManager

            manager = ConfigurationManager(workspace=self.workspace)
            team_settings = manager.load_team_settings(path)

            # Extract member info from team settings
            members_data = []
            for member in team_settings.members:
                members_data.append(
                    {
                        "member_settings": member,
                        "source_file": None,  # Member source tracking can be added later
                    }
                )

            return {
                "team_settings": team_settings,
                "source_file": path,
                "members": members_data,
            }

        return self._load_with_recursion_protection(team_path, load_team)
