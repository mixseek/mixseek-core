"""Unit tests for ADKResearchAgent."""

import pytest

# Skip entire module if google-adk is not installed
pytest.importorskip("google.adk")

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from examples.custom_agents.adk_research.agent import ADKResearchAgent
from examples.custom_agents.adk_research.models import SearchResult
from mixseek.models.member_agent import MemberAgentConfig, ResultStatus


class TestADKResearchAgentInit:
    """Tests for ADKResearchAgent initialization."""

    def test_init_with_valid_config(self, sample_member_agent_config: MemberAgentConfig) -> None:
        """Test successful initialization with valid config."""
        agent = ADKResearchAgent(sample_member_agent_config)

        assert agent.config == sample_member_agent_config
        assert agent.adk_config.gemini_model == "gemini-2.5-flash"
        assert agent.adk_config.temperature == 0.7
        assert agent.adk_config.researcher_count == 3

    def test_init_missing_adk_settings(self, sample_member_agent_config_missing_settings: MemberAgentConfig) -> None:
        """Test that missing ADK settings raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ADKResearchAgent(sample_member_agent_config_missing_settings)

        assert "Missing [agent.metadata.tool_settings.adk_research]" in str(exc_info.value)


class TestADKResearchAgentHelpers:
    """Tests for ADKResearchAgent helper methods."""

    def test_create_researcher(self, sample_member_agent_config: MemberAgentConfig) -> None:
        """Test _create_researcher creates valid LlmAgent."""
        agent = ADKResearchAgent(sample_member_agent_config)
        researcher = agent._create_researcher(name="test_researcher", focus="AI trends")

        assert researcher.name == "test_researcher"
        assert researcher.model == "gemini-2.5-flash"
        assert "google_search" in str(researcher.tools)

    def test_create_researcher_without_focus(self, sample_member_agent_config: MemberAgentConfig) -> None:
        """Test _create_researcher without focus area."""
        agent = ADKResearchAgent(sample_member_agent_config)
        researcher = agent._create_researcher()

        assert researcher.name == "researcher"
        assert researcher.model == "gemini-2.5-flash"

    def test_create_summarizer(self, sample_member_agent_config: MemberAgentConfig) -> None:
        """Test _create_summarizer creates valid LlmAgent."""
        agent = ADKResearchAgent(sample_member_agent_config)
        summarizer = agent._create_summarizer()

        assert summarizer.name == "summarizer"
        assert summarizer.model == "gemini-2.5-flash"
        # Summarizer should have no tools
        assert not summarizer.tools or len(summarizer.tools) == 0

    def test_build_pipeline(self, sample_member_agent_config: MemberAgentConfig) -> None:
        """Test _build_pipeline creates valid SequentialAgent."""
        agent = ADKResearchAgent(sample_member_agent_config)
        pipeline = agent._build_pipeline()

        assert pipeline.name == "deep_research_pipeline"
        assert len(pipeline.sub_agents) == 2  # ParallelAgent + Summarizer

    def test_parse_sources_extracts_from_grounding_metadata(
        self, sample_member_agent_config: MemberAgentConfig
    ) -> None:
        """Test _parse_sources extracts sources from grounding metadata (FR-004)."""
        agent = ADKResearchAgent(sample_member_agent_config)

        response = {
            "content": "Research findings here",
            "events": [],
            "grounding_metadata": [
                {
                    "sources": [
                        {"url": "https://example.com/article1", "title": "AI Trends 2025"},
                        {"url": "https://example.com/article2", "title": "ML Guide"},
                    ]
                }
            ],
        }

        sources = agent._parse_sources(response)

        assert len(sources) == 2
        assert all(isinstance(s, SearchResult) for s in sources)
        assert sources[0].url == "https://example.com/article1"
        assert sources[0].title == "AI Trends 2025"
        assert sources[1].url == "https://example.com/article2"
        assert sources[1].title == "ML Guide"

    def test_parse_sources_empty_grounding_metadata(self, sample_member_agent_config: MemberAgentConfig) -> None:
        """Test _parse_sources with no grounding metadata returns empty list."""
        agent = ADKResearchAgent(sample_member_agent_config)

        response = {"content": "No sources here", "events": [], "grounding_metadata": []}

        sources = agent._parse_sources(response)

        assert len(sources) == 0

    def test_parse_sources_respects_limit(self, sample_member_agent_config: MemberAgentConfig) -> None:
        """Test _parse_sources respects search_result_limit."""
        agent = ADKResearchAgent(sample_member_agent_config)
        agent.adk_config.search_result_limit = 2

        response = {
            "content": "Many sources",
            "events": [],
            "grounding_metadata": [
                {
                    "sources": [
                        {"url": "https://a.com", "title": "A"},
                        {"url": "https://b.com", "title": "B"},
                        {"url": "https://c.com", "title": "C"},
                        {"url": "https://d.com", "title": "D"},
                    ]
                }
            ],
        }

        sources = agent._parse_sources(response)

        assert len(sources) == 2


class TestADKResearchAgentErrorHandling:
    """Tests for ADKResearchAgent error handling."""

    def test_classify_error_auth(self, sample_member_agent_config: MemberAgentConfig) -> None:
        """Test error classification for authentication errors."""
        agent = ADKResearchAgent(sample_member_agent_config)

        code, message = agent._classify_error(Exception("authentication failed"))
        assert code == "AUTH_ERROR"

        code, message = agent._classify_error(Exception("Invalid API key"))
        assert code == "AUTH_ERROR"

        code, message = agent._classify_error(Exception("401 Unauthorized"))
        assert code == "AUTH_ERROR"

    def test_classify_error_rate_limit(self, sample_member_agent_config: MemberAgentConfig) -> None:
        """Test error classification for rate limit errors."""
        agent = ADKResearchAgent(sample_member_agent_config)

        code, message = agent._classify_error(Exception("Rate limit exceeded"))
        assert code == "RATE_LIMIT"

        code, message = agent._classify_error(Exception("429 Too Many Requests"))
        assert code == "RATE_LIMIT"

        code, message = agent._classify_error(Exception("Quota exceeded"))
        assert code == "RATE_LIMIT"

    def test_classify_error_timeout(self, sample_member_agent_config: MemberAgentConfig) -> None:
        """Test error classification for timeout errors."""
        agent = ADKResearchAgent(sample_member_agent_config)

        code, message = agent._classify_error(Exception("Request timeout"))
        assert code == "TIMEOUT"

        code, message = agent._classify_error(Exception("Operation timed out"))
        assert code == "TIMEOUT"

    def test_classify_error_network(self, sample_member_agent_config: MemberAgentConfig) -> None:
        """Test error classification for network errors."""
        agent = ADKResearchAgent(sample_member_agent_config)

        code, message = agent._classify_error(Exception("Network error occurred"))
        assert code == "NETWORK_ERROR"

        code, message = agent._classify_error(Exception("Connection refused"))
        assert code == "NETWORK_ERROR"

    def test_classify_error_no_results(self, sample_member_agent_config: MemberAgentConfig) -> None:
        """Test error classification for no results."""
        agent = ADKResearchAgent(sample_member_agent_config)

        code, message = agent._classify_error(Exception("No results found"))
        assert code == "SEARCH_NO_RESULTS"

    def test_classify_error_unknown(self, sample_member_agent_config: MemberAgentConfig) -> None:
        """Test error classification for unknown errors."""
        agent = ADKResearchAgent(sample_member_agent_config)

        code, message = agent._classify_error(Exception("Something weird happened"))
        assert code == "UNKNOWN_ERROR"

    @pytest.mark.asyncio
    async def test_handle_error_returns_error_result(self, sample_member_agent_config: MemberAgentConfig) -> None:
        """Test _handle_error returns proper error result with content (FR-006)."""
        agent = ADKResearchAgent(sample_member_agent_config)

        error = Exception("Rate limit exceeded")
        result = await agent._handle_error(error)

        assert result.status == ResultStatus.ERROR
        assert result.error_code == "RATE_LIMIT"
        # FR-006: Error content must include natural-language explanation
        assert "RATE_LIMIT" in result.content
        assert "Troubleshooting" in result.content
        assert result.metadata["error_code"] == "RATE_LIMIT"
        assert "Rate limit exceeded" in result.metadata["error_message"]


class TestADKResearchAgentExecute:
    """Tests for ADKResearchAgent execute method."""

    @pytest.mark.asyncio
    async def test_execute_single_search_success(
        self,
        sample_member_agent_config: MemberAgentConfig,
        mock_adk_response: dict[str, Any],
    ) -> None:
        """Test successful single search execution."""
        agent = ADKResearchAgent(sample_member_agent_config)

        with patch("examples.custom_agents.adk_research.agent.ADKRunnerWrapper") as mock_runner_cls:
            mock_instance = MagicMock()
            mock_instance.run_once = AsyncMock(return_value=mock_adk_response)
            mock_instance.cleanup = AsyncMock()
            mock_runner_cls.return_value = mock_instance

            result = await agent.execute("What are AI trends?")

        assert result.status == ResultStatus.SUCCESS
        assert "Research Summary" in result.content
        assert result.metadata["mode"] == "single_search"
        assert result.execution_time_ms is not None
        assert result.execution_time_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_deep_research_kwarg(
        self,
        sample_member_agent_config: MemberAgentConfig,
        mock_adk_response: dict[str, Any],
    ) -> None:
        """Test deep research mode via kwarg."""
        agent = ADKResearchAgent(sample_member_agent_config)

        with patch("examples.custom_agents.adk_research.agent.ADKRunnerWrapper") as mock_runner_cls:
            mock_instance = MagicMock()
            mock_instance.run_once = AsyncMock(return_value=mock_adk_response)
            mock_instance.cleanup = AsyncMock()
            mock_runner_cls.return_value = mock_instance

            result = await agent.execute("What are AI trends?", deep_research=True)

        assert result.status == ResultStatus.SUCCESS
        assert result.metadata["mode"] == "deep_research"

    @pytest.mark.asyncio
    async def test_execute_deep_research_context(
        self,
        sample_member_agent_config: MemberAgentConfig,
        mock_adk_response: dict[str, Any],
    ) -> None:
        """Test deep research mode via context."""
        agent = ADKResearchAgent(sample_member_agent_config)

        with patch("examples.custom_agents.adk_research.agent.ADKRunnerWrapper") as mock_runner_cls:
            mock_instance = MagicMock()
            mock_instance.run_once = AsyncMock(return_value=mock_adk_response)
            mock_instance.cleanup = AsyncMock()
            mock_runner_cls.return_value = mock_instance

            result = await agent.execute("What are AI trends?", context={"deep_research": True})

        assert result.status == ResultStatus.SUCCESS
        assert result.metadata["mode"] == "deep_research"

    @pytest.mark.asyncio
    async def test_execute_error_handling(self, sample_member_agent_config: MemberAgentConfig) -> None:
        """Test error handling during execution."""
        agent = ADKResearchAgent(sample_member_agent_config)

        with patch("examples.custom_agents.adk_research.agent.ADKRunnerWrapper") as mock_runner_cls:
            mock_instance = MagicMock()
            mock_instance.run_once = AsyncMock(side_effect=Exception("Rate limit exceeded"))
            mock_instance.cleanup = AsyncMock()
            mock_runner_cls.return_value = mock_instance

            result = await agent.execute("What are AI trends?")

        assert result.status == ResultStatus.ERROR
        assert result.error_code == "RATE_LIMIT"

    @pytest.mark.asyncio
    async def test_execute_empty_content_error(self, sample_member_agent_config: MemberAgentConfig) -> None:
        """Test error when response has no content."""
        agent = ADKResearchAgent(sample_member_agent_config)

        with patch("examples.custom_agents.adk_research.agent.ADKRunnerWrapper") as mock_runner_cls:
            mock_instance = MagicMock()
            mock_instance.run_once = AsyncMock(return_value={"content": "", "events": []})
            mock_instance.cleanup = AsyncMock()
            mock_runner_cls.return_value = mock_instance

            result = await agent.execute("What are AI trends?")

        assert result.status == ResultStatus.ERROR

    @pytest.mark.asyncio
    async def test_execute_sources_in_metadata(
        self,
        sample_member_agent_config: MemberAgentConfig,
        mock_adk_response: dict[str, Any],
    ) -> None:
        """Test that sources are properly included in metadata."""
        agent = ADKResearchAgent(sample_member_agent_config)

        with patch("examples.custom_agents.adk_research.agent.ADKRunnerWrapper") as mock_runner_cls:
            mock_instance = MagicMock()
            mock_instance.run_once = AsyncMock(return_value=mock_adk_response)
            mock_instance.cleanup = AsyncMock()
            mock_runner_cls.return_value = mock_instance

            result = await agent.execute("What are AI trends?")

        assert "sources" in result.metadata
        assert "source_count" in result.metadata
        # The mock response contains URLs that should be extracted
        assert isinstance(result.metadata["sources"], list)


class TestADKResearchAgentCleanup:
    """Tests for ADKResearchAgent cleanup method."""

    @pytest.mark.asyncio
    async def test_cleanup(self, sample_member_agent_config: MemberAgentConfig) -> None:
        """Test cleanup method cleans up resources."""
        agent = ADKResearchAgent(sample_member_agent_config)

        # Simulate having an active runner
        mock_runner = MagicMock()
        mock_runner.cleanup = AsyncMock()
        agent._runner = mock_runner

        await agent.cleanup()

        assert agent._runner is None
        mock_runner.cleanup.assert_called_once()
