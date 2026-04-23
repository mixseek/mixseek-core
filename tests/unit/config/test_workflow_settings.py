"""Tests for workflow-mode Pydantic schemas.

PR1 で追加された以下スキーマの単体テスト:
- FunctionPluginMetadata
- AgentExecutorSettings (to_member_agent_config を含む)
- FunctionExecutorSettings
- StepExecutorConfig (discriminated union)
- WorkflowStepSettings
- WorkflowSettings (team_id/team_name @property を含む)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from pytest_mock import MockerFixture

from mixseek.config.schema import (
    AgentExecutorSettings,
    FunctionExecutorSettings,
    FunctionPluginMetadata,
    WorkflowSettings,
    WorkflowStepSettings,
)
from mixseek.models.member_agent import MemberAgentConfig, PluginMetadata

# ---------------------------------------------------------------------------
# ヘルパー (TOML ロード相当の dict → model_validate 経由で実装と同じパスを通す)
# ---------------------------------------------------------------------------


def _agent_executor_dict(name: str = "a1", type: str = "plain", **kw: Any) -> dict[str, Any]:
    return {"name": name, "type": type, **kw}


def _function_executor_dict(name: str = "f1", **kw: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "name": name,
        "type": "function",
        "plugin": {"module": "mypkg.tools", "function": "fn"},
    }
    data.update(kw)
    return data


def _minimum_workflow_dict(**kw: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "workflow_id": "wf-1",
        "workflow_name": "Workflow 1",
        "steps": [{"id": "s1", "executors": [_agent_executor_dict()]}],
    }
    data.update(kw)
    return data


def _make_step(id: str = "s1", executors: list[dict[str, Any]] | None = None) -> WorkflowStepSettings:
    """WorkflowStepSettings を dict 経由で生成（discriminator を通す実装パス）。"""
    if executors is None:
        executors = [_agent_executor_dict()]
    return WorkflowStepSettings.model_validate({"id": id, "executors": executors})


def _make_workflow(**kw: Any) -> WorkflowSettings:
    """WorkflowSettings を dict 経由で生成（steps 含め validator を通す）。"""
    return WorkflowSettings.model_validate(_minimum_workflow_dict(**kw))


# ---------------------------------------------------------------------------
# FunctionPluginMetadata
# ---------------------------------------------------------------------------


class TestFunctionPluginMetadata:
    def test_valid_instance(self) -> None:
        meta = FunctionPluginMetadata(module="mypkg.tools", function="format_as_markdown")
        assert meta.module == "mypkg.tools"
        assert meta.function == "format_as_markdown"

    def test_missing_module_raises(self) -> None:
        with pytest.raises(ValidationError):
            FunctionPluginMetadata.model_validate({"function": "fn"})

    def test_missing_function_raises(self) -> None:
        with pytest.raises(ValidationError):
            FunctionPluginMetadata.model_validate({"module": "mypkg"})

    def test_extra_fields_forbidden(self) -> None:
        """agent 用 PluginMetadata のフィールド名 (agent_class 等) を渡すと拒否される。"""
        with pytest.raises(ValidationError):
            FunctionPluginMetadata.model_validate({"module": "m", "function": "f", "agent_class": "x"})

    def test_str_strip_whitespace(self) -> None:
        """str_strip_whitespace=True により前後の空白は自動で除去される。"""
        meta = FunctionPluginMetadata(module="  mypkg  ", function="  fn  ")
        assert meta.module == "mypkg"
        assert meta.function == "fn"


# ---------------------------------------------------------------------------
# AgentExecutorSettings
# ---------------------------------------------------------------------------


class TestAgentExecutorSettings:
    def test_valid_minimum(self) -> None:
        exe = AgentExecutorSettings(name="a1", type="plain")
        assert exe.name == "a1"
        assert exe.type == "plain"
        assert exe.model is None  # デフォルト
        assert exe.timeout_seconds is None
        assert exe.max_retries == 3

    def test_missing_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            AgentExecutorSettings.model_validate({"type": "plain"})

    def test_missing_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            AgentExecutorSettings.model_validate({"name": "a1"})

    def test_model_is_optional(self) -> None:
        """model=None は許容される（WorkflowSettings.default_model にフォールバック）。"""
        exe = AgentExecutorSettings(name="a1", type="plain", model=None)
        assert exe.model is None

    def test_invalid_model_format_raises(self) -> None:
        """model 形式不正 (`provider:model-name` 形式でない) は ValidationError。"""
        with pytest.raises(ValidationError):
            AgentExecutorSettings(name="a1", type="plain", model="invalid-model")

    def test_valid_model_format(self) -> None:
        exe = AgentExecutorSettings(name="a1", type="plain", model="anthropic:claude-sonnet-4-5")
        assert exe.model == "anthropic:claude-sonnet-4-5"

    def test_invalid_name_whitespace(self) -> None:
        with pytest.raises(ValidationError):
            AgentExecutorSettings(name="invalid name", type="plain")

    def test_valid_name_with_allowed_chars(self) -> None:
        exe = AgentExecutorSettings(name="agent.v1-alpha_2", type="plain")
        assert exe.name == "agent.v1-alpha_2"

    def test_type_custom_without_plugin_raises(self) -> None:
        """type='custom' で plugin=None は model_validator で拒否される（PR1 タスク L53 要件）。"""
        with pytest.raises(ValidationError) as exc_info:
            AgentExecutorSettings(name="c1", type="custom", plugin=None)
        assert "custom" in str(exc_info.value)
        assert "plugin" in str(exc_info.value)

    def test_type_custom_with_plugin_ok(self) -> None:
        plugin = PluginMetadata(agent_class="mypkg.MyAgent")
        exe = AgentExecutorSettings(name="c1", type="custom", plugin=plugin)
        assert exe.type == "custom"
        assert exe.plugin is plugin

    def test_tool_name_extra_forbidden(self) -> None:
        """MemberAgentSettings 専用フィールド tool_name は AgentExecutorSettings では拒否。"""
        with pytest.raises(ValidationError):
            AgentExecutorSettings.model_validate({"name": "a1", "type": "plain", "tool_name": "x"})

    def test_tool_description_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            AgentExecutorSettings.model_validate({"name": "a1", "type": "plain", "tool_description": "x"})

    def test_timeout_seconds_zero_rejected(self) -> None:
        """ge=1 バリデーション: timeout_seconds=0 は拒否。"""
        with pytest.raises(ValidationError):
            AgentExecutorSettings(name="a1", type="plain", timeout_seconds=0)

    def test_timeout_seconds_none_accepted(self) -> None:
        exe = AgentExecutorSettings(name="a1", type="plain", timeout_seconds=None)
        assert exe.timeout_seconds is None

    def test_timeout_seconds_one_accepted(self) -> None:
        exe = AgentExecutorSettings(name="a1", type="plain", timeout_seconds=1)
        assert exe.timeout_seconds == 1


class TestAgentToMemberAgentConfig:
    """AgentExecutorSettings.to_member_agent_config の変換仕様。"""

    def test_returns_member_agent_config(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch(
            "mixseek.config.schema._resolve_bundled_system_instruction",
            return_value="RESOLVED",
        )
        exe = AgentExecutorSettings(name="a1", type="plain")
        config = exe.to_member_agent_config(
            workspace=tmp_path,
            default_model="google-gla:gemini-2.5-flash",
        )
        assert isinstance(config, MemberAgentConfig)
        assert config.name == "a1"
        assert config.type == "plain"
        assert config.system_instruction == "RESOLVED"

    def test_delegates_bundled_resolution(self, tmp_path: Path, mocker: MockerFixture) -> None:
        resolver = mocker.patch(
            "mixseek.config.schema._resolve_bundled_system_instruction",
            return_value="BUNDLED_TEXT",
        )
        exe = AgentExecutorSettings(name="a1", type="plain", system_instruction=None)
        config = exe.to_member_agent_config(
            workspace=tmp_path,
            default_model="google-gla:gemini-2.5-flash",
        )
        assert config.system_instruction == "BUNDLED_TEXT"
        resolver.assert_called_once_with(
            agent_type="plain",
            system_instruction=None,
            workspace=tmp_path,
        )

    def test_model_none_uses_default_model(self, mocker: MockerFixture) -> None:
        """model=None のとき default_model にフォールバックする。"""
        mocker.patch(
            "mixseek.config.schema._resolve_bundled_system_instruction",
            return_value="",
        )
        exe = AgentExecutorSettings(name="a1", type="plain", model=None)
        config = exe.to_member_agent_config(default_model="google-gla:gemini-2.5-flash")
        assert config.model == "google-gla:gemini-2.5-flash"

    def test_explicit_model_overrides_default(self, mocker: MockerFixture) -> None:
        """model 指定があればそちらが優先される。"""
        mocker.patch(
            "mixseek.config.schema._resolve_bundled_system_instruction",
            return_value="",
        )
        exe = AgentExecutorSettings(name="a1", type="plain", model="anthropic:claude-sonnet-4-5")
        config = exe.to_member_agent_config(default_model="google-gla:gemini-2.5-flash")
        assert config.model == "anthropic:claude-sonnet-4-5"

    def test_plugin_and_tool_settings_propagated(self, mocker: MockerFixture) -> None:
        mocker.patch(
            "mixseek.config.schema._resolve_bundled_system_instruction",
            return_value="",
        )
        plugin = PluginMetadata(agent_class="mypkg.MyAgent")
        exe = AgentExecutorSettings(name="c1", type="custom", plugin=plugin, metadata={"k": "v"})
        config = exe.to_member_agent_config(default_model="google-gla:gemini-2.5-flash")
        assert config.plugin is plugin
        assert config.metadata.get("k") == "v"


# ---------------------------------------------------------------------------
# FunctionExecutorSettings
# ---------------------------------------------------------------------------


def _function_plugin() -> FunctionPluginMetadata:
    return FunctionPluginMetadata(module="m", function="f")


class TestFunctionExecutorSettings:
    def test_valid_minimum(self) -> None:
        exe = FunctionExecutorSettings(name="f1", plugin=_function_plugin())
        assert exe.name == "f1"
        assert exe.type == "function"  # default
        assert exe.timeout_seconds is None

    def test_type_default(self) -> None:
        """type は Literal["function"] で default="function"。"""
        exe = FunctionExecutorSettings(name="f1", plugin=_function_plugin())
        assert exe.type == "function"

    def test_plugin_required(self) -> None:
        with pytest.raises(ValidationError):
            FunctionExecutorSettings.model_validate({"name": "f1"})

    def test_model_extra_forbidden(self) -> None:
        """model は AgentExecutor 専用フィールド。Function 側では拒否。"""
        with pytest.raises(ValidationError):
            FunctionExecutorSettings.model_validate(
                {
                    "name": "f1",
                    "plugin": {"module": "m", "function": "f"},
                    "model": "google-gla:gemini-2.5-flash",
                }
            )

    def test_timeout_seconds_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            FunctionExecutorSettings(name="f1", plugin=_function_plugin(), timeout_seconds=0)

    def test_timeout_seconds_none_accepted(self) -> None:
        exe = FunctionExecutorSettings(name="f1", plugin=_function_plugin(), timeout_seconds=None)
        assert exe.timeout_seconds is None

    def test_invalid_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            FunctionExecutorSettings(name="bad name", plugin=_function_plugin())


# ---------------------------------------------------------------------------
# StepExecutorConfig (discriminated union) + WorkflowStepSettings
# ---------------------------------------------------------------------------


class TestStepExecutorConfig:
    def test_agent_discriminator(self) -> None:
        step = _make_step(executors=[_agent_executor_dict(name="a1", type="plain")])
        assert isinstance(step.executors[0], AgentExecutorSettings)

    def test_function_discriminator(self) -> None:
        step = _make_step(executors=[_function_executor_dict(name="f1")])
        assert isinstance(step.executors[0], FunctionExecutorSettings)

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            _make_step(executors=[{"name": "x1", "type": "bogus"}])

    def test_mixed_executors(self) -> None:
        step = _make_step(
            executors=[
                _agent_executor_dict(name="a1", type="plain"),
                _function_executor_dict(name="f1"),
                _agent_executor_dict(name="a2", type="web_search"),
            ]
        )
        assert isinstance(step.executors[0], AgentExecutorSettings)
        assert isinstance(step.executors[1], FunctionExecutorSettings)
        assert isinstance(step.executors[2], AgentExecutorSettings)


class TestWorkflowStepSettings:
    def test_empty_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_step(id="")

    def test_whitespace_only_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_step(id="   ")

    def test_empty_executors_rejected(self) -> None:
        """min_length=1 により空 list は拒否。"""
        with pytest.raises(ValidationError):
            _make_step(executors=[])

    def test_duplicate_executor_names_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            _make_step(
                executors=[
                    _agent_executor_dict(name="dup"),
                    _agent_executor_dict(name="dup"),
                ]
            )
        msg = str(exc_info.value)
        assert "s1" in msg
        assert "dup" in msg

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            WorkflowStepSettings.model_validate(
                {
                    "id": "s1",
                    "executors": [_agent_executor_dict()],
                    "unknown_field": "x",
                }
            )


# ---------------------------------------------------------------------------
# WorkflowSettings
# ---------------------------------------------------------------------------


class TestWorkflowSettings:
    def test_valid_minimum(self) -> None:
        wf = _make_workflow()
        assert wf.workflow_id == "wf-1"
        assert wf.workflow_name == "Workflow 1"
        assert wf.default_model == "google-gla:gemini-2.5-flash"
        assert wf.include_all_context is True
        assert wf.final_output_format == "json"
        assert len(wf.steps) == 1

    def test_workflow_id_empty_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_workflow(workflow_id="")

    def test_workflow_name_whitespace_only_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_workflow(workflow_name="   ")

    def test_default_model_default_value(self) -> None:
        wf = _make_workflow()
        assert wf.default_model == "google-gla:gemini-2.5-flash"

    def test_default_model_invalid_format_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_workflow(default_model="bad")

    def test_duplicate_step_ids_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            WorkflowSettings.model_validate(
                {
                    "workflow_id": "wf-1",
                    "workflow_name": "W",
                    "steps": [
                        {"id": "dup", "executors": [_agent_executor_dict(name="a1")]},
                        {"id": "dup", "executors": [_agent_executor_dict(name="a2")]},
                    ],
                }
            )
        assert "dup" in str(exc_info.value)

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            _make_workflow(unknown="x")

    def test_include_all_context_default_true(self) -> None:
        wf = _make_workflow()
        assert wf.include_all_context is True

    def test_final_output_format_literal_enforced(self) -> None:
        with pytest.raises(ValidationError):
            _make_workflow(final_output_format="xml")

    def test_steps_min_length(self) -> None:
        with pytest.raises(ValidationError):
            WorkflowSettings.model_validate({"workflow_id": "wf-1", "workflow_name": "W", "steps": []})

    def test_team_id_property_maps_to_workflow_id(self) -> None:
        wf = _make_workflow(workflow_id="my-wf")
        assert wf.team_id == "my-wf"
        assert wf.team_id == wf.workflow_id

    def test_team_name_property_maps_to_workflow_name(self) -> None:
        wf = _make_workflow(workflow_name="My Flow")
        assert wf.team_name == "My Flow"
        assert wf.team_name == wf.workflow_name

    def test_model_dump_excludes_property_keys(self) -> None:
        """@property は model_fields に入らないため model_dump() に含まれない（設計書§10 要件）。

        `computed_field` を使った誤実装を早期検出するため明示的に検証。
        """
        wf = _make_workflow()
        dumped = wf.model_dump()
        assert "team_id" not in dumped
        assert "team_name" not in dumped
        # workflow_id / workflow_name は実フィールドなので含まれる
        assert dumped["workflow_id"] == "wf-1"
        assert dumped["workflow_name"] == "Workflow 1"

    def test_model_dump_json_excludes_property_keys(self) -> None:
        wf = _make_workflow()
        parsed = json.loads(wf.model_dump_json())
        assert "team_id" not in parsed
        assert "team_name" not in parsed
