"""History table component."""

import pandas as pd
import streamlit as st

from mixseek.ui.models.history import HistoryEntry


def render_history_table(entries: list[HistoryEntry], key: str = "history_selection") -> str | None:
    """履歴テーブルをレンダリング.

    Args:
        entries: 履歴エントリのリスト
        key: セッション状態のキー（デフォルト: "history_selection"）

    Returns:
        str | None: 選択された実行ID（行クリック時）
    """
    if not entries:
        st.info("実行履歴がありません。タスクを実行すると履歴が記録されます。")
        if st.button("実行ページへ"):
            st.switch_page("pages/1_execution.py")
        return None

    # DataFrameに変換
    df = pd.DataFrame(
        [
            {
                "実行ID": entry.execution_id[:8] + "...",
                "プロンプト": entry.prompt_preview,
                "最高スコアチーム": entry.best_team_display,
                "ステータス": entry.status.value if hasattr(entry.status, "value") else entry.status,
                "実行日時": entry.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "full_execution_id": entry.execution_id,
            }
            for entry in entries
        ]
    )

    # テーブル表示（行選択可能）
    event = st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        column_config={
            "full_execution_id": None,  # full_execution_idは非表示
        },
        on_select="rerun",
        selection_mode="single-row",
        key=key,
    )

    # 選択された行からexecution_idを取得
    if event.selection and event.selection.rows:  # type: ignore[attr-defined]
        selected_row_index = event.selection.rows[0]  # type: ignore[attr-defined]
        selected_execution_id: str = df.iloc[selected_row_index]["full_execution_id"]
        return selected_execution_id

    return None
