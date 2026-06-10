# outputs — 各パターンの成果物置き場

このディレクトリには各パターンが生成した計画ファイル群が入る。

| サブディレクトリ | パターン | 生成ブランチ |
|------------------|----------|--------------|
| `a-opus48/`   | A: Opus 4.8 / 単発     | `experiment/refactor-plan-a-opus48`   |
| `b-fable5/`   | B: Fable 5 / 単発      | `experiment/refactor-plan-b-fable5`   |
| `c-fable5-wf/`| C: Fable 5 / ワークフロー | `experiment/refactor-plan-c-fable5-wf` |

**注意:** 各サブディレクトリの実体は、それぞれのパターンブランチでのみ生成される。
ベースブランチ `experiment/refactor-planning-compare` にはこの README のみを置く。
比較フェーズで3ブランチの outputs をベースに集約し、`../comparison.md` を作成する。
