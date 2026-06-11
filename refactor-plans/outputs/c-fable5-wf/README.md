# リファクタリング計画（パターンC: Fable 5 + Workflow）

## 概要

本計画は、mixseek-core リポジトリ（`src/` 159 ファイル / 約 25,500 行）を対象とした優先度付き
リファクタリング計画である。11 のサブシステムを並列に分析するワークフロー（サブシステムごとの
分析サブエージェント → 統合エージェントによる集約）で作成した。実装は行わず、計画ドキュメントのみを提供する。

前提となる現状認識:

- 300 行超のファイルが 20 個存在（AGENTS.md の自己ルール違反）。最大は `config/schema.py` の 1,641 行
- `os.getenv` 直接呼び出し・共通ロガー未使用・例外設計の不統一が複数サブシステムに散在
- `tests/` は 180 ファイルとテスト資産が厚く、多くの候補で安全網として活用できる

## ドキュメント構成（インデックス）

| ファイル | 対象サブシステム | 概要 |
|---|---|---|
| [01-config.md](01-config.md) | config | schema/manager/views の肥大解消、TOML ソース共通化、循環参照解消 |
| [02-evaluator.md](02-evaluator.md) | evaluator | LLM パラメータ集約、evaluator.py 分割、メトリクス継承設計の改善 |
| [03-orchestrator-round-controller.md](03-orchestrator-round-controller.md) | orchestrator / round_controller | 責務分割、private 依存解消、型安全化 |
| [04-framework-core.md](04-framework-core.md) | framework / core | auth レジストリ化、integration_hooks 削減、TestModel 暗黙置換の解消 |
| [05-storage.md](05-storage.md) | storage | AggregationStore 分割、DDL 一元化、ロガー導入、UI 読み取り経路統合 |
| [06-cli.md](06-cli.md) | cli | workspace 解決共通化、Logfire 初期化重複解消、表示ロジック分離 |
| [07-ui.md](07-ui.md) | ui | execution_service 分割、DB 接続一本化、エラー処理の一貫化 |
| [08-models.md](08-models.md) | models | 評価設定スキーマの新旧二重定義解消、重複ゲッター統合、責務分割 |
| [09-agents-prompt-builder.md](09-agents-prompt-builder.md) | agents / prompt_builder | execute() 共通化、usage_info バグ修正、レガシー撤去 |
| [10-workflow-observability-utils.md](10-workflow-observability-utils.md) | workflow / observability / utils | 分割、workspace 移設、例外階層 |
| [11-cross-cutting.md](11-cross-cutting.md) | 横断テーマ | env アクセス / ロギング / DRY / 例外設計 / Python 3.13 モダナイズ |

## 優先度サマリ（全候補・推奨着手順）

類似・重複する候補は 1 行に統合した（※印、表下の注記参照）。

