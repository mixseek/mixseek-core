---
description: similarity-pyを使った重複コード検出とチーム共有可能なリファクタリング分析レポート生成
---

## User Input

```text
$ARGUMENTS
```

出力ファイルパスやスキャンオプションを指定できます。未指定の場合は`plans/duplication-analysis-[日付].md`に保存されます。

## Goal

similarity-pyを使用してコードベースの重複を検出し、優先度付けされたリファクタリング提案を含むMarkdownレポートを生成します。憲法Article 10（DRY原則）、Article 11（リファクタリングポリシー）に基づいて分析し、チームで共有可能な形式で保存します。

## Operating Constraints

**READ-ONLY SCAN + REPORT WRITE**: similarity-pyでスキャンしてレポートを生成しますが、ソースコード自体は変更しません。

**Constitution Authority**: 憲法Article 3（Test-First）、Article 8（Code Quality）、Article 9（Data Accuracy）、Article 10（DRY）、Article 11（Refactoring Policy）を厳守します。

**Prerequisites**: similarity-pyがインストール済みであることを前提とします（`cargo install similarity-py`）。

## Execution Steps

### 1. 引数のパース

`$ARGUMENTS`から以下を抽出：

**出力ファイルパス**:
- 第1引数が`.md`で終わる場合、それを出力パスとして使用
- 未指定または非`.md`の場合: `plans/duplication-analysis-YYYY-MM-DD.md`（現在日付を使用）

**スキャンオプション**:
- `--path <path>`: スキャン対象パス（デフォルト: `src/mixseek`）
- `--threshold <float>`: 類似度閾値（デフォルト: 0.85）
- `--min-lines <int>`: 最小行数（デフォルト: 15）

**引数例のパース結果**:
```bash
# 例1: /refactor-scan
# → 出力: plans/duplication-analysis-2025-01-15.md, デフォルトスキャン

# 例2: /refactor-scan docs/my-report.md
# → 出力: docs/my-report.md, デフォルトスキャン

# 例3: /refactor-scan custom.md --path src/mixseek/agents --threshold 0.90
# → 出力: custom.md, スキャン: src/mixseek/agents, 閾値: 0.90

# 例4: /refactor-scan --path src/mixseek/orchestrator
# → 出力: plans/duplication-analysis-2025-01-15.md, スキャン: src/mixseek/orchestrator
```

### 2. 出力ディレクトリの確保

出力パスのディレクトリが存在しない場合は作成：

```bash
mkdir -p "$(dirname [出力パス])"
```

### 3. similarity-pyスキャン実行

以下のスキャンを実行（`--path`指定がある場合はそのパスのみ）：

**デフォルトスキャン**（`--path`未指定時）:

```bash
# 全体スキャン（高閾値）
similarity-py src/mixseek --threshold 0.85 --min-lines 15 --cross-file --print

# Member Agents詳細スキャン
similarity-py src/mixseek/agents/member --threshold 0.80 --min-lines 10 --print

# CLI Commands詳細スキャン
similarity-py src/mixseek/cli/commands --threshold 0.75 --min-lines 15 --print

# UI Services詳細スキャン
similarity-py src/mixseek/ui/services --threshold 0.80 --min-lines 8 --print
```

**カスタムスキャン**（`--path`指定時）:

```bash
similarity-py [指定パス] --threshold [閾値] --min-lines [最小行数] --cross-file --print
```

各スキャン結果から以下を抽出：
- 類似度スコア（0.0-1.0）
- 重複箇所のファイルパスと行番号
- 重複行数
- コードスニペット（`--print`フラグの出力）

### 4. 優先度判定

検出された重複に対して以下の基準で優先度を判定：

| 優先度 | 類似度 | 重複行数 | 影響範囲 | Article 10違反度 |
|-------|--------|----------|---------|-----------------|
| **P0** | >90% | >100行 | クロスモジュール | CRITICAL |
| **P1** | >85% | >50行 | 同一モジュール内 | HIGH |
| **P2** | >80% | >30行 | 同一ファイル内 | MEDIUM |
| **P3** | >75% | >15行 | 局所的 | LOW |

### 5. デザインパターン提案

各重複箇所に対して、コード構造から適用可能なパターンを推定：

- **Template Method**: メソッド名が類似し、制御フローが同じ場合
- **Strategy**: 同じ目的で異なるアルゴリズム実装がある場合
- **Factory**: オブジェクト生成ロジックの重複
- **共通関数抽出**: 単純な関数/メソッドの重複
- **基底クラス拡張**: 継承階層での共通実装

