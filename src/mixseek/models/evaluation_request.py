"""評価リクエストモデル。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from mixseek.models.evaluation_config import EvaluationConfig


class EvaluationRequest(BaseModel):
    """AIエージェントのSubmissionを評価するためのリクエスト。

    このモデルは、ユーザーのクエリ、AIエージェントのSubmission、
    評価のための文脈情報を含むEvaluatorコンポーネントへの入力を表します。

    Attributes:
        user_query: ユーザーからの元のクエリ
        submission: AIエージェントによって生成されたSubmission
        execution_id: この評価に関連する実行ID（オプション）
        team_id: Submissionを生成したチームの識別子（オプション）
        round_number: この評価に関連するラウンド番号（オプション）
        config: オプションのカスタム評価設定（デフォルトをオーバーライド）

    Example:
        ```python
        from mixseek.models.evaluation_request import EvaluationRequest

        request = EvaluationRequest(
            user_query="What are the benefits of Python?",
            submission="Python is a versatile programming language...",
            execution_id="exec-20260220-001",
            team_id="team-alpha-001",
            round_number=1,
        )
        ```

    Validation Rules:
        - user_query: 空または空白のみにはできない（FR-013）
        - submission: 空または空白のみにはできない（FR-013）
        - execution_id: Noneまたは空でない文字列でなければならない
        - team_id: Noneまたは空でない文字列でなければならない
        - round_number: Noneまたは1以上の整数でなければならない
    """

    user_query: str = Field(
        ...,
        description="ユーザーからの元のクエリ",
        min_length=1,
        examples=["What are the benefits of Python?"],
    )

    submission: str = Field(
        ...,
        description="評価されるAIエージェントによって生成されたSubmission",
        min_length=1,
        examples=["Python is a versatile programming language..."],
    )

    execution_id: str | None = Field(
        None,
        description="この評価に関連する実行ID（オプション）",
        examples=["exec-20260220-001", None],
    )

    team_id: str | None = Field(
        None,
        description="このSubmissionを生成したチームの識別子（オプション）",
        examples=["team-alpha-001", None],
    )

    round_number: int | None = Field(
        None,
        description="この評価に関連するラウンド番号（オプション）",
        ge=1,
        examples=[1, 3, None],
    )

    config: EvaluationConfig | None = Field(
        None, description="オプションのカスタム評価設定（TOMLからのデフォルトをオーバーライド）"
    )

    @field_validator("user_query")
    @classmethod
    def validate_user_query_not_empty(cls, v: str) -> str:
        """ユーザークエリが空または空白のみでないことを検証します。

        Raises:
            ValueError: クエリが空または空白のみの場合（FR-013）
        """
        if not v or not v.strip():
            raise ValueError(
                "User query cannot be empty or whitespace-only. Please provide a valid query for evaluation."
            )
        return v.strip()

    @field_validator("submission")
    @classmethod
    def validate_submission_not_empty(cls, v: str) -> str:
        """Submissionが空または空白のみでないことを検証します。

        Raises:
            ValueError: Submissionが空または空白のみの場合（FR-013）
        """
        if not v or not v.strip():
            raise ValueError("AI response cannot be empty or whitespace-only. Cannot evaluate empty responses.")
        return v.strip()

    @field_validator("execution_id")
    @classmethod
    def validate_execution_id_not_empty(cls, v: str | None) -> str | None:
        """実行IDがNoneまたは空でない文字列であることを検証します。

        Raises:
            ValueError: 実行IDが空文字列または空白のみの場合
        """
        if v is None:
            return None
        if not v or not v.strip():
            raise ValueError("Execution ID cannot be empty or whitespace-only when provided")
        return v.strip()

    @field_validator("team_id")
    @classmethod
    def validate_team_id_not_empty(cls, v: str | None) -> str | None:
        """チームIDがNoneまたは空でない文字列であることを検証します。

        Raises:
            ValueError: チームIDが空文字列または空白のみの場合
        """
        # Noneの場合は許可
        if v is None:
            return None

        # 文字列が提供された場合、空でないことを検証
        if not v or not v.strip():
            raise ValueError("Team ID cannot be empty or whitespace-only when provided")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_query": "What are the key features of Python 3.13?",
                    "submission": "Python 3.13 introduces several key features including...",
                    "execution_id": "exec-20260220-001",
                    "team_id": "team-alpha-001",
                    "round_number": 1,
                    "config": None,
                },
                {
                    "user_query": "What are the key features of Python 3.13?",
                    "submission": "Python 3.13 introduces several key features including...",
                    "execution_id": None,
                    "team_id": None,
                    "round_number": None,
                    "config": None,
                },
            ]
        }
    }
