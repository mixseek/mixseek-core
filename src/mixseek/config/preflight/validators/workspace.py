"""プリフライトチェック: ワークスペース検証"""

import tempfile
from pathlib import Path

from mixseek.config.preflight.models import CategoryResult, CheckResult, CheckStatus


def _validate_workspace_writable(workspace: Path) -> CategoryResult:
    """ワークスペースディレクトリへの書き込み権限を検証する。"""
    checks: list[CheckResult] = []
    try:
        with tempfile.NamedTemporaryFile(dir=workspace, delete=True):
            pass
        checks.append(
            CheckResult(
                name="workspace_writable",
                status=CheckStatus.OK,
                message=f"ワークスペース '{workspace}' は書き込み可能です",
            )
        )
    except (PermissionError, OSError, FileNotFoundError) as e:
        checks.append(
            CheckResult(
                name="workspace_writable",
                status=CheckStatus.ERROR,
                message=f"ワークスペース '{workspace}' に書き込みできません: {e}",
            )
        )
    return CategoryResult(category="ワークスペース", checks=checks)
