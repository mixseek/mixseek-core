-- Database Schema: Leader Agent - Agent Delegation と Member Agent応答記録
-- Feature: 026-mixseek-core-leader
-- Date: 2025-10-23
-- Database: DuckDB >=1.3.1

-- ============================================================================
-- シーケンス定義（IDENTITY代替、Clarifications 2025-10-23）
-- ============================================================================

CREATE SEQUENCE IF NOT EXISTS round_history_id_seq;
CREATE SEQUENCE IF NOT EXISTS leader_board_id_seq;
CREATE SEQUENCE IF NOT EXISTS execution_summary_id_seq;

-- ============================================================================
-- round_history テーブル (FR-006, FR-007, FR-008)
-- ============================================================================
-- Purpose: チーム×ラウンドごとのMessage HistoryとMember Agent応答記録を永続化
-- MVCC並列書き込み対応、単一トランザクション保存（FR-007-1）

CREATE TABLE IF NOT EXISTS round_history (
    -- プライマリキー
    id INTEGER PRIMARY KEY DEFAULT nextval('round_history_id_seq'),

    -- 実行識別情報（Orchestrator統合、025-mixseek-core-orchestration）
    execution_id TEXT NOT NULL,

    -- チーム識別情報
    team_id TEXT NOT NULL,
    team_name TEXT NOT NULL,
    round_number INTEGER NOT NULL CHECK (round_number >= 1),

    -- Pydantic AI Message History（JSON型、FR-006）
    -- Pydantic AIのModelMessagesTypeAdapterでシリアライズ・デシリアライズ
    message_history JSON,

    -- Member Agent応答記録（JSON型、FR-007）
    -- MemberSubmissionsRecordの構造化データ
    -- 注意: 従来の aggregated_submissions から member_submissions_record に変更
    member_submissions_record JSON,

    -- メタデータ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 一意性制約（FR-008、Orchestrator統合対応）
    -- 同一実行内の同一チーム・同一ラウンドの重複を防ぐ（UPSERT可能）
    UNIQUE(execution_id, team_id, round_number)
);

-- インデックス（読み取り最適化、Orchestrator統合対応）
CREATE INDEX IF NOT EXISTS idx_round_history_execution
ON round_history(execution_id, team_id, round_number);

COMMENT ON TABLE round_history IS 'Leader Agentのラウンド履歴（Message History + Member Agent応答記録）';
COMMENT ON COLUMN round_history.message_history IS 'Pydantic AI Message History（JSON型）';
COMMENT ON COLUMN round_history.member_submissions_record IS 'MemberSubmissionsRecord（構造化JSON、Agent Delegation記録）';

-- ============================================================================
-- leader_board テーブル (FR-010, FR-011)
-- ============================================================================
-- Purpose: Submission評価結果のランキング管理
-- スコア降順インデックスで高速ランキング取得

