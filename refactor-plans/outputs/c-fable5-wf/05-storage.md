# リファクタリング計画: storage サブシステム

## 概要（責務と依存の現状）

`src/mixseek/storage/` は3ファイル・計1,016行（wc -l 実測）。

| ファイル | 行数 | 内容 |
|---|---|---|
| `aggregation_store.py` | 907 | `AggregationStore` クラス1つに全永続化責務が集中 |
| `schema.py` | 101 | Round Controller 用 DDL 定数（Feature 037） |
| `__init__.py` | 8 | `AggregationStore` のみ公開 |

`AggregationStore` が担う責務（単一クラスに7種混在）:

1. DBパス解決（`_get_db_path`、`utils.env.get_workspace_path` 経由）
2. スレッドローカル接続管理（`_get_connection`、MVCC並列書き込み対応）
3. トランザクション管理（`_transaction` コンテキストマネージャ）
4. スキーマ初期化（`_init_tables_sync` のインラインDDL + `schema.ALL_SCHEMA_DDL`）
5. 4テーブル（round_history / leader_board / execution_summary / round_status）のCRUD
6. リトライ制御（エクスポネンシャルバックオフ、sync/asyncペアの定型）
7. Pydantic⇔JSON 変換（`to_jsonable_python` / `ModelMessagesTypeAdapter`）

依存:
- 外部: `duckdb`, `pandas`, `pydantic_ai`, `pydantic_core`
- 内部: `mixseek.agents.leader.models.MemberSubmissionsRecord`（L29、**上位層 agents への逆方向依存**）、
  `mixseek.utils.env`
- 利用側: `round_controller/controller.py`（L36, 112, 372...）、`orchestrator/orchestrator.py`（L350-352）、
  `cli/commands/team.py`（L53, 312）、`prompt_builder/builder.py`（L15, 128）
- 注意: UI 層は storage を介さず `duckdb.connect` を直接4箇所で実行
  （`ui/utils/db_utils.py:71`, `ui/utils/duckdb_conn.py:32`, `ui/services/execution_service.py:573,681`）。
  読み取り経路が二重化している。

## 評価サマリ（観点1〜5）

### 観点1: 責務と依存
上記の通り、`AggregationStore` が god class 化。接続管理・スキーマ・クエリ・リトライ・シリアライズが
1クラスに混在。また storage→agents という依存方向の逆転がある（永続化層がドメイン上位層の型を import）。

### 観点2: 設計上の臭い
- **肥大化**: 907行の単一ファイル・単一クラス。
- **DRY違反（重大）**:
  - リトライループ `delays = [1, 2, 4]` + `for attempt, delay in enumerate(...)` がほぼ同一の形で
    **4回複製**（L298-308, L566-589, L701-724, L827-851）。
  - `leader_board` テーブルDDLが `_init_tables_sync`（L176-198）と `schema.py`（L46-76）に**二重定義**。
    `leader_board_id_seq` も両方で作成（L148 と schema.py L89-91）。`IF NOT EXISTS` のため先勝ちとなり、
    将来のカラム変更時にドリフトする危険がある。
  - `_init_tables_sync`（L239-240）と `initialize_schema`（L591-604）の両方が `ALL_SCHEMA_DDL` を実行し、
    `initialize_schema` はコンストラクタ実行後は実質冗長。
  - sync版 `_xxx_sync` / async版 `xxx` のペアで引数リストを2回書き写す定型が5組。
- **古いパターン**: 関数内 import（`datetime` L640-641, L760-761 / `get_workspace_path` L98）。
- **公開APIの型漏れ**: `get_leader_board` が `pandas.DataFrame` を返し（L398）、pandas が永続化層の
  公開契約に露出。

### 観点3: AGENTS.md 自己ルール違反
- `aggregation_store.py` 907行は **300行ルールの3倍超**（リポジトリ内2位）。
- **共通ロガー完全不在**: storage 配下に logger/logging への参照がゼロ（grep で0件）。
  リトライ失敗・ROLLBACK・スキーマ初期化が一切ログされず、構造化JSONログ規約に違反。
