# パターンA 実行プロンプト — Opus 4.8 / 単発（非ワークフロー）

## 事前準備（人間が実施）

1. モデルを **Opus 4.8** にする（`/model` で `claude-opus-4-8`）。
2. ベースから専用ブランチを作成:
   ```bash
   git checkout experiment/refactor-planning-compare
   git checkout -b experiment/refactor-plan-a-opus48
   ```
3. 以下「投入プロンプト」を新規セッションにそのまま貼り付ける。

---

## 投入プロンプト（ここから下をコピー）

まず `refactor-plans/prompts/_shared-brief.md` を読み、その指示に従ってください。

**実行条件（パターンA）:**
- あなたは **単独で** 作業します。**サブエージェント（Agent ツール）もワークフロー（Workflow ツール）も使用禁止**です。
  自分自身でコードを読み、自分で計画を書いてください。
- 出力先ディレクトリは `refactor-plans/outputs/a-opus48/` です。このディレクトリ配下にのみ成果物を作成してください。
- 他パターンの出力（`refactor-plans/outputs/b-*`, `c-*`）は参照しないでください。
- コードは変更しないでください（読み取りと計画ドキュメント生成のみ）。

共通ブリーフの「成果物」に従い、`refactor-plans/outputs/a-opus48/README.md`
（計画ドキュメント群を読むためのインデックス＋優先度サマリ表）を必須とし、それ以外のファイル構成は任意です。
完了したら、作成したファイル一覧と概観を報告してください。
