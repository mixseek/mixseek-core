# 02. storage：sync/async 二重定義の解消と分割

## R5 — `aggregation_store.py` の sync/async 重複デコレータ化＋責務分割

- **対象**: `src/mixseek/storage/aggregation_store.py`（907行・`AggregationStore`）
- **問題**（DRY違反 / 肥大化）:
  - DuckDB 操作のほぼ全てが **`_xxx_sync`（同期実体）＋ `async xxx`（`asyncio.to_thread`
    ＋例外ラップ＋リトライ）** の対で実装され、約10対が並んでいる：
    - `_save_sync` / `save_aggregation`
    - `_load_round_history_sync` / `load_round_history`
    - `_get_leader_board_sync` / `get_leader_board`
    - `_get_team_statistics_sync` / `get_team_statistics`
    - `_save_execution_summary_sync` / `save_execution_summary`
    - `_save_round_status_sync` / `save_round_status`
    - `_save_to_leader_board_sync` / `save_to_leader_board`
    - `_get_leader_board_ranking_sync` / `get_leader_board_ranking`
  - async 側のコードは「`asyncio.to_thread(self._xxx_sync, ...)` ＋ 失敗時の
    `DatabaseReadError`/`DatabaseWriteError` ラップ」「書き込み系は `delays=[1,2,4]` の指数バックオフ」
    という**ほぼ同一の定型**が毎回コピーされている（例: `save_aggregation` の retry ループ）。
  - 加えてテーブル初期化（`_init_tables_sync`：138〜240行で巨大な DDL）、読み取り、書き込み、
    集計、ランキングが1クラスに同居しており単一責任を超えている。
- **影響度**: 高（ラウンド履歴・リーダーボード・実行サマリの永続化中枢。orchestrator/
  round_controller/UI が依存）
- **リスク**: 中（DB I/O の挙動は壊すと検知しづらいが、storage テスト12ファイル＋
  `tests/database` が安全網。デコレータ化自体は機械的）
- **推奨アプローチ**:
  1. **async ラッパの定型をデコレータに集約**：
     - `@async_db_read`（`to_thread` 実行＋`DatabaseReadError` ラップ）と
       `@async_db_write`（同＋指数バックオフリトライ `[1,2,4]`）を新設し、
       各 async メソッドは `_xxx_sync` を指す薄い宣言にする。
     - これで async 側のボイラープレートが約10箇所→2デコレータに収斂し、リトライ方針の一元管理も実現。
  2. **責務でファイル分割**（パッケージ化）：
     - `aggregation_store/schema_ddl.py`（`_init_tables_sync` の DDL）
     - `aggregation_store/round_history.py`・`leaderboard.py`・`statistics.py`・`execution_summary.py`
       のように「読み書きのまとまり」を mixin もしくは協調オブジェクトに分離。
     - 接続管理（`_get_connection`・`_transaction`・`_get_db_path`）は基盤として残す。
  3. 例外クラス（`DatabaseWriteError`/`DatabaseReadError`）は `storage/exceptions.py` 等へ。
- **関連テスト**: `tests/unit/storage/`・`tests/database/`（aggregation_store参照12ファイル）。
  デコレータ化はまず「同期実体は不変・async 振る舞いも不変」を保つ形で進めれば回帰は出にくい。
- **工数**: L（デコレータ化は M 相当、ファイル分割まで含めて L）

### メモ：デコレータ化のイメージ（説明用、実装はしない）

現状の各 async メソッドは概ね次の形をしている：

```
async def save_xxx(self, ...):
    delays = [1, 2, 4]
    for attempt, delay in enumerate(delays, 1):
        try:
            await asyncio.to_thread(self._save_xxx_sync, ...)
            return
        except Exception as e:
            if attempt == len(delays):
                raise DatabaseWriteError(...) from e
            await asyncio.sleep(delay)
```

この「リトライ＋to_thread＋例外ラップ」を `@async_db_write` 1つに括り出せば、
書き込み系メソッドはシグネチャと `_save_xxx_sync` 呼び出しだけの宣言に縮む。
読み取り系も同様に `@async_db_read`（リトライ無し・`DatabaseReadError` ラップ）へ。
