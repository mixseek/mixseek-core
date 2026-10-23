"""--log-format 共通オプションのテスト

typer 0.26 以降は click をベンダリングしており、click 固有の型（click.Choice など）を
click_type に渡す使い方はサポートされない。選択肢は LogFormatType（Literal）の型注釈から
typer に生成させるため、その挙動を検証する。
"""

import inspect

import pytest
import typer
from typer.testing import CliRunner

from mixseek.cli.common_options import LOG_FORMAT_OPTION
from mixseek.cli.main import app as mixseek_app
from mixseek.config.logging import LogFormatType

runner = CliRunner()

probe_app = typer.Typer()


@probe_app.command()
def probe(log_format: LogFormatType | None = LOG_FORMAT_OPTION) -> None:
    """受け取った log_format をそのまま出力する"""
    typer.echo(f"log_format={log_format!r}")


def _commands_with_log_format_option() -> list[str]:
    """LOG_FORMAT_OPTION を使う登録済みコマンド名"""
    names = []
    for info in mixseek_app.registered_commands:
        if info.name is None or info.callback is None:
            continue
        parameters = inspect.signature(info.callback).parameters.values()
        if any(parameter.default is LOG_FORMAT_OPTION for parameter in parameters):
            names.append(info.name)
    return names


LOG_FORMAT_COMMANDS = _commands_with_log_format_option()


@pytest.mark.unit
@pytest.mark.parametrize("value", ["text", "json"])
def test_log_format_accepts_valid_values_as_str(value: str) -> None:
    """text / json はそのまま文字列として渡される"""
    result = runner.invoke(probe_app, ["--log-format", value])

    assert result.exit_code == 0, result.output
    assert f"log_format={value!r}" in result.output


@pytest.mark.unit
def test_log_format_defaults_to_none() -> None:
    """未指定時は None（環境変数 MIXSEEK_LOG_FORMAT へのフォールバックは呼び出し側で解決する）"""
    result = runner.invoke(probe_app, [])

    assert result.exit_code == 0, result.output
    assert "log_format=None" in result.output


@pytest.mark.unit
def test_log_format_rejects_invalid_value() -> None:
    """選択肢以外の値は使用方法エラー（終了コード 2）になる"""
    result = runner.invoke(probe_app, ["--log-format", "xml"])

    assert result.exit_code == 2
    assert "xml" in result.output


@pytest.mark.unit
def test_log_format_option_commands_are_detected() -> None:
    """LOG_FORMAT_OPTION を使うコマンドを検出できている（パラメータ化テストの空振り防止）"""
    assert {"exec", "member", "team", "evaluate", "ui"} <= set(LOG_FORMAT_COMMANDS)


@pytest.mark.unit
@pytest.mark.parametrize("command", LOG_FORMAT_COMMANDS)
def test_commands_reject_invalid_log_format(command: str) -> None:
    """--log-format を持つ全コマンドで選択肢以外の値が拒否される（LogFormatType 注釈の付け忘れ検知）"""
    result = runner.invoke(mixseek_app, [command, "--log-format", "xml"])

    assert result.exit_code == 2
    assert "xml" in result.output
