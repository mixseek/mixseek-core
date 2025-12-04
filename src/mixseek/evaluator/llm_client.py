"""Pydantic AI Agentを使用したLLMクライアントラッパー。"""

import logging

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from mixseek.core.auth import create_authenticated_model
from mixseek.evaluator.exceptions import EvaluatorAPIError

logger = logging.getLogger(__name__)


async def evaluate_with_llm(
    instruction: str,
    user_prompt: str,
    model: str,
    response_model: type[BaseModel],
    temperature: float = 0.0,
    max_tokens: int | None = None,
    max_retries: int = 3,
    timeout_seconds: int | None = None,
    stop_sequences: list[str] | None = None,
    top_p: float | None = None,
    seed: int | None = None,
) -> BaseModel:
    """構造化された出力を持つLLM-as-a-Judgeを使用して評価します。

    この関数はPydantic AI Agentを使用して、
    構造化された出力、自動リトライ、包括的なエラー処理を持つ
    シンプルな評価インターフェースを提供します。

    Args:
        instruction: 評価者の役割と指示を定義するシステムプロンプト
        user_prompt: 評価するクエリとSubmissionを含むユーザープロンプト
        model: LLMモデル識別子（フォーマット："provider:model-name"）
        temperature: LLM temperature設定（FR-019）
        max_tokens: LLM max_tokens設定、Noneの場合は制限なし（FR-019）
        response_model: 構造化された出力検証のためのPydanticモデルクラス
        max_retries: 最大リトライ試行回数（デフォルト：3）
        timeout_seconds: HTTPタイムアウト（秒）。Noneの場合はデフォルトタイムアウト
        stop_sequences: 生成を停止するシーケンスのリスト。Noneの場合は使用しない
        top_p: Top-pサンプリングパラメータ（0.0-1.0）。Noneの場合はモデルデフォルト
        seed: ランダムシード。Noneの場合はランダム（OpenAI/Geminiでサポート）

    Returns:
        検証された評価結果を持つresponse_modelのインスタンス

    Raises:
        EvaluatorAPIError: すべてのリトライ後にLLM API呼び出しが失敗した場合
        ValueError: モデルフォーマットが無効またはAPIキーが欠落している場合

    Example:
        ```python
        from pydantic import BaseModel, Field

        class ClarityCoherenceScore(BaseModel):
            score: float = Field(ge=0, le=100)
            comment: str

        result = await evaluate_with_llm(
            instruction="You are an expert evaluator...",
            user_prompt="Evaluate this response...",
            model="anthropic:claude-sonnet-4-5-20250929",
            temperature=0.0,
            max_tokens=2000,
            response_model=ClarityCoherenceScore,
            max_retries=3
        )
        print(f"Score: {result.score}")
        ```
    """
    # モデルフォーマットを検証
    if ":" not in model or not model.strip():
        raise ValueError(
            f"Invalid model format: '{model}'. "
            "Expected format: 'provider:model-name' "
            "(e.g., 'anthropic:claude-sonnet-4-5-20250929')"
        )

    provider, model_name = model.split(":", 1)

    # プロバイダーとモデル名が両方とも空でないことを確認
    if not provider.strip() or not model_name.strip():
        raise ValueError(
            f"Invalid model format: '{model}'. "
            "Both provider and model name must be non-empty. "
            "Expected format: 'provider:model-name' "
            "(e.g., 'anthropic:claude-sonnet-4-5-20250929')"
        )

    # 認証済みモデル作成（DRY準拠、Article 10）
    try:
        authenticated_model = create_authenticated_model(model)
    except Exception as e:
        raise EvaluatorAPIError(
            f"Failed to create authenticated model: {str(e)}",
            provider=provider,
            metric_name=None,
            retry_count=0,
        ) from e

    # ModelSettings作成（FR-019）
    model_settings = ModelSettings(temperature=temperature)
    if max_tokens is not None:
        model_settings["max_tokens"] = max_tokens
    if timeout_seconds is not None:
        model_settings["timeout"] = timeout_seconds
    if stop_sequences is not None:
        model_settings["stop_sequences"] = stop_sequences
    if top_p is not None:
        model_settings["top_p"] = top_p
    if seed is not None:
        model_settings["seed"] = seed

    # Agent作成（構造化出力とリトライ設定）
    agent = Agent(
        authenticated_model,
        output_type=response_model,  # 構造化出力を自動的に実現
        instructions=instruction,  # システムプロンプト
        model_settings=model_settings,  # temperature, max_tokens
        retries=max_retries,  # 自動リトライ
    )

    # 実行（非同期）
    try:
        result = await agent.run(user_prompt)
        return result.output

    except Exception as e:
        raise EvaluatorAPIError(
            f"Failed to evaluate after retries: {str(e)}",
            provider=provider,
            metric_name=None,
            retry_count=max_retries,
        ) from e