- `os.getenv` 直接呼び出しは無し（`utils.env` 経由）— 適合。1関数200行超も無し — 適合。
- docstring が日本語/英語混在（Feature 037 追加分 L591 以降は英語）。共通語日本語の方針と不整合（軽微）。

### 観点4: エラー処理・型
- 型注釈は概ね網羅（mypy 対応の `cast` あり L115）。
- リトライが広い `except Exception`（L305, 586, 721, 848）のため、プログラミングエラー
  （TypeError 等）まで最大7秒リトライしてしまう。`duckdb.Error` への限定が望ましい。
- `status` の手動 set バリデーション（L511-514）は `Literal["completed", "partial_failure", "failed"]` で
  型として表現可能。
- `save_to_leader_board` は **10引数**（L795-807）、`save_round_status` 9引数、`save_execution_summary`
  8引数。`models/leaderboard.py` に `LeaderBoardEntry` が既存なのに未使用。
- `close()` やコンテキストマネージャが無く、スレッドローカル接続が `asyncio.to_thread` のプール
  スレッドに残留しうる（明示的なライフサイクル管理なし）。

### 観点5: テスト被覆
安全網は**厚い**。リファクタの前提条件は良好。

- `tests/unit/storage/test_aggregation_store.py`: 635行・18テスト（保存/読込/UPSERT/ランキング/統計/
  スコア範囲/タイブレーク）
- `tests/agents/leader/test_store.py`: 248行。**リトライ・バックオフ・最大リトライ超過を直接検証**
- `tests/database/test_schema.py`: 219行（テーブル/制約/インデックス）
- `tests/integration/test_concurrent_writes.py`: 156行（MVCC並列書き込み）

手薄な点: `save_execution_summary` の直接ユニットテスト、`DatabaseReadError` 系の異常系。

## リファクタリング候補

### 候補1: スキーマDDLの schema.py への一元化
- **対象**: `aggregation_store.py` L138-240（`_init_tables_sync`）、`storage/schema.py`
- **問題**: 観点2（DRY違反）。`leader_board` のDDL・シーケンスが2箇所に二重定義され、`IF NOT EXISTS` の
  先勝ちでスキーマドリフトの温床。`initialize_schema` と `_init_tables_sync` の役割も重複。
- **影響度**: 中 / **リスク**: 低
- **推奨アプローチ**: 全テーブル（round_history / execution_summary 含む）のDDLを `schema.py` に集約し、
  `_init_tables_sync` は `ALL_SCHEMA_DDL` の実行のみとする。冗長化した `initialize_schema` は
  `_init_tables_sync` への委譲に変更（公開APIは互換維持）。
- **関連テスト**: `tests/database/test_schema.py` がテーブル・制約・インデックスを直接検証しており安全網十分。
- **工数感**: S

### 候補2: リトライ/sync-async 定型コードの共通化
- **対象**: `aggregation_store.py` L298-308, L566-589, L701-724, L827-851
- **問題**: 観点2（DRY違反）・観点4。同一のバックオフリトライが4回複製。`except Exception` が広すぎ、
  非DBエラーまでリトライする。
- **影響度**: 中 / **リスク**: 低
- **推奨アプローチ**: `async def _write_with_retry(self, func, /, *args, error_label: str)` のような
  共通ヘルパ（または デコレータ）に集約。捕捉対象を `duckdb.Error` に限定し、`ValueError` 即時再送出の
  分岐も1箇所に。delays をクラス定数化。
- **関連テスト**: `tests/agents/leader/test_store.py::test_exponential_backoff_retry` /
  `test_max_retries_exceeded` がリトライ挙動を直接検証。
- **工数感**: S

### 候補3: 共通ロガー導入と例外・ログ設計の整理
- **対象**: `src/mixseek/storage/` 全体
- **問題**: 観点3（共通ロガー未使用・構造化JSONログ無し）・観点4。リトライ失敗・ROLLBACK・接続生成が
  無音で、障害時の追跡が不可能。例外は文字列メッセージのみで文脈（テーブル名等）が構造化されていない。
- **影響度**: 中 / **リスク**: 低
- **推奨アプローチ**: プロジェクト共通のロギング設定（`mixseek/config/logging.py` 系）に従う logger を導入し、
  リトライ各試行（warning）・最終失敗（error）・スキーマ初期化（debug）を構造化フィールド
  （execution_id, team_id, table, attempt）付きで記録。`DatabaseWriteError`/`DatabaseReadError` は
  維持しつつ発生箇所に文脈を付与。
