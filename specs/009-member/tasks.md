# Implementation Tasks: MixSeek-Core Member Agent バンドル（更新版）

**Branch**: `009-member`
**Feature**: MixSeek-Core Member Agent Bundle
**Generated**: 2025-10-21
**Updated**: 2025-11-20 (Phase 10: Custom Agent Dynamic Loading Implementation)
**Status**: 🎉 **ALL PHASES COMPLETED**
**Total Tasks**: 28 (Phase 7-9: 16タスク完了 + Phase 10: 12/12タスク完了)
**Completed**: 28/28 (100%)

## 更新履歴

- **2025-11-20 (v5 - Phase 10追加)**: FR-020-FR-022対応タスク追加（T075-T086）- カスタムエージェント動的ロード実装
- **2025-10-22 (v4)**: Phase 7-9完了（T056-T074）- 実装100%完了
- **2025-10-22 (v3)**: Phase 7完了（T056-T064）、Phase 8完了（T065-T071）、Phase 9完了（T072-T074）
- **2025-10-22 (v2)**: T056追加（パッケージリソース準備）- [tasks-review] #1への対応
- **2025-10-22 (v1)**: コマンド名変更（`test-member` → `member`）、`--agent`オプション実装、モデルID更新タスクを追加
- **2025-10-21**: 初回生成（56タスク）- ほぼすべて完了済み

## 実装状況サマリー

**既存実装**: ~85% 完了（56タスク中48完了）

**Phase 7-9**: ✅ **100%完了** (16/16タスク)
- ✅ 🔴 Critical: `--agent`オプション実装（9タスク）- **完了**
- ✅ 🟡 High: コマンド名変更とドキュメント更新（7タスク）- **完了**
- ✅ 🟢 Medium: モデルID更新（3タスク）- **完了**

**Phase 10**: ✅ **100%完了** (12/12タスク)
- ✅ FR-020, FR-021, FR-022: カスタムエージェント動的ロード実装（10タスク）- **完了**
- ✅ Documentation: カスタムエージェント開発ガイド（2タスク）- **完了**

---

## Phase 7: `--agent`オプション実装（Critical）

**Goal**: User Story 1のAcceptance Scenario 2, 3を満たす`--agent`フロー実装

**Article 3準拠**: テスト → 実装の順序で進める（TDD）

**重要**: T056（パッケージリソース準備）を最初に実施する必要があります。これは[tasks-review] #1への対応です。

---

### T056: [Critical] パッケージリソース準備（`__init__.py`作成）[P]

