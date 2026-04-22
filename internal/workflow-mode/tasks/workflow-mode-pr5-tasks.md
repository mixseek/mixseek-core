# PR5: Sample config + E2E integration tests

## Scope

実装者が E2E で workflow mode を動作確認できるサンプルと、
team/workflow mode 混在を検証する integration tests を追加。
本PRでワークフローモードが一貫動作することを最終検証する。

## Dependencies

- 前提PR: [PR1](workflow-mode-pr1-tasks.md), [PR2](workflow-mode-pr2-tasks.md),
  [PR3](workflow-mode-pr3-tasks.md), [PR4](workflow-mode-pr4-tasks.md)
  (PR4 は本PRの E2E タスクに `mixseek preflight` 実行を含むため必須)
- 設計根拠: [workflow-mode-plan.md §8.2, §8.4, §9, §11-9](workflow-mode-plan.md)

## Tasks

### Sample config (§8.4)

- [ ] `examples/workflow-sample/configs/orchestrator.toml` 新規
  - `[orchestrator]` + `[[orchestrator.teams]]` で workflow TOML 参照
  - `evaluator` / `judgment` 設定
- [ ] `examples/workflow-sample/configs/workflows/workflow_research.toml` 新規
  - 3 ステップ構成:
    - Step 1 `gather`: `web_search` + `plain` 並列
    - Step 2 `format`: `function` (`mypackage.formatters.format_as_markdown`)
    - Step 3 `synthesize`: `plain`
  - `include_all_context = true`, `final_output_format = "json"`
- [ ] `examples/workflow-sample/mypackage/__init__.py` 新規
- [ ] `examples/workflow-sample/mypackage/formatters.py` 新規
  - `format_as_markdown(input: str) -> str`
  - 入力: `{user_prompt, previous_steps}` JSON 文字列
  - 出力: Markdown 文字列
- [ ] `examples/workflow-sample/README.md` (optional)
  - `PYTHONPATH=examples/workflow-sample` または `pip install -e examples/workflow-sample/`
    必要な点を明記

### Integration tests (§8.2)

- [ ] `tests/integration/test_workflow_round_controller.py` 新規
  - 2 step (agent 並列 → function → agent) で `RoundController.run_round` を走らせる
  - `round_history` / `leader_board` / `round_status` が team と同じ形式で保存される確認
  - モデルは既存 `test_model` を使用 (外部 LLM を叩かない)
- [ ] `tests/integration/test_workflow_orchestrator.py` 新規
  - `orchestrator.toml` に `[team]` と `[workflow]` を混在させ並列実行
  - 両方成功、`execution_summary` に両方入ることを確認
- [ ] `tests/integration/test_workflow_hard_failure.py` 新規
  - Round 1 で function 例外 → `TeamStatus="failed"`
  - Round 2 成功後に function 失敗 → `PartialTeamFailureError` で best_round 採用

### E2E 手動検証 (§9)

- [ ] `cp -rp examples/workflow-sample workspaces/`
- [ ] `export MIXSEEK_WORKSPACE=workspaces/workflow-sample`
- [ ] `export PYTHONPATH=$MIXSEEK_WORKSPACE` (または `pip install -e $MIXSEEK_WORKSPACE`)
- [ ] `mixseek exec "量子コンピュータの最新動向をまとめて" --config $MIXSEEK_WORKSPACE/configs/orchestrator.toml`
- [ ] 期待値確認 (DuckDB):
  - `round_history` に `team_id="research-pipeline"` が `round_number=1..N` 分
  - `member_submissions_record` に `agent_type="web_search"/"plain"/"function"` が混在
  - `leader_board.final_submission=true` が 1 件
  - `execution_summary.status="completed"`
- [ ] `LOGFIRE_ENABLED=1` で再実行し span 確認:
  - `orchestrator.execute` → `round_controller.run_round` → `workflow.engine.run` →
    `workflow.function` + pydantic-ai spans
  - `mixseek.workflow.function` log レコード
- [ ] `mixseek preflight` を workflow sample に対して実行し、エラー無しを確認 (PR4 依存)

### Regression (§9)

- [ ] `examples/orchestrator-sample` (team mode) が引き続き動く
- [ ] team/workflow 混在 TOML を preflight 実行

## Files touched

### 新規
- `examples/workflow-sample/configs/orchestrator.toml`
- `examples/workflow-sample/configs/workflows/workflow_research.toml`
- `examples/workflow-sample/mypackage/__init__.py`
- `examples/workflow-sample/mypackage/formatters.py`
- `examples/workflow-sample/README.md` (optional)
- `tests/integration/test_workflow_round_controller.py`
- `tests/integration/test_workflow_orchestrator.py`
- `tests/integration/test_workflow_hard_failure.py`

## Merge gate

- 全 integration test green
- E2E 手動検証が上記期待値を満たす
- `examples/orchestrator-sample` の team mode regression なし
- `make lint format-check type-check test-fast` 全通

## 注意事項

- `mypackage` は `importlib.import_module` で解決 (§10)。実行時に `PYTHONPATH` もしくは
  `pip install -e` 必要。integration test 側では `sys.path.insert` か `conftest.py` の
  `pytest fixture` で解決する
- `tests/integration/test_workflow_hard_failure.py` は function の例外で
  `WorkflowStepFailedError` → `TeamStatus="failed"` 昇格経路を検証する E2E 唯一の場所なので、
  フェイル動作のリグレッションをここで捕まえる
