"""apply_reasoning_effort / apply_enable_thinking の単体テスト."""

import pytest
from pydantic_ai.settings import ModelSettings

from mixseek.core.reasoning import apply_enable_thinking, apply_reasoning_effort

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

    def test_openai_responses_prefix_also_supported(self) -> None:
        """/v1/responses 経由のモデルでも同じ openai_reasoning_effort キーを使う."""
        settings: ModelSettings = {}
        apply_reasoning_effort(settings, "openai-responses:gpt-5.4-nano", "low")
        assert settings.get("openai_reasoning_effort") == "low"  # type: ignore[typeddict-item]

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


class TestApplyEnableThinkingNoOp:
    """enable_thinking=None 時は何もしない."""

    def test_none_leaves_settings_unchanged(self) -> None:
        settings: ModelSettings = {"temperature": 0.5}
        result = apply_enable_thinking(settings, "qwen:qwen3.5-35b-a3b", None)
        assert result is settings
        assert result == {"temperature": 0.5}

    def test_none_unsupported_provider_does_not_raise(self) -> None:
        """qwen: 以外のプレフィックスでも enable_thinking=None なら ValueError を出さない."""
        settings: ModelSettings = {}
        result = apply_enable_thinking(settings, "openai:gpt-5", None)
        assert result == {}


class TestApplyEnableThinkingQwen:
    """qwen: prefix で extra_body.chat_template_kwargs.enable_thinking を注入."""

    @pytest.mark.parametrize("value", [True, False])
    def test_qwen_sets_chat_template_kwargs(self, value: bool) -> None:
        settings: ModelSettings = {}
        apply_enable_thinking(settings, "qwen:qwen3.5-35b-a3b", value)
        assert settings["extra_body"] == {
            "chat_template_kwargs": {"enable_thinking": value},
        }

    def test_qwen_preserves_existing_unrelated_extra_body_keys(self) -> None:
        settings: ModelSettings = {"extra_body": {"user": "alice"}}
        apply_enable_thinking(settings, "qwen:qwen3.5-35b-a3b", True)
        assert settings["extra_body"] == {
            "user": "alice",
            "chat_template_kwargs": {"enable_thinking": True},
        }

    def test_qwen_preserves_existing_chat_template_kwargs_other_keys(self) -> None:
        settings: ModelSettings = {
            "extra_body": {"chat_template_kwargs": {"some_other_kw": "x"}},
        }
        apply_enable_thinking(settings, "qwen:qwen3.5-35b-a3b", False)
        assert settings["extra_body"] == {
            "chat_template_kwargs": {"some_other_kw": "x", "enable_thinking": False},
        }

    def test_qwen_coexists_with_existing_reasoning_subkey(self) -> None:
        """既に extra_body.reasoning.effort が入っている状態でも破壊しない."""
        settings: ModelSettings = {
            "extra_body": {"reasoning": {"effort": "medium"}},
        }
        apply_enable_thinking(settings, "qwen:qwen3.5-35b-a3b", True)
        assert settings["extra_body"] == {
            "reasoning": {"effort": "medium"},
            "chat_template_kwargs": {"enable_thinking": True},
        }

    def test_qwen_preserves_other_settings(self) -> None:
        settings: ModelSettings = {"temperature": 0.2, "max_tokens": 100}
        apply_enable_thinking(settings, "qwen:qwen3.5-35b-a3b", True)
        assert settings["temperature"] == 0.2
        assert settings["max_tokens"] == 100
        assert settings["extra_body"] == {
            "chat_template_kwargs": {"enable_thinking": True},
        }


class TestApplyEnableThinkingUnsupportedProviders:
    """qwen: 以外のプレフィックスは ValueError（フォールバック禁止）."""

    @pytest.mark.parametrize(
        "model_id",
        [
            "openai:gpt-5",
            "openai-responses:gpt-5.4-nano",
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
        with pytest.raises(ValueError, match="enable_thinking is supported only for 'qwen:'"):
            apply_enable_thinking(settings, model_id, True)
