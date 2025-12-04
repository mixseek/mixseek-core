# Implementation Plan: Google ADK Search Agent Sample

**Feature Branch**: `134-custom-member-adk`
**Created**: 2025-11-25
**Status**: Ready for Implementation

## Overview

This plan implements a sample Google ADK (Agent Development Kit) integration demonstrating how to wrap ADK's multi-agent system within the MixSeek-Core `BaseMemberAgent` interface. The implementation follows the bitbank pattern as reference.

## File Structure

```
examples/custom_agents/adk_research/
├── __init__.py              # Module exports
├── agent.py                 # ADKResearchAgent(BaseMemberAgent)
├── models.py                # Pydantic models (ADKAgentConfig, SearchResult, ResearchReport)
├── runner.py                # ADK runner wrapper (InMemoryRunner management)
├── adk_research_agent.toml  # Sample TOML configuration
├── README.md                # Usage documentation
└── tests/
    ├── __init__.py
    ├── conftest.py          # Shared fixtures
    ├── test_agent.py        # Unit tests (mocked ADK)
    ├── test_models.py       # Model validation tests
    └── test_e2e.py          # E2E tests (@pytest.mark.e2e)
```

## Class Design

### 1. ADKResearchAgent (agent.py)

```python
class ADKResearchAgent(BaseMemberAgent):
    """Google ADK Research Agent wrapping ADK multi-agent system."""

    def __init__(self, config: MemberAgentConfig) -> None:
        """Initialize with MemberAgentConfig, extract ADK settings from metadata."""

    async def execute(self, task: str, context: dict[str, Any] | None = None, **kwargs: Any) -> MemberAgentResult:
        """Execute research task using ADK pipeline."""

    def _build_pipeline(self) -> SequentialAgent:
        """Build Deep Research pipeline (3 parallel + 1 summarizer)."""

    def _create_researcher(self, name: str, focus: str) -> LlmAgent:
        """Create a single research LlmAgent with google_search tool."""

    def _create_summarizer(self) -> LlmAgent:
        """Create summarizer agent for result synthesis."""

    def _parse_sources(self, response: Any) -> list[dict[str, Any]]:
        """Extract source URLs/titles from ADK response for metadata."""

    async def _handle_error(self, error: Exception) -> MemberAgentResult:
        """Generate structured error info + LLM-interpreted error message."""
```

### 2. Pydantic Models (models.py)

```python
class ADKAgentConfig(BaseModel):
    """Google ADK agent configuration (Article 9 compliant)."""
    gemini_model: str = Field(default="gemini-2.5-flash", description="Gemini model name")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_output_tokens: int = Field(default=4096, gt=0)
    search_result_limit: int = Field(default=10, ge=1, le=50)
    researcher_count: int = Field(default=3, ge=1, le=5)
    timeout_seconds: int = Field(default=30, gt=0)

class SearchResult(BaseModel):
    """Single search result from google_search tool."""
    url: str
    title: str
    snippet: str
    timestamp: datetime

class ResearchReport(BaseModel):
    """Deep Research pipeline output."""
    summary: str
    key_findings: list[str]
    sources: list[SearchResult]
    patterns: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
```

### 3. Runner Wrapper (runner.py)

```python
class ADKRunnerWrapper:
    """Wrapper for Google ADK InMemoryRunner lifecycle management."""

    def __init__(self, agent: Agent, app_name: str) -> None:
        """Initialize runner with agent."""

    async def run(self, user_id: str, message: str) -> Any:
        """Execute agent with session management."""

    async def cleanup(self) -> None:
        """Clean up session resources."""
```

## Implementation Phases

### Phase 1: Foundation (models.py, runner.py)

**Tasks:**
1. Create `models.py` with Pydantic models
   - `ADKAgentConfig` with all config fields
   - `SearchResult` for source tracking
   - `ResearchReport` for structured output
   - Full type annotations (Article 16)

2. Create `runner.py` with ADK runner wrapper
   - `ADKRunnerWrapper` class
   - Session lifecycle management
   - Error handling for runner operations

