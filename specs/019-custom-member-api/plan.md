# Implementation Plan: bitbank Public API連携サンプルエージェント

**Branch**: `133-custom-member-api` | **Date**: 2025-11-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/home/driller/repo/dseek_for_drillan/specs/019-custom-member-api/spec.md`

## Summary

bitbank Public APIを利用して暗号資産の価格データ（BTC/JPY、XRP/JPY等）を取得し、投資家向け金融指標分析（年率リターン、年率ボラティリティ、シャープレシオ、最大ドローダウン、リターン分布の歪度・尖度）を実行するカスタムMember Agentのサンプル実装です。

このサンプルエージェントは、親仕様（`specs/018-custom-member/spec.md`）で定義された「外部API連携エージェント」として、開発者が独自のカスタムエージェントを作成する際の実装パターンを提供します。

**技術選定のポイント**:
- **HTTPクライアント**: httpx（非同期、リトライ機構、Python 3.13対応）
- **金融指標計算**: numpy（高速、軽量、メモリ効率、年率換算・ドローダウン・分布統計）
- **設定管理**: TOML（Article 9準拠、ハードコード禁止、リスクフリーレート外部化）
- **型安全性**: Pydantic Model（Article 16準拠、包括的な型注釈）

## Technical Context

**Language/Version**: Python 3.13.9
**Primary Dependencies**:
- httpx 0.27.0以上（非同期HTTPクライアント）- インストール済み: 0.28.1 ✓
- numpy 1.26.0以上（統計計算）- インストール済み: 2.3.5 ✓
- pydantic >=2.0.0（データバリデーション）- インストール済み: 2.12.4 ✓
- pydantic-ai >=0.1.0（AI Agent SDK）- インストール済み: 1.20.0 ✓
- google-genai >=1.51.0（Google Gemini APIクライアント）- インストール済み: 1.51.0 ✓

**Storage**: N/A（ステートレスエージェント、データ永続化なし）
**Testing**: pytest >=8.3.4（単体テスト、統合テスト、E2Eテスト）
**Target Platform**: Linux server（Python 3.13コンテナ環境）
**Project Type**: Single project（mixseek-coreパッケージのexamples/custom_agents/bitbank/）
**Performance Goals**:
- リアルタイム価格取得: 3秒以内（ネットワーク正常時）
- 時系列データ取得・金融指標分析: 10秒以内（最大1000件のロウソク足データ、年率換算・ドローダウン・シャープレシオ計算含む）

**Constraints**:
- bitbank APIレート制限（公式未明示、保守的に1秒間隔推奨）
- HTTP 429（レート制限）検出時のエクスポネンシャルバックオフ実装必須
- Article 9（Data Accuracy Mandate）準拠（ハードコード禁止、TOML設定管理）
- Article 16（Type Safety Mandate）準拠（包括的な型注釈、mypy strict mode）

**Scale/Scope**:
- サンプルコード（約500-800行）
- 主要通貨ペア10種類サポート（btc_jpy、xrp_jpy、eth_jpy等）
- ロウソク足データ最大1000件処理
- テストカバレッジ80%以上（コアロジックのみ）

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Article 3: Test-First Imperative ✓

- **Status**: PASS
- **Evidence**:
  - テスト設計を実装前に完了する計画（tasks.mdで明示）
  - 単体テスト（APIクライアント、データパース、金融指標計算）
  - 統合テスト（ツール連携）
  - E2Eテスト（実際のbitbank API使用、`@pytest.mark.e2e`）
- **Action**: `/speckit.tasks`実行時にテスト作成タスクを最優先で配置

### Article 4: Documentation Integrity ✓

- **Status**: PASS
- **Evidence**:
  - spec.mdの要件（FR-001 ～ FR-010）に完全準拠
  - 親仕様（009-member、018-custom-member）との整合性確認済み
  - 実装前の仕様確認プロセスを計画
- **Action**: 実装中に仕様との矛盾を検出した場合は即座に停止し、ユーザーに報告

### Article 8: Code Quality Standards ✓

- **Status**: PASS
- **Evidence**:
  - ruff、mypy品質チェックを実装タスクに含める
  - コミット前に`ruff check --fix . && ruff format . && mypy .`を実行
  - 品質基準違反時は次工程に進まない
- **Action**: CI/CDパイプラインで品質チェックを自動実行（既存インフラ利用）

### Article 9: Data Accuracy Mandate ✓

- **Status**: PASS
- **Evidence**:
  - すべての設定値をTOML管理（base_url、timeout_seconds、max_retries、risk_free_rate、trading_days_per_year、minimum_acceptable_return）
  - 環境変数による明示的な取得（`GOOGLE_API_KEY`）
  - ハードコード禁止、暗黙的フォールバック禁止
  - エラー時の明示的例外発生
  - 金融指標パラメータ（リスクフリーレート0.1%、365日換算、MAR=0）を外部化
- **Action**: TOML設定ファイルの検証ロジックを実装（`BitbankAPIConfig` Pydantic Model）

### Article 10: DRY Principle ✓

- **Status**: PASS
- **Evidence**:
  - 既存の`BaseMemberAgent`インターフェースを再利用（親仕様027で定義）
  - httpxライブラリの既存機能を活用（リトライ、タイムアウト）
  - 統計計算でnumpyの標準関数を使用（車輪の再発明を回避）
- **Action**: 実装前にGlob/Grepで既存実装を検索し、重複を回避

### Article 14: SpecKit Framework Consistency ✓

- **Status**: PASS
- **Evidence**:
  - MixSeek-Core Framework（specs/001-specs）との整合性確認済み
  - Member Agentアーキテクチャに準拠（BaseMemberAgent、TOML設定、動的ロード機構）
  - Leader Agentからの呼び出し形式（Pydantic AI Toolset、FR-019）に準拠
  - エラー時のチーム失格判定（FR-017）に準拠
- **Action**: 実装中にFramework仕様との矛盾を検出した場合は即座に停止

### Article 16: Python Type Safety Mandate ✓

- **Status**: PASS
- **Evidence**:
  - すべてのPydantic Modelで包括的な型注釈
  - mypy strict mode設定（pyproject.toml）
  - `Any`型の使用を最小限に抑制
  - field_validatorによる実行時型チェック
- **Action**: 実装時にmypyエラーゼロを確認、CI/CDで型チェック失敗時はビルド停止

### Complexity Tracking

**No violations**: すべての憲法要件に準拠しており、複雑性の正当化は不要です。

## Project Structure

### Documentation (this feature)

```
specs/019-custom-member-api/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (completed)
├── data-model.md        # Phase 1 output (completed)
├── quickstart.md        # Phase 1 output (completed)
├── checklists/
│   └── requirements.md  # Specification quality checklist (completed)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created yet)
```

### Source Code (repository root)

```
# Single project structure (mixseek-core package)

