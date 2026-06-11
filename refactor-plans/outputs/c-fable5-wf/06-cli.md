# リファクタリング計画: cli サブシステム

## 概要（責務と依存の現状）

`src/mixseek/cli/` は Typer ベースの CLI エントリポイント層。構成は以下の通り（wc -l 実測）。

| ファイル | 行数 | 責務 |
| --- | --- | --- |
| `commands/config.py` | 407 | config show/list/init サブコマンド |
| `formatters.py` | 375 | Member Agent 結果の整形（structured/json/text/csv） |
| `commands/exec.py` | 361 | オーケストレーション実行＋結果・リーダーボード表示 |
| `commands/team.py` | 333 | チーム実行（開発用）＋評価＋DB保存 |
| `utils.py` | 321 | 終了コード定数・排他オプション・ロギング/Logfire初期化 |
| `commands/member.py` | 238 | Member Agent 単体実行（開発用） |
| `commands/evaluate_helper.py` | 186 | 評価の共通ヘルパー（team/evaluate で共用） |
| `commands/ui.py` | 148 | Streamlit 起動（環境変数経由で設定伝搬） |
| `commands/init.py` | 146 | ワークスペース初期化 |
| `commands/evaluate.py` | 114 | LLM-as-a-Judge 評価コマンド |
| `common_options.py` | 78 | 共通 Typer オプション定義（DRY 対応済み） |
| `main.py` | 68 | コマンド登録エントリポイント |

依存方向: `cli → config(ConfigurationManager/views/preflight) / orchestrator / agents / evaluator /
storage / observability / utils.env`。公開物は `mixseek.cli.main:app`（コンソールスクリプト）のみで、
下位層からの逆依存はなく方向は健全。`common_options.py` と `initialize_observability()` による
共通化は既に一定進んでいるが、ワークスペース解決と Logfire 設定構築に重複が残る。

## 評価サマリ（観点1〜5）

### 観点1: 責務と依存
- コマンド層としての層分離は概ね良好。ただし exec.py / team.py はコマンド定義・実行制御・
  結果表示（テキスト/JSON/リーダーボード）の3責務を1ファイルで担い肥大化。
- ワークスペース解決が3系統併存: exec.py:147-158（ConfigurationManager→失敗時CLI引数）、
  team.py:100-122（ほぼ同一の独自実装）、member.py:160 / evaluate.py:72（`utils.env.get_workspace_path`）。
  ui.py:76-77 は UISettings 経由の第4の経路。

### 観点2: 設計上の臭い（肥大化・DRY違反・古いパターン）
- **Logfire プライバシーモード決定の重複**: utils.py:150-161 と ui.py:97-108 に同一の if/elif 連鎖。
  ui.py:93 と utils.py:146 の `LOGFIRE_PROJECT` 判定も重複。
- **`os.environ[WORKSPACE_ENV_VAR] = ...` の重複**: exec.py:158、team.py:122（同一コメント
  「Issue #273 fix」付きでコピーされている）。
- **デッドコード**: `formatters.py` の `ProgressFormatter`（341-375行）は src 内で未使用
  （参照は tests/unit/test_formatters.py のみ）。utils.py の `exit_with_error`/`exit_success`
  （38-58行）も src/tests 双方で未使用。
- **古いパターン**: config.py:357-373 に Python 3.9 未満向け `pkgutil` フォールバック
  （プロジェクトは Python 3.13 のため不要）。formatters.py の `ResultFormatter` は
  staticmethod のみのクラス（モジュール関数で十分）。`_format_message_history`
  （75-133行）は `hasattr`/クラス名文字列比較による型分岐で、isinstance / match 文に置換可能。

### 観点3: AGENTS.md 自己ルール違反
- **300行超**: config.py(407) / formatters.py(375) / exec.py(361) / team.py(333) / utils.py(321) の5件。
  1関数200行超はなし（最大は team.py `_execute_team_command` の166行、config.py `config_init` の約145行）。
- **os.getenv / os.environ 直接使用**: utils.py:146,172,299,300、ui.py:87,93,111-129、
  exec.py:158、team.py:122。規約上は共通設定モジュール経由が必須。
  特に utils.py:300 と ui.py:87 の `os.getenv("MIXSEEK_LOG_FORMAT", "text")` は完全重複。
- **共通ロガー/構造化JSONログ**: CLI 層はユーザ向け出力に typer.echo を使うのは妥当だが、
  内部ログを出しているのは init.py:20 の `logging.getLogger(__name__)` のみで様式が不統一
  （exec.py:31 は logger 定義のみで未使用）。

