"""Common validation functions for configuration schemas.

This module provides reusable validation logic to eliminate code duplication
across settings classes (Article 10: DRY).

Constitution Compliance:
    - Article 10 (DRY): Eliminates duplicate validation logic (97% similarity)
    - Article 9 (Data Accuracy): Explicit error messages with clear guidance
    - Article 16 (Type Safety): Comprehensive type annotations
    - Article 8 (Code Quality): Clean, well-documented code
"""


def validate_model_format(value: str, allow_empty: bool = False) -> str:
    """モデル形式のバリデーション（provider:model-name形式）。

    この関数は以下の設定クラスで共通利用されます：
    - LeaderAgentSettings.validate_model
    - EvaluatorSettings.validate_default_model
    - MemberAgentSettings.validate_model

    Args:
        value: モデル形式文字列
        allow_empty: 空文字列を許容するか（デフォルト: False）
            - True: 空文字列やホワイトスペースのみの文字列を許容
            - False: 空文字列を拒否し、ValidationErrorを発生させる

    Returns:
        バリデーション済みのモデル形式（入力値をそのまま返す）

    Raises:
        ValueError: 以下の場合に発生
            - 形式が不正な場合（コロン `:` が含まれていない）
            - allow_empty=False で空文字列が渡された場合

    Examples:
        基本的な使用法（LeaderAgentSettings、EvaluatorSettings）:

        >>> validate_model_format("google-gla:gemini-2.5-flash-lite")
        'google-gla:gemini-2.5-flash-lite'

        >>> validate_model_format("gpt-4o")  # コロンなし
        Traceback (most recent call last):
        ...
        ValueError: Invalid model format: 'gpt-4o'. Expected format: 'provider:model-name'

        空文字列を許容する場合（MemberAgentSettings）:

        >>> validate_model_format("", allow_empty=True)
        ''

        >>> validate_model_format("")  # デフォルトでは拒否
        Traceback (most recent call last):
        ...
        ValueError: Invalid model format: ''. Expected format: 'provider:model-name'

    Design Rationale:
        この関数は以下の設計判断に基づいています：
        1. **Article 10準拠**: LeaderAgentSettings、EvaluatorSettings、MemberAgentSettingsで
           重複していたバリデーションロジック（97%一致）を統合
        2. **空文字列の扱い**: MemberAgentSettingsのみ空文字列を許容するため、
           `allow_empty`パラメータで制御
        3. **エラーメッセージ**: Article 9に従い、明示的で理解しやすいエラーメッセージを提供
    """
    # allow_empty=True の場合、空文字列やホワイトスペースのみの文字列を許容
    if allow_empty and not value.strip():
        return value

    # モデル形式のバリデーション（provider:model-name形式）
    if ":" not in value:
        raise ValueError(f"Invalid model format: '{value}'. Expected format: 'provider:model-name'")

    return value
