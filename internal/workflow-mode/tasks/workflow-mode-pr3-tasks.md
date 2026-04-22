# PR3: Strategy 導入 + RoundController/Orchestrator 切替

## Scope

既存 team mode のロジックを `LeaderStrategy` に carve-out し、
`RoundController` / `Orchestrator` を strategy ベースに差し替え。
**最もリスクが高いフェーズ**: 既存経路を保ちつつ workflow mode を合流させる。

## Dependencies

- 前提PR: [PR1](workflow-mode-pr1-tasks.md), [PR2](workflow-mode-pr2-tasks.md)
- 設計根拠: [workflow-mode-plan.md §5.3, §5.4, §5.5, §8.3, §11-5, §11-6, §11-7](workflow-mode-plan.md)

## Risk

**高** — 既存 team mode の behavior-preserving refactor。
**既存テストが全通過することが最優先の merge gate。**

## Tasks

### Strategy 新規 (§5.3)

- [ ] `src/mixseek/round_controller/strategy.py` 新規
  - `ExecutionStrategy` Protocol
  - `LeaderStrategy` (既存 controller の Member 生成〜Leader 実行を carve-out)
  - `WorkflowStrategy` (`WorkflowEngine.run()` 委譲)
  - **module-level import** (`create_leader_agent` を関数内ローカルにしない —
    テストの patch 先を `mixseek.round_controller.strategy.create_leader_agent` に統一)
- [ ] `src/mixseek/round_controller/__init__.py` に strategy を re-export

### RoundController 改修 (§5.4)

- [ ] `__init__` (既存 L52-107): `load_team_settings` → `load_unit_settings`
- [ ] `__init__`: 戻り値の type で strategy 決定
  - `TeamSettings` → `LeaderStrategy` + `self.team_config = team_settings_to_team_config(...)`
  - `WorkflowSettings` → `WorkflowStrategy` + `self.team_config = None`
  - その他 → `TypeError`
- [ ] `__init__`: `self.team_id` / `self.team_name` を `unit_settings.team_id/team_name` から保持
- [ ] `get_team_id()` / `get_team_name()` を `self.team_id` / `self.team_name` 返却に変更
- [ ] **`self.team_config.team_id` / `.team_name` 参照を 1 箇所ずつ置換** (§11-6)
  - 手順:
    1. `grep -n "self\.team_config" src/mixseek/round_controller/controller.py` で全件目視
    2. `Edit` で **1 箇所ずつ** 置換 (`self.team_id` / `self.team_name`)
    3. 各修正後に `grep` で残件確認
    4. `self.team_config` 単独参照 (例: L88, L300 の `create_leader_agent(self.team_config, ...)`)
       は LeaderStrategy に移植されるため workflow 到達しない経路と確認
  - **`replace_all` 禁止** (`self.team_config.members` / `.leader` 等の他アクセスが紛れる)
- [ ] `_execute_single_round` (既存 L266-413):
  - 「Member Agents 作成」〜「Leader Agent 実行」を `strategy.execute(user_prompt, deps)` 1 呼び出しに置換
  - 以降 (`MemberSubmissionsRecord` 生成以降) は**無変更**
  - `message_history` は `StrategyResult.all_messages` 経由
- [ ] `_format_prompt_for_round` / `_should_continue_round` / `_finalize_and_return_best`:
  **#2 置換以外無変更**
- [ ] `on_round_complete` hook と `run_round(user_prompt, timeout_seconds)` シグネチャ:
  **変更しない**
- [ ] 進捗ファイル (`_write_progress_file` の `current_agent`): workflow mode は `None` 統一

### Orchestrator 改修 (§5.5)

- [ ] `load_team_config` 直呼び 3 箇所 (既存 L186-218) を `ConfigurationManager.load_unit_settings`
  経由に差し替え
- [ ] `_primary_model_of` ヘルパー追加 (plan §5.5)
  - `TeamSettings` → `leader.get("model") or LeaderAgentSettings.model_fields["model"].default`
  - `WorkflowSettings` → `WorkflowSettings.default_model`
- [ ] import 修正:
  - 削除: `from mixseek.agents.leader.config import load_team_config`
  - 追加: `from mixseek.config.schema import LeaderAgentSettings, TeamSettings, WorkflowSettings`

### 既存テスト patch 先修正 (§8.3)

- [ ] `grep -rn "mixseek.round_controller.controller\." tests/` で全箇所洗う
- [ ] `create_leader_agent` patch: `...controller.create_leader_agent` →
  `...strategy.create_leader_agent` (unit/round_controller 配下 + integration の
  prompt_builder/orchestrator_e2e に計 ~15 箇所)
- [ ] `load_team_settings` patch: `load_unit_settings` に差し替え
- [ ] `orchestrator.load_team_config` patch: `load_unit_settings` ベースのモックに差し替え
- [ ] `team_settings_to_team_config` / `MemberAgentFactory` 等の patch パス見直し
  (controller → strategy 移動に伴うもの)
- [ ] 除外対象: CLI 層 (`tests/unit/cli/test_team_command.py`)、`test_leader_agent_e2e.py`、
  `test_http_timeout.py` (patch していない)

### 新規テスト

- [ ] `tests/unit/round_controller/test_strategy.py` 新規
  - `LeaderStrategy.execute` が既存挙動を再現 (Leader Agent 生成〜実行)
  - `WorkflowStrategy.execute` が `WorkflowEngine.run` を呼ぶ
  - `StrategyResult` の `submission_content` / `all_messages` 構造

## Files touched

### 新規
- `src/mixseek/round_controller/strategy.py`
- `tests/unit/round_controller/test_strategy.py`

### 改修
- `src/mixseek/round_controller/controller.py` (~100行差し替え + ~30箇所置換)
- `src/mixseek/round_controller/__init__.py`
- `src/mixseek/orchestrator/orchestrator.py` (3 箇所 + `_primary_model_of` 追加)
- `tests/unit/round_controller/*.py` (patch 先修正 ~15 箇所)
- `tests/integration/` 配下の該当テスト (prompt_builder/orchestrator_e2e 等)

## Merge gate

- **既存 team mode テスト全 green** (最重要)
- `grep -n "self\.team_config\." src/mixseek/round_controller/controller.py` で
  workflow mode 到達経路に残件ゼロ
- 新規 `test_strategy.py` green
- `make lint format-check type-check test-fast` 全通

## 実装順序 (PR 内)

1. `strategy.py` に `LeaderStrategy` を書く (既存 controller からコピペ + 引数 deps 化)
2. 既存テスト patch 先修正 — 実装差し替え前に新 patch パスでも動く状態にする
3. controller `__init__` の strategy 分岐を**team のみ**先行導入
4. `_execute_single_round` の差し替え — **ここでも既存テスト green を必ず確認**
5. `self.team_config.team_id` 一斉洗い出し & 1つずつ置換
6. workflow 分岐を `__init__` に足す + `WorkflowStrategy` 配線
7. orchestrator 差し替え

## 次PRへの signal

Merge 後、PR5 (sample + E2E integration) が着手可能。
PR4 (preflight) は本PRと独立に merge 可 (PR3 完了を待つ必要なし)。
