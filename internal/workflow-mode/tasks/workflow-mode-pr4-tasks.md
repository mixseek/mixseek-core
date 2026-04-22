# PR4: Preflight 拡張

## Scope

`mixseek preflight` が workflow TOML を正しく検証できるよう validator を拡張。
team/workflow を TOML トップレベルキーで判別し、auth 検証も workflow の
agent executor model を収集する。

## Dependencies

- 前提PR: [PR1](workflow-mode-pr1-tasks.md) (`WorkflowSettings` schema 使用),
  [PR2](workflow-mode-pr2-tasks.md) (`load_unit_settings` / `load_workflow_settings` を呼ぶため)
- 並列可能: [PR3](workflow-mode-pr3-tasks.md) と同時着手 OK
  (workflow engine 本体には依存しない、touch 範囲が `config/preflight/` に閉じる)
- 設計根拠: [workflow-mode-plan.md §5.8, §10 (判別失敗 skip 回帰), §11-8](workflow-mode-plan.md)

## Design invariant

**全 config が必ずどこかの validator で ERROR 化される**性質を維持する。

`_detect_unit_kind` の `"unknown"` (TOML 解析失敗 / 両方あり / どちらもなし) は
team validator 側で `load_unit_settings` を呼び `ValueError` / `FileNotFoundError` /
`TOMLDecodeError` を ERROR CheckResult 化する経路を**必ずテストで検証**する。

## Tasks

### Validator 新規 (§5.8.1)

- [ ] `src/mixseek/config/preflight/validators/workflow.py` 新規
  - `_validate_workflows(settings, workspace, unit_kind_map) -> (CategoryResult, list[WorkflowSettings])`
  - `unit_kind_map[config] == "workflow"` のみ `ConfigurationManager.load_workflow_settings()`
    で検証し `CheckResult` を積む
  - それ以外は skip (`_validate_teams` 側で処理される)

### Validator 改修 (§5.8.2, §5.8.4)

- [ ] `src/mixseek/config/preflight/validators/team.py`
  - `_validate_teams(settings, workspace, *, unit_kind_map=None)` シグネチャ追加
  - `unit_kind_map` で `kind == "workflow"` のみ skip
  - それ以外 (`"team"` / `"unknown"`) は全て `load_unit_settings()` で検証
    (`FileNotFoundError` / `TOMLDecodeError` / `ValueError` を ERROR 化)
  - 戻り値 `isinstance(result, TeamSettings)` を assert (想定外 `WorkflowSettings` 検出)
  - `unit_kind_map` 未指定時は既存挙動 (全 config を `load_team_settings`) を維持 (後方互換)
- [ ] `src/mixseek/config/preflight/validators/auth.py`
  - `_collect_model_ids(..., *, workflow_settings_list=None)` 追加
  - `_validate_auth(..., *, workflow_settings_list=None)` 追加
  - workflow からは **`default_model`** と各 agent executor の `model` (指定時のみ) を収集
    (function は model なしで無視、plan §5.8.4):
    ```python
    for wf in (workflow_settings_list or []):
        model_ids.add(wf.default_model)  # デフォルトモデルも必ず認証検証対象
        for step in wf.steps:
            for exe in step.executors:
                if isinstance(exe, AgentExecutorSettings) and exe.model:
                    model_ids.add(exe.model)
    ```
  - 既存 positional 呼び出しの互換維持 (キーワード + default)
  - team 側の既存実装 (`auth.py:50-67` dict/Pydantic 両対応) は**触らない**

### Runner dispatch (§5.8.3)

- [ ] `src/mixseek/config/preflight/runner.py`
  - `unit_kind_map` 生成 (各 `entry.get("config")` に `_detect_unit_kind` 適用)
  - `_validate_teams` / `_validate_workflows` 両方呼び出し
  - `categories.extend([team_result, wf_result])`
  - `_validate_auth(..., workflow_settings_list=workflow_settings_list)` 配線
- [ ] `src/mixseek/config/preflight/validators/__init__.py` に `_detect_unit_kind` 追加
  - 戻り値: `Literal["team", "workflow", "unknown"]`
  - `[team]` のみ → `"team"`
  - `[workflow]` のみ → `"workflow"`
  - 両方あり / どちらもなし / TOML 解析失敗 → `"unknown"`

### テスト

- [ ] `tests/unit/config/preflight/test_workflow_validator.py` 新規
  - workflow TOML 正常検証で OK CheckResult
  - 不正 schema → ERROR CheckResult
  - `unit_kind_map[config] != "workflow"` は skip
- [ ] `tests/unit/config/preflight/test_detect_unit_kind.py` 新規
  - `[team]` のみ → `"team"`
  - `[workflow]` のみ → `"workflow"`
  - 両方あり → `"unknown"`
  - どちらもなし → `"unknown"`
  - TOML 解析失敗 (不正構文) → `"unknown"`
  - ファイル not found → `"unknown"`
- [ ] `tests/unit/config/preflight/test_team_validator.py` 更新
  - `unit_kind_map` 指定時の skip 動作
  - **`"unknown"` が team validator で ERROR 化される回帰テスト** (§10 の invariant)
  - `unit_kind_map=None` 時の後方互換
- [ ] `tests/unit/config/preflight/test_auth_validator.py` 更新
  - workflow の `default_model` が必ず収集される
  - workflow の agent executor `model` (指定時) が収集される
  - function は model なしで無視される
  - 既存 positional 呼び出しが壊れない

## Files touched

### 新規
- `src/mixseek/config/preflight/validators/workflow.py`
- `tests/unit/config/preflight/test_workflow_validator.py`
- `tests/unit/config/preflight/test_detect_unit_kind.py`

### 改修
- `src/mixseek/config/preflight/validators/team.py`
- `src/mixseek/config/preflight/validators/auth.py`
- `src/mixseek/config/preflight/runner.py`
- `src/mixseek/config/preflight/validators/__init__.py`
- `tests/unit/config/preflight/test_team_validator.py`
- `tests/unit/config/preflight/test_auth_validator.py`

## Merge gate

- 既存 preflight テスト全 green
- `"unknown"` → team validator ERROR 化の invariant テスト green (最重要)
- `make lint format-check type-check test-fast` 全通

## 並列実行時の注意

- PR2 merge 後の `develop` を base にする (PR4 は `load_unit_settings` /
  `load_workflow_settings` を呼ぶため PR2 完了必須)
- PR3 と並列時は touch 対象が `round_controller/` vs `config/preflight/` で分離、conflict なし
- `config/schema.py` は read のみ (PR1 で追加された型を import)
- `config/manager.py` も read のみ (PR2 で追加された API を呼ぶだけ)

## 実装順序 (PR 内)

1. `_detect_unit_kind` をヘルパーに切り出し + 単体テスト
2. `auth.py` に `workflow_settings_list` パラメータ追加 (関数シグネチャのみ、collect は空)
3. `team.py` の `unit_kind_map` 対応 + skip 動作テスト
4. `workflow.py` 実装 + テスト
5. `runner.py` で dispatch 配線 + e2e 風テスト
