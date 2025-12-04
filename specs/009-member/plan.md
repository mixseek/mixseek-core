# Implementation Plan: MixSeek-Core Member Agent バンドル

**Branch**: `009-member` | **Date**: 2025-10-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/009-member/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

mixseek-coreにバンドルされる3種類の標準Member Agent（plain, web-search, code-exec）を実装します。各エージェントはPydantic AIフレームワークを基盤とし、Google AI（Gemini 2.0 Flash Lite）およびAnthropic Claude（Haiku 4.5）をサポートします。開発・テスト専用の`mixseek member`コマンドを提供し、TOML設定ファイルによるカスタマイズを可能にします。

## Technical Context

**Language/Version**: Python 3.13.9
**Primary Dependencies**:
  - Pydantic AI >= 0.0.8（コアフレームワーク - すべてのプロバイダーSDKを含む）
    - 自動的に含まれる: google-genai, anthropic, openai
  - google-cloud-aiplatform >= 1.40.0（Vertex AI用 - 別途必要）
  - Typer >= 0.9.0（CLIフレームワーク）
  - tomllib（Python 3.13.9標準ライブラリ - TOML読み込み）
  - Pydantic Settings >= 2.0.0（環境変数統合）

**Storage**:
  - パッケージリソース（標準エージェントTOML: `mixseek_core/configs/agents/*.toml`）
  - ログファイル（`~/.mixseek/logs/member-agent-{date}.log`）

**Testing**: pytest >= 8.3.4（unit, integration, e2eマーカー使用）

**Target Platform**: Linux/macOS/Windows（Python環境）、開発・テスト用途専用

**Project Type**: Single project（mixseek-coreパッケージの一部）

**Performance Goals**:
  - エージェント起動: 30秒以内
  - 平均応答時間: 5秒以内
  - Web検索機能: 90%以上の関連性
  - コード実行機能: 95%以上の精度

**Constraints**:
  - 開発・テスト専用（本番利用は禁止）
  - Google AI/Vertex AI: `plain`, `web-search`のみ
  - Anthropic Claude: `code-exec`専用（他プロバイダー不可）
  - コード実行セキュリティ: Anthropic側で制御（設定不可）

**Scale/Scope**:
  - 3種類の標準エージェント
  - パッケージ内バンドル（mixseek_core/configs/agents/）
  - CLIコマンド1つ（`mixseek member`）

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Article 1: Library-First Principle ✅ PASS
本機能はmixseek-coreパッケージの一部として実装され、スタンドアロンライブラリとして機能します。

### Article 2: CLI Interface Mandate ✅ PASS
`mixseek member` CLIコマンドを提供し、stdin/stdout/stderrをサポートします。JSON出力にも対応予定。

### Article 3: Test-First Imperative ✅ PASS
TDD手法に従い、実装前にテストを作成します。ユニット、インテグレーション、E2Eテストを含みます。

### Article 4: Documentation Integrity ✅ PASS
仕様書（spec.md）との完全な整合性を保ちます。本plan.mdで仕様を参照し、実装前に確認を行います。

### Article 5: Simplicity ✅ PASS
Single project構造（mixseek-coreパッケージの一部）で、3プロジェクト制限内です。

### Article 6: Anti-Abstraction ✅ PASS
Pydantic AIフレームワークの機能を直接使用し、不必要なラッパーは作成しません。

### Article 7: Integration-First Testing ✅ PASS
実際のAI APIを使用したインテグレーションテストを優先します（e2eマーカー使用）。

### Article 8: Code Quality Standards ✅ PASS
コミット前に `ruff check --fix . && ruff format . && mypy .` を必須実行します。

### Article 9: Data Accuracy Mandate ✅ PASS
環境変数（GOOGLE_API_KEY, ANTHROPIC_API_KEY等）から認証情報を取得し、ハードコード・暗黙的フォールバックを禁止します。

### Article 10: DRY Principle ✅ PASS
実装前に既存コードを検索し、重複を避けます。標準エージェント設定はパッケージリソースとして一元管理します。

