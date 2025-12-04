"""Data models for UserPromptBuilder.

Feature: 092-user-prompt-builder-team, 140-user-prompt-builder-evaluator-judgement
Date: 2025-11-19, 2025-11-25
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ValidationInfo, field_validator

if TYPE_CHECKING:
    from mixseek.round_controller.models import RoundState


class RoundPromptContext(BaseModel):
    """Context information required for prompt generation.

    Args:
        user_prompt: Original user prompt
        round_number: Current round number (>=1)
        round_history: History of all past rounds (list of RoundState)
        team_id: Unique team identifier
        team_name: Team name
        execution_id: Execution ID (used for Leader Board retrieval)
        store: DuckDB store (for Leader Board retrieval). None if ranking info unavailable

    Raises:
        ValueError: If validation fails
    """

    model_config = {"arbitrary_types_allowed": True}

    user_prompt: str
    round_number: int
    round_history: list[RoundState]
    team_id: str
    team_name: str
    execution_id: str
    store: Any = None  # AggregationStore | None - using Any to allow mocks in tests

    @field_validator("round_number")
    @classmethod
    def validate_round_number(cls, v: int) -> int:
        """Validate that round_number is >= 1.

        Args:
            v: round_number value

        Returns:
            Validated round_number

        Raises:
            ValueError: If round_number < 1
        """
        if v < 1:
            msg = "round_number must be >= 1"
            raise ValueError(msg)
        return v

    @field_validator("user_prompt", "team_id", "team_name", "execution_id")
    @classmethod
    def validate_not_empty(cls, v: str, info: ValidationInfo) -> str:
        """Validate that string fields are not empty.

        Args:
            v: Field value
            info: Field validation info

        Returns:
            Validated field value

        Raises:
            ValueError: If field is empty
        """
        if not v or v.strip() == "":
            field_name = info.field_name
            msg = f"{field_name} cannot be empty"
            raise ValueError(msg)
        return v


class EvaluatorPromptContext(BaseModel):
    """Context information for Evaluator prompt generation.

    Args:
        user_query: Original user query
        submission: AI agent's submission content

    Raises:
        ValueError: If validation fails

    Note:
        current_datetime is not included in this context. It is retrieved
        within UserPromptBuilder by calling get_current_datetime_with_timezone().
        This follows the same pattern as RoundPromptContext.

    Example:
        ```python
        from mixseek.prompt_builder.models import EvaluatorPromptContext

        context = EvaluatorPromptContext(
            user_query="Pythonとは何ですか？",
            submission="Pythonはプログラミング言語です..."
        )
        ```
    """

    user_query: str
    submission: str

    @field_validator("user_query", "submission")
    @classmethod
    def validate_not_empty(cls, v: str, info: ValidationInfo) -> str:
        """Validate that string fields are not empty.

        Args:
            v: Field value
            info: Field validation info

        Returns:
            Validated field value

        Raises:
            ValueError: If field is empty
        """
        if not v or v.strip() == "":
            field_name = info.field_name
            msg = f"{field_name} cannot be empty"
            raise ValueError(msg)
        return v
