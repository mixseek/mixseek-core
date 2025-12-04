"""Unit tests for MemberAgentResult.all_messages field (FR-016)

Tests verify that MemberAgentResult can store complete message history
from Pydantic AI and properly serialize/deserialize it.
"""

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)

from mixseek.models.member_agent import MemberAgentResult


def test_member_agent_result_all_messages_field_type() -> None:
    """MemberAgentResult.all_messagesフィールドの型が正しいこと"""
    # Create mock ModelMessage list
    mock_messages: list[ModelMessage] = [
        ModelRequest(
            parts=[
                SystemPromptPart(content="Test system prompt"),
                UserPromptPart(content="Test user prompt"),
            ]
        ),
        ModelResponse(
            parts=[TextPart(content="Test response")],
            model_name="test-model",
        ),
    ]

    result = MemberAgentResult.success(
        content="test output",
        agent_name="test_agent",
        agent_type="plain",
        execution_time_ms=100,
        all_messages=mock_messages,
    )

    assert result.all_messages is not None
    assert result.all_messages == mock_messages
    assert isinstance(result.all_messages, list)
    assert len(result.all_messages) == 2


def test_member_agent_result_all_messages_default_none() -> None:
    """all_messagesフィールドのデフォルト値がNoneであること"""
    result = MemberAgentResult.success(
        content="test output",
        agent_name="test_agent",
        agent_type="plain",
    )

    assert result.all_messages is None


def test_member_agent_result_all_messages_serialization() -> None:
    """all_messagesフィールドがJSONシリアライゼーション可能であること"""
    mock_messages: list[ModelMessage] = [
        ModelRequest(
            parts=[
                SystemPromptPart(content="Test system prompt"),
                UserPromptPart(content="Test user prompt"),
            ]
        ),
        ModelResponse(
            parts=[TextPart(content="Test response")],
            model_name="test-model",
        ),
    ]

    result = MemberAgentResult.success(
        content="test output",
        agent_name="test_agent",
        agent_type="plain",
        all_messages=mock_messages,
    )

    # Pydantic v2のmodel_dump(mode="json")でシリアライゼーション
    result_dict = result.model_dump(mode="json")

    assert "all_messages" in result_dict
    assert result_dict["all_messages"] is not None
    assert isinstance(result_dict["all_messages"], list)
    assert len(result_dict["all_messages"]) == 2


def test_member_agent_result_all_messages_deserialization() -> None:
    """all_messagesフィールドがJSONデシリアライゼーション可能であること"""
    mock_messages: list[ModelMessage] = [
        ModelRequest(
            parts=[
                SystemPromptPart(content="Test system prompt"),
                UserPromptPart(content="Test user prompt"),
            ]
        ),
        ModelResponse(
            parts=[TextPart(content="Test response")],
            model_name="test-model",
        ),
    ]

    original_result = MemberAgentResult.success(
        content="test output",
        agent_name="test_agent",
        agent_type="plain",
        all_messages=mock_messages,
    )

    # Serialize to dict
    result_dict = original_result.model_dump(mode="json")

    # Deserialize from dict
    restored_result = MemberAgentResult.model_validate(result_dict)

    assert restored_result.all_messages is not None
    assert len(restored_result.all_messages) == 2
    assert restored_result.all_messages[0].parts[0].content == "Test system prompt"  # type: ignore
    assert restored_result.all_messages[1].parts[0].content == "Test response"  # type: ignore


def test_member_agent_result_error_with_all_messages() -> None:
    """エラー結果にもall_messagesを含められること"""
    mock_messages: list[ModelMessage] = [
        ModelRequest(
            parts=[
                SystemPromptPart(content="Test system prompt"),
                UserPromptPart(content="Test user prompt"),
            ]
        ),
        ModelResponse(
            parts=[TextPart(content="Error occurred")],
            model_name="test-model",
        ),
    ]

    result = MemberAgentResult.error(
        error_message="Test error",
        agent_name="test_agent",
        agent_type="plain",
        error_code="TEST_ERROR",
        execution_time_ms=100,
        all_messages=mock_messages,
    )

    assert result.status == "error"
    assert result.all_messages is not None
    assert len(result.all_messages) == 2


def test_member_agent_result_all_messages_empty_list() -> None:
    """all_messagesが空リストの場合も正しく処理されること"""
    result = MemberAgentResult.success(
        content="test output",
        agent_name="test_agent",
        agent_type="plain",
        all_messages=[],
    )

    assert result.all_messages is not None
    assert result.all_messages == []
    assert isinstance(result.all_messages, list)
