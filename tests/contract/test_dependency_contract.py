"""依存宣言の契約テスト

src/mixseek がモジュールレベルで import するサードパーティパッケージは、
pyproject.toml の [project] dependencies または optional-dependencies に宣言されていなければならない。

他パッケージの推移的依存に頼った import は、上流の依存変更で突然 ModuleNotFoundError になる。
例: typer 0.26.0 で click がベンダリング化されて依存から外れ、`import click` が失敗した。
"""

import ast
import importlib.metadata
import re
import sys
import tomllib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = PROJECT_ROOT / "src" / "mixseek"

# 宣言せずに import してよいモジュール
ALLOWED_UNDECLARED_MODULES = frozenset(
    {
        # pydantic が同一バージョンに固定して必須依存にしており、pydantic と一体で提供される
        "pydantic_core",
    }
)


def _normalize(name: str) -> str:
    """ディストリビューション名を PEP 503 に従って正規化する"""
    return re.sub(r"[-_.]+", "-", name).lower()


def _declared_distributions() -> set[str]:
    """pyproject.toml の dependencies と optional-dependencies に宣言されたディストリビューション名"""
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    requirements: list[str] = list(project["dependencies"])
    for extra_requirements in project.get("optional-dependencies", {}).values():
        requirements.extend(extra_requirements)

    names = set()
    for requirement in requirements:
        match = re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", requirement)
        assert match is not None, f"依存指定を解釈できません: {requirement}"
        names.add(_normalize(match.group()))
    return names


class _ModuleLevelImportCollector(ast.NodeVisitor):
    """モジュール読み込み時に実行される import のトップレベルモジュール名を収集する

    関数内の遅延 import（任意機能向け）と `if TYPE_CHECKING:` ブロックは対象外とする。
    """

    def __init__(self) -> None:
        self.modules: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        self.modules.update(alias.name.split(".")[0] for alias in node.names)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level == 0 and node.module is not None:
            self.modules.add(node.module.split(".")[0])

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """関数内の import は遅延 import のため辿らない"""

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """関数内の import は遅延 import のため辿らない"""

    def visit_If(self, node: ast.If) -> None:
        test = node.test
        is_type_checking = (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
            isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
        )
        if not is_type_checking:
            self.generic_visit(node)
            return
        for statement in node.orelse:
            self.visit(statement)


@pytest.mark.contract
def test_module_level_third_party_imports_are_declared() -> None:
    """モジュールレベルで import するサードパーティパッケージが依存として宣言されている"""
    declared = _declared_distributions()
    module_to_distributions = importlib.metadata.packages_distributions()

    undeclared: dict[str, list[str]] = {}
    for path in sorted(PACKAGE_DIR.rglob("*.py")):
        collector = _ModuleLevelImportCollector()
        collector.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        for module in sorted(collector.modules):
            if module in sys.stdlib_module_names or module == "mixseek" or module in ALLOWED_UNDECLARED_MODULES:
                continue
            # 未インストールの場合は import 名とディストリビューション名が一致するとみなす
            distributions = {_normalize(name) for name in module_to_distributions.get(module, [module])}
            if declared.isdisjoint(distributions):
                undeclared.setdefault(module, []).append(str(path.relative_to(PROJECT_ROOT)))

    assert not undeclared, (
        "pyproject.toml に宣言されていないサードパーティパッケージを import しています。"
        f"推移的依存に頼らず dependencies に宣言してください: {undeclared}"
    )
