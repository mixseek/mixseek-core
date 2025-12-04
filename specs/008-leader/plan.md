# Implementation Plan: Leader Agent - Agent Delegation と Member Agent応答記録

**Branch**: `026-mixseek-core-leader` | **Date**: 2025-10-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-leader/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Leader AgentはPydantic AIのAgent Delegationパターンを使用し、タスクを分析して適切なMember AgentをToolを通じて動的に選択・実行します。選択されたMember Agent応答は構造化データ（`List[MemberSubmission]`）として記録され、DuckDBに永続化されます。Leader Agentは単一ラウンド内の記録のみを担当し、前ラウンドを意識しない独立した設計です。複数ラウンド間の統合処理・整形処理はRound Controllerが実施します。TUMIX論文は参考にしますが、全Agent並列実行方式は破棄し、リソース効率と柔軟性を優先します。

## Technical Context

**Language/Version**: Python 3.13.9
**Primary Dependencies**:
- Pydantic AI (Agent, RunContext, RunUsage, ModelMessage)
- DuckDB >=1.3.1 (MVCC並列書き込み、ネイティブJSON型)
- Pydantic >=2.0 (BaseModel, computed field)
- asyncio (非同期Agent実行)

**Storage**: DuckDB (単一ファイル `$MIXSEEK_WORKSPACE/mixseek.db`)
**Testing**: pytest >=8.3.4, pytest-asyncio, pytest-mock
**Target Platform**: Linux server (開発環境: Docker devコンテナ)
**Project Type**: Library (CLIインターフェース付き)
**Performance Goals**:
- 複数チーム並列実行時のロック競合ゼロ
- Leader Board集計クエリ <1秒（100万行）
- Agent Delegation 1回あたり <5秒（Member Agent実行時間含む）

**Constraints**:
- 環境変数 `MIXSEEK_WORKSPACE` 必須（Article 9準拠）
- UsageLimits による無制限実行防止
- 単一ノード実行（分散環境非対応）

**Scale/Scope**:
- 同時実行チーム数: 5-50
- Member Agent数/チーム: 3-15（デフォルト上限15、親仕様FR-014）
- ラウンド数: 1-10（親仕様設定依存）
- Agent Delegation呼び出し数: 1-10回/ラウンド

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Article 1: Library-First Principle ✅ PASS
**Status**: 準拠
**実装**: `mixseek_core/agents/leader/`配下にライブラリとして実装、アプリケーションコード内には直接実装しない

### Article 2: CLI Interface Mandate ✅ PASS
**Status**: 準拠
**実装**: `mixseek team`コマンド提供（stdin/stdout/stderr、JSON出力サポート、開発・テスト専用、FR-021-024）

### Article 3: Test-First Imperative ✅ PASS
**Status**: 準拠
**実装**: Phase 2（tasks.md）でテスト先行を強制、ユーザー承認後に実装

### Article 4: Documentation Integrity ✅ PASS
**Status**: 準拠
**実装**: 仕様（spec.md）に基づく厳密な実装、仕様曖昧性は明確化済み（Clarifications）

### Article 8: Code Quality Standards ✅ PASS
**Status**: 準拠
**実装**: ruff + mypy必須、コミット前チェック強制

### Article 9: Data Accuracy Mandate ✅ PASS
**Status**: 準拠
**実装**:
- 環境変数`MIXSEEK_WORKSPACE`必須、未設定時エラー終了（FR-016, FR-020）
- ハードコード禁止、フォールバック禁止、明示的エラー処理（Edge Cases多数）
- デフォルト値は明示的TOML設定のみ

### Article 10: DRY Principle ✅ PASS
**Status**: 準拠
**実装**:
- Member Agent TOML参照形式サポート（FR-025）
- 既存実装の調査必須（Phase 0 Research）
- Pydantic AI標準パターン活用（Agent Delegation）

### Article 14: SpecKit Framework Consistency ⚠️ DEVIATION DETECTED
**Status**: **逸脱あり - 要承認**
**逸脱内容**:
- 親仕様FR-004「Leader Agentはタスク分解、Member Agentへの作業割当、出力統合ができなければならない」を実装
- **ただし**、親仕様の想定する「全Member Agent並列実行」方式を破棄し、Agent Delegation（動的選択）を採用

