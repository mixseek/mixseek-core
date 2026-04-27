"""`_detect_unit_kind` ヘルパーの単体テスト。

TOML トップレベルキー `[team]` / `[workflow]` の判別ロジックを検証する。
判別不能なケース（解析失敗・両在・不在・file not found）は全て `"unknown"` に丸めて、
呼び出し側 (team validator) が `load_unit_settings` 経由で ERROR 化する設計を保証する。
"""

from pathlib import Path

import pytest

from mixseek.config.preflight import _detect_unit_kind


class TestDetectUnitKind:
    """`_detect_unit_kind` のキー判別ロジック検証"""

    def test_team_only(self, tmp_path: Path) -> None:
        """`[team]` のみ存在 → `"team"` を返す"""
        toml = tmp_path / "team_only.toml"
        toml.write_text('[team]\nteam_id = "t1"\nteam_name = "T1"\n')

        assert _detect_unit_kind(toml, tmp_path) == "team"

    def test_workflow_only(self, tmp_path: Path) -> None:
        """`[workflow]` のみ存在 → `"workflow"` を返す"""
        toml = tmp_path / "workflow_only.toml"
        toml.write_text('[workflow]\nworkflow_id = "wf1"\nworkflow_name = "WF1"\n')

        assert _detect_unit_kind(toml, tmp_path) == "workflow"

    def test_both_team_and_workflow(self, tmp_path: Path) -> None:
        """`[team]` と `[workflow]` 両方存在 → `"unknown"` (判別不能)"""
        toml = tmp_path / "both.toml"
        toml.write_text('[team]\nteam_id = "t1"\n[workflow]\nworkflow_id = "wf1"\n')

        assert _detect_unit_kind(toml, tmp_path) == "unknown"

    def test_neither_team_nor_workflow(self, tmp_path: Path) -> None:
        """`[team]` も `[workflow]` も存在しない → `"unknown"` (判別不能)"""
        toml = tmp_path / "neither.toml"
        toml.write_text('[orchestrator]\nname = "test"\n')

        assert _detect_unit_kind(toml, tmp_path) == "unknown"

    def test_invalid_toml_syntax(self, tmp_path: Path) -> None:
        """TOML 構文エラー → `"unknown"` (TOMLDecodeError を吸収)"""
        toml = tmp_path / "invalid.toml"
        toml.write_text("[invalid\n")

        assert _detect_unit_kind(toml, tmp_path) == "unknown"

    def test_file_not_found(self, tmp_path: Path) -> None:
        """ファイル不在 → `"unknown"` (FileNotFoundError を吸収)"""
        missing = tmp_path / "nonexistent.toml"

        assert _detect_unit_kind(missing, tmp_path) == "unknown"

    def test_relative_path_resolves_against_workspace(self, tmp_path: Path) -> None:
        """相対パスは workspace 起点で解決される"""
        toml = tmp_path / "relative_team.toml"
        toml.write_text('[team]\nteam_id = "t1"\nteam_name = "T1"\n')

        # 相対パスでも workspace を起点に解決して同じ結果を返す
        assert _detect_unit_kind(Path("relative_team.toml"), tmp_path) == "team"

    def test_absolute_path_used_as_is(self, tmp_path: Path) -> None:
        """絶対パスは workspace 関係なくそのまま使用される"""
        toml = tmp_path / "absolute_team.toml"
        toml.write_text('[team]\nteam_id = "t1"\nteam_name = "T1"\n')
        unrelated = tmp_path / "elsewhere"
        unrelated.mkdir()

        # 絶対パスなら workspace が無関係でも判別できる
        assert _detect_unit_kind(toml, unrelated) == "team"

    def test_empty_string_path(self, tmp_path: Path) -> None:
        """空文字列パス → `Path("")` で FileNotFoundError → `"unknown"`"""
        # `entry.get("config", "")` が空文字列を返した場合の防御確認
        # invariant: orchestrator schema 検証で本来弾かれるが、本ヘルパー単体では
        # `"unknown"` を返して呼び出し側 ERROR 化に委ねる
        assert _detect_unit_kind(Path(""), tmp_path) == "unknown"

    @pytest.mark.parametrize(
        "section_content, expected",
        [
            ('[team]\nteam_id = "t1"\n', "team"),
            ('[workflow]\nworkflow_id = "wf1"\n', "workflow"),
        ],
    )
    def test_parametrized_single_section(self, tmp_path: Path, section_content: str, expected: str) -> None:
        """シングルセクションパターンを parametrize"""
        toml = tmp_path / "param.toml"
        toml.write_text(section_content)

        assert _detect_unit_kind(toml, tmp_path) == expected