**ソース**: `feedbacks/2025-10-22-tasks-review.md` (Critical指摘 #1)
**Files**:
- `src/mixseek/configs/__init__.py`（新規作成）
- `src/mixseek/configs/agents/__init__.py`（新規作成）
- `pyproject.toml`（パッケージデータ設定追加）

**Description**: パッケージリソースとして標準エージェントTOMLを読み込むための準備を行います。`importlib.resources.files("mixseek.configs.agents")`が正常に動作するために必要です。

**Problem**:
- T059のコードは`importlib.resources.files("mixseek.configs.agents")`を使用しますが、パッケージが未整備の場合は`ModuleNotFoundError`が発生します
- `__init__.py`ファイルが存在しない場合、Pythonはディレクトリをパッケージとして認識しません

**Implementation Steps**:

1. **`src/mixseek/configs/__init__.py`作成**:
```python
"""MixSeek configuration management module.

This package contains configuration loaders, validators, and bundled
agent configurations.
"""

__all__ = ["agents"]
```

2. **`src/mixseek/configs/agents/__init__.py`作成**:
```python
"""Bundled agent configurations.

This package contains standard agent configuration TOML files that are
bundled with mixseek-core.

Standard Agents:
    - plain: Basic inference agent without tools
    - web-search: Agent with web search capabilities
    - code-exec: Agent with code execution capabilities (Anthropic Claude only)
"""

__all__ = ["plain", "web-search", "code-exec"]

# Package resource marker - この__init__.pyの存在により
# importlib.resources.files("mixseek.configs.agents") が動作可能
```

3. **`pyproject.toml`更新** - パッケージデータ設定追加:
```toml
[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
"mixseek.configs.agents" = ["*.toml"]
```

または、より簡潔に：
```toml
[tool.setuptools]
include-package-data = true

[tool.setuptools.packages.find]
where = ["src"]
```

この場合、`MANIFEST.in`も作成：
```
include src/mixseek/configs/agents/*.toml
```

**Success Criteria**:
- `src/mixseek/configs/__init__.py`が作成され、適切なdocstringを含む
- `src/mixseek/configs/agents/__init__.py`が作成され、標準エージェント一覧を記載
- `pyproject.toml`にパッケージデータ設定が追加されている
- Pythonインタプリタで以下が成功する：
  ```python
  from importlib.resources import files
  files("mixseek.configs.agents")  # ModuleNotFoundErrorが発生しない
  ```

**Article Compliance**:
- **Article 9 (Data Accuracy Mandate)**: 明示的なパッケージ定義、暗黙的な動作に依存しない
- **Article 16 (Type Safety)**: `__all__`で明示的なエクスポート定義

**Dependencies**: なし（Phase 7の最初に実行）

**Next Task**: T057（標準エージェントTOML作成）

---

### T057: [US1] 標準エージェントTOML作成（パッケージリソース）[P]
**Files**:
- `src/mixseek/configs/agents/plain.toml`
- `src/mixseek/configs/agents/web-search.toml`
- `src/mixseek/configs/agents/code-exec.toml`

**Description**: 3種類の標準エージェント設定TOMLファイルを作成します。

**Content**:

```toml
# plain.toml
[agent]
name = "plain"
type = "plain"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.7
max_tokens = 2048

[agent.instructions]
text = "あなたは親切で正確な情報を提供するアシスタントです。"

# web-search.toml
[agent]
name = "web-search"
type = "web_search"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.5
max_tokens = 4096

[agent.instructions]
text = "あなたは最新情報を検索し、正確な分析を提供するリサーチエージェントです。"

# code-exec.toml
[agent]
name = "code-exec"
type = "code_execution"
model = "anthropic:claude-haiku-4-5"
temperature = 0.1
max_tokens = 4096

[agent.instructions]
text = "あなたはデータ分析とコード実行が可能なアシスタントです。"
```

**Success Criteria**: 3つのTOMLファイルが作成され、Pydanticバリデーションを通過する

---

### T058: [US1] バンドルエージェントローダー実装テスト（TDD Red）
**File**: `tests/unit/test_bundled_agents.py`

**Description**: パッケージリソースから標準エージェントTOMLを読み込むローダーのテストを作成します。

**Test Cases**:
```python
import pytest
from pathlib import Path
from mixseek.config.bundled_agent_loader import BundledAgentLoader, BundledAgentError

class TestBundledAgentLoader:
    """Tests for bundled agent configuration loader."""

    def test_load_plain_agent_success(self):
        """Test successful loading of plain agent."""
        loader = BundledAgentLoader()
        config = loader.load("plain")

        assert config.name == "plain"
        assert config.type == "plain"
        assert "gemini-2.5-flash-lite" in config.model
        assert config.instructions.text

    def test_load_web_search_agent_success(self):
        """Test successful loading of web-search agent."""
        loader = BundledAgentLoader()
        config = loader.load("web-search")

        assert config.name == "web-search"
        assert config.type == "web_search"
        assert "gemini-2.5-flash-lite" in config.model

    def test_load_code_exec_agent_success(self):
        """Test successful loading of code-exec agent."""
        loader = BundledAgentLoader()
        config = loader.load("code-exec")

        assert config.name == "code-exec"
        assert config.type == "code_execution"
        assert "claude-haiku-4-5" in config.model

    def test_load_invalid_agent_name_error(self):
        """Test error for invalid agent name."""
        loader = BundledAgentLoader()

        with pytest.raises(BundledAgentError) as exc_info:
            loader.load("invalid-agent")

        assert "Unknown agent 'invalid-agent'" in str(exc_info.value)
        assert "Available agents:" in str(exc_info.value)

    def test_list_available_agents(self):
        """Test listing all available bundled agents."""
        loader = BundledAgentLoader()
        agents = loader.list_available()

        assert set(agents) == {"plain", "web-search", "code-exec"}
```

**Success Criteria**: テストが作成され、実行するとすべて失敗する（Red phase）

---

### T059: [US1] バンドルエージェントローダー実装（TDD Green）
**File**: `src/mixseek/config/bundled_agent_loader.py`

**Description**: パッケージリソースから標準エージェントTOMLを読み込むローダーを実装します。

**Implementation**:
```python
"""Bundled agent configuration loader.

Loads standard agent configurations bundled with mixseek-core package.
"""

import tomllib
from importlib.resources import files
from typing import Literal

from mixseek.models.member_agent import MemberAgentConfig


class BundledAgentError(Exception):
    """Raised when bundled agent loading fails."""
    pass


class BundledAgentLoader:
    """Loader for bundled standard agent configurations."""

    AVAILABLE_AGENTS: set[str] = {"plain", "web-search", "code-exec"}

    def load(self, agent_name: Literal["plain", "web-search", "code-exec"]) -> MemberAgentConfig:
        """Load bundled agent configuration.

        Args:
            agent_name: Name of bundled agent

        Returns:
            Validated agent configuration

        Raises:
            BundledAgentError: If agent not found or invalid
        """
        if agent_name not in self.AVAILABLE_AGENTS:
            available = ", ".join(sorted(self.AVAILABLE_AGENTS))
            raise BundledAgentError(
                f"Unknown agent '{agent_name}'. Available agents: {available}"
            )

        try:
            # Load from package resources
            config_text = (
                files("mixseek.configs.agents")
                .joinpath(f"{agent_name}.toml")
                .read_text(encoding="utf-8")
            )
            toml_data = tomllib.loads(config_text)

            if "agent" not in toml_data:
                raise BundledAgentError(
                    f"Invalid bundled agent '{agent_name}': missing [agent] section"
                )

            return MemberAgentConfig.model_validate(toml_data["agent"])

        except FileNotFoundError as e:
            raise BundledAgentError(
                f"Bundled agent '{agent_name}' configuration not found"
            ) from e
        except Exception as e:
            raise BundledAgentError(
                f"Failed to load bundled agent '{agent_name}': {e}"
            ) from e

    def list_available(self) -> list[str]:
        """List all available bundled agents.

        Returns:
            Sorted list of agent names
        """
        return sorted(self.AVAILABLE_AGENTS)
```

**Success Criteria**: T058のテストがすべてパスする（Green phase）

---

### T060: [US1] CLI `mixseek member` コマンド実装テスト（TDD Red）
**File**: `tests/integration/test_cli_member_command.py`

**Description**: `--agent`オプションを含むCLI統合テストを作成します。

**Test Cases**:
```python
import pytest
from typer.testing import CliRunner
from mixseek.cli.main import app

runner = CliRunner()

class TestMemberCommand:
    """Integration tests for mixseek member command."""

    def test_agent_option_plain_success(self):
        """Test --agent plain option success."""
        result = runner.invoke(
            app,
            ["member", "こんにちは", "--agent", "plain"]
        )

        assert result.exit_code == 0
        assert "⚠️" in result.stderr  # Warning message
        assert "Development/Testing only" in result.stderr

    def test_agent_option_web_search_success(self):
        """Test --agent web-search option success."""
        result = runner.invoke(
            app,
            ["member", "最新ニュース", "--agent", "web-search"]
        )

        assert result.exit_code == 0

    def test_agent_option_code_exec_success(self):
        """Test --agent code-exec option success."""
        result = runner.invoke(
            app,
            ["member", "計算してください", "--agent", "code-exec"]
        )

        assert result.exit_code == 0

    def test_agent_option_invalid_name_error(self):
        """Test error for invalid agent name."""
        result = runner.invoke(
            app,
            ["member", "test", "--agent", "invalid"]
        )

        assert result.exit_code == 1
        assert "Unknown agent 'invalid'" in result.stderr
        assert "Available agents: " in result.stderr

    def test_mutually_exclusive_config_and_agent(self):
        """Test that --config and --agent are mutually exclusive."""
        result = runner.invoke(
            app,
            ["member", "test", "--config", "test.toml", "--agent", "plain"]
        )

        assert result.exit_code == 1
        assert "mutually exclusive" in result.stderr.lower()

    def test_neither_config_nor_agent_error(self):
        """Test error when neither --config nor --agent specified."""
        result = runner.invoke(
            app,
            ["member", "test"]
        )

        assert result.exit_code == 1
        assert "Either --config or --agent must be specified" in result.stderr
```

**Success Criteria**: テストが作成され、実行するとすべて失敗する（Red phase）

---

### T061: [US1] CLI `mixseek member` コマンド実装（TDD Green）
**Files**:
- `src/mixseek/cli/commands/test_member.py` → `src/mixseek/cli/commands/member.py`
- `src/mixseek/cli/main.py`

**Description**: `--agent`オプションを実装し、コマンド名を変更します。

**Implementation Steps**:

1. **ファイル名変更とインポート更新**:
```bash
# Git で追跡しながらリネーム
git mv src/mixseek/cli/commands/test_member.py src/mixseek/cli/commands/member.py
```

2. **member.pyの修正**:
```python
# src/mixseek/cli/commands/member.py

from mixseek.config.bundled_agent_loader import BundledAgentLoader, BundledAgentError

def member(  # 関数名を test_member から member へ変更
    prompt: str = typer.Argument(..., help="Prompt to send to agent"),
    config: Path | None = typer.Option(None, "--config", help="TOML config file path"),
    agent: str | None = typer.Option(None, "--agent", help="Bundled agent name (plain, web-search, code-exec)"),
    verbose: bool = typer.Option(False, "--verbose"),
    output_format: str = typer.Option("structured", "--format"),
) -> None:
    """Test Member Agent functionality (development/testing only).

    Examples:
        mixseek member "質問" --config custom.toml
        mixseek member "質問" --agent plain
    """
    # 警告表示
    show_development_warning()  # 既存関数

    # 相互排他チェック
    if not config and not agent:
        typer.echo("Error: Either --config or --agent must be specified", err=True)
        raise typer.Exit(1)

    if config and agent:
        typer.echo("Error: --config and --agent are mutually exclusive", err=True)
        raise typer.Exit(1)

    # 設定ファイルパス決定
    if config:
        config_path = config
    else:
        # --agent オプション: バンドルエージェントを読み込む
        try:
            loader = BundledAgentLoader()
            bundled_config = loader.load(agent)

            # 一時的にメモリ上の設定を使用
            # （または一時ファイルに書き出す）
            # ここでは execute_agent を修正して MemberAgentConfig を直接受け取る
            result = asyncio.run(execute_agent_from_config(bundled_config, prompt, verbose))
            # ... 結果表示
            return

        except BundledAgentError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)

    # 既存の --config フロー
    result = asyncio.run(execute_agent(config_path, prompt, verbose))
    # ...
```

3. **main.pyの更新**:
```python
# src/mixseek/cli/main.py

from mixseek.cli.commands.member import member  # test_member から member へ

app = typer.Typer(...)

app.command(name="member")(member)  # "test-member" から "member" へ
```

**Success Criteria**: T060のテストがすべてパスする（Green phase）

---

### T062: [US1] CLIユーティリティモジュール作成 [P]
**File**: `src/mixseek/cli/utils.py`

**Description**: 共通CLI機能を集約したユーティリティモジュールを作成します（Article 10 DRY準拠）。

**Implementation**:
```python
"""CLI utility functions and constants."""
from typing import Any, TypeVar
import typer
from rich.console import Console

# 終了コード定数
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_USAGE_ERROR = 2
EXIT_INTERRUPT = 130

# グローバルConsole
console = Console()
err_console = Console(stderr=True)

T = TypeVar('T')

def mutually_exclusive_group(group_size: int = 2) -> Any:
    """Create callback for mutually exclusive options.

    Args:
        group_size: Maximum number of options in group

    Returns:
        Callback function for typer.Option
    """
    group: set[str] = set()

    def callback(
        ctx: typer.Context,
        param: typer.CallbackParam,
        value: T | None
    ) -> T | None:
        if value is not None and param.name is not None:
            if len(group) + 1 > group_size:
                existing = ", ".join(f"--{name}" for name in group)
                raise typer.BadParameter(
                    f"'{param.name}' is mutually exclusive with {existing}"
                )
            group.add(param.name)
        return value

    return callback
```

**Success Criteria**: モジュールが作成され、mypyとruffを通過する

---

### T063: [US1] CLI Member コマンドのコントラクトテスト作成（TDD Red）[P]
**File**: `tests/contract/test_member_contract.py`

**Description**: CLIコマンドのコントラクトテストを作成します。

**Test Cases**:
```python
"""Contract tests for mixseek member CLI command."""
import pytest
from typer.testing import CliRunner
from mixseek.cli.main import app

runner = CliRunner()

class TestMemberCommandContract:
    """Contract tests for member command interface."""

    def test_command_exists(self):
        """Test that member command is registered."""
        result = runner.invoke(app, ["--help"])
        assert "member" in result.stdout

    def test_requires_prompt_argument(self):
        """Test that prompt argument is required."""
        result = runner.invoke(app, ["member"])
        assert result.exit_code != 0

    def test_supports_config_option(self):
        """Test that --config option is supported."""
        result = runner.invoke(app, ["member", "--help"])
        assert "--config" in result.stdout

    def test_supports_agent_option(self):
        """Test that --agent option is supported."""
        result = runner.invoke(app, ["member", "--help"])
        assert "--agent" in result.stdout

    def test_supports_verbose_option(self):
        """Test that --verbose option is supported."""
        result = runner.invoke(app, ["member", "--help"])
        assert "--verbose" in result.stdout

    def test_supports_format_option(self):
        """Test that --format option is supported."""
        result = runner.invoke(app, ["member", "--help"])
        assert "--format" in result.stdout

    def test_displays_development_warning(self):
        """Test that development warning is displayed."""
        # モックを使用してAPI呼び出しをスキップ
        result = runner.invoke(app, ["member", "test", "--agent", "plain"])
        assert "Development/Testing only" in result.stderr or "⚠️" in result.stderr
```

**Success Criteria**: テストが作成され、実行すると失敗する（Red phase）

---

### T064: [US1] CLI Member コマンドの完全実装とリファクタリング（TDD Refactor）
**File**: `src/mixseek/cli/commands/member.py`

**Description**: T061の実装を洗練し、cli/utils.pyを活用してコード品質を向上させます。

**Refactoring**:
```python
"""Member Agent CLI command."""
import asyncio
from pathlib import Path
import typer

from mixseek.cli.utils import (
    EXIT_SUCCESS,
    EXIT_ERROR,
    EXIT_INTERRUPT,
    console,
    err_console,
    mutually_exclusive_group
)
from mixseek.config.bundled_agent_loader import BundledAgentLoader, BundledAgentError
from mixseek.cli.formatters import ResultFormatter

exclusivity = mutually_exclusive_group(group_size=1)

def member(
    prompt: str = typer.Argument(...),
    config: Path | None = typer.Option(None, "--config", callback=exclusivity),
    agent: str | None = typer.Option(None, "--agent", callback=exclusivity),
    verbose: bool = typer.Option(False, "--verbose"),
    output_format: str = typer.Option("structured", "--format"),
) -> None:
    """Test Member Agent (development/testing only)."""

    # 警告 → stderr
    err_console.print("⚠️  Development/Testing only - Not for production use")

    # 少なくとも1つ必須
    if not any([config, agent]):
        raise typer.BadParameter("Either --config or --agent must be specified")

    try:
        if agent:
            loader = BundledAgentLoader()
            bundled_config = loader.load(agent)
            result = asyncio.run(execute_agent_from_config(bundled_config, prompt))
        else:
            result = asyncio.run(execute_agent_from_path(config, prompt))

        display_result(result, output_format, verbose)
        raise typer.Exit(EXIT_SUCCESS)

    except BundledAgentError as e:
        err_console.print(f"[red]{e}[/red]")
        raise typer.Exit(EXIT_ERROR)
    except KeyboardInterrupt:
        err_console.print("\n⚠️  Interrupted by user")
        raise typer.Exit(EXIT_INTERRUPT)
```

**Success Criteria**: すべてのテスト（T058, T060, T063）がパスし、ruff + mypyを通過する

---

## Phase 8: ドキュメント更新（High Priority）

**Goal**: コマンド名変更をすべてのLiving Documentsに反映

### T065: [DOC] quickstart.md更新
**File**: `specs/009-member/quickstart.md`

**Description**: コマンド例を `mixseek test-member` → `mixseek member` へ更新します。

**Changes**:
- すべてのコマンド例を更新
- `--agent`オプション使用例を追加
- 出力例を最新の警告メッセージに合わせる

**Success Criteria**: ドキュメント内のすべてのコマンド例が正しい

---

### T066: [DOC] docs/member-agents.md更新
**File**: `docs/member-agents.md`

**Description**: メインドキュメントのコマンド例を更新します。

**Changes**:
- コマンド名を `member` へ更新
- `--agent`オプションのセクションを追加
- 標準エージェント（plain, web-search, code-exec）の説明を追加

**Success Criteria**: ユーザー向けドキュメントが最新の仕様に準拠

---

### T067: [DOC] contracts/cli_interface.py更新 [P]
**File**: `specs/009-member/contracts/cli_interface.py`

**Description**: CLIインターフェース仕様を更新します。

**Changes**:
- コマンド名を `member` へ更新
- `--agent`オプションの仕様を追加
- 相互排他性の契約を明記

**Success Criteria**: 契約定義が実装と一致

---

### T068: [DOC] examples/README_Vertex_AI.md更新 [P]
**File**: `examples/README_Vertex_AI.md`

**Description**: 使用例ドキュメントを更新します。

**Changes**:
- コマンド例を `mixseek member` へ更新
- Vertex AI環境での実行例を更新

**Success Criteria**: 使用例が実行可能

---

### T069: [DOC] research.md更新 [P]
**File**: `specs/009-member/research.md`

**Description**: リサーチドキュメントのコマンド例を更新します。

**Changes**:
- コマンド例を `mixseek member` へ更新
- モデルIDを `gemini-2.5-flash-lite` へ更新

**Success Criteria**: ドキュメントの一貫性確保

---

### T070: [DOC] data-model.md更新 [P]
**File**: `specs/009-member/data-model.md`

**Description**: データモデルドキュメントの参照を更新します。

**Changes**:
- コマンド例を更新
- モデルID例を更新

**Success Criteria**: データモデル定義が最新

---

### T071: [DOC] tasks.md更新（本ファイル）
**File**: `specs/009-member/tasks.md`

**Description**: 本タスクファイルを新しいタスクリストで上書きします。

**Success Criteria**: タスク定義が最新の実装計画に準拠

---

## Phase 9: モデルID更新（Medium Priority）

**Goal**: Gemini 1.5 Flash → Gemini 2.0 Flash Liteへの更新

### T072: [UPDATE] Agent実装のモデルID更新 [P]
**Files**:
- `src/mixseek/agents/plain.py`
- `src/mixseek/agents/web_search.py`
- `src/mixseek/agents/code_execution.py`

**Description**: デフォルトモデルIDやコメント内の参照を更新します。

**Changes**:
```bash
# 全置換（レビュー推奨）
grep -r "gemini-1.5-flash" src/mixseek/agents/
# → gemini-2.5-flash-lite へ置換
```

**Success Criteria**: すべてのAgent実装で最新モデルIDを使用

---

### T073: [UPDATE] テストコードのモデルID更新 [P]
**Files**:
- `tests/unit/test_*.py`
- `tests/integration/test_*.py`

**Description**: テスト内のモデルID参照を更新します。

**Success Criteria**: すべてのテストがパスし、最新モデルIDを使用

---

### T074: [UPDATE] 標準エージェントTOMLの最終検証
**Files**:
- `src/mixseek/configs/agents/plain.toml`
- `src/mixseek/configs/agents/web-search.toml`
- `src/mixseek/configs/agents/code-exec.toml`

**Description**: 作成済みTOMLファイルのモデルIDが正しいことを確認します。

**Validation**:
- plain: `google-gla:gemini-2.5-flash-lite` ✓
- web-search: `google-gla:gemini-2.5-flash-lite` ✓
- code-exec: `anthropic:claude-haiku-4-5` ✓

**Success Criteria**: すべてのTOMLが最新モデルIDを使用し、バリデーションを通過

---

## Dependencies & Execution Order

### Critical Path

```
Phase 7: --agent実装（Critical）
├─ T056: パッケージリソース準備（__init__.py作成）[P] ⚠️ 最優先
    ↓
├─ T057: 標準TOML作成 [P]
├─ T058: ローダーテスト作成 [P]
└─ T059: ローダー実装（T056依存）
    ↓
├─ T060: CLIテスト作成 [P]
└─ T061: CLI実装（test_member→member）
    ↓
├─ T062: CLIユーティリティ作成 [P]
└─ T064: CLI Refactoring
    ↓
└─ T063: コントラクトテスト [P]

Phase 8: ドキュメント更新（High - 並行可能）
├─ T065: quickstart.md [P]
├─ T066: docs/member-agents.md [P]
├─ T067: contracts/cli_interface.py [P]
├─ T068: examples/README_Vertex_AI.md [P]
├─ T069: research.md [P]
├─ T070: data-model.md [P]
└─ T071: tasks.md

Phase 9: モデルID更新（Medium - 並行可能）
├─ T072: Agent実装更新 [P]
├─ T073: テストコード更新 [P]
└─ T074: TOML検証 [P]
```

### User Story Mapping

| Task | User Story | Type | 並行可能 |
|------|-----------|------|----------|
| T056 | US1 | Setup | ✅ [P] ⚠️ 最優先 |
| T057 | US1 | Setup | ✅ [P] |
| T058 | US1 | Test | ✅ [P] |
| T059 | US1 | Implementation | ❌ (T056, T058依存) |
| T060 | US1 | Test | ✅ [P] |
| T061 | US1 | Implementation | ❌ (T059依存) |
| T062 | US1 | Utility | ✅ [P] |
| T063 | US1 | Test | ✅ [P] |
| T064 | US1 | Refactoring | ❌ (T061依存) |
| T065-T071 | All | Documentation | ✅ [P] |
| T072-T074 | All | Update | ✅ [P] |

### Parallel Execution Example

**Phase 7の並行実行**:
```bash
# ステップ0: 最優先タスク（必ず最初に実行）
T056 (パッケージリソース準備)

# ステップ1: 並行実行可能なタスク（T056完了後）
T057 (TOML作成) & T058 (ローダーテスト) & T062 (CLIユーティリティ) を並行実行

# ステップ2: T058完了後
T059 (ローダー実装) & T060 (CLIテスト) を実行

# ステップ3: T059, T060完了後
T061 (CLI実装) を実行

# ステップ4: T061完了後
T063 (コントラクトテスト) & T064 (Refactoring) を並行実行
```

**Phase 8の並行実行**:
```bash
# すべてのドキュメント更新を並行実行
T065 & T066 & T067 & T068 & T069 & T070 を同時実行
→ T071 (tasks.md) を最後に実行
```

---

## Testing Strategy

### Test Levels

本タスクリストでは**Article 3 (Test-First)に準拠**してテストを作成します：

1. **Unit Tests** (T058):
   - BundledAgentLoaderの単体テスト
   - パッケージリソース読み込み検証

2. **Integration Tests** (T060):
   - CLI全体の統合テスト
   - `--agent`オプションの動作検証
   - 相互排他性のテスト

3. **Contract Tests** (T063):
   - CLIインターフェース契約の検証
   - オプション・引数の存在確認

### Test Execution

```bash
# Unit tests
pytest tests/unit/test_bundled_agents.py -v

# Integration tests
pytest tests/integration/test_cli_member_command.py -v

# Contract tests
pytest tests/contract/test_member_contract.py -v

# すべて実行
pytest tests/ -v -m "not e2e"
```

---

## Implementation Notes

### Article 3 (Test-First) Compliance

すべての実装タスクは対応するテストタスクの**後**に配置されています：

- T058 (Test) → T059 (Implementation)
- T060 (Test) → T061 (Implementation)
- T063 (Test) → T064 (Refactoring)

### Article 4 (Documentation Integrity) Compliance

Phase 8でドキュメント更新を完了してから、本番デプロイを行います。

### Article 10 (DRY Principle) Compliance

- CLIユーティリティ（T062）で共通機能を集約
- 既存実装（85%）を最大限活用
- 重複コード削減

---

## Summary

### タスク統計

- **Total Tasks**: 16（新規追加）
- **Critical Tasks**: 9（Phase 7: `--agent`実装、T056-T064）
- **Documentation Tasks**: 7（Phase 8: ドキュメント更新）
- **Update Tasks**: 3（Phase 9: モデルID更新）

### 並行実行機会

- **Phase 7**: T056完了後、3タスク並行可能（T057, T058, T062）
- **Phase 8**: 6タスク並行可能（T065-T070）
- **Phase 9**: 3タスク並行可能（T072-T074）

### MVP Scope

**Minimum Viable Product** (User Story 1完全実装):
- Phase 7タスクすべて（T056-T064）⚠️ T056が最優先
- Phase 8の最低限のドキュメント（T065, T066）

**推奨実装順序**:
1. **T056（最優先）**: パッケージリソース準備
2. Phase 7: `--agent`実装（Critical）
3. Phase 8: Living Documents更新（High）
4. Phase 9: モデルID更新（Medium）

### Critical課題への対応

**[tasks-review] #1への対応**:
- ✅ T056追加により、パッケージ化手順不足を解決
- `__init__.py`ファイル作成手順を明示
- `pyproject.toml`更新手順を明示
- `ModuleNotFoundError`の防止を保証

---

---

## Phase 10: カスタムエージェント動的ロード実装（FR-020, FR-021, FR-022）

**Goal**: カスタムMember Agent（`type = "custom"`）の動的ロード機構実装

**Requirements**:
- FR-020: 動的ロード機構（agent_module推奨、path代替）
- FR-021: ロード優先順位処理（agent_module → path フォールバック）
- FR-022: エラーハンドリング（詳細なエラーメッセージ + 推奨対処方法）

**Article 3準拠**: テスト → 実装 → リファクタリング → ドキュメントの順序で進める（TDD）

**Status**: 🔴 **未実装**

---

### T075: [Test] dynamic_loader単体テスト作成（agent_module方式）[P]

**File**: `tests/unit/test_dynamic_loader.py`（新規作成）

**Description**: `load_agent_from_module()`のユニットテストを作成します（Article 3 Test-First準拠）。

**Implementation Steps**:

1. **テストクラス`TestLoadAgentFromModule`作成**:
```python
import pytest
from mixseek.agents.member.dynamic_loader import load_agent_from_module
from mixseek.models.member_agent import MemberAgentConfig

class TestLoadAgentFromModule:
    """agent_module方式のテスト"""

    def test_module_not_found_error(self, mock_config):
        """ModuleNotFoundErrorのエラーメッセージ検証"""
        with pytest.raises(ModuleNotFoundError) as exc_info:
            load_agent_from_module(
                agent_module="nonexistent_package.agents.custom",
                agent_class="CustomAgent",
                config=mock_config
            )
        assert "Failed to load custom agent from module" in str(exc_info.value)
        assert "Install package: pip install" in str(exc_info.value)

    def test_class_not_found_error(self):
        """AttributeErrorのエラーメッセージ検証"""
        # TODO: 存在するモジュール、存在しないクラス
        pass

    def test_not_inherit_base_agent_error(self):
        """BaseMemberAgent非継承のTypeError検証"""
        # TODO: BaseMemberAgentを継承しないクラス
        pass
```

2. **fixtureの準備**:
```python
@pytest.fixture
def mock_config():
    """モック設定"""
    return MemberAgentConfig(
        name="Test Agent",
        type="custom",
        # ... その他の必須フィールド
    )
```

**AC (Acceptance Criteria)**:
- [X] `test_module_not_found_error`が実装されている
- [X] エラーメッセージに「Failed to load」「Install package」が含まれる検証
- [X] pytest実行でRed（失敗）になることを確認（実装前）

**Dependencies**: なし

**Estimated Effort**: 1h

**Status**: ✅ **COMPLETED** (2025-11-20)

---

### T076: [Test] dynamic_loader単体テスト作成（path方式）[P]

**File**: `tests/unit/test_dynamic_loader.py`（継続）

**Description**: `load_agent_from_path()`のユニットテストを作成します。

**Implementation Steps**:

1. **テストクラス`TestLoadAgentFromPath`作成**:
```python
class TestLoadAgentFromPath:
    """path方式のテスト"""

    def test_file_not_found_error(self, mock_config):
        """FileNotFoundErrorのエラーメッセージ検証"""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_agent_from_path(
                path="/nonexistent/path/custom_agent.py",
                agent_class="CustomAgent",
                config=mock_config
            )
        assert "Failed to load custom agent from path" in str(exc_info.value)
        assert "Check file path in TOML config" in str(exc_info.value)

    def test_class_not_found_in_file_error(self, tmp_path):
        """AttributeErrorのエラーメッセージ検証"""
        # TODO: クラスが存在しないPyファイル
        pass

    def test_load_valid_file(self, tmp_path):
        """正常なファイルロード"""
        # TODO: 一時ファイルにカスタムエージェント作成
        pass
```

**AC**:
- [ ] `test_file_not_found_error`が実装されている
- [ ] エラーメッセージに「Failed to load」「Check file path」が含まれる検証
- [ ] pytest実行でRed（失敗）になることを確認

**Dependencies**: T075

**Estimated Effort**: 1h

**Status**: ✅ **COMPLETED** (2025-11-20)

---

### T077: [Test] ファクトリ優先順位処理テスト作成（FR-021）[P]

**File**: `tests/unit/test_factory_custom_loading.py`（新規作成）

**Description**: `MemberAgentFactory._load_custom_agent()`の優先順位処理をテストします。

**Implementation Steps**:

1. **テストクラス作成**:
```python
import pytest
from mixseek.agents.member.factory import MemberAgentFactory
from mixseek.models.member_agent import MemberAgentConfig

class TestCustomAgentPriorityHandling:
    """FR-021優先順位処理のテスト"""

    def test_agent_module_priority(self):
        """agent_moduleとpath両方指定時、agent_moduleが優先される"""
        # TODO: agent_moduleを優先的にロード
        pass

    def test_fallback_to_path(self):
        """agent_module失敗時、pathフォールバック"""
        # TODO: agent_module失敗 → path成功
        pass

    def test_neither_specified_error(self):
        """agent_module/path両方未指定時のエラー"""
        # モックconfig作成（pluginセクションなし）
        with pytest.raises(ValueError) as exc_info:
            MemberAgentFactory.create_agent(mock_config_custom_no_plugin)
        assert "must specify either 'agent_module' or 'path'" in str(exc_info.value)
```

**AC**:
- [ ] 優先順位テストが実装されている
- [ ] フォールバックテストが実装されている
- [ ] 未指定エラーテストが実装されている

**Dependencies**: T075, T076

**Estimated Effort**: 1h

**Status**: ✅ **COMPLETED** (2025-11-20)

---

### T078: [Test] インテグレーションテスト作成（E2E）[I]

**File**: `tests/integration/test_custom_agent_loading.py`（新規作成）

**Description**: カスタムエージェントのE2Eテスト（ロード → execute()実行）を作成します。

**Implementation Steps**:

1. **テストクラス作成**:
```python
import pytest
from pathlib import Path
from mixseek.agents.member.factory import MemberAgentFactory
from mixseek.config.member_agent_loader import load_member_agent_config

class TestCustomAgentE2E:
    """カスタムエージェントのE2Eテスト"""

    @pytest.mark.integration
    def test_load_from_module_and_execute(self, tmp_path):
        """agent_module方式でロード → execute()実行"""
        # TODO: モックパッケージ作成 → TOML作成 → ロード → execute()
        pass

    @pytest.mark.integration
    def test_load_from_path_and_execute(self, tmp_path):
        """path方式でロード → execute()実行"""
        # TODO: カスタムエージェント.py作成 → TOML作成 → ロード → execute()
        pass
```

**AC**:
- [ ] agent_module方式のE2Eテストが実装されている
- [ ] path方式のE2Eテストが実装されている
- [ ] `@pytest.mark.integration`マーカーが付与されている

**Dependencies**: T075, T076, T077

**Estimated Effort**: 1h

**Status**: ✅ **COMPLETED** (2025-11-20)

---

### T079: [Implementation] dynamic_loader実装（agent_module方式）[P]

**File**: `src/mixseek/agents/member/dynamic_loader.py`（新規作成）

**Description**: `load_agent_from_module()`を実装します（FR-020）。

**Implementation Steps**:

1. **ファイル作成とインポート**:
```python
"""Dynamic loading utilities for custom Member Agents.

This module provides functions to dynamically load custom agent classes
from Python modules or file paths.
"""

import importlib
from typing import Type

from mixseek.agents.member.base import BaseMemberAgent
from mixseek.models.member_agent import MemberAgentConfig
```

2. **`load_agent_from_module()`実装**:
```python
def load_agent_from_module(
    agent_module: str,
    agent_class: str,
    config: MemberAgentConfig
) -> BaseMemberAgent:
    """Pythonモジュールパスからカスタムエージェントクラスをロード

    Args:
        agent_module: モジュールパス（例: "my_package.agents.custom"）
        agent_class: クラス名（例: "MyCustomAgent"）
        config: エージェント設定

    Returns:
        インスタンス化されたカスタムエージェント

    Raises:
        ModuleNotFoundError: モジュールが見つからない
        AttributeError: クラスが見つからない
        TypeError: BaseMemberAgentを継承していない
    """
    try:
        module = importlib.import_module(agent_module)
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError(
            f"Error: Failed to load custom agent from module '{agent_module}'. "
            f"ModuleNotFoundError: {e}. "
            f"Install package: pip install <package-name>"
        ) from e

    try:
        cls: Type[BaseMemberAgent] = getattr(module, agent_class)
    except AttributeError as e:
        raise AttributeError(
            f"Error: Custom agent class '{agent_class}' not found in module '{agent_module}'. "
            f"Check agent_class in TOML config."
        ) from e

    if not issubclass(cls, BaseMemberAgent):
        raise TypeError(
            f"Error: Custom agent class '{agent_class}' must inherit from BaseMemberAgent."
        )

    return cls(config)
```

**AC**:
- [ ] `load_agent_from_module()`が実装されている
- [ ] FR-022準拠のエラーメッセージが実装されている
- [ ] T075のテストがGreen（成功）になる
- [ ] Article 16準拠: 型注釈が完備されている

**Dependencies**: T075

**Estimated Effort**: 1h

**Status**: ✅ **COMPLETED** (2025-11-20)

---

### T080: [Implementation] dynamic_loader実装（path方式）[P]

**File**: `src/mixseek/agents/member/dynamic_loader.py`（継続）

**Description**: `load_agent_from_path()`を実装します（FR-020）。

**Implementation Steps**:

1. **追加インポート**:
```python
import importlib.util
import sys
from pathlib import Path
```

2. **`load_agent_from_path()`実装**:
```python
def load_agent_from_path(
    path: str,
    agent_class: str,
    config: MemberAgentConfig
) -> BaseMemberAgent:
    """ファイルパスからカスタムエージェントクラスをロード

    Args:
        path: ファイルパス（例: "/path/to/custom_agent.py"）
        agent_class: クラス名（例: "MyCustomAgent"）
        config: エージェント設定

    Returns:
        インスタンス化されたカスタムエージェント

    Raises:
        FileNotFoundError: ファイルが見つからない
        AttributeError: クラスが見つからない
        TypeError: BaseMemberAgentを継承していない
    """
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(
            f"Error: Failed to load custom agent from path '{path}'. "
            f"FileNotFoundError: File not found. "
            f"Check file path in TOML config."
        )

    spec = importlib.util.spec_from_file_location("custom_agent", path_obj)
    if spec is None or spec.loader is None:
        raise ImportError(
            f"Error: Failed to create module spec from path '{path}'."
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules["custom_agent"] = module
    spec.loader.exec_module(module)

    try:
        cls: Type[BaseMemberAgent] = getattr(module, agent_class)
    except AttributeError as e:
        raise AttributeError(
            f"Error: Custom agent class '{agent_class}' not found in file '{path}'. "
            f"Check agent_class in TOML config."
        ) from e

    if not issubclass(cls, BaseMemberAgent):
        raise TypeError(
            f"Error: Custom agent class '{agent_class}' must inherit from BaseMemberAgent."
        )

    return cls(config)
```

**AC**:
- [ ] `load_agent_from_path()`が実装されている
- [ ] FR-022準拠のエラーメッセージが実装されている
- [ ] T076のテストがGreen（成功）になる
- [ ] Article 16準拠: 型注釈が完備されている

**Dependencies**: T076, T079

**Estimated Effort**: 1h

**Status**: ✅ **COMPLETED** (2025-11-20)

---

### T081: [Implementation] PluginMetadataモデル更新[P]

**File**: `src/mixseek/models/member_agent.py`（既存ファイル更新）

**Description**: `PluginMetadata` Pydanticモデルを追加/更新します。

**Implementation Steps**:

1. **Pydanticモデル追加**:
```python
from pydantic import BaseModel, Field
from typing import Optional

class PluginMetadata(BaseModel):
    """カスタムエージェントプラグイン情報"""

    agent_module: Optional[str] = Field(
        None,
        description="Pythonモジュールパス（例: 'my_package.agents.custom'）"
    )
    path: Optional[str] = Field(
        None,
        description="ファイルパス（例: '/path/to/custom_agent.py'）"
    )
    agent_class: str = Field(
        ...,
        description="エージェントクラス名（例: 'MyCustomAgent'）"
    )
```

2. **MemberAgentConfigモデル更新**（既存）:
```python
class MemberAgentConfig(BaseModel):
    # ... 既存フィールド

    class Metadata(BaseModel):
        plugin: Optional[PluginMetadata] = None
        # ... その他のメタデータ
```

**AC**:
- [ ] `PluginMetadata`モデルが追加されている
- [ ] `agent_module`, `path`, `agent_class`フィールドが定義されている
- [ ] Article 16準拠: 型注釈が完備されている
- [ ] mypy検査がパスする

**Dependencies**: なし

**Estimated Effort**: 1h

**Status**: ✅ **COMPLETED** (2025-11-20)

---

### T082: [Implementation] ファクトリ優先順位処理実装（FR-021）[P]

**File**: `src/mixseek/agents/member/factory.py`（既存ファイル更新）

**Description**: `MemberAgentFactory`にカスタムエージェントロード機能を追加します。

**Implementation Steps**:

1. **インポート追加**:
```python
from mixseek.agents.member.dynamic_loader import load_agent_from_module, load_agent_from_path
```

2. **`_load_custom_agent()`メソッド追加**:
```python
@classmethod
def _load_custom_agent(cls, config: MemberAgentConfig) -> BaseMemberAgent:
    """カスタムエージェントの動的ロード（FR-021優先順位処理）

    Priority:
        1. agent_module（推奨）
        2. path（代替）

    Args:
        config: エージェント設定

    Returns:
        インスタンス化されたカスタムエージェント

    Raises:
        ValueError: agent_module/path両方未指定
        ModuleNotFoundError: agent_moduleロード失敗
        FileNotFoundError: pathロード失敗
    """
    plugin = config.metadata.plugin
    if plugin is None:
        raise ValueError(
            "Error: Custom agent must have [agent.metadata.plugin] section. "
            "Check TOML config."
        )

    # 第1優先: agent_module
    if plugin.agent_module is not None:
        try:
            agent = load_agent_from_module(
                agent_module=plugin.agent_module,
                agent_class=plugin.agent_class,
                config=config
            )
            # 成功時は登録して返す
            cls.register_agent(config.type, type(agent))
            return agent
        except (ModuleNotFoundError, AttributeError, TypeError) as e:
            # pathフォールバックを試行
            if plugin.path is None:
                raise
            # ログ記録（警告レベル）
            import logging
            logging.getLogger(__name__).warning(
                f"Failed to load from agent_module '{plugin.agent_module}', "
                f"falling back to path '{plugin.path}': {e}"
            )

    # 第2優先: path
    if plugin.path is not None:
        agent = load_agent_from_path(
            path=plugin.path,
            agent_class=plugin.agent_class,
            config=config
        )
        cls.register_agent(config.type, type(agent))
        return agent

    # どちらも未指定
    raise ValueError(
        "Error: Custom agent must specify either 'agent_module' or 'path' "
        "in [agent.metadata.plugin] section. Check TOML config."
    )
```

3. **`create_agent()`メソッド更新**:
```python
@classmethod
def create_agent(cls, config: MemberAgentConfig) -> BaseMemberAgent:
    """Create agent instance based on configuration.

    # ... 既存docstring
    """
    agent_type = config.type

    # カスタムエージェント: 動的ロード
    if agent_type == "custom":
        return cls._load_custom_agent(config)

    # 標準エージェント: 既存の辞書ルックアップ
    agent_class = cls._agent_classes.get(agent_type)
    if not agent_class:
        available_types = list(cls._agent_classes.keys())
        raise ValueError(
            f"Unsupported agent type: {agent_type}. "
            f"Available types: {available_types}"
        )

    # ... 既存の実装（emit_agent_created_event等）
```

**AC**:
- [ ] `_load_custom_agent()`が実装されている
- [ ] FR-021の優先順位処理が実装されている
- [ ] `register_agent()`が呼び出されている
- [ ] T077のテストがGreen（成功）になる
- [ ] T078のE2EテストがGreen（成功）になる

**Dependencies**: T077, T079, T080, T081

**Estimated Effort**: 1h

**Status**: ✅ **COMPLETED** (2025-11-20)

---

### T083: [Refactor] エラーメッセージ一貫性確認[P]

**Files**:
- `src/mixseek/agents/member/dynamic_loader.py`
- `src/mixseek/agents/member/factory.py`

**Description**: FR-022準拠のエラーメッセージが一貫しているか確認し、必要に応じて調整します。

**Verification Checklist**:
- [ ] すべてのエラーメッセージが「Error:」で始まる
- [ ] ロード方式（agent_module/path）が明記されている
- [ ] 試行したパス/モジュール名が含まれている
- [ ] 失敗原因が明示されている
- [ ] 推奨対処方法が含まれている

**AC**:
- [ ] エラーメッセージが一貫している
- [ ] FR-022要件を満たしている

**Dependencies**: T082

**Estimated Effort**: 1h

**Status**: ✅ **COMPLETED** (2025-11-20)

---

### T084: [Refactor] コード品質チェック実行[P]

**Description**: Article 8準拠のコード品質チェックを実行します。

**Implementation Steps**:

1. **Ruffチェック実行**:
```bash
ruff check src/mixseek/agents/member/dynamic_loader.py src/mixseek/agents/member/factory.py
ruff check tests/unit/test_dynamic_loader.py tests/unit/test_factory_custom_loading.py
```

2. **Ruffフォーマット実行**:
```bash
ruff format src/mixseek/agents/member/ tests/unit/ tests/integration/
```

3. **mypy型チェック実行**:
```bash
mypy src/mixseek/agents/member/dynamic_loader.py
mypy src/mixseek/agents/member/factory.py
```

**AC**:
- [ ] Ruffチェックがパスする
- [ ] Ruffフォーマットが適用されている
- [ ] mypy型チェックがパスする（Article 16準拠）
- [ ] すべてのテストがパスする

**Dependencies**: T083

**Estimated Effort**: 1h

**Status**: ✅ **COMPLETED** (2025-11-20)

---

### T085: [Documentation] カスタムエージェント開発ガイド追加[D]

**File**: `docs/member-agents.md`（既存ファイル更新）

**Description**: カスタムエージェント開発ガイドセクションを追加します。

**Implementation Steps**:

1. **新規セクション追加**:
```markdown
## カスタムエージェント開発ガイド

### 概要

mixseek-coreでは、`type = "custom"`を指定することで独自のMember Agentを開発・統合できます。

### 実装方法

#### Option A: agent_module方式（推奨）

本番環境・SDKとしての配布に適しています。

**1. カスタムエージェントクラス作成**:

\```python
# my_analytics_package/agents/data_analyst.py
from mixseek.agents.member.base import BaseMemberAgent
from mixseek.models.member_agent import MemberAgentConfig, MemberAgentResult

class DataAnalystAgent(BaseMemberAgent):
    """データ分析専門のカスタムエージェント"""

    async def execute(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        **kwargs: Any
    ) -> MemberAgentResult:
        # 実装
        ...
\```

**2. TOML設定**:

\```toml
[agent]
name = "データ分析エージェント"
type = "custom"
description = "Pandas/NumPyを使ったデータ分析専門エージェント"

[agent.metadata.plugin]
agent_module = "my_analytics_package.agents.data_analyst"
agent_class = "DataAnalystAgent"
\```

**3. パッケージインストール**:
\```bash
pip install my-analytics-package
\```

#### Option B: path方式（代替）

開発プロトタイピング・スタンドアロンファイルに適しています。

**1. カスタムエージェントファイル作成**:

\```python
# /path/to/custom_agents/data_analyst.py
# ... 同様の実装
\```

**2. TOML設定**:

\```toml
[agent]
name = "データ分析エージェント"
type = "custom"
description = "Pandas/NumPyを使ったデータ分析専門エージェント"

[agent.metadata.plugin]
path = "/path/to/custom_agents/data_analyst.py"
agent_class = "DataAnalystAgent"
\```

### 動的ロード優先順位

1. **第1優先**: `agent_module`が指定されている場合、モジュールインポートを試行
2. **第2優先**: `agent_module`が未指定または失敗した場合、`path`からのロードを試行

### エラーハンドリング

（FR-022のエラーメッセージ例を含める）
```

**AC**:
- [X] カスタムエージェント開発ガイドが追加されている
- [X] agent_module方式とpath方式の両方が説明されている
- [X] サンプルコードが含まれている
- [X] 優先順位処理が説明されている

**Dependencies**: T084

**Estimated Effort**: 1.5h

**Status**: ✅ **COMPLETED** (2025-11-20)

---

### T086: [Documentation] クイックスタートに使用例追加[D]

**File**: `specs/009-member/quickstart.md`（既存ファイル更新）

**Description**: カスタムエージェントの使用例をクイックスタートガイドに追加します。

**Implementation Steps**:

1. **新規セクション追加**:
```markdown
## カスタムエージェントの使用

### agent_module方式

\```bash
# パッケージインストール
pip install my-analytics-package

# カスタムエージェント設定
cat > custom-data-analyst.toml <<EOF
[agent]
name = "データ分析エージェント"
type = "custom"
description = "Pandas/NumPyを使ったデータ分析専門エージェント"

[agent.metadata.plugin]
agent_module = "my_analytics_package.agents.data_analyst"
agent_class = "DataAnalystAgent"
EOF

# 実行
mixseek member "売上データを分析してください" --config custom-data-analyst.toml
\```

### path方式

\```bash
# カスタムエージェント設定
cat > custom-data-analyst.toml <<EOF
[agent]
name = "データ分析エージェント"
type = "custom"
description = "Pandas/NumPyを使ったデータ分析専門エージェント"

[agent.metadata.plugin]
path = "/path/to/custom_agents/data_analyst.py"
agent_class = "DataAnalystAgent"
EOF

# 実行
mixseek member "売上データを分析してください" --config custom-data-analyst.toml
\```
```

**AC**:
- [X] カスタムエージェント使用例が追加されている
- [X] agent_module方式とpath方式の両方が含まれている
- [X] 実行可能なコマンド例が含まれている

**Dependencies**: T084

**Estimated Effort**: 1h

**Status**: ✅ **COMPLETED** (2025-11-20)

---

## Summary (Phase 10追加後)

### タスク統計（更新）

- **Total Tasks**: 28（Phase 7-9: 16タスク + Phase 10: 12タスク）
- **Phase 10 Tasks**: 12（動的ロード実装）
  - Test Tasks: 4（T075-T078）
  - Implementation Tasks: 4（T079-T082）
  - Refactor Tasks: 2（T083-T084）
  - Documentation Tasks: 2（T085-T086）

### Phase 10タスク依存関係

```
T075 (agent_module test) ─→ T079 (agent_module impl) ─┐
T076 (path test)        ─→ T080 (path impl)        ─┤
T077 (priority test)    ───────────────────────────┼─→ T082 (factory impl) ─→ T083 (refactor) ─→ T084 (quality) ─┬→ T085 (docs)
T078 (E2E test)         ───────────────────────────┘                                                              └→ T086 (quickstart)
                              T081 (model) ─────────┘
```

### 並行実行機会（Phase 10）

1. **並行グループ1**: T075, T076, T077, T078, T081（5タスク同時実行可能）
2. **並行グループ2**: T079, T080（T075/T076完了後、2タスク同時実行可能）
3. **並行グループ3**: T085, T086（T084完了後、2タスク同時実行可能）

### MVP Scope（Phase 10）

**Minimum Viable Product**:
- T075-T082（テスト + 実装）
- T084（品質チェック）

**推奨実装順序**:
1. Phase 1 (Test Creation): T075-T078 + T081
2. Phase 2 (Implementation): T079-T082
3. Phase 3 (Refactor): T083-T084
4. Phase 4 (Documentation): T085-T086

### Constitution準拠（Phase 10）

- **Article 3 (Test-First)**: ✅ テスト作成（T075-T078） → 実装（T079-T082）の順序
- **Article 9 (Data Accuracy)**: ✅ 明示的エラーハンドリング（FR-022準拠）
- **Article 10 (DRY)**: ✅ `dynamic_loader.py`で共通ロジック集約
- **Article 16 (Type Safety)**: ✅ すべての関数に型注釈付与、mypy検証（T084）

---

**タスク生成完了**: 2025-10-22
**Phase 10追加**: 2025-11-20（FR-020, FR-021, FR-022対応）
**最終更新**: 2025-11-20 (v3 - Phase 10追加)
**Total Tasks**: 28
**Article 3準拠**: ✅ Test-First順序
**Article 4準拠**: ✅ ドキュメント整合性
**Article 9準拠**: ✅ 明示的エラーハンドリング
**準備完了**: ✅ 実装可能