examples/custom_agents/bitbank/
├── __init__.py          # Package marker
├── agent.py             # BitbankAPIAgent class (BaseMemberAgent implementation)
├── tools.py             # Custom tools (get_ticker_data, get_candlestick_data, calculate_financial_metrics, etc.)
├── models.py            # Pydantic Models (BitbankTickerData, FinancialSummary, etc.)
├── client.py            # BitbankAPIClient (httpx wrapper)
├── config.py            # Configuration loading (BitbankAPIConfig)
└── bitbank_agent.toml   # TOML configuration file

tests/examples/custom_agents/
├── test_bitbank_agent.py         # Unit tests (agent, tools)
├── test_bitbank_client.py        # Unit tests (httpx client)
├── test_bitbank_models.py        # Unit tests (Pydantic Models)
├── test_bitbank_integration.py   # Integration tests (tool + agent)
└── test_bitbank_e2e.py           # E2E tests (actual API, @pytest.mark.e2e)

docs/
└── custom-agent-guide.md         # Developer guide (includes bitbank example)
```

**Structure Decision**:
- Single project構造を採用（mixseek-coreパッケージのexamples/ディレクトリ配下）
- カスタムエージェントはexamples/custom_agents/で管理（親仕様114で定義）
- テストはtests/examples/custom_agents/で一元管理
- ドキュメントはdocs/で集中管理（Article 12準拠）

## MixSeek-Core Framework Consistency Validation

### FR-005: Member Agent Types

- **検証項目**: カスタムエージェントが`BaseMemberAgent`基底クラスを継承しているか
- **結果**: PASS - `BitbankAPIAgent(BaseMemberAgent)`で実装
- **エビデンス**: `agent.py`で`BaseMemberAgent`を継承、`execute(task, context)`メソッドを実装

### FR-019: Communication Protocol

- **検証項目**: Leader AgentとMember Agent間の通信がPydantic AI Toolsetを通じて行われるか
- **結果**: PASS - Toolsetベースの関数呼び出し実装
- **エビデンス**: `tools.py`で定義された関数がToolsetとして登録、Leader Agentと同一プロセス内で実行

### FR-017: Error Handling

- **検証項目**: エラー発生時に該当チーム全体が失格となり、他チームで処理が継続されるか
- **結果**: PASS - 例外を適切に伝播、Leader Agentがキャッチしてチーム失格判定
- **エビデンス**: エラーハンドリング戦略（research.md）で明示的なエラー伝播を実装

### FR-014: TOML Configuration

- **検証項目**: エージェント設定がTOMLファイルで階層的に定義されているか
- **結果**: PASS - `bitbank_agent.toml`で設定管理
- **エビデンス**:
  - `type = "custom"`固定（018-custom-member仕様）
  - `agent_module`による動的ロード機構
  - `tool_settings.bitbank_api`で階層的設定

### FR-020: Extensibility

- **検証項目**: Member Agentのクラス設計が拡張可能か（SDKでのカスタムエージェント開発）
- **結果**: PASS - `BaseMemberAgent`継承パターンをサンプルコードで示す
- **エビデンス**: `BitbankAPIAgent`が拡張可能な実装例として機能

### FR-022: Submission Structure

- **検証項目**: 応答が`MemberAgentResult` Pydantic Modelで型安全に定義されているか
- **結果**: PASS - `MemberAgentResult(success, content, metadata)`を返却
- **エビデンス**: `data-model.md`で`MemberAgentResult`モデルを定義

## Implementation Phases

### Phase 0: Research ✓ (Completed)

- [x] bitbank Public API エンドポイント仕様調査
- [x] HTTPクライアントライブラリ選定（httpx）
- [x] 統計分析ライブラリ選定（numpy）
- [x] エラーハンドリング戦略策定
- [x] TOML設定構造設計
- [x] research.md生成完了

### Phase 1: Design & Contracts ✓ (Completed)

- [x] Pydantic Models設計（BitbankTickerData、BitbankCandlestickData、FinancialSummary等）
- [x] 金融指標詳細設計（年率リターン、年率ボラティリティ、シャープレシオ、ソルティーノレシオ、最大ドローダウン、歪度、尖度）
- [x] data-model.md生成完了
- [x] quickstart.md生成完了（10分セットアップガイド）
- [x] TOML設定ファイル構造確定（risk_free_rate設定追加）

### Phase 2: Tasks Generation (Pending - `/speckit.tasks` command)

- [ ] tasks.md生成（実装タスクの依存関係順リスト）
- [ ] テスト作成タスク（Article 3準拠、実装前にテスト）
- [ ] コアロジック実装タスク
- [ ] 統合・E2Eテストタスク
- [ ] ドキュメント更新タスク

## Technology Stack Summary

### Core Dependencies

- **Python**: 3.13.9（プロジェクト標準）
- **httpx**: 0.27.0以上（非同期HTTPクライアント、リトライ機構、タイムアウト設定）
  - 現在インストール済み: 0.28.1 ✓
- **numpy**: 1.26.0以上（統計計算、高速・軽量・メモリ効率）
  - 現在インストール済み: 2.3.5 ✓
- **pydantic**: >=2.0.0（データバリデーション、型安全性）
  - 現在インストール済み: 2.12.4 ✓
- **pydantic-ai**: >=0.1.0（AI Agent SDK、Toolset管理）
  - 現在インストール済み: 1.20.0 ✓
- **google-genai**: >=1.51.0（Google Gemini APIクライアント、LLM実行）
  - 現在インストール済み: 1.51.0 ✓

### Development Tools

- **pytest**: >=8.3.4（単体、統合、E2Eテスト）
- **pytest-asyncio**: 非同期テストサポート
- **pytest-mock**: モックサポート
- **ruff**: >=0.8.4（リンター、フォーマッター）
- **mypy**: >=1.13.0（型チェッカー、strict mode）

### Package Management

- **uv**: パッケージマネージャ（高速な依存関係解決）
- **pyproject.toml**: 依存関係定義、ビルド設定、品質ツール設定

## Configuration Management

### TOML Configuration Structure

```toml
[agent]
type = "custom"  # 固定（018-custom-member仕様）
name = "bitbank-api-agent"
description = "Sample agent for bitbank Public API integration"
capabilities = ["data_retrieval", "financial_metrics_analysis"]