**逸脱理由**:
- TUMIX論文は参考にするが遵守しない方針（ユーザー明示的承認済み）
- Pydantic AI Agent Delegationパターンに従い、リソース効率と柔軟性を優先
- 親仕様FR-004の「作業割当」「出力統合」は実現するが、実行方式が異なる

**影響分析**:
- ✅ Leader Agent責務（記録・永続化）は変更なし
- ✅ Round Controller責務（統合・整形）は変更なし
- ✅ データモデル（MemberSubmissionsRecord）は互換性あり
- ⚠️ Member Agent実行方式のみ変更（並列→動的選択）

**推奨**: この逸脱は技術的に合理的であり、親仕様の本質（マルチエージェント協調）は維持されるため、承認を推奨します。

### Article 16: Python Type Safety Mandate ✅ PASS
**Status**: 準拠
**実装**:
- 全モデルにPydantic BaseModel使用
- Pydantic AI型（RunUsage、ModelMessage）活用
- mypy strict mode必須

## MixSeek-Core Framework Consistency Check

*Article 14要件: 親仕様（001-mixseek-core-specs）との整合性検証*

### 親仕様FR-003との整合性 ✅ PASS
**親仕様要件**: チームは複数の専門Member Agentを調整する1名のLeader Agentで構成
**本仕様実装**: Leader Agent 1名 + Member Agent 3-15名のチーム構成（FR-029-034）
**判定**: 準拠

### 親仕様FR-004との整合性 ⚠️ PARTIAL (実装方式変更)
**親仕様要件**: Leader Agentはタスク分解、Member Agentへの作業割当、出力統合ができなければならない
**本仕様実装**:
- ✅ タスク分解: Leader AgentのLLMがタスクを分析（FR-033）
- ✅ 作業割当: Agent DelegationパターンでMember Agentを動的選択・実行（FR-031-032）
- ✅ 出力統合: MemberSubmissionsRecordで構造化データ記録（FR-001-003）
- ⚠️ **実行方式変更**: 全Agent並列実行 → Agent Delegation（動的選択）

**変更の妥当性**:
- TUMIX遵守不要（ユーザー承認済み）
- Pydantic AI標準パターン採用
- リソース効率向上（不要なAgent実行を回避）
- 親仕様の本質（マルチエージェント協調）は維持

**判定**: 実装方式変更あり、技術的合理性あり、承認推奨

### 親仕様FR-006との整合性 ✅ PASS
**親仕様要件**: 反復的なラウンドベース処理、前ラウンドSubmission結果と評価フィードバックを引き継ぐ
**本仕様実装**:
- Leader Agentは単一ラウンド内のみ動作（前ラウンド非依存）
- Round Controllerが前ラウンド統合・整形を担当（Out of Scope明記）
- データベースに各ラウンドのMessage History + MemberSubmissionsRecordを保存（FR-006-007）

**判定**: 準拠（責務分離が明確）

### 親仕様FR-007との整合性 ✅ PASS
**親仕様要件**: Round ControllerがMessage Historyを永続化
**本仕様実装**: Leader AgentがMessage HistoryをDuckDB JSON型で保存（FR-006）、Round Controllerが読み込み・統合
**判定**: 準拠

### データ永続化方式の整合性 ⚠️ TECHNOLOGY CHOICE
**親仕様想定**: SQLiteまたはPostgreSQL
**本仕様採用**: DuckDB（Clarifications Session 2025-10-22で決定）
**変更理由**:
- ネイティブJSON型サポート
- MVCC並列書き込み対応
- 高速分析クエリ（Leader Board集計）
- Pandas統合

**判定**: 技術選択の範囲内、合理的、承認済み

### 総合判定 ✅ PASS WITH NOTES
**結論**: Article 14要件を満たしています。Agent Delegation採用による実行方式変更はありますが、親仕様の本質（マルチエージェント協調、ラウンドベース処理、データ永続化）は完全に維持されており、技術的に合理的です。

## Project Structure

### Documentation (this feature)

```
specs/008-leader/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (in progress)
├── research.md          # Phase 0: 技術調査・ベストプラクティス
├── data-model.md        # Phase 1: データモデル詳細設計
├── quickstart.md        # Phase 1: クイックスタートガイド
├── contracts/           # Phase 1: API契約定義
│   ├── leader-agent-api.md
│   └── database-schema.sql
└── tasks.md             # Phase 2: タスク分解（/speckit.tasks）
```

