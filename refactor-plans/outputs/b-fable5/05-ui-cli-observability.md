# UI / CLI / 観測性のリファクタリング計画（U1〜U4）

Streamlit UI（`ui/`）と Typer CLI（`cli/`）はともにエントリポイント層で、
observability（logfire/logging）初期化と環境変数の扱いに重複・暗黙結合が集中している。

## 責務と依存（現状把握）

- `ui/` … `app.py`（エントリ）＋ `pages/` ＋ `services/`（ロジック）＋ `components/`（描画）＋
  `models/`。サービス層と描画の分離は概ねできている
- `cli/` … `commands/` 8コマンド＋ `utils.py`（observability 初期化・エラー処理）＋
  `formatters.py`
- `observability/` … `setup_logging`（"mixseek" named logger、text/JSON 両対応）と
  `setup_logfire`。**設定クラス（`LoggingConfig`/`LogfireConfig`）は `config/` 側にあり**、
  初期化関数と設定が別パッケージに割れている

テスト被覆: ui 14・cli 17（contract テスト含む）・observability 4ファイル。
UI サービスは `tests/ui/test_execution_service.py` 等があるが、バックグラウンド実行系は
スレッド絡みで被覆が薄い可能性が高い。

---

## U1: `execution_service.py`(772行) の責務分割

- **対象**: `src/mixseek/ui/services/execution_service.py`
- **影響度: 中 / リスク: 中 / 工数: M**

### 問題（分析観点: 肥大化・責務・規約違反）

モジュールレベル関数9個に3つの責務が同居:

1. **進捗ファイル読み取り**（`_read_progress_from_file` 98行、
   `_get_failed_teams_from_progress_files`、`get_all_teams_execution_status`）
2. **オーケストレーション実行**（`run_orchestration` 140行、
   `run_orchestration_in_background` 98行 — スレッド生成・logfire 再初期化・
   asyncio.run・auth キャッシュクリアまで抱える）
3. **結果・ログ読み出し**（`get_execution_result` 110行、`get_recent_logs` 66行ほか）

加えて `os.getenv` 直接呼び出し（規約違反）と、logfire 初期化コードの3重複の一角
（U2 参照）。`run_orchestration` 内の Execution 構築は正常系/異常系でほぼ同型の二重実装。

### 推奨アプローチ

1. 3ファイルへ分割: `progress_service.py`（進捗ファイル読み）/ `execution_runner.py`
   （実行・スレッド管理）/ `execution_service.py`（結果・ログ読み出し、既存名を維持して
   再エクスポート）。
2. `run_orchestration` 内の logfire 再初期化ブロック（`execution_service.py:272-289`）は
   U2 の共通初期化 API 呼び出しに置換する（U2 とセットで実施）。
3. `ExecutionSummary → Execution` の変換を1関数に抽出し、正常系/異常系の二重構築を解消。
4. 進捗ファイルのスキーマを round_controller 側と共有のモデルに固定する
   （[04](04-execution.md) E2 で詳述。書き手と読み手が別ファイルの dict キーで
   暗黙結合している現状が最大の退行リスク源）。

### 関連テスト（安全網）

`tests/ui/test_execution_service.py`。バックグラウンド実行（スレッド + asyncio.run +
auth キャッシュクリア。Issue #197 対応の回帰防止コメントあり）は手を入れる前に
最低限のテスト（実行→ステータス遷移）を追加すること。

---

## U2: 観測性初期化（logfire/logging）の一本化

- **対象**: `cli/utils.py`（`setup_logfire_from_cli` 76行・`initialize_observability` 53行）、
  `ui/app.py:35-70`、`ui/services/execution_service.py:270-289`、`cli/commands/ui.py:87-129`
- **影響度: 高 / リスク: 中 / 工数: M**

### 問題（分析観点: DRY 違反・規約違反）

「環境変数（`LOGFIRE_ENABLED`/`MIXSEEK_LOG_FORMAT`/`MIXSEEK_LOG_FILE` 等）を読み、
`LogfireConfig.from_env()` と `setup_logfire`/`setup_logging` を呼ぶ」コードが
**CLI・UI app・UI バックグラウンドスレッドの3箇所**にコピーされている。
いずれも `os.getenv` 直接（規約違反）で、デフォルト値の解釈（`"1"`/`"true"` 判定）も
微妙に重複。新しいログ設定を足すたび3箇所の同期修正が必要になっている。

