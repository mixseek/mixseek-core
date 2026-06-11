# リファクタリング計画: agents / prompt_builder サブシステム

## 概要（責務と依存の現状）

担当範囲は `src/mixseek/agents/`（2,479行）と `src/mixseek/prompt_builder/`（564行）。

- **agents/member/**: 4種の Member Agent 実装（plain 192行 / web_search 230行 / web_fetch 222行 /
  code_execution 231行）、抽象基底 `base.py`（99行）、`factory.py`（182行）、`dynamic_loader.py`（174行）、
  構造化ロギング `logging.py`（133行）。pydantic-ai の `Agent` をラップし、`core/auth`
  （`create_authenticated_model`）と `core/model_settings`（`build_model_settings`）、
  `models/member_agent`（設定・結果モデル）に依存する。
- **agents/leader/**: `agent.py`（107行、Leader Agent 生成）、`tools.py`（132行、Member Agent の
  Tool 動的登録）、`config.py`（251行、レガシー設定 API）、`dependencies.py` / `models.py`。
  `config/manager`・`config/schema` への移行が完了済みで、`config.py` は変換層として残存。
- **prompt_builder/**: `builder.py`（219行、Jinja2 でのプロンプト整形）、`formatters.py`（192行）、
  `models.py`（132行）。`config/schema.PromptBuilderSettings` と `storage/aggregation_store`
  （リーダーボード取得）に依存。`__init__.py` が forward reference 解決のため
  `round_controller` と `storage` を import 時に読み込み、軽量モジュールにしては依存が重い。

呼び出し元は `cli/commands/team.py`、`round_controller/strategy.py`、`workflow/executable.py` 等。
公開 API は `MemberAgentFactory.create_agent` / `create_leader_agent` / `UserPromptBuilder` が中心。

## 評価サマリ（観点1〜5）

### 観点1: 責務と依存
責務分割自体は明瞭（基底クラス＋型別実装＋ファクトリ、leader はビルダ関数＋ツール登録）。
ただし `agents/leader/config.py` が「レガシー API 維持のための変換層」と「Pydantic スキーマ定義」を
兼ねており、`config/schema.py` の `LeaderAgentSettings` / `MemberAgentSettings` と二重定義になっている。

### 観点2: 設計上の臭い（最重要）
- **大規模 DRY 違反**: 4つの Member Agent の `execute()` がほぼ同一の約120行
  （実行開始ログ → 空タスク検証 → `_agent.run` → usage 抽出 → metadata 構築 → 成功/エラー結果生成）を
  コピーしている。usage 抽出ブロック（`plain.py:113-121` / `web_search.py:153-161` /
  `web_fetch.py:160-168` / `code_execution.py:146-154`）と `IncompleteToolCall` ハンドリングは
  4ファイルで文面まで一致。`web_fetch.py:204-229` のみ例外処理が整理済みで、実装間に揺れがある。
- **`Agent(...)` 生成の if/else 重複**: `system_prompt` が None かどうかで全引数を二重に書く分岐が
  `plain.py:47-65`、`code_execution.py:73-93`、`leader/agent.py:88-104` に重複
  （`web_search.py` / `web_fetch.py` は dict 構築方式で別解になっており不統一）。
- **LLM 生成パラメータの四重定義**: `temperature` / `max_tokens` / `top_p` / `seed` /
  `stop_sequences` / `timeout_seconds` / `max_retries` / `model_settings` / `google_model_settings` の
  Field 定義が `leader/config.py:26-60`（LeaderAgentConfig）、同 `:79-135`（TeamMemberAgentConfig）、
  `models/member_agent.py:282-316`（MemberAgentConfig）、`config/schema.py:338+ / 477+` の4箇所に存在。
- **潜在バグ（キー不整合）**: Member Agent は usage_info を `prompt_tokens` / `completion_tokens` キーで
  格納（例 `plain.py:118-119`）するが、`leader/tools.py:91-92` は `input_tokens` / `output_tokens` を
  参照しており常に 0 になる。MemberSubmission のトークン集計が機能していない疑いが濃い。
- `leader/tools.py` は関数3段ネスト（`register_member_tools` → `make_tool_func` → `tool_func`）で
  テスト容易性が低い。

### 観点3: AGENTS.md 自己ルール違反
- **300行超ファイルなし**（最大 251行の `leader/config.py`）。関数200行超もなし。
- **`os.environ` 直接参照**: `prompt_builder/formatters.py:39` の `os.environ.get("TZ")`。
  規約では共通設定モジュール経由が必須（`utils/env.py` には `get_workspace_path` 等の前例あり）。
- **構造化ログの不徹底**: `member/logging.py` は extra dict 方式で規約準拠だが、
  `factory.py:19` / `dynamic_loader.py:25` は `logging.getLogger(__name__)`＋f-string メッセージで
  構造化されていない（例 `factory.py:84` の `logger.info(f"Successfully loaded ...")`）。

### 観点4: エラー処理・型
- 型注釈は概ね網羅的（mypy 前提）。ただし `prompt_builder/models.py:42` の
  `store: Any = None`（テストでモック許容のため）は型安全性を損ねている。
- 認証失敗を `ValueError(f"Authentication failed: {e}")` に詰め替えるパターンが4実装で重複し、
  例外型の情報が失われる。`mixseek.exceptions` の専用例外に統一する余地あり。
- `formatters.py` の docstring と実装の乖離: `format_ranking_table` は「None なら空文字列を返す」と
  記載（:114, :127-128）だが実装（:133-134）は None でも「まだランキング情報がありません。」を返す。
  `generate_position_message`（:153）も同様の乖離あり。

### 観点5: テスト被覆
安全網は厚い。`tests/unit/test_plain_agent.py`（315行）、`test_web_search_agent.py`（296行）、
`test_web_fetch_agent.py`（397行）、`test_code_execution_agent.py`（440行）、
`tests/agents/leader/test_tools.py`（293行）、`tests/unit/prompt_builder/` 5ファイル（約1,535行）、
統合テスト（`test_member_agent_integration.py` 429行、`test_prompt_builder_integration.py` 397行、
`test_custom_agent_loading.py` 321行）が存在。執行パス共通化のリファクタは既存テストで回帰検知可能。
一方、`factory.py` 単体のユニットテストは薄く（custom 型経由が中心）、usage 集計の正しさを検証する
テストが無い（観点2の潜在バグが検知されていない理由）。

## リファクタリング候補

### 候補1: Member Agent execute() のテンプレートメソッド化

- **対象**: `src/mixseek/agents/member/{base,plain,web_search,web_fetch,code_execution}.py`
- **問題**: 観点2（DRY違反）。約120行 × 4ファイルの実行フロー重複。`IncompleteToolCall` 処理や
  usage 抽出の文面一致コピーが保守コストとバグ温床（修正漏れ）になっている。
  実際に `web_fetch.py` のみ例外処理が改善され他3つに反映されていない。
- **影響度**: 高（member パッケージの行数を約4割削減、今後のエージェント追加コストを大幅減）
- **リスク**: 中（4エージェント全部の実行パスに触れるが、外部 API・挙動は不変）
- **推奨アプローチ**: `BaseMemberAgent.execute()` を共通実装（ログ → 検証 → 実行 → 結果生成 →
  例外ハンドリング）とし、サブクラスは `_build_agent(config) -> Agent`・`_build_deps(context)`・
  `_extra_metadata()` のフックのみ実装するテンプレートメソッドに再構成。
  `Agent(...)` 生成の system_prompt 分岐も dict 構築方式の共通ヘルパに統一し、
  `leader/agent.py:88-104` の同分岐も同ヘルパを利用。認証失敗の `ValueError` 詰め替えも基底へ集約。
  併せて `factory.py` / `dynamic_loader.py` の f-string ログを extra dict 方式に統一。
- **関連テスト**: `tests/unit/test_{plain,web_search,web_fetch,code_execution}_agent.py`（計1,448行）、
  `tests/integration/test_member_agent_integration.py`・`test_member_agent_all_messages.py`。安全網は十分。
- **工数感**: M

### 候補2: usage_info キー不整合の修正と leader/tools.py の平坦化

- **対象**: `src/mixseek/agents/leader/tools.py`、`src/mixseek/agents/member/*.py`（usage 抽出部）
- **問題**: 観点2・4。Member Agent 側は `prompt_tokens`/`completion_tokens`（`plain.py:118-119`）、
  leader 側は `input_tokens`/`output_tokens`（`tools.py:91-92`）と参照キーが不一致で、
  `MemberSubmission.usage` のトークン数が常に 0 になる潜在バグ。また pydantic-ai の `RunUsage` は
  `input_tokens`/`output_tokens` が正式属性であり、`getattr(usage, "prompt_tokens", None)` は
  None を返す可能性が高い。加えて `tools.py` は関数3段ネストで単体テストしづらい。
- **影響度**: 高（リーダーボード・コスト集計の正確性に直結する機能バグの修正）
- **リスク**: 低（修正範囲は限定的。dict キーではなく型付きモデルで受け渡せば再発も防げる）
- **推奨アプローチ**: usage_info を `dict[str, Any]` でなく `RunUsage` または専用 pydantic モデルで
  受け渡すよう統一（候補1の共通 `execute()` に組み込むと効率的）。`make_tool_func` 内の
  `tool_func` 本体をモジュールレベル関数 `_run_member_and_record(ctx, mc, ma, task)` に抽出。
  トークン数が正しく伝播することを検証するユニットテストを先に追加（TDD）。
- **関連テスト**: `tests/agents/leader/test_tools.py`（293行）。usage 検証テストは新規追加が必要。
- **工数感**: S

### 候補3: LLM 生成パラメータ定義の共通基底モデル化

- **対象**: `src/mixseek/agents/leader/config.py`、`src/mixseek/models/member_agent.py`、
  `src/mixseek/config/schema.py`（LeaderAgentSettings / MemberAgentSettings）
- **問題**: 観点2（DRY違反）。temperature 等9項目の Field 定義（制約・説明文込み）が4クラスに重複。
  制約変更時（例: temperature の上限変更）に4箇所の同期が必要で、既に説明文の揺れが発生している。
- **影響度**: 中（設定スキーマの一貫性・保守性向上。挙動は不変）
- **リスク**: 中（config サブシステムの担当範囲と重なるため、横断調整が必要。
  pydantic の MRO・BaseSettings 継承との整合に注意）
- **推奨アプローチ**: `LLMGenerationParamsMixin`（pydantic BaseModel）を `models/` か `config/` に
  新設し、9項目の Field と validator を一元化。各設定クラスは Mixin 継承＋固有フィールドのみ定義。
  config サブシステム側のリファクタ計画と着手順を調整すること。
- **関連テスト**: `tests/unit/test_member_agent_config.py`（380行）、
  `tests/unit/agents/leader/test_config_timeout.py`、`tests/unit/models/test_leader_agent.py`。
- **工数感**: M

### 候補4: prompt_builder の環境変数直接参照の排除と docstring 乖離修正

- **対象**: `src/mixseek/prompt_builder/formatters.py`、`src/mixseek/prompt_builder/models.py`
- **問題**: 観点3（自己ルール違反）・観点4。`formatters.py:39` で `os.environ.get("TZ")` を直接参照
  （規約は共通設定モジュール経由）。`format_ranking_table`（:114）と `generate_position_message`
  （:153）の docstring が実装と乖離。`models.py:42` の `store: Any` が型安全性を損ねている。
- **影響度**: 中（規約準拠とテスト容易性の改善。TZ 取得のモックが容易になる）
- **リスク**: 低（純粋関数群でテストが厚く、挙動変更なし）
- **推奨アプローチ**: `utils/env.py` に `get_timezone() -> tzinfo` を追加（`get_workspace_path` と
  同パターン）し、formatters はそれを利用。docstring を実装に合わせて修正。
  `store: Any` は `if TYPE_CHECKING` での `AggregationStore | None` 注釈＋Protocol 化を検討。
- **関連テスト**: `tests/unit/prompt_builder/test_prompt_formatters.py`（202行）、
  `test_builder*.py`（計1,098行）、`tests/integration/test_prompt_builder_integration.py`（397行）。
- **工数感**: S

### 候補5: leader/config.py レガシー変換層の段階的撤去

- **対象**: `src/mixseek/agents/leader/config.py`
- **問題**: 観点1・2。`load_team_config()` は deprecated 宣言済み（:170-176）で内部は
  `ConfigurationManager` に委譲する薄いラッパ。`LeaderAgentConfig` / `TeamMemberAgentConfig` /
  `TeamConfig` は `config/schema.py` の Settings 群と二重定義であり、`team_settings_to_team_config()`
  による変換が `cli/commands/team.py` と `round_controller/strategy.py` で毎回走っている。
- **影響度**: 中（設定の流れが一本化され、agents/config 間の概念重複が解消）
- **リスク**: 中（`create_leader_agent` / `register_member_tools` のシグネチャ変更を伴い、
  cli・round_controller・workflow の呼び出し元修正が必要。外部利用者がいる場合は非互換）
- **推奨アプローチ**: まず `create_leader_agent` 系を `TeamSettings`（新スキーマ）を直接受ける形に
  変更し、`TeamConfig` 系は deprecation 警告付きで1リリース維持 → 次リリースで削除の2段階。
  候補3（共通基底モデル化）の後に実施すると変換ロジック自体が縮小し作業が楽になる。
- **関連テスト**: `tests/integration/test_leader_agent_e2e.py`（274行）、
  `tests/agents/leader/test_models.py`・`test_tools.py`、`tests/unit/agents/leader/test_config_timeout.py`。
- **工数感**: M

### 推奨着手順

1. 候補2（S・バグ修正を伴うため最優先）→ 2. 候補1（最大の重複解消、候補2の型統一を取り込む）
→ 3. 候補4（独立・小粒でいつでも可）→ 4. 候補3（config 側と調整の上）→ 5. 候補5（候補3の後）