### Article 11: Refactoring Policy ✅ PASS
V2クラス作成を避け、既存コードの直接修正を優先します。

### Article 12: Documentation Standards ✅ PASS
`docs/` ディレクトリでMarkdown形式のドキュメントを管理します。

### Article 13: Environment & Infrastructure ✅ PASS
開発環境はDockerコンテナで構築されます（既存のmixseek-core環境を使用）。

### Article 14: SpecKit Framework Consistency ✅ PASS
**CRITICAL**: 本機能はspecs/001-specs/spec.mdのMember Agent要件（FR-005）に完全準拠します：
- BaseMemberAgentインターフェース実装
- Pydantic AI Toolsetを通じたLeader Agentからの呼び出し
- システム標準Member Agentとして mixseek-core パッケージにバンドル

### Article 15: SpecKit Naming Convention ✅ PASS
ディレクトリ名 `009-member` は命名規則に準拠しています。

### Article 16: Python Type Safety Mandate ✅ PASS
すべてのコードに包括的な型注釈を付与し、mypyストリクトモードで検証します。

### Article 17: Python Docstring Standards ✅ PASS (推奨)
Google-style docstringを使用してすべてのpublic APIにドキュメントを提供します。

**GATE STATUS**: ✅ **PASS** - すべての憲法要件を満たしています。Phase 0リサーチに進みます。

## Project Structure

### Documentation (this feature)

```
specs/009-member/
├── plan.md              # This file (/speckit.plan output) ✅
├── research.md          # Phase 0 output (既存) ✅
├── data-model.md        # Phase 1 output (既存) ✅
├── quickstart.md        # Phase 1 output (既存) ✅
├── contracts/           # Phase 1 output (既存) ✅
│   ├── BaseMemberAgent.py  # Member Agent protocol definition
│   └── MemberAgentResult.py  # Result schema
├── tasks.md             # Phase 2 output (既存) ✅
├── findings/            # 技術調査結果
│   ├── README.md
│   ├── 2025-10-21-authentication-system-overhaul.md
│   ├── 2025-10-21-code-execution-provider-compatibility.md
│   └── 2025-10-21-pydantic-ai-tool-initialization-patterns.md
└── checklists/          # コンプライアンスチェックリスト
    └── constitutional-compliance.md
```

### Source Code (repository root)

本機能はmixseek-coreパッケージの一部として実装されます（Single project構造）。

```
src/mixseek/
├── agents/                    # Member Agent実装
│   ├── __init__.py
│   ├── plain.py              # PlainMemberAgent（既存 ✅）
│   ├── web_search.py         # WebSearchMemberAgent（既存 ✅）
│   └── code_execution.py     # CodeExecutionMemberAgent（既存 ✅）
├── core/                      # コアモジュール
│   ├── __init__.py
│   └── auth.py               # マルチプロバイダー認証（既存 ✅）
├── models/                    # Pydanticモデル
│   ├── __init__.py
│   └── member_agent.py       # MemberAgentConfig, Result（既存 ✅）
├── config/                    # 設定管理
│   ├── __init__.py
│   ├── member_agent_loader.py  # 設定ローダー（既存 ✅）
│   ├── templates.py          # テンプレート生成（既存 ✅）
│   └── validators.py         # 設定バリデーション（既存 ✅）
├── cli/                       # CLIコマンド
│   ├── __init__.py
│   ├── main.py               # メインエントリーポイント（既存 ✅）
│   ├── formatters.py         # 出力フォーマッター（既存 ✅）
│   ├── utils.py              # 📝 CLIユーティリティ（新規作成）
│   └── commands/
│       ├── __init__.py
│       ├── init.py           # mixseek initコマンド（既存 ✅）
│       ├── test_member.py    # 📝 → member.py へリネーム予定
│       └── member.py         # 📝 新規作成（test_member.pyからリネーム）
└── configs/                   # パッケージ内設定ファイル
    └── agents/                # 標準エージェント設定
        ├── plain.toml         # 📝 新規作成（Gemini 2.0 Flash Lite）
        ├── web-search.toml    # 📝 新規作成（Gemini 2.0 Flash Lite）
        └── code-exec.toml     # 📝 新規作成（Claude Haiku 4.5）

tests/
├── unit/                      # ユニットテスト
│   ├── test_auth.py          # 認証テスト（既存 ✅・31テスト）
│   ├── test_plain_agent.py   # PlainAgentテスト（既存 ✅）
│   ├── test_web_search_agent.py  # WebSearchAgentテスト（既存 ✅）
│   ├── test_code_execution_agent.py  # CodeExecAgentテスト（既存 ✅）
│   ├── test_member_agent_config.py  # 設定テスト（既存 ✅）
│   ├── test_validators.py    # バリデーションテスト（既存 ✅）
│   └── 📝 test_bundled_agents.py  # 新規作成（--agentフロー）
├── integration/               # インテグレーションテスト
│   ├── test_member_agent_integration.py  # Agent統合テスト（既存 ✅）
│   └── 📝 test_cli_member_command.py  # 新規作成（CLI統合テスト）
├── contract/                  # コントラクトテスト
│   ├── test_init_contract.py  # initコマンド（既存 ✅）
│   └── 📝 test_member_contract.py  # 新規作成（memberコマンド）
├── cli/                       # CLIテスト
│   └── （既存ファイル構造確認中）
├── agents/                    # Agentテスト
│   └── （既存ファイル構造確認中）
└── （その他のディレクトリ）
```

