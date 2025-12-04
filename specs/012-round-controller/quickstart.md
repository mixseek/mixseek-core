# Quickstart: Round Controller - ラウンドライフサイクル管理

**日付**: 2025-11-10
**対象**: 開発者、テスター

## 概要

本ドキュメントでは、Round Controller機能のクイックスタートガイドを提供します。既存の`025-mixseek-core-orchestration`実装を置き換え、複数ラウンド反復改善機能を追加します。

---

## 前提条件

- Python 3.13.9環境
- 環境変数`MIXSEEK_WORKSPACE`が設定済み
- DuckDB 1.0以降（`$MIXSEEK_WORKSPACE/mixseek.db`に配置）
- 既存のチーム設定TOML（`$MIXSEEK_WORKSPACE/configs/`配下）

---

## セットアップ

### 1. 環境変数設定

```bash
export MIXSEEK_WORKSPACE=/path/to/workspace
```

### 2. 依存関係インストール

```bash
uv sync
```

### 3. DuckDBスキーマ初期化

```bash
# DuckDB CLIで実行
duckdb $MIXSEEK_WORKSPACE/mixseek.db < specs/012-round-controller/contracts/schema.sql
```

または、Pythonコードで実行：

```python
from pathlib import Path
from mixseek.storage.aggregation_store import AggregationStore

workspace = Path("/path/to/workspace")
store = AggregationStore(db_path=workspace / "mixseek.db")

# schema.pyにDDL文を実装する（実装時に追加）
store.initialize_schema()
```

---

## 基本的な使い方

### 1. オーケストレータ設定TOML

既存の`orchestration.toml`にラウンド設定を追加します（オプション。設定しない場合はデフォルト値を使用）：

```toml
[orchestrator]
timeout_per_team_seconds = 600

# ラウンド設定（新規追加、オプション）
max_rounds = 5                      # 最大ラウンド数（デフォルト: 5）
min_rounds = 2                      # 最小ラウンド数（デフォルト: 2）
submission_timeout_seconds = 300    # Submissionタイムアウト（デフォルト: 300秒）
judgment_timeout_seconds = 60       # 次ラウンド判定タイムアウト（デフォルト: 60秒）

[[orchestrator.teams]]
config = "configs/team_a.toml"

[[orchestrator.teams]]
config = "configs/team_b.toml"
```

### 2. 単一ラウンド実行（既存互換）

```python
from pathlib import Path
from mixseek.orchestrator import Orchestrator, load_orchestrator_settings

workspace = Path("/path/to/workspace")
settings = load_orchestrator_settings(Path("orchestration.toml"), workspace)

orchestrator = Orchestrator(settings=settings)

# 非同期実行
import asyncio

async def main():
    summary = await orchestrator.execute(
        user_prompt="データ分析タスク",
        timeout_seconds=600,
    )

    print(f"Best Team: {summary.best_team_id}")
    print(f"Best Score: {summary.best_score}")

    for result in summary.team_results:
        print(f"{result.team_id}: {result.evaluation_score}")

asyncio.run(main())
```

### 3. 複数ラウンド実行（新機能）

Round Controllerは自動的に複数ラウンドを実行します：

```python
# オーケストレータの呼び出しは既存と同じ
summary = await orchestrator.execute(
    user_prompt="データ分析タスク",
    timeout_seconds=600,
)

# 各チームは最大5ラウンド（設定可能）を実行
# - ラウンド1: 初回Submission
# - ラウンド2以降: 過去のSubmission履歴、評価フィードバック、ランキング情報を統合したプロンプトで改善
# - 最小ラウンド数（デフォルト: 2）に達するまでLLM判定なし
# - 最小ラウンド数到達後、LLMによる改善見込み判定を実行
# - 最大ラウンド数到達または改善見込みなしで終了

# 最終結果はOrchestratorが返す
print(f"Best Team: {summary.best_team_id}")
print(f"Best Score: {summary.best_score:.2f}")  # 0-100スケール

# 各チームの最高スコアSubmission（LeaderBoardEntry）を確認
for entry in summary.team_results:
    print(f"Team: {entry.team_name} (Round {entry.round_number})")
    print(f"  Score: {entry.score:.2f}")
    print(f"  Exit Reason: {entry.exit_reason}")
    print(f"  Final Submission: {entry.final_submission}")
```

---

## DuckDBデータ確認

### round_statusテーブル

各ラウンドのステータスを確認：

```sql
SELECT
    execution_id,
    team_id,
    team_name,
    round_number,
    should_continue,
    reasoning,
    confidence_score,
    round_started_at,
    round_ended_at
FROM round_status
WHERE execution_id = '<execution_id>'
ORDER BY team_id, round_number;
```

### leader_boardテーブル

各ラウンドの評価結果を確認：

```sql
SELECT
    execution_id,
    team_id,
    team_name,
    round_number,
    score,
    final_submission,
    exit_reason,
    created_at
FROM leader_board
WHERE execution_id = '<execution_id>'
ORDER BY score DESC, round_number DESC;
```

ランキングを取得：

```sql
SELECT
    team_id,
    team_name,
    MAX(score) AS max_score,
    COUNT(*) AS total_rounds
FROM leader_board
WHERE execution_id = '<execution_id>'
GROUP BY team_id, team_name
ORDER BY max_score DESC;
```

---

## テスト実行

### ユニットテスト

```bash
# Round Controllerのユニットテスト
pytest tests/unit/round_controller/ -v

# 改善見込み判定のテスト
pytest tests/unit/round_controller/test_improvement_judgment.py -v

# DuckDB統合テスト
pytest tests/unit/storage/test_aggregation_store.py -v
```

### 統合テスト

```bash
# オーケストレータE2Eテスト
pytest tests/integration/test_orchestrator_e2e.py -v
```

---

## トラブルシューティング

### 問題: `round_status`テーブルが見つからない

**解決方法**: DuckDBスキーマを初期化してください：

```bash
duckdb $MIXSEEK_WORKSPACE/mixseek.db < specs/012-round-controller/contracts/schema.sql
```

### 問題: スコアが0-1スケールで保存されている

**解決方法**: 本仕様では0-100スケールを使用します。既存のデータがある場合、マイグレーションスクリプトで変換してください：

```sql
UPDATE leader_board SET score = score * 100 WHERE score <= 1.0;
```

### 問題: LLM改善見込み判定がタイムアウトする

**解決方法**: `judgment_timeout_seconds`を増やしてください：

```toml
[orchestrator]
judgment_timeout_seconds = 120  # デフォルト: 60秒
```

### 問題: DuckDB書き込み競合エラー

**解決方法**: 既存実装のリトライロジック（3回、エクスポネンシャルバックオフ）が自動的に再試行します。全リトライ失敗時はチーム全体が失格となります。ログを確認してください。

---

## 次のステップ

1. **カスタム評価基準の設定**: チーム設定TOMLで評価基準をカスタマイズ
2. **複数チーム並列実行**: オーケストレータ設定TOMLで複数チームを追加
3. **ランキング可視化**: DuckDBデータをStreamlit UIで可視化（Feature 076-ui）

---

## 参考資料

- **機能仕様書**: `specs/012-round-controller/spec.md`
- **実装計画**: `specs/012-round-controller/plan.md`
- **データモデル**: `specs/012-round-controller/data-model.md`
- **リサーチ**: `specs/012-round-controller/research.md`
- **DuckDBスキーマ**: `specs/012-round-controller/contracts/schema.sql`
- **親仕様**: `specs/001-specs/spec.md`
- **憲章**: `.specify/memory/constitution.md`