### 6. 憲法準拠性チェック

各重複について以下をチェック：

- **Article 10（DRY原則）**: 重複の存在自体が違反
- **Article 11（Refactoring Policy）**: V2クラス作成の必要性（禁止事項）vs 既存コード直接修正可能性
- **Article 3（Test-First）**: `tests/`以下に対応するテストファイルが存在するか
- **Article 9（Data Accuracy）**: 重複コード内にハードコーディングや暗黙的デフォルトが含まれているか
- **Article 8（Code Quality）**: リファクタリング後のruff/mypy準拠性への影響

### 7. Markdownレポート生成

以下の構造でレポートを生成：

```markdown
# Code Duplication Analysis Report

**Generated**: [実行日時（ISO 8601形式）]
**Scanned Paths**: [スキャンしたパス一覧]
**Threshold**: [使用した類似度閾値]
**Min Lines**: [最小行数]
**Tool**: similarity-py

---

## Executive Summary

- **Total Duplications Found**: [件数]
- **Total Duplicate Lines**: [推定行数]
- **Estimated Code Reduction Potential**: [削減可能行数]
- **Priority Distribution**:
  - P0 (Critical): [件数] - [行数]
  - P1 (High): [件数] - [行数]
  - P2 (Medium): [件数] - [行数]
  - P3 (Low): [件数] - [行数]

---

## Priority Findings

### P0: Critical Duplications

[P0の重複がない場合は「None found.」と表示]

[各P0重複について以下のテンプレートで記載]

#### P0-[番号]: [簡潔なタイトル]

**Metrics**:
- **Similarity Score**: [XX]%
- **Duplicate Lines**: [行数]
- **Files Affected**: [ファイル数]

**Location**:
- `[ファイルパス1]:[開始行]-[終了行]`
- `[ファイルパス2]:[開始行]-[終了行]`
- ...

**Common Pattern**:
[共通するロジック/処理の箇条書き]

**Differences**:
[差異の箇条書き]

**Suggested Refactoring Pattern**: [Template Method / Strategy / Factory / 共通関数抽出 / 基底クラス拡張]

**Refactoring Proposal**:
```python
# [提案されるコード例]
```

**Constitution Compliance**:
- **Article 10 (DRY)**: ❌ VIOLATION - [理由]
- **Article 11 (Refactoring)**: [✅ 既存コード修正可能 / ⚠️ 要検討]
- **Article 3 (Test-First)**: [✅ テスト存在 / ⚠️ テスト不足]
- **Article 9 (Data Accuracy)**: [✅ 問題なし / ⚠️ ハードコーディング検出]
- **Article 8 (Code Quality)**: [リファクタリング後の品質影響評価]

**Estimated Impact**:
- Lines reduced: ~[削減行数] lines
- Maintainability: [HIGH / MEDIUM / LOW] improvement
- Test impact: [Minimal / Moderate / Significant]
- Complexity reduction: [評価]

---

### P1: High Priority Duplications

[P0と同様の構造で記載]

---

### P2: Medium Priority Duplications

[P0と同様の構造で記載、ただし詳細度は低め]

---

### P3: Low Priority Duplications

[件数と概要のみ、詳細は省略]

---

## Constitution Alignment Summary

| Article | Status | Issues Found | Recommendation |
|---------|--------|--------------|----------------|
| Article 10 (DRY) | [✅ / ⚠️ / ❌] | [件数] duplications ([行数] lines) | [推奨アクション] |
| Article 11 (Refactoring) | [✅ / ⚠️] | [評価] | [推奨アクション] |
| Article 3 (Test-First) | [✅ / ⚠️] | [評価] | [推奨アクション] |
| Article 9 (Data Accuracy) | [✅ / ⚠️] | [件数] hardcoded values | [推奨アクション] |
| Article 8 (Code Quality) | [✅ / ⚠️] | [評価] | [推奨アクション] |

---

## Refactoring Roadmap

### Immediate Actions (Week 1)

[P0項目について]
1. **P0-[番号]: [タイトル]**
   - Estimated effort: [時間]
   - Prerequisites: [事前条件]
   - Implementation: [実装方針]
   - Validation: [検証方法]

### Short-term Actions (Week 2-3)

[P1項目について]

### Medium-term Actions (Month 1)

[P2項目について]

### Low Priority (Backlog)

[P3項目について - 簡潔に]

---

## Metrics

- **Total Files Scanned**: [ファイル数]
- **Duplication Percentage**: [重複率]%
- **Potential Code Reduction**: ~[行数] lines ([全体の%]% of scanned code)
- **Affected Modules**:
  [モジュールごとの重複行数リスト]

---

## Next Steps

### Option 1: 即座にP0リファクタリング実行

最優先度の重複に対して、以下の手順で実装：

1. 既存テストの確認（`pytest tests/[対象モジュール]/ -v`）
2. リファクタリング設計の承認取得（Article 3準拠）
3. Template Method/Strategy等のパターン適用
4. 段階的な実装（1ファイルずつ移行）
5. 各ステップでテスト実行
6. 品質チェック（`ruff check --fix . && ruff format . && mypy .`）

### Option 2: チームレビュー後に優先度調整

このレポートをチームで共有し、ビジネス優先度と技術的負債のバランスを考慮して実装計画を調整。

### Option 3: モニタリングのみ（CI/CD統合）

新規重複の発生を監視するため、CI/CDパイプラインに`similarity-py`チェックを統合：

```yaml
# .github/workflows/code-quality.yml 例
name: Code Quality Check
on: [push, pull_request]
jobs:
  duplication-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install similarity-py
        run: cargo install similarity-py
      - name: Check duplications
        run: similarity-py src/mixseek --threshold 0.85 --min-lines 15
