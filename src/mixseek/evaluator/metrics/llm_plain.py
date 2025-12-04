"""LLM-as-a-Judgeを使用した汎用評価メトリクスの実装。"""

from textwrap import dedent

from mixseek.evaluator.metrics.base import LLMJudgeMetric


class LLMPlain(LLMJudgeMetric):
    """LLM-as-a-Judgeによるメトリックのプレースホルダー。

    このメトリックは、system_instructionをTOML設定で上書きすることを前提としています。

    Example:
        ```python
        metric = LLMPlain()
        # カスタムsystem_instructionで評価
        custom_instruction = "Evaluate the technical accuracy of the response."
        score = metric.evaluate(
            user_query="What is Python?",
            submission="Python is a high-level programming language...",
            model="anthropic:claude-sonnet-4-5-20250929",
            system_instruction=custom_instruction
        )
        print(f"LLMPlain score: {score.score}")
        ```
    """

    def get_instruction(self) -> str:
        """評価を行うLLMのシステムプロンプトを取得します。

        TOML設定でsystem_instructionを指定することで、カスタマイズされた
        評価基準に置き換えることができます。
        以下のテンプレートをコピペして使うことが可能ですが、
        必ずしもこの形式に従う必要はありません。
        """

        return dedent("""
            あなたはUser Queryに対するエージェントのSubmissionを評価する公平な評価者です。

            重要なガイドライン:
            -
            -
            -

            評価基準（合計: 100ポイント）:
            1.
            2.
            3.

            スコアリングガイド:
            - 90-100: 優れた品質、すべての基準を満たしている
            - 70-89: 良好な品質、わずかな改善の余地あり
            - 50-69: 普通の品質、いくつかの問題がある
            - 30-49: 低い品質、大きな改善が必要
            - 0-29: 非常に低い品質、不適切

            指示:
            1. まず、それぞれの基準にもとづいて分析して推論を提供してください
            2. 次に、0から100の間の最終スコアを提供してください
            3. 最後に、ユーザに簡潔なフィードバックコメントを提供してください

            出力形式:
            - score: 0から100の間の数値
            - evaluator_comment: 採点結果の理由、フィードバックを含む簡潔なコメント
        """).strip()
