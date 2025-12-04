"""RoundController - ラウンドライフサイクル管理

単一チームのラウンド実行を管理するコンポーネント。
Leader Agent実行、Evaluator呼び出し、DuckDB記録を担当。

将来的に複数ラウンド対応、状態管理、終了判定ロジックを追加予定。
詳細はspecs/001-specs/spec.mdを参照。
"""

from mixseek.round_controller.controller import RoundController
from mixseek.round_controller.models import OnRoundCompleteCallback, RoundState

__all__ = ["OnRoundCompleteCallback", "RoundController", "RoundState"]
