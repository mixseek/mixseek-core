# PR5: Sample config + E2E integration tests

## Scope

実装者が E2E で workflow mode を動作確認できるサンプルと、
team/workflow mode 混在を検証する integration tests を追加。
本PRでワークフローモードが一貫動作することを最終検証する。

PR4.5 で `FunctionPluginMetadata.path` が追加された (`module` / `path` 排他) ため、
sample / 一部 integration test はその `path` 方式を前提に書く (PYTHONPATH 不要)。

## Dependencies

- 前提PR: [PR1](workflow-mode-pr1-tasks.md), [PR2](workflow-mode-pr2-tasks.md),
  [PR3](workflow-mode-pr3-tasks.md), [PR4](workflow-mode-pr4-tasks.md),
  [PR4.5](workflow-mode-pr4-5-tasks.md)
  (PR4 は本PRの E2E タスクに `mixseek exec --dry-run` 実行を含むため必須。
  PR4.5 は sample TOML を `path` 方式で書く前提として必須)
- 設計根拠: [workflow-mode-plan.md §8.2, §8.4, §9, §11-9](../workflow-mode-plan.md)
- 詳細実装計画: [.logs/plans/internal-workflow-mode-workflow-mode-pl-piped-dream.md](../../../.logs/plans/internal-workflow-mode-workflow-mode-pl-piped-dream.md)

## Tasks

### Sample config (§8.4)

- [ ] `examples/workflow-sample/configs/orchestrator.toml` 新規
  - `[orchestrator]` + `[[orchestrator.teams]]` で workflow TOML 参照
  - Evaluator / Judgment 設定はデフォルト動作 (`extra="forbid"` のためネスト不可)
- [ ] `examples/workflow-sample/configs/workflows/workflow_research.toml` 新規
  - 3 ステップ構成:
    - Step 1 `gather`: `web_search` + `plain` 並列
    - Step 2 `format`: `function` (PR4.5 の `path` 方式で `mypackage/formatters.py` を指定)
    - Step 3 `synthesize`: `plain`
  - `include_all_context = true`, `final_output_format = "json"`
- [ ] `examples/workflow-sample/mypackage/formatters.py` 新規
  - `format_as_markdown(input: str) -> str`
  - 入力: `{user_prompt, previous_steps}` JSON 文字列
  - 出力: Markdown 文字列
  - Note: PR4.5 の `path` 方式 (`_load_module_from_path`) は file を直接ロードするため、
    `mypackage/__init__.py` は **作成しない** (package 化不要)
- [ ] `examples/workflow-sample/README.md` 新規
  - PR4.5 の `path` 方式採用と、`cd "$MIXSEEK_WORKSPACE"` 必須を明記
  - DuckDB 検証 SQL / logfire span 期待値も収録

### Integration tests (§8.2)

- [ ] `tests/integration/_workflow_helpers.py` 新規
  - `FakeExecutable` / `install_fake_builder` / `write_workflow_toml` ヘルパー集約
  - pytest collection 対象外 (`_` プレフィックス)
- [ ] `tests/integration/test_workflow_round_controller.py` 新規
  - 3 step (agent 並列 → function → agent) で `RoundController.run_round` を走らせる
  - `round_history` / `leader_board` / `round_status` が team と同じ形式で保存される確認
  - `mixseek.workflow.engine.build_executable` を `install_fake_builder` で差し替え
- [ ] `tests/integration/test_workflow_orchestrator.py` 新規
  - `orchestrator.toml` に `team` (`tests/fixtures/team1.toml`) と `workflow` を混在させ並列実行
  - 両方成功、`execution_summary` に両方入ることを確認
  - サブテスト: `workflow_id` と既存 `team_id` の重複検出 (`Orchestrator._execute_impl`)
- [ ] `tests/integration/test_workflow_hard_failure.py` 新規
  - Test 1: Round 1 で function ERROR → 全ラウンド失敗 (`team_results == []`)
  - Test 2: Round 1 成功 → Round 2 で function ERROR → `partial_failure` リカバリで
    Round 1 entry が UPSERT 経由で `final_submission=TRUE/exit_reason="partial_failure"` に
- [ ] `tests/integration/test_workflow_function_path_engine.py` 新規 (PR4.5 引き継ぎ)
  - PR4.5 引き継ぎ §5 の要件: `path` 方式 plugin を `WorkflowEngine` 全体で通す E2E
  - 3 ケース: 絶対 path 正常系 / 絶対 path 不在 → `WorkflowStepFailedError` 昇格 /
    相対 path × `monkeypatch.chdir` で sample TOML 前提の回帰防止
  - 既存 `test_workflow_function_path.py` は `build_executable` までの配線確認のため、
    engine 全体経路は本ファイルでカバー

