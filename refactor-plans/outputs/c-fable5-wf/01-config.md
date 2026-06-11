# リファクタリング計画: config サブシステム

## 概要（責務と依存の現状）

`src/mixseek/config/` は設定管理サブシステムで、実測（wc -l）で Python 実装は約 5,900 行。主な構成は以下。

| ファイル | 行数 | 責務 |
|---|---|---|
| `schema.py` | 1,641 | Pydantic Settings スキーマ群 + 環境変数マッピングソース2クラス |
| `manager.py` | 887 | `ConfigurationManager`（読み込みオーケストレーション、トレース付与） |
| `views.py` | 819 | `ConfigViewService`（CLI 向け表示・整形・マスキング） |
| `recursive_loader.py` | 259 | orchestrator→team→member の再帰読み込み（循環参照検出） |
| `template.py` | 224 | TOML テンプレート生成 |
| `sources/` | 約1,200 | TOML/CLI/トレーシング等の設定ソース 9 ファイル |
| `env_mappers.py` | 137 | MIXSEEK_WORKSPACE 等→内部フィールド名のマッピング戦略 |
| `logging.py` / `logfire.py` | 112 / 77 | ロギング/Logfire 設定モデル（`from_env()` で手動 os.getenv） |
| `preflight/` | 約700 | 起動前バリデーション群（各ファイル 300 行未満で健全） |

依存関係: `mixseek.models.member_agent`、`mixseek.utils.{env,toml}` に依存。公開 API は
`__init__.py` 経由の `ConfigurationManager` と各 Settings クラスで、cli / ui / orchestrator /
evaluator / observability など全サブシステムから参照される基盤層。

問題のある依存構造として **3 つの循環参照** が存在し、いずれも遅延 import で回避されている:

