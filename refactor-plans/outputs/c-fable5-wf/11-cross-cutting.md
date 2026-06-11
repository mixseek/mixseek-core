# リファクタリング計画: 横断テーマ（リポジトリ全体）

## 概要（責務と依存の現状）

本ドキュメントはサブシステム個別ではなく、リポジトリ横断のテーマを扱う。
対象は (a) 環境変数アクセス経路、(b) ロガー利用の一貫性、(c) サブシステム間の重複、
(d) 300行超ファイルの実測、(e) Python 3.13 で簡潔化できる古いパターン、(f) 例外設計の一貫性。

横断インフラの現状構成は以下のとおり。

- 環境変数の正規経路: `src/mixseek/config/`（`schema.py` の pydantic-settings、`env_mappers.py`、
  `logging.py` / `logfire.py` の `from_env()`）と `src/mixseek/utils/env.py`（workspace 解決）
- ロギング基盤: `src/mixseek/observability/logging_setup.py` が統一ロガー `"mixseek"` を初期化し、
  `JsonFormatter` / `TextFormatter` で構造化出力を提供。各モジュールは `logging.getLogger(__name__)` で
  `mixseek.*` 階層ロガーを取得しており、ロガー取得自体は概ね一貫している
- 例外: ルート `src/mixseek/exceptions.py` のほか、`evaluator/exceptions.py`、
  `round_controller/exceptions.py`、`workflow/exceptions.py` が存在。一方で `core/auth.py`、
  `storage/aggregation_store.py`、`orchestrator/models.py` 等にインライン定義の例外が散在
- LLM 呼び出し: `core/auth.py`（認証済みモデル生成）と `core/model_settings.py`（設定合成）を
  evaluator / round_controller が共用するが、Agent 生成〜実行〜例外ラップは各所で重複実装

## 評価サマリ（観点1〜5）

### 観点1: 責務と依存

- 正規経路は存在する（config モジュール・utils/env.py・observability）が、利用側が経路を迂回して
  直接 `os.getenv` する箇所が多く、「正規経路があるのに使われない」状態が主問題。
- `cli` → `os.environ` 書き込み → 下流（UI/Orchestrator）が `os.getenv` で読む、という
  環境変数をプロセス内 IPC として使う設計（`cli/commands/ui.py:111-129`、`exec.py:158`、
  `team.py:122`、`observability/logfire.py:148`）が依存関係を不可視にしている。

### 観点2: 設計上の臭い（DRY 違反・重複）

- **ロギング初期化の三重実装**: `LoggingConfig.from_env()`（`config/logging.py:67-112`）が存在するのに、
  `ui/app.py:36-47` と `ui/services/execution_service.py:272-286` が `os.getenv` で同等ロジックを再実装。
  `cli/utils.py:143-194`（`setup_logfire_from_cli`）と `cli/commands/ui.py:87-129` にも類似分岐がある。
- **workspace 解決の三重実装**: `utils/env.py:14-59`（正規）、`ui/utils/workspace.py`（正規へ委譲、OK）、
  `ui/utils/db_utils.py:21-44`（`os.getenv` + `ValueError` で独自再実装。例外型も正規経路の
  `WorkspacePathNotSpecifiedError` と不一致）。
- **構造化 LLM 呼び出しの二重実装**: `evaluator/llm_client.py:96-141` と
  `round_controller/judgment_client.py:88-126` が「`create_authenticated_model` →
  `build_model_settings` → `Agent(output_type=..., retries=...)` → `run` →
  `except Exception` で独自 API エラーにラップ」という同型コード。例外クラス
  `EvaluatorAPIError` と `JudgmentAPIError` も属性・docstring までほぼ同型。
- **認証検証の五重同型コード**: `core/auth.py` の `validate_google_ai_credentials`（L109）/
  `validate_anthropic_credentials`（L252）/ `validate_openai_credentials`（L283）/
  `validate_grok_credentials`（L314）は「未設定 / 空 / 長さ20未満」の3チェックがコピペ同型。
  さらに `get_auth_info`（L429-487）が同じ環境変数参照を再度列挙している。

### 観点3: AGENTS.md 自己ルール違反

