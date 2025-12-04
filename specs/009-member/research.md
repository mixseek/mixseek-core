# Research Findings: MixSeek-Core Member Agent バンドル

**Date**: 2025-10-21
**Phase**: 0 - Research & Analysis

## Overview

This document consolidates research findings for implementing the MixSeek-Core Member Agent bundle. All technical decisions are based on Pydantic AI documentation analysis and MixSeek-Core framework requirements.

---

## 1. Pydantic AI Agent Architecture

### Decision: Agent as Reusable, Stateless Container

**Chosen**: Pydantic AI Agent pattern with dependency injection
- Agents instantiated once as module globals
- Stateless design with dependencies passed at runtime
- Instructions instead of system_prompt for cleaner context management

**Rationale**:
- Follows Pydantic AI best practices for performance
- Instructions are re-evaluated per run without polluting message history
- Enables proper dependency injection for TUMIX integration
- Supports structured output with Pydantic models

**Alternatives Considered**:
- Per-request agent creation: Rejected due to performance overhead
- System prompts: Rejected due to message history pollution in multi-agent workflows

**Implementation Pattern**:
```python
from pydantic_ai import Agent, RunContext
from dataclasses import dataclass

@dataclass
class MemberAgentDeps:
    config: AgentConfig
    tumix_client: TUMIXClient  # Future TUMIX integration

member_agent = Agent(
    'google-gla:gemini-2.5-flash-lite',
    deps_type=MemberAgentDeps,
    output_type=ProcessResult,
    instructions="You are a specialized member agent..."
)
```

---

## 2. Built-in Tools Strategy

### Decision: Avoid Built-in Tools for Member Agents

**Chosen**: Custom function tools instead of WebSearchTool/CodeExecutionTool
- Reserve built-in tools for Leader Agent only
- Implement web search and code execution as custom tools

**Rationale**:
- **Google Model Limitation**: Cannot combine built-in tools with function tools
- **TUMIX Integration Need**: Member agents require function tools for framework integration
- **Consistency**: All member agents use same tool architecture pattern

**Alternatives Considered**:
- Built-in tools with PromptedOutput: Rejected due to structured output requirements
- Separate agent instances for built-in vs function tools: Rejected for complexity

**Implementation Impact**:
- Web Search Agent: Custom web search tool implementation
- Code Execution Agent: Custom sandboxed code execution tool
- Plain Agent: No external tools, pure reasoning

---

## 3. Google/Gemini Model Integration

### Decision: Dual API Support with Environment Variable Switching

**Chosen**: Support both Gemini API and Vertex AI with GOOGLE_GENAI_USE_VERTEXAI flag

**Configuration Strategy**:
1. **Development**: Gemini API with GOOGLE_API_KEY
2. **Production**: Vertex AI with GOOGLE_APPLICATION_CREDENTIALS
3. **Switching**: GOOGLE_GENAI_USE_VERTEXAI environment variable

**Rationale**:
- **Development Simplicity**: Gemini API requires only API key
- **Production Requirements**: Vertex AI provides enterprise guarantees
- **Flexibility**: Environment variable allows deployment-time switching

**Model Selection**:
- **Member Agents**: `google-gla:gemini-2.5-flash-lite` (fast, cost-effective)
- **Default Settings**: Temperature 0.2, max_tokens 2048, thinking disabled

**Alternatives Considered**:
- Gemini API only: Rejected due to production scalability concerns
- Vertex AI only: Rejected due to development complexity
- Runtime model switching: Rejected for configuration complexity

---

## 4. Toolset Architecture for TUMIX Integration

### Decision: FunctionToolset with Agent Delegation Pattern

**Chosen**: Direct agent-to-agent communication via tool delegation
- Member agents expose capabilities through FunctionToolset
- Leader agents call member agents directly (same process)
- Usage tracking passed between agents

**Rationale**:
- **Performance**: Same-process execution, no network overhead
- **Type Safety**: Full Pydantic validation throughout call chain
- **Usage Tracking**: Seamless usage limit management across agents
- **Simplicity**: No external toolset complexity for same-process communication

