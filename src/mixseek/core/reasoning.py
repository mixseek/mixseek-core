"""reasoning_effort / enable_thinking のプロバイダ別ディスパッチ。

モデル prefix に応じて Pydantic AI の ModelSettings へ reasoning / thinking 指定を注入する。

- reasoning_effort
  - openai:  → OpenAIChatModelSettings の openai_reasoning_effort（固有キー）
  - qwen:    → ModelSettings.extra_body["reasoning"]["effort"]（OpenRouter 経由）
  - その他   → ValueError（フォールバック禁止）
- enable_thinking (Qwen3 系の thinking モード制御)
  - qwen:    → ModelSettings.extra_body["chat_template_kwargs"]["enable_thinking"]
  - その他   → ValueError（フォールバック禁止）
"""

from typing import Literal, cast

from pydantic_ai.settings import ModelSettings

ReasoningEffort = Literal["minimal", "low", "medium", "high"]

_OPENAI_PREFIXES: tuple[str, ...] = ("openai:", "openai-responses:")
# mixseek では qwen: のみが OpenRouter（OpenAI 互換エンドポイント）経路
_OPENROUTER_PREFIXES: tuple[str, ...] = ("qwen:",)


def apply_reasoning_effort(
    settings: ModelSettings,
    model_id: str,
    effort: ReasoningEffort | None,
) -> ModelSettings:
    """reasoning_effort を model prefix に応じて ModelSettings に注入する。

    Args:
        settings: 対象の ModelSettings（破壊的に更新）
        model_id: モデル識別子（例: "openai:gpt-5", "qwen:qwen3.5-35b-a3b"）
        effort: reasoning 強度。None の場合は何もしない

    Returns:
        同一の settings オブジェクト（チェーン用）

    Raises:
        ValueError: 未サポートのプロバイダ prefix が指定された場合
    """
    if effort is None:
        return settings

    if model_id.startswith(_OPENAI_PREFIXES):
        # ModelSettings は TypedDict（実体は dict）。OpenAIChatModelSettings 固有キー
        # openai_reasoning_effort は ModelSettings 側に未定義なため、dict にキャストして追加する。
        # 値は ReasoningEffort 文字列のみのため Any ではなく object で十分。
        cast(dict[str, object], settings)["openai_reasoning_effort"] = effort
        return settings

    if model_id.startswith(_OPENROUTER_PREFIXES):
        # OpenRouter は extra_body.reasoning.effort を受け取る
        existing_extra = settings.get("extra_body")
        extra_body: dict[str, object] = dict(existing_extra) if isinstance(existing_extra, dict) else {}
        reasoning_raw = extra_body.get("reasoning")
        reasoning: dict[str, object] = dict(reasoning_raw) if isinstance(reasoning_raw, dict) else {}
        reasoning["effort"] = effort
        extra_body["reasoning"] = reasoning
        settings["extra_body"] = extra_body
        return settings

    raise ValueError(
        f"reasoning_effort is not supported for model '{model_id}'. "
        f"Supported model prefixes: {_OPENAI_PREFIXES + _OPENROUTER_PREFIXES}."
    )


def apply_enable_thinking(
    settings: ModelSettings,
    model_id: str,
    enable_thinking: bool | None,
) -> ModelSettings:
    """enable_thinking を qwen: プレフィックス時のみ ModelSettings に注入する。

    Qwen3 系モデルの thinking モード (default) と non-thinking (instruct) を切り替える。
    OpenAI 互換エンドポイント (OpenRouter 等) では
    extra_body.chat_template_kwargs.enable_thinking が正規パス。

    Args:
        settings: 対象の ModelSettings（破壊的に更新）
        model_id: モデル識別子（例: "qwen:qwen3.5-35b-a3b"）
        enable_thinking: True で thinking on、False で off。None の場合は何もしない

    Returns:
        同一の settings オブジェクト（チェーン用）

    Raises:
        ValueError: qwen: 以外のプレフィックスで enable_thinking が指定された場合
    """
    if enable_thinking is None:
        return settings

    if not model_id.startswith(_OPENROUTER_PREFIXES):
        raise ValueError(
            f"enable_thinking is supported only for 'qwen:' models, got '{model_id}'. "
            f"Supported model prefixes: {_OPENROUTER_PREFIXES}."
        )

    existing_extra = settings.get("extra_body")
    extra_body: dict[str, object] = dict(existing_extra) if isinstance(existing_extra, dict) else {}
    chat_template_kwargs_raw = extra_body.get("chat_template_kwargs")
    chat_template_kwargs: dict[str, object] = (
        dict(chat_template_kwargs_raw) if isinstance(chat_template_kwargs_raw, dict) else {}
    )
    chat_template_kwargs["enable_thinking"] = enable_thinking
    extra_body["chat_template_kwargs"] = chat_template_kwargs
    settings["extra_body"] = extra_body
    return settings
