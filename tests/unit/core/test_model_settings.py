"""build_model_settings の単体テスト."""

import pytest

from mixseek.agents.leader.config import LeaderAgentConfig, TeamMemberAgentConfig
from mixseek.core.model_settings import build_model_settings
from mixseek.models.member_agent import MemberAgentConfig

pytestmark = pytest.mark.unit


class TestBuildModelSettingsBase:
    """既存パラメータがそのまま反映される."""

    def test_empty_config_returns_empty_settings(self) -> None:
        config = MemberAgentConfig(name="a", type="plain", model="openai:gpt-4o")
        settings = build_model_settings(config)
        assert settings == {}

    def test_all_llm_params_reflected(self) -> None:
        config = MemberAgentConfig(
            name="a",
            type="plain",
            model="openai:gpt-4o",
            temperature=0.5,
            max_tokens=1024,
            stop_sequences=["END"],
            top_p=0.9,
            seed=42,
            timeout_seconds=30,
        )
        settings = build_model_settings(config)
        assert settings["temperature"] == 0.5
        assert settings["max_tokens"] == 1024
        assert settings["stop_sequences"] == ["END"]
        assert settings["top_p"] == 0.9
        assert settings["seed"] == 42
        assert settings["timeout"] == 30.0


class TestReasoningEffortDispatch:
    """build_model_settings 経由でも reasoning_effort がプロバイダ別に注入される."""

    def test_openai_reasoning_effort_via_build(self) -> None:
        config = MemberAgentConfig(name="a", type="plain", model="openai:gpt-5", reasoning_effort="high")
        settings = build_model_settings(config)
        assert settings.get("openai_reasoning_effort") == "high"  # type: ignore[typeddict-item]

    def test_qwen_reasoning_effort_via_build(self) -> None:
        config = MemberAgentConfig(
            name="a",
            type="plain",
            model="qwen:qwen3.5-35b-a3b",
            reasoning_effort="medium",
        )
        settings = build_model_settings(config)
        assert settings["extra_body"] == {"reasoning": {"effort": "medium"}}

    def test_leader_config_also_works(self) -> None:
        leader = LeaderAgentConfig(model="openai:gpt-5", reasoning_effort="low")
        settings = build_model_settings(leader)
        assert settings.get("openai_reasoning_effort") == "low"  # type: ignore[typeddict-item]

    def test_team_member_config_also_works(self) -> None:
        member = TeamMemberAgentConfig(
            agent_name="a",
            agent_type="plain",
            tool_description="desc",
            model="qwen:qwen3.5-35b-a3b",
            reasoning_effort="high",
        )
        settings = build_model_settings(member)
        assert settings["extra_body"] == {"reasoning": {"effort": "high"}}

    def test_unsupported_provider_raises(self) -> None:
        config = MemberAgentConfig(
            name="a",
            type="plain",
            model="anthropic:claude-3-5-sonnet-20241022",
            reasoning_effort="high",
        )
        with pytest.raises(ValueError, match="reasoning_effort is not supported"):
            build_model_settings(config)


class TestEnableThinkingDispatch:
    """build_model_settings 経由で enable_thinking が qwen: のみ注入される."""

    @pytest.mark.parametrize("value", [True, False])
    def test_qwen_enable_thinking_via_build(self, value: bool) -> None:
        config = MemberAgentConfig(
            name="a",
            type="plain",
            model="qwen:qwen3.5-35b-a3b",
            enable_thinking=value,
        )
        settings = build_model_settings(config)
        assert settings["extra_body"] == {
            "chat_template_kwargs": {"enable_thinking": value},
        }

    def test_qwen_reasoning_effort_and_enable_thinking_coexist(self) -> None:
        """reasoning_effort と enable_thinking が同時に注入されても互いを破壊しない."""
        config = MemberAgentConfig(
            name="a",
            type="plain",
            model="qwen:qwen3.5-35b-a3b",
            reasoning_effort="medium",
            enable_thinking=False,
        )
        settings = build_model_settings(config)
        assert settings["extra_body"] == {
            "reasoning": {"effort": "medium"},
            "chat_template_kwargs": {"enable_thinking": False},
        }

    def test_both_none_does_not_create_extra_body(self) -> None:
        config = MemberAgentConfig(
            name="a",
            type="plain",
            model="qwen:qwen3.5-35b-a3b",
        )
        settings = build_model_settings(config)
        assert "extra_body" not in settings

    def test_leader_config_also_works(self) -> None:
        leader = LeaderAgentConfig(model="qwen:qwen3.5-35b-a3b", enable_thinking=True)
        settings = build_model_settings(leader)
        assert settings["extra_body"] == {
            "chat_template_kwargs": {"enable_thinking": True},
        }

    def test_team_member_config_also_works(self) -> None:
        member = TeamMemberAgentConfig(
            agent_name="a",
            agent_type="plain",
            tool_description="desc",
            model="qwen:qwen3.5-35b-a3b",
            enable_thinking=False,
        )
        settings = build_model_settings(member)
        assert settings["extra_body"] == {
            "chat_template_kwargs": {"enable_thinking": False},
        }

    def test_unsupported_provider_raises(self) -> None:
        config = MemberAgentConfig(
            name="a",
            type="plain",
            model="openai:gpt-5",
            enable_thinking=True,
        )
        with pytest.raises(ValueError, match="enable_thinking is supported only for 'qwen:'"):
            build_model_settings(config)