### E2E 手動検証 (§9)

- [ ] `cp -rp examples/workflow-sample workspaces/`
- [ ] `export MIXSEEK_WORKSPACE=$PWD/workspaces/workflow-sample`
- [ ] `export GOOGLE_API_KEY="..."` (または `GEMINI_API_KEY`)
- [ ] `cd "$MIXSEEK_WORKSPACE"` (PR4.5 `path` 方式は cwd 起点で解決するため必須)
- [ ] `mixseek exec --dry-run --config configs/orchestrator.toml`
  (preflight: schema / auth / workspace 書き込み権限を検証。
  `path` のファイル存在は **検証されない** — 本実行で初めて顕在化する)
- [ ] `mixseek exec "量子コンピュータの最新動向をまとめて" --config configs/orchestrator.toml`
- [ ] 期待値確認 (DuckDB):
  - `round_history` に `team_id="research-pipeline"` が `round_number=1..N` 分
  - `member_submissions_record` に `agent_type="web_search"/"plain"/"function"` が混在
  - `leader_board.final_submission=TRUE` が 1 件
  - `execution_summary.status="completed"`
- [ ] `LOGFIRE_ENABLED=1` で再実行し span 確認:
  - `orchestrator.execute` → `round_controller.run_round` → `workflow.engine.run` →
    `workflow.function` + pydantic-ai spans
  - `mixseek.workflow.function` log レコード

### Regression (§9)

- [ ] `examples/orchestrator-sample` (team mode) が引き続き動く (`mixseek exec --dry-run`)
- [ ] team/workflow 混在 TOML を preflight 実行 (任意。PR4 の
  `tests/unit/config/preflight/test_runner_dispatch.py` で網羅済み)

## Files touched

### 新規

- `examples/workflow-sample/configs/orchestrator.toml`
- `examples/workflow-sample/configs/workflows/workflow_research.toml`
- `examples/workflow-sample/mypackage/formatters.py`  (`__init__.py` は作成しない)
- `examples/workflow-sample/README.md`
- `tests/integration/_workflow_helpers.py`
- `tests/integration/test_workflow_round_controller.py`
- `tests/integration/test_workflow_orchestrator.py`
- `tests/integration/test_workflow_hard_failure.py`
- `tests/integration/test_workflow_function_path_engine.py`  (PR4.5 引き継ぎ)

### 更新 (本 PR で同時に同期)

- `internal/workflow-mode/tasks/workflow-mode-pr5-tasks.md` (本ファイル)
- `internal/workflow-mode/workflow-mode-plan.md` §8.4 / §10 に PR4.5 反映の 1 行注釈

## Merge gate

- 4 本の workflow integration test が全て green。特に
  `test_workflow_function_path_engine.py` の 3 ケース (絶対 path 正常 / 絶対 path 不在 /
  相対 path × `monkeypatch.chdir`) で、`path` 方式 plugin の実 loader
  (`_load_module_from_path`) が engine 全体経路で動作することを CI で担保
- `examples/workflow-sample` の TOML 構文 / schema が `mixseek exec --dry-run --config
  configs/orchestrator.toml` で OK 化される (preflight は schema レベルのみ。
  `_load_module_from_path` は通らないため path file 存在は検証されない)
- E2E 手動検証で DuckDB 期待値達成 / logfire span 確認
- `examples/orchestrator-sample` の team mode regression なし
- `make -C dockerfiles/ci lint format-check type-check test-fast` 全通

## 注意事項

- **`cd "$MIXSEEK_WORKSPACE"` 必須**: sample TOML の function plugin は
  `path = "mypackage/formatters.py"` 相対 path で書かれる。相対 path は cwd 起点で
  解釈されるため、workspace 以外のディレクトリで `mixseek exec` を呼ぶと
  `Failed to load function from path 'mypackage/formatters.py'. FileNotFoundError: ...`
  で実行時エラーになる。`mixseek exec --dry-run` はこのエラーを **検出できない**
  (preflight は schema レベルのみ) ため、README / Quick start で必ず案内する。
- **PYTHONPATH は不要**: PR4.5 で `path` 方式が追加されたため、sample の
  `mypackage/` を `PYTHONPATH` に通したり `pip install -e` する必要はない。
  古い PR5 計画書の手順 (PR4.5 マージ前) には PYTHONPATH 設定が記載されていたが、
  本 PR で更新済み。
- `tests/integration/test_workflow_hard_failure.py` は function 例外で
  `WorkflowStepFailedError` → `TeamStatus="failed"` 昇格経路を検証する E2E 唯一の場所。
  `partial_failure` リカバリ経路 (`Orchestrator._try_recover_partial_failure` →
  `LeaderBoard` の UPSERT 更新) も Test 2 で網羅する。
