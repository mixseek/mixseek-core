"""pydantic-ai ModelSettings 構築ユーティリティ。

TOML 設定（model_settings / google_model_settings の pass-through dict）と
個別フィールド（temperature, max_tokens 等）を合成して pydantic-ai 互換の
ModelSettings TypedDict を構築する。

LLM Provider の進化に追従する目的で TOML 値は検証せずそのまま渡す方針。
pydantic-ai の TypedDict 設計と同じ思想（実行時検証なし、エラーは Provider API
呼び出し時に表面化）。
"""

import logging
from typing import Any, cast

from pydantic_ai.settings import ModelSettings

from mixseek.core.auth import AuthenticationError, AuthProvider, detect_auth_provider

logger = logging.getLogger(__name__)

_GOOGLE_PROVIDERS = {AuthProvider.GOOGLE_AI, AuthProvider.VERTEX_AI}


def build_model_settings(
    *,
    model_id: str,
    model_settings: dict[str, Any] | None = None,
    google_model_settings: dict[str, Any] | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    stop_sequences: list[str] | None = None,
    top_p: float | None = None,
    seed: int | None = None,
    timeout_seconds: int | float | None = None,
) -> ModelSettings:
    """TOML pass-through dict と個別フィールドをマージして ModelSettings を構築。

    合成順序（後勝ち）:
        1. model_settings (pydantic-ai ModelSettings TypedDict pass-through)
        2. google_model_settings (Google モデルのときのみ重ねがけ)
        3. 個別フィールド (temperature, max_tokens, stop_sequences, top_p, seed, timeout_seconds)

    Google 以外のモデルに google_model_settings が指定されていた場合は警告を出力して無視する
    （実行は継続）。

    Args:
        model_id: モデル識別子 (例: "google-gla:gemini-2.5-pro", "anthropic:claude-...")。
            Provider 判定に使用する。
        model_settings: pydantic-ai の ModelSettings TypedDict に渡す dict。
        google_model_settings: pydantic-ai の GoogleModelSettings TypedDict に渡す dict。
            Google モデルのときのみ適用される。
        temperature: 個別 temperature 設定（最優先）。
        max_tokens: 個別 max_tokens 設定（最優先）。
        stop_sequences: 個別 stop_sequences 設定（最優先）。
        top_p: 個別 top_p 設定（最優先）。
        seed: 個別 seed 設定（最優先）。
        timeout_seconds: 個別 timeout 設定（秒、最優先）。

    Returns:
        ModelSettings: マージ済み TypedDict。空 dict も valid な ModelSettings。

    Note:
        戻り値型は ModelSettings だが、Google モデルのときは GoogleModelSettings の
        フィールド (google_thinking_config 等) を含むことがある。両者とも TypedDict
        （実体は dict）なので pydantic-ai 側で問題なく受理される。
    """
    result: dict[str, Any] = {}

    if model_settings:
        result.update(model_settings)

    if google_model_settings:
        provider: AuthProvider | None
        try:
            provider = detect_auth_provider(model_id)
        except AuthenticationError:
            # 未知のプレフィックス: provider 判定不能扱いで無視
            provider = None

        if provider in _GOOGLE_PROVIDERS:
            result.update(google_model_settings)
        else:
            logger.warning(
                "google_model_settings is set but model is not a Google model; ignoring",
                extra={
                    "model_id": model_id,
                    "provider": provider.value if provider is not None else "unknown",
                },
            )

    # 個別フィールド（最優先・後勝ち）
    if temperature is not None:
        result["temperature"] = temperature
    if max_tokens is not None:
        result["max_tokens"] = max_tokens
    if stop_sequences is not None:
        result["stop_sequences"] = stop_sequences
    if top_p is not None:
        result["top_p"] = top_p
    if seed is not None:
        result["seed"] = seed
    if timeout_seconds is not None:
        result["timeout"] = float(timeout_seconds)

    # TypedDict は実行時 dict なので変換コストはないが、型チェッカに対しては
    # 明示的に ModelSettings 型へキャストする（typing.cast で意図を表現）。
    return cast(ModelSettings, result)
