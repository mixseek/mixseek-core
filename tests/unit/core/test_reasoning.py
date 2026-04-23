"""apply_reasoning_effort の単体テスト."""

import pytest
from pydantic_ai.settings import ModelSettings

from mixseek.core.reasoning import apply_reasoning_effort

pytestmark = pytest.mark.unit


class TestApplyReasoningEffortNoOp:
    """effort=None 時は何もしない."""

    def test_none_effort_leaves_settings_unchanged(self) -> None:
        settings: ModelSettings = {"temperature": 0.5}
        result = apply_reasoning_effort(settings, "openai:gpt-5", None)
        assert result is settings
        assert result == {"temperature": 0.5}

    def test_none_effort_unknown_provider_does_not_raise(self) -> None:
        """未サポートのプロバイダでも effort=None なら ValueError を出さない."""
        settings: ModelSettings = {}
        result = apply_reasoning_effort(settings, "anthropic:claude-4-7", None)
        assert result == {}


class TestOpenAIProvider:
    """openai: prefix は openai_reasoning_effort キーを直接セット."""

    @pytest.mark.parametrize("effort", ["minimal", "low", "medium", "high"])
    def test_openai_sets_reasoning_effort_key(self, effort: str) -> None:
        settings: ModelSettings = {}
        apply_reasoning_effort(settings, "openai:gpt-5", effort)  # type: ignore[arg-type]
        assert settings.get("openai_reasoning_effort") == effort  # type: ignore[typeddict-item]

    def test_openai_preserves_existing_settings(self) -> None:
        settings: ModelSettings = {"temperature": 0.2, "max_tokens": 100}
        apply_reasoning_effort(settings, "openai:gpt-5", "high")
        assert settings["temperature"] == 0.2
        assert settings["max_tokens"] == 100
        assert settings.get("openai_reasoning_effort") == "high"  # type: ignore[typeddict-item]


class TestOpenRouterQwen:
    """qwen: prefix は OpenRouter 経由で extra_body.reasoning.effort を使う."""

    def test_qwen_sets_extra_body_reasoning_effort(self) -> None:
        settings: ModelSettings = {}
        apply_reasoning_effort(settings, "qwen:qwen3.5-35b-a3b", "medium")
        assert settings["extra_body"] == {"reasoning": {"effort": "medium"}}

    def test_qwen_preserves_existing_unrelated_extra_body_keys(self) -> None:
        settings: ModelSettings = {"extra_body": {"user": "alice"}}
        apply_reasoning_effort(settings, "qwen:qwen3.5-35b-a3b", "high")
        assert settings["extra_body"] == {
            "user": "alice",
            "reasoning": {"effort": "high"},
        }

    def test_qwen_preserves_existing_reasoning_keys(self) -> None:
        settings: ModelSettings = {
            "extra_body": {"reasoning": {"max_tokens": 2048}},
        }
        apply_reasoning_effort(settings, "qwen:qwen3.5-35b-a3b", "low")
        assert settings["extra_body"] == {
            "reasoning": {"max_tokens": 2048, "effort": "low"},
        }


class TestUnsupportedProviders:
    """未サポートのプロバイダは ValueError（フォールバック禁止）."""

    @pytest.mark.parametrize(
        "model_id",
        [
            "anthropic:claude-4-7",
            "google-gla:gemini-2.5-flash",
            "google-vertex:gemini-2.5-flash",
            "grok:grok-2-1212",
            "grok-responses:grok-4-fast",
            "unknown-provider:some-model",
        ],
    )
    def test_unsupported_provider_raises(self, model_id: str) -> None:
        settings: ModelSettings = {}
        with pytest.raises(ValueError, match="reasoning_effort is not supported"):
            apply_reasoning_effort(settings, model_id, "high")
