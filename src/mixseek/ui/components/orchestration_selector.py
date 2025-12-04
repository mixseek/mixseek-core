"""Orchestration selector component."""

import streamlit as st

from mixseek.ui.models.config import OrchestrationOption
from mixseek.ui.services.config_service import get_all_orchestration_options


def render_orchestration_selector() -> OrchestrationOption | None:
    """オーケストレーション選択ドロップダウンをレンダリング.

    Returns:
        OrchestrationOption | None: 選択されたオーケストレーション（未選択時はNone）
    """
    options = get_all_orchestration_options()

    if not options:
        st.warning("設定ファイルが見つかりません。設定ページで作成してください。")
        # TODO: 設定ページへのリンク追加（設定ページ実装後）
        return None

    # display_labelのリストを作成
    display_labels = [opt.display_label for opt in options]

    # セレクトボックスを表示
    selected_label = st.selectbox(
        "オーケストレーション",
        options=display_labels,
        key="selected_orchestration_label",
        help="実行するオーケストレーション設定を選択してください",
    )

    # 選択されたオプションを返す
    selected_option = next((opt for opt in options if opt.display_label == selected_label), None)

    return selected_option
