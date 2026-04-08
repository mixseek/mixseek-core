"""MixSeek設定の定数定義。"""

# デフォルトプロジェクト名
DEFAULT_PROJECT_NAME: str = "mixseek-project"

# ワークスペース環境変数名
WORKSPACE_ENV_VAR: str = "MIXSEEK_WORKSPACE"

# 設定ファイル再帰深度制限（Phase 13 T107, FR-043）
MAX_CONFIG_RECURSION_DEPTH: int = 10

# センシティブフィールドパターン
SENSITIVE_FIELD_PATTERNS: tuple[str, ...] = (
    "api_key",
    "password",
    "secret",
    "token",
    "credential",
    "private_key",
    "access_key",
)

# 非センシティブフィールド例外（max_tokens はLLMパラメータであり、セキュリティトークンではない）
NON_SENSITIVE_FIELD_EXCEPTIONS: tuple[str, ...] = ("max_tokens",)

# O(1) メンバーシップテスト用の事前計算セット
_NON_SENSITIVE_FIELD_EXCEPTIONS_LOWER: frozenset[str] = frozenset(
    exc.lower() for exc in NON_SENSITIVE_FIELD_EXCEPTIONS
)

# マスク値
MASKED_VALUE: str = "[REDACTED]"