3. Create `__init__.py` with exports

**Acceptance:**
- All models pass mypy strict mode
- Models have proper validators
- Runner wrapper handles basic operations

### Phase 2: Core Agent (agent.py)

**Tasks:**
1. Implement `ADKResearchAgent.__init__`
   - Extract config from `config.metadata.tool_settings.adk_research`
   - Validate config with `ADKAgentConfig.model_validate()`
   - Initialize ADK pipeline components

2. Implement `_build_pipeline()`
   - Create 3 `LlmAgent` researchers with different focus areas
   - Wrap in `ParallelAgent`
   - Create summarizer `LlmAgent`
   - Combine with `SequentialAgent`

3. Implement `_create_researcher()` and `_create_summarizer()`
   - Configure `LlmAgent` with `google_search` tool
   - Set proper instructions for each role
   - Use `output_key` for state sharing

4. Implement `execute()`
   - Run pipeline via `ADKRunnerWrapper`
   - Parse response to extract content
   - Extract sources for metadata
   - Build `MemberAgentResult`

5. Implement `_parse_sources()`
   - Extract URLs and titles from ADK response
   - Build `SearchResult` list for metadata

6. Implement `_handle_error()`
   - Map ADK errors to error codes
   - Generate LLM-interpreted error messages (Markdown)
   - Return proper `MemberAgentResult.error()`

**Acceptance:**
- Agent executes without errors (mocked)
- Returns proper `MemberAgentResult`
- Error handling covers all cases

### Phase 3: Configuration (TOML)

**Tasks:**
1. Create `adk_research_agent.toml`
   - Standard `[agent]` section matching MemberAgentConfig
   - `[agent.plugin]` section with path/agent_class
   - `[agent.metadata.tool_settings.adk_research]` section

**Example Structure:**
```toml
[agent]
type = "custom"
name = "adk-research-agent"
model = "google-gla:gemini-2.5-flash"
temperature = 0.7
max_tokens = 4096
description = "Google ADK Deep Research Agent"

[agent.system_instruction]
text = """..."""

[agent.plugin]
path = "/app/examples/custom_agents/adk_research/agent.py"
agent_class = "ADKResearchAgent"

[agent.metadata.tool_settings.adk_research]
gemini_model = "gemini-2.5-flash"
temperature = 0.7
max_output_tokens = 4096
search_result_limit = 10
researcher_count = 3
timeout_seconds = 30
```

**Acceptance:**
- TOML loads without errors
- All settings are explicit (Article 9)
- No hardcoded values in code

### Phase 4: Testing

**Tasks:**
1. Create `tests/conftest.py`
   - Mock fixtures for ADK components
   - Sample config fixtures
   - Response fixtures

2. Create `tests/test_models.py`
   - Test `ADKAgentConfig` validation
   - Test `SearchResult` parsing
   - Test `ResearchReport` structure

3. Create `tests/test_agent.py` (unit tests)
   - Mock `InMemoryRunner` and ADK agents
   - Test `__init__` with valid/invalid config
   - Test `execute()` success path
   - Test `execute()` error paths
   - Test `_build_pipeline()` structure
   - Test `_parse_sources()` extraction

4. Create `tests/test_e2e.py` (E2E tests)
   - Mark with `@pytest.mark.e2e`
   - Test real Gemini API call
   - Test google_search tool execution
   - Test full pipeline execution

**Acceptance:**
- Unit tests pass with 100% mock coverage
- E2E tests pass with real API (when key available)
- Code coverage >= 80%

### Phase 5: Documentation (README.md)

**Tasks:**
1. Create `README.md` with:
   - Purpose and architecture overview
   - Prerequisites (API key, dependencies)
   - Quick start guide
   - Configuration reference
   - Error handling guide
   - Testing instructions

**Acceptance:**
- Junior developer can run agent following README
- All config options documented
- Error scenarios explained

## Configuration Schema

### TOML Configuration Reference