**凡例**:
- ✅ 既存・実装済み
- 📝 新規作成予定
- ⚠️ 要更新


**Structure Decision**:

本機能はmixseek-coreパッケージの一部として実装されるため、既存のSingle project構造を使用します。

**既存実装の確認結果**:

実装の大部分が既に完成しています（Article 10 DRY Principle準拠）：

✅ **既存実装（完成済み）**:
1. **Agents**:
   - `src/mixseek/agents/plain.py` - PlainMemberAgent実装済み
   - `src/mixseek/agents/web_search.py` - WebSearchMemberAgent実装済み
   - `src/mixseek/agents/code_execution.py` - CodeExecutionMemberAgent実装済み
   - `src/mixseek/agents/base.py` - BaseMemberAgent抽象基底クラス
   - `src/mixseek/agents/factory.py` - MemberAgentFactory実装済み

2. **Core/Auth**:
   - `src/mixseek/core/auth.py` - マルチプロバイダー認証システム（Article 9準拠）
   - Google AI, Vertex AI, OpenAI, Anthropic Claude対応
   - 明示的エラーハンドリング実装済み

3. **Config**:
   - `src/mixseek/config/member_agent_loader.py` - 設定ローダー実装済み
   - `src/mixseek/config/validators.py` - 設定バリデーション実装済み
   - `src/mixseek/config/templates.py` - テンプレート生成実装済み

4. **Models**:
   - `src/mixseek/models/member_agent.py` - MemberAgentConfig, MemberAgentResult
   - Pydantic v2による完全な型安全性実装済み

5. **CLI**:
   - `src/mixseek/cli/commands/test_member.py` - `mixseek test-member`コマンド実装済み
   - `src/mixseek/cli/formatters.py` - 出力フォーマッター実装済み
   - `src/mixseek/cli/main.py` - メインエントリーポイント

6. **Tests**:
   - `tests/unit/test_auth.py` - 31テストケース（認証システム）
   - 包括的なテストカバレッジ

📝 **未実装/作成予定**（重要度順）:

**🔴 Critical - 機能要件を満たすために必須**:

1. **`--agent` オプション実装**（Acceptance Scenario 2, 3を満たすため）:
   - `src/mixseek/config/bundled_agent_loader.py` - パッケージリソースから標準TOML読み込み
   - `src/mixseek/cli/commands/test_member.py` (line 101-106) - `--agent`実装追加
   - **理由**: 現在は「未実装エラー」で終了。US1/US2のAcceptance Criteriaを満たせない

