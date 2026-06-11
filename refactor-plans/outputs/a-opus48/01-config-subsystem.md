# 01. config サブシステム

`config/`（42ファイル・約7,294行）はリポジトリ最大の領域であり、300行超ファイルの上位を
独占している（schema 1,641 / manager 887 / views 819）。設定の読み込み・マッピング・表示・
検証が一つのパッケージに集中しており、肥大化と責務混在が顕著。

## R1 — `config/schema.py` を Settings クラス単位で分割

- **対象**: `src/mixseek/config/schema.py`（1,641行）
- **問題**（肥大化 / 責務混在）:
  - 1ファイルに12以上の責務の異なる定義が同居している：
    - 設定ソース実装：`MappedEnvSettingsSource`・`MappedDotEnvSettingsSource`・`MixSeekBaseSettings`
      （`settings_customise_sources` を持つ基底）
    - 各ドメインの Settings：`LeaderAgentSettings` / `MemberAgentSettings` / `EvaluatorSettings` /
      `JudgmentSettings` / `OrchestratorSettings` / `UISettings` / `PromptBuilderSettings` /
      `TeamSettings` / `WorkflowSettings` / `AgentExecutorSettings` / `FunctionExecutorSettings` /
      `WorkflowStepSettings` / `FunctionPluginMetadata`
    - モジュール関数 `_load_prompt_builder_defaults()` などの補助ロジック
  - 「環境変数マッピングの基盤」と「各ドメインのスキーマ」という抽象度の違うものが混在し、
    どこを直しても再読込が重い。AGENTS.md の300行ルールを5倍超過。
- **影響度**: 高（config を import する全モジュールに波及する中心ファイル）
- **リスク**: 中（公開シンボルの import 経路が変わるため `__init__` の再エクスポート整備が必須。
  ただし `schema` はテスト56ファイルが参照しており回帰検知は強い）
- **推奨アプローチ**:
  1. `config/sources_base.py`（仮）へ `MappedEnvSettingsSource` / `MappedDotEnvSettingsSource` /
     `MixSeekBaseSettings` を移動（設定ソース基盤として独立）。
  2. ドメイン別に `schema/leader.py`・`schema/member.py`・`schema/evaluator.py`・
     `schema/orchestrator.py`・`schema/team.py`・`schema/workflow.py`・`schema/ui.py` 等へ分割
     （= `schema.py` をパッケージ化）。各ファイル300行以内を目標。
  3. `config/schema/__init__.py` で従来の `from mixseek.config.schema import XxxSettings` を
     **そのまま再エクスポート**し、外部 import を壊さない（後方互換の薄いファサード）。
- **関連テスト**: `tests/config/`・`tests/unit/config/`・`tests/integration/config/`。
  `schema` を参照するテスト56ファイル＝厚い安全網。分割は import 経路の互換維持が要点。
- **工数**: L

## R2 — `ConfigurationManager` の loader 重複統合

- **対象**: `src/mixseek/config/manager.py`（887行・単一クラス `ConfigurationManager`）
- **問題**（DRY違反 / 肥大化）:
  - `load_team_settings` / `load_workflow_settings` / `load_unit_settings` / `load_member_settings` /
    `load_evaluation_settings` / `load_judgment_settings` / `load_orchestrator_settings` /
    `load_prompt_builder_settings` と、それぞれ対の `get_evaluator_settings` / `get_judgment_settings` /
    `get_prompt_builder_settings`（フォールバック付き）が並ぶ。
  - `get_evaluator_settings`（manager.py:559付近）に見られる「明示パス→存在チェック→既定パス
    →存在しなければデフォルト値で warning」というフォールバック手順が、各 `get_*` で繰り返されている。
  - `workspace is None` ガードや相対パス解決も各メソッドに散在。
- **影響度**: 中（設定読み込みの全入口。CLI/UI/orchestrator が依存）
- **リスク**: 中（呼び出し側が多い。テスト26ファイルで保護されるが挙動差異に注意）
- **推奨アプローチ**:
  - 共通フォールバックを `_resolve_config_path(explicit, default_relpath)` と
    `_load_with_fallback(settings_cls, explicit, default_relpath)` のような汎用ヘルパーに集約し、
    各 `get_*` はドメイン固有のパス・型を渡すだけにする（テンプレートメソッド/ジェネリック化）。
  - `workspace is None` チェックは1メソッドに寄せる。
  - 肥大化が解けない場合は、トレーシング系（`_load_settings_with_tracing`・`get_trace_info`・
    `print_debug_info`）を別 mixin / 別ファイルへ切り出す。
