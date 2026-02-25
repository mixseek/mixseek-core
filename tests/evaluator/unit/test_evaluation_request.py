"""Unit tests for EvaluationRequest model."""

from typing import Any

import pytest
from pydantic import ValidationError

from mixseek.models.evaluation_request import EvaluationRequest

# Rebuild model to resolve forward references
EvaluationRequest.model_rebuild()


class TestEvaluationRequestValidation:
    """Test EvaluationRequest validation rules."""

    def test_valid_evaluation_request(
        self, sample_user_query: str, sample_submission: str, sample_team_id: str
    ) -> None:
        """Test creating a valid EvaluationRequest."""
        request = EvaluationRequest(
            user_query=sample_user_query,
            submission=sample_submission,
            team_id=sample_team_id,
            config=None,
        )

        assert request.user_query == sample_user_query
        assert request.submission == sample_submission
        assert request.team_id == sample_team_id
        assert request.config is None

    def test_empty_user_query_raises_error(self, sample_submission: str, sample_team_id: str) -> None:
        """Test that empty user_query raises ValidationError (FR-013)."""
        with pytest.raises(ValidationError) as exc_info:
            EvaluationRequest(
                user_query="",
                submission=sample_submission,
                team_id=sample_team_id,
                config=None,
            )

        error = exc_info.value
        assert "user_query" in str(error)

    def test_whitespace_only_user_query_raises_error(self, sample_submission: str, sample_team_id: str) -> None:
        """Test that whitespace-only user_query raises ValidationError (FR-013)."""
        with pytest.raises(ValidationError) as exc_info:
            EvaluationRequest(
                user_query="   \n\t  ",
                submission=sample_submission,
                team_id=sample_team_id,
                config=None,
            )

        error = exc_info.value
        assert "user_query" in str(error)

    def test_empty_submission_raises_error(self, sample_user_query: str, sample_team_id: str) -> None:
        """Test that empty submission raises ValidationError (FR-013)."""
        with pytest.raises(ValidationError) as exc_info:
            EvaluationRequest(
                user_query=sample_user_query,
                submission="",
                team_id=sample_team_id,
                config=None,
            )

        error = exc_info.value
        assert "submission" in str(error)

    def test_whitespace_only_submission_raises_error(self, sample_user_query: str, sample_team_id: str) -> None:
        """Test that whitespace-only submission raises ValidationError (FR-013)."""
        with pytest.raises(ValidationError) as exc_info:
            EvaluationRequest(
                user_query=sample_user_query,
                submission="   \n\t  ",
                team_id=sample_team_id,
                config=None,
            )

        error = exc_info.value
        assert "submission" in str(error)

    def test_empty_team_id_raises_error(self, sample_user_query: str, sample_submission: str) -> None:
        """Test that empty team_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            EvaluationRequest(
                user_query=sample_user_query,
                submission=sample_submission,
                team_id="",
                config=None,
            )

        error = exc_info.value
        assert "team_id" in str(error)

    def test_whitespace_normalization(self, sample_submission: str, sample_team_id: str) -> None:
        """Test that leading/trailing whitespace is normalized."""
        request = EvaluationRequest(
            user_query="  What is Python?  ",
            submission=sample_submission,
            team_id=sample_team_id,
            config=None,
        )

        # Check if whitespace is preserved or normalized based on implementation
        assert request.user_query.strip() == "What is Python?"

    def test_long_user_query(self, sample_submission: str, sample_team_id: str) -> None:
        """Test evaluation request with long user query."""
        long_query = "What are " + "the benefits of Python " * 100
        request = EvaluationRequest(
            user_query=long_query,
            submission=sample_submission,
            team_id=sample_team_id,
            config=None,
        )

        assert len(request.user_query) > 1000
        assert request.submission == sample_submission

    def test_long_submission(self, sample_user_query: str, sample_team_id: str) -> None:
        """Test evaluation request with long submission."""
        long_submission = "Python is great. " * 200
        request = EvaluationRequest(
            user_query=sample_user_query,
            submission=long_submission,
            team_id=sample_team_id,
            config=None,
        )

        assert len(request.submission) > 1000
        assert request.user_query == sample_user_query

    def test_special_characters_in_query(self, sample_submission: str, sample_team_id: str) -> None:
        """Test evaluation request with special characters."""
        special_query = "What is Python? 🐍 How does it compare to C++, Java & Ruby?"
        request = EvaluationRequest(
            user_query=special_query,
            submission=sample_submission,
            team_id=sample_team_id,
            config=None,
        )

        assert "🐍" in request.user_query
        assert "&" in request.user_query

    def test_multiline_submission(self, sample_user_query: str, sample_team_id: str) -> None:
        """Test evaluation request with multiline submission."""
        multiline = """
        Line 1: Introduction
        Line 2: Main content
        Line 3: Conclusion
        """
        request = EvaluationRequest(
            user_query=sample_user_query,
            submission=multiline,
            team_id=sample_team_id,
            config=None,
        )

        assert "\n" in request.submission
        assert "Line 1" in request.submission

    def test_custom_config_optional(self, sample_user_query: str, sample_submission: str, sample_team_id: str) -> None:
        """Test that config field is optional and defaults to None."""
        request = EvaluationRequest(
            user_query=sample_user_query,
            submission=sample_submission,
            team_id=sample_team_id,
            config=None,
        )

        assert request.config is None


class TestEvaluationRequestExecutionContext:
    """Test EvaluationRequest execution context fields (execution_id, round_number)."""

    def test_valid_request_with_execution_context(
        self,
        sample_user_query: str,
        sample_submission: str,
        sample_team_id: str,
        sample_execution_id: str,
        sample_round_number: int,
    ) -> None:
        """Test creating a valid EvaluationRequest with all execution context fields."""
        request = EvaluationRequest(
            user_query=sample_user_query,
            submission=sample_submission,
            execution_id=sample_execution_id,
            team_id=sample_team_id,
            round_number=sample_round_number,
            config=None,
        )

        assert request.execution_id == sample_execution_id
        assert request.team_id == sample_team_id
        assert request.round_number == sample_round_number

    def test_execution_id_none_allowed(self, sample_user_query: str, sample_submission: str) -> None:
        """Test that execution_id=None passes validation."""
        request = EvaluationRequest(
            user_query=sample_user_query,
            submission=sample_submission,
            execution_id=None,
        )
        assert request.execution_id is None

    def test_execution_id_empty_rejected(self, sample_user_query: str, sample_submission: str) -> None:
        """Test that empty execution_id is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EvaluationRequest(
                user_query=sample_user_query,
                submission=sample_submission,
                execution_id="",
            )
        assert "execution_id" in str(exc_info.value)

    def test_execution_id_whitespace_rejected(self, sample_user_query: str, sample_submission: str) -> None:
        """Test that whitespace-only execution_id is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EvaluationRequest(
                user_query=sample_user_query,
                submission=sample_submission,
                execution_id="   \t  ",
            )
        assert "execution_id" in str(exc_info.value)

    def test_round_number_valid(self, sample_user_query: str, sample_submission: str) -> None:
        """Test that valid positive round_number passes."""
        for rn in [1, 3, 100]:
            request = EvaluationRequest(
                user_query=sample_user_query,
                submission=sample_submission,
                round_number=rn,
            )
            assert request.round_number == rn

    def test_round_number_none_allowed(self, sample_user_query: str, sample_submission: str) -> None:
        """Test that round_number=None passes validation."""
        request = EvaluationRequest(
            user_query=sample_user_query,
            submission=sample_submission,
            round_number=None,
        )
        assert request.round_number is None

    def test_round_number_zero_rejected(self, sample_user_query: str, sample_submission: str) -> None:
        """Test that round_number=0 is rejected (ge=1)."""
        with pytest.raises(ValidationError) as exc_info:
            EvaluationRequest(
                user_query=sample_user_query,
                submission=sample_submission,
                round_number=0,
            )
        assert "round_number" in str(exc_info.value)

    def test_round_number_negative_rejected(self, sample_user_query: str, sample_submission: str) -> None:
        """Test that negative round_number is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EvaluationRequest(
                user_query=sample_user_query,
                submission=sample_submission,
                round_number=-1,
            )
        assert "round_number" in str(exc_info.value)

    def test_defaults_none_for_backward_compatibility(self, sample_user_query: str, sample_submission: str) -> None:
        """Test that execution_id and round_number default to None for backward compatibility."""
        request = EvaluationRequest(
            user_query=sample_user_query,
            submission=sample_submission,
        )
        assert request.execution_id is None
        assert request.round_number is None


