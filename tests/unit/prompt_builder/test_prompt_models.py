"""Unit tests for prompt_builder models.

Feature: 092-user-prompt-builder-team, 140-user-prompt-builder-evaluator-judgement
Date: 2025-11-19, 2025-11-25
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from mixseek.config.schema import PromptBuilderSettings
from mixseek.prompt_builder.models import EvaluatorPromptContext, RoundPromptContext
from mixseek.round_controller.models import RoundState


class TestPromptBuilderSettings:
    """Tests for PromptBuilderSettings model."""

    def test_default_team_user_prompt(self) -> None:
        """Test that default team_user_prompt is set correctly."""
        settings = PromptBuilderSettings()
        assert settings.team_user_prompt
        assert "{{ user_prompt }}" in settings.team_user_prompt
        assert "{{ submission_history }}" in settings.team_user_prompt
        assert "{{ ranking_table }}" in settings.team_user_prompt
        assert "{{ team_position_message }}" in settings.team_user_prompt

    def test_empty_team_user_prompt_raises_error(self) -> None:
        """Test that empty team_user_prompt raises ValidationError."""
        with pytest.raises(ValidationError, match="team_user_prompt cannot be empty"):
            PromptBuilderSettings(team_user_prompt="")

    def test_whitespace_only_team_user_prompt_raises_error(self) -> None:
        """Test that whitespace-only team_user_prompt raises ValidationError."""
        with pytest.raises(ValidationError, match="team_user_prompt cannot be empty"):
            PromptBuilderSettings(team_user_prompt="   ")

    def test_default_evaluator_user_prompt(self) -> None:
        """Test that default evaluator_user_prompt is set correctly.

        Feature: 140-user-prompt-builder-evaluator-judgement
        Task: T014
        """
        settings = PromptBuilderSettings()
        assert settings.evaluator_user_prompt
        assert "{{ user_prompt }}" in settings.evaluator_user_prompt
        assert "{{ submission }}" in settings.evaluator_user_prompt
        assert "{{ current_datetime }}" in settings.evaluator_user_prompt

    def test_empty_evaluator_user_prompt_raises_error(self) -> None:
        """Test that empty evaluator_user_prompt raises ValidationError.

        Feature: 140-user-prompt-builder-evaluator-judgement
        Task: T014
        """
        with pytest.raises(ValidationError, match="evaluator_user_prompt cannot be empty"):
            PromptBuilderSettings(evaluator_user_prompt="")

    def test_whitespace_only_evaluator_user_prompt_raises_error(self) -> None:
        """Test that whitespace-only evaluator_user_prompt raises ValidationError.

        Feature: 140-user-prompt-builder-evaluator-judgement
        Task: T014
        """
        with pytest.raises(ValidationError, match="evaluator_user_prompt cannot be empty"):
            PromptBuilderSettings(evaluator_user_prompt="   ")

    def test_default_judgment_user_prompt(self) -> None:
        """Test that default judgment_user_prompt is set correctly.

        Feature: 140-user-prompt-builder-evaluator-judgement
        Task: T014
        """
        settings = PromptBuilderSettings()
        assert settings.judgment_user_prompt
        assert "{{ user_prompt }}" in settings.judgment_user_prompt
        assert "{{ submission_history }}" in settings.judgment_user_prompt
        assert "{{ ranking_table }}" in settings.judgment_user_prompt

    def test_empty_judgment_user_prompt_raises_error(self) -> None:
        """Test that empty judgment_user_prompt raises ValidationError.

        Feature: 140-user-prompt-builder-evaluator-judgement
        Task: T014
        """
        with pytest.raises(ValidationError, match="judgment_user_prompt cannot be empty"):
            PromptBuilderSettings(judgment_user_prompt="")

    def test_whitespace_only_judgment_user_prompt_raises_error(self) -> None:
        """Test that whitespace-only judgment_user_prompt raises ValidationError.

        Feature: 140-user-prompt-builder-evaluator-judgement
        Task: T014
        """
        with pytest.raises(ValidationError, match="judgment_user_prompt cannot be empty"):
            PromptBuilderSettings(judgment_user_prompt="   ")


class TestRoundPromptContext:
    """Tests for RoundPromptContext model."""

    def test_valid_context_round_1(self) -> None:
        """Test valid context for round 1."""
        context = RoundPromptContext(
            user_prompt="Test task",
            round_number=1,
            round_history=[],
            team_id="team1",
            team_name="Alpha",
            execution_id="exec1",
            store=None,
        )
        assert context.user_prompt == "Test task"
        assert context.round_number == 1
        assert context.round_history == []
        assert context.team_id == "team1"
        assert context.team_name == "Alpha"
        assert context.execution_id == "exec1"
        assert context.store is None

    def test_valid_context_round_2_with_history(self) -> None:
        """Test valid context for round 2 with history."""
        now = datetime.now(UTC)
        history = [
            RoundState(
                round_number=1,
                submission_content="First submission",
                evaluation_score=75.5,
                score_details={},
                round_started_at=now,
                round_ended_at=now,
            )
        ]
        context = RoundPromptContext(
            user_prompt="Test task",
            round_number=2,
            round_history=history,
            team_id="team1",
            team_name="Alpha",
            execution_id="exec1",
            store=None,
        )
        assert context.round_number == 2
        assert len(context.round_history) == 1
        assert context.round_history[0].round_number == 1

    def test_round_number_less_than_one_raises_error(self) -> None:
        """Test that round_number < 1 raises ValidationError."""
        with pytest.raises(ValidationError, match="round_number must be >= 1"):
            RoundPromptContext(
                user_prompt="Test task",
                round_number=0,
                round_history=[],
                team_id="team1",
                team_name="Alpha",
                execution_id="exec1",
            )

    def test_empty_user_prompt_raises_error(self) -> None:
        """Test that empty user_prompt raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            RoundPromptContext(
                user_prompt="",
                round_number=1,
                round_history=[],
                team_id="team1",
                team_name="Alpha",
                execution_id="exec1",
            )

    def test_empty_team_id_raises_error(self) -> None:
        """Test that empty team_id raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            RoundPromptContext(
                user_prompt="Test task",
                round_number=1,
                round_history=[],
                team_id="",
                team_name="Alpha",
                execution_id="exec1",
            )

    def test_empty_team_name_raises_error(self) -> None:
        """Test that empty team_name raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            RoundPromptContext(
                user_prompt="Test task",
                round_number=1,
                round_history=[],
                team_id="team1",
                team_name="",
                execution_id="exec1",
            )

    def test_empty_execution_id_raises_error(self) -> None:
        """Test that empty execution_id raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            RoundPromptContext(
                user_prompt="Test task",
                round_number=1,
                round_history=[],
                team_id="team1",
                team_name="Alpha",
                execution_id="",
            )


class TestEvaluatorPromptContext:
    """Tests for EvaluatorPromptContext model.

    Feature: 140-user-prompt-builder-evaluator-judgement
    Task: T014
    """

    def test_valid_context(self) -> None:
        """Test valid EvaluatorPromptContext creation."""
        context = EvaluatorPromptContext(
            user_query="What is Python?", submission="Python is a programming language..."
        )
        assert context.user_query == "What is Python?"
        assert context.submission == "Python is a programming language..."

    def test_empty_user_query_raises_error(self) -> None:
        """Test that empty user_query raises ValidationError."""
        with pytest.raises(ValidationError, match="user_query cannot be empty"):
            EvaluatorPromptContext(user_query="", submission="Valid submission")

    def test_whitespace_only_user_query_raises_error(self) -> None:
        """Test that whitespace-only user_query raises ValidationError."""
        with pytest.raises(ValidationError, match="user_query cannot be empty"):
            EvaluatorPromptContext(user_query="   ", submission="Valid submission")

    def test_empty_submission_raises_error(self) -> None:
        """Test that empty submission raises ValidationError."""
        with pytest.raises(ValidationError, match="submission cannot be empty"):
            EvaluatorPromptContext(user_query="What is Python?", submission="")

    def test_whitespace_only_submission_raises_error(self) -> None:
        """Test that whitespace-only submission raises ValidationError."""
        with pytest.raises(ValidationError, match="submission cannot be empty"):
            EvaluatorPromptContext(user_query="What is Python?", submission="   ")

    def test_validation_error_contains_field_name(self) -> None:
        """Test that ValidationError messages contain the field name."""
        try:
            EvaluatorPromptContext(user_query="", submission="Valid submission")
        except ValidationError as e:
            error_dict = e.errors()[0]
            assert "user_query" in str(error_dict)
            assert "cannot be empty" in str(error_dict)

    def test_multiline_user_query_accepted(self) -> None:
        """Test that multiline user_query is accepted."""
        context = EvaluatorPromptContext(user_query="Line 1\nLine 2\nLine 3", submission="Response to multiline query")
        assert "Line 1" in context.user_query
        assert "Line 2" in context.user_query
        assert "Line 3" in context.user_query

    def test_multiline_submission_accepted(self) -> None:
        """Test that multiline submission is accepted."""
        context = EvaluatorPromptContext(
            user_query="What is Python?",
            submission="Python is:\n- A programming language\n- Easy to learn\n- Powerful",
        )
        assert "Python is:" in context.submission
        assert "- A programming language" in context.submission