### 観点4: エラー処理・型
- **typer.Exit の握りつぶし（軽微なバグ）**: `typer.Exit` は `Exception` のサブクラスのため、
  config.py の `except Exception`（172,235,404行）が内部の `raise typer.Exit(code=1)` を捕捉し、
  空メッセージの `Error: ` 行を二重出力して Exit(1) に変換する。exec.py:217-218 は
  `except typer.Exit: raise` ガードを持つが config.py / 他には無く、方針が不統一。
- 終了コードの意味もコマンド間で不統一（exec: 部分成功=1/全失敗=2、member: エラー=1、
  team: 全失敗=2、usage error は 2 と 1 が混在）。utils.py に定数はあるが大半は数値直書き。
- 型注釈はほぼ網羅されているが、`mutually_exclusive_group() -> Any`（utils.py:61）は
  Callable を返すべき箇所で Any に逃げている。

### 観点5: テスト被覆
- 被覆は比較的厚い: tests/unit/cli/test_config_commands.py(1,856行)、test_exec_dry_run.py(279行)、
  test_exec_exit_code.py(341行)、test_team_command.py(368行)、tests/cli/commands/test_exec_logfire.py(182行)、
  test_ui_logfire.py(224行)、tests/unit/test_formatters.py(308行)、integration/contract 多数。
- ギャップ: utils.py のヘルパー（`initialize_observability`、`mutually_exclusive_group`、
  `setup_logging_from_cli`）の直接ユニットテストがなく、exec/ui の logfire テスト経由の間接被覆のみ。
  member.py は integration/contract のみで unit テストなし。evaluate_helper.py の単体テストもなし。

## リファクタリング候補

### 候補1: ワークスペース解決と環境変数伝搬の共通化
- **対象**: `commands/exec.py:145-158`、`commands/team.py:100-122`、`commands/ui.py:74-84,123`、
  `commands/member.py:160`、`commands/evaluate.py:72`
- **問題**（観点1,2,3）: ワークスペース解決ロジックが4系統併存し、exec/team は同一コードの
  コピー。`os.environ[WORKSPACE_ENV_VAR]` 直書き（規約違反）も2箇所に重複。
  挙動差（失敗時 fallback するか即エラーか）が暗黙的でコマンドごとに異なる。
- **影響度**: 高（全コマンドの起動経路に関わり、設定解決の一貫性に直結）
- **リスク**: 中（各コマンドの微妙な挙動差を仕様として明文化する必要がある）
- **推奨アプローチ**: `cli/utils.py`（または新設 `cli/workspace.py`）に
  `resolve_workspace(cli_arg, *, required: bool)` を新設し、ConfigurationManager 経由の解決と
  環境変数伝搬（config 層に setter を用意して直書きを排除）を一元化。各コマンドは1行呼び出しに置換。
- **関連テスト**: test_exec_dry_run/test_exec_exit_code/test_team_command/test_ui_logfire が
  workspace 解決経路を間接被覆。新ヘルパーの unit テストを先に追加（TDD）。
- **工数感**: M

### 候補2: Logfire初期化ロジックの重複解消とenv直読みの集約
- **対象**: `cli/utils.py:119-194,299-300`、`commands/ui.py:86-129`
- **問題**（観点2,3）: プライバシーモード決定の if/elif 連鎖が utils.py:150-161 と ui.py:97-108 で
  重複（DRY違反）。`os.getenv("LOGFIRE_*")`/`os.getenv("MIXSEEK_LOG_FORMAT")` の直読みが
  AGENTS.md 規約違反。ui.py は Streamlit 子プロセスへの伝搬のため環境変数を直接書き込んでおり、
  設定の流れが追いにくい。
- **影響度**: 中（観測性設定の一貫性。機能追加時の二重修正リスクを解消）
- **リスク**: 中（環境変数経由の Streamlit 連携があるため、伝搬仕様の回帰に注意）
- **推奨アプローチ**: CLI フラグ→`LogfireConfig` 変換を `config/logfire.py` 側の
  ファクトリ（例: `LogfireConfig.from_cli_flags()`）へ移動し両者から利用。
  環境変数の読み書きは config 層の専用関数（export_to_env / from_env）に閉じ込める。
- **関連テスト**: tests/cli/commands/test_exec_logfire.py、test_ui_logfire.py が厚く、安全網あり。
- **工数感**: M

### 候補3: utils.py の責務分割とデッドコード削除
- **対象**: `cli/utils.py`（321行）
- **問題**（観点2,3,5）: 終了コード定数・開発警告・排他オプション callback・ロギング/Logfire
  初期化という無関係な責務が同居し300行超。`exit_with_error`/`exit_success`（38-58行）は未使用。
  `mutually_exclusive_group() -> Any`（61行）の戻り値型が Any。ヘルパーの直接ユニットテストなし。