### 推奨アプローチ

1. `observability/__init__.py` に冪等な統合初期化 API を新設する:

   ```python
   def ensure_observability(*, force: bool = False) -> None:
       """LoggingConfig/LogfireConfig.from_env() を読み、setup_logging/setup_logfire を
       一度だけ実行する。スレッド再初期化は force=True で明示。"""
   ```

   環境変数の読み取りは既存の `LoggingConfig.from_env()`/`LogfireConfig.from_env()`
   （config モジュール内、規約準拠）に完全委譲し、呼び出し側から `os.getenv` を排除する。
2. CLI は引数 → 環境変数の変換を `initialize_observability` に残し、最終的な初期化は
   `ensure_observability` に委譲。UI app / バックグラウンドスレッドは
   `ensure_observability(force=True)` の1行になる。
3. `config/logfire.py`・`config/logging.py` と `observability/` の分割は維持してよいが、
   迷子防止のため `observability/README` 程度の docstring で「設定は config、実行は
   observability」と明記する。

### 関連テスト（安全網）

`tests/integration/test_logfire_integration.py`・`tests/config/test_logfire_config.py`・
`tests/observability/test_logging_setup.py` あり。冪等性（二重呼び出しで handler が
増えない）のテストを新 API に追加する。

---

## U3: CLI→UI の環境変数による暗黙の設定伝搬の明示化

- **対象**: `cli/commands/ui.py:111-129`、`ui/app.py`、`ui/utils/db_utils.py`
- **影響度: 中 / リスク: 高 / 工数: M**

### 問題（分析観点: 密結合・規約違反）

`mixseek ui` コマンドが `os.environ` に9個の変数（`LOGFIRE_*` 5個・`MIXSEEK_LOG_*` 3個・
`MIXSEEK_WORKSPACE`）を書き込み、Streamlit サブプロセス側の `ui/app.py` が
`os.getenv` で読み戻す。設定の受け渡し契約がコードのどこにも型として現れず、
変数名のタイポや片側だけの変更を静的に検知できない。

### 推奨アプローチ

Streamlit をサブプロセスで起動する以上、プロセス間の伝搬手段が環境変数になるのは妥当。
よって「環境変数を使わない」のではなく**契約を1箇所に定義する**:

1. `config/ui_bridge.py`（仮）に pydantic モデル `UIBridgeSettings` を定義し、
   `to_env() -> dict[str, str]` / `from_env() -> UIBridgeSettings` を持たせる。
   CLI 側は `os.environ.update(bridge.to_env())`、app 側は `UIBridgeSettings.from_env()` のみ。
2. 変数名はモデルの1箇所に集約され、mypy とユニットテスト（to_env→from_env の往復）で
   契約を保証できる。
3. U2 完了後に実施する（伝搬する変数の半分が observability 系のため、先に U2 で
   変数セットが安定してから取り組むほうが手戻りがない）。

リスクが「高」なのは、Streamlit の起動環境（dev container / 本番）でしか踏めない経路で、
自動テストでの再現が難しいため。実施時は手動の起動確認をチェックリスト化すること。

### 関連テスト（安全網）

`tests/ui/test_app_entrypoint.py`・`tests/contract/` の CLI contract。
往復変換のユニットテストを新設できる点が現状からの大きな改善。

---

## U4: `cli/commands/config.py` の長関数分割（クイックウィン）

- **対象**: `src/mixseek/cli/commands/config.py`（407行）
- **影響度: 低 / リスク: 低 / 工数: S**

### 問題（分析観点: 肥大化）

`config_show`（141行）と `config_init`（166行）は Typer コマンド関数に
引数解釈・分岐・サービス呼び出し・出力整形が直書きされている。
表示ロジック本体は `ConfigViewService`（[01](01-config.md) C3）に分離済みなので、
コマンド側は「オプション解釈 → サービス呼び出し → 出力」の薄い層に整えるだけでよい。

### 推奨アプローチ

出力形式（table/json/hierarchical）の分岐をディスパッチ表に、`config_init` の
テンプレート種別ごとの処理をヘルパー関数に抽出する。407行 → 300行未満を見込む。
C3 と同一エリアのため、C3 とまとめて実施してもよい。

### 関連テスト（安全網）

`tests/contract/test_help_contract.py`・`tests/e2e/test_config_workflow.py`・
`tests/integration/test_init_integration.py` が CLI 出力を固定しており、安全網は十分。