- **`os.getenv` / `os.environ` 直接使用**: `src/` 全体で約60箇所・15ファイル（grep 実測）。
  config 配下と `utils/env.py` の約20箇所は正規経路側の実装なので適法。違反側の主な内訳:
  - `core/auth.py`: 13箇所（L106, 115, 146, 258, 289, 320, 407, 450-487）
  - `ui/app.py`: 8箇所（L37-67）、`ui/services/execution_service.py`: 3箇所（L272-280）
  - `ui/utils/db_utils.py:38`、`cli/utils.py`: 4箇所（L146, 172, 299-300）
  - `cli/commands/ui.py`: 読み書き計13箇所、`exec.py:158` / `team.py:122`（書き込み）
  - `prompt_builder/formatters.py:39`（`TZ` 読み取り）
- **1ファイル300行超**: `wc -l` 実測で **19ファイル**（ブリーフ記載は20）。
  schema.py 1,641 / aggregation_store.py 907 / manager.py 887 / evaluation_config.py 875 /
  views.py 819 / execution_service.py 772 / integration_hooks.py 576 / auth.py 570 /
  controller.py 567 / evaluator.py 531 / orchestrator.py 530 / member_agent.py 487 /
  cli/commands/config.py 407 / workflow/executable.py 393 / cli/formatters.py 375 /
  cli/commands/exec.py 361 / cli/commands/team.py 333 / cli/utils.py 321 /
  evaluator/metrics/base.py 305。個別の分割計画は各サブシステム担当に委ねる。
- **構造化 JSON ログ**: 基盤（`JsonFormatter` + `extra` フィールド昇格）はあるが、利用側の
  `logger.*` 呼び出し約105箇所のうち `extra=` 使用は7箇所のみ。f-string 直埋め込みが61箇所あり、
  JSON モードでメッセージ内に値が埋もれフィールド化されない（規約の趣旨に反する）。

### 観点4: エラー処理・型

- 共通基底例外（`MixseekError` 等）が無く、各例外が `Exception` / `ValueError` を直接継承。
  横断的に `except MixseekError` で扱えない。`except Exception` の広域捕捉が92箇所ある一方、
  `raise ... from` は34箇所で、原因チェーンの保持が不徹底。
- 同義の例外が `ValueError`（`db_utils.py:40`）と `WorkspacePathNotSpecifiedError`
  （`utils/env.py:59`）に分裂しており、呼び出し側のハンドリングが安定しない。
- 型注釈は概ね現代的（`X | None` 使用、`Optional[]` 0件・`Union[]` はコメント1件のみ）。
  残る古いパターンは、引用符による前方参照の戻り値注釈 41件（`typing.Self` で置換可。例:
  `config/logging.py:67` の `-> "LoggingConfig"`）と、`TypeVar` 2件
  （`config/manager.py:31`、`cli/utils.py:25`。PEP 695 ジェネリクス構文で置換可）、
  `config/logging.py:90,104` の `# type: ignore[assignment]` 程度。

### 観点5: テスト被覆

- ロギング/Logfire: `tests/observability/test_logging_setup.py`（34件）、
  `tests/config/test_logging.py`（22件）、`tests/cli/commands/test_ui_logfire.py` /
  `test_exec_logfire.py`、`tests/ui/integration/test_logfire_integration.py` と厚い。
- 認証: `tests/unit/test_auth.py`（43件）が厚く、テーブル駆動化の安全網になる。
- workspace 解決: `tests/unit/test_env.py`（8件）、`tests/ui/test_workspace_utils.py`（4件）、
  `tests/ui/test_duckdb_conn.py` あり。
- LLM クライアント: `tests/evaluator/unit/test_llm_client.py` / `test_exceptions.py`、
  `tests/unit/round_controller/test_improvement_judgment.py` 等あり。
- 全体として横断リファクタの安全網は良好。ただし `ui/app.py` のモジュールレベル初期化は
  `test_app_entrypoint.py` 程度で被覆が薄く、候補1では先に振る舞いテスト追加が望ましい。

## リファクタリング候補

### 候補1: ロギング/Logfire 初期化ブートストラップの一元化

- **対象**: `src/mixseek/ui/app.py:33-80`、`src/mixseek/ui/services/execution_service.py:270-289`、
  `src/mixseek/cli/utils.py:113-321`、`src/mixseek/cli/commands/ui.py:80-129`、
  `src/mixseek/observability/`（新設 `bootstrap.py` の置き場）
- **問題**（観点2: DRY 違反 / 観点3: `os.getenv` 直接使用）: `LoggingConfig.from_env()` が存在するのに
  UI 側2箇所が `os.getenv` で設定構築を再実装。CLI 側にも Logfire 有効判定・format 解決の同型分岐が
  重複し、デフォルト値（`"1"` vs `"true"`）の微妙な差異がバグ温床になっている。
