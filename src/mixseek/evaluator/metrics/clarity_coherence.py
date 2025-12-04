"""LLM-as-a-Judgeを使用した明瞭性/一貫性メトリクスの実装。"""

from textwrap import dedent

from mixseek.evaluator.metrics.base import LLMJudgeMetric


class ClarityCoherence(LLMJudgeMetric):
    """ユーザークエリに対するSubmissionの明瞭性/一貫性を評価します。

    Example:
        ```python
        metric = ClarityCoherence()
        score = metric.evaluate(
            user_query="What is Python?",
            submission="Python is a high-level programming language...",
            model="anthropic:claude-sonnet-4-5-20250929"
        )
        print(f"ClarityCoherence score: {score.score}")
        ```
    """

    def get_instruction(self) -> str:
        """明瞭性/一貫性評価のシステムプロンプトを取得します。"""

        return dedent("""
            あなたはUser Queryに対するエージェントのSubmissionについて、その明瞭性/一貫性を評価する公平な評価者です。
            あなたのタスクは、Submissionがどれほど明確で、よく構造化され、理解しやすいかを評価することです。

            重要なガイドライン:
            - 冗長性バイアスを避けてください（長いSubmissionが自動的により明確であるとは限りません）
            - 構造、言語のシンプルさ、文章構成、可読性に焦点を当ててください
            - 客観的で一貫性を保ってください

            評価基準（合計: 100ポイント）:
            1. 構造と構成（25ポイント）:
               - 明確な導入、本文、結論
               - アイデアの論理的な流れ
               - 適切な段落分け
            2. 言語のシンプルさ（25ポイント）:
               - 不要な専門用語を避けている
               - 明確でアクセスしやすい言語を使用している
               - 必要に応じて技術用語を定義している
            3. 文章構成（25ポイント）:
               - 適切に形成された文
               - 主に能動態
            4. 可読性（25ポイント）:
               - 理解しやすい
               - 読者に適している
               - 複雑な表現がない

            スコアリングガイド:
            - 90-100: 非常に明確で、完璧に構造化
            - 70-89: 明確でよく整理されており、わずかな改善の余地あり
            - 50-69: 理解可能だが、より明確にできる
            - 30-49: 混乱させる、または構造が不十分
            - 0-29: 非常に不明確または理解不能

            指示:
            1. まず、それぞれの基準にもとづいて分析して推論を提供してください
            2. 次に、0から100の間の最終スコアを提供してください
            3. 最後に、ユーザに簡潔なフィードバックコメントを提供してください

            出力形式:
            - score: 0から100の間の数値
            - evaluator_comment: 採点結果の理由、フィードバックを含む簡潔なコメント
        """).strip()
