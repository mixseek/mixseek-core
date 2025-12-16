"""Round Controller data models

Feature: 037-mixseek-core-round-controller
Date: 2025-11-10
"""

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from mixseek.agents.leader.models import MemberSubmission


class ImprovementJudgment(BaseModel):
    """LLM-based improvement prospect judgment result

    This model captures the result of LLM-as-a-Judge assessment
    to determine if another round should be executed.
    """

    should_continue: bool = Field(description="Whether to proceed to the next round")
    reasoning: str = Field(description="Detailed reasoning for the judgment")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence score (0.0-1.0 range)")


class RoundState(BaseModel):
    """Complete state for a single round

    This model holds all information for a round,
    including submission, evaluation, and judgment results.
    """

    round_number: int = Field(ge=1, description="Round number")
    submission_content: str = Field(description="Submission content")
    evaluation_score: float = Field(description="Evaluation score")
    score_details: dict[str, Any] = Field(
        description="Detailed score breakdown (JSON format, consistent with LeaderBoardEntry)"
    )
    improvement_judgment: ImprovementJudgment | None = Field(
        default=None, description="Improvement prospect judgment result"
    )
    round_started_at: datetime = Field(description="Round start timestamp")
    round_ended_at: datetime = Field(description="Round end timestamp")
    message_history: list[dict[str, Any]] = Field(default_factory=list, description="Message history (JSON format)")


# Type alias for round completion callback
# Called after each round completes with the round state and member agent submissions
# Second argument is list of MemberSubmission from individual Member Agents (not Leader's final submission)
OnRoundCompleteCallback = Callable[
    ["RoundState", list["MemberSubmission"]],
    Awaitable[None],
]