- **影響度**: 中（CLI 全コマンドが import する共通基盤の見通し改善）
- **リスク**: 低（import パス変更のみ。利用箇所は cli 内に閉じる）
- **推奨アプローチ**: `cli/observability_setup.py`（setup_logging_from_cli / setup_logfire_from_cli /
  initialize_observability / validate_logfire_flags）と `cli/options_support.py`
  （mutually_exclusive_group、戻り値型を Callable に修正）に分割。デッドコードは削除し、
  終了コード定数の利用を各コマンドに展開（数値直書きの置換は候補4と併せて実施可）。
- **関連テスト**: 直接テストがないため、分割前に utils 単体テストを新規作成してから移動（TDD）。
- **工数感**: S

### 候補4: config.py の例外処理修正と config_init 分割
- **対象**: `commands/config.py`（407行、config_init は約145行）
- **問題**（観点2,3,4）: ①`except Exception`（172,235,404行）が `typer.Exit` を捕捉し、
  空の `Error: ` を二重出力して終了コードを上書きし得る（exec.py:217 のようなガードがない）。
  ②config_init が workspace 解決→component 決定→出力パス決定→存在チェック→テンプレート生成→
  メッセージ表示の6段を直列に持つ。③357-373行に Python 3.13 では不要な `pkgutil`
  フォールバックと `importlib.resources` の AttributeError 分岐。④ファイル300行超。
- **影響度**: 中（終了コードはスクリプト連携の契約。表示の正確性にも関わる）
- **リスク**: 低（unit テストが1,856行と最も厚く、安全網が強い）
- **推奨アプローチ**: 全ハンドラに `except typer.Exit: raise` を追加（または広域 try を撤去し
  失敗し得る箇所のみ局所 try に変更）。config_init をステップごとの私的関数
  （_resolve_output_path / _generate_template 等）に分割し、prompt_builder 特別扱いは
  TemplateGenerator 側へ吸収。pkgutil フォールバックは削除。必要なら show/list/init を
  ファイル分割し300行未満化。
- **関連テスト**: tests/unit/cli/test_config_commands.py(1,856行)。Exit 二重出力の回帰テストを追加。
- **工数感**: M

### 候補5: exec.py/team.py の表示ロジック分離
- **対象**: `commands/exec.py:229-361`、`commands/team.py:168-333`
- **問題**（観点1,2,3）: exec.py は表示関数（_output_preflight_result / _print_leaderboard_table /
  _print_text_summary）が約130行を占め361行。team.py の `_execute_team_command`（166行）は
  実行・JSON/テキスト整形・評価・DB保存を1関数で担い、関数200行制限に接近。両者とも300行超。
- **影響度**: 中（300行超2ファイル解消、表示変更時の差分局所化）
- **リスク**: 低（純粋な移動・抽出が中心で挙動変更なし）
- **推奨アプローチ**: `cli/presenters/`（または formatters.py 拡張）へ ExecutionSummary /
  MemberSubmissionsRecord の表示関数を移動。team.py は「実行」「結果整形」「保存」を
  3関数に分割。出力フォーマット分岐（json/text）のパターンも formatters 側に寄せ統一する。
- **関連テスト**: test_exec_exit_code.py / test_exec_dry_run.py / test_team_command.py。
  表示文字列に依存するテストがあるため出力不変を保ちつつ移動する。
- **工数感**: M

### 候補6: formatters.py の整理（デッドコード削除と現代化）
- **対象**: `cli/formatters.py`（375行）
- **問題**（観点2,3）: `ProgressFormatter`（341-375行）は本番コードから未使用（デッドコード）。
  `ResultFormatter` は staticmethod のみの名前空間クラス（古いパターン）。
  `_format_message_history`（75-133行）は `part.__class__.__name__` 文字列比較と hasattr で
  型分岐しており、pydantic_ai の型を使った isinstance / match 文で簡潔・型安全にできる。
  ファイル300行超。
- **影響度**: 低（member コマンドの表示品質・保守性の改善に留まる）
- **リスク**: 低（テストあり、利用箇所は member.py のみ）
- **推奨アプローチ**: ProgressFormatter と対応テストを削除。ResultFormatter をモジュール関数化
  （`get_formatter` の dict ディスパッチは維持）。メッセージ履歴整形は ModelRequest/ModelResponse と
  TextPart/ToolCallPart/ToolReturnPart の isinstance / match 分岐に書き換え。候補5の
  presenters 集約と同時実施するとファイル構成を一度で確定できる。
- **関連テスト**: tests/unit/test_formatters.py(308行)、tests/integration/test_cli_member_command.py。
- **工数感**: S

### 推奨着手順
1. 候補3（S・低リスク、共通基盤の整地）→ 2. 候補4（厚いテストの下で例外処理を是正）→
3. 候補1（最重要の重複解消、候補3の成果を利用）→ 4. 候補2 → 5. 候補5 → 6. 候補6。
