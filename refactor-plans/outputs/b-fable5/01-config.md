# config 層のリファクタリング計画（C1〜C3）

config サブシステムは本リポジトリ最大のモジュール群であり、300行超ファイル上位5件のうち
3件（`schema.py` 1,641行 / `manager.py` 887行 / `views.py` 819行）を占める。
一方で `sources/`（TOML ソース群）と `preflight/`（バリデータ群）は既に小さく分割されており、
設計方針自体は健全。問題は「1ファイルに詰め込まれた定義」と「同型コードの繰り返し」に集中している。

## 責務と依存（現状把握）

- `schema.py` … 全サブシステムの pydantic-settings スキーマ定義（Leader/Member/Evaluator/
  Judgment/Orchestrator/UI/PromptBuilder/Team/Workflow + 独自 SettingsSource 2種）
- `manager.py` … `ConfigurationManager`。TOML ソースとスキーマを束ね、トレース付きで設定をロード
- `views.py` … `mixseek config show/list` 用の表示サービス（text/JSON/階層表示）
- `sources/` … 設定種別ごとの TOML ソース（field_mapper による互換キー吸収を含む）
- `preflight/` … 実行前バリデーション（auth/evaluator/team 等。良い分割例）
- 依存方向は cli/ui/orchestrator → manager → schema/sources で一方向。循環は遅延 import で回避
  しており（`manager.py:416` など）、分割時もこの方針を踏襲すればよい

テスト被覆: config を参照するテストは **78ファイル**と全サブシステム中最厚。
`tests/unit/config`・`tests/integration/config`・`tests/e2e/test_config_workflow.py` があり、
分割系リファクタの安全網としては十分。

---

## C1: `schema.py`（1,641行）のモジュール分割

- **対象**: `src/mixseek/config/schema.py`
- **影響度: 高 / リスク: 低 / 工数: M**

### 問題（分析観点: 自己ルール違反・肥大化）

300行制限の5.5倍。13クラス＋共通バリデータが1ファイルに同居し、どの設定がどのサブシステムの
ものか探しにくい。git の変更履歴も全サブシステムの設定変更がこのファイルに集中し、
コンフリクトの温床になっている。

クラス境界は明確で相互依存も薄い（`TeamSettings` → `MemberAgentSettings`、
`WorkflowSettings` → `AgentExecutorSettings`/`FunctionExecutorSettings` 程度）ため、
分割は機械的に行える。

### 推奨アプローチ

`config/schema/` パッケージ化し、おおよそ次の単位に分割する（各100〜250行）:

| 新ファイル | 移動するクラス |
| --- | --- |
| `schema/sources.py` | `MappedEnvSettingsSource`, `MappedDotEnvSettingsSource` |
| `schema/base.py` | `MixSeekBaseSettings`（`settings_customise_sources` 含む） |
| `schema/agents.py` | `LeaderAgentSettings`, `MemberAgentSettings` |
| `schema/evaluation.py` | `EvaluatorSettings`, `JudgmentSettings` |
| `schema/orchestrator.py` | `OrchestratorSettings`, `UISettings` |
| `schema/prompt_builder.py` | `PromptBuilderSettings`, `_load_prompt_builder_defaults` |
| `schema/team.py` | `TeamSettings` |
| `schema/workflow.py` | `WorkflowSettings`, `WorkflowStepSettings`, `AgentExecutorSettings`, 他 executor 系2クラス |

`schema/__init__.py` で全クラスを再エクスポートすれば、既存の
`from mixseek.config.schema import XxxSettings`（src/tests 双方に多数）は無変更で動く。

注意点:

- `MixSeekBaseSettings.settings_customise_sources`（112行）はソース優先順位の中核。
  分割そのものとは独立に、ソース構築ロジックのヘルパー抽出も検討余地がある（別 PR 推奨）
- M2（LLM パラメータ共通基底モデル、[02](02-models-unification.md)）と同時に行うと
  `agents.py`/`evaluation.py` の行数がさらに減る。順序は M2 → C1 でも C1 → M2 でもよいが、
  コンフリクト回避のため連続して実施するのが望ましい

### 関連テスト（安全網）

`tests/unit/config/`・`tests/integration/config/` が直接被覆。再エクスポート維持なら
既存テストがそのまま回帰検知になる。追加テストは不要。