CREATE TABLE IF NOT EXISTS leader_board (
    -- プライマリキー
    id INTEGER PRIMARY KEY DEFAULT nextval('leader_board_id_seq'),

    -- 実行識別情報（Orchestrator統合、025-mixseek-core-orchestration）
    execution_id TEXT NOT NULL,

    -- チーム識別情報
    team_id TEXT NOT NULL,
    team_name TEXT NOT NULL,
    round_number INTEGER NOT NULL CHECK (round_number >= 1),

    -- 評価結果
    -- スコアは0.0-1.0の範囲（DB level validation）
    evaluation_score DOUBLE NOT NULL CHECK (evaluation_score >= 0.0 AND evaluation_score <= 1.0),
    evaluation_feedback TEXT,

    -- Submission内容
    submission_content TEXT NOT NULL,
    -- 注意: 'markdown' → 'structured_json' に変更
    submission_format TEXT DEFAULT 'structured_json',

    -- リソース使用量（JSON型）
    -- Pydantic AI RunUsage形式: {"input_tokens": 100, "output_tokens": 200, "requests": 1}
    usage_info JSON,

    -- メタデータ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ランキングクエリ最適化インデックス（FR-011）
-- スコア降順、同スコアは作成日時早い順
CREATE INDEX IF NOT EXISTS idx_leader_board_score
ON leader_board(evaluation_score DESC, created_at ASC);

-- Orchestrator実行単位での検索インデックス
CREATE INDEX IF NOT EXISTS idx_leader_board_execution
ON leader_board(execution_id);

COMMENT ON TABLE leader_board IS 'チームSubmissionの評価ランキング';
COMMENT ON COLUMN leader_board.evaluation_score IS '評価スコア（0.0-1.0、CHECK制約付き）';
COMMENT ON COLUMN leader_board.submission_format IS 'Submission形式（structured_json: 構造化データ、markdownはレガシー）';

-- ============================================================================
-- execution_summary テーブル (Orchestrator、025-mixseek-core-orchestration)
-- ============================================================================
-- Purpose: オーケストレーション実行全体の最終サマリー記録
-- 複数チームの実行結果を集約し、完了ステータスとメトリクスを保存

CREATE TABLE IF NOT EXISTS execution_summary (
    -- プライマリキー（実行識別子）
    execution_id TEXT PRIMARY KEY,

    -- 実行メタデータ
    user_prompt TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('completed', 'partial_failure', 'failed')),

    -- チーム結果集約（JSON型）
    -- 構造: [{team_id, team_name, status, score, error}]
    team_results JSON NOT NULL,
    total_teams INTEGER NOT NULL,

    -- 実行統計
    best_team_id TEXT,
    best_score DOUBLE,
    total_execution_time_seconds DOUBLE NOT NULL,

    -- メタデータ
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ステータス別検索インデックス（完了日時降順）
CREATE INDEX IF NOT EXISTS idx_execution_summary_status
ON execution_summary(status, completed_at DESC);

COMMENT ON TABLE execution_summary IS 'Orchestrator実行全体のサマリー（025-mixseek-core-orchestration）';
COMMENT ON COLUMN execution_summary.status IS '実行ステータス（completed: 全成功、partial_failure: 一部失敗、failed: 全失敗）';
COMMENT ON COLUMN execution_summary.team_results IS 'チーム別結果（JSON配列、構造化データ）';

-- ============================================================================
-- クエリ例
-- ============================================================================

-- 1. ラウンド履歴保存（単一トランザクション、FR-007-1）
-- 注意: アプリケーションコードでBEGIN/COMMIT必須
-- BEGIN TRANSACTION;
-- INSERT INTO round_history (execution_id, team_id, team_name, round_number, message_history, member_submissions_record)
-- VALUES (?, ?, ?, ?, ?::JSON, ?::JSON)
-- ON CONFLICT (execution_id, team_id, round_number) DO UPDATE SET
--     message_history = EXCLUDED.message_history,
--     member_submissions_record = EXCLUDED.member_submissions_record,
--     created_at = CURRENT_TIMESTAMP;
-- COMMIT;

-- 2. ラウンド履歴読み込み（FR-012）
-- SELECT message_history, member_submissions_record
-- FROM round_history
-- WHERE execution_id = ? AND team_id = ? AND round_number = ?;

-- 3. Leader Boardランキング取得（FR-011）
-- SELECT team_name, round_number, evaluation_score, evaluation_feedback, created_at
-- FROM leader_board
-- ORDER BY evaluation_score DESC, created_at ASC
-- LIMIT 10;

-- 4. チーム統計集計（FR-013、JSON内部クエリ）
-- SELECT
--     COUNT(*) as total_rounds,
--     AVG(evaluation_score) as avg_score,
--     MAX(evaluation_score) as best_score,
--     SUM(CAST(json_extract(usage_info, '$.input_tokens') AS INTEGER)) as total_input_tokens,
--     SUM(CAST(json_extract(usage_info, '$.output_tokens') AS INTEGER)) as total_output_tokens
-- FROM leader_board
-- WHERE team_id = ?;

-- 5. 特定Member Agentの応答抽出（JSON内部クエリ）
-- SELECT
--     team_id,
--     round_number,
--     json_extract(member_submissions_record, '$.submissions[*].agent_name') as agent_names,
--     json_extract(member_submissions_record, '$.submissions[*].content') as contents
-- FROM round_history
-- WHERE team_id = ?
-- ORDER BY round_number;

-- 6. Execution Summary保存（Orchestrator、025-mixseek-core-orchestration）
-- INSERT INTO execution_summary
-- (execution_id, user_prompt, status, team_results, total_teams, best_team_id, best_score, total_execution_time_seconds)
-- VALUES (?, ?, ?, ?::JSON, ?, ?, ?, ?);

-- 7. Execution Summary取得（特定実行の完了サマリー）
-- SELECT execution_id, user_prompt, status, team_results, total_teams, best_team_id, best_score, total_execution_time_seconds, completed_at
-- FROM execution_summary
-- WHERE execution_id = ?;

-- 8. 実行履歴一覧取得（ステータス別、完了日時降順）
-- SELECT execution_id, user_prompt, status, total_teams, best_score, completed_at
-- FROM execution_summary
-- WHERE status = ?
-- ORDER BY completed_at DESC
-- LIMIT 10;

-- ============================================================================
-- MVCC並列書き込みテスト (SC-001, FR-014)
-- ============================================================================
-- 複数チーム同時書き込み（ロック競合なし）
-- 例: 10チーム×5ラウンド=50件の同時INSERT

-- Python側でasyncio.gather()を使用:
-- await asyncio.gather(*[
--     store.save_aggregation(record_i, messages_i)
--     for i in range(50)
-- ])

-- ============================================================================
-- Parquetエクスポート（Orchestration Layer責務、Out of Scope）
-- ============================================================================
-- JSON型カラムはSTRING型でParquet保存される点に注意

-- COPY (SELECT * FROM round_history WHERE created_at >= CURRENT_DATE)
-- TO 'archive/2025-10-23/history.parquet'
-- (FORMAT PARQUET, COMPRESSION ZSTD);

-- Parquetから読み込み時、JSON演算子使用にはCAST必要:
-- SELECT
--     CAST(member_submissions_record AS JSON)->'submissions'->0->>'agent_name' as first_agent
-- FROM 'archive/*/history.parquet';

-- ============================================================================
-- データベース初期化（テスト用）
-- ============================================================================
-- ⚠️ 本番環境では使用禁止

-- DELETE FROM round_history WHERE team_id LIKE 'dev-test-%';
-- DELETE FROM leader_board WHERE team_id LIKE 'dev-test-%';
-- VACUUM;  -- ディスク容量回収

-- ============================================================================
-- バージョン情報
-- ============================================================================
-- DuckDB Version: >=1.3.1
-- Schema Version: 2.0.0
-- Last Modified: 2025-11-05
-- Compatibility: Orchestrator統合対応、execution_id追加、execution_summaryテーブル追加
-- BREAKING CHANGE: UNIQUE制約変更 (team_id, round_number) -> (execution_id, team_id, round_number)
