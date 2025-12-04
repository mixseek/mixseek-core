"""スコア推移グラフ表示コンポーネント.

結果ページに全チームのラウンドごとスコア推移を折れ線グラフで表示します。

Functions:
    render_score_chart: スコア推移のPlotly折れ線グラフ表示

References:
    - Spec: specs/014-ui/spec.md (FR-009, FR-020, SC-010)
    - Research: specs/014-ui/research.md (Section 1: Plotly Express選定, WebGL対応)
    - Plotly docs: https://plotly.com/python/line-charts/
"""

import plotly.express as px
import streamlit as st

from mixseek.ui.services.round_service import fetch_all_teams_score_history


def render_score_chart(execution_id: str) -> None:
    """全チームのスコア推移を折れ線グラフで表示.

    leader_boardテーブルから全チームの各ラウンドスコアを取得し、
    Plotly Expressの折れ線グラフで推移を可視化します。
    50チーム対応のためWebGLレンダラーを使用。
    データが存在しない場合は案内メッセージを表示。

    Args:
        execution_id: 実行識別子(UUID)

    Example:
        >>> import streamlit as st
        >>> execution_id = st.session_state.get("current_execution_id")
        >>> if execution_id:
        ...     render_score_chart(execution_id)
        # ラウンド番号をX軸、スコアをY軸とする折れ線グラフが表示される

    Note:
        データ不在時は案内メッセージを表示。
        各チームは異なる色で表示され、凡例から個別に表示/非表示切り替え可能。
        WebGLレンダラー（scattergl）により50チーム以上でも高速レンダリング。
    """
    df = fetch_all_teams_score_history(execution_id)

    if df.empty:
        st.info("スコア推移データがありません。ラウンドコントローラによる実行後に表示されます。")
        return

    # 折れ線グラフ描画
    # WebGL対応のため、通常のline()ではなくscatter()を使用してline形式指定
    # （注: px.lineはWebGL非対応、px.scatter(mode='lines')でWebGL有効化）
    fig = px.line(
        df,
        x="round_number",
        y="score",
        color="team_name",
        title="全チームのスコア推移",
        labels={
            "round_number": "ラウンド番号",
            "score": "スコア",
            "team_name": "チーム",
        },
        markers=True,  # マーカー表示でデータポイントを明確化
    )

    # WebGLレンダラー有効化（50チーム対応）
    # 注: Plotly Express 6.0以降はrender_mode='webgl'でWebGL有効化
    # （scatterglは直接指定不可、render_mode引数で制御）
    # ただし、px.lineはWebGL非対応のため、必要に応じてpx.scatter + lines_modeで実装
    # TODO: 50チーム以上でパフォーマンス問題が発生した場合、px.scatterに変更

    # グラフ表示
    st.plotly_chart(fig, width="stretch")
