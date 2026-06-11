# リファクタリング計画: orchestrator / round_controller サブシステム

## 概要（責務と依存の現状）

対象は `src/mixseek/orchestrator/`（計710行）と `src/mixseek/round_controller/`（計819行）。
実測行数（wc -l）:

| ファイル | 行数 |
|---|---|
| orchestrator/orchestrator.py | 530 |
| orchestrator/models.py | 162 |
| round_controller/controller.py | 567 |
| round_controller/judgment_client.py | 123 |
| round_controller/strategy.py | 99 |
| round_controller/models.py | 56 |
| round_controller/exceptions.py | 49 |

- **Orchestrator**（orchestrator.py:90）: 複数チームの並列実行管理。`OrchestratorSettings` を受け取り、
  チームごとに `RoundController` を生成して `asyncio.gather` で並列実行。タイムアウト・リトライ・
  部分成功リカバリ・`ExecutionSummary` 生成・DuckDB保存（`AggregationStore`）を担う。
- **RoundController**（controller.py:52）: 単一チームのマルチラウンドライフサイクル管理。
  プロンプト整形（`UserPromptBuilder`）→ Strategy実行（`LeaderStrategy`/`WorkflowStrategy`）→
  評価（`Evaluator`）→ 継続判定（`JudgmentClient`）→ DuckDB永続化 → 進捗JSON書き出し、を全て1クラスで実施。
- 依存方向: Orchestrator → RoundController（循環回避のため orchestrator.py:194 で遅延import、
  逆方向は `orchestrator.models.OrchestratorTask` のみ参照で健全）。両者とも config / storage /
  evaluator / prompt_builder / core.auth に依存。
- strategy.py の Protocol ベースの team/workflow 統一、judgment_client.py の「LLM呼び出しのみ」への
  責務限定は良い設計。問題は2つの中核ファイルの肥大化と相互の密結合に集中している。

## 評価サマリ（観点1〜5）

### 観点1: 責務と依存
- RoundController が「ラウンド制御」に加え **永続化**（`self.store is not None` ガードが7箇所、
  controller.py:329/371/387/433/451/488/527）と **UI向け進捗ファイル書き出し**（_write_progress_file、
  呼び出し7箇所）を抱え込み、SRP違反。
- Orchestrator が RoundController の **private メソッドを直接呼び出す**密結合:
  `controller._finalize_and_return_best(exit_reason, None)`（orchestrator.py:409）、
  `controller._write_progress_file(...)`（orchestrator.py:513、コメントで「密結合のため許容」と自認）。
- 設定の二重ロード: Orchestrator が `load_unit_settings` で全チームTOMLをロード（orchestrator.py:203-206）
  した直後、RoundController の `__init__` が同じTOMLを再ロード（controller.py:91-92）。
  orchestrator.py:201 のコメント「3回ロードする無駄を避ける」が半分しか達成されていない。

### 観点2: 設計上の臭い
- Logfire のオプショナル import + `LOGFIRE_AVAILABLE` フラグ + 「spanあり/なしで `_impl` に分岐」
  パターンが orchestrator.py:16-21/166-175、controller.py:41-46/204-216、workflow/executable.py:46-49 の
  **3箇所に重複**（DRY違反）。`contextlib.nullcontext` を使えば `_execute_impl`/`_run_round_impl` の
  二重化自体が不要。
- `_should_continue_round` 内で `store.save_round_status(...)` のほぼ同一引数の呼び出しが
  **3回重複**（controller.py:433-444, 451-462, 488-499）。
- `OrchestratorTask` 生成の if/else 二重化（orchestrator.py:141-163、execution_id の有無だけで
  全引数を二重記述）。
- `Evaluator` をラウンドごとに再生成（controller.py:337-340）。設定は不変なので `__init__` で1回が妥当。
- `orchestrator/models.py` の `RoundResult`（models.py:68）は本番コードで未使用
  （`__init__.py` 公開とテストのみ）。Feature 037 で `LeaderBoardEntry` に置換済みの残骸。
- `EvaluationConfig` の `# noqa: F401` import と `EvaluationRequest.model_rebuild()` の
  モジュールimport時副作用（controller.py:23, 49）。

### 観点3: AGENTS.md 自己ルール違反
- **300行超ファイル**: orchestrator.py 530行、controller.py 567行（いずれも実測）。
- **200行超関数**: `Orchestrator._execute_impl` が orchestrator.py:177-379 の **203行**。
- `os.getenv` 直接呼び出し: 担当範囲には**なし**（utils.env / ConfigurationManager 経由で規約準拠）。
- ロギング: `logging.getLogger(__name__)` 自体は observability/logging_setup.py の "mixseek" 親ロガーに
  伝播するため許容範囲だが、全ログが f-string 連結で `extra` フィールド未使用のため、
  **構造化JSONログの恩恵（team_id 等のキー検索）を受けられていない**。

