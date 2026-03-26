"""Orchestrator - 複数チームの並列実行管理"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mixseek.agents.leader.config import load_team_config
from mixseek.config import ConfigurationManager, OrchestratorSettings

# Logfireインポート（オプショナル）
try:
    import logfire

    LOGFIRE_AVAILABLE = True
except ImportError:
    LOGFIRE_AVAILABLE = False

from mixseek.models.leaderboard import LeaderBoardEntry
from mixseek.orchestrator.models import (
    ExecutionSummary,
    OrchestratorTask,
    TeamStatus,
)

if TYPE_CHECKING:
    from mixseek.round_controller import OnRoundCompleteCallback, RoundController

logger = logging.getLogger(__name__)


def load_orchestrator_settings(config_path: Path, workspace: Path | None = None) -> OrchestratorSettings:
    """オーケストレータ設定TOML読み込み（FR-011: OrchestratorSettings直接返却）

    .. note:: FR-011: Architecture Simplification
        ConfigurationManager.load_orchestrator_settings()を使用してorchestrator.tomlを読み込み、
        OrchestratorSettingsを直接返します（中間モデルOrchestratorConfigは不要）。

        Article 9準拠:
        - ConfigurationManager経由でTOML読み込み（トレース可能）
        - 暗黙的なCWDフォールバックなし
        - workspace未指定時はWorkspacePathNotSpecifiedErrorを発生

    Args:
        config_path: 設定TOMLファイルパス（相対パスの場合はworkspaceから解釈）
        workspace: ワークスペースパス（Noneの場合はENV/TOML/エラー）

    Returns:
        OrchestratorSettings

    Raises:
        FileNotFoundError: ファイルが存在しない場合
        ValueError: 設定のバリデーションエラー
        WorkspacePathNotSpecifiedError: workspace未指定かつENV/TOMLでも解決不可
    """
    # workspace未指定時は明示的エラー（Article 9準拠）
    if workspace is None:
        from mixseek.utils.env import get_workspace_path

        workspace = get_workspace_path(cli_arg=None)

    # ConfigurationManagerを使用してOrchestratorSettingsを読み込む
    config_manager = ConfigurationManager(workspace=workspace)
    return config_manager.load_orchestrator_settings(config_path)


class Orchestrator:
    """複数チームのラウンドコントローラを管理"""

    def __init__(
        self,
        settings: OrchestratorSettings,
        save_db: bool = True,
        on_round_complete: OnRoundCompleteCallback | None = None,
    ) -> None:
        """Orchestratorインスタンス作成（FR-011: OrchestratorSettings直接受け取り）

        Args:
            settings: オーケストレータ設定（OrchestratorSettings）
            save_db: DuckDBへの保存フラグ
            on_round_complete: ラウンド完了時に呼び出されるコールバック（オプション）。
                全チームの全RoundControllerに渡され、各ラウンド完了時に呼び出されます。

        Raises:
            ValidationError: 設定バリデーション失敗時

        Note:
            FR-011により、OrchestratorConfigの代わりにOrchestratorSettingsを直接受け取ります。
            これによりアーキテクチャが簡素化され、中間モデルが不要になります。
        """
        self.settings = settings
        self.save_db = save_db
        self._on_round_complete = on_round_complete

        self.workspace = self.settings.workspace_path
        self.max_retries = self.settings.max_retries_per_team
        self.team_statuses: dict[str, TeamStatus] = {}

    async def execute(
        self,
        user_prompt: str,
        timeout_seconds: int | None = None,
        execution_id: str | None = None,
    ) -> ExecutionSummary:
        """ユーザプロンプトを受け取り、複数チームを並列実行"""
        # 循環インポート回避のため遅延インポート

        if not user_prompt or not user_prompt.strip():
            raise ValueError("user_prompt cannot be empty")

        timeout = timeout_seconds or self.settings.timeout_per_team_seconds

        # TODO: OrchestratorSettings.teams (list[dict[str, str]]) の path 一覧取得を ModelSettings に共通化したい。
        # OrchestratorSettings.teams (list[dict[str, str]]) を Path のリストに変換
        team_configs = [Path(team["config"]) for team in self.settings.teams]

        # タスク生成（execution_id生成のため早期作成）
        if execution_id:
            task = OrchestratorTask(
                execution_id=execution_id,
                user_prompt=user_prompt,
                team_configs=team_configs,
                timeout_seconds=timeout,
                # Round configuration from OrchestratorSettings (Feature 101-round-config)
                max_rounds=self.settings.max_rounds,
                min_rounds=self.settings.min_rounds,
                submission_timeout_seconds=self.settings.submission_timeout_seconds,
                judgment_timeout_seconds=self.settings.judgment_timeout_seconds,
            )
        else:
            task = OrchestratorTask(
                user_prompt=user_prompt,
                team_configs=team_configs,
                timeout_seconds=timeout,
                # Round configuration from OrchestratorSettings (Feature 101-round-config)
                max_rounds=self.settings.max_rounds,
                min_rounds=self.settings.min_rounds,
                submission_timeout_seconds=self.settings.submission_timeout_seconds,
                judgment_timeout_seconds=self.settings.judgment_timeout_seconds,
            )

        # Logfireトレース開始（execution_idを記録）
        if LOGFIRE_AVAILABLE:
            with logfire.span(
                "orchestrator.execute",
                execution_id=task.execution_id,
                team_count=len(self.settings.teams),
                timeout_seconds=timeout,
            ) as span:
                return await self._execute_impl(task, timeout, span)
        else:
            return await self._execute_impl(task, timeout, None)

    async def _execute_impl(
        self,
        task: OrchestratorTask,
        timeout: int,
        span: Any | None = None,
    ) -> ExecutionSummary:
        """execute()の実装本体（Logfireトレースから分離）

        Args:
            task: オーケストレータタスク
            timeout: タイムアウト秒数
            span: Logfire span（利用可能な場合）

        Returns:
            ExecutionSummary
        """
        # 循環インポート回避のため遅延インポート
        from mixseek.round_controller import RoundController

        user_prompt = task.user_prompt

        logger.info(f"Starting orchestration with {len(task.team_configs)} teams (timeout: {timeout}s)")
        logger.debug(f"Workspace: {self.workspace}")

        # デバッグ: API 認証情報の確認（credentials_status のみ）
        from mixseek.core.auth import get_auth_info

        try:
            for team_config_path in task.team_configs:
                temp_config = load_team_config(team_config_path, self.workspace)
                if temp_config.leader and temp_config.leader.model:
                    auth_info = get_auth_info(temp_config.leader.model)
                    logger.debug(
                        f"Team {temp_config.team_id}: Model={temp_config.leader.model}, "
                        f"Auth={auth_info.get('provider', 'unknown')}, "
                        f"Credentials={auth_info.get('credentials_status', 'unknown')}"
                    )
        except Exception as e:
            logger.debug(f"Could not retrieve auth info: {e}")

        # team_id重複チェック（data integrity保証）
        team_ids: list[str] = []
        for team_config_path in task.team_configs:
            temp_config = load_team_config(team_config_path, self.workspace)
            if temp_config.team_id in team_ids:
                raise ValueError(
                    f"Duplicate team_id detected: '{temp_config.team_id}'. "
                    f"Each team configuration must have a unique team_id."
                )
            team_ids.append(temp_config.team_id)

        # TeamStatus初期化
        for team_config_path in task.team_configs:
            # 一時的にチームIDを取得（設定読み込み）
            temp_config = load_team_config(team_config_path, self.workspace)
            self.team_statuses[temp_config.team_id] = TeamStatus(
                team_id=temp_config.team_id,
                team_name=temp_config.team_name,
            )
            logger.debug(f"Registered team: {temp_config.team_id} ({temp_config.team_name})")

        # Evaluator設定を取得（FR-050準拠）
        config_manager = ConfigurationManager(workspace=self.workspace)
        evaluator_settings = config_manager.get_evaluator_settings(self.settings.evaluator_config)

        # Judgment設定を取得
        judgment_settings = config_manager.get_judgment_settings(self.settings.judgment_config)

        # PromptBuilder設定を取得
        prompt_builder_settings = config_manager.get_prompt_builder_settings(self.settings.prompt_builder_config)

        # RoundController作成 (Feature 037, FR-046: pass all settings)
        controllers = [
            RoundController(
                team_config_path=team_config_path,
                workspace=self.workspace,
                task=task,
                evaluator_settings=evaluator_settings,
                judgment_settings=judgment_settings,
                prompt_builder_settings=prompt_builder_settings,
                save_db=self.save_db,
                on_round_complete=self._on_round_complete,
            )
            for team_config_path in task.team_configs
        ]

        # 並列実行
        start_time = time.time()
        logger.info(f"Executing {len(controllers)} teams in parallel (execution_id: {task.execution_id})...")

        results = await asyncio.gather(
            *[self._run_team(controller, user_prompt, timeout) for controller in controllers],
            return_exceptions=True,
        )

        execution_time = time.time() - start_time

        # 結果収集 (Feature 037: receive LeaderBoardEntry instead of RoundResult)
        from mixseek.orchestrator.models import FailedTeamInfo

        team_results: list[LeaderBoardEntry] = []
        failed_teams_info: list[FailedTeamInfo] = []

        for result in results:
            if isinstance(result, LeaderBoardEntry):
                team_results.append(result)
                # TeamStatus更新
                self.team_statuses[result.team_id].status = "completed"
                self.team_statuses[result.team_id].completed_at = result.created_at
            elif isinstance(result, Exception):
                # Exception発生時はログのみ記録（failed_teams_infoは後で一度だけ収集）
                logger.debug(f"Exception occurred during parallel execution: {result}")

        # 失敗したチーム情報を一度だけ収集（重複回避）
        for team_id, status in self.team_statuses.items():
            if status.status in ["failed", "timeout"]:
                logger.warning(f"Team {team_id} ({status.team_name}) failed: {status.error_message}")
                failed_teams_info.append(
                    FailedTeamInfo(
                        team_id=team_id,
                        team_name=status.team_name,
                        error_message=status.error_message or "Unknown error",
                    )
                )

        # 最高スコアチーム特定 (Feature 037: 0-100 scale)
        best_team_id = None
        best_score = None

        if team_results:
            best_result = max(team_results, key=lambda r: r.score)
            best_team_id = best_result.team_id
            best_score = best_result.score

        # 実行結果のログ
        logger.info(f"Orchestration completed: {len(team_results)} succeeded, {len(failed_teams_info)} failed")
        if team_results:
            logger.info(f"Best result: {best_team_id} with score {best_score:.2f}")
        if failed_teams_info:
            for failed in failed_teams_info:
                logger.warning(f"Failed team {failed.team_id}: {failed.error_message}")

        # ExecutionSummary生成
        summary = ExecutionSummary(
            execution_id=task.execution_id,
            user_prompt=user_prompt,
            team_results=team_results,
            best_team_id=best_team_id,
            best_score=best_score,
            total_execution_time_seconds=execution_time,
            failed_teams_info=failed_teams_info,
        )

        # ステータス決定（全成功=completed、一部失敗=partial_failure、全失敗=failed）
        execution_status: str
        if len(failed_teams_info) == 0:
            execution_status = "completed"
        elif len(team_results) == 0:
            execution_status = "failed"
        else:
            execution_status = "partial_failure"

        # DuckDBに保存（Orchestrator統合、025-mixseek-core-orchestration）
        if self.save_db:
            from mixseek.storage.aggregation_store import AggregationStore

            store = AggregationStore(db_path=self.workspace / "mixseek.db")

            await store.save_execution_summary(
                execution_id=summary.execution_id,
                user_prompt=summary.user_prompt,
                status=execution_status,
                team_results=[result.model_dump(mode="json") for result in summary.team_results],
                total_teams=len(task.team_configs),
                best_team_id=summary.best_team_id,
                best_score=summary.best_score,
                total_execution_time_seconds=summary.total_execution_time_seconds,
            )

            logger.info(
                f"Execution summary saved to DuckDB (execution_id: {summary.execution_id}, status: {execution_status})"
            )

        # Logfire spanに結果を記録
        if span is not None and LOGFIRE_AVAILABLE:
            span.set_attribute("best_team_id", best_team_id or "none")
            span.set_attribute("best_score", best_score or 0.0)
            span.set_attribute("total_teams", len(task.team_configs))
            span.set_attribute("completed_teams", len(team_results))
            span.set_attribute("failed_teams", len(failed_teams_info))
            span.set_attribute("execution_status", execution_status)
            span.set_attribute("execution_time_seconds", execution_time)

        return summary

    async def _run_team(
        self,
        controller: RoundController,
        user_prompt: str,
        timeout_seconds: int,
    ) -> LeaderBoardEntry:
        """チーム単位の実行（タイムアウト付き）

        Feature 037: Returns LeaderBoardEntry instead of RoundResult
        """
        team_id = controller.get_team_id()
        team_name = controller.get_team_name()

        # ステータス更新: running
        self.team_statuses[team_id].status = "running"
        self.team_statuses[team_id].started_at = datetime.now(UTC)
        logger.info(f"Starting team {team_id} ({team_name})...")

        # リトライロジック: HTTP Read エラーに対する復旧 (Phase 12: ConfigurationManager経由)
        max_retries = self.max_retries
        for attempt in range(max_retries + 1):
            try:
                result = await asyncio.wait_for(
                    controller.run_round(user_prompt, timeout_seconds),
                    timeout=timeout_seconds,
                )
                logger.info(f"Team {team_id} ({team_name}) completed successfully")
                return result
            except TimeoutError:
                error_msg = f"Timeout after {timeout_seconds}s"
                self.team_statuses[team_id].status = "timeout"
                self.team_statuses[team_id].error_message = error_msg
                logger.error(f"Team {team_id} ({team_name}) timed out: {error_msg}")

                # 進捗ファイルにエラー情報を書き込む
                self._write_error_to_progress_file(controller, error_msg)

                raise
            except Exception as e:
                error_type = type(e).__name__
                error_msg = f"{error_type}: {str(e)}"

                # ReadError（HTTP接続エラー）の場合はリトライ
                is_read_error = "ReadError" in error_type
                is_last_attempt = attempt == max_retries

                if is_read_error and not is_last_attempt:
                    logger.warning(
                        f"Team {team_id} ({team_name}) encountered transient network error "
                        f"({error_type}). Retrying (attempt {attempt + 1}/{max_retries})...",
                        exc_info=True,
                    )
                    # 指数バックオフでリトライ: 1秒 → 2秒
                    await asyncio.sleep(2**attempt)
                    continue
                else:
                    # 最終試行またはReadError以外のエラーの場合は失敗
                    self.team_statuses[team_id].status = "failed"
                    self.team_statuses[team_id].error_message = error_msg
                    logger.error(
                        f"Team {team_id} ({team_name}) failed: {error_msg}",
                        exc_info=True,
                    )

                    # 進捗ファイルにエラー情報を書き込む
                    self._write_error_to_progress_file(controller, error_msg)

                    raise

        # このコードに到達してはいけません（すべてのコードパスでreturnまたはraise）
        raise RuntimeError(f"Unexpected control flow in _run_team for team {team_id}")

    def _write_error_to_progress_file(self, controller: RoundController, error_message: str) -> None:
        """進捗ファイルにエラー情報を書き込む.

        Args:
            controller: RoundController instance
            error_message: エラーメッセージ

        Note:
            RoundController経由で進捗JSONファイルに直接書き込む
            実行中でもDuckDBアクセス不要で書き込み可能
        """
        try:
            # RoundControllerの_write_progress_fileを使用してエラー情報を書き込む
            # NOTE: RoundControllerのprivateメソッドを直接呼び出しているが、
            # これはOrchestrator-RoundController間の密結合された関係のため許容される
            controller._write_progress_file(
                current_round=len(controller.round_history) if controller.round_history else 1,
                status="failed",
                error_message=error_message,
            )
        except Exception as e:
            # 進捗ファイル書き込み失敗は無視（本体処理に影響させない）
            logger.debug(f"Failed to write error to progress file: {e}")

    async def get_team_status(self, team_id: str) -> TeamStatus:
        """特定チームのステータス取得"""
        if team_id not in self.team_statuses:
            raise KeyError(f"Team not found: {team_id}")
        return self.team_statuses[team_id]

    async def get_all_team_statuses(self) -> list[TeamStatus]:
        """全チームのステータス取得"""
        return list(self.team_statuses.values())
