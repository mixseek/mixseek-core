"""結果ページ - リーダーボード・ラウンド進捗・スコア推移表示UI.

ラウンドタイムライン、スコア推移グラフを含む統合結果ページ。

References:
    - Spec: specs/014-ui/spec.md (User Story 2, User Story 5)
    - Develop: Existing leaderboard and submission features
"""

import streamlit as st

from mixseek.ui.components.leaderboard_table import render_leaderboard_table
from mixseek.ui.components.score_chart import render_score_chart
from mixseek.ui.services.leaderboard_service import (
    fetch_leaderboard,
    fetch_team_submission,
    fetch_top_submission,
)

st.title("実行結果")

# 実行IDの取得（セッション状態から）
execution_id = st.session_state.get("current_execution_id")

if not execution_id:
    st.warning("実行結果がありません。タスクを実行してください。")
    if st.button("実行ページへ"):
        st.switch_page("pages/1_execution.py")
    st.stop()

# リーダーボード取得
leaderboard = fetch_leaderboard(execution_id)

# トップサブミッション取得
top_submission = fetch_top_submission(execution_id)

# トップサブミッションのハイライト（FR-007）
if top_submission:
    st.subheader("🏆 最高スコアサブミッション")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"**スコア**: {round(top_submission.score)}")
        st.markdown(f"**チーム名**: {top_submission.team_name}")
        st.markdown(f"**チームID**: {top_submission.team_id}")
        st.markdown(f"**ラウンド**: {top_submission.round_number}")
        st.markdown(f"**作成日時**: {top_submission.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    with col2:
        # TODO: 貢献エージェント情報（データモデル拡張後に追加）
        pass

    with st.expander("サブミッション内容"):
        st.markdown(top_submission.submission_content)

    if top_submission.evaluation_feedback:
        with st.expander("評価フィードバック"):
            st.markdown(top_submission.evaluation_feedback)

    st.divider()

# リーダーボードテーブル（FR-008: 行クリックでチーム選択）
st.subheader("リーダーボード")
st.caption("チームの行をクリックすると詳細が表示されます")

selected_entry = render_leaderboard_table(leaderboard)

# チーム詳細ビュー（FR-008）
if selected_entry:
    selected_team_id, selected_round_number = selected_entry
    team_submission = fetch_team_submission(execution_id, selected_team_id, selected_round_number)

    if team_submission:
        st.divider()
        st.subheader(f"チーム詳細: {team_submission.team_name}")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**チームID**: {team_submission.team_id}")
            st.markdown(f"**スコア**: {round(team_submission.score)}")
            st.markdown(f"**ラウンド**: {team_submission.round_number}")
        with col2:
            st.markdown(f"**作成日時**: {team_submission.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

        st.markdown("**サブミッション内容**")
        st.text_area(
            "サブミッション内容",
            value=team_submission.submission_content,
            height=200,
            disabled=True,
            label_visibility="collapsed",
            key=f"submission_content_{selected_team_id}",
        )

        if team_submission.evaluation_feedback:
            st.markdown("**評価フィードバック**")
            st.info(team_submission.evaluation_feedback)

# スコア推移エリア（FR-009, FR-020, SC-010）
st.divider()
st.subheader("スコア推移")
render_score_chart(execution_id)
