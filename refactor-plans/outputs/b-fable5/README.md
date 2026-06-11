# mixseek-core リファクタリング計画（パターンB: Fable 5 単独）

リポジトリ全体（`src/` 159ファイル・約25,500行）を読み取り調査して作成した、優先度付きリファクタリング計画。
実装は行わず、計画ドキュメントのみを提供する。

## ドキュメント構成

| ファイル | 内容 |
| --- | --- |
| [01-config.md](01-config.md) | config 層（schema/manager/views）の分割・重複排除（C1〜C3） |
| [02-models-unification.md](02-models-unification.md) | 新旧二重設定モデルの統一と LLM パラメータ共通化（M1〜M3） |
| [03-storage.md](03-storage.md) | `aggregation_store.py` の sync/async 重複とリトライ統一（S1〜S2） |
| [04-execution.md](04-execution.md) | orchestrator / round_controller / evaluator の実行フロー整理（E1〜E3） |
| [05-ui-cli-observability.md](05-ui-cli-observability.md) | UI サービス分割・観測性初期化の一本化・CLI 整理（U1〜U4） |
| [06-cross-cutting.md](06-cross-cutting.md) | 横断課題: デッドコード・`os.getenv` 集約・例外階層・モダナイズ（X1〜X4） |

## 全体診断サマリ

調査で確認した主要な事実（詳細は各ドキュメント）:

1. **新旧二重設定モデルが最大の構造課題**。`config/schema.py` の Settings 群（新）と
   `models/` `agents/leader/config.py` の Config 群（旧）が並存し、3系統の変換関数
   （Evaluator / Team / MemberAgent）で橋渡ししている。875行の `evaluation_config.py` は
   ほぼ旧モデルの維持コスト。
2. **300行超ファイルは実測19個**（AGENTS.md の自己ルール違反）。ただし大半はクラス/関数境界が
   明確で、機械的な分割が可能。200行超の関数は `Orchestrator._execute_impl`（203行）の1件のみ。
3. **同型コードの繰り返しが多い**。`get_*_for_metric` 10連発、`manager.py` の
   `get_*_settings` 3×65行、`aggregation_store.py` の sync/async 7ペア、`auth.py` の
   provider 別 validate 3連発、`views.py` の text/JSON 並列フォーマッタなど、
   テーブル駆動・ヘルパー抽出で大幅に圧縮できる。
4. **`framework/integration_hooks.py`（576行）はほぼデッドコード**。本番呼び出しは
   `agents/member/factory.py` の1箇所のみ。
5. **`os.getenv` 直接呼び出しが約20ファイルに分散**（規約は共通 config モジュール経由）。
   特に logfire/logging 初期化が CLI・UI app・UI サービスの3箇所でコピーされている。
6. **テスト資産は厚く（180ファイル・約42,000行）、安全網は良好**。config 参照78ファイル、
   models 56、agents 39。手薄なのは storage（12）と ui（14）で、該当箇所のリファクタ時は
   テスト追加から始めるのが安全。

## 優先度サマリ表（全候補・推奨着手順）

影響度 = 改善が全体品質・開発速度に与える効果。リスク = 退行の起こりやすさ（テスト被覆と変更範囲から判断）。

