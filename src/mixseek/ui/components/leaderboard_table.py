"""Leaderboard table component."""

import pandas as pd
import streamlit as st

from mixseek.ui.models.leaderboard import LeaderboardEntry


def render_leaderboard_table(
    entries: list[LeaderboardEntry], key: str = "leaderboard_selection"
) -> tuple[str, int] | None:
    """リーダーボードテーブルをレンダリング.

    Args:
        entries: リーダーボードエントリのリスト
        key: セッション状態のキー（デフォルト: "leaderboard_selection"）

    Returns:
        tuple[str, int] | None: 選択された(team_id, round_number)のタプル（行クリック時）
    """
    if not entries:
        st.info("データがありません。タスクを実行すると結果が表示されます。")
        if st.button("実行ページへ"):
            st.switch_page("pages/1_execution.py")
        return None

    # DataFrameに変換
    df = pd.DataFrame(
        [
            {
                "順位": entry.rank,
                "チーム名": entry.team_name,
                "スコア": round(entry.score),
                "ラウンド": entry.round_number,
                "作成日時": entry.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "team_id": entry.team_id,
            }
            for entry in entries
        ]
    )

    # トップチームをハイライト
    def highlight_top(row: pd.Series) -> list[str]:
        if row["順位"] == 1:
            return ["background-color: #d4edda"] * len(row)
        return [""] * len(row)

    styled_df = df.style.apply(highlight_top, axis=1)

    # テーブル表示（行選択可能）
    event = st.dataframe(
        styled_df,
        width="stretch",
        hide_index=True,
        column_config={
            "team_id": None,  # team_idは非表示
        },
        on_select="rerun",
        selection_mode="single-row",
        key=key,
    )

    # 選択された行からteam_idとround_numberを取得
    if event.selection and event.selection.rows:  # type: ignore[attr-defined]
        selected_row_index = event.selection.rows[0]  # type: ignore[attr-defined]
        selected_team_id: str = df.iloc[selected_row_index]["team_id"]
        selected_round_number: int = int(df.iloc[selected_row_index]["ラウンド"])
        return (selected_team_id, selected_round_number)

    return None
