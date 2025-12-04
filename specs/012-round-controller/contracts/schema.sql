-- DuckDB Schema Definition for Round Controller
-- Feature: 037-mixseek-core-round-controller
-- Date: 2025-11-10

-- ===================================================
-- round_status テーブル
-- チームがどのように行動したかを記録する役割を持つ
-- ===================================================

CREATE TABLE IF NOT EXISTS round_status (
    -- 主キー
    id INTEGER PRIMARY KEY,

    -- 識別子
    execution_id VARCHAR NOT NULL,
    team_id VARCHAR NOT NULL,
    team_name VARCHAR NOT NULL,
    round_number INTEGER NOT NULL,

    -- 改善見込み判定結果（LLM-as-a-Judge）
    should_continue BOOLEAN NULL,       -- TRUE: 継続すべき、FALSE: 終了すべき、NULL: 未判定
    reasoning TEXT NULL,                -- 判定理由の詳細説明
    confidence_score FLOAT NULL,        -- 信頼度スコア（0-1の範囲）

    -- ラウンド日時
    round_started_at TIMESTAMP NULL,
    round_ended_at TIMESTAMP NULL,

    -- レコード管理
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- UNIQUE制約: (execution_id, team_id, round_number) の組み合わせで一意性を保証
    UNIQUE (execution_id, team_id, round_number)
);

-- INDEX: execution_id, team_id, round_number DESC でラウンド履歴照会を最適化
CREATE INDEX IF NOT EXISTS idx_round_status_execution_team_round
ON round_status (execution_id, team_id, round_number DESC);

-- ===================================================
-- leader_board テーブル
-- 各チーム、各ラウンドのSubmissionと評価結果を記録する役割を持つ
-- ===================================================

CREATE TABLE IF NOT EXISTS leader_board (
    -- 主キー
    id INTEGER PRIMARY KEY,

    -- 識別子
    execution_id VARCHAR NOT NULL,
    team_id VARCHAR NOT NULL,
    team_name VARCHAR NOT NULL,
    round_number INTEGER NOT NULL,

    -- Submission情報
    submission_content TEXT NOT NULL,
    submission_format VARCHAR NOT NULL DEFAULT 'md',

    -- 評価結果
    score FLOAT NOT NULL,               -- Evaluatorからの評価スコア（0-100）
    score_details JSON NOT NULL,        -- 各評価指標のスコア内訳、コメント（JSON形式）

    -- 終了情報
    final_submission BOOLEAN NOT NULL DEFAULT FALSE,
    exit_reason VARCHAR NULL,           -- 例: "max rounds reached", "no improvement expected"

    -- レコード管理
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- UNIQUE制約: (execution_id, team_id, round_number) の組み合わせで一意性を保証
    UNIQUE (execution_id, team_id, round_number)
);

-- INDEX: execution_id, score DESC, round_number DESC でタスクごとのランキング照会とタイブレークを最適化
CREATE INDEX IF NOT EXISTS idx_leader_board_execution_score
ON leader_board (execution_id, score DESC, round_number DESC);