| 順 | 候補 | 対象 | 影響度 | リスク | 工数 | 詳細 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | M3: `get_*_for_metric` 10メソッド統合 | `models/evaluation_config.py` | 中 | 低 | S | [02](02-models-unification.md) |
| 2 | C2: `get_*_settings` フォールバック共通化 | `config/manager.py` | 中 | 低 | S | [01](01-config.md) |
| 3 | E1: `_execute_impl`（203行）のフェーズ分割 | `orchestrator/orchestrator.py` | 中 | 低 | S | [04](04-execution.md) |
| 4 | X1: integration_hooks デッドコード削除 | `framework/` | 中 | 低 | S | [06](06-cross-cutting.md) |
| 5 | U4: `config_show`/`config_init` の分割 | `cli/commands/config.py` | 低 | 低 | S | [05](05-ui-cli-observability.md) |
| 6 | X4: Pydantic v1 残滓の除去 | `ui/models/*` | 低 | 低 | S | [06](06-cross-cutting.md) |
| 7 | M2: LLM パラメータ共通基底モデル導入 | `config/schema.py` ほか約10クラス | 高 | 低 | M | [02](02-models-unification.md) |
| 8 | C1: `schema.py`（1,641行）のモジュール分割 | `config/schema.py` | 高 | 低 | M | [01](01-config.md) |
| 9 | S1: sync/async ラッパーとリトライの統一 | `storage/aggregation_store.py` | 中 | 低 | M | [03](03-storage.md) |
| 10 | X3: 例外階層の統一（共通基底導入） | `exceptions.py` ほか各所 | 中 | 低 | S | [06](06-cross-cutting.md) |
| 11 | E2: ラウンド実行・継続判定の分割 | `round_controller/controller.py` | 中 | 低 | S | [04](04-execution.md) |
| 12 | C3: 設定ビューのデータ抽出/表示分離 | `config/views.py` | 中 | 低 | M | [01](01-config.md) |
| 13 | X2: `os.getenv` 直接呼び出しの集約 | `core/auth.py`・`cli/`・`ui/` ほか | 中 | 中 | M | [06](06-cross-cutting.md) |
| 14 | U2: 観測性初期化の一本化 | `cli/utils.py`・`ui/app.py` ほか | 高 | 中 | M | [05](05-ui-cli-observability.md) |
| 15 | E3: カスタムメトリクスローダーの分離 | `evaluator/evaluator.py` | 中 | 低 | M | [04](04-execution.md) |
| 16 | U1: `execution_service.py`（772行）の分割 | `ui/services/` | 中 | 中 | M | [05](05-ui-cli-observability.md) |
| 17 | S2: ストアのテーブル別リポジトリ化 | `storage/aggregation_store.py` | 中 | 中 | M | [03](03-storage.md) |
| 18 | M1: 新旧二重設定モデルの統一 | `models/` `agents/leader/config.py` ほか | 高 | 中 | L | [02](02-models-unification.md) |
| 19 | U3: CLI→UI の環境変数伝搬の明示化 | `cli/commands/ui.py`・`ui/app.py` | 中 | 高 | M | [05](05-ui-cli-observability.md) |

## 推奨ロードマップ（フェーズ分け）

依存関係と安全性を考慮した進め方。各フェーズ完了ごとに
`make -C dockerfiles/ci lint format-check type-check test-fast` を通す。

- **フェーズ0 — クイックウィン（順1〜6）**: 規約違反（200行超関数）の解消、明白な重複の統合、
  デッドコード削除。いずれも既存テストが厚く、半日〜1日単位で完了する独立タスク。
- **フェーズ1 — 構造整理（順7〜12）**: ファイル分割と共通化。公開 API（import パス）を
  `__init__.py` の再エクスポートで維持すれば外部影響なしに進められる。
  M2（共通基底モデル）は M1 の前提整備を兼ねるため、このフェーズで実施する。
- **フェーズ2 — 中リスク改善（順13〜17）**: 環境変数アクセスと観測性初期化の集約、
  UI サービス・ストアの再設計。動作確認に integration テスト実行が必要。
- **フェーズ3 — アーキテクチャ統一（順18〜19）**: 旧 Config モデル群の廃止と
  プロセス間設定伝搬の再設計。影響範囲が広いため、フェーズ0〜2で足場を固めてから着手する。

## 調査方法のメモ

- `wc -l` / AST 解析（クラス・関数の行数一覧）で規約違反を機械的に棚卸し
- `grep` で `os.getenv`・後方互換マーカー（`deprecated`/`後方互換`/`legacy`）・参照関係を追跡
- 主要19ファイル（300行超）の構造と、重複疑い箇所の本文を直接読んで確認
- テスト被覆はサブシステム別の参照テストファイル数とディレクトリ構成から所感を記載
