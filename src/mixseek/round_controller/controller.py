"""Round Controller - ラウンドライフサイクル管理

Feature: 037-mixseek-core-round-controller
This module manages multi-round execution for a single team.
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mixseek.agents.leader.agent import create_leader_agent
from mixseek.agents.leader.config import team_settings_to_team_config
from mixseek.agents.leader.dependencies import TeamDependencies
from mixseek.agents.leader.models import MemberSubmissionsRecord
from mixseek.agents.member.factory import MemberAgentFactory
from mixseek.config import ConfigurationManager
from mixseek.config.member_agent_loader import member_settings_to_config
from mixseek.config.schema import EvaluatorSettings, JudgmentSettings, PromptBuilderSettings
from mixseek.evaluator import Evaluator
from mixseek.models.evaluation_config import EvaluationConfig  # noqa: F401
from mixseek.models.evaluation_request import EvaluationRequest
from mixseek.models.leaderboard import LeaderBoardEntry
from mixseek.orchestrator.models import OrchestratorTask
from mixseek.prompt_builder import UserPromptBuilder
from mixseek.prompt_builder.models import RoundPromptContext
from mixseek.round_controller.judgment_client import JudgmentClient
from mixseek.round_controller.models import OnRoundCompleteCallback, RoundState
from mixseek.storage.aggregation_store import AggregationStore

logger = logging.getLogger(__name__)

# Logfireインポート(オプショナル)
try:
    import logfire

    LOGFIRE_AVAILABLE = True
except ImportError:
    LOGFIRE_AVAILABLE = False

# Pydantic循環参照を解決
EvaluationRequest.model_rebuild()


class RoundController:
    """Round Controller for single team multi-round execution

    This controller manages the entire lifecycle of rounds for a single team,
    from initial submission to termination decision.
    """

    def __init__(
        self,
        team_config_path: Path,
        workspace: Path,
        task: OrchestratorTask,
        evaluator_settings: EvaluatorSettings,
        judgment_settings: JudgmentSettings,
        prompt_builder_settings: PromptBuilderSettings,
        save_db: bool = True,
        on_round_complete: OnRoundCompleteCallback | None = None,
    ) -> None:
        """Initialize RoundController instance

        .. note:: FR-046準拠
            Orchestrator から EvaluatorSettings, JudgmentSettings, PromptBuilderSettings を受け取ります。

        Args:
            team_config_path: Team configuration TOML file path
            workspace: Workspace path
            task: Orchestrator task containing round configuration
            evaluator_settings: Evaluator configuration (from Orchestrator)
            judgment_settings: Judgment configuration (from Orchestrator)
            prompt_builder_settings: PromptBuilder configuration (from Orchestrator)
            save_db: DuckDBへの保存フラグ
            on_round_complete: Callback invoked after each round completes.
                Receives (RoundState, list[MemberSubmission]). Exceptions are logged but don't stop execution.

        Raises:
            FileNotFoundError: If team_config_path does not exist
            ValidationError: If team configuration is invalid
        """
        # T088 fix: Use ConfigurationManager to load TeamSettings
        config_manager = ConfigurationManager(workspace=workspace)
        team_settings = config_manager.load_team_settings(team_config_path)

        # Convert to TeamConfig for backward compatibility
        self.team_config = team_settings_to_team_config(team_settings)
        self.team_settings = team_settings  # Keep for member agent creation
        self.workspace = workspace
        self.task = task
        self.evaluator_settings = evaluator_settings
        self.judgment_settings = judgment_settings
        self.prompt_builder_settings = prompt_builder_settings
        self.save_db = save_db
        if self.save_db:
            self.store: AggregationStore | None = AggregationStore(db_path=self.workspace / "mixseek.db")
        else:
            self.store = None
        self.round_history: list[RoundState] = []
        self._on_round_complete = on_round_complete

        # Initialize UserPromptBuilder for prompt formatting with settings
        self.prompt_builder = UserPromptBuilder(settings=prompt_builder_settings, store=self.store)

        # Initialize JudgmentClient with settings
        self.judgment_client = JudgmentClient(settings=judgment_settings)

    def get_team_id(self) -> str:
        """Get team identifier"""
        return self.team_config.team_id

    def get_team_name(self) -> str:
        """Get team name"""
        return self.team_config.team_name

    def _write_progress_file(
        self,
        current_round: int,
        status: str = "running",
        current_agent: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """進捗ファイルを書き出す（UI用）.

        Args:
            current_round: 現在のラウンド番号
            status: 実行ステータス（"running", "completed", or "failed"）
            current_agent: 現在実行中のエージェント（"leader", "evaluator", or None）
            error_message: エラーメッセージ（status="failed"時に設定）

        Note:
            進捗ファイル: $MIXSEEK_WORKSPACE/logs/{execution_id}.{team_id}.progress.json
            UIはこのファイルからリアルタイム進捗を取得する
        """
        try:
            # logsディレクトリを確保
            logs_dir = self.workspace / "logs"
            logs_dir.mkdir(exist_ok=True)

            # 進捗ファイルパス（チームごとに分離）
            progress_file = logs_dir / f"{self.task.execution_id}.{self.team_config.team_id}.progress.json"

            # 進捗データ
            progress_data = {
                "execution_id": self.task.execution_id,
                "status": status,
                "current_round": current_round,
                "total_rounds": self.task.max_rounds,
                "team_id": self.team_config.team_id,
                "team_name": self.team_config.team_name,
                "current_agent": current_agent,
                "updated_at": datetime.now(UTC).isoformat(),
            }

            # エラーメッセージを追加（存在する場合）
            if error_message:
                progress_data["error_message"] = error_message

            # JSON書き出し（上書き）
            with open(progress_file, "w") as f:
                json.dump(progress_data, f, indent=2)

        except Exception:
            # 進捗ファイル書き出し失敗は無視（本体処理に影響させない）
            pass

    async def run_round(
        self,
        user_prompt: str,
        timeout_seconds: int,
    ) -> LeaderBoardEntry:
        """Execute rounds and return the best LeaderBoardEntry

        This is the main entry point for Round Controller.
        Implements User Story 2: multi-round execution with improvement judgment.

        Args:
            user_prompt: User prompt
            timeout_seconds: Timeout (seconds)

        Returns:
            LeaderBoardEntry: Best submission entry

        Raises:
            Exception: If round execution fails
        """
        # Logfireトレース開始
        if LOGFIRE_AVAILABLE:
            with logfire.span(
                "round_controller.run_round",
                team_id=self.team_config.team_id,
                team_name=self.team_config.team_name,
                execution_id=self.task.execution_id,
                max_rounds=self.task.max_rounds,
                min_rounds=self.task.min_rounds,
                timeout_seconds=timeout_seconds,
            ) as span:
                return await self._run_round_impl(user_prompt, timeout_seconds, span)
        else:
            return await self._run_round_impl(user_prompt, timeout_seconds, None)

    async def _run_round_impl(
        self,
        user_prompt: str,
        timeout_seconds: int,
        span: Any | None = None,
    ) -> LeaderBoardEntry:
        """run_round() implementation with multi-round loop

        Args:
            user_prompt: User prompt
            timeout_seconds: Timeout (seconds)
            span: Logfire span (if available)

        Returns:
            LeaderBoardEntry: Best submission entry
        """
        # T026: Multi-round loop
        for round_number in range(1, self.task.max_rounds + 1):
            # 進捗ファイル更新（ラウンド開始）
            self._write_progress_file(round_number, status="running")

            # Format prompt for this round
            formatted_prompt = await self._format_prompt_for_round(user_prompt, round_number)

            # Execute single round
            round_state = await self._execute_single_round(
                round_number, formatted_prompt, user_prompt, timeout_seconds
            )
            self.round_history.append(round_state)

            # T023: Round continuation judgment (3-stage)
            should_continue, exit_reason = await self._should_continue_round(user_prompt, round_number)

            if not should_continue:
                # T027-T029: Finalize and return best submission
                return await self._finalize_and_return_best(exit_reason, span)

        # Max rounds reached
        return await self._finalize_and_return_best("max_rounds_reached", span)

    async def _format_prompt_for_round(self, user_prompt: str, round_number: int) -> str:
        """Format prompt for specific round using UserPromptBuilder

        Args:
            user_prompt: Original user prompt
            round_number: Current round number

        Returns:
            Formatted prompt string
        """
        # Create context for UserPromptBuilder
        context = RoundPromptContext(
            user_prompt=user_prompt,
            round_number=round_number,
            round_history=self.round_history,
            team_id=self.team_config.team_id,
            team_name=self.team_config.team_name,
            execution_id=self.task.execution_id,
            store=self.store,
        )

        return await self.prompt_builder.build_team_prompt(context)

    async def _execute_single_round(
        self,
        round_number: int,
        user_prompt: str,
        original_user_prompt: str,
        timeout_seconds: int,
    ) -> RoundState:
        """Execute a single round

        Args:
            round_number: Current round number
            user_prompt: Formatted user prompt (with history/ranking for Leader Agent)
            original_user_prompt: Original user prompt (for Evaluator)
            timeout_seconds: Timeout (seconds)

        Returns:
            RoundState: Completed round state
        """
        round_started_at = datetime.now(UTC)

        # 1. Create Member Agents
        # T088 fix: Use member_settings_to_config() for consistent MemberAgentConfig generation
        member_agents: dict[str, object] = {}
        for member_settings in self.team_settings.members:
            # member_settings_to_config()を使用（詳細設定を保持）
            member_config = member_settings_to_config(member_settings, agent_data=None, workspace=self.workspace)

            member_agent = MemberAgentFactory.create_agent(member_config)
            member_agents[member_settings.agent_name] = member_agent

        # 2. Execute Leader Agent
        # 進捗ファイル更新: Leader実行開始
        self._write_progress_file(round_number, status="running", current_agent="leader")

        leader_agent = create_leader_agent(self.team_config, member_agents)
        deps = TeamDependencies(
            execution_id=self.task.execution_id,
            team_id=self.team_config.team_id,
            team_name=self.team_config.team_name,
            round_number=round_number,
        )

        result = await leader_agent.run(user_prompt, deps=deps)
        submission_content: str = result.output
        message_history = result.all_messages()

        # 進捗ファイル更新: Leader実行完了
        self._write_progress_file(round_number, status="running", current_agent=None)

        # 3. Save round history (existing table)
        member_record = MemberSubmissionsRecord(
            execution_id=self.task.execution_id,
            team_id=self.team_config.team_id,
            team_name=self.team_config.team_name,
            round_number=round_number,
            submissions=deps.submissions,
        )

        if self.store is not None:
            await self.store.save_aggregation(self.task.execution_id, member_record, message_history)

        # 4. Execute Evaluator
        # 進捗ファイル更新: Evaluator実行開始
        self._write_progress_file(round_number, status="running", current_agent="evaluator")

        # FR-046準拠: EvaluatorSettings と PromptBuilderSettings から Evaluator を生成
        evaluator = Evaluator(
            settings=self.evaluator_settings,
            prompt_builder_settings=self.prompt_builder_settings,
        )
        request = EvaluationRequest(
            user_query=original_user_prompt,
            submission=submission_content,
            team_id=self.team_config.team_id,
        )

        evaluation_result = await evaluator.evaluate(request)
        evaluation_score = evaluation_result.overall_score

        # 進捗ファイル更新: Evaluator実行完了
        self._write_progress_file(round_number, status="running", current_agent=None)

        # Build score_details
        score_details: dict[str, Any] = {
            "overall_score": evaluation_score,
            "metrics": [
                {
                    "metric_name": metric.metric_name,
                    "score": metric.score,
                    "evaluator_comment": metric.evaluator_comment,
                }
                for metric in evaluation_result.metrics
            ],
        }

        round_ended_at = datetime.now(UTC)

        # 5. Save to leader_board table
        if self.store is not None:
            await self.store.save_to_leader_board(
                execution_id=self.task.execution_id,
                team_id=self.team_config.team_id,
                team_name=self.team_config.team_name,
                round_number=round_number,
                submission_content=submission_content,
                submission_format="md",
                score=evaluation_score,
                score_details=score_details,
                final_submission=False,  # Will be updated later
                exit_reason=None,
            )

        # 6. Save to round_status table (without judgment yet)
        if self.store is not None:
            await self.store.save_round_status(
                execution_id=self.task.execution_id,
                team_id=self.team_config.team_id,
                team_name=self.team_config.team_name,
                round_number=round_number,
                should_continue=None,  # Will be updated after judgment
                reasoning=None,
                confidence_score=None,
                round_started_at=round_started_at.isoformat(),
                round_ended_at=round_ended_at.isoformat(),
            )

        # 7. Create RoundState
        round_state = RoundState(
            round_number=round_number,
            submission_content=submission_content,
            evaluation_score=evaluation_score,
            score_details=score_details,
            improvement_judgment=None,  # Will be set after judgment
            round_started_at=round_started_at,
            round_ended_at=round_ended_at,
            message_history=[],
        )

        # 8. Call on_round_complete hook (if set)
        if self._on_round_complete:
            try:
                await self._on_round_complete(round_state, deps.submissions)
            except Exception as e:
                logger.warning(f"on_round_complete hook failed: {e}", exc_info=True)

        return round_state

    async def _should_continue_round(self, user_query: str, current_round: int) -> tuple[bool, str]:
        """Determine if should continue to next round (T023: 3-stage judgment)

        Args:
            user_query: Original user query/prompt
            current_round: Current round number

        Returns:
            Tuple of (should_continue, exit_reason)
        """
        # Stage (a): Check minimum rounds
        if current_round < self.task.min_rounds:
            # Update round_status with continuation decision
            if self.store is not None:
                await self.store.save_round_status(
                    execution_id=self.task.execution_id,
                    team_id=self.team_config.team_id,
                    team_name=self.team_config.team_name,
                    round_number=current_round,
                    should_continue=True,
                    reasoning=f"Below minimum rounds ({current_round} < {self.task.min_rounds})",
                    confidence_score=1.0,
                    round_started_at=self.round_history[-1].round_started_at.isoformat(),
                    round_ended_at=self.round_history[-1].round_ended_at.isoformat(),
                )
            return True, ""

        # Stage (b): LLM-based judgment
        # FR-013: RoundControllerがRoundPromptContextを作成してプロンプト整形
        judgment_context = RoundPromptContext(
            user_prompt=user_query,
            round_number=current_round,
            round_history=self.round_history,
            team_id=self.team_config.team_id,
            team_name=self.team_config.team_name,
            execution_id=self.task.execution_id,
            store=self.store,
        )

        # UserPromptBuilderでプロンプト整形
        formatted_prompt = await self.prompt_builder.build_judgment_prompt(judgment_context)

        # 整形済みプロンプトをJudgmentClientに渡す（FR-021）
        judgment = await self.judgment_client.judge_improvement_prospects(formatted_prompt)

        # Stage (c): Check maximum rounds (override LLM decision)
        if current_round >= self.task.max_rounds:
            judgment.should_continue = False

        # Update round_status with judgment
        if self.store is not None:
            await self.store.save_round_status(
                execution_id=self.task.execution_id,
                team_id=self.team_config.team_id,
                team_name=self.team_config.team_name,
                round_number=current_round,
                should_continue=judgment.should_continue,
                reasoning=judgment.reasoning,
                confidence_score=judgment.confidence_score,
                round_started_at=self.round_history[-1].round_started_at.isoformat(),
                round_ended_at=self.round_history[-1].round_ended_at.isoformat(),
            )

        # Update RoundState
        self.round_history[-1].improvement_judgment = judgment

        # Determine exit reason
        if not judgment.should_continue:
            if current_round >= self.task.max_rounds:
                return False, "max_rounds_reached"
            else:
                return False, "no_improvement_expected"

        return True, ""

    async def _finalize_and_return_best(self, exit_reason: str, span: Any | None) -> LeaderBoardEntry:
        """Finalize execution and return best LeaderBoardEntry (T027-T029)

        Args:
            exit_reason: Reason for termination
            span: Logfire span (if available)

        Returns:
            LeaderBoardEntry: Best submission entry
        """
        # T027: Find best round (highest score, latest round if tied)
        best_state = max(self.round_history, key=lambda s: (s.evaluation_score, s.round_number))

        # T028: Update leader_board with final_submission flag and exit_reason
        if self.store is not None:
            await self.store.save_to_leader_board(
                execution_id=self.task.execution_id,
                team_id=self.team_config.team_id,
                team_name=self.team_config.team_name,
                round_number=best_state.round_number,
                submission_content=best_state.submission_content,
                submission_format="md",
                score=best_state.evaluation_score,
                score_details=best_state.score_details,
                final_submission=True,
                exit_reason=exit_reason,
            )

        # T029: Create and return LeaderBoardEntry
        leader_board_entry = LeaderBoardEntry(
            execution_id=self.task.execution_id,
            team_id=self.team_config.team_id,
            team_name=self.team_config.team_name,
            round_number=best_state.round_number,
            submission_content=best_state.submission_content,
            submission_format="md",
            score=best_state.evaluation_score,
            score_details=best_state.score_details,
            final_submission=True,
            exit_reason=exit_reason,
            created_at=best_state.round_ended_at,
            updated_at=datetime.now(UTC),
        )

        # Logfire span attributes
        if span is not None and LOGFIRE_AVAILABLE:
            span.set_attribute("total_rounds", len(self.round_history))
            span.set_attribute("best_round", best_state.round_number)
            span.set_attribute("best_score", best_state.evaluation_score)
            span.set_attribute("exit_reason", exit_reason)

        # 進捗ファイル更新（完了）
        self._write_progress_file(best_state.round_number, status="completed")

        return leader_board_entry