- **関連テスト**: `tests/config/`・`tests/integration/config/`（manager参照26ファイル）。
- **工数**: M

## R3 — `ConfigViewService` の表示責務分離

- **対象**: `src/mixseek/config/views.py`（819行・`ConfigViewService` + `SettingInfo`）
- **問題**（肥大化 / 単一責任違反）:
  - 1クラスに「設定の収集（`get_all_settings`/`get_setting`/`get_overridden_settings`）」と
    「多数の出力フォーマット（`format_table`/`format_single`/`format_single_json`/
    `format_schema_table`/`format_schema_json`/`format_list`/`format_hierarchical`/
    `format_hierarchical_json`）」、さらに「値整形ユーティリティ（`_get_type_string`/
    `_is_sensitive_field`/`_mask_value`/`_settings_to_dict`）」が同居。
  - 表示形式（table/json/hierarchical）ごとにメソッドが増殖しており、責務が「データ取得」と
    「レンダリング」に分かれていない。
- **影響度**: 中（CLI の `config` 表示系が利用。views参照テストは1ファイルと薄め）
- **リスク**: 低（出力整形が中心で副作用が少なく、依存も CLI 表示に限定的）
- **推奨アプローチ**:
  - データ収集層（`ConfigViewService`：設定→`SettingInfo` の構築）と、
    レンダラ層（`TableRenderer`/`JsonRenderer`/`HierarchicalRenderer`）に分離。
  - 機密マスキング・型文字列化（`_mask_value`/`_get_type_string`/`_is_sensitive_field`）は
    `config/view_format.py` のような純関数ユーティリティへ。
  - **テストが薄い領域**なので、分割前に主要フォーマットのスナップショット的テストを足してから着手すると安全。
- **関連テスト**: views直接参照は1ファイル（薄い）。CLI 経由の `tests/cli` がある程度カバー。
  → 安全網が薄いため、リファクタ前のテスト補強を推奨。
- **工数**: M

## R4 — `config/sources/*TomlSource` の共通基底抽出

- **対象**: `src/mixseek/config/sources/`（`evaluation_toml_source.py`・`judgment_toml_source.py`・
  `member_toml_source.py`・`orchestrator_toml_source.py`・`prompt_builder_toml_source.py`・
  `team_toml_source.py`・`workflow_toml_source.py`・`cli_source.py` ほか）
- **問題**（DRY違反）:
  - 8つの `*TomlSource` が揃って `PydanticBaseSettingsSource` を直接継承し、
    `__init__` / `_load_and_convert`（または `_load_toml`）/ `get_field_value` /
    `prepare_field_value` / `__call__` という同じ骨格を各々再実装している。
  - 既に `sources/toml_source.py` に汎用 `CustomTomlConfigSettingsSource` と
    `sources/field_mapper.py`（`normalize_member_agent_fields`）という共通化の芽があるが、
    ドメイン別ソースはそれを使い切れておらず TOML 読込・フィールド値返却の定型が重複。
- **影響度**: 中（設定読み込みの基盤。新ドメイン追加時のコピペ温床）
- **リスク**: 中（pydantic-settings のソース契約に依存。微妙な挙動差を壊さないテストが必要）
- **推奨アプローチ**:
  - `BaseTomlSource(PydanticBaseSettingsSource)` を新設し、TOML ロード・`get_field_value`・
    `prepare_field_value`・`__call__` の定型を実装。各ドメインは「ファイル探索ロジック」と
    「フィールド正規化（field_mapper 利用）」だけを差分実装する形に整理。
  - `field_mapper` を全ソースの正規化窓口に統一（現状 member 系のみ集約済み）。
- **関連テスト**: `tests/config/`・`tests/unit/config/`・`tests/integration/config/`。
  ソース単位のテストがどこまであるか着手前に確認し、不足分を補ってから抽出するのが安全。
- **工数**: M

## 補足：config 配下のその他

- `config/schema.py` 内に `os.getenv` 直呼びがある（R14 で横断対応。config 自身は
  設定モジュールの実装中枢なので一部は許容範囲だが、内部 util 経由に寄せると一貫する）。
- `preflight/` 配下は1ファイルあたり概ね小さく（最大187行）、現時点では優先度低。
