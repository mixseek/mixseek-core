# リファクタリング計画: workflow / observability / utils サブシステム

## 概要（責務と依存の現状）

担当範囲は横断的な基盤レイヤー4つ。実測行数（wc -l、`__pycache__` 除外）は以下の通り。

| モジュール | ファイル | 行数 | 責務 |
| --- | --- | --- | --- |
| workflow | `executable.py` | **393** | Executable プロトコル + agent/function アダプター + プラグイン動的ロード |
| workflow | `engine.py` | 207 | ステップ直列・executor 並列の実行エンジン |
| workflow | `models.py` / `exceptions.py` / `__init__.py` | 158 / 27 / 41 | 結果モデル / 例外 / 公開 API |
| observability | `logfire.py` | 256 | Logfire 初期化・JsonSpanProcessor・計装切替 |
| observability | `logging_setup.py` / `tee_writer.py` | 167 / 70 | 統一ロガー初期化（4モード）/ 多重出力 |
| utils | `filesystem.py` / `env.py` / `toml.py` | 230 / 97 / 52 | パス検証 / workspace 解決 / TOML 読込 |
| ルート | `exceptions.py` | 62 | workspace 関連例外3クラスのみ |

依存関係: workflow は `agents.member`・`agents.leader.dependencies`・`config.schema`・pydantic_ai に依存し、
logfire はオプション依存（try-import フォールバック）。observability は `config.logfire` / `config.logging` に依存。
`utils/env.py` は `config`（ConfigurationManager）に依存する一方、`config.sources.*` 7ファイルが `utils.env` を
関数内 import で逆参照しており、**utils ⇔ config の循環依存**が存在する（`utils/toml.py:36-37` のコメントで明示）。
ルート `exceptions.py` は `utils/env.py`・`models/workspace.py`・`cli/commands/init.py` 等から参照される。

## 評価サマリ（観点1〜5）

### 観点1: 責務と依存
- workflow は engine（制御）/ executable（アダプター）/ models（データ）の分離が明確で良好。
  ただし `executable.py` はアダプター定義に加えプラグイン動的ロード（`_load_function` /
  `_load_module_from_path`、353-393行・312-350行）と logfire span ヘルパー（54-63行）を抱え込み多責務。
- `utils/env.py` の workspace 解決は実質「設定解決」の責務であり、utils に置かれていることが
  config との循環依存の根因（21箇所の利用元のうち config 配下7箇所が関数内 import で回避している）。

### 観点2: 設計上の臭い
- **DRY違反（重大）**: `utils/env.py` の `get_workspace_path`（26-59行）と `get_workspace_for_config`
  （62-97行）は docstring 以外ほぼ同一の実装（CLI引数 → 環境変数 → ConfigurationManager → 例外）。
- **DRY違反**: `observability/logfire.py:160-163` と `logging_setup.py:131-134` で
  `workspace / "logs" / "mixseek.log"` のディレクトリ作成・ファイルオープンが重複。
- **DRY違反**: `utils/filesystem.py:51 validate_safe_path` と `config/sources/toml_source.py:14
  _validate_safe_path` でパストラバーサル検証が二重実装（検査内容も微妙に不一致）。
- **重複パターン**: `executable.py:40-49` の logfire try-import フォールバックは
  `round_controller/controller.py:34-39` と同一パターン（コード内コメントでも自認）。
- **デッドコード**: `filesystem.py` の `validate_parent_exists` / `validate_write_permission` /
  `resolve_symlinks` / `sanitize_filename` は src 配下で未使用（grep で利用箇所ゼロ。テストのみ参照）。
  実利用は `validate_safe_path` と `validate_disk_space` の2関数（`models/workspace.py:10` のみ）。

### 観点3: AGENTS.md 自己ルール違反
- **300行超**: `workflow/executable.py` 393行（規約は1ファイル300行以内）。担当範囲で唯一の超過。
  1関数200行超は担当範囲になし（最長は `setup_logfire` の約100行）。
- **os.getenv / os.environ 直接使用**:
  - `utils/env.py:20` `os.environ.get(WORKSPACE_ENV_VAR)` — 共通 config モジュール外での直接参照。
  - `observability/logfire.py:148` `os.environ["LOGFIRE_PROJECT"] = ...` — 参照ではなく**書き込み**
    （プロセス全体への副作用。テスト間の状態漏れリスク）。
  - `config/logfire.py:58-67` は config モジュール内のため規約上は許容だが、`MIXSEEK_LOG_CONSOLE` の
    解釈ロジックが `LoggingConfig` と二重管理（67行コメントで自認）。
