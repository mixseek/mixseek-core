# Quickstart Guide: Round Configuration in TOML

**Feature**: 101-round-config
**Audience**: システム運用者、開発者
**Date**: 2025-11-18

## Overview

このガイドでは、orchestrator.tomlファイルおよび環境変数を使用してラウンド実行パラメータを設定する方法を説明します。

## Basic Configuration

### Step 1: orchestrator.tomlに設定を追加

`orchestrator.toml`ファイルに以下のラウンド設定セクションを追加します：

```toml
# orchestrator.toml

workspace = "/path/to/workspace"
timeout_per_team_seconds = 300

# === Round Configuration ===
max_rounds = 5                       # 最大ラウンド数（デフォルト: 5）
min_rounds = 2                       # 最小ラウンド数（デフォルト: 2）
submission_timeout_seconds = 300     # Submission生成タイムアウト（デフォルト: 300秒）
judgment_timeout_seconds = 60        # 評価判定タイムアウト（デフォルト: 60秒）

[[teams]]
config = "path/to/team1.toml"

[[teams]]
config = "path/to/team2.toml"
```

### Step 2: 設定を検証

```bash
# 設定を確認（mixseek config listコマンド）
mixseek config list

# OrchestratorSettings配下に新規フィールドが表示されることを確認
# - max_rounds: 5
# - min_rounds: 2
# - submission_timeout_seconds: 300
# - judgment_timeout_seconds: 60
```

### Step 3: タスクを実行

```bash
# 通常実行（TOML設定を使用）
mixseek exec "Analyze sales data trends"

# 実行結果でラウンド数を確認
# Expected: 最大5ラウンドまで実行される
```

## Use Cases

### Use Case 1: 開発環境で高速テスト

開発時は少ないラウンド数で素早くテストしたい場合：

```toml
# orchestrator-dev.toml

max_rounds = 3                       # 開発環境: 3ラウンドまで
min_rounds = 1                       # 開発環境: 1ラウンドから終了判定可能
submission_timeout_seconds = 60      # 開発環境: 1分タイムアウト
judgment_timeout_seconds = 30        # 開発環境: 30秒タイムアウト
```

```bash
# 開発用設定で実行
mixseek exec "Test analysis" --config orchestrator-dev.toml
```

### Use Case 2: 本番環境で徹底的な改善

本番環境では複数ラウンドで品質を追求したい場合：

```toml
# orchestrator-prod.toml

max_rounds = 10                      # 本番環境: 最大10ラウンド
min_rounds = 3                       # 本番環境: 最低3ラウンド実行
submission_timeout_seconds = 600     # 本番環境: 10分タイムアウト
judgment_timeout_seconds = 120       # 本番環境: 2分タイムアウト
```

```bash
# 本番用設定で実行
mixseek exec "Production analysis" --config orchestrator-prod.toml
```

### Use Case 3: 環境変数による動的調整

CI/CD環境やKubernetes環境で環境変数を使用して動的に調整：

```bash
# Staging環境: 中間的な設定
export MIXSEEK_MAX_ROUNDS=7
export MIXSEEK_MIN_ROUNDS=2
export MIXSEEK_SUBMISSION_TIMEOUT_SECONDS=300
export MIXSEEK_JUDGMENT_TIMEOUT_SECONDS=90

# 実行（環境変数がTOML設定を上書き）
mixseek exec "Staging analysis"
```

### Use Case 4: 後方互換性（設定なし）

既存のorchestrator.tomlファイル（ラウンド設定なし）も引き続き動作：

```toml
# orchestrator-legacy.toml
# ラウンド設定フィールドが含まれていない既存ファイル

workspace = "/workspace"
timeout_per_team_seconds = 300

[[teams]]
config = "team1.toml"

# ↓ デフォルト値が自動的に使用される:
# - max_rounds = 5
# - min_rounds = 2
# - submission_timeout_seconds = 300
# - judgment_timeout_seconds = 60
```

## Environment Variable Override

### Override Precedence

環境変数はTOML設定を上書きします（優先順位: ENV > TOML > Default）：

```bash
# orchestrator.tomlに max_rounds = 5 が設定されている場合でも、
# 環境変数で上書き可能
export MIXSEEK_MAX_ROUNDS=7

# 実行（max_rounds = 7 が使用される）
mixseek exec "Analysis task"
```

