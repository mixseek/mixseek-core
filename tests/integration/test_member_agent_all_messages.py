"""Integration tests for Member Agent all_messages capture (FR-016)

Tests verify that Member Agent implementations correctly capture
complete message history from Pydantic AI and store it in MemberAgentResult.

Note: Uses mocks to avoid TestModel limitations (does not support built-in tools).
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_ai.messages import ModelRequest, ModelResponse, SystemPromptPart, TextPart, UserPromptPart

from mixseek.agents.member.code_execution import CodeExecutionMemberAgent
from mixseek.agents.member.plain import PlainMemberAgent
from mixseek.agents.member.web_search import WebSearchMemberAgent
from mixseek.models.member_agent import AgentType, MemberAgentConfig


@pytest.mark.integration
@pytest.mark.asyncio
async def test_plain_member_agent_captures_all_messages() -> None:
    """PlainMemberAgentがall_messages()を保存すること"""
    config = MemberAgentConfig(
        name="test_plain_agent",
        type=AgentType.PLAIN,
        model="google-gla:gemini-2.5-flash-lite",
        temperature=0.7,
        max_tokens=512,
        system_instruction="You are a test agent. Respond concisely.",
    )

    agent = PlainMemberAgent(config)

    # Mock Pydantic AI agent to avoid TestModel limitations
    mock_messages = [
        ModelRequest(
            parts=[
                SystemPromptPart(content="You are a test agent. Respond concisely."),
                UserPromptPart(content="What is 2+2?"),
            ]
        ),
        ModelResponse(
            parts=[TextPart(content="4")],
            model_name="gemini-2.5-flash-lite",
        ),
    ]

    mock_result = MagicMock()
    mock_result.output = "4"
    mock_result.all_messages.return_value = mock_messages
    mock_usage = MagicMock(total_tokens=100, prompt_tokens=50, completion_tokens=50, requests=1)
    mock_result.usage = MagicMock(return_value=mock_usage)

    agent._agent.run = AsyncMock(return_value=mock_result)  # type: ignore[method-assign]

    result = await agent.execute("What is 2+2?")

    # Verify result is successful
    assert result.status == "success"
    assert result.is_success()

    # Verify all_messages is captured (FR-016)
    assert result.all_messages is not None, "all_messages should be captured from Pydantic AI"
    assert isinstance(result.all_messages, list), "all_messages should be a list"
    assert len(result.all_messages) == 2, "all_messages should contain ModelRequest and ModelResponse"

    # Verify message structure (should contain SystemPrompt, UserPrompt, ModelResponse)
    assert any(hasattr(msg, "parts") for msg in result.all_messages), (
        "Messages should have parts (ModelRequest/ModelResponse)"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_web_search_member_agent_captures_all_messages() -> None:
    """WebSearchMemberAgentがall_messages()を保存すること"""
    config = MemberAgentConfig(
        name="test_web_search_agent",
        type=AgentType.WEB_SEARCH,
        model="google-gla:gemini-2.5-flash-lite",
        temperature=0.7,
        max_tokens=512,
        system_instruction="You are a web search agent. Respond concisely.",
    )

    agent = WebSearchMemberAgent(config)

    # Mock Pydantic AI agent to avoid TestModel built-in tools limitation
    mock_messages = [
        ModelRequest(
            parts=[
                SystemPromptPart(content="You are a web search agent. Respond concisely."),
                UserPromptPart(content="What is Python?"),
            ]
        ),
        ModelResponse(
            parts=[TextPart(content="Python is a high-level programming language.")],
            model_name="gemini-2.5-flash-lite",
        ),
    ]

    mock_result = MagicMock()
    mock_result.output = "Python is a high-level programming language."
    mock_result.all_messages.return_value = mock_messages
    mock_usage = MagicMock(total_tokens=150, prompt_tokens=80, completion_tokens=70, requests=1)
    mock_result.usage = MagicMock(return_value=mock_usage)

    agent._agent.run = AsyncMock(return_value=mock_result)  # type: ignore[method-assign]

    result = await agent.execute("What is Python?")

    # Verify result is successful
    assert result.status == "success"
    assert result.is_success()

    # Verify all_messages is captured (FR-016)
    assert result.all_messages is not None, "all_messages should be captured from Pydantic AI"
    assert isinstance(result.all_messages, list), "all_messages should be a list"
    assert len(result.all_messages) == 2, "all_messages should contain messages"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_code_execution_member_agent_captures_all_messages() -> None:
    """CodeExecutionMemberAgentがall_messages()を保存すること"""
    # Note: Code Execution Agent requires Anthropic Claude model
    config = MemberAgentConfig(
        name="test_code_execution_agent",
        type=AgentType.CODE_EXECUTION,
        model="anthropic:claude-sonnet-4-5-20250929",  # Use Anthropic model
        temperature=0.7,
        max_tokens=512,
        system_instruction="You are a code execution agent. Respond concisely.",
    )

    agent = CodeExecutionMemberAgent(config)

    # Mock Pydantic AI agent to avoid TestModel built-in tools limitation
    mock_messages = [
        ModelRequest(
            parts=[
                SystemPromptPart(content="You are a code execution agent. Respond concisely."),
                UserPromptPart(content="What is 2+2?"),
            ]
        ),
        ModelResponse(
            parts=[TextPart(content="4")],
            model_name="claude-sonnet-4-5-20250929",
        ),
    ]

    mock_result = MagicMock()
    mock_result.output = "4"
    mock_result.all_messages.return_value = mock_messages
    mock_usage = MagicMock(total_tokens=120, prompt_tokens=60, completion_tokens=60, requests=1)
    mock_result.usage = MagicMock(return_value=mock_usage)

    agent._agent.run = AsyncMock(return_value=mock_result)  # type: ignore[method-assign]

    result = await agent.execute("What is 2+2?")

    # Verify result is successful
    assert result.status == "success"
    assert result.is_success()

    # Verify all_messages is captured (FR-016)
    assert result.all_messages is not None, "all_messages should be captured from Pydantic AI"
    assert isinstance(result.all_messages, list), "all_messages should be a list"
    assert len(result.all_messages) == 2, "all_messages should contain messages"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_member_agent_all_messages_includes_system_prompt() -> None:
    """all_messagesにSystemPromptが含まれることを検証"""
    config = MemberAgentConfig(
        name="test_agent",
        type=AgentType.PLAIN,
        model="google-gla:gemini-2.5-flash-lite",
        temperature=0.7,
        max_tokens=512,
        system_instruction="UNIQUE_SYSTEM_PROMPT_FOR_TESTING",
    )

    agent = PlainMemberAgent(config)

    # Mock Pydantic AI agent with explicit system prompt in messages
    mock_messages = [
        ModelRequest(
            parts=[
                SystemPromptPart(content="UNIQUE_SYSTEM_PROMPT_FOR_TESTING"),
                UserPromptPart(content="Test task"),
            ]
        ),
        ModelResponse(
            parts=[TextPart(content="Test response")],
            model_name="gemini-2.5-flash-lite",
        ),
    ]

    mock_result = MagicMock()
    mock_result.output = "Test response"
    mock_result.all_messages.return_value = mock_messages
    mock_usage = MagicMock(total_tokens=80, prompt_tokens=40, completion_tokens=40, requests=1)
    mock_result.usage = MagicMock(return_value=mock_usage)

    agent._agent.run = AsyncMock(return_value=mock_result)  # type: ignore[method-assign]

    result = await agent.execute("Test task")

    assert result.all_messages is not None
    assert len(result.all_messages) == 2

    # Verify that system prompt is included in message history
    first_message = result.all_messages[0]
    assert hasattr(first_message, "parts"), "First message should have parts"

    # Check if any part contains the system prompt
    system_prompt_found = False
    for part in first_message.parts:
        if hasattr(part, "content") and "UNIQUE_SYSTEM_PROMPT_FOR_TESTING" in str(part.content):
            system_prompt_found = True
            break

    assert system_prompt_found, "System prompt should be included in message history"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_member_agent_all_messages_includes_user_prompt() -> None:
    """all_messagesにUserPromptが含まれることを検証"""
    config = MemberAgentConfig(
        name="test_agent",
        type=AgentType.PLAIN,
        model="google-gla:gemini-2.5-flash-lite",
        temperature=0.7,
        max_tokens=512,
        system_instruction="You are a test agent.",
    )

    agent = PlainMemberAgent(config)

    # Mock Pydantic AI agent with explicit user prompt in messages
    mock_messages = [
        ModelRequest(
            parts=[
                SystemPromptPart(content="You are a test agent."),
                UserPromptPart(content="UNIQUE_USER_PROMPT_FOR_TESTING"),
            ]
        ),
        ModelResponse(
            parts=[TextPart(content="Test response")],
            model_name="gemini-2.5-flash-lite",
        ),
    ]

    mock_result = MagicMock()
    mock_result.output = "Test response"
    mock_result.all_messages.return_value = mock_messages
    mock_usage = MagicMock(total_tokens=90, prompt_tokens=45, completion_tokens=45, requests=1)
    mock_result.usage = MagicMock(return_value=mock_usage)

    agent._agent.run = AsyncMock(return_value=mock_result)  # type: ignore[method-assign]

    result = await agent.execute("UNIQUE_USER_PROMPT_FOR_TESTING")

    assert result.all_messages is not None
    assert len(result.all_messages) == 2

    # Verify that user prompt is included in message history
    user_prompt_found = False
    for message in result.all_messages:
        if hasattr(message, "parts"):
            for part in message.parts:
                if hasattr(part, "content") and "UNIQUE_USER_PROMPT_FOR_TESTING" in str(part.content):
                    user_prompt_found = True
                    break

    assert user_prompt_found, "User prompt should be included in message history"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_member_agent_all_messages_includes_model_response() -> None:
    """all_messagesにModelResponseが含まれることを検証"""
    config = MemberAgentConfig(
        name="test_agent",
        type=AgentType.PLAIN,
        model="google-gla:gemini-2.5-flash-lite",
        temperature=0.7,
        max_tokens=512,
        system_instruction="You are a test agent.",
    )

    agent = PlainMemberAgent(config)

    # Mock Pydantic AI agent with complete message history
    mock_messages = [
        ModelRequest(
            parts=[
                SystemPromptPart(content="You are a test agent."),
                UserPromptPart(content="What is 2+2?"),
            ]
        ),
        ModelResponse(
            parts=[TextPart(content="The answer is 4")],
            model_name="gemini-2.5-flash-lite",
        ),
    ]

    mock_result = MagicMock()
    mock_result.output = "The answer is 4"
    mock_result.all_messages.return_value = mock_messages
    mock_usage = MagicMock(total_tokens=85, prompt_tokens=42, completion_tokens=43, requests=1)
    mock_result.usage = MagicMock(return_value=mock_usage)

    agent._agent.run = AsyncMock(return_value=mock_result)  # type: ignore[method-assign]

    result = await agent.execute("What is 2+2?")

    assert result.all_messages is not None
    assert len(result.all_messages) >= 2  # At least ModelRequest and ModelResponse

    # Verify that ModelResponse is included
    # Last message should be ModelResponse
    last_message = result.all_messages[-1]
    assert hasattr(last_message, "parts"), "Last message should have parts (ModelResponse)"

    # ModelResponse should have model_name attribute
    assert hasattr(last_message, "model_name"), "ModelResponse should have model_name"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_member_agent_error_case_captures_all_messages() -> None:
    """エラー時もall_messagesが保存されることを検証"""
    config = MemberAgentConfig(
        name="test_agent",
        type=AgentType.PLAIN,
        model="google-gla:gemini-2.5-flash-lite",
        temperature=0.7,
        max_tokens=512,
        system_instruction="You are a test agent.",
    )

    agent = PlainMemberAgent(config)

    # Trigger an error by passing empty task
    result = await agent.execute("")  # Empty task should cause validation error

    assert result.status == "error"
    assert result.is_error()

    # Empty task error occurs before Pydantic AI call, so all_messages will be None
    # This verifies the behavior is consistent
    assert result.all_messages is None, "all_messages should be None when error occurs before AI call"
