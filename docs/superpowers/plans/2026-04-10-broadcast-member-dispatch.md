# Broadcast Member Dispatch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `broadcast` member dispatch mode that forces all member agents to execute in parallel, then aggregates results via the Leader Agent LLM.

**Architecture:** A new `member_dispatch` field (`"selective"` | `"broadcast"`) on `TeamConfig` / `TeamSettings` controls behavior. In `_execute_single_round`, when `broadcast` is set, all member agents run via `asyncio.gather`, then a Tool-less Leader Agent synthesizes the results. All downstream processing (Evaluator, Judgment, DB) is shared with the existing `selective` path.

**Tech Stack:** Python 3.13, Pydantic v2, Pydantic AI, asyncio, pytest + pytest-asyncio

**Design Spec:** `docs/superpowers/specs/2026-04-10-broadcast-member-dispatch-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/mixseek/config/schema.py` | Modify (line ~1110) | Add `member_dispatch` field to `TeamSettings` |
| `src/mixseek/config/sources/team_toml_source.py` | Modify (line ~114) | Map TOML field to `TeamSettings` dict |
| `src/mixseek/agents/leader/config.py` | Modify (lines ~107, ~225-230) | Add `member_dispatch` field to `TeamConfig` + update `team_settings_to_team_config` |
| `src/mixseek/round_controller/controller.py` | Modify (lines ~287-314) | Add dispatch branch + `_execute_broadcast`, `_run_single_member`, `_aggregate_with_leader`, `_build_aggregation_prompt` |
| `tests/fixtures/team_broadcast.toml` | Create | Test fixture for broadcast mode |
| `tests/unit/config/test_member_dispatch.py` | Create | Config validation tests |
| `tests/unit/round_controller/test_broadcast.py` | Create | Broadcast execution tests |

---

## Task 1: Add `member_dispatch` field to config schema

**Files:**
- Modify: `src/mixseek/config/schema.py:1110-1111`
- Modify: `src/mixseek/config/sources/team_toml_source.py:111-117`
- Modify: `src/mixseek/agents/leader/config.py:102-111`
- Modify: `src/mixseek/agents/leader/config.py:224-231`
- Create: `tests/fixtures/team_broadcast.toml`
- Create: `tests/unit/config/test_member_dispatch.py`

- [ ] **Step 1: Write failing tests for config validation**

Create `tests/unit/config/test_member_dispatch.py`:

```python
"""Unit tests for member_dispatch field in TeamSettings and TeamConfig."""

from pathlib import Path
from typing import Literal

import pytest
from pydantic import ValidationError

from mixseek.agents.leader.config import TeamConfig, team_settings_to_team_config
from mixseek.config.schema import TeamSettings


class TestMemberDispatchField:
    """Tests for member_dispatch field on TeamSettings."""

    def test_default_value_is_selective(self) -> None:
        """member_dispatch未指定時はselectiveがデフォルト."""
        settings = TeamSettings(
            team_id="test-team",
            team_name="Test Team",
            leader={"model": "google-gla:gemini-2.5-flash-lite"},
        )
        assert settings.member_dispatch == "selective"

    def test_broadcast_value_accepted(self) -> None:
        """member_dispatch=broadcastが受け付けられる."""
        settings = TeamSettings(
            team_id="test-team",
            team_name="Test Team",
            member_dispatch="broadcast",
            leader={"model": "google-gla:gemini-2.5-flash-lite"},
        )
        assert settings.member_dispatch == "broadcast"

    def test_invalid_value_rejected(self) -> None:
        """無効なmember_dispatch値はValidationErrorになる."""
        with pytest.raises(ValidationError, match="member_dispatch"):
            TeamSettings(
                team_id="test-team",
                team_name="Test Team",
                member_dispatch="invalid",  # type: ignore[arg-type]
                leader={"model": "google-gla:gemini-2.5-flash-lite"},
            )


class TestMemberDispatchTeamConfig:
    """Tests for member_dispatch on TeamConfig."""

    def test_default_value_is_selective(self) -> None:
        """TeamConfigのデフォルトもselective."""
        config = TeamConfig(
            team_id="test-team",
            team_name="Test Team",
        )
        assert config.member_dispatch == "selective"

    def test_broadcast_value_accepted(self) -> None:
        """TeamConfigでbroadcastが受け付けられる."""
        config = TeamConfig(
            team_id="test-team",
            team_name="Test Team",
            member_dispatch="broadcast",
        )
        assert config.member_dispatch == "broadcast"


class TestMemberDispatchConversion:
    """Tests for team_settings_to_team_config conversion."""

    def test_selective_converted(self) -> None:
        """selectiveがTeamConfigに正しく変換される."""
        settings = TeamSettings(
            team_id="test-team",
            team_name="Test Team",
            member_dispatch="selective",
            leader={"model": "google-gla:gemini-2.5-flash-lite"},
        )
        config = team_settings_to_team_config(settings)
        assert config.member_dispatch == "selective"

    def test_broadcast_converted(self) -> None:
        """broadcastがTeamConfigに正しく変換される."""
        settings = TeamSettings(
            team_id="test-team",
            team_name="Test Team",
            member_dispatch="broadcast",
            leader={"model": "google-gla:gemini-2.5-flash-lite"},
        )
        config = team_settings_to_team_config(settings)
        assert config.member_dispatch == "broadcast"

    def test_default_preserved_when_not_specified(self) -> None:
        """未指定時のデフォルトが変換後も保持される."""
        settings = TeamSettings(
            team_id="test-team",
            team_name="Test Team",
            leader={"model": "google-gla:gemini-2.5-flash-lite"},
        )
        config = team_settings_to_team_config(settings)
        assert config.member_dispatch == "selective"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/config/test_member_dispatch.py -v`