### Source Code (repository root)

**Structure Decision**: Library-First Principle（Article 1）に従い、単一プロジェクト構成を採用

```
mixseek_core/
├── agents/
│   └── leader/
│       ├── __init__.py
│       ├── agent.py              # LeaderAgent クラス（Agent Delegation実装）
│       ├── models.py             # MemberSubmission, MemberSubmissionsRecord
│       ├── tools.py              # Member Agent Tool定義（動的生成）
│       ├── config.py             # TeamConfig TOML読み込み
│       └── store.py              # AggregationStore（DuckDB永続化）
│
├── database/
│   ├── __init__.py
│   ├── schema.py                 # RoundHistory, LeaderBoard テーブル定義
│   └── connection.py             # DuckDB接続管理（MVCC、トランザクション）
│
└── cli/
    └── team.py                   # mixseek team コマンド実装

tests/
├── agents/
│   └── leader/
│       ├── test_agent_delegation.py      # Agent Delegation動作テスト
│       ├── test_member_submissions.py    # MemberSubmissionsRecord記録テスト
│       ├── test_tools.py                 # Member Agent Tool生成テスト
│       └── test_store.py                 # DuckDB永続化テスト
│
├── database/
│   ├── test_schema.py                    # スキーマ定義テスト
│   └── test_concurrent_writes.py         # MVCC並列書き込みテスト
│
├── cli/
│   └── test_team_command.py              # mixseek team コマンドテスト
│
└── integration/
    └── test_leader_agent_e2e.py          # Leader Agent E2Eテスト
```

**既存コード調査（DRY Article 10）**:
- `mixseek_core/agents/member/` （specs/027）との共通パターン
- DuckDB接続管理の共通化可能性（Phase 0 Researchで調査）

## Complexity Tracking

*Article 5準拠: 最大3プロジェクト以内*

**現在のプロジェクト数**: 1（mixseek_core単一ライブラリ）
**判定**: ✅ Article 5準拠

**追加の複雑性**: なし

---

## Phase 0: Research (完了)

**Status**: ✅ Complete
**Output**: `research.md`

### 調査完了事項
1. ✅ Pydantic AI Agent Delegationパターン
2. ✅ DuckDB MVCC並列書き込みベストプラクティス
3. ✅ Member Agent TOML設定読み込みとTool自動生成
4. ✅ 既存DuckDB接続管理コード調査（DRY Article 10）
5. ✅ Pydantic AI Message Historyシリアライズ・デシリアライズ
6. ✅ エクスポネンシャルバックオフリトライロジック
7. ✅ Member Agent Tool引数設計

### 主要な技術決定
- **Agent実行方式**: Agent Delegation（動的選択）採用、全Agent並列実行破棄
- **Database**: DuckDB >=1.3.1（MVCC、JSON型）
- **TOML読み込み**: tomllib（Python 3.11+標準）
- **DRY準拠**: 既存`AggregationStore`クラス最大限再利用

---

## Phase 1: Design & Contracts (完了)

**Status**: ✅ Complete
**Outputs**:
- `data-model.md`
- `contracts/leader-agent-api.md`
- `contracts/database-schema.sql`
- `quickstart.md`

### 生成された設計成果物

#### 1. data-model.md
- **エンティティ**: MemberSubmission, MemberSubmissionsRecord, TeamConfig（Leader + Member）, TeamDependencies
- **データベース**: RoundHistory, LeaderBoard
- **変更点**: `AggregatedMemberSubmissions` → `MemberSubmissionsRecord`、`aggregated_content`削除
- **DRY準拠**: 既存コード最大限再利用、Article 11準拠のリファクタリング方針

#### 2. contracts/leader-agent-api.md
- **7つのAPI契約**: LeaderAgent.run(), save_to_database(), MemberAgentTool, register_member_tools(), AggregationStore各メソッド, CLI command
- **型安全性**: すべてPydantic BaseModel
- **エラー処理**: Article 9準拠（フォールバック禁止）
- **パフォーマンス**: 具体的な数値目標

#### 3. contracts/database-schema.sql
- **RoundHistory**: team_id + round_number UNIQUE制約、JSON型カラム
- **LeaderBoard**: スコア降順インデックス
- **クエリ例**: ランキング取得、チーム統計集計、JSON内部クエリ