- **ロガー**: workflow / observability は `logging.getLogger("mixseek.*")` で統一ロガー階層に乗っており
  良好。`utils/filesystem.py` はロガー未使用（例外送出のみなので許容範囲）。

### 観点4: エラー処理・型
- 例外モジュールが4箇所に分散（ルート / `evaluator` / `workflow` / `round_controller`）し、
  **共通基底クラス（例: `MixseekError`）が存在しない**。継承元も `ValueError` 系
  （`WorkspacePathNotSpecifiedError` 等）と素の `Exception`（`WorkflowStepFailedError`,
  `EvaluatorAPIError`, `JudgmentAPIError`）が混在し、呼び出し側で一括捕捉できない。
- ルート `exceptions.py` は名前に反して workspace 関連3クラスのみで「全体の例外定義」になっていない。
- `utils/env.py:57,95` の `except Exception:` は ConfigurationManager の失敗理由を握り潰して
  `WorkspacePathNotSpecifiedError` に差し替えており、原因調査を困難にする（`from e` もない）。
- `executable.py:145` に `status.value.upper()  # type: ignore[arg-type]` があり、
  ResultStatus（小文字）と ExecutableResult.status（大文字 Literal）の型変換が ignore で隠蔽されている。
- 型注釈は全体に良好（Protocol + runtime_checkable、`from __future__ import annotations` 等活用）。

### 観点5: テスト被覆
- **workflow: 厚い**。`tests/unit/workflow/` 1,432行（executable/engine/models 個別テスト）+
  `tests/integration/test_workflow_*` 5ファイル約1,070行。リファクタの安全網として十分。
- **observability: 中〜厚**。`tests/observability/test_logging_setup.py` 500行、`test_tee_writer.py`
  157行。`logfire.py` 単体テストはなく `tests/integration/test_logfire_integration.py`（447行、
  テスト20件、JsonSpanProcessor 含む）でカバー。内部分割は可能だが挙動変更には注意が必要。
- **utils: あり**。`tests/unit/test_env.py`（8件）/ `test_filesystem.py`（30件）/ `test_toml.py`（7件）。
  filesystem のデッドコードにもテストがあるため、削除時はテストも併せて削除する。
- **exceptions: 薄い**。ルート `exceptions.py` 直接のテストはなく、`cli/commands/init.py` 経由の
  間接カバーのみ。`tests/evaluator/unit/test_exceptions.py` は evaluator 例外のみ。

## リファクタリング候補

### 候補1: workflow/executable.py の分割（プラグインローダー抽出）
- **対象**: `src/mixseek/workflow/executable.py`（393行）
- **問題**: 観点3（300行超違反）・観点1（アダプター定義とプラグイン動的ロードの多責務）・
  観点2（logfire フォールバックが `round_controller/controller.py` と重複）
- **影響度**: 中 / **リスク**: 低
- **推奨アプローチ**:
  1. `_load_function` / `_load_module_from_path`（312-393行、約82行）を `workflow/plugin_loader.py`
     に抽出 → executable.py は約310行 → さらに `_logfire_span` と try-import フォールバック
     （40-63行）を `observability/spans.py` 等の共通ヘルパーに移し、round_controller 側と統合すれば
     300行以内に収まる。
  2. 公開 API（`build_executable`, `Executable`）は `workflow/__init__.py` 経由のため再 export で
     呼び出し側の変更は不要。
- **関連テスト**: `tests/unit/workflow/test_executable_builder.py`（230行）が `_load_function` 系を、
  `test_executable_function.py` / `test_executable_agent.py` がアダプターを直接カバー。安全網は厚い。
- **工数感**: S

### 候補2: workspace 解決の config への移設と重複関数の統合
- **対象**: `src/mixseek/utils/env.py`（97行）、`src/mixseek/utils/toml.py:36-37`、
  `config/sources/*` の関数内 import 7箇所
- **問題**: 観点2（`get_workspace_path` と `get_workspace_for_config` がほぼ完全な重複）・
  観点3（`os.environ.get` 直接使用）・観点1（utils ⇔ config 循環依存の根因）・
  観点4（`except Exception` による原因握り潰し）
- **影響度**: 高 / **リスク**: 中
- **推奨アプローチ**:
  1. 2関数を1つに統合（差分は docstring のみ。`get_workspace_for_config` を thin alias として
     残し deprecation 移行も可）。
  2. `config/workspace.py`（仮）へ移設し、`config.sources.*` 7ファイルの関数内 import を通常 import に
     戻して循環依存を解消。`utils/env.py` は再 export のみ残すか段階的に削除（利用元21箇所）。
  3. `except Exception` を具体的な例外型に絞り `raise ... from e` で原因を保持する。