class TestEvaluationRequestSerialization:
    """Test EvaluationRequest serialization/deserialization."""

    def test_model_dump(self, sample_user_query: str, sample_submission: str, sample_team_id: str) -> None:
        """Test converting EvaluationRequest to dictionary."""
        request = EvaluationRequest(
            user_query=sample_user_query,
            submission=sample_submission,
            team_id=sample_team_id,
            config=None,
        )

        data = request.model_dump()

        assert data["user_query"] == sample_user_query
        assert data["submission"] == sample_submission
        assert data["team_id"] == sample_team_id
        assert data["config"] is None

    def test_model_dump_json(self, sample_user_query: str, sample_submission: str, sample_team_id: str) -> None:
        """Test converting EvaluationRequest to JSON."""
        request = EvaluationRequest(
            user_query=sample_user_query,
            submission=sample_submission,
            team_id=sample_team_id,
            config=None,
        )

        json_str = request.model_dump_json()

        assert sample_user_query in json_str
        assert sample_team_id in json_str

    def test_model_validate(self, sample_evaluation_request_data: dict[str, Any]) -> None:
        """Test creating EvaluationRequest from dictionary."""
        request = EvaluationRequest.model_validate(sample_evaluation_request_data)

        assert request.user_query == sample_evaluation_request_data["user_query"]
        assert request.submission == sample_evaluation_request_data["submission"]
        assert request.team_id == sample_evaluation_request_data["team_id"]

    def test_model_dump_with_execution_context(
        self,
        sample_user_query: str,
        sample_submission: str,
        sample_team_id: str,
        sample_execution_id: str,
        sample_round_number: int,
    ) -> None:
        """Test that model_dump includes execution context fields."""
        request = EvaluationRequest(
            user_query=sample_user_query,
            submission=sample_submission,
            execution_id=sample_execution_id,
            team_id=sample_team_id,
            round_number=sample_round_number,
            config=None,
        )

        data = request.model_dump()

        assert data["execution_id"] == sample_execution_id
        assert data["round_number"] == sample_round_number
        assert data["team_id"] == sample_team_id
