"""チーム進捗一覧表示コンポーネント.

実行ページの進捗確認領域に全チームの現在ラウンド番号、完了数、開始/終了時刻を表示します。

Functions:
    render_team_progress_list: チーム進捗一覧テーブル表示

References:
    - Spec: specs/014-ui/spec.md (FR-023, SC-012)
    - Pattern: build/lib/mixseek_ui/components/leaderboard_table.py
"""

import pandas as pd
import streamlit as st

from mixseek.ui.services.round_service import fetch_team_progress_list


def render_team_progress_list(execution_id: str) -> None:
    """チーム進捗一覧をDataFrame形式で表示.

    round_statusテーブルから各チームの現在ラウンド、完了数、開始/終了時刻を取得し、
    st.dataframe()で一覧表示します。データが存在しない場合は案内メッセージを表示。

    Args:
        execution_id: 実行識別子(UUID)

    Example:
        >>> import streamlit as st
        >>> execution_id = st.session_state.get("current_execution_id")
        >>> if execution_id:
        ...     render_team_progress_list(execution_id)
        # チーム名、現在ラウンド、完了数、開始時刻、終了時刻の一覧テーブル表示

    Note:
        データ不在時は案内メッセージとともに実行ページへのリンクを表示。
        これによりラウンドコントローラ未実行時もUI起動可能。
    """
    progress_list = fetch_team_progress_list(execution_id)

    if not progress_list:
        st.info("チーム進捗データがありません。ラウンドコントローラによる実行後に表示されます。")
        return

    # DataFrameに変換
    df = pd.DataFrame(
        [
            {
                "チーム名": progress.team_name,
                "現在ラウンド": progress.round_number,
                # 完了したラウンド数 = 現在のラウンド番号 - 1
                # （round_numberは実行中のラウンドを指すため）
                "完了数": max(0, progress.round_number - 1),
                "開始時刻": (
                    progress.round_started_at.strftime("%Y-%m-%d %H:%M:%S") if progress.round_started_at else "-"
                ),
                "終了時刻": (
                    progress.round_ended_at.strftime("%Y-%m-%d %H:%M:%S") if progress.round_ended_at else "-"
                ),
            }
            for progress in progress_list
        ]
    )

    # テーブル表示
    st.dataframe(
        df,
        width="stretch",
        hide_index=True,
    )
