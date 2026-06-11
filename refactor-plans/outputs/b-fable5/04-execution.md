# 実行フロー（orchestrator / round_controller / evaluator）の計画（E1〜E3）

コンペティション実行の中核3モジュール。いずれも300行超だが、設計自体は
Strategy パターン（round_controller）や部分失敗リカバリ（orchestrator）など考えられており、
問題は「長い手続き関数」と「本筋でない責務の同居」に絞られる。

## 責務と依存（現状把握）

- `orchestrator/orchestrator.py`（530行）… 複数チームの並列実行・タイムアウト・部分失敗処理・
  進捗ファイル書き出し。round_controller へは循環回避の遅延 import
- `round_controller/controller.py`（567行）… 1チームのラウンドループ。`strategy.py`
  （Leader/Workflow 戦略）・`judgment_client.py`・進捗ファイル書き出し
- `evaluator/evaluator.py`（531行）… メトリクス実行と総合スコア計算＋
  カスタムメトリクスの動的ロード。`metrics/`（base 305行＋具象4種、各60〜70行）

テスト被覆: orchestrator 15・round_controller 15・evaluator 22ファイル。
`tests/integration/test_orchestrator_e2e.py`・`tests/evaluator/`（unit/integration/e2e/performance
の4層）と厚く、安全網は良好。

---

## E1: `Orchestrator._execute_impl`（203行）のフェーズ分割

- **対象**: `src/mixseek/orchestrator/orchestrator.py:177-379`
- **影響度: 中 / リスク: 低 / 工数: S**

### 問題（分析観点: 自己ルール違反）

**リポジトリ唯一の「1関数200行」規約違反**（203行）。実体は明確に直列の6フェーズ:
設定ロード → auth デバッグログ → team_id 重複チェック＆TeamStatus 初期化 →
Evaluator/Judgment/PromptBuilder 設定取得 → RoundController 生成・並列実行 →
結果収集・サマリ構築。

### 推奨アプローチ

フェーズ境界がコメントで既に示されているため、そのままプライベートメソッドへ機械的に抽出する:

```python
async def _execute_impl(self, task, timeout, span=None) -> ExecutionSummary:
    units = self._load_unit_settings(task)          # ロード＋重複チェック＋status初期化
    shared = self._load_shared_settings()            # evaluator/judgment/prompt_builder
    results = await self._run_all_teams(task, units, shared, timeout)
    return self._collect_results(task, results, span)
```

auth デバッグログ（`orchestrator.py:208-222`）は try/except で握りつぶす純粋な診断コードなので
`_log_auth_diagnostics(units)` に隔離する。挙動変更なし・530行 → 規約内が完了条件。

### 関連テスト（安全網）

`tests/unit/orchestrator/`＋`test_orchestrator_e2e.py`。部分失敗系
（`PartialTeamFailureError` の分岐）のテスト有無を着手時に確認し、なければ
`_collect_results` 抽出と同時にユニットテストを足す（抽出後はモック注入が容易になる）。

---

## E2: RoundController のラウンド実行・継続判定の分割

- **対象**: `src/mixseek/round_controller/controller.py`（567行）
- **影響度: 中 / リスク: 低 / 工数: S**

### 問題（分析観点: 肥大化・責務）

- `_execute_single_round`（138行）が Strategy 実行・進捗ファイル更新（4回）・履歴保存・
  Evaluator 実行・score_details 構築・リーダーボード保存を直列に抱える
- `_should_continue_round`（92行）はラウンド継続判定（最大ラウンド・スコア閾値・
  Judgment 呼び出し）の複合条件
- 進捗ファイル書き出し（`_write_progress_file` 50行）は UI との連携用 I/O であり、
  ラウンド制御の本筋と毛色が異なる

### 推奨アプローチ

1. `_execute_single_round` を「実行（strategy）」「評価（evaluator 呼び出し＋
   score_details 構築）」「永続化（store 2回の保存）」の3メソッドに分ける。
   進捗ファイル更新はフック的に挟まる横断処理なので、`ProgressReporter` 的な小クラス
   （`round_controller/progress.py`）へ抽出すると orchestrator 側の
   `_write_error_to_progress_file` とも共通化できる（進捗ファイルのスキーマが
   `ui/services/execution_service.py:_read_progress_from_file` と暗黙に結合している点に注意。
   E2 実施時に進捗ファイル形式を dataclass/pydantic モデルとして1箇所に定義し、
   読み書き双方をそれ経由にすると、この暗黙結合も解消できる）。
2. `_should_continue_round` は判定理由を enum（`StopReason`）で返す純粋関数群に分解すると、
   テストが書きやすくなりログも構造化しやすい。
3. 567行 → 400行前後＋progress.py を見込む。300行未満には judgment_client 連携部の
   さらなる抽出が必要だが、第一段階では関数粒度の改善を優先する。

### 関連テスト（安全網）

`tests/unit/round_controller/`・`tests/integration/test_workflow_round_controller.py`。
継続判定は境界値（閾値ちょうど・最大ラウンド）のテストが重要なので、分解と同時に
パラメタライズドテストへ整理する。

---

## E3: カスタムメトリクスローダーの分離

- **対象**: `src/mixseek/evaluator/evaluator.py`（531行）
- **影響度: 中 / リスク: 低 / 工数: M**

### 問題（分析観点: 責務・肥大化）

`Evaluator` クラス（446行）のうち約170行が「カスタムメトリクスの動的ロード」
（`register_custom_metric` 47行・`_load_custom_metrics_from_config` 60行・
`_load_metric_from_directory` 61行）。動的 import・ファイル探索・クラス検証という
プラグインローダーの責務で、評価実行（`evaluate` 113行・`_calculate_overall_score`）とは
独立している。同種の動的ロード機構は `agents/member/dynamic_loader.py` と
`workflow/executable.py:_load_module_from_path`（39行）にも存在し、**3箇所目の再実装**。

### 推奨アプローチ

1. `evaluator/metric_loader.py` を新設し、ロード系3メソッドを移す。`Evaluator.__init__` は
   ローダーが返す `dict[str, type[BaseMetric]]` を受け取るだけにする。
2. 余力があれば、`utils/plugin_loader.py` として「パス/モジュール名から指定基底クラスの
   サブクラスをロードして検証する」共通機構に
   `agents/member/dynamic_loader.py`・`workflow/executable.py:_load_module_from_path` を
   合流させる（DRY）。ただし3者でエラーメッセージ・検証規則が異なるため、
   第一段階は evaluator 内の分離に留め、共通化は別 PR とする。
3. あわせて `evaluate`（113行）はメトリクス並列実行と結果集約の2段に割ると規約内に収まる。

### 関連テスト（安全網）

`tests/evaluator/unit/`（カスタムメトリクス登録のテストあり）・
`tests/unit/test_dynamic_loader.py`（member 側）。ローダー分離後は
「不正なメトリクスクラスを弾く」検証テストをローダー単体で書けるようになる。

---

## 補足: 実行フローで「やらなくてよい」こと

- `round_controller/strategy.py`・`judgment_client.py`・`workflow/engine.py`（207行）は
  規約内で責務も明確。`workflow/executable.py`（393行）は E3 の共通ローダー化の際に
  `_load_module_from_path`/`_load_function` が抜ければ規約内に収まるため、単独では扱わない。
- `evaluator/metrics/base.py`（305行）は LLM メトリクス基底として僅かに超過しているが、
  `evaluate`（108行）はプロンプト構築・LLM 呼び出し・パースの直列で可読性は保たれている。
  M2 の `to_model_settings()` 共通化で自然に縮む見込みのため、独立候補とはしない。
