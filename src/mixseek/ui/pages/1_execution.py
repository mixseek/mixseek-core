"""実行ページ - タスク実行UI.

ラウンド進捗表示、チーム進捗一覧、サブミッションタブを含む統合実行ページ。

References:
    - Spec: specs/014-ui/spec.md (User Story 1)
    - Develop: Existing execution service and orchestration selector
"""

import time

import streamlit as st

from mixseek.ui.components.log_viewer import render_log_viewer
from mixseek.ui.components.orchestration_selector import render_orchestration_selector
from mixseek.ui.components.realtime_progress import render_realtime_progress, render_team_status_cards
from mixseek.ui.components.round_progress import render_round_progress
from mixseek.ui.components.submission_tabs import render_submission_tabs
from mixseek.ui.components.team_progress import render_team_progress_list
from mixseek.ui.models.execution import Execution, ExecutionStatus
from mixseek.ui.services.execution_service import (
    get_execution_result,
    get_execution_status,
    get_team_ids_for_execution,
    run_orchestration_in_background,
)

# セッション状態初期化
if "is_running" not in st.session_state:
    st.session_state.is_running = False
if "current_execution_result" not in st.session_state:
    st.session_state.current_execution_result = None
if "current_execution_id" not in st.session_state:
    st.session_state.current_execution_id = None
if "task_prompt" not in st.session_state:
    st.session_state.task_prompt = ""
if "polling_enabled" not in st.session_state:
    st.session_state.polling_enabled = False

st.title("タスク実行")

# ポーリングループ（FR-004, SC-011）
if st.session_state.polling_enabled and st.session_state.current_execution_id:
    # 実行状態を取得
    state = get_execution_status(st.session_state.current_execution_id)

    # リアルタイム進捗表示
    render_realtime_progress(st.session_state.current_execution_id)

    # チーム別ステータス表示
    render_team_status_cards(st.session_state.current_execution_id)

    # 実行ログ表示（FR-026）
    render_log_viewer(lines=100, expanded=False)

    if state.is_completed:
        # 実行完了 → ポーリング停止
        st.session_state.polling_enabled = False
        st.session_state.is_running = False

        # 実行結果を取得して保存
        execution_result = get_execution_result(st.session_state.current_execution_id)
        if execution_result:
            st.session_state.current_execution_result = execution_result.model_dump()

        # 完了ステータスに応じてメッセージ表示
        # エラー詳細は「エラーが発生したチーム」セクション（realtime_progress.py）で表示
        if state.status == ExecutionStatus.COMPLETED:
            st.success("✅ 実行完了しました！")
        elif state.status == ExecutionStatus.FAILED:
            st.error("❌ 実行に失敗しました。詳細は下部の「エラーが発生したチーム」を確認してください。")
        elif state.status == ExecutionStatus.PARTIAL_FAILURE:
            st.warning("⚠️ 一部のチームが失敗しました。詳細は下部の「エラーが発生したチーム」を確認してください。")

        # DuckDBロック解放を待つため5秒待機
        # Orchestratorの非同期処理完了とDB接続クローズを待つ
        time.sleep(5)

        # ページを再レンダリング（詳細表示に切り替え）
        st.rerun()
    else:
        # 実行中 → 2秒後に再レンダリング
        time.sleep(2)
        st.rerun()

# ラウンド進捗表示（FR-022, SC-011）- 実行完了後のみ表示
if st.session_state.current_execution_id and not st.session_state.polling_enabled and not st.session_state.is_running:
    render_round_progress(st.session_state.current_execution_id)

    # 実行ログ表示（実行完了後も参照可能）
    render_log_viewer(lines=100, expanded=False)

    st.divider()

# オーケストレーション選択
selected_orchestration = render_orchestration_selector()

# タスクプロンプト入力
prompt = st.text_area(
    "タスクプロンプト",
    height=200,
    placeholder="実行するタスクの内容を入力してください...",
    help="エージェントに実行させたいタスクを記述してください",
)

# 実行ボタン（実行中は無効化）
execute_button = st.button(
    "実行",
    disabled=st.session_state.is_running,
    type="primary",
)

# 実行中警告
if st.session_state.is_running:
    st.warning("タスク実行中です。完了するまでお待ちください。")

# 実行ボタンクリック時の処理
if execute_button:
    # バリデーション
    if not selected_orchestration:
        st.error("オーケストレーションを選択してください。")
    elif not prompt.strip():
        st.error("タスクプロンプトを入力してください。")
    else:
        # バックグラウンド実行開始
        try:
            execution_id = run_orchestration_in_background(prompt, selected_orchestration)

            # セッション状態を更新
            st.session_state.is_running = True
            st.session_state.polling_enabled = True
            st.session_state.current_execution_id = execution_id
            st.session_state.task_prompt = prompt

            # 即座に再レンダリング（ポーリング開始）
            st.rerun()

        except Exception as e:
            st.error(f"実行開始に失敗しました: {e}")
            st.session_state.is_running = False
            st.session_state.polling_enabled = False

# 詳細表示エリア（実行完了後のみ表示）
if st.session_state.current_execution_id and not st.session_state.polling_enabled and not st.session_state.is_running:
    # チーム進捗一覧表示（FR-023, SC-012）
    st.divider()
    st.subheader("チーム進捗確認")
    render_team_progress_list(st.session_state.current_execution_id)

    # 実行結果表示（FR-005）
    if st.session_state.current_execution_result:
        result = st.session_state.current_execution_result

        st.divider()
        st.subheader("実行結果")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("ステータス", result["status"])
        with col2:
            st.metric("実行ID", result["execution_id"][:8] + "...")
        with col3:
            if result.get("duration_seconds"):
                st.metric("実行時間", f"{result['duration_seconds']:.2f}秒")

        # Executionモデルを再構築してresult_summaryプロパティを利用（DRY原則）
        execution = Execution(**result)
        if execution.result_summary:
            st.markdown("**結果サマリー**")
            st.info(execution.result_summary)

        # 失敗したチームの情報表示
        if execution.failed_teams_info:
            st.markdown("**エラーが発生したチーム**")
            for failed_team in execution.failed_teams_info:
                with st.expander(f"❌ {failed_team.team_name}", expanded=False):
                    st.code(failed_team.error_message, language="text")

    # サブミッションタブ表示（FR-024, SC-013）
    st.divider()
    st.subheader("サブミッション")

    # execution_idから動的にチームIDのリストを取得
    team_ids = get_team_ids_for_execution(st.session_state.current_execution_id)

    # チームが存在する場合のみタブを表示
    if team_ids:
        # task_promptがセッション状態にない場合、execution_resultから取得
        task_prompt = st.session_state.task_prompt
        if not task_prompt and st.session_state.current_execution_result:
            task_prompt = st.session_state.current_execution_result.get("prompt", "")

        # それでもない場合は、execution_summaryから直接取得
        if not task_prompt:
            result = get_execution_result(st.session_state.current_execution_id)
            if result:
                task_prompt = result.prompt
                # セッション状態に保存
                st.session_state.current_execution_result = result.model_dump()

        if task_prompt:
            render_submission_tabs(st.session_state.current_execution_id, task_prompt, team_ids)
        else:
            st.warning("タスクプロンプトを取得できませんでした。")
    else:
        st.info("サブミッションデータがまだ利用できません。実行が完了するまでお待ちください。")

# ページナビゲーション
st.divider()
col1, col2 = st.columns(2)
with col2:
    if st.button("📜 実行履歴を見る", width="stretch"):
        st.switch_page("pages/3_history.py")