- **関連テスト**: `tests/unit/test_env.py`（8件）が優先順位ロジックをカバー。利用元が広いため
  `make test-fast` 全体での回帰確認を推奨。
- **工数感**: M

### 候補3: observability/logfire.py の責務分割と環境変数書き込みの排除
- **対象**: `src/mixseek/observability/logfire.py`（256行）、`logging_setup.py`（167行）
- **問題**: 観点3（`logfire.py:148` の `os.environ` への**書き込み**副作用）・観点2（log ファイルパス
  組み立てが `logging_setup.py:131-134` と重複 / `setup_logfire` が writer 組立・configure・計装・
  HTTPX 計装の4責務を直列に持つ）・観点1（モジュール内グローバル `_logfire_file_handles` + atexit）
- **影響度**: 中 / **リスク**: 中
- **推奨アプローチ**:
  1. `LOGFIRE_PROJECT` の設定は `logfire.configure()` への引数渡しか、起動時の config 層での解決に
     変更し、ライブラリコードからの `os.environ` 書き込みを排除する。
  2. `workspace / "logs" / "mixseek.log"` のパス解決・mkdir を共通関数（例: `observability/paths.py`）
     に一元化し、logging_setup と logfire の二重実装を解消。
  3. `setup_logfire` を `_build_console_options` / `_setup_instrumentation` 等の私的関数に分割
     （現状約100行で規約内だが、4モード分岐の見通し改善）。
- **関連テスト**: `tests/integration/test_logfire_integration.py`（20件・447行）と
  `tests/observability/test_logging_setup.py`（500行）。4モードの挙動はテストで固定されているが、
  ハンドラ除去タイミング（`finalize_mode3_handlers`）は副作用が繊細なため挙動不変を厳守する。
- **工数感**: M

### 候補4: utils/filesystem.py のデッドコード削除とパス検証の一元化
- **対象**: `src/mixseek/utils/filesystem.py`（230行）、`src/mixseek/config/sources/toml_source.py:14`
- **問題**: 観点2（`validate_parent_exists` / `validate_write_permission` / `resolve_symlinks` /
  `sanitize_filename` の4関数が src 配下で未使用のデッドコード。パストラバーサル検証が
  `toml_source.py` と二重実装）
- **影響度**: 低 / **リスク**: 低
- **推奨アプローチ**:
  1. 未使用4関数と対応テスト（`tests/unit/test_filesystem.py` の該当ケース）を削除
     （230行 → 約130行）。
  2. `toml_source.py` の `_validate_safe_path` を `utils.filesystem.validate_safe_path` に統合するか、
     検査要件が異なるなら差分を docstring に明記して意図的な分離であることを示す。
- **関連テスト**: `tests/unit/test_filesystem.py`（30件）。削除対象のテストも同時に整理。
- **工数感**: S

### 候補5: 例外階層の一貫化（共通基底クラス導入とルート exceptions.py 再編）
- **対象**: `src/mixseek/exceptions.py`（62行）、`workflow/exceptions.py`、`evaluator/exceptions.py`、
  `round_controller/exceptions.py`
- **問題**: 観点4（共通基底クラス不在で一括捕捉が不可能。`ValueError` 系と素の `Exception` 系の混在。
  ルート exceptions.py は workspace 専用なのに全体例外モジュールの名前を占有）
- **影響度**: 中 / **リスク**: 低
- **推奨アプローチ**:
  1. ルート `exceptions.py` に `class MixseekError(Exception)` を導入し、各サブシステム例外の基底に
     差し込む（`WorkspacePathNotSpecifiedError(MixseekError, ValueError)` のように既存の
     `ValueError` 互換は多重継承で維持し、既存の `except ValueError` を壊さない）。
  2. workspace 3例外は `models/workspace.py` 近傍か `config` 配下への移動を検討し、ルートは
     基底クラス置き場として再定義する（移動時は `cli/commands/init.py:12-14` 等の import を更新）。
- **関連テスト**: ルート例外の直接テストがないため、着手前に
  `tests/unit/test_exceptions.py` を新設して現行メッセージ・継承関係を固定してから変更する。
- **工数感**: M

### 着手順の推奨
安全網が厚く効果が確実な候補1・候補4（S）から着手し、次に利用元の広い候補2（M）、
挙動が繊細な候補3（M）、最後に全サブシステムへ波及する候補5（M）の順を推奨する。