---

## C2: `ConfigurationManager` の `get_*_settings` フォールバック共通化

- **対象**: `src/mixseek/config/manager.py`（887行）
- **影響度: 中 / リスク: 低 / 工数: S**

### 問題（分析観点: DRY 違反・肥大化）

`get_evaluator_settings` / `get_judgment_settings` / `get_prompt_builder_settings`（各65行）は
「明示パスがあれば workspace 基準で解決して必須ロード → なければ
`{workspace}/configs/<name>.toml` を試行 → それもなければデフォルト値＋警告ログ」という
完全に同型のロジック（`manager.py:559-623` ほか）。`load_*_settings` 系8メソッドも
スキーマクラスと TOML ソースクラスを `_load_settings_with_tracing` に渡すだけの薄い定型で、
docstring が本体の3〜4倍を占める。

### 推奨アプローチ

1. 共通フォールバックを1メソッドに抽出する:

   ```python
   def _get_settings_with_fallback(
       self, settings_cls, source_cls, explicit: Path | str | None, default_rel: str, **kw
   ): ...
   ```

   公開 API（`get_evaluator_settings` 等）は1〜3行の委譲として残す（呼び出し側変更なし）。
2. `load_*_settings` 系は（スキーマ, ソース）対応表をモジュール定数にし、定型部を圧縮する。
   docstring は Examples を削って要点のみに短縮（Sphinx 方針は `internal/sphinx.md` 準拠で確認）。
3. 結果として 887行 → 500行前後を見込む。300行未満まで縮めるには C1 同様のパッケージ分割
   （loader 部とトレース部の分離）まで踏み込む。第一段階は重複排除を優先し、分割は任意。

### 関連テスト（安全網）

`tests/unit/config/` に manager 系テストあり、フォールバック挙動（デフォルトパス未存在時の
警告＋デフォルト値返却）も e2e の `test_config_workflow.py` が踏む。既存テストで十分。

---

## C3: `ConfigViewService` のデータ抽出と表示の分離

- **対象**: `src/mixseek/config/views.py`（819行）
- **影響度: 中 / リスク: 低 / 工数: M**

### 問題（分析観点: DRY 違反・密結合・肥大化）

`format_hierarchical`（79行）と `format_hierarchical_json`（93行）は
orchestrator → teams → members の同じ木構造をそれぞれ独立に歩いており（`views.py:478-557` と
`views.py:559-651`）、構造変更時に2箇所の同期修正が必要。`format_table`/`format_single`/
`format_schema_*`/`format_list` も「同じ SettingInfo 列を別形式で出す」並列実装になっている。

### 推奨アプローチ

1. **中間表現を1つに定める**: 木構造を `dict`（既存 `_settings_to_dict` ベース）へ正規化する
   抽出層を作り、JSON 出力は `json.dumps(中間表現)`、text 出力は中間表現の整形のみとする。
   これで階層ウォークが1本化され、`format_hierarchical_json` はほぼ消える。
2. ファイルを `views/`（または `views.py` + `view_formatters.py`）に分け、
   「抽出（settings → SettingInfo/dict）」と「整形（table/text/json）」を分離する。
   `_is_sensitive_field`/`_mask_value` は抽出側に置き、全出力形式で一貫してマスクされることを
   テストで保証する（現状は形式ごとの実装に依存）。
3. 819行 → 2ファイル各300行未満を見込む。

### 関連テスト（安全網）

`tests/ui/test_config_service.py`・CLI contract テスト（`tests/contract/test_help_contract.py` 等）
と `tests/integration/config/` が出力形式を固定している。出力文字列のスナップショット的
アサーションがある場合、リファクタは「出力を変えない」制約で進めること。
マスク一貫性のユニットテストを1本追加してから着手すると安全。

---

## 補足: config 層で「やらなくてよい」こと

- `sources/` の各 TOML ソース（100〜210行）と `preflight/validators/`（30〜190行）は
  既に適切な粒度。`field_mapper.py` がレガシーキー吸収を一元化しており、ここは触らない。
- `recursive_loader.py`（259行）・`template.py`（224行）・`member_agent_loader.py`（214行）は
  規約内。`member_agent_loader.py` の旧モデル変換だけは M1（[02](02-models-unification.md)）の
  対象として扱う。
