"""プリフライトチェック データモデル

チェック結果を表現するデータモデルを定義する。
"""

from enum import Enum

from pydantic import BaseModel


class CheckStatus(str, Enum):
    """チェック結果ステータス"""

    OK = "ok"
    WARN = "warn"
    ERROR = "error"
    SKIPPED = "skipped"


class CheckResult(BaseModel):
    """個別チェック項目の結果"""

    name: str
    status: CheckStatus
    message: str = ""
    source_file: str | None = None


class CategoryResult(BaseModel):
    """カテゴリ単位の検証結果"""

    category: str
    checks: list[CheckResult] = []

    @property
    def has_errors(self) -> bool:
        """ERROR ステータスのチェックが含まれるか"""
        return any(c.status == CheckStatus.ERROR for c in self.checks)


class PreflightResult(BaseModel):
    """プリフライトチェック全体の結果"""

    categories: list[CategoryResult] = []

    @property
    def is_valid(self) -> bool:
        """全カテゴリにエラーがないか"""
        return not any(cat.has_errors for cat in self.categories)

    @property
    def error_count(self) -> int:
        """ERROR ステータスの総数"""
        return sum(1 for cat in self.categories for c in cat.checks if c.status == CheckStatus.ERROR)

    @property
    def warn_count(self) -> int:
        """WARN ステータスの総数"""
        return sum(1 for cat in self.categories for c in cat.checks if c.status == CheckStatus.WARN)
