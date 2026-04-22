# PR1: Schema 追加 + member_agent_loader 共通化

## Scope

workflow mode に必要な Pydantic スキーマを `config/schema.py` に追加し、
team/workflow 両方から使う bundled system_instruction 解決ヘルパーを抽出する。
既存 team mode の挙動は**不変** (加算 + 軽微リファクタのみ)。

## Dependencies

- 前提PR: なし (`develop` から直接派生)
- 設計根拠: [workflow-mode-plan.md §5.1, §5.9, §11-1, §11-2](workflow-mode-plan.md)
- 後続ブロック解除: PR2, PR4 が並列着手可能になる

## Tasks

### Schema 追加 (§5.1)

- [ ] `config/schema.py` に `FunctionPluginMetadata` 追加 (§5.1.1)
- [ ] `config/schema.py` に `AgentExecutorSettings` 追加 (§5.1.2)
  - `to_member_agent_config(workspace)` は `_resolve_bundled_system_instruction` 経由
- [ ] `config/schema.py` に `FunctionExecutorSettings` 追加 (§5.1.3)
- [ ] `config/schema.py` に `StepExecutorConfig` (discriminated union) + `WorkflowStepSettings` 追加 (§5.1.4)
  - `discriminator="type"` で分岐 (`Literal` 値に重複なし)
  - step id / executor name の重複バリデーション (model_validator)
- [ ] `config/schema.py` に `WorkflowSettings` 追加 (§5.1.5)
  - `@property team_id` / `team_name` で `workflow_id` / `workflow_name` をマップ
  - workflow_id / workflow_name 非空バリデーション
  - step ids 重複バリデーション

### timeout_seconds 下限統一 (§10, §11-1)

- [ ] `MemberAgentSettings.timeout_seconds` を `ge=0` → `ge=1` に変更
  (下流 `MemberAgentConfig.timeout_seconds: ge=1` と一致させ、設定通過→実行段で落ちる
  遅延失敗を回避)
- [ ] 事前確認: `grep -rn "timeout_seconds.*=.*0" tests/` で `timeout_seconds=0` 用例が無い
  ことを確認 (無ければ回帰なし)

### member_agent_loader 共通化 (§5.9, §11-2)

- [ ] `config/member_agent_loader.py` に `_resolve_bundled_system_instruction(agent_type,
  system_instruction, workspace) -> str` を抽出 (既存 `member_settings_to_config` の
  L54-78 相当のロジック)
- [ ] 既存 `member_settings_to_config` を新ヘルパー経由にリファクタ

### テスト

- [ ] `tests/unit/config/test_workflow_settings.py` 新規
  - `workflow_id` / `workflow_name` 必須
  - step ids 重複 → `ValueError`
  - 同一ステップ内 executor names 重複 → `ValueError`
  - `type="function"` で `model` 不要、`plugin` 必須
  - `type="custom"` で `plugin` 必須
  - `team_id` / `team_name` プロパティが `workflow_id` / `workflow_name` を返す
  - discriminator 分岐 (agent/function 正しくパースされる)
- [ ] `tests/unit/config/test_member_agent_loader.py` に `_resolve_bundled_system_instruction`
  単体テスト追加 (リファクタ回帰防止)

## Files touched

### 新規
- `tests/unit/config/test_workflow_settings.py`

### 改修
- `src/mixseek/config/schema.py` (+ ~220行)
- `src/mixseek/config/member_agent_loader.py` (helper 抽出)
- `tests/unit/config/test_member_agent_loader.py` (回帰テスト追加)

## Merge gate

- 既存 team mode テスト全 green (特に `test_member_agent_loader.py`, `test_team_settings.py`)
- 新規 workflow schema テスト green
- `make lint format-check type-check test-fast` 全通

## 次PRへの signal

Merge 後、PR2 (workflow package) と PR4 (preflight) が並列着手可能。
