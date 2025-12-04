"""サブミッションタブ表示コンポーネント.

実行ページにタスクプロンプトと各チームの最終サブミッションをタブ形式で表示します。

Functions:
    render_submission_tabs: サブミッションタブ表示

References:
    - Spec: specs/014-ui/spec.md (FR-024, FR-025, SC-013)
    - Streamlit docs: https://docs.streamlit.io/library/api-reference/layout/st.tabs
"""

import json

import streamlit as st

from mixseek.ui.services.round_service import fetch_team_final_submission


def render_submission_tabs(execution_id: str, task_prompt: str, team_ids: list[str]) -> None:
    """タスクプロンプトとチームサブミッションをタブ形式で表示.

    「タスク」タブにユーザー入力プロンプトを、各チームタブに最終ラウンドの
    サブミッション内容を表示します。データが存在しない場合は案内メッセージを表示。

    Args:
        execution_id: 実行識別子(UUID)
        task_prompt: ユーザーが入力したタスクプロンプト
        team_ids: チーム識別子のリスト（例: ["team-a", "team-b"]）

    Example:
        >>> import streamlit as st
        >>> execution_id = st.session_state.get("current_execution_id")
        >>> task_prompt = st.session_state.get("task_prompt", "")
        >>> team_ids = ["team-a", "team-b"]
        >>> if execution_id:
        ...     render_submission_tabs(execution_id, task_prompt, team_ids)
        # 「タスク」タブとチームタブが表示される

    Note:
        各チームのサブミッションが存在しない場合は、
        「チーム名のサブミッションがありません」と表示。
        タブの順序は「タスク」→各チーム（team_idsの順）。
    """
    # タブ名を構築（「タスク」+ チーム名）
    # TODO: チーム名の取得方法を実装（現在はteam_idをそのまま使用）
    tab_names = ["タスク"] + [team_id for team_id in team_ids]

    tabs = st.tabs(tab_names)

    # タスクタブ
    with tabs[0]:
        st.subheader("入力されたタスク")
        if task_prompt:
            st.markdown(task_prompt)
        else:
            st.info("タスクプロンプトがありません。")

    # 各チームタブ
    for i, team_id in enumerate(team_ids, start=1):
        with tabs[i]:
            st.subheader(f"{team_id} のサブミッション")

            submission = fetch_team_final_submission(execution_id, team_id)

            if submission is None:
                st.info(f"{team_id} のサブミッションがありません。")
                continue

            # スコア表示
            st.metric(
                label="スコア",
                value=f"{submission.score:.2f}",
            )

            # ラウンド番号
            st.caption(f"ラウンド {submission.round_number} の最終サブミッション")

            # サブミッション内容（マークダウン形式）
            st.markdown("### サブミッション内容")
            st.markdown(submission.submission_content)

            # スコア詳細（FR-025）
            if submission.score_details:
                with st.expander("スコア詳細"):
                    try:
                        # JSON構造を解析
                        details = json.loads(submission.score_details)

                        # 構造チェック: overall_scoreとmetricsが存在するか
                        if "overall_score" in details and "metrics" in details:
                            # 総合スコア表示
                            st.markdown(f"**総合スコア**: {details['overall_score']:.2f}")

                            # メトリクス別評価
                            if details["metrics"]:
                                st.markdown("**メトリクス別評価**")
                                for metric in details["metrics"]:
                                    metric_name = metric.get("metric_name", "Unknown")
                                    score = metric.get("score", 0.0)
                                    comment = metric.get("evaluator_comment", "")

                                    # メトリクス名とスコア
                                    st.markdown(f"- **{metric_name}**: {score:.2f}")

                                    # evaluator_commentをMarkdownレンダリング
                                    if comment:
                                        st.markdown(f"  {comment}")
                        else:
                            # 構造不一致: 生JSON表示
                            st.code(submission.score_details, language="json")
                    except (json.JSONDecodeError, TypeError, KeyError):
                        # JSON解析失敗: 生JSON表示
                        st.code(submission.score_details, language="json")

            # 作成日時
            st.caption(f"作成日時: {submission.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