### Full Environment Variable Example

```bash
#!/bin/bash

# すべてのラウンド設定を環境変数で設定

export MIXSEEK_WORKSPACE="/workspace"
export MIXSEEK_TIMEOUT_PER_TEAM_SECONDS=300

# Round configuration
export MIXSEEK_MAX_ROUNDS=8
export MIXSEEK_MIN_ROUNDS=3
export MIXSEEK_SUBMISSION_TIMEOUT_SECONDS=450
export MIXSEEK_JUDGMENT_TIMEOUT_SECONDS=90

# 実行（TOMLファイル不要）
mixseek exec "Analysis task"
```

### Docker Environment

```yaml
# docker-compose.yml

services:
  mixseek:
    image: mixseek-core:latest
    environment:
      - MIXSEEK_WORKSPACE=/workspace
      - MIXSEEK_MAX_ROUNDS=7
      - MIXSEEK_MIN_ROUNDS=2
      - MIXSEEK_SUBMISSION_TIMEOUT_SECONDS=400
      - MIXSEEK_JUDGMENT_TIMEOUT_SECONDS=80
    volumes:
      - ./workspace:/workspace
```

### Kubernetes ConfigMap

```yaml
# k8s-configmap.yaml

apiVersion: v1
kind: ConfigMap
metadata:
  name: mixseek-config
data:
  MIXSEEK_MAX_ROUNDS: "10"
  MIXSEEK_MIN_ROUNDS: "3"
  MIXSEEK_SUBMISSION_TIMEOUT_SECONDS: "600"
  MIXSEEK_JUDGMENT_TIMEOUT_SECONDS: "120"
```

## Troubleshooting

### Error 1: max_rounds out of range

**Symptom**:
```
ValidationError: 1 validation error for OrchestratorSettings
max_rounds
  Input should be greater than or equal to 1
```

**Cause**: max_roundsが範囲外（1～10以外）

**Solution**:
```toml
# ✗ Bad
max_rounds = 0    # 1未満
max_rounds = 15   # 10超過

# ✓ Good
max_rounds = 5    # 1～10の範囲内
```

### Error 2: min_rounds > max_rounds

**Symptom**:
```
ValidationError: 1 validation error for OrchestratorSettings
  Value error, min_rounds (5) must be <= max_rounds (3)
```

**Cause**: min_roundsがmax_roundsを超えている

**Solution**:
```toml
# ✗ Bad
max_rounds = 3
min_rounds = 5    # max_roundsを超えている

# ✓ Good
max_rounds = 5
min_rounds = 3    # max_rounds以下
```

### Error 3: Negative timeout

**Symptom**:
```
ValidationError: 1 validation error for OrchestratorSettings
submission_timeout_seconds
  Input should be greater than 0
```

**Cause**: タイムアウト値が負または0

**Solution**:
```toml
# ✗ Bad
submission_timeout_seconds = 0      # 0は不可
submission_timeout_seconds = -100   # 負の値は不可

# ✓ Good
submission_timeout_seconds = 300    # 正の整数
```

### Error 4: Typo in field name

**Symptom**:
```
ValidationError: 1 validation error for OrchestratorSettings
  Extra inputs are not permitted [type=extra_forbidden]
```

**Cause**: フィールド名のタイプミス（`extra="forbid"`により検出）

**Solution**:
```toml
# ✗ Bad (タイプミス)
max_round = 5           # "max_rounds"が正しい
minrounds = 2           # "min_rounds"が正しい
submission_timeout = 300 # "submission_timeout_seconds"が正しい

# ✓ Good
max_rounds = 5
min_rounds = 2
submission_timeout_seconds = 300
```

### Error 5: Wrong data type

**Symptom**:
```
ValidationError: 1 validation error for OrchestratorSettings
max_rounds
  Input should be a valid integer
```

**Cause**: 整数フィールドに文字列や小数が指定されている

**Solution**:
```toml
# ✗ Bad
max_rounds = "5"    # 文字列は不可
max_rounds = 5.5    # 小数は不可

# ✓ Good
max_rounds = 5      # 整数
```

## Verification Commands

### Check Configuration

```bash
# すべての設定を表示
mixseek config list

# OrchestratorSettings配下のラウンド設定を確認
# - max_rounds
# - min_rounds
# - submission_timeout_seconds
# - judgment_timeout_seconds

# 特定の設定グループを表示
mixseek config show orchestrator
```

