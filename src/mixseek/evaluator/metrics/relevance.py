"""LLM-as-a-Judgeを使用した関連性メトリクスの実装。"""

from textwrap import dedent

from mixseek.evaluator.metrics.base import LLMJudgeMetric


class Relevance(LLMJudgeMetric):
    """ユーザークエリに対するSubmissionの関連性を評価します。

    Example:
        ```python
        metric = Relevance()
        score = metric.evaluate(
            user_query="What is Python?",
            submission="Python is a high-level programming language...",
            model="anthropic:claude-sonnet-4-5-20250929"
        )
        print(f"Relevance score: {score.score}")
        ```
    """

    def get_instruction(self) -> str:
        """関連性評価のシステムプロンプトを取得します。"""

        return dedent("""
            あなたはUser Queryに対するエージェントのSubmissionについて、その関連性を評価する公平な評価者です。

            あなたのタスクは、Submissionがユーザーのクエリに対してどれほど直接的かつ適切に対応しているかを評価することです。

            重要なガイドライン:
            - Submissionが実際に問われたことに答えているかどうかに焦点を当ててください
            - 脱線や無関係な情報にペナルティを課してください
            - 客観的で一貫性を保ってください


            評価基準（合計: 100ポイント）:
            1. クエリへの直接的な回答（40ポイント）:
               - 質問に直接対応している
               - ユーザーのニーズに的確である
               - 大きな脱線がない

            2. 文脈上の適切性（30ポイント）:
               - クエリの文脈に適合している
               - 適切な範囲と詳細レベルである
               - ユーザーの意図に関連している

            3. フォーカスと簡潔性（30ポイント）:
               - 全体を通してトピックを維持している
               - 無関係な情報を避けている
               - 効率的なコミュニケーションである

            スコアリングガイド:
            - 90-100: 高度に関連性があり、クエリに直接回答、脱線なし
            - 70-89: ほぼ関連性があり、わずかに脱線した内容
            - 50-69: やや関連性があるが、トピック外の情報を含む
            - 30-49: 部分的に関連性があり、大きな脱線
            - 0-29: 無関係または要点を外している

            指示:
            1. まず、それぞれの基準にもとづいて分析して推論を提供してください
            2. 次に、0から100の間の最終スコアを提供してください
            3. 最後に、ユーザに簡潔なフィードバックコメントを提供してください

            出力形式:
            - score: 0から100の間の数値
            - evaluator_comment: 採点結果の理由、フィードバックを含む簡潔なコメント
        """).strip()
