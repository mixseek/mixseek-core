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