- **関連テスト**: 既存テストはログ非依存のため回帰リスク小。ログ出力のユニットテストを追加。
- **工数感**: S

### 候補4: AggregationStore の責務分割（接続基盤 + テーブル別リポジトリ）
- **対象**: `aggregation_store.py`（907行）
- **問題**: 観点1・観点2・観点3（300行ルールの3倍超）。接続管理/トランザクション/4テーブルCRUD/
  シリアライズが単一クラスに混在し、変更影響範囲が常にファイル全体に及ぶ。
- **影響度**: 高 / **リスク**: 中
- **推奨アプローチ**: 候補1〜3完了後に実施。以下に分割し、`AggregationStore` は後方互換の
  ファサード（各リポジトリへ委譲）として維持する:
  - `storage/connection.py` … パス解決・スレッドローカル接続・`_transaction`・リトライヘルパ（約150行）
  - `storage/round_history_store.py` … save_aggregation / load_round_history（約150行）
  - `storage/leader_board_store.py` … leader_board 系4メソッド（約250行）
  - `storage/round_status_store.py` / `storage/execution_summary_store.py`（各約120行）
  既存呼び出し側4箇所（round_controller / orchestrator / cli / prompt_builder）は変更不要。
- **関連テスト**: unit 635行 + integration（並列書き込み）+ leader/test_store.py。公開API不変なら
  既存テストがそのまま回帰検証になる。
- **工数感**: L

### 候補5: 公開APIの型整理（パラメータオブジェクト化・pandas/レイヤ逆転の解消）
- **対象**: `save_to_leader_board`（10引数）、`save_round_status`（9引数）、`save_execution_summary`
  （8引数）、`get_leader_board`（DataFrame返却 L398）、`MemberSubmissionsRecord` import（L29）
- **問題**: 観点1（storage→agents の依存逆転）・観点4（長い引数リスト、`status` の手動バリデーション、
  既存 `models/leaderboard.py::LeaderBoardEntry` の未活用）。引数の順序ミスを型で防げない。
- **影響度**: 中 / **リスク**: 中（呼び出し側 round_controller / orchestrator / cli の修正を伴う）
- **推奨アプローチ**: `models/` 配下に `RoundStatusRecord` / `ExecutionSummaryRecord` 等の Pydantic モデルを
  定義し（`status` は `Literal` 化）、save 系はモデル1個を受ける署名に移行（経過期間は旧署名を
  デプリケート併存）。`get_leader_board` は dict リスト返却を基本とし、DataFrame 変換は UI 側に寄せる。
  storage が参照するドメイン型は `models/` 層へ移して依存方向を一方向化。
- **関連テスト**: unit テストが各 save/get を網羅。署名変更分のテスト書き換えが必要（機械的）。
- **工数感**: M

### 候補6: UI 層の DuckDB 直接接続を storage 読み取りAPIへ統合
- **対象**: `ui/utils/db_utils.py:71`、`ui/utils/duckdb_conn.py:32`、
  `ui/services/execution_service.py:573,681`（storage 側に read-only 接続APIを追加）
- **問題**: 観点1・観点2（重複・密結合）。UI が storage を迂回して `duckdb.connect(read_only=True)` を
  4箇所で重複実装し、スキーマ知識（テーブル名・カラム）が UI に漏れている。
- **影響度**: 中 / **リスク**: 中（UI の挙動仕様「Orchestrator 実行中は None 返却」を維持する必要あり）
- **推奨アプローチ**: storage 側に read-only 接続ファクトリ（または読み取り専用クエリAPI）を追加し、
  UI 4箇所をそれに置き換え。候補4の `connection.py` 切り出しと同時に行うと効率的。
- **関連テスト**: `tests/ui/` 配下の既存テストを安全網とし、接続失敗時フォールバックの回帰テストを追加。
- **工数感**: M

### 推奨着手順
候補1 → 候補2 → 候補3（いずれも低リスク・即効）→ 候補4（本丸のファイル分割）→ 候補5 → 候補6。
