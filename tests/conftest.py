"""Root-level pytest fixtures for all tests."""

from pathlib import Path

import pytest


@pytest.fixture
def isolate_from_project_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """テスト中はプロジェクトルートの.envファイルを読み込まないようにする。

    Issue #251対応: MappedDotEnvSettingsSourceが正しく動作するようになったことで、
    プロジェクトルートの.envファイルがテストに影響を与えるようになりました。
    このフィクスチャは作業ディレクトリを一時ディレクトリに変更し、
    テストの隔離性を確保します。

    使用方法:
        def test_example(isolate_from_project_dotenv):
            # このテストはプロジェクトルートの.envファイルの影響を受けません
            ...
    """
    monkeypatch.chdir(tmp_path)