- **影響度**: 高（ログ/観測の初期化は全実行経路に関わる）
- **リスク**: 中（Streamlit セッション・バックグラウンドスレッド再初期化など実行文脈依存の挙動あり）
- **推奨アプローチ**: `observability/bootstrap.py` に `init_observability(source: LoggingConfig, ...)` を新設し、
  「env からの設定読込は `LoggingConfig.from_env()` / `LogfireConfig.from_env()` のみ」
  「setup_logging → setup_logfire の順序保証」を1関数に集約。UI/CLI は薄い呼び出しに置換。
  あわせて `cli/utils.py`（321行）の縮減にも寄与する。
- **関連テスト**: `tests/observability/test_logging_setup.py`、`tests/config/test_logging.py`、
  `tests/cli/commands/test_ui_logfire.py` / `test_exec_logfire.py`。`ui/app.py` 分は事前にテスト追加。
- **工数感**: M

### 候補2: workspace 解決と環境変数アクセスの正規経路統一

- **対象**: `src/mixseek/ui/utils/db_utils.py:21-44`、`src/mixseek/utils/env.py`、
  `src/mixseek/cli/commands/{ui,exec,team}.py` の `os.environ` 書き込み、
  `src/mixseek/prompt_builder/formatters.py:39`
- **問題**（観点2: 重複 / 観点3: 規約違反 / 観点4: 例外不一致）: workspace 解決が
  `db_utils.get_workspace_path()` で独自再実装され、失敗時例外も `ValueError` と
  `WorkspacePathNotSpecifiedError` に分裂。CLI が `os.environ` 書き込みで下流へ値を渡す暗黙依存もある。
- **影響度**: 中
- **リスク**: 低（読み取り統一は機械的。`os.environ` 書き込みの除去はサブプロセス境界の確認が必要なため
  第2段階に分離する）
- **推奨アプローチ**: 第1段階で `db_utils.get_workspace_path` を削除し `utils/env.py` 経由に統一、
  例外型を `WorkspacePathNotSpecifiedError` に揃える。`formatters.py` の `TZ` も config 経由に移す。
  第2段階で `os.environ` 書き込みを棚卸しし、同一プロセス内の受け渡しは引数渡しへ置換
  （Streamlit サブプロセス起動など真に env が必要な箇所のみ明示的に残しコメントで根拠を書く）。
- **関連テスト**: `tests/unit/test_env.py`、`tests/ui/test_workspace_utils.py`、
  `tests/ui/test_duckdb_conn.py`、`tests/unit/cli/test_team_command.py` 等
- **工数感**: M

### 候補3: core/auth.py の資格情報検証テーブル駆動化

- **対象**: `src/mixseek/core/auth.py`（570行。L109-138, 252-343 の validate 5関数、L429-504 の
  `get_auth_info`、L345-427 の `create_authenticated_model`）
- **問題**（観点2: 同型コードのコピペ / 観点3: 300行超 + `os.getenv` 13箇所）: API キー系4プロバイダの
  検証が「未設定/空/短すぎ」の同型3チェックの繰り返し。`get_auth_info` が同じ env 参照を再列挙し、
  プロバイダ追加時に3箇所の同期修正が必要。
- **影響度**: 中（全 LLM 呼び出しの前提だが外部仕様は不変）
- **リスク**: 低（`tests/unit/test_auth.py` 43件の安全網が厚い）
- **推奨アプローチ**: `ProviderSpec`（env キー名・プロバイダ名・suggestion 文言）のレジストリを定義し、
  API キー検証を共通関数1つに畳み込む。env 読み取りは config 層の薄いアクセサに集約して
  `os.getenv` 直接呼びを解消。あわせて `auth.py` を `providers.py` / `validation.py` 等へ分割し
  300行以下化。Vertex AI のファイル検証のみ個別関数として残す。
- **関連テスト**: `tests/unit/test_auth.py`（43件）、`tests/unit/config/preflight/test_auth_validator.py`
- **工数感**: M

### 候補4: 構造化 LLM 呼び出しヘルパーの共通化

- **対象**: `src/mixseek/evaluator/llm_client.py:96-141`、
  `src/mixseek/round_controller/judgment_client.py:88-126`、`src/mixseek/core/`（新設ヘルパー置き場）