```

---

## How to Share This Report

### GitHub Issue Creation

以下のコマンドでGitHub Issueを作成：

```bash
gh issue create \
  --title "[Refactoring] Code Duplication Analysis - $(date +%Y-%m-%d)" \
  --label "refactoring,technical-debt,priority:high" \
  --body-file [このレポートのパス]
```

### Slack/Discord Notification

以下のメッセージをチームチャネルに投稿：

```
📊 Code Duplication Analysis完了

- 重複検出: [件数]件
- 削減可能行数: ~[行数]行
- P0対応: [件数]件

詳細: [レポートURL or GitHub Issue URL]
```

---

## Appendix: Raw similarity-py Output

<details>
<summary>全体スキャン結果（クリックで展開）</summary>

```
[similarity-pyの生出力]
```

</details>

<details>
<summary>Member Agentsスキャン結果</summary>

```
[similarity-pyの生出力]
```

</details>

<details>
<summary>CLI Commandsスキャン結果</summary>

```
[similarity-pyの生出力]
```

</details>

<details>
<summary>UI Servicesスキャン結果</summary>

```
[similarity-pyの生出力]
```

</details>

---

**Report Version**: 1.0
**Generated by**: Claude Code `/refactor-scan` command
**Constitution Version**: [.specify/memory/constitution.mdのバージョン]
```

### 8. レポートファイルの保存

Writeツールを使用して、指定されたパス（または`plans/duplication-analysis-YYYY-MM-DD.md`）に上記のMarkdownレポートを保存します。

保存後、ユーザーに以下を報告：

```
✅ 重複コード分析完了

📄 レポート: [保存先パス]
📊 検出件数: [件数]
🎯 P0対応: [件数]件
📉 削減可能行数: ~[行数]行

次のアクション:
1. レポートをレビュー: cat [保存先パス]
2. GitHub Issue作成: gh issue create --body-file [保存先パス]
3. P0リファクタリング実行: [具体的な提案]
```

## Operating Principles

### Token Efficiency

- **Minimal context loading**: similarity-pyの出力のみを処理、全ソースコードは読み込まない
- **Progressive disclosure**: P0→P1→P2→P3の順で詳細度を段階的に低下
- **Aggregation**: 50件以上の重複がある場合は上位30件に集約し、残りはサマリー表示

### Analysis Guidelines

- **NEVER modify source code**: レポート生成のみ（ソースコードは変更しない）
- **NEVER hallucinate metrics**: similarity-pyの実測値のみ使用（推測値は明示）
- **Prioritize actionability**: 具体的で実装可能なリファクタリング提案を含める
- **Use examples**: 理論ではなく実際のコードスニペットを引用
- **Constitution-first**: 憲法違反は自動的にCRITICAL判定

### Quality Standards

- **Article 8 Compliance**: 生成されたレポートもMarkdownとして高品質
- **Article 9 Compliance**: ハードコーディングされた閾値は引数でオーバーライド可能
- **Article 16 Compliance**: レポート内のコード例は型注釈を含む

### Error Handling

- similarity-pyがインストールされていない場合: インストール方法を提示して終了
- スキャン対象パスが存在しない場合: エラーメッセージと有効なパス例を表示
- 重複が1件も検出されなかった場合: 成功レポートを生成（"No duplications found"）

## Context

$ARGUMENTS
