"""インストール済みの mixseek-core が動作するかを検証する

開発環境や CI の Docker イメージには dev グループと [ui] extra が入っているため、
他パッケージ経由で入るモジュールに隠れて、コア依存だけでインストールしたときの
import 失敗に気付けない (例: 8a9ef15 以降、[ui] extra なしでは jinja2 が入らなかった)。

検証対象の環境の Python で、リポジトリのルートから実行する:

    # uv.lock のコア依存のみ
    UV_PROJECT_ENVIRONMENT=/tmp/core uv sync --locked --no-dev --no-editable
    /tmp/core/bin/python -I scripts/check_install.py

    # 最新の依存 (pip install mixseek-core と同じ解決)
    uv build --wheel --out-dir /tmp/dist
    uv venv /tmp/latest && uv pip install --python /tmp/latest/bin/python /tmp/dist/*.whl
    /tmp/latest/bin/python -I scripts/check_install.py

検証対象の環境に dev 依存を入れると欠けた依存を隠してしまうため、標準ライブラリだけで書く。
"""

import importlib
import importlib.util
import shutil
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

PACKAGE_NAME = "mixseek"
CONSOLE_SCRIPT = "mixseek"
# [ui] extra (streamlit) が必要なため、コア依存のみの環境では検証しない
EXCLUDED_PACKAGES = ("mixseek.ui",)


def list_module_names(package_dir: Path, package_name: str, excluded: Iterable[str]) -> list[str]:
    """パッケージ配下の全モジュール名を返す (除外したパッケージ配下と __main__ は含まない)"""
    excluded_prefixes = tuple(excluded)
    names = []
    for path in package_dir.rglob("*.py"):
        parts = path.relative_to(package_dir).with_suffix("").parts
        if parts[-1] == "__main__":
            continue
        if parts[-1] == "__init__":
            parts = parts[:-1]
        name = ".".join((package_name, *parts))
        if any(name == prefix or name.startswith(f"{prefix}.") for prefix in excluded_prefixes):
            continue
        names.append(name)
    return sorted(names)


def find_import_failures(module_names: Iterable[str]) -> dict[str, str]:
    """各モジュールを import し、失敗したモジュールと理由 (例外の型とメッセージ) を返す"""
    failures = {}
    for name in module_names:
        try:
            importlib.import_module(name)
        except Exception as error:
            failures[name] = f"{type(error).__name__}: {error}"
    return failures


def check_console_script(script: Path | None) -> str | None:
    """コンソールスクリプトの --help が成功するかを確認し、失敗時はその内容を返す"""
    if script is None:
        return f"コンソールスクリプト {CONSOLE_SCRIPT} が見つかりません"
    result = subprocess.run([str(script), "--help"], capture_output=True, text=True, timeout=120, check=False)
    if result.returncode == 0:
        return None
    output = (result.stderr or result.stdout).strip()
    return f"{script.name} --help が終了コード {result.returncode} で失敗しました:\n{output}"


def _find_console_script() -> Path | None:
    """検証対象の環境 (実行中の Python と同じディレクトリ) にあるコンソールスクリプトを探す"""
    found = shutil.which(CONSOLE_SCRIPT, path=str(Path(sys.executable).parent))
    return Path(found) if found else None


def main() -> int:
    spec = importlib.util.find_spec(PACKAGE_NAME)
    if spec is None or not spec.submodule_search_locations:
        print(f"{PACKAGE_NAME} がインストールされていません")
        return 1

    package_dir = Path(next(iter(spec.submodule_search_locations)))
    module_names = list_module_names(package_dir, PACKAGE_NAME, EXCLUDED_PACKAGES)
    failures = find_import_failures(module_names)
    console_error = check_console_script(_find_console_script())

    print(f"検証対象: {sys.prefix}")
    print(f"import: {len(module_names)} モジュール中 {len(failures)} 件失敗")
    # 1 つの欠けた依存で多数のモジュールが失敗するため、理由ごとにまとめて表示する
    names_by_reason: dict[str, list[str]] = {}
    for name, reason in failures.items():
        names_by_reason.setdefault(reason, []).append(name)
    for reason, names in names_by_reason.items():
        print(f"  {reason}")
        for name in names:
            print(f"    - {name}")
    print(f"CLI: {console_error or f'{CONSOLE_SCRIPT} --help 成功'}")
    return 1 if failures or console_error else 0


if __name__ == "__main__":
    sys.exit(main())
