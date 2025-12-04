"""ログ表示コンポーネント.

実行ログをリアルタイムで表示するためのStreamlitコンポーネント。

References:
    - FR-026: 実行ログセクション要件
    - SC-014: ログ読み取り・表示パフォーマンス要件
"""

import streamlit as st

from mixseek.ui.services.execution_service import get_recent_logs


def render_log_viewer(lines: int = 100, expanded: bool = False) -> None:
    """ログ表示コンポーネント.

    Args:
        lines: 表示するログ行数（デフォルト100）
        expanded: expanderの初期展開状態（デフォルトFalse）

    Note:
        - st.expander: 折りたたみ可能なパネル
        - st.code: モノスペースフォント、スクロール可能
        - INFO以上のログレベルのみ表示
    """
    logs = get_recent_logs(lines=lines, level="INFO")

    with st.expander("📋 実行ログ", expanded=expanded):
        if logs:
            # ログをコードブロックで表示（スクロール可能）
            st.code("\n".join(logs), language="text")
        else:
            st.info("ログがありません")