| 順位 | 候補 | 対象 | 影響度 | リスク | 工数 | 詳細 |
|---|---|---|---|---|---|---|
| 1 | usage_info キー不整合の修正（トークン集計バグ） | agents/leader/tools.py ほか | 高 | 低 | S | [09](09-agents-prompt-builder.md) |
| 2 | 循環参照の解消（contextvars 専用モジュール化） | config/manager.py, schema.py | 中 | 低 | S | [01](01-config.md) |
| 3 | 例外階層の統一（MixseekError 基底導入）※1 | exceptions.py ほか各所 | 中 | 低 | M | [11](11-cross-cutting.md) |
| 4 | evaluator.py の分割とデッドコード除去 | evaluator/evaluator.py | 高 | 低 | M | [02](02-evaluator.md) |
| 5 | UI の DB 接続・workspace 取得一本化（db_utils 廃止） | ui/utils/ | 高 | 低 | S | [07](07-ui.md) |
| 6 | storage への共通ロガー導入 | storage/ 全体 | 中 | 低 | S | [05](05-storage.md) |
| 7 | スキーマ DDL の schema.py 一元化 | storage/aggregation_store.py | 中 | 低 | S | [05](05-storage.md) |
| 8 | リトライ/sync-async 定型コードの共通化 | storage/aggregation_store.py | 中 | 低 | S | [05](05-storage.md) |
| 9 | RoundController の private 依存・設定二重ロード解消 | orchestrator, round_controller | 中 | 低 | S | [03](03-orchestrator-round-controller.md) |
| 10 | Orchestrator._execute_impl（203 行）の分割 | orchestrator/orchestrator.py | 中 | 低 | S | [03](03-orchestrator-round-controller.md) |
| 11 | エラー処理・定数の型安全化（StrEnum 化等） | orchestrator, round_controller | 中 | 低 | S | [03](03-orchestrator-round-controller.md) |
| 12 | cli/utils.py の責務分割とデッドコード削除 | cli/utils.py | 中 | 低 | S | [06](06-cli.md) |
| 13 | cli config.py の例外処理修正と config_init 分割 | cli/commands/config.py | 中 | 低 | M | [06](06-cli.md) |
| 14 | prompt_builder の環境変数直接参照の排除 | prompt_builder/formatters.py | 中 | 低 | S | [09](09-agents-prompt-builder.md) |
| 15 | 実行ページのポーリング制御整理（sleep(5) 解消） | ui/pages/1_execution.py | 中 | 低 | S | [07](07-ui.md) |
| 16 | utils/filesystem.py のデッドコード削除 | utils/filesystem.py | 低 | 低 | S | [10](10-workflow-observability-utils.md) |
| 17 | evaluator 例外設計の一貫化（未使用例外の整理） | evaluator/exceptions.py | 低 | 低 | S | [02](02-evaluator.md) |
| 18 | result.py の typer 依存除去（表示の CLI 層移動） | models/result.py | 低 | 低 | S | [08](08-models.md) |
| 19 | cli formatters.py の整理（デッドコード削除） | cli/formatters.py | 低 | 低 | S | [06](06-cli.md) |
| 20 | pydantic class Config の ConfigDict 移行 | ui/models/*.py | 低 | 低 | S | [07](07-ui.md) |
| 21 | workspace 解決の正規経路統一（config 移設）※2 | utils/env.py, cli, ui | 高 | 中 | M | [11](11-cross-cutting.md) |
| 22 | ロギング/Logfire 初期化ブートストラップ一元化 ※3 | observability/, cli, ui | 高 | 中 | M | [11](11-cross-cutting.md) |
| 23 | auth.py のレジストリ化・分割・os.getenv 解消 ※4 | core/auth.py | 高 | 中 | M | [04](04-framework-core.md) |
| 24 | Logfire import/span 分岐の共通ヘルパー化 | orchestrator ほか 3 モジュール | 中 | 低 | S | [03](03-orchestrator-round-controller.md) |
| 25 | observability/logfire.py の責務分割と副作用排除 | observability/logfire.py | 中 | 中 | M | [10](10-workflow-observability-utils.md) |
| 26 | logging/logfire 設定の pydantic-settings 化 | config/logging.py, logfire.py | 中 | 中 | S | [01](01-config.md) |
| 27 | 構造化 LLM 呼び出しヘルパーの共通化 | evaluator, round_controller | 中 | 中 | M | [11](11-cross-cutting.md) |
| 28 | schema.py 分割＋LLM パラメータ共通 Mixin 化 ※5 | config/schema.py ほか | 高 | 中 | L | [01](01-config.md) |
| 29 | LLM 呼び出しパラメータのオブジェクト化 ※6 | evaluator/, models/ | 高 | 中 | M | [02](02-evaluator.md) |
| 30 | 評価設定スキーマの一本化（新旧二重定義の解消） | models/evaluation_config.py | 高 | 中 | L | [08](08-models.md) |
| 31 | config manager.py のフォールバック統合と分割 | config/manager.py | 中 | 低 | M | [01](01-config.md) |
| 32 | TOML ソースの基底クラス導入 | config/sources/ | 中 | 低 | M | [01](01-config.md) |
| 33 | config views.py の収集/整形分離 | config/views.py | 中 | 低 | M | [01](01-config.md) |
| 34 | Member Agent execute() のテンプレートメソッド化 | agents/member/* | 高 | 中 | M | [09](09-agents-prompt-builder.md) |
| 35 | RoundController の責務分割（永続化・進捗の抽出） | round_controller/controller.py | 高 | 中 | M | [03](03-orchestrator-round-controller.md) |
| 36 | AggregationStore の責務分割 | storage/aggregation_store.py | 高 | 中 | L | [05](05-storage.md) |
| 37 | storage 公開 API の型整理（引数オブジェクト化） | storage/aggregation_store.py | 中 | 中 | M | [05](05-storage.md) |
| 38 | UI の DuckDB 直接接続を storage 読み取り API へ統合 | ui/utils, storage | 中 | 中 | M | [05](05-storage.md) |
| 39 | execution_service.py（772 行）の責務分割 | ui/services/execution_service.py | 高 | 中 | L | [07](07-ui.md) |
| 40 | UI サービス層のエラー処理・接続クローズ一貫化 | ui/services/* | 中 | 低 | M | [07](07-ui.md) |
| 41 | member_agent.py の責務分割と config 層移設 | models/member_agent.py | 中 | 中 | M | [08](08-models.md) |
| 42 | メトリクス基底クラスの継承設計改善（LSP 違反解消） | evaluator/metrics/base.py | 中 | 中 | M | [02](02-evaluator.md) |
| 43 | integration_hooks.py の未使用機能削減と分割 | framework/integration_hooks.py | 中 | 低 | M | [04](04-framework-core.md) |
| 44 | exec.py/team.py の表示ロジック分離 | cli/commands/exec.py, team.py | 中 | 低 | M | [06](06-cli.md) |
| 45 | workflow/executable.py の分割 | workflow/executable.py | 中 | 低 | S | [10](10-workflow-observability-utils.md) |
| 46 | leader/config.py レガシー変換層の段階的撤去 | agents/leader/config.py | 中 | 中 | M | [09](09-agents-prompt-builder.md) |
| 47 | IntegrationManager のライフサイクル再設計 | framework/integration_hooks.py | 中 | 中 | M | [04](04-framework-core.md) |
| 48 | 構造化ログの徹底と型注釈モダナイズ（品質パス） | src/ 全体 | 中 | 低 | M | [11](11-cross-cutting.md) |
| 49 | TestModel 暗黙置換の明示オプトイン化 | core/auth.py | 中 | 高 | M | [04](04-framework-core.md) |

### 統合の注記

- ※1: [10](10-workflow-observability-utils.md) と [11](11-cross-cutting.md) の同種候補
  「MixseekError 基底導入」を統合。
- ※2: [11](11-cross-cutting.md)「workspace 正規経路統一」、
  [10](10-workflow-observability-utils.md)「config 移設」、[06](06-cli.md)「CLI workspace 共通化」を統合。
- ※3: [11](11-cross-cutting.md)「ブートストラップ一元化」、[06](06-cli.md)「Logfire 初期化重複解消」、
  [07](07-ui.md)「ロギング/Logfire 共通化」を統合。
- ※4: [04](04-framework-core.md)「レジストリ化」「os.getenv 解消」、
  [11](11-cross-cutting.md)「テーブル駆動化」を統合。
- ※5: [01](01-config.md)「schema 分割＋Mixin 化」、[08](08-models.md)「共通基底クラス化」、
  [09](09-agents-prompt-builder.md)「共通基底モデル化」を統合（同一 Mixin を 3 サブシステムで共有）。
- ※6: [02](02-evaluator.md)「パラメータオブジェクト化」、
  [08](08-models.md)「get_*_for_metric 11 メソッド統合」を統合。

### 優先度判断の根拠

1. **影響度が高くリスクが低いものを先頭に**: 順位 1 の usage_info キー不整合は「トークン集計が常に 0」
   という潜在バグの修正であり、最優先とした。順位 4・5 もデッドコード除去・重複統合が中心で安全網が厚い。
2. **前提整備を先行**: 順位 2 の循環参照解消は config の大型分割（順位 28・31）の前提。順位 3 の例外階層と
   順位 6 のロガー導入は、以降の全リファクタで使う横断方針のため早期に確定させる。
3. **横断基盤（順位 21〜27）を大型分割より先に**: workspace 解決・ロギング初期化・auth は多数の
   サブシステムから参照されるため、正規経路を先に確立すると後続の分割で逆流（再重複）を防げる。
4. **大型分割（順位 28〜45）は基盤確立後に**: schema.py や AggregationStore の分割は工数 L・影響大のため、
   Mixin / 例外 / ロガーの方針が固まった後に実施する。順位 30 は順位 28 と、順位 46 は順位 28 と依存関係がある。
5. **リスク高・効果が間接的なものは最後**: 順位 49 の TestModel オプトイン化は多数のテストが暗黙依存する
   ためリスク高とし、テスト整備を伴う最終フェーズに置いた。

## 推奨フェーズ分け

### フェーズ 1: クイックウィンと前提整備（順位 1〜20）

潜在バグ修正・デッドコード削除・低リスクの小分割で早期に成果を出しつつ、循環参照解消・例外基底・
共通ロガーという後続フェーズの前提を整える。すべてリスク低で既存テストが安全網になる。

### フェーズ 2: 横断基盤の確立（順位 21〜27）

workspace 解決・ロギング/Logfire 初期化・auth・LLM 呼び出しの「正規経路」を一元化し、
`os.getenv` 直読みなどの AGENTS.md 違反を構造的に再発不能にする。後続の分割が逆戻りしないための土台。

### フェーズ 3: 大型ファイルの責務分割（順位 28〜45）

300 行ルール違反の主犯（schema.py 1,641 行、aggregation_store.py 907 行、execution_service.py 772 行
など）を、フェーズ 1・2 で確立した方針（Mixin / 例外 / ロガー / 正規経路）に沿って分割する。
公開 API は後方互換ファサードや再エクスポートで維持する。

### フェーズ 4: 仕上げとリスクの高い再設計（順位 46〜49）

レガシー変換層の撤去、IntegrationManager の再設計、TestModel 暗黙置換の解消など、依存の多い
変更を最後に実施する。あわせて構造化ログと Python 3.13 モダナイズの品質パスを全体に適用する。
