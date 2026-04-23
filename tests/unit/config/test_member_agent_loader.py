"""Tests for _resolve_bundled_system_instruction and member_settings_to_config refactor.

PR1 で抽出した bundled system_instruction 解決ヘルパーの単体テストと、
既存 `member_settings_to_config` が新ヘルパー経由で bundled 解決を行うことの
回帰テストを含む。
"""

from __future__ import annotations

from pathlib import Path

from pytest_mock import MockerFixture

from mixseek.config.member_agent_loader import (
    _resolve_bundled_system_instruction,
    member_settings_to_config,
)
from mixseek.config.schema import MemberAgentSettings


class TestResolveBundledSystemInstruction:
    """`_resolve_bundled_system_instruction` 単体テスト（リファクタ回帰防止）。"""

    def test_explicit_instruction_is_returned_as_is(self, tmp_path: Path) -> None:
        """system_instruction が非 None の場合、その値がそのまま返る。"""
        result = _resolve_bundled_system_instruction(
            agent_type="plain",
            system_instruction="custom prompt",
            workspace=tmp_path,
        )
        assert result == "custom prompt"

    def test_empty_string_instruction_is_returned_as_is(self, tmp_path: Path) -> None:
        """空文字列は「明示的に空」として扱い、そのまま返る。"""
        result = _resolve_bundled_system_instruction(
            agent_type="plain",
            system_instruction="",
            workspace=tmp_path,
        )
        assert result == ""

    def test_none_instruction_with_custom_agent_returns_empty(self, tmp_path: Path) -> None:
        """custom など bundled に存在しない agent_type は空文字列。"""
        result = _resolve_bundled_system_instruction(
            agent_type="custom",
            system_instruction=None,
            workspace=tmp_path,
        )
        assert result == ""

    def test_web_fetch_not_in_bundled_map_returns_empty(self, tmp_path: Path) -> None:
        """web_fetch は bundled agent に含まれない（設計書§5.2）。"""
        result = _resolve_bundled_system_instruction(
            agent_type="web_fetch",
            system_instruction=None,
            workspace=tmp_path,
        )
        assert result == ""

    def test_loads_plain_bundled(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mock_cls = mocker.patch("mixseek.config.bundled_member_agents.BundledMemberAgentLoader")
        mock_cls.return_value.load.return_value.system_instruction = "PLAIN_BUNDLED"
        result = _resolve_bundled_system_instruction(
            agent_type="plain",
            system_instruction=None,
            workspace=tmp_path,
        )
        assert result == "PLAIN_BUNDLED"
        mock_cls.assert_called_once_with(workspace=tmp_path)
        mock_cls.return_value.load.assert_called_once_with("plain")

    def test_web_search_mapping(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """agent_type='web_search' は bundled 名 'web-search' にマップされる。"""
        mock_cls = mocker.patch("mixseek.config.bundled_member_agents.BundledMemberAgentLoader")
        mock_cls.return_value.load.return_value.system_instruction = "WS"
        result = _resolve_bundled_system_instruction(
            agent_type="web_search",
            system_instruction=None,
            workspace=tmp_path,
        )
        assert result == "WS"
        mock_cls.return_value.load.assert_called_once_with("web-search")

    def test_code_execution_mapping(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """agent_type='code_execution' は bundled 名 'code-exec' にマップされる。"""
        mock_cls = mocker.patch("mixseek.config.bundled_member_agents.BundledMemberAgentLoader")
        mock_cls.return_value.load.return_value.system_instruction = "CE"
        result = _resolve_bundled_system_instruction(
            agent_type="code_execution",
            system_instruction=None,
            workspace=tmp_path,
        )
        assert result == "CE"
        mock_cls.return_value.load.assert_called_once_with("code-exec")

    def test_bundled_none_instruction_returns_empty(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """bundled_settings.system_instruction が None の場合も安全に空文字列へ正規化される。"""
        mock_cls = mocker.patch("mixseek.config.bundled_member_agents.BundledMemberAgentLoader")
        mock_cls.return_value.load.return_value.system_instruction = None
        result = _resolve_bundled_system_instruction(
            agent_type="plain",
            system_instruction=None,
            workspace=tmp_path,
        )
        assert result == ""

    def test_workspace_none_is_propagated(self, mocker: MockerFixture) -> None:
        """workspace=None でも BundledMemberAgentLoader に引き渡される。"""
        mock_cls = mocker.patch("mixseek.config.bundled_member_agents.BundledMemberAgentLoader")
        mock_cls.return_value.load.return_value.system_instruction = "X"
        result = _resolve_bundled_system_instruction(
            agent_type="plain",
            system_instruction=None,
            workspace=None,
        )
        assert result == "X"
        mock_cls.assert_called_once_with(workspace=None)


class TestMemberSettingsToConfigBundledRefactor:
    """`member_settings_to_config` が新ヘルパー経由で bundled 解決を行う回帰テスト。"""

    def test_delegates_to_resolver(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """member_settings_to_config が _resolve_bundled_system_instruction を呼び出す。"""
        mock_resolver = mocker.patch(
            "mixseek.config.member_agent_loader._resolve_bundled_system_instruction",
            return_value="RESOLVED",
        )
        settings = MemberAgentSettings(
            agent_name="a1",
            agent_type="plain",
            tool_description="dummy",
            model="google-gla:gemini-2.5-flash",
            system_instruction=None,
        )

        config = member_settings_to_config(settings, agent_data=None, workspace=tmp_path)

        assert config.system_instruction == "RESOLVED"
        mock_resolver.assert_called_once_with("plain", None, tmp_path)

    def test_explicit_instruction_still_passed_through(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """system_instruction が明示指定されていればヘルパーは呼ばれるが値はそのまま返る。"""
        mock_resolver = mocker.patch(
            "mixseek.config.member_agent_loader._resolve_bundled_system_instruction",
            return_value="EXPLICIT",
        )
        settings = MemberAgentSettings(
            agent_name="a1",
            agent_type="plain",
            tool_description="dummy",
            model="google-gla:gemini-2.5-flash",
            system_instruction="EXPLICIT",
        )

        config = member_settings_to_config(settings, agent_data=None, workspace=tmp_path)

        assert config.system_instruction == "EXPLICIT"
        # system_instruction が非 None でもヘルパーは1度呼ばれる（戻り値はそのまま透過）
        mock_resolver.assert_called_once_with("plain", "EXPLICIT", tmp_path)

    def test_workspace_none_is_forwarded(self, mocker: MockerFixture) -> None:
        """workspace=None のケースでも新ヘルパーに同じ値が渡る。"""
        mock_resolver = mocker.patch(
            "mixseek.config.member_agent_loader._resolve_bundled_system_instruction",
            return_value="",
        )
        settings = MemberAgentSettings(
            agent_name="a1",
            agent_type="custom",
            tool_description="dummy",
            model="google-gla:gemini-2.5-flash",
            system_instruction=None,
        )

        member_settings_to_config(settings, agent_data=None, workspace=None)

        mock_resolver.assert_called_once_with("custom", None, None)
