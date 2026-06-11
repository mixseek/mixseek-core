# 04. CLI / UI

## R7 — `ui/services/execution_service.py` の分割

- **対象**: `src/mixseek/ui/services/execution_service.py`（772行・モジュール関数の集合）
- **問題**（肥大化 / 責務混在 / 規約違反）:
  - クラスを持たず、巨大なモジュール関数が並ぶ：`_read_progress_from_file`・
    `_get_failed_teams_from_progress_files`・`get_all_teams_execution_status`・
    `run_orchestration`（240〜382行＝約140行の長大関数）・`run_orchestration_in_background`・
    `get_execution_status`・`get_execution_result`（513〜625行＝約110行）・
    `get_team_ids_for_execution`・`get_recent_logs`。
  - 「進捗ファイルの読み取り」「オーケストレーション起動（同期/バックグラウンド）」「実行状態/結果の取得」
    「ログ取得」と複数関心事が1ファイルに同居。
  - `os.getenv("LOGFIRE_ENABLED")`・`MIXSEEK_LOG_FORMAT`・`MIXSEEK_LOG_FILE` を直呼び
    （272・279・280行）→ AGENTS.md 違反（R14 対象）。
  - `logging.getLogger` 直生成（R15 対象）。
- **影響度**: 中（UI の実行フロー中枢。ただし利用は UI ページに限定的）
- **リスク**: 中（バックグラウンド実行・進捗ファイル I/O は副作用が大きく、テストは2ファイルと薄め）
- **推奨アプローチ**:
  - 関心事ごとに分割：`progress_reader.py`（進捗ファイル読取系）、`runner.py`
    （`run_orchestration` / `run_orchestration_in_background`）、`status.py`（状態・結果・ログ取得）。
  - 長大関数 `run_orchestration` / `get_execution_result` は内部ステップを private 関数へ抽出し200行以内に。
  - ログ設定の env 参照は R14 のヘルパー経由に置換。
  - **テストが薄い**ため、分割前に主要関数の振る舞いテストを補強してから着手。
- **関連テスト**: `tests/ui/`（execution_service直接参照は2ファイル）。
- **工数**: L

## R13 — CLI コマンド／フォーマッタの分割

- **対象**: `src/mixseek/cli/commands/config.py`（407行）・`src/mixseek/cli/formatters.py`（375行）・
  `src/mixseek/cli/commands/exec.py`（361行）・`src/mixseek/cli/commands/team.py`（333行）・
  `src/mixseek/cli/utils.py`（321行）
- **問題**（肥大化 / 規約違反）:
  - 上記5ファイルが300行超。`cli/utils.py`・`cli/commands/team.py`・`exec.py`・`ui.py` は
    `os.getenv` / `os.environ` を直接読み書きしている（R14 対象）。
  - `formatters.py` は表示整形が一箇所に集まり肥大化。
- **影響度**: 低（CLI 層。内部分割で外部 I/F は不変に保てる）
- **リスク**: 低（Typer コマンド境界が明確で、サブコマンド単位に割りやすい）
- **推奨アプローチ**:
  - `config.py` はサブコマンド（show/list/get/set 等）単位、`formatters.py` は出力種別単位で分割。
  - `cli/utils.py` のログ/Logfire 設定の env 直読み（146・172・299・300行）と
    `commands/ui.py` の `os.environ[...]=...` 群（87〜129行：Logfire/Workspace/Log 設定の env 書き込み）を
    R14 の設定ヘルパーに集約。env を「プロセスへ書き込む」処理は副作用が大きいので、専用の
    `apply_runtime_env(settings)` のような単一窓口にまとめると見通しが良い。
- **関連テスト**: `tests/cli/`・`tests/unit/cli/`。
- **工数**: S（分割のみ。R14 と併せると M）

## 補足：UI のその他

- `ui/app.py`（124行）も `os.getenv` を多用（37〜67行：ログ/Logfire 初期化）。R14 で横断対応。
- `ui/utils/db_utils.py` の `os.getenv("MIXSEEK_WORKSPACE")`（38行）は
  既存の `utils/env.get_workspace_from_env()` に寄せられる（重複の解消）。
- UI コンポーネント／ページ群は概ね300行未満で当面問題なし。