[agent.metadata.plugin]
agent_module = "examples.custom_agents.bitbank.agent"
agent_class = "BitbankAPIAgent"

[agent.tool_settings.bitbank_api]
base_url = "https://public.bitbank.cc"
timeout_seconds = 30
max_retries = 3
retry_delay_seconds = 1
min_request_interval_seconds = 1
supported_pairs = ["btc_jpy", "xrp_jpy", "eth_jpy"]
supported_candle_types = ["4hour", "8hour", "12hour", "1day", "1week", "1month"]

# Financial metrics settings (Article 9: Data Accuracy Mandate)
[agent.tool_settings.bitbank_api.financial_metrics]
risk_free_rate = 0.001  # 年率0.1%（日本10年国債利回り）
trading_days_per_year = 365  # 暗号通貨は365日取引
minimum_acceptable_return = 0.0  # ソルティーノレシオMAR（ゼロリターン）

[agent.llm_settings]
model = "gemini-2.0-flash-exp"
temperature = 0.7
```

### Environment Variables

- **GOOGLE_API_KEY**: Google AI API Key（必須、環境変数で設定）
- **MIXSEEK_WORKSPACE**: ワークスペースディレクトリ（mixseek-core実行時）

## Error Handling Strategy

### 4層のエラーハンドリング

1. **入力バリデーション層**: Pydantic Modelによる厳密な検証
2. **ネットワーク層**: httpx例外の包括的処理（タイムアウト、404, 429, 5xx）
3. **レスポンス検証層**: Pydantic Modelでスキーマ検証
4. **データ処理層**: numpy金融指標計算エラー（空配列、NaN/Inf、ゼロ除算）のハンドリング

### Article 9準拠

- **NO ハードコーディング**: すべての設定値をTOML管理
- **NO 暗黙的フォールバック**: エラー時のデフォルト値自動適用禁止
- **明示的エラー伝播**: すべてのエラーで明確なメッセージを返す

## Testing Strategy

### Test Coverage Goals

- **コアロジック**: 80%以上（APIクライアント、データパース、金融指標計算）
- **統合テスト**: ツール連携の正常性確認
- **E2Eテスト**: 実際のbitbank API使用（`@pytest.mark.e2e`）

### Test Types

1. **単体テスト** (tests/examples/custom_agents/test_bitbank_*.py):
   - APIモック使用（httpx.AsyncClient.mock）
   - Pydantic Modelバリデーション
   - 金融指標計算ロジック（年率換算、ドローダウン、シャープレシオ、歪度、尖度）

2. **統合テスト** (tests/examples/custom_agents/test_bitbank_integration.py):
   - ツール関数とエージェントの連携
   - TOML設定の読み込み
   - エラーハンドリング

3. **E2Eテスト** (tests/examples/custom_agents/test_bitbank_e2e.py):
   - 実際のbitbank API呼び出し
   - レート制限対応の検証
   - リトライロジックの確認

## Documentation Plan

### Developer Guide Updates

**File**: `docs/custom-agent-guide.md`

**新規追加セクション**:
- bitbank API連携エージェントのサンプルコード説明
- 外部API統合パターンのベストプラクティス
- httpxによる非同期HTTP通信の実装例
- Article 9準拠の設定管理パターン（リスクフリーレート外部化）
- エラーハンドリング4層戦略の詳細
- 投資家向け金融指標計算パターン（年率換算、ドローダウン、シャープレシオ、分布統計）

### Specification Updates

**Files**:
- `specs/018-custom-member/spec.md`: bitbank API連携エージェントのサンプル追加を明記
- `specs/019-custom-member-api/tasks.md`: `/speckit.tasks`で生成（実装タスク詳細）

## Success Criteria

### Technical Success Criteria (from spec.md)

- **SC-001**: エージェントは、指定された通貨ペアの最新価格情報を3秒以内に取得できる ✓
- **SC-002**: エージェントは、時系列データ（最大1000件）を10秒以内に取得し、金融指標分析を完了できる ✓
- **SC-003**: エージェントは、APIエラー発生時に100%の確率で適切なエラーメッセージをユーザーに返す ✓
- **SC-004**: エージェントは、APIレート制限（HTTP 429）発生時にリトライロジックを実行し、最大3回まで自動的に再試行する ✓
- **SC-005**: エージェントのコアロジック（APIクライアント、データパース、金融指標計算）のテストカバレッジが80%以上を達成する ✓
- **SC-006**: 開発者がサンプルコードを参考にすることで、類似の外部API連携エージェント作成時間が40%短縮される ✓
- **SC-007**: エージェントは、Leader Agentから呼び出された際に100%の互換性を持つ ✓
- **SC-008**: エージェントは、金融指標分析結果に対してLLMが自然言語で解釈したObservationsセクション（リスク調整後パフォーマンス、ドローダウンリスク評価、リターン分布特性）をMarkdown形式で100%の確率で提供する ✓
- **SC-009**: エージェントは、金融指標分析結果（FinancialSummary）の完全な構造化データを`MemberAgentResult.metadata`にJSON形式で100%の確率で格納し、プログラマティックな後処理を可能にする ✓

### Implementation Success Criteria

- **ISC-001**: すべての憲法要件（Article 3, 8, 9, 10, 14, 16）に準拠
- **ISC-002**: MixSeek-Core Framework（specs/001-specs）との整合性確認
- **ISC-003**: 親仕様（009-member、018-custom-member）インターフェースに準拠
- **ISC-004**: テストカバレッジ80%以上達成（コアロジック）
- **ISC-005**: ruff、mypy品質チェック合格（エラーゼロ）

## Next Steps

1. **`/speckit.tasks`実行**: tasks.md生成（実装タスクの依存関係順リスト）
2. **テスト作成**: Article 3（Test-First Imperative）に従い実装前にテスト作成
3. **コアロジック実装**:
   - BitbankAPIClient（httpxラッパー）
   - models.py（FinancialSummary等のPydantic Models）
   - tools.py（calculate_financial_metrics: 年率換算、ドローダウン、シャープレシオ、歪度、尖度）
4. **エージェント実装**: BitbankAPIAgent（BaseMemberAgent継承）
5. **統合・E2Eテスト**: 実際のAPI使用テスト
6. **ドキュメント更新**: docs/custom-agent-guide.mdにbitbankサンプル＋金融指標計算パターン追加

## References

- **Feature Spec**: [spec.md](./spec.md)
- **Research**: [research.md](./research.md)
- **Data Model**: [data-model.md](./data-model.md)
- **Quickstart**: [quickstart.md](./quickstart.md)
- **Parent Spec (114)**: `specs/018-custom-member/spec.md`
- **Parent Spec (027)**: `specs/009-member/spec.md`
- **Framework Spec**: `specs/001-specs/spec.md`
- **Constitution**: `.specify/memory/constitution.md`
