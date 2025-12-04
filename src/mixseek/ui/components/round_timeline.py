"""ラウンドタイムライン表示コンポーネント.

結果ページに各ラウンドの開始/終了時刻をGanttチャート形式で表示します。

Functions:
    render_round_timeline: ラウンドタイムラインのPlotly Ganttチャート表示

References:
    - Spec: specs/014-ui/spec.md (FR-020, SC-010)
    - Research: specs/014-ui/research.md (Section 1: Plotly Express選定)
    - Plotly docs: https://plotly.com/python/gantt/
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from mixseek.ui.services.round_service import fetch_round_timeline


def render_round_timeline(execution_id: str, team_id: str) -> None:
    """ラウンドタイムラインをGanttチャート形式で表示.

    round_statusテーブルから特定チームの各ラウンドの開始/終了時刻を取得し、
    Plotly ExpressのGanttチャートでタイムライン表示します。
    データが存在しない場合は案内メッセージを表示。

    Args:
        execution_id: 実行識別子(UUID)
        team_id: チーム識別子

    Example:
        >>> import streamlit as st
        >>> execution_id = st.session_state.get("current_execution_id")
        >>> team_id = "team-a"
        >>> if execution_id:
        ...     render_round_timeline(execution_id, team_id)
        # 各ラウンドの開始→終了時刻がGanttチャート形式で表示される

    Note:
        データ不在時は案内メッセージを表示。
        Ganttチャートは各ラウンドをバーで表現し、開始/終了時刻を可視化。
        ラウンド進行中（round_ended_atがNone）の場合は現在時刻まで表示。
    """
    timeline = fetch_round_timeline(execution_id, team_id)

    if not timeline:
        st.info(f"{team_id} のラウンドタイムラインデータがありません。")
        return

    # Ganttチャート用のDataFrame作成
    # Plotly Expressのtimelineは Task, Start, Finish カラムを期待
    df_data = []
    for progress in timeline:
        if progress.round_started_at is None:
            continue  # 開始時刻がない場合はスキップ

        # 終了時刻がない場合は現在時刻を使用
        finish = progress.round_ended_at if progress.round_ended_at else pd.Timestamp.now()

        df_data.append(
            {
                "Task": f"ラウンド {progress.round_number}",
                "Start": progress.round_started_at,
                "Finish": finish,
            }
        )

    if not df_data:
        st.info("有効なタイムラインデータがありません（開始時刻が記録されていません）。")
        return

    df = pd.DataFrame(df_data)

    # Ganttチャート描画
    fig = px.timeline(
        df,
        x_start="Start",
        x_end="Finish",
        y="Task",
        title=f"{team_id} のラウンドタイムライン",
    )

    # Y軸の順序を逆にする（ラウンド1が上に来るように）
    fig.update_yaxes(categoryorder="total ascending")

    # グラフ表示
    st.plotly_chart(fig, width="stretch")