2. **標準エージェントTOMLバンドル**（`--agent`の前提条件）:
   - `src/mixseek/configs/agents/plain.toml` - Gemini 2.0 Flash Lite設定
   - `src/mixseek/configs/agents/web-search.toml` - Gemini 2.0 Flash Lite設定
   - `src/mixseek/configs/agents/code-exec.toml` - Claude Haiku 4.5設定
   - **理由**: `--agent plain`等の実行に必要

3. **`--agent`フローのテスト作成**（Article 3 Test-First準拠）:
   - `tests/unit/test_bundled_agents.py` - パッケージリソース読み込みテスト
   - `tests/integration/test_cli_member_command.py` - `--agent`成功/失敗パステスト
   - `tests/contract/test_member_contract.py` - CLIコントラクトテスト
   - **理由**: TDD準拠、実装前にテスト作成必須

**🟡 High - コマンド名変更関連**:

4. **CLIコマンド名変更**:
   - `src/mixseek/cli/commands/test_member.py` → `member.py` へファイル名変更
   - 関数名 `test_member()` → `member()` へ変更
   - `src/mixseek/cli/main.py` - コマンド登録を `test-member` → `member` へ更新
   - **理由**: 仕様変更（spec.md）に準拠

5. **CLIユーティリティ作成**:
   - `src/mixseek/cli/utils.py` - mutually_exclusive_group(), EXIT_* 定数
   - **理由**: コード再利用、Article 10 DRY準拠

**🟢 Medium - モデルID更新**:

