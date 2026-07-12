"""Unit tests for build_model_settings utility.

build_model_settings は TOML pass-through 設定 (model_settings / google_model_settings) と
個別フィールド (temperature 等) を合成して pydantic-ai 互換の ModelSettings dict を構築する。

検証ポイント:
- 空入力で空 dict を返す
- 個別フィールドが model_settings を上書きする（後勝ち）
- Google モデルでは google_model_settings がマージされる
- 非 Google モデルで google_model_settings が指定された場合は警告ログ + 無視
- 未知のモデル ID（プレフィックスが不明）でも google_model_settings は無視
"""

from typing import Any, cast
from unittest.mock import patch

from mixseek.core.model_settings import build_model_settings


class TestBuildModelSettingsEmpty:
    """空入力時の挙動。"""

    def test_no_inputs_returns_empty(self) -> None:
        result = build_model_settings(model_id="google-gla:gemini-flash-latest")
        assert result == {}

    def test_only_none_inputs_returns_empty(self) -> None:
        result = build_model_settings(
            model_id="anthropic:claude-sonnet-4-5",
            model_settings=None,
            google_model_settings=None,
            temperature=None,
            max_tokens=None,
            stop_sequences=None,
            top_p=None,
            seed=None,
            timeout_seconds=None,
        )
        assert result == {}


class TestIndividualFields:
    """個別フィールドのみのケース。"""

    def test_all_individual_fields_set(self) -> None:
        result = build_model_settings(
            model_id="anthropic:claude-sonnet-4-5",
            temperature=0.7,
            max_tokens=1024,
            stop_sequences=["END"],
            top_p=0.9,
            seed=42,
            timeout_seconds=60,
        )
        assert result == {
            "temperature": 0.7,
            "max_tokens": 1024,
            "stop_sequences": ["END"],
            "top_p": 0.9,
            "seed": 42,
            "timeout": 60.0,
        }

    def test_timeout_seconds_converted_to_float(self) -> None:
        result = build_model_settings(model_id="openai:gpt-4o", timeout_seconds=30)
        assert result["timeout"] == 30.0
        assert isinstance(result["timeout"], float)


class TestModelSettingsPassThrough:
    """model_settings の pass-through 動作。"""

    def test_model_settings_keys_are_passed_through_verbatim(self) -> None:
        custom = {"parallel_tool_calls": True, "extra_headers": {"x-trace": "abc"}}
        result = build_model_settings(model_id="openai:gpt-4o", model_settings=custom)
        assert result == custom

    def test_model_settings_does_not_mutate_input(self) -> None:
        custom = {"temperature": 0.5}
        build_model_settings(model_id="openai:gpt-4o", model_settings=custom, temperature=0.0)
        assert custom == {"temperature": 0.5}, "入力 dict は破壊されてはならない"


class TestMergeOrder:
    """合成順序（後勝ち）の検証。"""

    def test_individual_field_overrides_model_settings(self) -> None:
        result = build_model_settings(
            model_id="anthropic:claude-sonnet-4-5",
            model_settings={"temperature": 0.5, "max_tokens": 1000},
            temperature=0.0,
        )
        assert result["temperature"] == 0.0, "個別フィールドが model_settings を上書きすべき"
        assert result["max_tokens"] == 1000, "個別フィールドで指定されていない値は model_settings から残る"

    def test_google_model_settings_overrides_model_settings_on_google(self) -> None:
        result = build_model_settings(
            model_id="google-gla:gemini-flash-latest",
            model_settings={"temperature": 0.5},
            google_model_settings={"temperature": 0.3},
        )
        # google_model_settings は Google モデルのとき model_settings を上書きする
        assert result["temperature"] == 0.3

    def test_individual_field_overrides_google_model_settings(self) -> None:
        result = build_model_settings(
            model_id="google-gla:gemini-flash-latest",
            model_settings={"temperature": 0.5},
            google_model_settings={"temperature": 0.3},
            temperature=0.0,
        )
        assert result["temperature"] == 0.0, "個別フィールドは最優先"


class TestGoogleModelSettings:
    """google_model_settings の Provider 判定。"""

    def test_google_gla_applies_google_settings(self) -> None:
        result = build_model_settings(
            model_id="google-gla:gemini-flash-latest",
            google_model_settings={"google_thinking_config": {"thinking_level": "HIGH"}},
        )
        # google_thinking_config は GoogleModelSettings 固有キーのため、
        # 戻り値型 ModelSettings には含まれない。dict として参照する。
        assert cast(dict[str, Any], result)["google_thinking_config"] == {"thinking_level": "HIGH"}

    def test_google_vertex_applies_google_settings(self) -> None:
        result = build_model_settings(
            model_id="google-vertex:gemini-flash-latest",
            google_model_settings={"google_thinking_config": {"include_thoughts": True}},
        )
        assert cast(dict[str, Any], result)["google_thinking_config"] == {"include_thoughts": True}

    def test_non_google_model_warns_and_ignores(self) -> None:
        with patch("mixseek.core.model_settings.logger") as mock_logger:
            result = build_model_settings(
                model_id="anthropic:claude-sonnet-4-5",
                google_model_settings={"google_thinking_config": {"thinking_level": "HIGH"}},
            )
        assert result == {}, "非 Google モデルでは google_model_settings は無視される"
        mock_logger.warning.assert_called_once()
        message = mock_logger.warning.call_args[0][0]
        assert "google_model_settings is set but model is not a Google model" in message

    def test_openai_model_ignores_google_settings(self) -> None:
        with patch("mixseek.core.model_settings.logger") as mock_logger:
            result = build_model_settings(
                model_id="openai:gpt-4o",
                google_model_settings={"google_thinking_config": {}},
            )
        assert result == {}
        mock_logger.warning.assert_called_once()

    def test_unknown_provider_ignores_google_settings(self) -> None:
        """未知のプレフィックスでも警告のうえ無視（実行継続）。"""
        with patch("mixseek.core.model_settings.logger") as mock_logger:
            result = build_model_settings(
                model_id="unknown-provider:some-model",
                google_model_settings={"google_thinking_config": {}},
            )
        assert result == {}
        mock_logger.warning.assert_called_once()


class TestCombinedScenarios:
    """実利用シナリオ。"""

    def test_thinking_on_google_with_individual_fields(self) -> None:
        """Google モデルで Thinking を有効化しつつ個別 temperature/max_tokens を指定。"""
        result = build_model_settings(
            model_id="google-gla:gemini-flash-latest",
            model_settings={"parallel_tool_calls": True},
            google_model_settings={
                "google_thinking_config": {"thinking_level": "HIGH", "include_thoughts": True},
            },
            temperature=0.0,
            max_tokens=2048,
        )
        as_dict = cast(dict[str, Any], result)
        assert as_dict["parallel_tool_calls"] is True
        assert as_dict["google_thinking_config"] == {"thinking_level": "HIGH", "include_thoughts": True}
        assert result["temperature"] == 0.0
        assert result["max_tokens"] == 2048

    def test_model_settings_only_on_non_google(self) -> None:
        """Anthropic モデルで model_settings + 個別フィールド。"""
        result = build_model_settings(
            model_id="anthropic:claude-sonnet-4-5",
            model_settings={"extra_headers": {"anthropic-beta": "interleaved-thinking-2025-05-14"}},
            temperature=0.5,
            max_tokens=4096,
        )
        assert result["extra_headers"] == {"anthropic-beta": "interleaved-thinking-2025-05-14"}
        assert result["temperature"] == 0.5
        assert result["max_tokens"] == 4096
