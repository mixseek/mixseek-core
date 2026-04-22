# ワークフローモード 実装タスク分割 (Overview)

原設計: [workflow-mode-plan.md](workflow-mode-plan.md)

## 分割方針

加算系 (PR1, PR2, PR4) と差し替え系 (PR3) を分離し、最もリスクの高い
`RoundController` 改修 (PR3) の回帰検出性を最大化する。各PRは独立して
すべての品質チェックが green になる状態でマージする。

## 依存関係

```
PR1 (schema + loader refactor)
 └──> PR2 (workflow pkg + config source/manager)
       ├──> PR3 (strategy + controller + orchestrator) ──┐
       └──> PR4 (preflight)                              ├──> PR5 (sample + E2E integration)
                                                         ┘
```

- PR4 は `load_unit_settings` / `load_workflow_settings` (PR2 追加) を呼ぶため
  PR2 merge 後でないと着手できない。
- PR5 は E2E タスクで `mixseek preflight` を実行するため PR4 merge も必須。
- PR3 と PR4 は並列着手可能。

## 並列実行マトリクス

| フェーズ | 同時着手可能PR | ブロッカー |
|---|---|---|
| 1 | PR1 | なし |
| 2 | PR2 | PR1 merge |
| 3 | PR3, PR4 | PR2 merge |
| 4 | PR5 | PR1 + PR2 + PR3 + PR4 merge (PR5 の E2E に `mixseek preflight` 実行を含むため) |

並列時の conflict 想定:
- **PR3 × PR4**: touch 対象が `round_controller/` vs `config/preflight/` → conflict なし
- rebase は念のため実施

## クリティカルパス

PR1 → PR2 → PR3 → PR5 (4 フェーズ) — PR3 が PR4 より重い想定。

PR4 は PR3 と並列で走るが PR5 前に merge 必須 (PR5 の E2E が preflight を使うため)。
PR4 が PR3 より早く終われば critical path には乗らない。
PR1 着手から PR5 完了まで、逐次実行なら 5 単位、並列化で 4 単位に短縮。

## PR一覧

| # | タイトル | リスク | 規模目安 | 依存 |
|---|---|---|---|---|
| [PR1](workflow-mode-pr1-tasks.md) | Schema 追加 + member_agent_loader 共通化 | 低 | +~220行 / 改修 ~20行 | - |
| [PR2](workflow-mode-pr2-tasks.md) | workflow パッケージ + config source/manager | 低 | +~600行 (新規のみ) | PR1 |
| [PR3](workflow-mode-pr3-tasks.md) | Strategy 導入 + RoundController/Orchestrator 切替 | **高** | +~250行 / 改修 ~100行 | PR2 |
| [PR4](workflow-mode-pr4-tasks.md) | Preflight 拡張 | 中 | +~150行 / 改修 ~80行 | PR1+PR2 |
| [PR5](workflow-mode-pr5-tasks.md) | Sample + E2E integration tests | 低 | +~400行 (sample + tests) | PR1+PR2+PR3+PR4 |

## 共通マージゲート

全PR commit 前に以下を green にする:

```bash
make -C dockerfiles/ci lint format-check
make -C dockerfiles/ci type-check
make -C dockerfiles/ci test-fast
```

既存 team mode のテストが全通過することは全PR共通の必須条件。

## 推奨エージェント配分

- 単一エージェントで逐次実行: PR1 → PR2 → PR3 → PR4 → PR5
- 2エージェント並列時: {PR2 完了後} エージェントA = PR3→PR5, エージェントB = PR4
  (PR4 はエージェントBが PR5 まで手待ちになるため、完了後 PR5 の review/E2E 支援に回す)

## 注意事項

- PR3 の `self.team_config.team_id` 置換は約30箇所、**一括置換禁止** (feedback 記録済)
- 各PRの `Files touched` に明示した範囲外への diff は原則禁止
- 設計変更が必要な場合は `workflow-mode-plan.md` を先に更新し、影響PRで参照する