#### 4. quickstart.md
- **チーム設定TOML例**: Agent Delegation対応
- **CLI実行例**: 基本実行、JSON出力、DB保存
- **Troubleshooting**: 主要なエラーと解決方法

### Agent Context更新
- ✅ `CLAUDE.md`更新完了（Python 3.13.9、DuckDB）

---

## Phase 2: Tasks (次のステップ)

**Command**: `/speckit.tasks`

### 実装タスク（予定）

#### タスクカテゴリ
1. **データモデル実装**: MemberSubmission, MemberSubmissionsRecord, TeamConfig
2. **Agent Delegation**: Leader Agent + Member Agent Tool動的登録
3. **TOML設定**: TeamConfig読み込み（参照形式サポート）
4. **データベース永続化**: AggregationStore refactoring（モデル名変更）
5. **CLI Command**: `mixseek team`コマンド実装
6. **テスト**: TDD（Article 3準拠）

#### 実装順序（TDD）
1. データモデルのテスト作成 → 実装
2. TOML読み込みのテスト作成 → 実装
3. Agent Delegationのテスト作成 → 実装
4. データベース永続化のテスト作成 → 実装
5. CLIコマンドのテスト作成 → 実装
6. E2Eテスト作成 → 統合

---

## Deliverables Summary

### Phase 0 (完了)
- ✅ `research.md`: 技術調査・ベストプラクティス（7トピック）

### Phase 1 (完了)
- ✅ `data-model.md`: エンティティ詳細設計（4エンティティ + 2 DBテーブル）
- ✅ `contracts/leader-agent-api.md`: API契約定義（7契約）
- ✅ `contracts/database-schema.sql`: DDL + クエリ例
- ✅ `quickstart.md`: クイックスタートガイド
- ✅ Agent context更新（`CLAUDE.md`）

### Phase 2 (次のステップ)
- ⏭️ `/speckit.tasks`: タスク分解（`tasks.md`生成）
- ⏭️ テスト作成 → ユーザー承認 → 実装

---

## Constitution Check (再検証)

*Phase 1完了後の再検証*

### Article 1: Library-First ✅ PASS
`mixseek_core/agents/leader/`配下に実装、変更なし

### Article 2: CLI Interface ✅ PASS
`mixseek team`コマンド、quickstart.mdで詳細化

### Article 3: Test-First ✅ PASS
Phase 2でTDD強制、実装順序明確化

### Article 4: Documentation Integrity ✅ PASS
spec.md → plan.md → data-model.md → contracts/の一貫性保証

### Article 8: Code Quality ✅ PASS
ruff + mypy必須、変更なし

### Article 9: Data Accuracy ✅ PASS
環境変数必須、フォールバック禁止、quickstart.mdで強調

### Article 10: DRY ✅ PASS
既存`AggregationStore`再利用、research.md Section 4で調査完了

### Article 14: MixSeek-Core Consistency ✅ PASS WITH NOTES
Agent Delegation方式変更、技術的合理性確認済み

### Article 16: Type Safety ✅ PASS
全エンティティPydantic BaseModel、data-model.mdで型定義完全

**総合判定**: ✅ すべてのArticle準拠、Phase 1完了条件クリア

---

## Next Command

```bash
/speckit.tasks
```

このコマンドで`tasks.md`が生成され、実装タスクが依存関係順に分解されます。TDD（Article 3）に従い、各タスクでテスト作成 → ユーザー承認 → 実装の順で進みます。

---

## Feature Summary

**026-mixseek-core-leader: Leader Agent - Agent Delegation と Member Agent応答記録**

- **コア機能**: Agent Delegationによる動的Member Agent選択、構造化データ記録、DuckDB永続化
- **設計変更**: 全Agent並列実行 → Agent Delegation（TUMIX参考のみ）
- **型安全性**: Pydantic AI完全活用（RunUsage、ModelMessage、Agent Delegation）
- **DRY準拠**: 既存コード最大限再利用（AggregationStore）
- **憲章準拠**: 全Article準拠（Article 14は実装方式変更あり、ユーザー承認済み）

**実装準備完了**: すべての設計成果物が揃い、実装開始の準備が整いました。
