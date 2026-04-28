"""`build_executable` / `_load_function` / `_logfire_span` / `_to_run_usage` の単体テスト。

invariant:
    - build_executable 未知型 TypeError / _load_function 不正 import
    - logfire 非導入時 (_LOGFIRE_AVAILABLE=False) でも workflow が動く
"""

from contextlib import nullcontext
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from mixseek.agents.leader.dependencies import TeamDependencies
from mixseek.workflow import executable as executable_module
from mixseek.workflow.executable import (
    AgentExecutable,
    FunctionExecutable,
    _load_function,
    _logfire_span,
    _to_run_usage,
    build_executable,
)

from ._executable_helpers import make_agent_mock


class TestLogfireSpan:
    """logfire 非導入時の nullcontext fallback。"""

    def test_fallback_to_nullcontext_when_unavailable(self, mocker: MockerFixture) -> None:
        mocker.patch.object(executable_module, "_LOGFIRE_AVAILABLE", False)
        mocker.patch.object(executable_module, "_logfire", None)
        span = _logfire_span("workflow.function", function_name="x")
        assert isinstance(span, type(nullcontext()))

    def test_fallback_works_as_context_manager(self, mocker: MockerFixture) -> None:
        mocker.patch.object(executable_module, "_LOGFIRE_AVAILABLE", False)
        mocker.patch.object(executable_module, "_logfire", None)
        with _logfire_span("workflow.function", function_name="x"):
            pass  # 例外が出ないことを確認

    def test_uses_logfire_span_when_available(self, mocker: MockerFixture) -> None:
        fake_logfire = MagicMock()
        fake_span = MagicMock()
        fake_logfire.span.return_value = fake_span
        mocker.patch.object(executable_module, "_LOGFIRE_AVAILABLE", True)
        mocker.patch.object(executable_module, "_logfire", fake_logfire)
        result = _logfire_span("workflow.function", function_name="x")
        fake_logfire.span.assert_called_once_with("workflow.function", function_name="x")
        assert result is fake_span


class TestToRunUsage:
    def test_none_returns_empty_runusage(self) -> None:
        usage = _to_run_usage(None)
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0

    def test_empty_dict_returns_empty_runusage(self) -> None:
        usage = _to_run_usage({})
        assert usage.input_tokens == 0

    def test_populates_from_dict(self) -> None:
        usage = _to_run_usage({"input_tokens": 10, "output_tokens": 20, "requests": 2})
        assert usage.input_tokens == 10
        assert usage.output_tokens == 20
        assert usage.requests == 2


class TestBuildExecutable:
    def test_function_settings_returns_function_executable(self, team_deps: TeamDependencies) -> None:
        from mixseek.config.schema import (
            FunctionExecutorSettings,
            FunctionPluginMetadata,
        )

        cfg = FunctionExecutorSettings(
            name="fn",
            plugin=FunctionPluginMetadata(
                module="tests.unit.workflow._executable_helpers",
                function="sample_function",
            ),
            timeout_seconds=5,
        )
        ex = build_executable(cfg, team_deps, default_model="google-gla:gemini-2.5-flash")
        assert isinstance(ex, FunctionExecutable)
        assert ex.name == "fn"
        assert ex.executor_type == "function"

    def test_agent_settings_returns_agent_executable(self, team_deps: TeamDependencies, mocker: MockerFixture) -> None:
        from mixseek.config.schema import AgentExecutorSettings

        mock_agent = make_agent_mock(name="ag", agent_type="plain")
        mocker.patch(
            "mixseek.workflow.executable.MemberAgentFactory.create_agent",
            return_value=mock_agent,
        )
        cfg = AgentExecutorSettings(name="ag", type="plain")
        ex = build_executable(cfg, team_deps, default_model="google-gla:gemini-2.5-flash")
        assert isinstance(ex, AgentExecutable)
        assert ex.name == "ag"

    def test_unknown_type_raises_typeerror(self, team_deps: TeamDependencies) -> None:
        with pytest.raises(TypeError, match="Unsupported executor config"):
            build_executable(
                "not-a-cfg",  # type: ignore[arg-type]
                team_deps,
                default_model="google-gla:gemini-2.5-flash",
            )

    def test_function_settings_with_path(self, team_deps: TeamDependencies, tmp_path: Path) -> None:
        """`path` 経由の FunctionPluginMetadata でも build_executable が通る。"""
        from mixseek.config.schema import FunctionExecutorSettings, FunctionPluginMetadata

        f = tmp_path / "fmt.py"
        f.write_text("def fn(x):\n    return f'P:{x}'\n", encoding="utf-8")
        cfg = FunctionExecutorSettings(
            name="fn",
            plugin=FunctionPluginMetadata(path=str(f), function="fn"),
            timeout_seconds=5,
        )
        ex = build_executable(cfg, team_deps, default_model="google-gla:gemini-2.5-flash")
        assert isinstance(ex, FunctionExecutable)
        assert ex.name == "fn"
        assert ex.executor_type == "function"


