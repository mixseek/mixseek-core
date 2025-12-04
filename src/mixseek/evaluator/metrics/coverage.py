"""LLM-as-a-Judgeを使用した包括性メトリクスの実装。"""

from textwrap import dedent

from mixseek.evaluator.metrics.base import LLMJudgeMetric


class Coverage(LLMJudgeMetric):
    """ユーザークエリに対するSubmissionの包括性を評価します。

    Example:
        ```python
        metric = Coverage()
        score = metric.evaluate(
            user_query="What is Python?",
            submission="Python is a high-level programming language...",
            model="anthropic:claude-sonnet-4-5-20250929"
        )
        print(f"Coverage score: {score.score}")
        ```
    """

    def get_instruction(self) -> str:
        """包括性評価のシステムプロンプトを取得します。"""
        return dedent("""
            あなたはUser Queryに対するエージェントのSubmissionについて、その包括性を評価する公平な評価者です。
            あなたのタスクは、Submissionがユーザーのクエリに対してどれほど徹底的かつ完全に対応しているかを評価することです。

            重要なガイドライン:
            - 長いSubmissionが自動的により包括的であるとは限りません
            - カバレッジ、深さ、例、完全性に焦点を当ててください
            - 客観的で一貫性を保ってください

            評価基準（合計: 100ポイント）：
                1. 主要トピックのカバレッジ（40ポイント）：
                    - すべての主要な側面に対応
                    - 重要な欠落なし
                    - 適切な幅のカバレッジである
                2. 説明の深さ（30ポイント）：
                    - 十分な詳細が提供されている
                    - 表面的または軽薄でない
                    - 必要な箇所で徹底的な分析がある
                3. 完全性（30ポイント）：
                    - クエリのすべての部分に対応している
                    - 未回答のサブクエスチョンがない
                    - 完全で満足のいく内容である

            スコアリングガイド：
            - 90-100: 包括的で、深く、すべての側面を徹底的にカバー
            - 70-89: バランスが取れており、ほとんどの側面をカバー、わずかなギャップの可能性
            - 50-69: 適切なカバレッジだが、詳細が欠けている
            - 30-49: カバレッジに大きなギャップ
            - 0-29: 不完全または表面的

            指示:
            1. まず、それぞれの基準にもとづいて分析して推論を提供してください
            2. 次に、0から100の間の最終スコアを提供してください
            3. 最後に、ユーザに簡潔なフィードバックコメントを提供してください

            出力形式:
            - score: 0から100の間の数値
            - evaluator_comment: 採点結果の理由、フィードバックを含む簡潔なコメント
        """).strip()
