# PR2: workflow パッケージ + config source/manager

## Scope

workflow mode の実行エンジン一式を新規パッケージ `src/mixseek/workflow/` として追加。
既存コード改修は `config/manager.py` への関数追加のみ (既存関数は不変)。

## Dependencies

- 前提PR: [PR1](workflow-mode-pr1-tasks.md) (schema 型を import)
- 並列可能: [PR4](workflow-mode-pr4-tasks.md) とは同時着手 OK (touch 範囲が完全分離)
- 設計根拠: [workflow-mode-plan.md §5.2, §5.6, §5.7, §11-3, §11-4](workflow-mode-plan.md)

## Tasks

### workflow パッケージ (§5.2)

- [ ] `src/mixseek/workflow/__init__.py` 新規 (re-export)
- [ ] `src/mixseek/workflow/models.py` 新規 (§5.2.1)
  - `ExecutableResult`, `StepResult`, `ExecutableOutput`, `WorkflowContext`, `WorkflowResult`, `StrategyResult`
  - `WorkflowContext.build_task_context` / `_serialize` / `_all_previous_steps` / `_last_previous_step`
  - `_serialize` は 4 フィールド固定: `executor_name` / `status` / `content` / `error_message`
- [ ] `src/mixseek/workflow/exceptions.py` 新規 (§5.2.3)
  - `WorkflowStepFailedError`
- [ ] `src/mixseek/workflow/executable.py` 新規 (§5.2.2)
  - `Executable` Protocol
  - `AgentExecutable` (BaseMemberAgent ラッパー、3 キー context 合成)
  - `FunctionExecutable` (sync/async 両対応, `asyncio.wait_for` で timeout 統一適用)
  - `_logfire_span` ヘルパー (logfire 未導入時 `nullcontext` fallback)
  - `build_executable`, `_load_function`
- [ ] `src/mixseek/workflow/engine.py` 新規 (§5.2.4)
  - `WorkflowEngine.run` / `_execute_step` / `_run_one` / `_build_submission_content`
  - `_logfire_span("workflow.engine.run", ...)` で Leader span 階層を補完
  - **D3 準拠**: step 順 × executor 定義順で `all_messages` 連結
  - **D4 準拠**: function ERROR は `WorkflowStepFailedError` 即昇格
  - `_build_submission_content` は `user_prompt` を**含めない** (Round 再帰膨張回避)
  - 4 ケース整形 (json+all / json+last / text+all / text+last)
  - `build_executable` 例外も `WorkflowStepFailedError` に昇格

### config/ 拡張 (§5.6, §5.7)

- [ ] `src/mixseek/config/sources/workflow_toml_source.py` 新規 (§5.7)
  - `[workflow]` セクション必須
  - `workflow` 配下を平坦化 (`workflow_id`, `workflow_name`, `default_model`,
    `include_all_context`, `final_output_format`, `steps`)
  - `default_model` 省略時は `WorkflowSettings` のデフォルト値 (Pydantic field default)
    にフォールバックするため、source 側で辞書に含まれていれば上書き、なければ key ごと省略する
  - executor の `config = "..."` 参照解決はしない (Non-goal)
- [ ] `src/mixseek/config/manager.py` に `load_workflow_settings` 追加 (§5.6)
- [ ] `src/mixseek/config/manager.py` に `load_unit_settings` 追加 (§5.6)
  - TOML トップレベルキーで `[team]` / `[workflow]` 判別
  - 両方あり / どちらもなし → `ValueError`
- [ ] `src/mixseek/config/__init__.py` に `WorkflowSettings` 等 re-export (optional)

### テスト

- [ ] `tests/unit/workflow/__init__.py` 新規
- [ ] `tests/unit/workflow/test_models.py` 新規
  - `WorkflowContext.build_task_context` JSON スキーマ (`{user_prompt, previous_steps}`)
  - `_serialize` 4 フィールド固定
  - `_last_previous_step` で Step 1 時 `{}` 返却
  - `include_all=True` vs `False` の挙動差
- [ ] `tests/unit/workflow/test_executable.py` 新規
  - `AgentExecutable` 正常/例外 (status/error_message 伝搬)
  - `FunctionExecutable` sync/async/例外/timeout
  - `build_executable` 型分岐 (agent vs function vs 未知型)
  - `_load_function` エラー (module not found / attr not found / not callable)
  - logfire 未導入時に `nullcontext` fallback で落ちない
- [ ] `tests/unit/workflow/test_engine.py` 新規
  - 単一/並列ステップ
  - `include_all_context` true/false × `final_output_format` json/text の 4 ケース
  - agent soft failure (submission 積まれる、ラウンド継続)
  - function hard failure (`WorkflowStepFailedError` 昇格、後続ステップ未実行)
  - submission 積み順 (deps.submissions に step 順 × executor 定義順で入る)
  - `build_executable` 例外時に `WorkflowStepFailedError` 昇格
  - `_build_submission_content` に `user_prompt` が含まれない (膨張回避の invariant)
- [ ] `tests/unit/config/test_workflow_toml_source.py` 新規
  - `[workflow]` 正常読み込み
  - `[workflow]` 欠如時エラー
  - step/executor 配列の平坦化
  - `default_model` を TOML で指定すると `WorkflowSettings.default_model` に反映される
  - `default_model` 省略時は Pydantic field default が使われる
- [ ] `tests/unit/config/test_unit_settings.py` 新規
  - team/workflow 振り分け (戻り値の型)
  - 両方あり → `ValueError`
  - どちらもなし → `ValueError`

## Files touched

### 新規
- `src/mixseek/workflow/__init__.py`
- `src/mixseek/workflow/models.py`
- `src/mixseek/workflow/exceptions.py`
- `src/mixseek/workflow/executable.py`
- `src/mixseek/workflow/engine.py`
- `src/mixseek/config/sources/workflow_toml_source.py`
- `tests/unit/workflow/__init__.py`
- `tests/unit/workflow/test_models.py`
- `tests/unit/workflow/test_executable.py`
- `tests/unit/workflow/test_engine.py`
- `tests/unit/config/test_workflow_toml_source.py`
- `tests/unit/config/test_unit_settings.py`

### 改修
- `src/mixseek/config/manager.py` (`load_workflow_settings` / `load_unit_settings` 追加)
- `src/mixseek/config/__init__.py` (re-export, optional)

## Merge gate

- 既存 team mode テスト全 green (`config/manager.py` 改修の回帰確認)
- 新規 workflow unit テスト全 green
- coverage 80% 以上維持
- `make lint format-check type-check test-fast` 全通

## 実装順序 (PR 内)

1. `models.py` + `exceptions.py` (schema 依存なし、先に書ける)
2. `executable.py` (models 依存 + schema 依存)
3. `engine.py` (executable 依存)
4. `workflow_toml_source.py` (schema のみ依存)
5. `manager.py` に関数追加 (workflow_toml_source 依存)
6. 各段階で該当単体テストを通す

## 次PRへの signal

Merge 後、PR3 (strategy + controller) が着手可能。