Expected: FAIL — `member_dispatch` attribute not found on `TeamSettings` / `TeamConfig`

- [ ] **Step 3: Add `member_dispatch` field to `TeamSettings`**

In `src/mixseek/config/schema.py`, after line 1110 (`max_concurrent_members` field closing), add:

```python
    member_dispatch: Literal["selective", "broadcast"] = Field(
        default="selective",
        description="メンバーエージェント呼び出し方式。selective: LLMが自律的にAgent選択、broadcast: 全Agentを強制実行後にLLMで集約",
    )
```

- [ ] **Step 4: Add TOML mapping in `team_toml_source.py`**

In `src/mixseek/config/sources/team_toml_source.py`, in the `self.toml_data` dict (line ~111-117), add `member_dispatch` after `max_concurrent_members`:

```python
        self.toml_data = {
            "team_id": team_data.get("team_id"),
            "team_name": team_data.get("team_name"),
            "max_concurrent_members": team_data.get("max_concurrent_members", 15),
            "member_dispatch": team_data.get("member_dispatch", "selective"),
            "leader": team_data.get("leader", {}),
            "members": resolved_members,
        }
```

- [ ] **Step 5: Add `member_dispatch` field to `TeamConfig`**

In `src/mixseek/agents/leader/config.py`, add to `TeamConfig` class (after line 107):

```python
    member_dispatch: Literal["selective", "broadcast"] = Field(
        default="selective", description="メンバーエージェント呼び出し方式"
    )
```

Also add the `Literal` import at the top of the file. Change:

```python
from typing import Any
```

to:

```python
from typing import Any, Literal
```

- [ ] **Step 6: Update `team_settings_to_team_config` conversion**

In `src/mixseek/agents/leader/config.py`, update the `TeamConfig` construction in `team_settings_to_team_config` (line ~225-230) to include `member_dispatch`:

```python
    return TeamConfig(
        team_id=team_settings.team_id,
        team_name=team_settings.team_name,
        max_concurrent_members=team_settings.max_concurrent_members,
        member_dispatch=team_settings.member_dispatch,
        leader=leader_config,
        members=member_configs,
    )
```

- [ ] **Step 7: Create test fixture TOML**

Create `tests/fixtures/team_broadcast.toml`:

```toml
[team]
team_id = "test-broadcast-team"
team_name = "Test Broadcast Team"
max_concurrent_members = 5
member_dispatch = "broadcast"

[team.leader]
system_instruction = "全メンバーの結果を統合し、最終的な回答を作成してください。"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.7

[[team.members]]
agent_name = "agent-1"
agent_type = "plain"
tool_name = "delegate_to_agent_1"
tool_description = "Test agent 1"
model = "google-gla:gemini-2.5-flash-lite"

[[team.members]]
agent_name = "agent-2"
agent_type = "plain"
tool_name = "delegate_to_agent_2"
tool_description = "Test agent 2"
model = "google-gla:gemini-2.5-flash-lite"
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `uv run pytest tests/unit/config/test_member_dispatch.py -v`
Expected: All 8 tests PASS

- [ ] **Step 9: Run existing tests for regression**

Run: `uv run pytest tests/unit/config/ tests/unit/round_controller/ -v --timeout=30`
Expected: All existing tests PASS (no regressions)

- [ ] **Step 10: Quality check and commit**

Run: `ruff check --fix . && ruff format . && mypy src/mixseek/config/schema.py src/mixseek/agents/leader/config.py src/mixseek/config/sources/team_toml_source.py`

```bash
git add src/mixseek/config/schema.py src/mixseek/config/sources/team_toml_source.py src/mixseek/agents/leader/config.py tests/unit/config/test_member_dispatch.py tests/fixtures/team_broadcast.toml
git commit -m "feat: add member_dispatch field to TeamSettings and TeamConfig"
```

---

## Task 2: Implement `_run_single_member` in RoundController

**Files:**
- Modify: `src/mixseek/round_controller/controller.py`
- Create: `tests/unit/round_controller/test_broadcast.py`

- [ ] **Step 1: Write failing tests for `_run_single_member`**

Create `tests/unit/round_controller/test_broadcast.py`:

```python
"""Unit tests for broadcast member dispatch mode.

Feature: Broadcast Member Dispatch
Design: docs/superpowers/specs/2026-04-10-broadcast-member-dispatch-design.md
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic_ai import RunUsage

from mixseek.agents.leader.dependencies import TeamDependencies
from mixseek.agents.leader.models import MemberSubmission
from mixseek.agents.member.base import BaseMemberAgent
from mixseek.config.schema import EvaluatorSettings, JudgmentSettings, PromptBuilderSettings
from mixseek.evaluator import EvaluationResult
from mixseek.models.evaluation_result import MetricScore
from mixseek.models.member_agent import MemberAgentResult, ResultStatus
from mixseek.orchestrator.models import OrchestratorTask
from mixseek.round_controller import RoundController


def _create_mock_member_agent(
    content: str = "mock result",
    agent_name: str = "mock-agent",
    agent_type: str = "plain",
) -> AsyncMock:
    """Create a mock BaseMemberAgent with standard response."""
    mock = AsyncMock(spec=BaseMemberAgent)
    mock.execute.return_value = MemberAgentResult(
        status=ResultStatus.SUCCESS,
        content=content,
        agent_name=agent_name,
        agent_type=agent_type,
        timestamp=datetime.now(UTC),
        execution_time_ms=100,
        usage_info={"input_tokens": 50, "output_tokens": 30},
        error_message=None,
        error_code=None,
        retry_count=0,
        max_retries_exceeded=False,
        metadata={},
        all_messages=None,
    )
    mock.config = MagicMock()
    mock.config.name = agent_name
    mock.config.type = agent_type
    return mock


def _create_failing_mock_member_agent(
    agent_name: str = "failing-agent",
    agent_type: str = "plain",
) -> AsyncMock:
    """Create a mock BaseMemberAgent that raises an exception."""
    mock = AsyncMock(spec=BaseMemberAgent)
    mock.execute.side_effect = RuntimeError("Agent execution failed")
    mock.config = MagicMock()
    mock.config.name = agent_name
    mock.config.type = agent_type
    return mock


def _create_deps() -> TeamDependencies:
    """Create standard TeamDependencies for testing."""
    return TeamDependencies(
        execution_id=str(uuid4()),
        team_id="test-team",
        team_name="Test Team",
        round_number=1,
    )


class TestRunSingleMember:
    """Tests for RoundController._run_single_member."""

    @pytest.mark.asyncio
    @patch("mixseek.round_controller.controller.AggregationStore")
    async def test_success_records_submission(
        self,
        mock_store_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """成功したメンバー実行がMemberSubmissionとして記録される."""
        mock_store_class.return_value = AsyncMock()

        team_config_path = Path.cwd() / "tests" / "fixtures" / "team_broadcast.toml"
        task = OrchestratorTask(
            execution_id=str(uuid4()),
            user_prompt="Test prompt",
            team_configs=[team_config_path],
            timeout_seconds=300,
            max_rounds=1,
            min_rounds=1,
        )
        controller = RoundController(
            team_config_path=team_config_path,
            workspace=tmp_path,
            task=task,
            evaluator_settings=EvaluatorSettings(),
            judgment_settings=JudgmentSettings(),
            prompt_builder_settings=PromptBuilderSettings(),
        )

        deps = _create_deps()
        mock_agent = _create_mock_member_agent(
            content="search result",
            agent_name="web-searcher",
            agent_type="web_search",
        )

        await controller._run_single_member(
            agent_name="web-searcher",
            agent_type="web_search",
            member_agent=mock_agent,
            user_prompt="Analyze this topic",
            deps=deps,
        )

        assert len(deps.submissions) == 1
        sub = deps.submissions[0]
        assert sub.agent_name == "web-searcher"
        assert sub.agent_type == "web_search"
        assert sub.content == "search result"
        assert sub.status == "SUCCESS"
        assert sub.error_message is None
        assert sub.execution_time_ms is not None

    @pytest.mark.asyncio
    @patch("mixseek.round_controller.controller.AggregationStore")
    async def test_error_records_error_submission(
        self,
        mock_store_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """例外を送出したメンバーがERROR状態のMemberSubmissionとして記録される."""
        mock_store_class.return_value = AsyncMock()

        team_config_path = Path.cwd() / "tests" / "fixtures" / "team_broadcast.toml"
        task = OrchestratorTask(
            execution_id=str(uuid4()),
            user_prompt="Test prompt",
            team_configs=[team_config_path],
            timeout_seconds=300,
            max_rounds=1,
            min_rounds=1,
        )
        controller = RoundController(
            team_config_path=team_config_path,
            workspace=tmp_path,
            task=task,
            evaluator_settings=EvaluatorSettings(),
            judgment_settings=JudgmentSettings(),
            prompt_builder_settings=PromptBuilderSettings(),
        )

        deps = _create_deps()
        mock_agent = _create_failing_mock_member_agent(
            agent_name="failing-agent",
            agent_type="plain",
        )

        await controller._run_single_member(
            agent_name="failing-agent",
            agent_type="plain",
            member_agent=mock_agent,
            user_prompt="Analyze this topic",
            deps=deps,
        )

        assert len(deps.submissions) == 1
        sub = deps.submissions[0]
        assert sub.agent_name == "failing-agent"
        assert sub.status == "ERROR"
        assert "Agent execution failed" in (sub.error_message or "")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/round_controller/test_broadcast.py::TestRunSingleMember -v`
Expected: FAIL — `_run_single_member` does not exist on `RoundController`

- [ ] **Step 3: Implement `_run_single_member`**

In `src/mixseek/round_controller/controller.py`, add `import asyncio` at the top (line ~7, after `import json`), then add the following method to `RoundController` class (after `_execute_single_round`, around line 414):

```python
    async def _run_single_member(
        self,
        agent_name: str,
        agent_type: str,
        member_agent: object,
        user_prompt: str,
        deps: TeamDependencies,
    ) -> None:
        """単一メンバーエージェントを実行し、結果をdeps.submissionsに記録する.

        broadcastモードで使用。成功・失敗いずれもMemberSubmissionとして記録し、
        例外は送出しない（asyncio.gather内で安全に動作するため）。

        Args:
            agent_name: エージェント名
            agent_type: エージェント種別
            member_agent: BaseMemberAgentインスタンス
            user_prompt: ユーザープロンプト
            deps: TeamDependencies（submissions追記先）
        """
        from mixseek.agents.leader.models import MemberSubmission
        from mixseek.agents.member.base import BaseMemberAgent

        start_time = datetime.now(UTC)

        try:
            if not isinstance(member_agent, BaseMemberAgent):
                raise TypeError(f"Broadcast mode only supports BaseMemberAgent, got {type(member_agent).__name__}")

            context = {
                "execution_id": deps.execution_id,
                "team_id": deps.team_id,
                "round_number": deps.round_number,
            }
            result_obj = await member_agent.execute(user_prompt, context=context)

            end_time = datetime.now(UTC)
            execution_time_ms = (end_time - start_time).total_seconds() * 1000

            submission = MemberSubmission(
                agent_name=agent_name,
                agent_type=agent_type,
                content=result_obj.content,
                status=result_obj.status.value.upper(),
                error_message=result_obj.error_message,
                usage=RunUsage(
                    input_tokens=result_obj.usage_info.get("input_tokens", 0) if result_obj.usage_info else 0,
                    output_tokens=result_obj.usage_info.get("output_tokens", 0) if result_obj.usage_info else 0,
                    requests=1,
                ),
                execution_time_ms=execution_time_ms,
                timestamp=end_time,
                all_messages=result_obj.all_messages,
            )
        except Exception as e:
            end_time = datetime.now(UTC)
            execution_time_ms = (end_time - start_time).total_seconds() * 1000
            logger.warning(f"Broadcast member agent '{agent_name}' failed: {e}")

            submission = MemberSubmission(
                agent_name=agent_name,
                agent_type=agent_type,
                content="",
                status="ERROR",
                error_message=str(e),
                usage=RunUsage(input_tokens=0, output_tokens=0, requests=0),
                execution_time_ms=execution_time_ms,
                timestamp=end_time,
                all_messages=None,
            )

        deps.submissions.append(submission)
```

Also add the missing import. At the top of `controller.py` (around line 9), ensure `RunUsage` is imported:

```python
from pydantic_ai import RunUsage
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/round_controller/test_broadcast.py::TestRunSingleMember -v`
Expected: All 2 tests PASS

- [ ] **Step 5: Quality check and commit**

Run: `ruff check --fix . && ruff format . && mypy src/mixseek/round_controller/controller.py`

```bash
git add src/mixseek/round_controller/controller.py tests/unit/round_controller/test_broadcast.py
git commit -m "feat: add _run_single_member for broadcast dispatch"
```

---

## Task 3: Implement `_build_aggregation_prompt` and `_aggregate_with_leader`

**Files:**
- Modify: `src/mixseek/round_controller/controller.py`
- Modify: `tests/unit/round_controller/test_broadcast.py`

- [ ] **Step 1: Write failing tests for aggregation prompt and leader aggregation**

Append to `tests/unit/round_controller/test_broadcast.py`:

```python
class TestBuildAggregationPrompt:
    """Tests for RoundController._build_aggregation_prompt."""

    @patch("mixseek.round_controller.controller.AggregationStore")
    def test_formats_successful_submissions(
        self,
        mock_store_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """成功したsubmissionsが正しくフォーマットされる."""
        mock_store_class.return_value = AsyncMock()

        team_config_path = Path.cwd() / "tests" / "fixtures" / "team_broadcast.toml"
        task = OrchestratorTask(
            execution_id=str(uuid4()),
            user_prompt="Test prompt",
            team_configs=[team_config_path],
            timeout_seconds=300,
            max_rounds=1,
            min_rounds=1,
        )
        controller = RoundController(
            team_config_path=team_config_path,
            workspace=tmp_path,
            task=task,
            evaluator_settings=EvaluatorSettings(),
            judgment_settings=JudgmentSettings(),
            prompt_builder_settings=PromptBuilderSettings(),
        )

        submissions = [
            MemberSubmission(
                agent_name="web-searcher",
                agent_type="web_search",
                content="Search results here",
                status="SUCCESS",
                usage=RunUsage(input_tokens=50, output_tokens=30, requests=1),
            ),
            MemberSubmission(
                agent_name="data-analyst",
                agent_type="code_execution",
                content="Analysis results here",
                status="SUCCESS",
                usage=RunUsage(input_tokens=60, output_tokens=40, requests=1),
            ),
        ]

        prompt = controller._build_aggregation_prompt(
            original_prompt="Analyze this topic",
            submissions=submissions,
        )

        assert "Analyze this topic" in prompt
        assert "web-searcher" in prompt
        assert "SUCCESS" in prompt
        assert "Search results here" in prompt
        assert "data-analyst" in prompt
        assert "Analysis results here" in prompt

    @patch("mixseek.round_controller.controller.AggregationStore")
    def test_formats_error_submissions(
        self,
        mock_store_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """ERRORのsubmissionがエラー情報付きでフォーマットされる."""
        mock_store_class.return_value = AsyncMock()

        team_config_path = Path.cwd() / "tests" / "fixtures" / "team_broadcast.toml"
        task = OrchestratorTask(
            execution_id=str(uuid4()),
            user_prompt="Test prompt",
            team_configs=[team_config_path],
            timeout_seconds=300,
            max_rounds=1,
            min_rounds=1,
        )
        controller = RoundController(
            team_config_path=team_config_path,
            workspace=tmp_path,
            task=task,
            evaluator_settings=EvaluatorSettings(),
            judgment_settings=JudgmentSettings(),
            prompt_builder_settings=PromptBuilderSettings(),
        )

        submissions = [
            MemberSubmission(
                agent_name="failing-agent",
                agent_type="plain",
                content="",
                status="ERROR",
                error_message="Timeout exceeded",
                usage=RunUsage(input_tokens=0, output_tokens=0, requests=0),
            ),
        ]

        prompt = controller._build_aggregation_prompt(
            original_prompt="Analyze this topic",
            submissions=submissions,
        )

        assert "failing-agent" in prompt
        assert "ERROR" in prompt
        assert "Timeout exceeded" in prompt


class TestAggregateWithLeader:
    """Tests for RoundController._aggregate_with_leader."""

    @pytest.mark.asyncio
    @patch("mixseek.round_controller.controller.create_leader_agent")
    @patch("mixseek.round_controller.controller.AggregationStore")
    async def test_calls_leader_with_no_tools(
        self,
        mock_store_class: MagicMock,
        mock_create_leader: MagicMock,
        tmp_path: Path,
    ) -> None:
        """集約用Leader Agentがmember_agents={}で作成される."""
        mock_store_class.return_value = AsyncMock()

        mock_leader = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = "Aggregated response"
        mock_result.all_messages.return_value = []
        mock_leader.run.return_value = mock_result
        mock_create_leader.return_value = mock_leader

        team_config_path = Path.cwd() / "tests" / "fixtures" / "team_broadcast.toml"
        task = OrchestratorTask(
            execution_id=str(uuid4()),
            user_prompt="Test prompt",
            team_configs=[team_config_path],
            timeout_seconds=300,
            max_rounds=1,
            min_rounds=1,
        )
        controller = RoundController(
            team_config_path=team_config_path,
            workspace=tmp_path,
            task=task,
            evaluator_settings=EvaluatorSettings(),
            judgment_settings=JudgmentSettings(),
            prompt_builder_settings=PromptBuilderSettings(),
        )

        deps = _create_deps()
        deps.submissions = [
            MemberSubmission(
                agent_name="agent-1",
                agent_type="plain",
                content="Result 1",
                status="SUCCESS",
                usage=RunUsage(input_tokens=10, output_tokens=20, requests=1),
            ),
        ]

        result = await controller._aggregate_with_leader(
            user_prompt="Original prompt",
            deps=deps,
        )

        assert result == "Aggregated response"
        # Verify create_leader_agent called with empty member_agents
        mock_create_leader.assert_called_once()
        call_args = mock_create_leader.call_args
        assert call_args[0][1] == {}  # member_agents={}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/round_controller/test_broadcast.py::TestBuildAggregationPrompt tests/unit/round_controller/test_broadcast.py::TestAggregateWithLeader -v`
Expected: FAIL — methods do not exist

- [ ] **Step 3: Implement `_build_aggregation_prompt`**

Add to `RoundController` class in `controller.py` (after `_run_single_member`):

```python
    def _build_aggregation_prompt(
        self,
        original_prompt: str,
        submissions: list[MemberSubmission],
    ) -> str:
        """broadcastモードの集約プロンプトを構築する.

        Args:
            original_prompt: 元のユーザープロンプト
            submissions: 全メンバーの実行結果

        Returns:
            集約用プロンプト文字列
        """
        sections: list[str] = []
        for sub in submissions:
            if sub.status == "ERROR":
                section = f"### {sub.agent_name} ({sub.status})\nエラー: {sub.error_message}"
            else:
                section = f"### {sub.agent_name} ({sub.status})\n{sub.content}"
            sections.append(section)

        member_results = "\n\n".join(sections)

        return (
            "以下は各メンバーエージェントの実行結果です。\n"
            "これらを統合して、最終的な回答を作成してください。\n\n"
            f"## 元のタスク\n{original_prompt}\n\n"
            f"## メンバーエージェント結果\n\n{member_results}"
        )
```

- [ ] **Step 4: Implement `_aggregate_with_leader`**

Add to `RoundController` class (after `_build_aggregation_prompt`):

```python
    async def _aggregate_with_leader(
        self,
        user_prompt: str,
        deps: TeamDependencies,
    ) -> tuple[str, list[Any]]:
        """broadcastの結果をLeader Agentで集約する.

        Tool登録なしのLeader Agentを作成し、全メンバーの結果を
        集約プロンプトとして渡して最終回答を生成する。

        Args:
            user_prompt: 元のユーザープロンプト
            deps: TeamDependencies（submissionsを含む）

        Returns:
            tuple of (集約後の最終回答テキスト, message_history)
        """
        leader_agent = create_leader_agent(self.team_config, member_agents={})

        aggregation_prompt = self._build_aggregation_prompt(
            original_prompt=user_prompt,
            submissions=deps.submissions,
        )

        result = await leader_agent.run(aggregation_prompt, deps=deps)
        return result.output, result.all_messages()
```

Note: The return type is `tuple[str, list[Any]]` to also return `message_history` for the caller (needed in Task 4).

- [ ] **Step 5: Update the test for `_aggregate_with_leader` return type**

Update `TestAggregateWithLeader.test_calls_leader_with_no_tools` — the method now returns a tuple:

```python
        result, message_history = await controller._aggregate_with_leader(
            user_prompt="Original prompt",
            deps=deps,
        )

        assert result == "Aggregated response"
        assert message_history == []
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/unit/round_controller/test_broadcast.py::TestBuildAggregationPrompt tests/unit/round_controller/test_broadcast.py::TestAggregateWithLeader -v`
Expected: All 3 tests PASS

- [ ] **Step 7: Quality check and commit**

Run: `ruff check --fix . && ruff format . && mypy src/mixseek/round_controller/controller.py`

```bash
git add src/mixseek/round_controller/controller.py tests/unit/round_controller/test_broadcast.py
git commit -m "feat: add aggregation prompt builder and leader aggregation"
```

---

## Task 4: Implement `_execute_broadcast` and dispatch branch

**Files:**
- Modify: `src/mixseek/round_controller/controller.py`
- Modify: `tests/unit/round_controller/test_broadcast.py`

- [ ] **Step 1: Write failing tests for broadcast execution**

Append to `tests/unit/round_controller/test_broadcast.py`:

```python
def _create_mock_leader_agent() -> AsyncMock:
    """Create a mock leader agent for aggregation."""
    mock_agent = AsyncMock()
    mock_result = MagicMock()
    mock_result.output = "Aggregated final answer"
    mock_result.all_messages.return_value = []
    mock_result.usage.return_value = RunUsage(input_tokens=100, output_tokens=50, requests=1)
    mock_agent.run.return_value = mock_result
    return mock_agent


def _create_mock_evaluator() -> MagicMock:
    """Create a mock evaluator."""
    mock_evaluator = MagicMock()
    mock_evaluator.evaluate = AsyncMock(
        return_value=EvaluationResult(
            overall_score=85.0,
            metrics=[
                MetricScore(metric_name="accuracy", score=85.0, evaluator_comment="Good"),
            ],
        )
    )
    return mock_evaluator


def _create_mock_judgment_client(should_continue: bool = False) -> MagicMock:
    """Create a mock judgment client."""
    from mixseek.round_controller.models import ImprovementJudgment

    mock_client = MagicMock()
    mock_client.judge_improvement_prospects = AsyncMock(
        return_value=ImprovementJudgment(
            should_continue=should_continue,
            reasoning="Test judgment",
            confidence_score=0.9,
        )
    )
    return mock_client


class TestExecuteBroadcastEndToEnd:
    """End-to-end tests for broadcast dispatch mode through run_round."""

    @pytest.mark.asyncio
    @patch("mixseek.round_controller.controller.MemberAgentFactory")
    @patch("mixseek.round_controller.controller.create_leader_agent")
    @patch("mixseek.round_controller.controller.AggregationStore")
    @patch("mixseek.round_controller.controller.Evaluator")
    @patch("mixseek.round_controller.controller.JudgmentClient")
    async def test_broadcast_calls_all_members(
        self,
        mock_judgment_class: MagicMock,
        mock_evaluator_class: MagicMock,
        mock_store_class: MagicMock,
        mock_create_leader: MagicMock,
        mock_factory_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """broadcastモードで全メンバーが呼ばれる."""
        mock_store_class.return_value = AsyncMock()
        mock_evaluator_class.return_value = _create_mock_evaluator()
        mock_judgment_class.return_value = _create_mock_judgment_client()
        mock_create_leader.return_value = _create_mock_leader_agent()

        # Setup 2 mock member agents via factory
        mock_member_1 = _create_mock_member_agent(content="Result 1", agent_name="agent-1", agent_type="plain")
        mock_member_2 = _create_mock_member_agent(content="Result 2", agent_name="agent-2", agent_type="web_search")
        mock_factory_class.create_agent.side_effect = [mock_member_1, mock_member_2]

        team_config_path = Path.cwd() / "tests" / "fixtures" / "team_broadcast.toml"
        task = OrchestratorTask(
            execution_id=str(uuid4()),
            user_prompt="Test prompt",
            team_configs=[team_config_path],
            timeout_seconds=300,
            max_rounds=1,
            min_rounds=1,
        )
        controller = RoundController(
            team_config_path=team_config_path,
            workspace=tmp_path,
            task=task,
            evaluator_settings=EvaluatorSettings(),
            judgment_settings=JudgmentSettings(),
            prompt_builder_settings=PromptBuilderSettings(),
        )

        result = await controller.run_round("Test prompt", timeout_seconds=300)

        # Both member agents should have been called
        mock_member_1.execute.assert_called_once()
        mock_member_2.execute.assert_called_once()

    @pytest.mark.asyncio
    @patch("mixseek.round_controller.controller.MemberAgentFactory")
    @patch("mixseek.round_controller.controller.create_leader_agent")
    @patch("mixseek.round_controller.controller.AggregationStore")
    @patch("mixseek.round_controller.controller.Evaluator")
    @patch("mixseek.round_controller.controller.JudgmentClient")
    async def test_broadcast_partial_failure_continues(
        self,
        mock_judgment_class: MagicMock,
        mock_evaluator_class: MagicMock,
        mock_store_class: MagicMock,
        mock_create_leader: MagicMock,
        mock_factory_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """broadcastモードで一部メンバー失敗時も集約が続行される."""
        mock_store_class.return_value = AsyncMock()
        mock_evaluator_class.return_value = _create_mock_evaluator()
        mock_judgment_class.return_value = _create_mock_judgment_client()
        mock_create_leader.return_value = _create_mock_leader_agent()

        # 1 success + 1 failure
        mock_member_1 = _create_mock_member_agent(content="Good result", agent_name="agent-1")
        mock_member_2 = _create_failing_mock_member_agent(agent_name="agent-2")
        mock_factory_class.create_agent.side_effect = [mock_member_1, mock_member_2]

        team_config_path = Path.cwd() / "tests" / "fixtures" / "team_broadcast.toml"
        task = OrchestratorTask(
            execution_id=str(uuid4()),
            user_prompt="Test prompt",
            team_configs=[team_config_path],
            timeout_seconds=300,
            max_rounds=1,
            min_rounds=1,
        )
        controller = RoundController(
            team_config_path=team_config_path,
            workspace=tmp_path,
            task=task,
            evaluator_settings=EvaluatorSettings(),
            judgment_settings=JudgmentSettings(),
            prompt_builder_settings=PromptBuilderSettings(),
        )

        # Should not raise — partial failure is handled
        result = await controller.run_round("Test prompt", timeout_seconds=300)

        # Leader aggregation should still have been called
        mock_create_leader.assert_called()
        assert result.submission_content == "Aggregated final answer"


class TestSelectiveModeUnchanged:
    """Verify selective (default) mode is not affected."""

    @pytest.mark.asyncio
    @patch("mixseek.round_controller.controller.create_leader_agent")
    @patch("mixseek.round_controller.controller.AggregationStore")
    @patch("mixseek.round_controller.controller.Evaluator")
    @patch("mixseek.round_controller.controller.JudgmentClient")
    async def test_selective_uses_existing_leader_path(
        self,
        mock_judgment_class: MagicMock,
        mock_evaluator_class: MagicMock,
        mock_store_class: MagicMock,
        mock_create_leader: MagicMock,
        tmp_path: Path,
    ) -> None:
        """selectiveモードでは既存のleader_agent.run()パスが使われる."""
        mock_store_class.return_value = AsyncMock()
        mock_evaluator_class.return_value = _create_mock_evaluator()
        mock_judgment_class.return_value = _create_mock_judgment_client()
        mock_create_leader.return_value = _create_mock_leader_agent()

        # team1.toml has no member_dispatch (defaults to selective)
        team_config_path = Path.cwd() / "tests" / "fixtures" / "team1.toml"
        task = OrchestratorTask(
            execution_id=str(uuid4()),
            user_prompt="Test prompt",
            team_configs=[team_config_path],
            timeout_seconds=300,
            max_rounds=1,
            min_rounds=1,
        )
        controller = RoundController(
            team_config_path=team_config_path,
            workspace=tmp_path,
            task=task,
            evaluator_settings=EvaluatorSettings(),
            judgment_settings=JudgmentSettings(),
            prompt_builder_settings=PromptBuilderSettings(),
        )

        result = await controller.run_round("Test prompt", timeout_seconds=300)

        # create_leader_agent should be called WITH member_agents (not empty)
        mock_create_leader.assert_called_once()
        call_args = mock_create_leader.call_args
        member_agents_arg = call_args[0][1]
        # For team1.toml (no members), it should be an empty dict but via the normal path
        assert isinstance(member_agents_arg, dict)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/round_controller/test_broadcast.py::TestExecuteBroadcastEndToEnd tests/unit/round_controller/test_broadcast.py::TestSelectiveModeUnchanged -v`
Expected: FAIL — `_execute_broadcast` does not exist, no dispatch branching

- [ ] **Step 3: Implement `_execute_broadcast`**

Add to `RoundController` class in `controller.py` (after `_aggregate_with_leader`). Also add `import asyncio` at the top if not already present:

```python
    async def _execute_broadcast(
        self,
        member_agents: dict[str, object],
        user_prompt: str,
        deps: TeamDependencies,
    ) -> tuple[str, list[Any]]:
        """全メンバーを並列実行し、Leader Agentで集約する.

        asyncio.gatherで全メンバーを同時実行した後、
        Tool登録なしのLeader Agentで結果を統合する。

        Args:
            member_agents: メンバーエージェントマップ（agent_name -> Agent）
            user_prompt: ユーザープロンプト
            deps: TeamDependencies

        Returns:
            tuple of (集約後の最終回答, message_history)
        """
        # メンバー設定マップを構築（agent_name -> (agent_type)）
        member_type_map: dict[str, str] = {
            m.agent_name: m.agent_type for m in self.team_settings.members
        }

        # 全メンバーを並列実行
        tasks = [
            self._run_single_member(
                agent_name=name,
                agent_type=member_type_map.get(name, "unknown"),
                member_agent=agent,
                user_prompt=user_prompt,
                deps=deps,
            )
            for name, agent in member_agents.items()
        ]
        await asyncio.gather(*tasks)

        # Leader Agentで集約
        return await self._aggregate_with_leader(user_prompt, deps)
```

- [ ] **Step 4: Add dispatch branch in `_execute_single_round`**

In `_execute_single_round` (line ~297-314), replace the existing "Execute Leader Agent" block with a dispatch branch. Replace from `# 2. Execute Leader Agent` up to (and including) the line `message_history = result.all_messages()`:

```python
        # 2. Execute: dispatch by member_dispatch mode
        self._write_progress_file(round_number, status="running", current_agent="leader")

        deps = TeamDependencies(
            execution_id=self.task.execution_id,
            team_id=self.team_config.team_id,
            team_name=self.team_config.team_name,
            round_number=round_number,
        )

        if self.team_config.member_dispatch == "broadcast":
            # Broadcast: 全メンバー並列実行 → Leader集約
            submission_content, message_history = await self._execute_broadcast(
                member_agents=member_agents,
                user_prompt=user_prompt,
                deps=deps,
            )
        else:
            # Selective (default): LLMがToolとしてメンバーを選択
            leader_agent = create_leader_agent(self.team_config, member_agents)
            result = await leader_agent.run(user_prompt, deps=deps)
            submission_content = result.output
            message_history = result.all_messages()

        self._write_progress_file(round_number, status="running", current_agent=None)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/round_controller/test_broadcast.py -v`
Expected: All tests PASS

- [ ] **Step 6: Run full regression**

Run: `uv run pytest tests/unit/round_controller/ tests/unit/config/ -v --timeout=30`
Expected: All existing + new tests PASS

- [ ] **Step 7: Quality check and commit**

Run: `ruff check --fix . && ruff format . && mypy src/mixseek/round_controller/controller.py`

```bash
git add src/mixseek/round_controller/controller.py tests/unit/round_controller/test_broadcast.py
git commit -m "feat: implement broadcast dispatch mode with parallel execution and leader aggregation"
```

---

## Task 5: Final integration verification

**Files:**
- No new files

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest tests/unit/ -v --timeout=60`
Expected: All tests PASS

- [ ] **Step 2: Full quality gate**

Run: `ruff check --fix . && ruff format . && mypy .`
Expected: No errors

- [ ] **Step 3: Verify git log**

Run: `git log --oneline -5`
Expected: 3 commits for this feature:
1. `feat: add member_dispatch field to TeamSettings and TeamConfig`
2. `feat: add _run_single_member for broadcast dispatch`
3. `feat: implement broadcast dispatch mode with parallel execution and leader aggregation`
