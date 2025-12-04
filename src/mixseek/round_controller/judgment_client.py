"""LLM-as-a-Judge improvement prospect judgment client

Feature: 037-mixseek-core-round-controller, 140-user-prompt-builder-evaluator-judgement
This module implements LLM-based judgment to determine if another round should be executed.

Responsibility: Agent呼び出しとsystem_interaction生成のみ
プロンプト整形はRoundControllerがUserPromptBuilderで行う（FR-021, FR-013準拠）
"""

import textwrap
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from mixseek.config.schema import JudgmentSettings
from mixseek.core.auth import create_authenticated_model
from mixseek.round_controller.exceptions import JudgmentAPIError
from mixseek.round_controller.models import ImprovementJudgment

DEFAULT_SYSTEM_INSTRUCTION = """
    あなたは複数ラウンドにわたるチームの提出物の改善を分析する専門的な判定者です。

    あなたのタスクは、以下の要素に基づいて、チームが次のラウンドに進むべきかを判定することです：
    1. 過去の提出物の品質トレンド
    2. 評価スコアの推移
    3. さらなる改善の可能性

    提出履歴を注意深く分析し、以下を提供してください：
    - should_continue: 真偽値の判定（継続する場合はTrue、停止する場合はFalse）
    - reasoning: あなたの判定の詳細な説明
    - confidence_score: あなたの確信度（0.0-1.0）

    以下の要素を考慮してください：
    - スコアが一貫して改善している場合は、継続を推奨
    - 提出物が収穫逓減を示している場合は、停止を推奨
    - 直近のスコアが低くても、数ラウンド先での改善が見込まれる場合は、継続を推奨
"""


class JudgmentClient:
    """LLM-as-a-Judge client for improvement prospect judgment

    This client uses Pydantic AI to determine if the team should continue
    to the next round based on formatted prompt from RoundController.

    Note:
        Prompt formatting is handled by RoundController using UserPromptBuilder.
        JudgmentClient only performs LLM calls with formatted prompts (FR-021).
    """

    def __init__(self, settings: JudgmentSettings) -> None:
        """Initialize judgment client

        Args:
            settings: Judgment設定（JudgmentSettings インスタンス）
        """
        self.settings = settings

    def _get_system_instruction(self) -> str:
        """Get system instruction (configurable or default).

        Returns:
            System instruction string
        """
        instruction = self.settings.system_instruction or DEFAULT_SYSTEM_INSTRUCTION
        return textwrap.dedent(instruction).strip()

    async def judge_improvement_prospects(self, formatted_prompt: str) -> ImprovementJudgment:
        """Judge if the team should continue to the next round

        This method uses Pydantic AI Agent for structured output and automatic retries.
        Prompt formatting is handled by RoundController using UserPromptBuilder (FR-021).

        Args:
            formatted_prompt: Pre-formatted user prompt (from RoundController)

        Returns:
            ImprovementJudgment: Judgment result

        Raises:
            JudgmentAPIError: If all retries fail
        """
        if not formatted_prompt or not formatted_prompt.strip():
            raise ValueError("formatted_prompt cannot be empty")

        # 認証済みモデル作成（DRY準拠、Article 10）
        authenticated_model = create_authenticated_model(self.settings.model)

        # ModelSettings作成（settings から取得、None値はスキップ）
        model_settings_dict: dict[str, Any] = {
            "temperature": self.settings.temperature,
            "timeout": self.settings.timeout_seconds,
        }
        if self.settings.max_tokens is not None:
            model_settings_dict["max_tokens"] = self.settings.max_tokens
        if self.settings.top_p is not None:
            model_settings_dict["top_p"] = self.settings.top_p
        if self.settings.stop_sequences is not None:
            model_settings_dict["stop"] = self.settings.stop_sequences
        if self.settings.seed is not None:
            model_settings_dict["seed"] = self.settings.seed
        model_settings = ModelSettings(**model_settings_dict)  # type: ignore[typeddict-item]

        # Agent作成（構造化出力とリトライ設定）
        agent = Agent(
            authenticated_model,
            output_type=ImprovementJudgment,  # 構造化出力を自動的に実現
            instructions=self._get_system_instruction(),  # システムプロンプト
            model_settings=model_settings,  # LLM設定
            retries=self.settings.max_retries,  # 自動リトライ
        )

        # 実行
        try:
            result = await agent.run(formatted_prompt)
            return result.output

        except Exception as e:
            # Extract provider name from model (e.g., "google-gla:gemini-2.5-flash" -> "google-gla")
            provider = self.settings.model.split(":")[0] if ":" in self.settings.model else self.settings.model
            raise JudgmentAPIError(
                f"Failed to judge improvement prospects after {self.settings.max_retries} retries: {str(e)}",
                provider=provider,
                retry_count=self.settings.max_retries,
            ) from e
