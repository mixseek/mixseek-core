"""scripts/check_install.py (インストール検証スクリプト) のテスト"""

import stat
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from scripts.check_install import check_console_script, find_import_failures, list_module_names

PACKAGE = "fake_install_check_pkg"


@pytest.fixture
def fake_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """import できるモジュール・依存が欠けたモジュール・除外対象を含む偽パッケージ"""
    package_dir = tmp_path / PACKAGE
    (package_dir / "ui").mkdir(parents=True)
    (package_dir / "__init__.py").write_text("")
    (package_dir / "__main__.py").write_text("raise SystemExit('__main__ は import しない')\n")
    (package_dir / "ok.py").write_text("VALUE = 1\n")
    (package_dir / "broken.py").write_text("import not_installed_dependency_for_test\n")
    (package_dir / "ui" / "__init__.py").write_text("raise RuntimeError('除外対象は import しない')\n")
    (package_dir / "ui" / "page.py").write_text("raise RuntimeError('除外対象は import しない')\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    yield package_dir
    for name in [name for name in sys.modules if name == PACKAGE or name.startswith(f"{PACKAGE}.")]:
        del sys.modules[name]


def _write_script(path: Path, body: str) -> Path:
    """実行可能なシェルスクリプトを作成する"""
    path.write_text(f"#!/bin/sh\n{body}\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


@pytest.mark.unit
def test_list_module_names_skips_excluded_packages(fake_package: Path) -> None:
    """除外したパッケージ配下と __main__ を除き、パッケージ自身を含む全モジュール名を返す"""
    names = list_module_names(fake_package, PACKAGE, excluded=[f"{PACKAGE}.ui"])

    assert names == [PACKAGE, f"{PACKAGE}.broken", f"{PACKAGE}.ok"]


@pytest.mark.unit
def test_find_import_failures_reports_missing_dependency(fake_package: Path) -> None:
    """依存が欠けて import できないモジュールだけを、理由付きで返す"""
    failures = find_import_failures([PACKAGE, f"{PACKAGE}.ok", f"{PACKAGE}.broken"])

    assert failures == {
        f"{PACKAGE}.broken": "ModuleNotFoundError: No module named 'not_installed_dependency_for_test'",
    }


@pytest.mark.unit
def test_check_console_script_succeeds(tmp_path: Path) -> None:
    """--help が終了コード 0 なら問題なし (None) を返す"""
    script = _write_script(tmp_path / "mixseek", "exit 0")

    assert check_console_script(script) is None


@pytest.mark.unit
def test_check_console_script_reports_failure(tmp_path: Path) -> None:
    """--help が失敗したら、終了コードとエラー出力を返す"""
    script = _write_script(tmp_path / "mixseek", "echo \"ModuleNotFoundError: No module named 'click'\" >&2; exit 1")

    error = check_console_script(script)

    assert error is not None
    assert "終了コード 1" in error
    assert "No module named 'click'" in error


@pytest.mark.unit
def test_check_console_script_reports_missing_script() -> None:
    """コンソールスクリプトが見つからなければエラーを返す"""
    error = check_console_script(None)

    assert error is not None
    assert "見つかりません" in error