6. **モデルID更新**（既存コード内）:
   - `gemini-1.5-flash` → `gemini-2.5-flash-lite` 全置換
   - 影響ファイル: agents/*.py, configs/agents/*.toml, tests/*.py
   - **理由**: Gemini 1.5 Flash廃止、仕様変更

**実装状況サマリー**:
- 実装済み: ~85%（`--agent`フロー未実装を考慮）
- 残作業:
  - **Critical**: `--agent`実装 + テスト作成（Article 3準拠）
  - **High**: コマンド名変更 + ドキュメント更新（19ファイル）
  - **Medium**: モデルID更新

---

## Documentation Update Requirements

### コマンド名変更の影響範囲

`mixseek test-member` → `mixseek member` への変更により、以下のファイルの更新が必要です：

#### 📝 Specification & Planning Documents
1. ✅ `specs/009-member/spec.md` - 仕様書（既に更新済み）
2. ✅ `specs/009-member/plan.md` - 実装計画（本ファイル、更新済み）
3. ⚠️ `specs/009-member/quickstart.md` - クイックスタート（要更新）
4. ⚠️ `specs/009-member/research.md` - リサーチ（要更新）
5. ⚠️ `specs/009-member/tasks.md` - タスク定義（要更新）
6. ⚠️ `specs/009-member/data-model.md` - データモデル（要更新）

#### 📚 Main Documentation
7. ⚠️ `docs/member-agents.md` - Member Agentドキュメント（要更新）

#### 💻 Source Code
8. ⚠️ `src/mixseek/cli/commands/test_member.py` - CLIコマンド実装
   - ファイル名変更: `test_member.py` → `member.py`
   - 関数名変更: `test_member()` → `member()`
   - docstring更新
9. ⚠️ `src/mixseek/cli/main.py` - メインエントリーポイント
   - コマンド登録更新

#### 📋 Contracts & Examples
10. ⚠️ `specs/009-member/contracts/cli_interface.py` - CLIインターフェース仕様（要更新）
11. ⚠️ `examples/README_Vertex_AI.md` - 使用例（要更新）

#### 🔍 Findings & Feedback
12. ⚠️ `specs/009-member/findings/2025-10-21-code-execution-provider-compatibility.md`（要更新）
13. ⚠️ `specs/009-member/findings/2025-10-21-pydantic-ai-tool-initialization-patterns.md`（要更新）
14. ⚠️ `specs/009-member/feedbacks/*.md`（4ファイル、要確認・更新）

#### 📊 DRY Analysis Documents
15. ⚠️ `specs/009-member/DRY-*.md`（3ファイル、要確認・更新）

### 更新優先順位とポリシー

#### Living Documents（常に最新に保つ）

**P0 (Critical - 機能に直接影響)**:
1. `src/mixseek/cli/commands/test_member.py` → `member.py`
2. `src/mixseek/cli/main.py`
3. `specs/009-member/quickstart.md`
4. `docs/member-agents.md`

**P1 (High - ユーザー向けドキュメント)**:
5. `specs/009-member/contracts/cli_interface.py`
6. `examples/README_Vertex_AI.md`

**P2 (Medium - 内部ドキュメント)**:
7. `specs/009-member/tasks.md`
8. `specs/009-member/research.md`
9. `specs/009-member/data-model.md`

#### Archival Documents（時点スナップショット・更新不要）

**ポリシー**: 以下のドキュメントは作成時点の記録として保存されており、軽微な名前変更では更新しません。

**P3 (Archival - 更新不要と判断)**:
- `specs/009-member/findings/*.md`（2025-10-21時点の調査記録）
- `specs/009-member/feedbacks/*.md`（過去のレビュー記録）
- `specs/009-member/DRY-*.md`（分析時点のDRY状況）

**理由**: これらは過去の調査・分析の履歴記録であり、コマンド名変更のような軽微な変更での更新は非効率です。新しい調査が必要な場合は新規ドキュメントを作成します。

### Article 4準拠

**Article 4 (Documentation Integrity)**: 実装とドキュメントの完全な整合性を保つため、コマンド名変更に伴うすべてのドキュメント更新を実装前に完了する必要があります。

**推奨アクション**:
1. `/speckit.tasks` でタスク生成時にドキュメント更新タスクを含める
2. **Article 3 (Test-First)準拠**: テスト作成 → ドキュメント更新 → 実装の順序で進める
3. すべてのLiving Documents更新完了後に実装を開始

**Critical Path**:
```
Phase 1: テスト作成（Red）
├─ test_bundled_agents.py（--agentローダーのユニットテスト）
├─ test_cli_member_command.py（CLI統合テスト）
└─ test_member_contract.py（コントラクトテスト）

Phase 2: ドキュメント更新（P0-P2）
├─ quickstart.md, docs/member-agents.md（ユーザー向け）
├─ contracts/, examples/（開発者向け）
└─ tasks.md, research.md, data-model.md（内部）

Phase 3: 実装（Green → Refactor）
├─ bundled_agent_loader.py（パッケージリソース読み込み）
├─ member.py（コマンド実装）
└─ configs/agents/*.toml（標準TOML作成）

Phase 4: モデルID更新
└─ gemini-1.5-flash → gemini-2.5-flash-lite（全置換）
```

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |

---

## Dynamic Loading Implementation (FR-020, FR-021, FR-022)

**Added**: 2025-11-20 | **Spec Reference**: spec.md L523-545

### Summary

カスタムMember Agent（`type = "custom"`）の動的ロード機構を実装します。2つのロード方式（agent_module推奨、path代替）をサポートし、優先順位処理とエラーハンドリングを提供します。

### Requirements Overview

- **FR-020**: 動的ロード機構（agent_module方式 + path方式）
- **FR-021**: ロード優先順位処理（agent_module → path フォールバック）
- **FR-022**: エラーハンドリング（詳細なエラーメッセージ + 推奨対処方法）

### Implementation Approach

#### 1. agent_module Method (FR-020, Priority 1)

**Purpose**: 本番環境・SDKとしての配布・pip installableパッケージからのロード

**Implementation**:
```python
# src/mixseek/agents/member/dynamic_loader.py (新規作成)

import importlib
from typing import Type
from mixseek.agents.member.base import BaseMemberAgent
from mixseek.models.member_agent import MemberAgentConfig

def load_agent_from_module(
    agent_module: str,
    agent_class: str,
    config: MemberAgentConfig
) -> BaseMemberAgent:
    """
    Pythonモジュールパスからカスタムエージェントクラスをロード

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
        # FR-022準拠エラーメッセージ
        raise ModuleNotFoundError(
            f"Error: Failed to load custom agent from module '{agent_module}'. "
            f"ModuleNotFoundError: {e}. "
            f"Install package: pip install <package-name>"
        ) from e

    try:
        cls: Type[BaseMemberAgent] = getattr(module, agent_class)
    except AttributeError as e:
        # FR-022準拠エラーメッセージ
        raise AttributeError(
            f"Error: Custom agent class '{agent_class}' not found in module '{agent_module}'. "
            f"Check agent_class in TOML config."
        ) from e

    # BaseMemberAgent継承チェック
    if not issubclass(cls, BaseMemberAgent):
        raise TypeError(
            f"Error: Custom agent class '{agent_class}' must inherit from BaseMemberAgent."
        )

    return cls(config)
```

**TOML Config Example**:
```toml
[agent]
name = "データ分析エージェント"
type = "custom"
description = "Pandas/NumPyを使ったデータ分析専門エージェント"

[agent.metadata.plugin]
agent_module = "my_analytics_package.agents.data_analyst"
agent_class = "DataAnalystAgent"
```

#### 2. path Method (FR-020, Priority 2)

**Purpose**: 開発プロトタイピング・スタンドアロンファイルからのロード

**Implementation**:
```python
# src/mixseek/agents/member/dynamic_loader.py (継続)

import importlib.util
import sys
from pathlib import Path

def load_agent_from_path(
    path: str,
    agent_class: str,
    config: MemberAgentConfig
) -> BaseMemberAgent:
    """
    ファイルパスからカスタムエージェントクラスをロード

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
        # FR-022準拠エラーメッセージ
        raise FileNotFoundError(
            f"Error: Failed to load custom agent from path '{path}'. "
            f"FileNotFoundError: File not found. "
            f"Check file path in TOML config."
        )

    # importlib.utilでファイルパスからモジュールをロード
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
        # FR-022準拠エラーメッセージ
        raise AttributeError(
            f"Error: Custom agent class '{agent_class}' not found in file '{path}'. "
            f"Check agent_class in TOML config."
        ) from e

    # BaseMemberAgent継承チェック
    if not issubclass(cls, BaseMemberAgent):
        raise TypeError(
            f"Error: Custom agent class '{agent_class}' must inherit from BaseMemberAgent."
        )

    return cls(config)
```

**TOML Config Example**:
```toml
[agent]
name = "データ分析エージェント"
type = "custom"
description = "Pandas/NumPyを使ったデータ分析専門エージェント"

[agent.metadata.plugin]
path = "/path/to/custom_agent.py"
agent_class = "DataAnalystAgent"
```

#### 3. Priority Handling (FR-021)

**Implementation**:
```python
# src/mixseek/agents/member/factory.py (既存ファイル更新)

from mixseek.agents.member.dynamic_loader import load_agent_from_module, load_agent_from_path

class MemberAgentFactory:
    """Member Agent factory with dynamic loading support"""

    @staticmethod
    def create_agent(config: MemberAgentConfig) -> BaseMemberAgent:
        """
        設定からMember Agentを作成

        Args:
            config: エージェント設定

        Returns:
            インスタンス化されたエージェント

        Raises:
            ValueError: 不正なagent.type
            ModuleNotFoundError: agent_moduleロード失敗
            FileNotFoundError: pathロード失敗
        """
        agent_type = config.agent.type

        # 標準エージェント: 動的ロードをスキップ
        if agent_type in ("plain", "web_search", "code_execution"):
            return MemberAgentFactory._create_standard_agent(config)

        # カスタムエージェント: 動的ロード
        if agent_type == "custom":
            return MemberAgentFactory._load_custom_agent(config)

        raise ValueError(f"Unknown agent type: {agent_type}")

    @staticmethod
    def _load_custom_agent(config: MemberAgentConfig) -> BaseMemberAgent:
        """
        カスタムエージェントの動的ロード（FR-021優先順位処理）

        Priority:
            1. agent_module（推奨）
            2. path（代替）
        """
        plugin = config.agent.metadata.plugin

        # 第1優先: agent_module
        if plugin.agent_module is not None:
            try:
                return load_agent_from_module(
                    agent_module=plugin.agent_module,
                    agent_class=plugin.agent_class,
                    config=config
                )
            except (ModuleNotFoundError, AttributeError, TypeError) as e:
                # agent_module失敗時、pathフォールバックを試行
                if plugin.path is None:
                    # pathも未指定の場合はエラー
                    raise
                # pathフォールバックを試行（ログ記録推奨）
                pass  # Continue to path method

        # 第2優先: path
        if plugin.path is not None:
            return load_agent_from_path(
                path=plugin.path,
                agent_class=plugin.agent_class,
                config=config
            )

        # どちらも未指定
        raise ValueError(
            f"Error: Custom agent must specify either 'agent_module' or 'path' "
            f"in [agent.metadata.plugin] section. Check TOML config."
        )

    @staticmethod
    def _create_standard_agent(config: MemberAgentConfig) -> BaseMemberAgent:
        """標準エージェント作成（既存実装）"""
        from mixseek.agents.plain import PlainMemberAgent
        from mixseek.agents.web_search import WebSearchMemberAgent
        from mixseek.agents.code_execution import CodeExecutionMemberAgent

        agent_type = config.agent.type
        if agent_type == "plain":
            return PlainMemberAgent(config)
        elif agent_type == "web_search":
            return WebSearchMemberAgent(config)
        elif agent_type == "code_execution":
            return CodeExecutionMemberAgent(config)
        else:
            raise ValueError(f"Unknown standard agent type: {agent_type}")
```

#### 4. Error Handling (FR-022)

**Requirements**:
- エラーメッセージに以下を含める：
  - ロード方式（agent_module/path）
  - 試行したモジュール名またはファイルパス
  - 失敗原因（ModuleNotFoundError, ImportError, AttributeError等）
  - 推奨対処方法（パッケージインストール、パスの確認、クラス名の確認等）

**Implementation**: 上記の各関数で実装済み

**Error Message Examples**:
```
Error: Failed to load custom agent from module 'my_package.agents.custom'.
ModuleNotFoundError: No module named 'my_package'.
Install package: pip install my-package

Error: Failed to load custom agent from path '/path/to/custom_agent.py'.
FileNotFoundError: File not found.
Check file path in TOML config.

Error: Custom agent class 'MyCustomAgent' not found in module 'my_package.agents.custom'.
Check agent_class in TOML config.
```

### Files to Create/Update

#### 📝 New Files

1. **src/mixseek/agents/member/dynamic_loader.py**
   - `load_agent_from_module()`: agent_module方式実装
   - `load_agent_from_path()`: path方式実装
   - Article 9準拠: 明示的エラーハンドリング、ハードコード禁止
   - Article 10準拠: 動的ロードロジックを一元管理（DRY原則）

#### ⚠️ Files to Update

2. **src/mixseek/agents/member/factory.py**
   - `_load_custom_agent()`: 優先順位処理実装（FR-021）
   - `create_agent()`: カスタムエージェント分岐追加
   - `register_agent()`の既存実装を活用

3. **src/mixseek/models/member_agent.py**
   - `PluginMetadata` Pydanticモデル更新:
     ```python
     class PluginMetadata(BaseModel):
         agent_module: Optional[str] = None
         path: Optional[str] = None
         agent_class: str
     ```

### Test Requirements (Article 3 Test-First)

#### Unit Tests

**tests/unit/test_dynamic_loader.py** (新規作成):

```python
import pytest
from pathlib import Path
from mixseek.agents.member.dynamic_loader import (
    load_agent_from_module,
    load_agent_from_path
)
from mixseek.models.member_agent import MemberAgentConfig

class TestLoadAgentFromModule:
    """agent_module方式のテスト"""

    def test_load_valid_module(self, mock_config):
        """正常なモジュールロード"""
        # TODO: モックエージェントパッケージを使用
        pass

    def test_module_not_found_error(self, mock_config):
        """ModuleNotFoundErrorのエラーメッセージ"""
        with pytest.raises(ModuleNotFoundError) as exc_info:
            load_agent_from_module(
                agent_module="nonexistent_package.agents.custom",
                agent_class="CustomAgent",
                config=mock_config
            )
        assert "Failed to load custom agent from module" in str(exc_info.value)
        assert "Install package: pip install" in str(exc_info.value)

    def test_class_not_found_error(self, mock_config):
        """AttributeErrorのエラーメッセージ"""
        # TODO: 存在するモジュール、存在しないクラス
        pass

    def test_not_inherit_base_agent_error(self, mock_config):
        """BaseMemberAgent非継承のTypeError"""
        # TODO: BaseMemberAgentを継承しないクラス
        pass

class TestLoadAgentFromPath:
    """path方式のテスト"""

    def test_load_valid_file(self, tmp_path, mock_config):
        """正常なファイルロード"""
        # TODO: 一時ファイルにカスタムエージェント作成
        pass

    def test_file_not_found_error(self, mock_config):
        """FileNotFoundErrorのエラーメッセージ"""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_agent_from_path(
                path="/nonexistent/path/custom_agent.py",
                agent_class="CustomAgent",
                config=mock_config
            )
        assert "Failed to load custom agent from path" in str(exc_info.value)
        assert "Check file path in TOML config" in str(exc_info.value)

    def test_class_not_found_in_file_error(self, tmp_path, mock_config):
        """AttributeErrorのエラーメッセージ"""
        # TODO: クラスが存在しないPyファイル
        pass
```

**tests/unit/test_factory_custom_loading.py** (新規作成):

```python
import pytest
from mixseek.agents.member.factory import MemberAgentFactory
from mixseek.models.member_agent import MemberAgentConfig

class TestCustomAgentPriorityHandling:
    """FR-021優先順位処理のテスト"""

    def test_agent_module_priority(self, mock_config_with_both):
        """agent_moduleとpath両方指定時、agent_moduleが優先される"""
        # TODO: agent_moduleを優先的にロード
        pass

    def test_fallback_to_path(self, mock_config_with_both):
        """agent_module失敗時、pathフォールバック"""
        # TODO: agent_module失敗 → path成功
        pass

    def test_neither_specified_error(self, mock_config_custom_no_plugin):
        """agent_module/path両方未指定時のエラー"""
        with pytest.raises(ValueError) as exc_info:
            MemberAgentFactory.create_agent(mock_config_custom_no_plugin)
        assert "must specify either 'agent_module' or 'path'" in str(exc_info.value)
```

#### Integration Tests

**tests/integration/test_custom_agent_loading.py** (新規作成):

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

### Constitution Compliance

- **Article 3 (Test-First)**: ✅ テスト作成 → 実装の順序で進める
- **Article 9 (Data Accuracy)**: ✅ 明示的エラーハンドリング、暗黙的フォールバック禁止
- **Article 10 (DRY)**: ✅ `agents/member/dynamic_loader.py`で共通ロジック集約（CLIや他のクライアントから再利用可能）
- **Article 16 (Type Safety)**: ✅ すべての関数に型注釈付与、mypyストリクトモード準拠

### Implementation Order

1. **Phase 1: Test Creation (Red)**
   - `tests/unit/test_dynamic_loader.py` 作成
   - `tests/unit/test_factory_custom_loading.py` 作成
   - `tests/integration/test_custom_agent_loading.py` 作成

2. **Phase 2: Implementation (Green)**
   - `src/mixseek/agents/member/dynamic_loader.py` 作成
   - `src/mixseek/agents/member/factory.py` 更新
   - `src/mixseek/models/member_agent.py` 更新（PluginMetadata）

3. **Phase 3: Refactor**
   - エラーメッセージの一貫性確認
   - ログ記録追加（agent_module → path フォールバック時）
   - mypy/ruffチェック実行

4. **Phase 4: Documentation**
   - `docs/member-agents.md` にカスタムエージェント開発ガイド追加
   - `specs/009-member/quickstart.md` に使用例追加
