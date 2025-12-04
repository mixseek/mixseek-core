"""Pydantic models for Google ADK Research Agent.

This module provides data models for the ADK Research Agent implementation,
following Article 9 (Data Accuracy Mandate) and Article 16 (Type Safety) compliance.
"""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ADKAgentConfig(BaseModel):
    """Google ADK agent configuration (Article 9 compliant).

    All settings are explicitly defined with no implicit fallbacks.
    Values should be provided via TOML configuration file.

    Attributes:
        gemini_model: Gemini model name for ADK agents (e.g., gemini-2.5-flash).
        temperature: Generation temperature (0.0 = deterministic, 2.0 = creative).
        max_output_tokens: Maximum tokens per response.
        search_result_limit: Maximum number of search results to process.
        researcher_count: Number of parallel researcher agents for Deep Research.
        timeout_seconds: Request timeout in seconds.
        deep_research_default: Enable Deep Research mode by default.
        structured_output: Enable structured output in metadata.
        debug_mode: Enable debug mode to log ADK event and grounding data via standard logging.
        persist_metadata: Persist metadata to JSON for team/orchestration access.
    """

    gemini_model: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model name for ADK internal agents",
    )
    temperature: float = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        description="Generation temperature (0.0 = deterministic, 2.0 = creative)",
    )
    max_output_tokens: int = Field(
        default=8192,
        gt=0,
        le=65536,
        description="Maximum tokens per response",
    )
    search_result_limit: int = Field(
        default=15,
        ge=1,
        le=50,
        description="Maximum number of search results to process",
    )
    researcher_count: int = Field(
        default=5,
        ge=1,
        le=5,
        description="Number of parallel researcher agents for Deep Research",
    )
    timeout_seconds: int = Field(
        default=120,
        gt=0,
        le=300,
        description="Request timeout in seconds (Deep Research requires longer)",
    )
    deep_research_default: bool = Field(
        default=True,
        description="Enable Deep Research mode by default (parallel multi-agent search)",
    )
    structured_output: bool = Field(
        default=True,
        description="Enable structured output (ResearchReport) in metadata",
    )
    debug_mode: bool = Field(
        default=False,
        description="Enable debug mode to log ADK event and grounding data via standard logging",
    )
    persist_metadata: bool = Field(
        default=False,
        description="Persist metadata (sources, structured_report) to JSON for team/orchestration access",
    )
    append_sources_to_content: bool = Field(
        default=True,
        description="Append sources section to markdown content (enables source visibility in UI)",
    )

    @field_validator("gemini_model")
    @classmethod
    def validate_gemini_model(cls, v: str) -> str:
        """Validate that gemini_model is a supported model.

        Supported models for google_search tool (Search grounding):
        - gemini-2.0-flash
        - gemini-2.5-flash (default, recommended)
        - gemini-2.5-flash-lite
        - gemini-2.5-pro
        - gemini-3-pro-preview
        """
        supported_prefixes = (
            "gemini-2.0-flash",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-3-pro",
        )
        if not v.startswith(supported_prefixes):
            raise ValueError(
                f"Unsupported model '{v}'. Model must start with one of: "
                f"{', '.join(supported_prefixes)}. "
                f"google_search tool requires Gemini 2.0+ models."
            )
        return v

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "gemini_model": "gemini-2.5-flash",
                    "temperature": 0.5,
                    "max_output_tokens": 8192,
                    "search_result_limit": 15,
                    "researcher_count": 5,
                    "timeout_seconds": 60,
                    "deep_research_default": True,
                    "structured_output": True,
                }
            ]
        },
    )


class SearchResult(BaseModel):
    """Single search result from google_search tool (FR-004).

    Used for source tracking in MemberAgentResult.metadata.

    Attributes:
        url: Source URL.
        title: Page title.
        snippet: Text excerpt from the source.
        timestamp: When the result was retrieved.
    """

    url: str = Field(..., description="Source URL")
    title: str = Field(..., description="Page title")
    snippet: str = Field(default="", description="Text excerpt from the source")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the result was retrieved",
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL format: {v}. URL must start with http:// or https://")
        return v

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "url": "https://example.com/article",
                    "title": "Example Article Title",
                    "snippet": "This is an excerpt from the article...",
                    "timestamp": "2025-01-01T12:00:00Z",
                }
            ]
        },
    )


class ResearchReport(BaseModel):
    """Deep Research pipeline output (FR-003).

    Structured output from the multi-agent research pipeline.

    Attributes:
        summary: Executive summary of research findings.
        key_findings: List of key findings from the research.
        sources: List of SearchResult sources used.
        patterns: Detected patterns across sources.
        recommendations: Actionable recommendations based on research.
    """

    summary: str = Field(..., description="Executive summary of research findings")
    key_findings: list[str] = Field(
        default_factory=list,
        description="List of key findings from the research",
    )
    sources: list[SearchResult] = Field(
        default_factory=list,
        description="List of SearchResult sources used",
    )
    patterns: list[str] = Field(
        default_factory=list,
        description="Detected patterns across sources",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Actionable recommendations based on research",
    )

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "summary": "Research summary about AI trends...",
                    "key_findings": [
                        "Finding 1: LLMs are becoming multimodal",
                        "Finding 2: Agent frameworks are evolving",
                    ],
                    "sources": [
                        {
                            "url": "https://example.com/article1",
                            "title": "AI Trends 2025",
                            "snippet": "Excerpt...",
                            "timestamp": "2025-01-01T12:00:00Z",
                        }
                    ],
                    "patterns": ["Pattern 1: Convergence of AI capabilities"],
                    "recommendations": ["Recommendation 1: Adopt multi-agent architectures"],
                }
            ]
        },
    )


class ResearchReportSchema(BaseModel):
    """Gemini JSON mode output schema for summarizer agent.

    This schema is used with response_mime_type="application/json"
    to have LLM directly output structured JSON.

    Note: Unlike ResearchReport, this does NOT include 'sources' field
    as sources are extracted from grounding_metadata separately.

    Attributes:
        executive_summary: Brief overview of research findings.
        key_findings: List of main discoveries from the research.
        patterns: Common themes and trends identified across sources.
        recommendations: Actionable insights based on research findings.
    """

    executive_summary: str = Field(description="Brief overview of research findings (3-5 sentences)")
    key_findings: list[str] = Field(
        default_factory=list,
        description="List of main discoveries from the research",
    )
    patterns: list[str] = Field(
        default_factory=list,
        description="Common themes and trends identified across sources",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Actionable insights based on research findings",
    )

    # Note: Do NOT use extra="forbid" here as it generates additionalProperties
    # in JSON Schema, which Gemini API does not support.
    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


# Error codes for ADK agent operations (FR-006)
ADKErrorCode = Literal[
    "AUTH_ERROR",
    "RATE_LIMIT",
    "TIMEOUT",
    "NETWORK_ERROR",
    "SEARCH_NO_RESULTS",
    "PIPELINE_ERROR",
    "CONFIG_ERROR",
    "UNKNOWN_ERROR",
]


__all__ = [
    "ADKAgentConfig",
    "SearchResult",
    "ResearchReport",
    "ResearchReportSchema",
    "ADKErrorCode",
]
