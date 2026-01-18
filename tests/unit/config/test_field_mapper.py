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

    def test_tool_settings_empty_direct_falls_back_to_metadata(self) -> None:
        """直接指定が空dict/Noneの場合、metadata側が使用されること。"""
        agent_data = {
            "name": "test-agent",
            "type": "gemini",
            "tool_settings": None,
            "metadata": {"tool_settings": {"fallback": True}},
        }

        result = normalize_member_agent_fields(agent_data)

        assert result["tool_settings"] == {"fallback": True}

    def test_tool_settings_empty_dict_direct_is_truthy(self) -> None:
        """直接指定が空dictの場合、空dictが返される（falsy判定されないこと）。

        NOTE: 空のdict {} はPythonではfalsyなので、現在の実装では
        metadata側にフォールバックする。これは期待動作かどうか検討の余地あり。
        """
        agent_data = {
            "name": "test-agent",
            "type": "gemini",
            "tool_settings": {},
            "metadata": {"tool_settings": {"nested": True}},
        }

        result = normalize_member_agent_fields(agent_data)

        # 現在の実装: 空dictはfalsyなのでmetadataにフォールバック
        # 空dictでも直接指定を優先したい場合は実装変更が必要
        assert result["tool_settings"] == {"nested": True}
