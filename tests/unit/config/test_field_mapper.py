"""Unit tests for field_mapper module.

Tests for normalize_member_agent_fields function.
"""

from mixseek.config.sources.field_mapper import normalize_member_agent_fields


class TestNormalizeMemberAgentFieldsToolSettings:
    """Test tool_settings field mapping in normalize_member_agent_fields."""

    def test_tool_settings_direct_specification(self) -> None:
        """tool_settings直接指定が認識されること。"""
        agent_data = {
            "name": "test-agent",
            "type": "gemini",
            "tool_settings": {"search_enabled": True, "max_results": 10},
        }

        result = normalize_member_agent_fields(agent_data)

        assert result["tool_settings"] == {"search_enabled": True, "max_results": 10}

    def test_tool_settings_metadata_nested_specification(self) -> None:
        """metadata.tool_settings形式も動作すること（後方互換性）。"""
        agent_data = {
            "name": "test-agent",
            "type": "gemini",
            "metadata": {"tool_settings": {"search_enabled": False, "timeout": 30}},
        }

        result = normalize_member_agent_fields(agent_data)

        assert result["tool_settings"] == {"search_enabled": False, "timeout": 30}

    def test_tool_settings_direct_takes_priority_over_metadata(self) -> None:
        """両方指定された場合、直接指定が優先されること。"""
        agent_data = {
            "name": "test-agent",
            "type": "gemini",
            "tool_settings": {"direct": True},
            "metadata": {"tool_settings": {"nested": True}},
        }

        result = normalize_member_agent_fields(agent_data)

        assert result["tool_settings"] == {"direct": True}

    def test_tool_settings_not_present(self) -> None:
        """tool_settingsが未指定の場合、キーがマップに含まれないこと。"""
        agent_data = {
            "name": "test-agent",
            "type": "gemini",
        }

        result = normalize_member_agent_fields(agent_data)

        assert "tool_settings" not in result

    def test_tool_settings_direct_none_is_removed(self) -> None:
        """直接指定がNoneの場合、キーが除去されること（metadata側を参照しない）。"""
        agent_data = {
            "name": "test-agent",
            "type": "gemini",
            "tool_settings": None,
            "metadata": {"tool_settings": {"fallback": True}},
        }

        result = normalize_member_agent_fields(agent_data)

        assert "tool_settings" not in result

    def test_tool_settings_empty_dict_direct_is_preserved(self) -> None:
        """直接指定が空dictの場合、空dictが返されること（falsy判定しない）。"""
        agent_data = {
            "name": "test-agent",
            "type": "gemini",
            "tool_settings": {},
            "metadata": {"tool_settings": {"nested": True}},
        }

        result = normalize_member_agent_fields(agent_data)

        # 空dictが直接指定された場合は、その値が維持される
        assert result["tool_settings"] == {}
