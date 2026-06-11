# mixseek-core リファクタリング計画（パターンA / Opus 4.8 単独）

> 本ディレクトリは **読み取り専用調査の成果物**です。コードは一切変更していません。
> mixseek-core リポジトリ全体（`src/` 159ファイル・約25,500行、`tests/` 180ファイル）を
> 単独で読み込み、共通ブリーフ（`refactor-plans/prompts/_shared-brief.md`）の分析観点
> （責務と依存 / 設計上の臭い / 自己ルール違反 / エラー処理・型 / テスト被覆）に沿って
> 優先度付きのリファクタリング候補を整理した。

## 全体所感

- **テスト資産は厚い**（`tests/` 180ファイル、主要モジュールは軒並み複数テストが参照）。
  これは大規模リファクタの安全網として強い追い風で、「テストを保ったまま内部分割する」型の
  リファクタを低リスクで進められる。
- 一方で **AGENTS.md の自己ルール（1ファイル300行・1関数200行・`os.getenv`直呼び禁止・
  共通ロガー使用・構造化JSONログ）は広範に破られている**。300行超ファイルが20個、
  `os.getenv`/`os.environ` 直呼びが config 外で多数、ロガーは `logging.getLogger` 直生成が散在。
- 設計面の最大の負債は **「新旧2系統の設定モデルが並存」**（`config/schema.py` の `*Settings` と
  `models/evaluation_config.py` の `EvaluationConfig`、両者をつなぐ移行ブリッジ関数）。
  これは肥大化と DRY 違反の根本原因になっている。
- `storage/aggregation_store.py` の **`_xxx_sync` + `async xxx`（retry/例外ラップ）二重定義**は
  典型的な機械的重複で、デコレータ化で大幅に縮小できる。

## ドキュメント構成（インデックス）

| ファイル | 内容 |
| --- | --- |
| [01-config-subsystem.md](01-config-subsystem.md) | `config/` 一式（schema/manager/views/sources）— 最大の肥大化領域 |
| [02-storage-async.md](02-storage-async.md) | `storage/aggregation_store.py` の sync/async 二重定義と責務分割 |
| [03-models-evaluator.md](03-models-evaluator.md) | 設定モデルの新旧二重化（evaluation_config ↔ EvaluatorSettings）、member_agent |
| [04-cli-ui.md](04-cli-ui.md) | `ui/services/execution_service.py`、CLI コマンド群の分割 |
| [05-core-framework.md](05-core-framework.md) | `core/auth.py`、`framework/integration_hooks.py`、orchestrator/controller の長大メソッド |
| [06-cross-cutting.md](06-cross-cutting.md) | 横断課題：`os.getenv`撲滅・共通ロガー/構造化ログ統一・300行ルール総覧 |

## 優先度サマリ表

影響度＝直すと効く範囲の広さ / リスク＝壊しやすさ・テスト網の薄さ。
推奨着手順は「低リスクな足場固め → 安全網が効く分割 → 高リスクな統合」の順で設計。

| # | 候補 | 対象 | 影響度 | リスク | 工数 | 推奨着手順 |
| --- | --- | --- | :---: | :---: | :---: | :---: |
| R15 | 共通ロガー＆構造化JSONログへ統一 | 横断（`logging.getLogger`散在19+箇所） | 中 | 低 | M | 1 |
| R14 | `os.getenv`直呼び撲滅（config経由へ） | ui/cli/core/prompt_builder | 中 | 中 | M | 2 |
| R3 | `ConfigViewService` の表示責務分離 | `config/views.py` (819行) | 中 | 低 | M | 3 |
| R1 | `schema.py` を Settings クラス単位で分割 | `config/schema.py` (1,641行) | 高 | 中 | L | 4 |
| R4 | `*TomlSource` の共通基底抽出 | `config/sources/*` (8クラス重複) | 中 | 中 | M | 5 |
| R5 | sync/async 二重定義のデコレータ化＋分割 | `storage/aggregation_store.py` (907行) | 高 | 中 | L | 6 |
| R2 | `ConfigurationManager` の loader 重複統合 | `config/manager.py` (887行) | 中 | 中 | M | 7 |
| R8 | プロバイダ別に auth 分割 | `core/auth.py` (570行) | 中 | 中 | M | 8 |
| R10 | 長大メソッドの抽出 | `round_controller/controller.py` (567行) | 中 | 中 | M | 9 |
| R11 | `_execute_impl` 等の抽出 | `orchestrator/orchestrator.py` (530行) | 中 | 中 | M | 10 |
| R6 | 設定モデル新旧二系統の統合 | `evaluation_config.py` ↔ `EvaluatorSettings` | 高 | 高 | L | 11 |
| R7 | UI 実行サービスの分割 | `ui/services/execution_service.py` (772行) | 中 | 中 | L | 12 |
| R9 | hooks 分割＋グローバル singleton 解消 | `framework/integration_hooks.py` (576行) | 低 | 低 | M | 13 |
| R12 | `EnvironmentConfig` 等の分離 | `models/member_agent.py` (487行) | 低 | 低 | S | 14 |
| R13 | CLI コマンド／フォーマッタ分割 | `cli/commands/config.py`・`cli/formatters.py` | 低 | 低 | S | 15 |

工数の目安: **S** = 半日〜1日 / **M** = 1〜3日 / **L** = 1週間前後（テスト確認含む）。

## 進め方の指針

1. **R15・R14 を最初に**：ロガーと環境変数アクセスの統一は規約違反の解消であると同時に、
   後続の分割で「どこからでも同じ作法で設定/ログを使う」前提を作る足場になる。純粋に機械的で安全。
2. **R3 → R1 → R4 → R2**：config サブシステムを上流から整地。views（表示）は依存が少なく安全に先行でき、
   その後 schema/sources/manager をクラス単位で割っていく。いずれもテストが厚い（schema:56・manager:26参照）。
3. **R5**：storage の二重定義はデコレータ抽出で局所的・機械的。storage テスト12ファイルが安全網。
4. **R10・R11・R8**：オーケストレーション中核の長大メソッド抽出。テスト網が厚い（orchestrator:33・controller:15）。
5. **R6 は最後**：新旧モデル統合は API 互換（公開シンボル）に影響しうる最も慎重を要する作業。
   先行リファクタで周辺を整えた後、移行ブリッジを段階的に畳む。
6. R7・R9・R12・R13 は独立性が高く、任意のタイミングで差し込める「掃除」項目。

各候補の詳細（問題・推奨アプローチ・関連テスト・工数）は上記の個別ドキュメントを参照。