**TUMIX Integration Pattern**:
```python
@member_agent.tool
async def tumix_process(ctx: RunContext[MemberAgentDeps], data: str) -> str:
    """Process data through TUMIX framework."""
    return await ctx.deps.tumix_client.process(data)

# Leader calls member agent
@leader_agent.tool
async def delegate_to_member(ctx: RunContext[LeaderDeps], task: str) -> ProcessResult:
    result = await member_agent.run(
        task,
        deps=ctx.deps.member_deps,
        usage=ctx.usage  # Pass usage tracking
    )
    return result.output
```

**Alternatives Considered**:
- ExternalToolset: Better for distributed systems, overkill for same-process
- MCP Protocol: Future consideration for high-security scenarios
- Direct function calls: Lacks usage tracking and proper context management

---

## 5. Configuration Management

### Decision: Three-Tier TOML + Pydantic Configuration

**Chosen**: TOML files with Pydantic validation and environment overrides

**Configuration Hierarchy**:
1. **TOML Files**: Base configuration and agent definitions
2. **Environment Variables**: Deployment-specific overrides
3. **Runtime Settings**: Per-execution customization

**Rationale**:
- **Type Safety**: Pydantic models provide validation and clear schemas
- **Flexibility**: Environment variables enable deployment customization
- **Usability**: TOML files are human-readable and easy to edit
- **Validation**: Early error detection with clear error messages

**Configuration Schema**:
```toml
[agent]
name = "plain-member-agent"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.2
max_tokens = 2048

[agent.instructions]
text = """
You are a specialized member agent responsible for...
"""

[agent.capabilities]
tools = []  # Empty for plain agent
description = "General reasoning and analysis"
```

**Alternatives Considered**:
- JSON configuration: Rejected due to lack of comments and readability
- YAML configuration: Rejected due to complexity and indentation issues
- Environment-only configuration: Rejected due to poor organization for complex settings

---

## 6. Testing Strategy Decisions

### Decision: Multi-Level Testing with TestModel

**Chosen**: Comprehensive testing strategy using Pydantic AI TestModel

**Testing Levels**:
1. **Unit Tests**: Individual agent behavior with TestModel
2. **Integration Tests**: Real API calls with rate limiting
3. **Configuration Tests**: TOML validation and loading

**Test Architecture**:
```python
from pydantic_ai.models.test import TestModel

def test_plain_agent_basic_reasoning():
    test_model = TestModel()
    agent = Agent(test_model, instructions="Test instructions")

    result = agent.run_sync("Test query")

    # Verify behavior without API costs
    assert result.output
    assert test_model.last_model_request_parameters
```

**Rationale**:
- **Cost Efficiency**: TestModel eliminates API costs during development
- **Deterministic Testing**: Predictable behavior for unit tests
- **Real API Validation**: Integration tests verify actual API compatibility
- **Constitution Compliance**: Follows Article 3 (Test-First Imperative)

**Alternatives Considered**:
- API-only testing: Rejected due to cost and rate limiting issues
- Mock-heavy testing: Rejected due to poor integration validation
- No structured testing: Rejected due to constitution requirements

---

## 7. CLI Interface Design

### Decision: Click-based CLI with Development Warnings

**Chosen**: Typer framework for `mixseek member` command

**Command Interface**:
```bash
mixseek member "user prompt" --config agent_name.toml
mixseek member "user prompt" --agent agent_name
```

**Key Features**:
- **Development Warning**: Clear warning that this is for development/testing only
- **TOML Support**: Load agent configuration from files
- **JSON Output**: Structured output for automation
- **Error Handling**: Clear error messages for configuration issues

**Rationale**:
- **User Experience**: Click provides excellent CLI experience with help, validation
- **Constitution Compliance**: Article 2 (CLI Interface Mandate) requirements
- **Safety**: Development-only warnings prevent production misuse
- **Integration**: Fits naturally into mixseek-core command structure

**Alternatives Considered**:
- argparse: Rejected due to poor user experience and limited functionality
- Direct Python execution: Rejected due to CLI mandate requirement
- Full production CLI: Rejected due to development/testing scope limitation

---

## 8. Error Handling and Reliability

### Decision: Explicit Error Handling with Graceful Degradation

**Chosen**: Comprehensive error handling without silent failures

**Error Categories**:
1. **Configuration Errors**: Invalid TOML, missing credentials
2. **API Errors**: Rate limiting, authentication failures
3. **Tool Errors**: Function execution failures
4. **Validation Errors**: Pydantic model validation failures