- **問題**（観点2: DRY 違反 / 観点4: 例外設計の分裂）: 「認証モデル生成 → ModelSettings 合成 →
  Agent 生成 → 実行 → `except Exception` を独自 API エラーへラップ」が二重実装。
  `EvaluatorAPIError` / `JudgmentAPIError` も属性までほぼ同型で、リトライ情報の持ち方だけ微妙に違う。
- **影響度**: 中（評価とラウンド判定の両方の品質・保守性に直結）
- **リスク**: 中（例外メッセージ・型に依存するテスト/呼び出し側の追従が必要）
- **推奨アプローチ**: `core/llm_call.py`（仮）に `run_structured_agent(model_id, output_type,
  instructions, settings...) -> BaseModel` を新設し、共通基底 `LLMAPIError`（provider/retry_count 属性）
  を導入。`EvaluatorAPIError` / `JudgmentAPIError` はこれを継承する後方互換サブクラスとして残す。
- **関連テスト**: `tests/evaluator/unit/test_llm_client.py` / `test_exceptions.py`、
  `tests/unit/round_controller/test_improvement_judgment.py`
- **工数感**: M

### 候補5: 例外階層の統一（MixseekError 基底の導入）

- **対象**: `src/mixseek/exceptions.py`、`src/mixseek/core/auth.py:42`、
  `src/mixseek/storage/aggregation_store.py:41-46`、`src/mixseek/orchestrator/models.py:94`、
  各サブシステムの `exceptions.py`
- **問題**（観点4: 例外設計の一貫性）: 共通基底が無く `Exception` / `ValueError` 直継承が混在。
  例外定義場所も「専用 exceptions.py」と「実装ファイル内インライン」で不統一
  （aggregation_store.py / orchestrator/models.py / auth.py）。広域 `except Exception` が92箇所あり、
  フレームワーク例外だけを選択的に扱う手段がない。
- **影響度**: 中（横断的なエラーハンドリング・CLI 終了コード設計の土台になる）
- **リスク**: 低（基底クラス追加は後方互換。インライン例外の移動は import 経路の互換 re-export で吸収）
- **推奨アプローチ**: `mixseek/exceptions.py` に `MixseekError` を定義し、既存カスタム例外の基底を
  順次差し替える。インライン定義の例外は各サブシステムの `exceptions.py` へ移動し、旧位置から
  re-export して互換維持。`raise ... from` の徹底を ruff（`B904`）で機械的に担保する。
- **関連テスト**: `tests/evaluator/unit/test_exceptions.py` ほか各サブシステムの例外テスト。
  基底変更は既存テストがそのまま回帰検知になる。
- **工数感**: M

### 候補6: 構造化ログの徹底と型注釈モダナイズ（品質パス）

- **対象**: `src/` 全体の `logger.*` 呼び出し（f-string 直埋め込み61箇所）、
  引用符前方参照の戻り値注釈41箇所、`config/manager.py:31` / `cli/utils.py:25` の `TypeVar`
- **問題**（観点3: 構造化 JSON ログ未活用 / 観点2: Python 3.13 で簡潔化できる古いパターン）:
  `JsonFormatter` は `extra` をトップレベルキー化する設計なのに、利用側の `extra=` 使用が7箇所のみで
  JSON ログの検索性が活きていない。型注釈は `typing.Self`（3.11+）と PEP 695（3.12+）で簡潔化できる。
- **影響度**: 中（観測性の実利は大きいが、機能挙動は不変）
- **リスク**: 低（機械的変換が中心。ログ文言に依存するテストの修正のみ注意）
- **推奨アプローチ**: ruff に `flake8-logging-format`（`G` 系）ルールを追加して f-string ログを検出し、
  値を `extra=` へ移すパターンで段階的に書き換える（高頻度経路の orchestrator / round_controller /
  evaluator から着手）。型注釈は `-> "X"` → `-> Self`、`TypeVar` → PEP 695 を ruff `UP` 系 + 一括 PR で対応。
- **関連テスト**: `tests/observability/test_logging_setup.py`（JsonFormatter の extra 昇格を検証済み）。
  ログ文言アサートを持つテストは grep で洗い出して同時修正。
- **工数感**: M

### 補足: 300行超ファイル（19件・実測）について

横断テーマとしては候補化せず実測リストの提示に留める（分割設計は各サブシステム担当の計画と統合すること）。
ただし候補1は `cli/utils.py`（321行）、候補3は `core/auth.py`（570行）の300行以下化に直接寄与する。
