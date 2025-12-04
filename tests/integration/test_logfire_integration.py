"""Logfire integration tests."""

from unittest.mock import MagicMock, patch

import pytest

from mixseek.config.logfire import LogfireConfig, LogfirePrivacyMode
from mixseek.observability.logfire import setup_logfire


@pytest.fixture
def mock_logfire():
    """Logfireモジュールをモック."""
    mock = MagicMock()
    # setup_logfire()内で"import logfire"しているので、sys.modulesをmock
    with patch.dict("sys.modules", {"logfire": mock}):
        yield mock


def test_setup_logfire_disabled():
    """config.enabled=Falseの場合は何もしない."""
    config = LogfireConfig(
        enabled=False,
        privacy_mode=LogfirePrivacyMode.METADATA_ONLY,
        capture_http=False,
        project_name=None,
        send_to_logfire=True,
    )

    # エラーが発生しないことを確認
    setup_logfire(config)


def test_setup_logfire_success_metadata_only(mock_logfire):
    """metadata_onlyモードで正常初期化."""
    config = LogfireConfig(
        enabled=True,
        privacy_mode=LogfirePrivacyMode.METADATA_ONLY,
        capture_http=False,
        project_name=None,
        send_to_logfire=True,
    )

    setup_logfire(config)

    # configure()が呼ばれたことを確認（send_to_logfire + consoleオプション）
    mock_logfire.configure.assert_called_once()
    call_kwargs = mock_logfire.configure.call_args[1]
    assert call_kwargs["send_to_logfire"] is True
    assert "console" in call_kwargs  # ConsoleOptionsが渡される

    # instrument_pydantic_ai()が呼ばれたことを確認（include_content=False）
    mock_logfire.instrument_pydantic_ai.assert_called_once()
    call_kwargs = mock_logfire.instrument_pydantic_ai.call_args[1]
    assert call_kwargs["include_content"] is False
    assert call_kwargs["include_binary_content"] is False


def test_setup_logfire_success_full_mode(mock_logfire):
    """fullモードで正常初期化."""
    config = LogfireConfig(
        enabled=True,
        privacy_mode=LogfirePrivacyMode.FULL,
        capture_http=False,
        project_name=None,
        send_to_logfire=True,
    )

    setup_logfire(config)

    # configure()が呼ばれたことを確認（send_to_logfire + consoleオプション）
    mock_logfire.configure.assert_called_once()
    call_kwargs = mock_logfire.configure.call_args[1]
    assert call_kwargs["send_to_logfire"] is True
    assert "console" in call_kwargs  # ConsoleOptionsが渡される

    # instrument_pydantic_ai()が引数なしで呼ばれたことを確認
    mock_logfire.instrument_pydantic_ai.assert_called_once_with()


def test_setup_logfire_disabled_mode(mock_logfire):
    """disabledモードでは何もしない."""
    config = LogfireConfig(
        enabled=True,
        privacy_mode=LogfirePrivacyMode.DISABLED,
        capture_http=False,
        project_name=None,
        send_to_logfire=True,
    )

    setup_logfire(config)

    # configure()は呼ばれる（send_to_logfire + consoleオプション）
    mock_logfire.configure.assert_called_once()
    call_kwargs = mock_logfire.configure.call_args[1]
    assert call_kwargs["send_to_logfire"] is True
    assert "console" in call_kwargs  # ConsoleOptionsが渡される

    # instrument_pydantic_ai()は呼ばれない
    mock_logfire.instrument_pydantic_ai.assert_not_called()


def test_setup_logfire_capture_http(mock_logfire):
    """capture_http=TrueでHTTPXインストルメンテーション有効化."""
    config = LogfireConfig(
        enabled=True,
        privacy_mode=LogfirePrivacyMode.METADATA_ONLY,
        capture_http=True,
        project_name=None,
        send_to_logfire=True,
    )

    setup_logfire(config)

    # instrument_httpx()が呼ばれたことを確認
    mock_logfire.instrument_httpx.assert_called_once_with(capture_all=True)


def test_setup_logfire_import_error():
    """logfire未インストール時のエラー."""
    config = LogfireConfig(
        enabled=True,
        privacy_mode=LogfirePrivacyMode.METADATA_ONLY,
        capture_http=False,
        project_name=None,
        send_to_logfire=True,
    )

    # "import logfire"を失敗させる
    # sys.modulesにNoneを設定してImportErrorを発生させる
    import sys

    # logfireがsys.modulesに存在する場合は削除
    logfire_backup = sys.modules.pop("logfire", None)

    try:
        # ImportErrorを発生させるために、logfireをNoneに設定
        sys.modules["logfire"] = None  # type: ignore

        with pytest.raises(ImportError, match="Logfire not installed"):
            setup_logfire(config)
    finally:
        # クリーンアップ
        sys.modules.pop("logfire", None)
        if logfire_backup is not None:
            sys.modules["logfire"] = logfire_backup