**Handling Strategy**:
- **No Silent Failures**: All errors propagate with clear messages
- **Configuration Validation**: Early validation at load time
- **API Resilience**: Retry with exponential backoff for transient failures
- **User-Friendly Messages**: Technical details logged, user sees actionable errors

**Implementation Pattern**:
```python
from pydantic_ai import UnexpectedModelBehavior
from pydantic_ai.exceptions import UsageLimitExceeded

try:
    result = await agent.run(prompt, deps=deps)
except UsageLimitExceeded as e:
    logger.error(f"Usage limit exceeded: {e}")
    raise RuntimeError(f"Member agent hit usage limit: {e.usage_limit_type}")
except UnexpectedModelBehavior as e:
    logger.error(f"Model behavior issue: {e}")
    raise RuntimeError("Member agent produced unexpected output")
```

**Rationale**:
- **Constitution Compliance**: Article 9 (Data Accuracy Mandate) - no silent failures
- **Debugging Support**: Clear error messages aid development and testing
- **Production Readiness**: Although development-only, maintain production-quality error handling

**Alternatives Considered**:
- Silent failure with defaults: Rejected due to constitution violation
- Basic try/catch: Rejected due to poor debugging experience
- Exception swallowing: Rejected due to data accuracy requirements

---

## 9. Documentation and Examples Strategy

### Decision: Comprehensive Examples with Real-World Scenarios

**Chosen**: Multiple example configurations and usage patterns

**Example Categories**:
1. **Basic Examples**: Simple agent configurations for each type
2. **Advanced Examples**: Complex scenarios with multiple tools
3. **Integration Examples**: Usage within MixSeek-Core framework
4. **Testing Examples**: Test patterns and best practices

**Documentation Structure**:
```
examples/
├── agent_configs/
│   ├── plain_assistant.toml      # Basic reasoning agent
│   ├── research_agent.toml       # Web search enabled
│   └── data_analyst.toml         # Code execution enabled
└── usage_examples/
    ├── basic_usage.py            # CLI usage patterns
    ├── integration_test.py       # Framework integration
    └── custom_tools.py           # Custom tool development
```

**Rationale**:
- **User Adoption**: Clear examples reduce learning curve
- **Best Practices**: Examples demonstrate recommended patterns
- **Testing Support**: Provides reference implementations for validation
- **Framework Integration**: Shows how to integrate with broader MixSeek-Core system

**Alternatives Considered**:
- Minimal documentation: Rejected due to complexity of multi-agent systems
- Code-only examples: Rejected due to need for configuration documentation
- External documentation: Rejected due to maintenance complexity

---

## 10. Performance and Scalability Considerations

### Decision: Optimize for Development Speed over Production Scale

**Chosen**: Simple, direct implementation optimized for development workflow

**Performance Characteristics**:
- **Response Time Goal**: < 5 seconds for basic queries
- **Concurrency**: Limited by API rate limits, not implementation
- **Memory Usage**: Minimal state, agents are stateless
- **Startup Time**: Fast configuration loading and agent initialization

**Optimization Strategies**:
- **Model Selection**: Gemini 1.5 Flash for speed/cost balance
- **Thinking Disabled**: No extended reasoning for faster responses
- **Direct Tool Calls**: No middleware overhead for basic operations
- **Configuration Caching**: Load TOML files once, reuse parsed configuration

**Rationale**:
- **Development Focus**: Primary use case is development and testing
- **Simplicity**: Avoid premature optimization for uncertain production requirements
- **API Constraints**: Performance primarily limited by external API calls
- **Future Extensibility**: Simple architecture allows later optimization

**Alternatives Considered**:
- Complex caching: Rejected due to development focus and complexity
- Connection pooling: Rejected due to API client limitations
- Distributed architecture: Rejected due to same-process design decision

---

## Summary

All research findings support a clean, type-safe implementation that:

1. **Leverages Pydantic AI strengths**: Structured output, tool integration, type safety
2. **Follows MixSeek-Core patterns**: TUMIX integration, Leader-Member communication
3. **Maintains development focus**: Clear warnings, excellent error messages, comprehensive examples
4. **Ensures constitution compliance**: Test-first, library-first, type-safe, no hardcoding
5. **Provides flexibility**: Environment-based configuration, multiple deployment options

**Next Phase**: Proceed to data model design and API contract definition based on these architectural decisions.