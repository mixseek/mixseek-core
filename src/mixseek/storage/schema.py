"""DuckDB schema definitions for Round Controller

Feature: 037-mixseek-core-round-controller
Date: 2025-11-10

This module defines DDL statements for round_status and leader_board tables.
"""

# DDL for round_status table
ROUND_STATUS_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS round_status (
    -- Primary key
    id INTEGER PRIMARY KEY DEFAULT nextval('round_status_id_seq'),

    -- Identifiers
    execution_id VARCHAR NOT NULL,
    team_id VARCHAR NOT NULL,
    team_name VARCHAR NOT NULL,
    round_number INTEGER NOT NULL,

    -- Improvement judgment results (LLM-as-a-Judge)
    should_continue BOOLEAN NULL,       -- TRUE: should continue, FALSE: should terminate, NULL: not judged
    reasoning TEXT NULL,                -- Detailed reasoning for the judgment
    confidence_score FLOAT NULL,        -- Confidence score (0.0-1.0 range)

    -- Round timestamps
    round_started_at TIMESTAMP NULL,
    round_ended_at TIMESTAMP NULL,

    -- Record management
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- UNIQUE constraint: ensures uniqueness of (execution_id, team_id, round_number)
    UNIQUE (execution_id, team_id, round_number)
)
"""

# Index for round_status table
ROUND_STATUS_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS idx_round_status_execution_team_round
ON round_status (execution_id, team_id, round_number DESC)
"""

# DDL for leader_board table
LEADER_BOARD_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS leader_board (
    -- Primary key
    id INTEGER PRIMARY KEY DEFAULT nextval('leader_board_id_seq'),

    -- Identifiers
    execution_id VARCHAR NOT NULL,
    team_id VARCHAR NOT NULL,
    team_name VARCHAR NOT NULL,
    round_number INTEGER NOT NULL,

    -- Submission information
    submission_content TEXT NOT NULL,
    submission_format VARCHAR NOT NULL DEFAULT 'md',

    -- Evaluation results
    score FLOAT NOT NULL,               -- Evaluation score from Evaluator (0-100)
    score_details JSON NOT NULL,        -- Detailed score breakdown and comments (JSON format)

    -- Termination information
    final_submission BOOLEAN NOT NULL DEFAULT FALSE,
    exit_reason VARCHAR NULL,           -- e.g., "max rounds reached", "no improvement expected"

    -- Record management
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- UNIQUE constraint: ensures uniqueness of (execution_id, team_id, round_number)
    UNIQUE (execution_id, team_id, round_number)
)
"""

# Index for leader_board table
LEADER_BOARD_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS idx_leader_board_execution_score
ON leader_board (execution_id, score DESC, round_number DESC)
"""

# Sequence definitions
ROUND_STATUS_SEQUENCE_DDL = """
CREATE SEQUENCE IF NOT EXISTS round_status_id_seq
"""

LEADER_BOARD_SEQUENCE_DDL = """
CREATE SEQUENCE IF NOT EXISTS leader_board_id_seq
"""

# All DDL statements in execution order
ALL_SCHEMA_DDL: list[str] = [
    ROUND_STATUS_SEQUENCE_DDL,
    LEADER_BOARD_SEQUENCE_DDL,
    ROUND_STATUS_TABLE_DDL,
    ROUND_STATUS_INDEX_DDL,
    LEADER_BOARD_TABLE_DDL,
    LEADER_BOARD_INDEX_DDL,
]
