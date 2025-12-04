"""ラウンド進捗表示コンポーネント.

実行ページ上部に現在のラウンド番号を"ラウンド X/Y"形式で表示します。

Functions:
    render_round_progress: ラウンド進捗メトリック表示

References:
    - Spec: specs/014-ui/spec.md (FR-022, SC-011)
    - Pattern: build/lib/mixseek_ui/pages/2_results.py (st.metric表示)
"""

import streamlit as st

from mixseek.ui.services.execution_service import get_execution_status
from mixseek.ui.services.round_service import fetch_current_round_progress


def render_round_progress(execution_id: str) -> None:
    """ラウンド進捗を"ラウンド X/Y"形式で表示.

    round_statusテーブルから現在のラウンド番号を取得し、
    st.metric()でKPI表示します。データが存在しない場合は何も表示しません。

    Args:
        execution_id: 実行識別子(UUID)

    Example:
        >>> import streamlit as st
        >>> execution_id = st.session_state.get("current_execution_id")
        >>> if execution_id:
        ...     render_round_progress(execution_id)
        # 表示例: "ラウンド 3/10"

    Note:
        データ不在時は何も表示しない（エラーとしない）。
        これによりラウンドコントローラ未実行時もUI起動可能。
    """
    progress = fetch_current_round_progress(execution_id)

    if progress is None:
        # データ不在時は何も表示しない（エラーとしない）
        return

    # ExecutionStateからtotal_roundsを取得（進捗ファイル経由）
    execution_state = get_execution_status(execution_id)

    # total_roundsが取得できた場合は "ラウンド X/Y" 形式で表示
    if execution_state.total_rounds is not None:
        value = f"ラウンド {progress.round_number}/{execution_state.total_rounds}"
    else:
        # total_roundsが取得できない場合は "ラウンド X" 形式で表示
        value = f"ラウンド {progress.round_number}"

    st.metric(
        label="現在のラウンド",
        value=value,
        delta=None,
    )