### 観点4: エラー処理・型
- リトライ判定が `is_read_error = "ReadError" in error_type` という**型名の文字列比較**
  （orchestrator.py:466）。`httpx.ReadError` 等の例外型タプルでの `isinstance` 判定にすべきで、
  現状は無関係な自作例外名にもマッチし得る脆い実装。
- `exit_reason`（"max_rounds_reached" / "no_improvement_expected" / "partial_failure" 等）、
  進捗 status（"running"/"completed"/"failed"）、current_agent（"leader"/"evaluator"）が
  生文字列で散在。`StrEnum` / `Literal` 化で typo をmypyで検出可能にできる。
- `span: Any | None`（orchestrator.py:181、controller.py:222）と `member_agents: dict[str, object]`
  （strategy.py:65）の弱い型注釈。controller.py は `from __future__ import annotations` 未使用。
- `_write_progress_file` の `except Exception: pass`（controller.py:179-181）は完全黙殺。
  意図的（本体処理を守る）だが debug ログすら無く、進捗が出ない障害の調査を困難にする。
- 例外設計は概ね良い: `PartialTeamFailureError`（orchestrator/models.py:94）による部分成功伝搬、
  `JudgmentAPIError`（exceptions.py:4）の provider/retry_count 付与は一貫している。

### 観点5: テスト被覆
安全網は**厚い**。リファクタの前提条件は良好。

- unit: tests/unit/orchestrator/（test_orchestrator.py 414行 + test_models.py 284行）、
  tests/unit/round_controller/（test_round_controller.py 861行、hooks 349行、run 93行、
  strategy 189行、improvement_judgment 193行）。部分成功リカバリ
  （test_run_team_partial_failure_with_round_history 等）や judge_on_final_round 分岐も被覆。
- integration: test_orchestrator_e2e.py 300行、test_workflow_orchestrator.py 238行、
  test_workflow_round_controller.py 206行。
- 注意点: strategy.py:11-15 の docstring が明記する通り、テストは
  `mixseek.round_controller.strategy.<symbol>` を patch するため、**import 位置の変更は patch を壊す**。
  また unit テストの一部は `_finalize_and_return_best` 等 private メソッドに依存しており、
  公開API化（候補2）の際にテスト側の追従が必要。

## リファクタリング候補

### 候補1: RoundController の責務分割（永続化・進捗レポートの抽出）
- **対象**: src/mixseek/round_controller/controller.py（567行）
- **問題**: 観点2・3。300行ルール違反。永続化ガード7箇所、`save_round_status` 同一引数3重複
  （controller.py:433-444, 451-462, 488-499）、UI向け進捗ファイルI/O（controller.py:132-181）が
  ラウンド制御ロジックに混在。
- **影響度**: 高 / **リスク**: 中（中核実行パス。ただしロジック移動のみで挙動不変にできる）
- **推奨アプローチ**:
  1. `RoundPersistence`（仮）を新設し、`store` への書き込み（save_aggregation /
     save_to_leader_board / save_round_status）を集約。`save_db=False` 時は no-op 実装
     （null object）にして `if self.store is not None` 分岐を全廃。
     execution_id / team_id / team_name の共通引数はコンストラクタで束ねる。
  2. `ProgressReporter`（仮）を新設し `_write_progress_file` を移動。公開メソッドにして
     Orchestrator からも正規に利用（候補2と連動）。
  3. あわせて `Evaluator` 生成を `__init__` へ移動（controller.py:337）、
     `EvaluationRequest.model_rebuild()` 副作用の置き場所を見直す。
  目標: controller.py を 300行未満に。
- **関連テスト**: tests/unit/round_controller/test_round_controller.py（DuckDB保存検証 test_single_round_duckdb_save 等）、
  tests/integration/test_workflow_round_controller.py。被覆は厚く安全網あり。
- **工数感**: M

### 候補2: Orchestrator→RoundController の結合整理（公開API化＋設定二重ロード解消）
- **対象**: src/mixseek/orchestrator/orchestrator.py:409, 498-520 / round_controller/controller.py:59-122
- **問題**: 観点1・2。private メソッド `_finalize_and_return_best` / `_write_progress_file` の
  外部呼び出しによる密結合。同一チームTOML の二重ロード（orchestrator.py:203-206 と controller.py:91-92）。