class TestLoadFunction:
    def test_module_not_found(self) -> None:
        with pytest.raises(ValueError, match="Failed to import module"):
            _load_function(module="no_such_module_xyz_abc", path=None, function="foo")

    def test_attribute_not_found(self) -> None:
        with pytest.raises(ValueError, match="has no attribute"):
            _load_function(
                module="tests.unit.workflow._executable_helpers",
                path=None,
                function="nonexistent_attr",
            )

    def test_not_callable(self) -> None:
        with pytest.raises(ValueError, match="is not callable"):
            _load_function(
                module="tests.unit.workflow._executable_helpers",
                path=None,
                function="sample_non_callable",
            )

    def test_callable_returned(self) -> None:
        fn = _load_function(
            module="tests.unit.workflow._executable_helpers",
            path=None,
            function="sample_function",
        )
        assert callable(fn)
        assert fn("x") == "sample: x"

    def test_path_file_not_found(self, tmp_path: Path) -> None:
        """`path` 指定時に file が存在しないと ValueError。"""
        with pytest.raises(ValueError, match="FileNotFoundError"):
            _load_function(
                module=None,
                path=str(tmp_path / "nonexistent.py"),
                function="fn",
            )

    def test_path_attribute_not_found(self, tmp_path: Path) -> None:
        """`path` ロードに成功しても function 名が無ければ ValueError。"""
        f = tmp_path / "mod.py"
        f.write_text("def existing(x):\n    return x\n", encoding="utf-8")
        with pytest.raises(ValueError, match="has no attribute"):
            _load_function(module=None, path=str(f), function="missing")

    def test_path_not_callable(self, tmp_path: Path) -> None:
        """`path` 内に非 callable な属性しかなければ ValueError。"""
        f = tmp_path / "mod.py"
        f.write_text("VALUE = 42\n", encoding="utf-8")
        with pytest.raises(ValueError, match="is not callable"):
            _load_function(module=None, path=str(f), function="VALUE")

    def test_path_callable_returned(self, tmp_path: Path) -> None:
        """絶対 path 経由で正しく callable が取得できる正常系。"""
        f = tmp_path / "mod.py"
        f.write_text("def fn(x):\n    return f'path: {x}'\n", encoding="utf-8")
        out = _load_function(module=None, path=str(f), function="fn")
        assert callable(out)
        assert out("hello") == "path: hello"

    def test_path_module_exec_failure(self, tmp_path: Path) -> None:
        """path 経由でモジュールレベルコードが例外を出した場合に ValueError へ正規化される。

        失敗時に不完全な module オブジェクトが `sys.modules` に残らないことも確認する
        （次回 import 時にキャッシュ汚染を引き起こさないよう_load_module_from_path で
        `sys.modules.pop` している契約）。
        """
        import hashlib
        import sys as _sys

        f = tmp_path / "mod.py"
        f.write_text("raise RuntimeError('boom at import time')\n", encoding="utf-8")
        path_hash = hashlib.sha256(str(f.resolve()).encode()).hexdigest()[:16]
        module_name = f"custom_function_{path_hash}"
        _sys.modules.pop(module_name, None)  # 念のため事前クリア（並列テスト耐性）

        with pytest.raises(ValueError, match="Failed to execute module from path"):
            _load_function(module=None, path=str(f), function="fn")

        assert module_name not in _sys.modules, f"failed module '{module_name}' must be cleaned up from sys.modules"

    def test_both_module_and_path_raises(self, tmp_path: Path) -> None:
        """upstream を迂回した呼び出しで module / path 両方指定された場合、防御的に ValueError。"""
        f = tmp_path / "mod.py"
        f.write_text("def fn(x):\n    return x\n", encoding="utf-8")
        with pytest.raises(ValueError, match="mutually exclusive"):
            _load_function(module="some.module", path=str(f), function="fn")

    def test_neither_module_nor_path_raises(self) -> None:
        """upstream を迂回した呼び出しで両方 None の場合、防御的に ValueError。"""
        with pytest.raises(ValueError, match="Either 'module' or 'path'"):
            _load_function(module=None, path=None, function="fn")
