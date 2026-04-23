"""Leader/Member Agent 共通の ModelSettings 構築ヘルパ。

Leader Agent (agents/leader/agent.py) と Member Agent (agents/member/base.py) で
重複していた ModelSettings 構築ロジックを一元化する。
"""

from typing import Protocol

from pydantic_ai.settings import ModelSettings

from mixseek.core.reasoning import ReasoningEffort, apply_reasoning_effort


class _HasLLMParams(Protocol):
    """ModelSettings 構築に必要な属性を持つ config の構造的型。

    MemberAgentConfig / LeaderAgentConfig / TeamMemberAgentConfig が満たす。
    """

    model: str
    temperature: float | None
    max_tokens: int | None
    stop_sequences: list[str] | None
    top_p: float | None
    seed: int | None
    timeout_seconds: int | None
    reasoning_effort: ReasoningEffort | None


def build_model_settings(config: _HasLLMParams) -> ModelSettings:
    """config から Pydantic AI の ModelSettings を構築する。

    None の値は含めず、reasoning_effort はプロバイダ別にディスパッチして注入する。

    Args:
        config: LLM パラメータを持つ agent config

    Returns:
        ModelSettings TypedDict（該当値のみ含む）
    """
    settings: ModelSettings = {}

    if config.temperature is not None:
        settings["temperature"] = config.temperature
    if config.max_tokens is not None:
        settings["max_tokens"] = config.max_tokens
    if config.stop_sequences is not None:
        settings["stop_sequences"] = config.stop_sequences
    if config.top_p is not None:
        settings["top_p"] = config.top_p
    if config.seed is not None:
        settings["seed"] = config.seed
    if config.timeout_seconds is not None:
        settings["timeout"] = float(config.timeout_seconds)

    return apply_reasoning_effort(settings, config.model, config.reasoning_effort)
