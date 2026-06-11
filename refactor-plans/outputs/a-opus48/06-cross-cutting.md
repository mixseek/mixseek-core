# 06. 横断課題（cross-cutting）

個別サブシステムに閉じず、リポジトリ全体に薄く広がる規約違反・一貫性の問題。
いずれも「最初に足場として片付けると後続リファクタが楽になる」性質を持つ。

## R14 — `os.getenv` / `os.environ` 直呼びの撲滅

- **対象**（config 配下の設定実装を除く、規約違反箇所）:
  - `ui/app.py`（37〜67行：ログ/Logfire 初期化で多数）
  - `ui/services/execution_service.py`（272・279・280行）
  - `ui/utils/db_utils.py`（38行：`MIXSEEK_WORKSPACE`）
  - `core/auth.py`（106・115・146・258・289・320・407・450〜487行：各種 API キー）
  - `cli/utils.py`（146・172・299・300行）
  - `cli/commands/team.py`（122行）・`exec.py`（158行）・`ui.py`（87〜129行で多数の `os.environ[...]=`）
  - `prompt_builder/formatters.py`（39行：`TZ`）
  - `observability/logfire.py`（148行）
- **問題**（AGENTS.md 違反 — 「直接 `os.getenv` せず共通設定モジュール経由で型安全にアクセス」）:
  - 環境変数の読み取り・**書き込み**（特に `cli/commands/ui.py` の `os.environ[...]=...` 群）が
    各所に散在し、キー名（`MIXSEEK_LOG_FORMAT`・`LOGFIRE_ENABLED` 等）が文字列リテラルで重複。
    型安全性も無く、デフォルト値の扱いも箇所ごとにバラバラ。
- **影響度**: 中（規約違反の解消＋設定アクセスの一元化。実行時挙動は基本不変）
- **リスク**: 中（env 書き込み系（ui.py）はプロセス全体の副作用があり、移行時に挙動差を出さない注意が必要）
- **推奨アプローチ**:
  - 既存の `utils/env.py`（`get_workspace_from_env` 等）と config モジュールを拡張し、
    ログ/Logfire/Workspace 系 env の**読み取りは型付きヘルパー**に集約（キー名定数も1箇所へ）。
  - `cli/commands/ui.py` の「子プロセス/Streamlit へ env を伝播する書き込み」は、
    `apply_runtime_env(settings)` のような**単一の適用関数**に括り、キー名の重複と書き込み順の暗黙依存を解消。
  - `db_utils.py` の workspace 取得は `utils/env.get_workspace_from_env()` へ統一（重複解消）。
- **関連テスト**: `tests/ui/`・`tests/cli/`・`tests/observability/`・`tests/agents/`。
  env 依存はテストで monkeypatch されている箇所が多く、ヘルパー集約で逆にテストも書きやすくなる。
- **工数**: M

## R15 — 共通ロガー＆構造化 JSON ログへの統一

- **対象**（`logging.getLogger` を直接生成している主な箇所）:
  - `orchestrator/orchestrator.py`・`round_controller/controller.py`・`evaluator/evaluator.py`・
    `evaluator/llm_client.py`・`workflow/executable.py`・`workflow/engine.py`・
    `framework/integration_hooks.py`・`config/manager.py`・`core/model_settings.py`・
    `ui/services/execution_service.py`・`ui/utils/duckdb_conn.py`・`utils/env.py`・
    `cli/commands/init.py`・`cli/commands/exec.py`・`agents/member/*` ほか（計19+ファイル）。
  - 生成方法も不統一：`logging.getLogger(__name__)`／`logging.getLogger("mixseek")`／
    `logging.getLogger("mixseek.workflow.engine")`／`logging.getLogger("mixseek.traces")` などが混在。
- **問題**（AGENTS.md 違反 — 「プロジェクト共通ロガーを使用し構造化 JSON ログを出力」）:
  - ロガー名の付け方がバラバラで、`observability/logging_setup.py`（167行）という
    集約セットアップが存在するにもかかわらず、各モジュールは標準 `logging` を直接叩いている。
  - 構造化ログ（`extra={...}`）の使用も箇所依存で一貫していない。
- **影響度**: 中（観測性の一貫性。実行ロジックは不変で安全に進めやすい）
- **リスク**: 低（ロガー取得を共通関数に置換するだけの機械的変更。挙動への影響が小さい）
- **推奨アプローチ**:
  - `observability` 配下に `get_logger(name)` の共通ファクトリを用意（命名規約：`mixseek.<subsystem>`）し、
    各モジュールの `logging.getLogger(...)` をそれに置換。
  - 構造化 JSON 出力は `logging_setup` のフォーマッタ設定に一本化し、各所は `extra=` で
    構造化フィールドを渡す作法に揃える（ガイドラインをドキュメント化）。
  - **最初に着手すべき項目**：純粋に機械的・低リスクで、以後の分割リファクタが
    「正しいロガー作法」の上で行えるようになる。
- **関連テスト**: `tests/observability/`（2ファイル）。ロガー差し替えは既存テストへの影響が小さい。
- **工数**: M

## 300行ルール違反ファイル 一覧（着手判断の早見表）

AGENTS.md「1ファイル300行以内」を超えるファイル（`tests/` 除く）。各候補との対応を併記。

| 行数 | ファイル | 対応候補 |
| ---: | --- | --- |
| 1,641 | `config/schema.py` | R1 |
| 907 | `storage/aggregation_store.py` | R5 |
| 887 | `config/manager.py` | R2 |
| 875 | `models/evaluation_config.py` | R6 |
| 819 | `config/views.py` | R3 |
| 772 | `ui/services/execution_service.py` | R7 |
| 576 | `framework/integration_hooks.py` | R9 |
| 570 | `core/auth.py` | R8 |
| 567 | `round_controller/controller.py` | R10 |
| 531 | `evaluator/evaluator.py` | （R6 と併走で確認）|
| 530 | `orchestrator/orchestrator.py` | R11 |
| 487 | `models/member_agent.py` | R12 |
| 407 | `cli/commands/config.py` | R13 |
| 393 | `workflow/executable.py` | 単独分割（優先度低）|
| 375 | `cli/formatters.py` | R13 |
| 361 | `cli/commands/exec.py` | R13 / R14 |
| 333 | `cli/commands/team.py` | R13 / R14 |
| 321 | `cli/utils.py` | R13 / R14 |
| 305 | `evaluator/metrics/base.py` | 単独分割（優先度低）|

> 共通ブリーフ記載の「300行超20個」に対し、本調査で `wc -l` 実測すると上表の19ファイルが
> 検出された（境界付近の差は計測タイミングによる軽微なもの）。`workflow/executable.py` と
> `evaluator/metrics/base.py` は特定候補に紐付けず、余力時の単独分割対象とする。
