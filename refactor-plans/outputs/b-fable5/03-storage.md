# storage 層のリファクタリング計画（S1〜S2）

`storage/` は `aggregation_store.py`（907行・src 第2位）と `schema.py` の2ファイル構成。
DuckDB への永続化（round_history / leader_board / execution_summary / round_status）を
単一クラス `AggregationStore` が担う。

## 責務と依存（現状把握）

- 公開 API はすべて async。内部は「同期メソッド `_xxx_sync` を `asyncio.to_thread` で
  スレッドプール退避」というパターンで統一されている（方針自体は妥当）
- 利用側: round_controller（保存）・orchestrator（サマリ保存）・ui/services（読み出し）
- 例外はファイル内定義の `DatabaseWriteError` / `DatabaseReadError`（中央 `exceptions.py` 外。
  [06](06-cross-cutting.md) X3 参照）

テスト被覆: storage 参照テストは **12ファイルと相対的に手薄**。
`tests/unit/storage/`・`tests/integration/test_concurrent_writes.py`・`tests/database/test_schema.py`
があるが、リトライ挙動やテーブル別 CRUD の網羅は薄い。**リファクタ前にテスト追加を推奨**。

---

## S1: sync/async ペアの定型と リトライポリシーの統一

- **対象**: `src/mixseek/storage/aggregation_store.py`
- **影響度: 中 / リスク: 低 / 工数: M**

### 問題（分析観点: DRY 違反・エラー処理の一貫性）

1. **sync/async の7ペア**（`_save_sync`/`save_aggregation`、`_load_round_history_sync`/
   `load_round_history`、`_get_leader_board_sync`/`get_leader_board`、
   `_get_team_statistics_sync`/`get_team_statistics`、`_save_execution_summary_sync`/
   `save_execution_summary`、`_save_round_status_sync`/`save_round_status`、
   `_save_to_leader_board_sync`/`save_to_leader_board` ほか）で、async 側は
   「to_thread + 例外ラップ」の定型を毎回手書きし、**docstring も両側にほぼ同文で重複**
   （例: `save_execution_summary` は sync 52行＋async 52行）。
2. **リトライポリシーが不統一**: `save_aggregation` だけ手書きの指数バックオフ
   （`delays = [1, 2, 4]`、`aggregation_store.py:298-308`）を持ち、他の save 系は
   リトライなしで `DatabaseWriteError` に直ラップ。同時書き込み（複数チーム並列）は
   全 save 系で起こり得るため、この差に設計上の根拠が見えない。

### 推奨アプローチ

1. 共通ヘルパーを導入し、async 側を1〜3行に圧縮する:

   ```python
   async def _run_write(self, fn, /, *args, retries: int = 3) -> Any:
       """to_thread 退避＋指数バックオフ＋DatabaseWriteError ラップ"""

   async def _run_read(self, fn, /, *args) -> Any:
       """to_thread 退避＋DatabaseReadError ラップ"""
   ```

   リトライの要否・回数はメソッドごとの引数で明示し、「なぜこの操作はリトライしないか」を
   設計判断として一元化する。
2. docstring は async 公開側に集約し、`_xxx_sync` は1行要約のみとする。
3. ここまでで 907行 → 600行前後を見込む（S2 まで行えば各ファイル300行未満が射程）。

### 関連テスト（安全網）

`test_concurrent_writes.py` が並列書き込みを、`tests/unit/storage/` が基本 CRUD を被覆。
**先にリトライ挙動のユニットテストを追加する**（モック接続で N 回失敗→成功、
失敗継続→`DatabaseWriteError`）。現状この挙動を固定するテストが見当たらないため、
ヘルパー統一時の退行を検知できない。

---

## S2: テーブル別リポジトリへの分割

- **対象**: 同上（S1 完了後に実施）
- **影響度: 中 / リスク: 中 / 工数: M**

### 問題（分析観点: 肥大化・責務）

`AggregationStore` は4テーブル（round_history / leader_board / execution_summary /
round_status）の DDL（`_init_tables_sync` 103行）と CRUD をすべて抱え、
「集約ストア」という名前と実際の責務（実行状態・リーダーボード・サマリ全般）が乖離している。

### 推奨アプローチ

1. 接続管理・トランザクション・S1 のヘルパーを `storage/base.py`（`DuckDBStoreBase`）に抽出。
2. テーブル単位でリポジトリを分割する:
   - `round_history_store.py`（save_aggregation / load_round_history）
   - `leader_board_store.py`（save_to_leader_board / get_leader_board / ranking / statistics）
   - `execution_store.py`（execution_summary / round_status）
3. DDL は `storage/schema.py`（既存）に寄せ、`initialize_schema` を一括初期化の入口として維持。
4. 既存利用側（round_controller / orchestrator / ui）への影響を抑えるため、
   `AggregationStore` を3リポジトリへ委譲するファサードとして残す選択肢もある。
   利用箇所が少なければ直接置換のほうがシンプル（着手時に呼び出し箇所を数えて判断）。

### リスクと判断材料

- UI 側の読み出し（`ui/services/round_service.py` 等）は独自に DuckDB へ接続している箇所があり
  （`ui/utils/duckdb_conn.py`）、ストア分割と同時に「UI も storage 層経由に寄せるか」という
  設計論点が出る。スコープ膨張を避けるため、本候補は**書き込み側の分割に限定**し、
  UI 読み出し経路の統一は別タスクとして起票するのを推奨。
- 工数対効果は S1 より低い。S1 だけで300行制限に収まらない場合の第二弾として位置づける。

### 関連テスト（安全網）

S1 で追加したテスト＋既存 integration が安全網。分割後はテストもリポジトリ単位に
再編成し、`tests/unit/storage/` の構造を実装に合わせる。
