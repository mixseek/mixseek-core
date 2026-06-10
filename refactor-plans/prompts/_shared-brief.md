# 共通ブリーフ — リファクタリング計画作成

> このファイルは3パターン（A/B/C）共通の指示。各パターン固有の指示は各プロンプトファイル側に記載。
> パターン間で条件を揃えるため、ここに書かれた内容は**改変せずそのまま**従うこと。

## タスク

mixseek-core リポジトリ全体を把握し、**優先度付きリファクタリング計画**を作成する。
**実装は一切行わない（コード変更禁止・読み取り専用）。計画ドキュメントの生成のみ。**

## プロジェクト概要

mixseek は LLM を活用したマルチエージェント・オーケストレーションフレームワーク。
リーダーエージェント＋複数メンバーエージェントで1チームを構成し、複数チームが単一タスクに
コンペティション形式で取り組む。各チームはラウンドごとに回答を提出 → Evaluator が評価・スコア化
→ リーダーボード掲載 → フィードバックを受けて次ラウンドで洗練、を繰り返す。

## 既知の現状（全パターン共通の出発点）

- `src/` : 159 ファイル / 約 25,500 行、`tests/` : 180 ファイル（テスト資産は厚い）
- Python 3.13.7 / ruff / mypy(pydantic plugin) / pydantic
- **300 行超のファイルが 20 個**存在（AGENTS.md の自己ルール違反）。主なもの:
  - `src/mixseek/config/schema.py` 1,641 行
  - `src/mixseek/storage/aggregation_store.py` 907 行
  - `src/mixseek/config/manager.py` 887 行
  - `src/mixseek/models/evaluation_config.py` 875 行
  - `src/mixseek/config/views.py` 819 行
  - `src/mixseek/ui/services/execution_service.py` 772 行
  - 他（framework/integration_hooks, core/auth, round_controller/controller,
    evaluator/evaluator, orchestrator/orchestrator 等）

## 主なサブシステム

`config`(schema/manager/views/validation/各種loader) ・ `evaluator`(evaluator/llm_client/metrics) ・
`orchestrator` ・ `round_controller` ・ `framework`(integration_hooks) ・ `core`(auth/model_settings) ・
`storage`(aggregation_store) ・ `cli`(commands/formatters/utils) ・ `ui`(app/services) ・
`models` ・ `workflow` ・ `observability` / `utils`

## 分析観点

各サブシステムについて以下を評価する:

1. **責務と依存** … 何を担い、どこに依存し、何を公開しているか
2. **設計上の臭い** … 肥大化 / 重複（DRY違反）/ 密結合 / 古いパターン（Python 3.13 で簡潔化できる箇所）
3. **自己ルール（AGENTS.md）違反** … 1ファイル300行・1関数200行超 / `os.getenv` 直接呼び出し
   （共通 config モジュール経由が規約）/ 共通ロガー未使用 / 構造化JSONログ未使用
4. **エラー処理・型** … 例外設計の一貫性、型注釈の網羅性
5. **テスト被覆の所感** … 対応するテストの有無・厚み（リファクタ時の安全網として）

## 成果物（出力形式）

自分の出力ディレクトリ（各プロンプトで指定）配下に Markdown ファイルで出力する。
ファイル構成（分割の仕方・命名）は任意だが、以下を満たすこと。

- **必須**: `README.md` … 生成した計画ドキュメント群を読むための**インデックス**。
  各ファイルへのリンクと概要を載せる。さらに、全リファクタ候補を優先度順に並べた**サマリ表**
  （列: 候補 / 対象 / 影響度[高中低] / リスク[高中低] / 推奨着手順）を README.md 内または別ファイルに必ず含める。
- **詳細**: 候補ごと、またはサブシステムごとにファイルを作成し、各候補に以下を記載:
  - 対象（ファイル/モジュール）
  - 問題（上記分析観点のどれに該当するか具体的に）
  - 影響度 / リスク
  - 推奨アプローチ（どう分割・再設計するか）
  - 関連テスト（安全網の有無）
  - 工数感（ざっくり: S/M/L）

## 制約

- **コード変更禁止**。計画ドキュメントのみ生成。
- 出力・記述は **日本語**（開発者の共通語）。
- 自分の出力ディレクトリ以外（他パターンの outputs 等）は**参照しない・書き込まない**。
- Markdown は1行120文字未満を目安、1ファイル500行未満を目安とする。