### Dry Run (Configuration Test)

```bash
# 設定を検証（実行なし）
mixseek exec "Test task" --dry-run

# Expected output:
# Configuration loaded successfully
# - max_rounds: 5
# - min_rounds: 2
# - submission_timeout_seconds: 300
# - judgment_timeout_seconds: 60
```

### Debug Mode

```bash
# デバッグモードで設定読み込みを確認
MIXSEEK_LOG_LEVEL=DEBUG mixseek exec "Test task"

# ログで設定値を確認:
# DEBUG: OrchestratorSettings loaded: max_rounds=5, min_rounds=2, ...
```

## Best Practices

### 1. 環境ごとに設定ファイルを分離

```
configs/
├── orchestrator-dev.toml       # 開発環境: 高速テスト設定
├── orchestrator-staging.toml   # ステージング: 中間設定
└── orchestrator-prod.toml      # 本番環境: 徹底的な改善設定
```

### 2. デフォルト値の明示的な文書化

```toml
# orchestrator.toml

# Round Configuration
# デフォルト値はOrchestratorTaskと一致（Feature 037準拠）
max_rounds = 5                       # Default: 5  (range: 1-10)
min_rounds = 2                       # Default: 2  (range: 1-max_rounds)
submission_timeout_seconds = 300     # Default: 300 (5 minutes)
judgment_timeout_seconds = 60        # Default: 60  (1 minute)
```

### 3. CI/CD環境では環境変数を優先

```bash
# .gitlab-ci.yml

test:
  variables:
    MIXSEEK_MAX_ROUNDS: "3"          # CI: 高速テスト
    MIXSEEK_MIN_ROUNDS: "1"
    MIXSEEK_SUBMISSION_TIMEOUT_SECONDS: "60"
  script:
    - mixseek exec "Test analysis"

production:
  variables:
    MIXSEEK_MAX_ROUNDS: "10"         # Production: 徹底的な改善
    MIXSEEK_MIN_ROUNDS: "3"
    MIXSEEK_SUBMISSION_TIMEOUT_SECONDS: "600"
  script:
    - mixseek exec "Production analysis"
```

### 4. バリデーションエラーは早期に検出

```bash
# 設定変更後は必ず検証
mixseek config list

# または
mixseek exec "Test" --dry-run
```

## FAQ

### Q1: ラウンド設定を指定しない場合はどうなりますか？

**A**: デフォルト値が自動的に使用されます：
- max_rounds = 5
- min_rounds = 2
- submission_timeout_seconds = 300
- judgment_timeout_seconds = 60

既存のorchestrator.tomlファイルは変更なしで動作します（後方互換性）。

### Q2: timeout_per_team_secondsとの関係は？

**A**: 独立したタイムアウトです：
- `timeout_per_team_seconds`: オーケストレータレベルの全体タイムアウト
- `submission_timeout_seconds`/`judgment_timeout_seconds`: ラウンドレベルのタイムアウト

相互検証は不要です（Clarifications Session 2025-11-18）。

### Q3: 環境変数とTOMLファイルの両方を設定した場合は？

**A**: 環境変数が優先されます：

優先順位: **環境変数 > TOMLファイル > デフォルト値**

```toml
# orchestrator.toml
max_rounds = 5
```

```bash
# 環境変数で上書き
export MIXSEEK_MAX_ROUNDS=7

# 実行 → max_rounds = 7 が使用される
mixseek exec "Task"
```

### Q4: max_roundsに達した場合の動作は？

**A**: その時点での最高スコアSubmissionが最終結果として返されます（FR-011）。

### Q5: min_roundsの目的は？

**A**: LLMベースの早期終了判定を防ぐためです。min_rounds未満では、終了判定が実行されず、必ず指定されたラウンド数まで実行されます。

## Related Documentation

- [spec.md](./spec.md): 機能要件と成功基準
- [data-model.md](./data-model.md): Pydanticモデル設計
- [research.md](./research.md): 技術調査結果
- [plan.md](./plan.md): 実装計画

## Support

問題が解決しない場合：

1. ログを確認: `MIXSEEK_LOG_LEVEL=DEBUG mixseek exec "Task"`
2. 設定を検証: `mixseek config list`
3. GitHubでissueを作成: https://github.com/AlpacaTechSolution/mixseek-core/issues
