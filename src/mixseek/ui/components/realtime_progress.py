"""リアルタイム進捗表示コンポーネント.

タスク実行中にStreamlit標準コンポーネントを使用してシンプルな進捗を表示します。

References:
    - リアルタイム進捗表示要件
    - ポーリング更新パフォーマンス要件（2秒間隔）
"""

import pandas as pd
import streamlit as st

from mixseek.ui.services.execution_service import get_all_teams_execution_status, get_execution_status


def render_realtime_progress(execution_id: str) -> None:
    """リアルタイム進捗を表示（実行中のみ）.

    Streamlit標準コンポーネントを使用してシンプルな進捗表示:
    - st.status(): 実行状態表示（実行中/完了/エラー）
    - st.progress(): 進捗バー表示（current_round / total_rounds）
    - st.metric(): 現在ラウンド表示（例: "ラウンド 3/10"）

    Args:
        execution_id: 実行ID

    Note:
        - ステータスがRUNNING以外の場合は何も表示しない
        - エラー時はst.error()でエラーメッセージを表示
        - 2秒間隔ポーリングはページ側で実装
    """
    # 実行状態を取得
    state = get_execution_status(execution_id)

    # 実行中のみ表示
    if not state.is_running:
        return

    # ステータス表示（st.statusコンテナ）
    # エラー詳細は「エラーが発生したチーム」セクション（下部）で表示
    with st.status("タスク実行中...", expanded=True):
        # 進捗バー表示
        if state.progress_percentage is not None:
            st.progress(
                state.progress_percentage,
                text=f"ラウンド {state.current_round}/{state.total_rounds}",
            )

            # メトリック表示（現在ラウンド）
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    label="現在ラウンド",
                    value=f"{state.current_round}/{state.total_rounds}",
                )
            with col2:
                st.metric(
                    label="進捗率",
                    value=f"{state.progress_percentage * 100:.0f}%",
                )
        else:
            # ラウンド情報がまだない場合はスピナー表示
            st.spinner("オーケストレーション準備中...")
            st.info("ラウンド情報を取得中です...")


def render_team_status_cards(execution_id: str) -> None:
    """チーム別ステータスをカード/テーブル形式で表示（実行中のみ）.

    Args:
        execution_id: 実行ID

    Note:
        - チーム数3以下: st.columnsでカード表示（横並び）
        - チーム数4以上: st.dataframeでテーブル表示
        - 実行中でない場合は何も表示しない
    """
    # 全チームの進捗を取得
    teams = get_all_teams_execution_status(execution_id)

    if not teams:
        return

    # 実行中のチームが1つでもあるか確認
    any_running = any(not team.is_completed for team in teams)
    if not any_running:
        return

    st.subheader("📊 チーム別進捗")

    # チーム数に応じて表示形式を切り替え
    if len(teams) <= 3:
        # カード表示（st.columns）
        cols = st.columns(len(teams))
        for idx, team in enumerate(teams):
            with cols[idx]:
                st.metric(
                    label=f"{team.status_icon} {team.team_name}",
                    value=f"{team.agent_display_text} (ラウンド {team.current_round}/{team.total_rounds})",
                )
                # エラーメッセージがある場合は表示
                if team.error_message:
                    st.error(f"エラー: {team.error_message}")
    else:
        # テーブル表示（st.dataframe）
        df = pd.DataFrame(
            [
                {
                    "ステータス": team.status_icon,
                    "チーム名": team.team_name,
                    "エージェント": team.agent_display_text,
                    "現在ラウンド": f"{team.current_round}/{team.total_rounds}",
                }
                for team in teams
            ]
        )
        st.dataframe(df, width="stretch", hide_index=True)

        # エラーがあるチームを個別に表示
        failed_teams = [team for team in teams if team.error_message]
        if failed_teams:
            st.subheader("⚠️ エラーが発生したチーム")
            for team in failed_teams:
                with st.expander(f"{team.team_name} のエラー詳細"):
                    st.error(team.error_message)
