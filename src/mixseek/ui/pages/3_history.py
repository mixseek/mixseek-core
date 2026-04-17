"""履歴ページ - 実行履歴UI."""

import streamlit as st

from mixseek.ui.components.history_table import render_history_table
from mixseek.ui.models.execution import ExecutionStatus
from mixseek.ui.services.history_service import fetch_execution_detail, fetch_history
from mixseek.ui.services.leaderboard_service import fetch_top_submission

# セッション状態初期化
if "history_page_number" not in st.session_state:
    st.session_state.history_page_number = 1
if "history_sort_order" not in st.session_state:
    st.session_state.history_sort_order = "desc"
if "history_status_filter" not in st.session_state:
    st.session_state.history_status_filter = None

st.title("実行履歴")

# フィルタ・ソートコントロール
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    sort_order = st.selectbox(
        "ソート順",
        options=["降順（新しい順）", "昇順（古い順）"],
        key="sort_order_select",
    )
    st.session_state.history_sort_order = "desc" if "降順" in sort_order else "asc"

with col2:
    status_options = ["すべて"] + [status.value for status in ExecutionStatus]
    selected_status = st.selectbox(
        "ステータス絞り込み",
        options=status_options,
        key="status_filter_select",
    )
    if selected_status == "すべて":
        st.session_state.history_status_filter = None
    else:
        st.session_state.history_status_filter = ExecutionStatus(selected_status)

with col3:
    if st.button("フィルタ解除"):
        st.session_state.history_status_filter = None
        st.session_state.history_page_number = 1
        st.rerun()

# 履歴取得
entries, total_count = fetch_history(
    page_number=st.session_state.history_page_number,
    page_size=50,
    sort_order=st.session_state.history_sort_order,
    status_filter=st.session_state.history_status_filter,
)

# フィルタ後データなし警告
if total_count == 0 and st.session_state.history_status_filter:
    st.warning("該当する実行履歴が見つかりません。")
    if st.button("フィルタを解除"):
        st.session_state.history_status_filter = None
        st.rerun()
    st.stop()

# 履歴テーブル（行クリックで詳細表示）
st.caption("実行履歴の行をクリックすると詳細が表示されます")
selected_execution_id = render_history_table(entries)

# ページネーション
if total_count > 50:
    total_pages = (total_count + 49) // 50
    st.markdown(f"**ページ {st.session_state.history_page_number} / {total_pages}** （総件数: {total_count}）")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("← 前へ", disabled=st.session_state.history_page_number == 1):
            st.session_state.history_page_number -= 1
            st.rerun()
    with col3:
        if st.button("次へ →", disabled=st.session_state.history_page_number == total_pages):
            st.session_state.history_page_number += 1
            st.rerun()

# 実行詳細ビュー
if selected_execution_id:
    execution = fetch_execution_detail(selected_execution_id)
    top_submission = fetch_top_submission(selected_execution_id)

    if execution:
        st.divider()
        st.subheader("実行詳細")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**実行ID**: {execution.execution_id}")
            status_text = execution.status.value if hasattr(execution.status, "value") else execution.status
            st.markdown(f"**ステータス**: {status_text}")
            if execution.best_team_id:
                st.markdown(f"**最高スコアチーム**: {execution.best_team_id}")
        with col2:
            st.markdown(f"**実行時刻**: {execution.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if execution.completed_at:
                st.markdown(f"**完了時刻**: {execution.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if execution.duration_seconds:
                st.markdown(f"**実行時間**: {execution.duration_seconds:.2f}秒")
            if execution.best_score is not None:
                score_display = round(execution.best_score)  # 整数に四捨五入（既に0-100の範囲）
                st.markdown(f"**最高スコア**: {score_display}")

        st.markdown("**プロンプト**")
        st.text_area("プロンプト", value=execution.prompt, height=150, disabled=True, label_visibility="collapsed")

        if execution.result_summary:
            st.markdown("**結果サマリー**")
            st.info(execution.result_summary)

        # トップサブミッション表示
        if top_submission:
            st.divider()
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

        # TODO: 使用されたLeader Agent・Member Agent情報（データモデル拡張後）

# ページナビゲーション
st.divider()
if st.button("🚀 新しいタスクを実行", width="stretch", type="primary"):
    st.switch_page("pages/1_execution.py")
