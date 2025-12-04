"""Tests for ADK Research Agent Pydantic models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from examples.custom_agents.adk_research.models import (
    ADKAgentConfig,
    ResearchReport,
    ResearchReportSchema,
    SearchResult,
)


class TestADKAgentConfig:
    """Tests for ADKAgentConfig model."""

    def test_valid_config(self, sample_adk_config: ADKAgentConfig) -> None:
        """Test creating a valid ADKAgentConfig."""
        assert sample_adk_config.gemini_model == "gemini-2.5-flash"
        assert sample_adk_config.temperature == 0.7
        assert sample_adk_config.max_output_tokens == 4096
        assert sample_adk_config.search_result_limit == 10
        assert sample_adk_config.researcher_count == 3
        assert sample_adk_config.timeout_seconds == 30

    def test_default_values(self) -> None:
        """Test default values are applied correctly."""
        config = ADKAgentConfig()
        assert config.gemini_model == "gemini-2.5-flash"
        assert config.temperature == 0.5
        assert config.max_output_tokens == 8192
        assert config.search_result_limit == 15
        assert config.researcher_count == 5
        assert config.timeout_seconds == 120

    def test_valid_gemini_models(self) -> None:
        """Test various supported Gemini model names."""
        valid_models = [
            "gemini-2.0-flash",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.5-pro",
            "gemini-3-pro-preview",
        ]
        for model in valid_models:
            config = ADKAgentConfig(gemini_model=model)
            assert config.gemini_model == model

    def test_invalid_gemini_model(self) -> None:
        """Test that unsupported models raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ADKAgentConfig(gemini_model="gpt-4")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "gemini_model" in str(errors[0]["loc"])

    def test_temperature_bounds(self) -> None:
        """Test temperature validation bounds."""
        # Valid temperatures
        ADKAgentConfig(temperature=0.0)
        ADKAgentConfig(temperature=2.0)
        ADKAgentConfig(temperature=1.0)

        # Invalid temperatures
        with pytest.raises(ValidationError):
            ADKAgentConfig(temperature=-0.1)

        with pytest.raises(ValidationError):
            ADKAgentConfig(temperature=2.1)

    def test_max_output_tokens_bounds(self) -> None:
        """Test max_output_tokens validation bounds."""
        ADKAgentConfig(max_output_tokens=1)
        ADKAgentConfig(max_output_tokens=65536)

        with pytest.raises(ValidationError):
            ADKAgentConfig(max_output_tokens=0)

        with pytest.raises(ValidationError):
            ADKAgentConfig(max_output_tokens=65537)

    def test_search_result_limit_bounds(self) -> None:
        """Test search_result_limit validation bounds."""
        ADKAgentConfig(search_result_limit=1)
        ADKAgentConfig(search_result_limit=50)

        with pytest.raises(ValidationError):
            ADKAgentConfig(search_result_limit=0)

        with pytest.raises(ValidationError):
            ADKAgentConfig(search_result_limit=51)

    def test_researcher_count_bounds(self) -> None:
        """Test researcher_count validation bounds."""
        ADKAgentConfig(researcher_count=1)
        ADKAgentConfig(researcher_count=5)

        with pytest.raises(ValidationError):
            ADKAgentConfig(researcher_count=0)

        with pytest.raises(ValidationError):
            ADKAgentConfig(researcher_count=6)

    def test_timeout_seconds_bounds(self) -> None:
        """Test timeout_seconds validation bounds."""
        ADKAgentConfig(timeout_seconds=1)
        ADKAgentConfig(timeout_seconds=300)

        with pytest.raises(ValidationError):
            ADKAgentConfig(timeout_seconds=0)

        with pytest.raises(ValidationError):
            ADKAgentConfig(timeout_seconds=301)

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected (Article 9 compliance)."""
        with pytest.raises(ValidationError):
            ADKAgentConfig(unknown_field="value")  # type: ignore[call-arg]


class TestSearchResult:
    """Tests for SearchResult model."""

    def test_valid_search_result(self) -> None:
        """Test creating a valid SearchResult."""
        result = SearchResult(
            url="https://example.com/article",
            title="Test Article",
            snippet="This is a test snippet",
        )
        assert result.url == "https://example.com/article"
        assert result.title == "Test Article"
        assert result.snippet == "This is a test snippet"
        assert isinstance(result.timestamp, datetime)

    def test_url_validation_https(self) -> None:
        """Test URL validation for HTTPS."""
        result = SearchResult(
            url="https://example.com/path",
            title="Test",
        )
        assert result.url.startswith("https://")

    def test_url_validation_http(self) -> None:
        """Test URL validation for HTTP."""
        result = SearchResult(
            url="http://example.com/path",
            title="Test",
        )
        assert result.url.startswith("http://")

    def test_invalid_url(self) -> None:
        """Test that invalid URLs raise validation error."""
        with pytest.raises(ValidationError):
            SearchResult(
                url="ftp://example.com/path",
                title="Test",
            )

        with pytest.raises(ValidationError):
            SearchResult(
                url="example.com/path",
                title="Test",
            )

    def test_default_timestamp(self) -> None:
        """Test that timestamp defaults to current time."""
        before = datetime.now(UTC)
        result = SearchResult(url="https://example.com", title="Test")
        after = datetime.now(UTC)

        assert before <= result.timestamp <= after

    def test_default_snippet(self) -> None:
        """Test that snippet defaults to empty string."""
        result = SearchResult(url="https://example.com", title="Test")
        assert result.snippet == ""


class TestResearchReport:
    """Tests for ResearchReport model."""

    def test_valid_research_report(self, sample_search_results: list[SearchResult]) -> None:
        """Test creating a valid ResearchReport."""
        report = ResearchReport(
            summary="This is a research summary",
            key_findings=["Finding 1", "Finding 2"],
            sources=sample_search_results,
            patterns=["Pattern 1"],
            recommendations=["Recommendation 1"],
        )
        assert report.summary == "This is a research summary"
        assert len(report.key_findings) == 2
        assert len(report.sources) == 2
        assert len(report.patterns) == 1
        assert len(report.recommendations) == 1

    def test_minimal_research_report(self) -> None:
        """Test ResearchReport with only required fields."""
        report = ResearchReport(summary="Minimal summary")
        assert report.summary == "Minimal summary"
        assert report.key_findings == []
        assert report.sources == []
        assert report.patterns == []
        assert report.recommendations == []

    def test_empty_lists_allowed(self) -> None:
        """Test that empty lists are valid for optional fields."""
        report = ResearchReport(
            summary="Test",
            key_findings=[],
            sources=[],
            patterns=[],
            recommendations=[],
        )
        assert len(report.key_findings) == 0
        assert len(report.sources) == 0

    def test_summary_required(self) -> None:
        """Test that summary is a required field."""
        with pytest.raises(ValidationError):
            ResearchReport()  # type: ignore[call-arg]


class TestResearchReportSchema:
    """Tests for ResearchReportSchema model (Gemini JSON mode)."""

    def test_valid_schema(self) -> None:
        """Test creating a valid ResearchReportSchema."""
        schema = ResearchReportSchema(
            executive_summary="This is a research summary",
            key_findings=["Finding 1", "Finding 2"],
            patterns=["Pattern 1"],
            recommendations=["Recommendation 1"],
        )
        assert schema.executive_summary == "This is a research summary"
        assert len(schema.key_findings) == 2
        assert len(schema.patterns) == 1
        assert len(schema.recommendations) == 1

    def test_default_values(self) -> None:
        """Test default values for optional fields."""
        schema = ResearchReportSchema(executive_summary="Minimal summary")
        assert schema.executive_summary == "Minimal summary"
        assert schema.key_findings == []
        assert schema.patterns == []
        assert schema.recommendations == []

    def test_executive_summary_required(self) -> None:
        """Test that executive_summary is a required field."""
        with pytest.raises(ValidationError):
            ResearchReportSchema()  # type: ignore[call-arg]

    def test_extra_fields_allowed_for_gemini_compatibility(self) -> None:
        """Test that extra fields are allowed (Gemini API doesn't support additionalProperties).

        Note: extra="forbid" was removed because Gemini API returns 400 INVALID_ARGUMENT
        when JSON Schema contains additionalProperties field.
        """
        # This should NOT raise - extra fields are silently ignored
        schema = ResearchReportSchema(
            executive_summary="Test",
            unknown_field="value",  # type: ignore[call-arg]
        )
        assert schema.executive_summary == "Test"
        # unknown_field is ignored, not stored
        assert not hasattr(schema, "unknown_field")

    def test_no_sources_field(self) -> None:
        """Test that sources field is NOT in schema (sources come from grounding)."""
        schema = ResearchReportSchema(executive_summary="Test")
        # sources should not be an attribute of the schema
        assert "sources" not in schema.model_fields
