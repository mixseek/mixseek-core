# リファクタリング計画 — モデル/ワークフロー比較実験

## 1. 趣旨

mixseek-core は約半年前の Claude Code（旧モデル）で開発された。モデルおよび Claude Code の
内部ツール（サブエージェント / ワークフロー機能）が進化したため、現行コードをリファクタリングするにあたり、
**「どのモデル・どの実行形態で計画を立てるのが最良か」** を比較検証する。

本実験では実装は行わず、**優先度付きリファクタリング計画の作成**までを対象とする。
3パターンそれぞれに同一のブリーフを渡し、生成された計画ファイル群を後から横並びで比較する。

## 2. 比較する3パターン

| ID | モデル | 実行形態 | 検証する軸 |
|----|--------|----------|------------|
| A  | Opus 4.8 | 単発（非ワークフロー） | 基準。B との差 = 純粋なモデル差 |
| B  | Fable 5  | 単発（非ワークフロー） | A との差＝モデル差 / C との差＝オーケストレーション差 |
| C  | Fable 5  | ワークフロー（並列ファンアウト） | 並列オーケストレーションの効果 |

- **A ↔ B** … モデル差（Opus 4.8 vs Fable 5）を分離
- **B ↔ C** … 実行形態差（単発 vs ワークフロー）を分離

## 3. 隔離方針（重要）

並列実行すると、先に出力された計画 `.md` を実行中の別 LLM が参照してしまい比較が汚染される。
これを防ぐため **各パターンは個別ブランチ・個別セッションで実行する**。

- ベースブランチ: `experiment/refactor-planning-compare`（develop から作成。本足場一式を保持）
- 各パターンはベースブランチから自分のブランチを切って実行する:

| ID | ブランチ | 出力ディレクトリ |
|----|----------|------------------|
| A  | `experiment/refactor-plan-a-opus48`  | `refactor-plans/outputs/a-opus48/` |
| B  | `experiment/refactor-plan-b-fable5`  | `refactor-plans/outputs/b-fable5/` |
| C  | `experiment/refactor-plan-c-fable5-wf` | `refactor-plans/outputs/c-fable5-wf/` |

各パターンは **自分の出力ディレクトリ配下のみ** に成果物を生成する。他パターンの outputs は参照しない。
ベースブランチには outputs の実体を置かない（各パターンブランチでのみ生成される）。

## 4. 実行手順

各パターンごとに、クリーンな新規セッションで以下を行う。

```bash
# ベースブランチを最新化してからパターン用ブランチを作成（例: A）
git checkout experiment/refactor-planning-compare
git checkout -b experiment/refactor-plan-a-opus48
```

その後、対応するプロンプトファイルの内容を新規セッションに投入する:

- A: `refactor-plans/prompts/a-opus48.md`
- B: `refactor-plans/prompts/b-fable5.md`
- C: `refactor-plans/prompts/c-fable5-workflow.md`

各プロンプトは共通ブリーフ `refactor-plans/prompts/_shared-brief.md` を参照する。

> モデル切替: A は Opus 4.8、B / C は `/model` で Fable 5（`claude-fable-5`）へ切り替えてから実行する。

## 5. 成果物の形式

計画は単一ファイルに限らない。各パターンは自分の出力ディレクトリ配下に複数ファイルで出力してよい。
ファイル構成は任意だが、**`README.md`（計画ドキュメント群を読むためのインデックス＋優先度サマリ表）を必須**とする。
詳細は共通ブリーフを参照。

## 6. 比較（足場側の最後の作業）

3パターンの実行完了後、ベースブランチに各 outputs を集約し、`refactor-plans/comparison.md` で
以下の軸を横並び比較する:

- 検出したリファクタ候補の数・粒度・網羅性
- 優先順位付け（影響度×リスク評価）の妥当性
- 自己ルール（AGENTS.md）違反の捕捉率
- 計画の具体性・実行可能性
- 所要時間・トークンコスト（参考）
