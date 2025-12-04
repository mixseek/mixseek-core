- あなたの思考過程、設計書等のすべてのアウトプットを日本語で記述すること
- `025-mixseek-core-orchestration` のspecは実装済みである。この実装の内容を深く理解し、実装済みの `Round Controller` を本FEATRUEのspecに従って置き換えること 
    - @src/mixseek/orchestrator
    - @src/mixseek/round_controller
- 本仕様で必要な変更以外はロジックを極力変更しないこと
- 本仕様で必要な変更は必ず網羅すること
- 既存のテストを用いて、既存実装で想定されている挙動を保証すること
- 既存のテストに加えて、本仕様で追加された要件を検証するためのテストを追加すること
- 既存実装ではスコアは0-1スケールだが、本仕様の定義通りEvaluatorが返した0-100スケールをそのまま使用すること
- `OrchestratorTask` に新たに与えられるラウンドの設定は、オーケストレータ設定のtomlで設定可能にし、設定されない場合はデフォルト値を採用すること

---

## context

- without slash command
- keep session

## prompt

data_model.mdで既存のRoundResultが返る設計をそのまま使っていますが、複数ラウンドでの最もよい結果を返す仕様がspecに明記されています。最もよかったラウンドのLeaderBoardEntryをOrchestratorに返すのが良いと思うのですが、どうですか？