- **影響度**: 中 / **リスク**: 低（インターフェース変更だが呼び出し元は Orchestrator のみ）
- **推奨アプローチ**:
  - RoundController に `finalize_partial_result(exit_reason) -> LeaderBoardEntry` と
    `report_error(error_message)` を公開APIとして定義し、Orchestrator 側の private 呼び出しを置換。
  - RoundController の `__init__` を `team_config_path` でなく
    `unit_settings: TeamSettings | WorkflowSettings` を受け取る形に変更し、
    Orchestrator がロード済みの設定を注入（ロード回数半減、テストの fixture も簡素化）。
- **関連テスト**: tests/unit/orchestrator/test_orchestrator.py（test_run_team_partial_failure_with_round_history,
  test_run_team_no_round_history_raises_original）。private 呼び出し前提のテストは追従修正が必要。
- **工数感**: S

### 候補3: Orchestrator._execute_impl（203行）の分割
- **対象**: src/mixseek/orchestrator/orchestrator.py:177-379
- **問題**: 観点3（1関数200行ルール違反）・観点1。設定ロード/auth確認/重複検査、controller生成、
  並列実行、結果集約、ExecutionSummary生成、DB保存、span記録が1関数に同居。
- **影響度**: 中 / **リスク**: 低（戻り値・例外契約を変えない純粋な抽出）
- **推奨アプローチ**: `_prepare_teams()`（ロード＋重複検査＋TeamStatus初期化）、
  `_collect_results()`（gather結果→team_results/failed_teams_info）、`_save_summary()`（DuckDB保存）
  に抽出。`OrchestratorTask` 生成の if/else 二重化（orchestrator.py:141-163）も
  「execution_id が None なら kwargs から除外」方式で一本化。
- **関連テスト**: tests/unit/orchestrator/test_orchestrator.py（test_execute_impl_handles_partial_team_failure,
  test_orchestrator_duplicate_team_id_raises_error）、tests/integration/test_orchestrator_e2e.py。
- **工数感**: S

### 候補4: Logfire オプショナル import / span 分岐の共通ヘルパー化
- **対象**: orchestrator.py:16-21,166-175,370-377 / controller.py:41-46,204-216,558-562 /
  （参考: workflow/executable.py:46-49 も同パターン）
- **問題**: 観点2（DRY違反）。try/except import と `LOGFIRE_AVAILABLE` 分岐、
  span 有無による `execute`/`_execute_impl` の二重化が3モジュールで重複。
- **影響度**: 中 / **リスク**: 低（観測コードのみ、ビジネスロジック不変）
- **推奨アプローチ**: `observability` パッケージに
  `maybe_span(name, **attrs) -> ContextManager`（logfire 不在時は `contextlib.nullcontext()` 相当の
  no-op span を返す）と `set_attributes(span, **attrs)` を実装。
  各所の `_impl` 分離を解消し、`span: Any | None` の引き回しも撤廃できる。
- **関連テスト**: 既存 unit テストは logfire 無効環境でも通る構造のため回帰検知可能。
  ヘルパー自体の unit テストを tests/observability/ に追加。
- **工数感**: S

### 候補5: エラー処理・定数の型安全化
- **対象**: orchestrator.py:461-496 / round_controller/controller.py, models.py
- **問題**: 観点4。`"ReadError" in error_type` の型名文字列比較（orchestrator.py:466）は
  無関係な例外にも誤マッチし得る。exit_reason / 進捗 status / current_agent が生文字列で散在し
  typo を静的検出できない。`except Exception: pass` の完全黙殺（controller.py:179-181）。
- **影響度**: 中 / **リスク**: 低（判定対象例外の網羅確認のみ要注意。httpx 系の transient エラーの
  範囲を integration テストで確認すること）
- **推奨アプローチ**:
  - リトライ対象を `RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (httpx.ReadError, ...)` で
    定義し `isinstance` 判定へ。TimeoutError 分岐と Exception 分岐で重複する
    「ステータス更新→部分成功リカバリ→進捗書き込み→raise」の後始末も共通化。
  - `ExitReason(StrEnum)` / `ProgressStatus(StrEnum)` を round_controller/models.py に定義し、
    `_should_continue_round` の戻り値型を `tuple[bool, ExitReason | None]` に。
  - `_write_progress_file` の握り潰しに `logger.debug` を追加（Orchestrator 側
    orchestrator.py:518-520 と同水準に統一）。あわせて未使用の `RoundResult`
    （orchestrator/models.py:68）の廃止を検討。
- **関連テスト**: tests/unit/orchestrator/test_orchestrator.py のリトライ/部分成功系、
  tests/unit/round_controller/test_round_controller.py の exit_reason 検証
  （test_best_score_submission_identification 等）が安全網。
- **工数感**: S

### 推奨着手順
候補4（独立・低リスク）→ 候補3 → 候補2 → 候補1（候補2の公開API化を前提に）→ 候補5。
候補1のみ M 規模のため、永続化抽出と進捗レポート抽出の2PRに分割することを推奨。
