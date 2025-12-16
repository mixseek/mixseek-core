"""LeaderBoard data models

Feature: 037-mixseek-core-round-controller
Date: 2025-11-10
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class LeaderBoardEntry(BaseModel):
    """Leader board table record

    This model represents a single leaderboard entry for a team's submission.
    It is the final return value from Round Controller to Orchestrator (FR-007).
    """

    id: int | None = Field(default=None, description="Auto-incremented unique ID")
    execution_id: str = Field(description="Task ID (linked to single user query)")
    team_id: str = Field(description="Team identifier")
    team_name: str = Field(description="Team name")
    round_number: int = Field(ge=1, description="Round number")
    submission_content: str = Field(description="Submission content from team")
    submission_format: str = Field(default="md", description="Submission format (default: md)")
    score: float = Field(description="Evaluation score from Evaluator")
    score_details: dict[str, Any] = Field(description="Detailed score breakdown and comments (JSON format)")
    final_submission: bool = Field(default=False, description="Flag indicating if this is the final round submission")
    exit_reason: str | None = Field(
        default=None,
        description="Reason for round termination (e.g., 'max rounds reached', 'no improvement expected')",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Record creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Record update timestamp")