- `schema.py:221` → `manager._config_file_context`（manager 側は schema を遅延 import）
- `manager.py:164` → `views.ConfigViewService._mask_value`（views は manager を通常 import）
- `utils/env.py:7` → `mixseek.config`（config の sources/* は `utils.env` を遅延 import。
  例: `sources/evaluation_toml_source.py:66`）

## 評価サマリ（観点1〜5）

### 観点1: 責務と依存

設定の「スキーマ定義」「読み込み」「表示」「テンプレート生成」「事前検証」が一応ファイル単位で分かれて
いるが、`schema.py` はスキーマ定義に加えて環境変数ソース実装（`MappedEnvSettingsSource` /
`MappedDotEnvSettingsSource`、35〜160 行）と contextvars によるトレース用グローバル状態
（`_trace_storage_context`、26 行）を抱えており単一責務でない。manager↔schema↔views の循環は
レイヤリング不全の兆候。

### 観点2: 設計上の臭い

- **LLM パラメータ 9 フィールドの大量重複（DRY 違反）**: `temperature` / `max_tokens` /
  `max_retries` / `timeout_seconds` / `stop_sequences` / `top_p` / `seed` / `model_settings` /
  `google_model_settings` が `LeaderAgentSettings`(373-426) / `MemberAgentSettings`(528-581) /
  `EvaluatorSettings`(675-728) / `JudgmentSettings`(790-843) / `AgentExecutorSettings`(1339-1385)
  の 5 クラスにほぼ同一定義で繰り返され、`validate_model` バリデータも 4 回重複。約 400 行相当。
- **TOML ソースのボイラープレート重複**: `sources/evaluation_toml_source.py:121-160` と
  `sources/judgment_toml_source.py:100-139` の `get_field_value` / `prepare_field_value` /
  `__call__` は完全同一。workspace 解決＋ファイル存在チェック（両者の 57〜80 行付近）も
  team/member/orchestrator/prompt_builder 各ソースに同型で存在（6 ファイル × 約 70 行）。
- **manager.py のフォールバック 3 連コピー**: `get_evaluator_settings`(559-623) /
  `get_judgment_settings`(671-735) / `get_prompt_builder_settings`(823-887) は設定クラス名と
  デフォルトパスだけが異なる同一ロジック（各約 65 行）。`load_*_settings` 6 メソッドも
  `_load_settings_with_tracing` への薄い委譲で docstring 込み各 40〜60 行を占める。
- **recursive_loader.py の 3 連コピー**: `_load_orchestrator_internal` 内で evaluator / judgment /
  prompt_builder のパス解決＋デフォルト探索が同型に 3 回出現（178-227 行）。
- **views.py / template.py 間の重複**: `_get_type_string` がほぼ同一実装で 2 箇所に存在
  （`views.py:742-771`、`template.py:202-224`）。views 内でも `format_table`(215-268) と
  `format_schema_table`(325-377) のテーブル描画ロジックが重複。
- **遅延 import の多用**: `schema.py:68,131,221`、`manager.py:113,242,258,292,313` など、
  循環参照回避のためのインライン import が十数箇所あり、依存方向の歪みを示す。
- `template.py:164-169` に if/else 両分岐が同一文の dead code、`schema.py:1053` に Python 3.13
  では不要な `importlib.resources` の AttributeError フォールバック等、古いパターンが残存。

### 観点3: AGENTS.md 自己ルール違反

- **300 行超**: `schema.py` 1,641 行（規約の 5.5 倍）、`manager.py` 887 行、`views.py` 819 行。
  1 関数 200 行超はなし（最長は `manager._load_settings_with_tracing` の約 135 行）。
- **os.getenv / os.environ 直接使用**: `logging.py:87,93,96,100`、`logfire.py:58-67`、
  `env_mappers.py:68,108`、`schema.py:228`、`sources/toml_source.py:94`。
  config パッケージ自体が規約上の「共通設定モジュール（正規アクセス点）」であるため、
  pydantic-settings の Env ソース経由の読み取りは適法と判断する。ただし `logging.py` /
  `logfire.py` の `from_env()` は同パッケージ内の他スキーマと異なり**手動 os.getenv パース**で
  実装されており（バリデーション・優先順位・トレースの仕組みに乗っていない）、正規アクセス点と
  しての一貫性を欠く。`env_mappers.py` の `os.environ.get` フォールバックは Env ソースの責務との
  二重読み取りで、`schema.py:228` / `toml_source.py:94` の `MIXSEEK_CONFIG_FILE` 直接読みは
  「後方互換」と注記されたまま残存している。
- **ロガー**: `manager.py:17` は stdlib `logging.getLogger` を使用（observability の
  `setup_logging` 経由で構造化 JSON 化されるため許容範囲）。ただし
  `manager.print_debug_info`(153-183) は `print()` 直書き。

### 観点4: エラー処理・型

- 例外設計は概ね `FileNotFoundError` / `ValueError` ＋具体的メッセージで一貫しており良好。
- 問題点: `views.py:123` の `except Exception:` 無言握り潰し（読み込み失敗時に default 表示へ
  フォールバック）、`utils/env.py:57,95` の `except Exception` → `WorkspacePathNotSpecifiedError`
  変換（真因がマスクされる）、`manager.py:135` の `# type: ignore`。
- `sources/toml_source.py:37-62` の `_sanitize_error_message` は正規表現 `/[a-z0-9/_.-]+` が
  小文字パスしかマッチせず、大文字を含むパスを素通しする一方で無関係な文字列を破壊し得る。
- 型注釈は概ね網羅されているが、views / template は `field_info: Any`、`toml_source_cls: type`
  （`manager.py:219`）など Any / 素の type が散見される。

### 観点5: テスト被覆

テスト資産は厚く、リファクタの安全網として十分:

- `tests/unit/config/` 28 ファイル（`test_schema.py` 397 行、`test_manager.py` 296 行＋
  `test_manager_load_methods.py` 414 行、`test_sources.py` 229 行、`test_env_mapping.py` 372 行、
  `test_recursive_loader.py` 488 行、`test_template_generation.py` 252 行 等）
- `tests/integration/config/`（priority / tracing / toml_loading / migration 等 7 ファイル）、
  `tests/e2e/test_config_workflow.py`、`tests/config/test_logging.py`(210行) /
  `test_logfire_config.py`(104行)
- 弱点: `views.py` の直接ユニットテストはマスキング系（`test_sensitive_field_masking.py`）のみで、
  整形ロジックの大半は `tests/unit/cli/test_config_commands.py`（1,856 行）経由の間接被覆。
  views 分割時は CLI テストをリグレッション網として活用できるが、出力文字列に依存するため
  挙動非互換に敏感（逆に言えば安全網としては有効）。

## リファクタリング候補

### 候補1: schema.py の分割と LLM 共通フィールドの Mixin 化

- **対象**: `src/mixseek/config/schema.py`（1,641 行）
- **問題**: 観点2（LLM 9 フィールド × 5 クラスの重複、env ソース実装の同居）、観点3（300 行規約の
  5.5 倍）。最大の自己ルール違反ファイル。
- **影響度**: 高（全サブシステムが import する基盤。可読性・変更容易性への効果が最大）
- **リスク**: 中（pydantic-settings の `model_config` 継承、`extra="forbid"`、トレース contextvars
  との相互作用に注意。再エクスポートで import 互換を維持すれば外部影響は限定的）
- **推奨アプローチ**:
  1. `LLMParameterMixin`（temperature/max_tokens/.../google_model_settings + `validate_model`）を
     抽出し 5 クラスに適用（約 400 行削減）
  2. `schema/` パッケージ化: `base.py`（MixSeekBaseSettings）、`agents.py`（Leader/Member）、
     `evaluation.py`（Evaluator/Judgment）、`orchestration.py`（Orchestrator/UI/PromptBuilder）、
     `team.py`、`workflow.py`（Workflow 系 360 行）に分割
  3. `MappedEnvSettingsSource` / `MappedDotEnvSettingsSource`（35-160 行）は `sources/` へ移動
  4. 旧 `schema.py` の import パスは `schema/__init__.py` の再エクスポートで完全互換に保つ
- **関連テスト**: `tests/unit/config/test_schema.py`、`test_workflow_settings.py`、
  `test_member_settings.py`、`tests/integration/config/test_priority.py` / `test_tracing.py`（厚い）
- **工数感**: L

### 候補2: manager.py のフォールバック/ロードメソッド統合と分割

- **対象**: `src/mixseek/config/manager.py`（887 行）
- **問題**: 観点2（`get_evaluator_settings` / `get_judgment_settings` / `get_prompt_builder_settings`
  の 65 行 × 3 コピー、`load_*_settings` 6 連の同型委譲）、観点3（300 行超）
- **影響度**: 中（行数を約 1/3 に削減可能。読み込み経路の理解コストが大幅低下）
- **リスク**: 低（公開メソッドのシグネチャを維持したまま内部を共通化できる）
- **推奨アプローチ**: 設定種別ごとの宣言的レジストリ（settings クラス / TOML ソースクラス /
  デフォルトファイル名のタプル）を定義し、汎用 `_get_settings_with_fallback()` と
  `_load_settings_with_tracing()` に集約。`print_debug_info`（print 直書き）は views 側へ移し、
  manager↔views の循環（`manager.py:164`）を解消する。
- **関連テスト**: `tests/unit/config/test_manager.py`、`test_manager_load_methods.py`（414 行）、
  `tests/integration/config/test_toml_loading.py`
- **工数感**: M

### 候補3: sources/ の TOML ソース基底クラス導入

- **対象**: `src/mixseek/config/sources/`（evaluation/judgment/member/team/orchestrator/
  prompt_builder の各 *_toml_source.py、計約 900 行）
- **問題**: 観点2（workspace 解決・存在チェック・`get_field_value` / `prepare_field_value` /
  `__call__` のボイラープレートが 6 ファイルに重複。例: `evaluation_toml_source.py:121-160` ≒
  `judgment_toml_source.py:100-139`）
- **影響度**: 中（重複約 400 行削減、新しい設定種別の追加コストが激減）
- **リスク**: 低（各ソースの差分は `_convert(data)` 部分のみで、振る舞いは既存テストで固定可能）
- **推奨アプローチ**: `BaseTomlFileSource(PydanticBaseSettingsSource)` を新設し、
  workspace 解決（`utils.env.get_workspace_for_config` 呼び出し含む）と共通 3 メソッドを実装。
  各ソースはセクション抽出・キー変換の `_convert()` のみオーバーライドする Template Method 構成。
- **関連テスト**: `tests/unit/config/test_sources.py`、`test_evaluation_settings.py`、
  `test_workflow_toml_source.py`、`tests/integration/config/test_toml_loading.py`
- **工数感**: M

### 候補4: views.py の収集と整形の分離

- **対象**: `src/mixseek/config/views.py`（819 行）、`template.py`（`_get_type_string` 重複）
- **問題**: 観点2（テーブル描画ロジック重複: 215-268 行 vs 325-377 行、`_get_type_string` の
  views/template 二重実装）、観点3（300 行超）、観点4（`views.py:123` の例外握り潰し）
- **影響度**: 中（CLI 表示専用のため他サブシステムへの波及は小さいが、規約違反解消と保守性向上）
- **リスク**: 低（CLI 出力文字列のリグレッションは `test_config_commands.py` 1,856 行が検知する）
- **推奨アプローチ**: `views/` パッケージ化し `collector.py`（SettingInfo 収集）、
  `formatters.py`（table/json/hierarchical、共通テーブル描画関数に統合）、`masking.py`
  （`_is_sensitive_field` / `_mask_value`）に分離。`_get_type_string` は共通ユーティリティ化して
  template.py と共有。`except Exception` には debug ログを追加して無言フォールバックを解消。
- **関連テスト**: `tests/unit/cli/test_config_commands.py`（間接・厚い）、
  `tests/unit/config/test_sensitive_field_masking.py`。分割時に formatter 単体テストの追加を推奨。
- **工数感**: M

### 候補5: logging.py / logfire.py の pydantic-settings 化（env アクセス統一）

- **対象**: `src/mixseek/config/logging.py`、`src/mixseek/config/logfire.py`、
  `src/mixseek/config/env_mappers.py`
- **問題**: 観点3（`logging.py:87-104` / `logfire.py:58-67` の手動 os.getenv パース。config
  パッケージは正規アクセス点だが、同居する他スキーマと方式が不統一でバリデーション・優先順位・
  トレース機構に乗っていない）、観点2（`env_mappers.py:68,108` の os.environ 直接読みは
  Env ソースとの二重読み取り）
- **影響度**: 中（環境変数アクセス方式がパッケージ内で統一され、規約の説得力が回復する）
- **リスク**: 中（`LOGFIRE_*` はプレフィックス無し、`MIXSEEK_LOG_CONSOLE` は 2 モデルで共有、
  env_mappers のフォールバックは Issue #251 の挙動に関わるため、既存テストでの挙動固定が必須）
- **推奨アプローチ**: `LoggingConfig` / `LogfireConfig` を `BaseSettings` ベース
  （`env_prefix` + `AliasChoices`）に置換し `from_env()` は互換ラッパーとして残す。
  `env_mappers.py` の `os.environ.get` フォールバックは、`MappedEnvSettingsSource` が常に
  生 env 値を渡すことをテストで確認した上で削除を検討。`schema.py:228` / `toml_source.py:94` の
  `MIXSEEK_CONFIG_FILE` 後方互換読み取りは deprecation コメントを付して集約する。
- **関連テスト**: `tests/config/test_logging.py`（210 行）、`test_logfire_config.py`（104 行）、
  `tests/unit/config/test_env_mapping.py`（372 行）— 安全網は十分
- **工数感**: S

### 候補6: 循環参照の解消（contextvars の専用モジュール化）

- **対象**: `src/mixseek/config/manager.py`（`_config_file_context`）、`schema.py`
  （`_trace_storage_context`、221 行の manager 遅延 import）、`utils/env.py`
- **問題**: 観点1（schema↔manager↔views、config↔utils.env の循環）、観点2（回避のための
  遅延 import 十数箇所が可読性を損なう）
- **影響度**: 中（候補1・2 の分割を安全に進める前提整備。import 順序バグの温床を除去）
- **リスク**: 低（モジュール移動のみで実行時挙動は不変。re-export で互換維持可能）
- **推奨アプローチ**: `config/context.py` を新設し `_config_file_context` /
  `_trace_storage_context` を移動（schema / manager 双方がそこを import）。`utils/env.py` の
  workspace 解決関数は config 側（例: `config/workspace.py`）へ移して utils→config の一方向依存に
  正す。あわせて `utils/env.py:57,95` の `except Exception` を具体的な例外型に絞り、真因を
  チェイン（`raise ... from e`）する。
- **関連テスト**: `tests/unit/config/test_trace_storage_thread_safety.py`、`test_manager.py`、
  `tests/integration/config/test_tracing.py`
- **工数感**: S

### 推奨着手順

候補6（前提整備・S）→ 候補3（低リスク・効果大）→ 候補2 → 候補1（最大効果・要 6/3/2 の完了）
→ 候補4 → 候補5。候補1 は他候補完了後に着手するとファイル移動の手戻りが最小になる。