| Section | Key | Type | Default | Description |
|---------|-----|------|---------|-------------|
| `agent` | `type` | string | required | Must be "custom" |
| `agent` | `name` | string | required | Agent identifier |
| `agent` | `model` | string | required | Pydantic AI model ID |
| `agent.plugin` | `path` | string | required | Path to agent.py |
| `agent.plugin` | `agent_class` | string | required | "ADKResearchAgent" |
| `tool_settings.adk_research` | `gemini_model` | string | "gemini-2.5-flash" | ADK internal model |
| `tool_settings.adk_research` | `temperature` | float | 0.7 | Generation temperature |
| `tool_settings.adk_research` | `max_output_tokens` | int | 4096 | Max tokens per response |
| `tool_settings.adk_research` | `search_result_limit` | int | 10 | Max search results |
| `tool_settings.adk_research` | `researcher_count` | int | 3 | Parallel researchers |
| `tool_settings.adk_research` | `timeout_seconds` | int | 30 | Request timeout |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Gemini API key for ADK |

## Success Criteria Verification

| Criteria | Verification Method |
|----------|---------------------|
| SC-001: 10s single search | Unit test with mock timing |
| SC-002: 30s Deep Research | E2E test with real API |
| SC-003: 100% error info | Unit tests for all error paths |
| SC-004: 100% source tracking | Unit test `_parse_sources()` |
| SC-005: 80% coverage | `pytest --cov` report |
| SC-006: 50% time reduction | N/A (qualitative) |
| SC-007: 100% compatibility | Integration test with loader |

## Error Code Reference

| Code | Description | User Message |
|------|-------------|--------------|
| `AUTH_ERROR` | Invalid/missing API key | Check GOOGLE_API_KEY |
| `RATE_LIMIT` | Gemini API rate limit | Retry after delay |
| `TIMEOUT` | Request timeout | Increase timeout_seconds |
| `NETWORK_ERROR` | Network connectivity | Check connection |
| `SEARCH_NO_RESULTS` | No search results found | Refine query |
| `PIPELINE_ERROR` | ADK pipeline failure | Check agent logs |

## Key Implementation Notes

### ADK API Usage (Latest Only)

```python
# Correct imports (latest API)
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.runners import InMemoryRunner
from google.adk.tools import google_search
from google.genai import types

# Creating LlmAgent with google_search
researcher = LlmAgent(
    name="Researcher",
    model="gemini-2.5-flash",
    instruction="Search and analyze the topic...",
    tools=[google_search],
    output_key="research_result"
)

# Running with InMemoryRunner
runner = InMemoryRunner(agent=pipeline, app_name="deep_research")
session = await runner.session_service.create_session(
    app_name="deep_research",
    user_id="user_123"
)
message = types.Content(parts=[types.Part(text=task)])
response = await runner.run(
    session_id=session.id,
    user_id="user_123",
    new_message=message
)
```

### Error Handling Pattern

```python
async def _handle_error(self, error: Exception) -> MemberAgentResult:
    """Generate error result with LLM-interpreted message."""
    error_code, base_message = self._classify_error(error)

    # Generate user-friendly explanation
    explanation = await self._generate_error_explanation(error_code, str(error))

    return MemberAgentResult.error(
        error_message=explanation,  # Markdown content
        agent_name=self.config.name,
        agent_type=str(AgentType.CUSTOM),
        error_code=error_code,
        metadata={
            "error_code": error_code,
            "error_message": str(error),
            "timestamp": datetime.now(UTC).isoformat()
        }
    )
```

### Source Extraction Pattern

```python
def _parse_sources(self, response: Any) -> list[dict[str, Any]]:
    """Extract sources from ADK response for metadata."""
    sources = []
    # Parse ADK response structure to extract URLs/titles
    # Store in MemberAgentResult.metadata["sources"]
    return sources
```

## Dependencies

- `google-adk >= 1.19.0` (latest version as of 2025-11)
- No changes to `src/mixseek/` required

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| ADK API changes | Pin version in pyproject.toml |
| Rate limiting in E2E tests | Use test fixtures, limit API calls |
| google_search availability | Document model requirements |
| Complex response parsing | Robust error handling, logging |
