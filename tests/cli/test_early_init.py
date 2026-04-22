"""mixseek.cli._early_init のユニットテスト。

early_init は CLI 起動の最上段で呼ばれるため、logfire 等の import 副作用を
回避する配置制約と、モード別の差し替え挙動が主要な検証対象となる。
"""

from __future__ import annotations

import importlib
import io
import json
import sys
import warnings
from collections.abc import Generator
from typing import Any

import pytest

MODULE_NAME = "mixseek.cli._early_init"


@pytest.fixture
def fresh_module(monkeypatch: pytest.MonkeyPatch) -> Generator[Any]:
    """early_init モジュールをクリーンな状態で再 import するためのフィクスチャ。

    ``_installed`` / ``_original_showwarning`` のモジュール状態をテスト間で
    リセットするため、毎回 ``sys.modules`` から除去して再 import する。
    併せて環境変数と ``warnings.showwarning`` の元値を退避/復元する。
    """
    original_showwarning = warnings.showwarning
    monkeypatch.delenv("MIXSEEK_LOG_FORMAT", raising=False)
    if MODULE_NAME in sys.modules:
        del sys.modules[MODULE_NAME]
    module = importlib.import_module(MODULE_NAME)
    try:
        yield module
    finally:
        warnings.showwarning = original_showwarning
        if MODULE_NAME in sys.modules:
            del sys.modules[MODULE_NAME]


class TestShowwarningJsonMode:
    """MIXSEEK_LOG_FORMAT=json 時の showwarning 差し替え"""

    def test_replaces_showwarning_in_json_mode(self, fresh_module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        """json モードでは showwarning が差し替わる"""
        monkeypatch.setenv("MIXSEEK_LOG_FORMAT", "json")
        original = warnings.showwarning
        fresh_module.install_early_stderr_hooks()
        assert warnings.showwarning is not original
        assert warnings.showwarning is fresh_module._json_showwarning

    def test_keeps_showwarning_in_text_mode(self, fresh_module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        """text モード (未設定) では showwarning は差し替えられない"""
        monkeypatch.delenv("MIXSEEK_LOG_FORMAT", raising=False)
        original = warnings.showwarning
        fresh_module.install_early_stderr_hooks()
        assert warnings.showwarning is original

    def test_keeps_showwarning_when_format_is_text(self, fresh_module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        """MIXSEEK_LOG_FORMAT="text" でも差し替えない"""
        monkeypatch.setenv("MIXSEEK_LOG_FORMAT", "text")
        original = warnings.showwarning
        fresh_module.install_early_stderr_hooks()
        assert warnings.showwarning is original

    def test_json_mode_is_case_insensitive(self, fresh_module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        """MIXSEEK_LOG_FORMAT は大文字小文字を無視する"""
        monkeypatch.setenv("MIXSEEK_LOG_FORMAT", "JSON")
        fresh_module.install_early_stderr_hooks()
        assert warnings.showwarning is fresh_module._json_showwarning


class TestJsonShowwarningOutput:
    """_json_showwarning の出力スキーマ"""

    def test_emits_json_with_schema_fields(self, fresh_module: Any) -> None:
        """必須スキーマキーが全て含まれる 1 行 JSON を出力"""
        buf = io.StringIO()
        fresh_module._json_showwarning(
            "hello",
            UserWarning,
            "foo.py",
            42,
            buf,
            None,
        )
        line = buf.getvalue().strip()
        entry = json.loads(line)
        assert entry["type"] == "warning"
        assert entry["level"] == "WARNING"
        assert entry["category"] == "UserWarning"
        assert entry["filename"] == "foo.py"
        assert entry["lineno"] == 42
        assert entry["message"] == "hello"
        assert "timestamp" in entry

    def test_writes_to_stderr_when_file_is_none(
        self, fresh_module: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """file 引数が None の場合は stderr に出力"""
        fresh_module._json_showwarning(
            "stderr test",
            UserWarning,
            "bar.py",
            1,
            None,
            None,
        )
        captured = capsys.readouterr()
        assert captured.out == ""
        entry = json.loads(captured.err.strip())
        assert entry["message"] == "stderr test"

    def test_warning_message_str_conversion(self, fresh_module: Any) -> None:
        """Warning インスタンス (str ではない) も str() 経由で格納される"""
        buf = io.StringIO()
        warning_obj = DeprecationWarning("deprecated feature")
        fresh_module._json_showwarning(
            warning_obj,
            DeprecationWarning,
            "x.py",
            10,
            buf,
            None,
        )
        entry = json.loads(buf.getvalue().strip())
        assert entry["message"] == "deprecated feature"
        assert entry["category"] == "DeprecationWarning"

    def test_end_to_end_via_warnings_warn(
        self, fresh_module: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """json モード install 後、``warnings.warn()`` 呼び出しが JSON 化される"""
        monkeypatch.setenv("MIXSEEK_LOG_FORMAT", "json")
        fresh_module.install_early_stderr_hooks()
        # 同一メッセージの再発火抑止 (warning filter) を回避
        warnings.simplefilter("always")
        warnings.warn("e2e warning", UserWarning, stacklevel=1)
        captured = capsys.readouterr()
        entry = json.loads(captured.err.strip())
        assert entry["type"] == "warning"
        assert entry["message"] == "e2e warning"
        assert entry["category"] == "UserWarning"


class TestIdempotency:
    """install_early_stderr_hooks() の冪等性"""

    def test_multiple_calls_do_not_stack(self, fresh_module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        """json モードで 2 回呼んでも showwarning は 1 度しか差し替えられない"""
        monkeypatch.setenv("MIXSEEK_LOG_FORMAT", "json")
        fresh_module.install_early_stderr_hooks()
        first_showwarning = warnings.showwarning
        fresh_module.install_early_stderr_hooks()
        second_showwarning = warnings.showwarning
        assert first_showwarning is second_showwarning


class TestImportSafety:
    """配置場所の制約: logfire を間接 import しない"""

    def test_import_does_not_load_logfire(self) -> None:
        """``mixseek.cli._early_init`` の import で logfire が読み込まれないこと。

        この性質が崩れると LOGFIRE_IGNORE_NO_CONFIG の setdefault が
        logfire import より後になり、LogfireNotConfiguredWarning の抑止が
        機能しなくなる (回帰防止用のガードテスト)。
        """
        # 既に別テストで logfire が読み込まれている可能性があるため、一度 purge する
        for m in list(sys.modules):
            if m.startswith("logfire") or m.startswith("mixseek"):
                del sys.modules[m]
        importlib.import_module(MODULE_NAME)
        loaded_mixseek = sorted(m for m in sys.modules if m.startswith("mixseek"))
        assert "logfire" not in sys.modules, f"logfire was eager-imported; mixseek modules loaded: {loaded_mixseek}"
        # 許容される親パッケージ以外は読み込まれていないこと
        assert loaded_mixseek == ["mixseek", "mixseek.cli", "mixseek.cli._early_init"]
