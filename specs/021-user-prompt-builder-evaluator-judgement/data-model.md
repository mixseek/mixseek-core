# データモデル設計: UserPromptBuilder - Evaluator/JudgementClient統合

**ブランチ**: `140-user-prompt-builder-evaluator-judgement` | **日付**: 2025-11-25
**Phase**: Phase 1 - Design & Contracts

## 概要

本ドキュメントは、UserPromptBuilderをEvaluatorとJudgementClientに統合するために必要なデータモデル（Pydantic Models）の詳細設計を記述します。

## エンティティ一覧

### 1. EvaluatorPromptContext（新規）

**目的**: Evaluatorプロンプト生成に必要なコンテキスト情報を型安全に保持

**定義場所**: `src/mixseek/prompt_builder/models.py`

**フィールド**:

| フィールド名 | 型 | 必須 | デフォルト | 説明 | バリデーション |
|------------|---|-----|----------|------|--------------|
| `user_query` | `str` | ✅ | - | 元のユーザークエリ | 空文字列不可 |
| `submission` | `str` | ✅ | - | AIエージェントのSubmission | 空文字列不可 |

**Pydantic実装**:
```python
class EvaluatorPromptContext(BaseModel):
    """Evaluatorプロンプト生成に必要なコンテキスト情報。

    Args:
        user_query: 元のユーザークエリ
        submission: AIエージェントのSubmission

    Raises:
        ValueError: バリデーション失敗時

    Note:
        current_datetimeはコンテキストに含めず、UserPromptBuilder内で
        get_current_datetime_with_timezone()を呼び出して取得します。
        これにより、時刻が使用直前に取得され、DRY原則に従います。

    Example:
        ```python
        from mixseek.prompt_builder.models import EvaluatorPromptContext

        context = EvaluatorPromptContext(
            user_query="Pythonとは何ですか？",
            submission="Pythonはプログラミング言語です..."
        )
        ```
    """
    user_query: str
    submission: str

    @field_validator("user_query", "submission")
    @classmethod
    def validate_not_empty(cls, v: str, info: ValidationInfo) -> str:
        """文字列フィールドが空でないことを検証。

        Args:
            v: フィールド値
            info: フィールドバリデーション情報

        Returns:
            検証済みフィールド値

        Raises:
            ValueError: フィールドが空の場合
        """
        if not v or v.strip() == "":
            field_name = info.field_name
            msg = f"{field_name} cannot be empty"
            raise ValueError(msg)
        return v
```

**関係性**:
- ✅ UserPromptBuilder.build_evaluator_promptメソッドで使用
- ✅ LLMJudgeMetric._get_user_promptから呼び出される

**設計根拠**:
- ✅ RoundPromptContextと同じ設計パターン（DRY原則、Article 10）
  - RoundPromptContextにもcurrent_datetimeフィールドは含まれていない
  - UserPromptBuilder内でget_current_datetime_with_timezone()を呼び出す
- ✅ 型注釈完備（Type Safety、Article 16）
- ✅ field_validatorによる明示的バリデーション（Data Accuracy、Article 9）
- ✅ 時刻は使用直前に取得（コンテキスト作成時ではない）

---

### 2. PromptBuilderSettings（既存拡張）

**目的**: UserPromptBuilderの設定を管理（Team、Evaluator、JudgementClient用プロンプトテンプレート）

**定義場所**: `src/mixseek/prompt_builder/models.py`

**フィールド（拡張部分）**:

| フィールド名 | 型 | 必須 | デフォルト | 説明 | バリデーション |
|------------|---|-----|----------|------|--------------|
| `evaluator_user_prompt` | `str` | ✅ | `DEFAULT_EVALUATOR_USER_PROMPT` | Evaluatorのプロンプトテンプレート（Jinja2形式） | 空文字列不可 |
| `judgment_user_prompt` | `str` | ✅ | `DEFAULT_JUDGMENT_USER_PROMPT` | JudgementClientのプロンプトテンプレート（Jinja2形式） | 空文字列不可 |

**Pydantic実装**:
```python
class PromptBuilderSettings(BaseSettings):
    """UserPromptBuilder設定。

    設定ソース優先順位（高→低）:
    1. 環境変数（MIXSEEK_プレフィックス）
    2. TOMLファイル（$MIXSEEK_WORKSPACE/configs/prompt_builder.toml）
    3. デフォルト値

    Args:
        team_user_prompt: Teamのプロンプトテンプレート（既存）
        evaluator_user_prompt: Evaluatorのプロンプトテンプレート（新規）
        judgment_user_prompt: JudgementClientのプロンプトテンプレート（新規）

    Raises:
        ValueError: プロンプトテンプレートが空の場合
    """
    team_user_prompt: str = DEFAULT_TEAM_USER_PROMPT
    evaluator_user_prompt: str = DEFAULT_EVALUATOR_USER_PROMPT  # 新規
    judgment_user_prompt: str = DEFAULT_JUDGMENT_USER_PROMPT    # 新規

    model_config = SettingsConfigDict(
        env_prefix="MIXSEEK_",
        toml_file="configs/prompt_builder.toml",
        env_file_encoding="utf-8",
    )

    @field_validator("team_user_prompt", "evaluator_user_prompt", "judgment_user_prompt")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """プロンプトテンプレートが空でないことを検証。

        Args:
            v: プロンプトテンプレート値

        Returns:
            検証済みプロンプトテンプレート

        Raises:
            ValueError: プロンプトテンプレートが空の場合
        """
        if not v or v.strip() == "":
            msg = "prompt template cannot be empty"
            raise ValueError(msg)
        return v
```

**関係性**:
- ✅ UserPromptBuilderのコンストラクタで読み込み
- ✅ build_evaluator_prompt、build_judgment_promptで使用

**設計根拠**:
- ✅ 既存のteam_user_promptと同じ設計パターン（DRY原則、Article 10）
- ✅ Pydantic Settings準拠（TOML/環境変数優先順位）
- ✅ デフォルト値をconstants.pyで一元管理（Data Accuracy、Article 9）

---

### 3. RoundPromptContext（既存、変更なし）

**目的**: プロンプト生成に必要なコンテキスト情報（Team、JudgementClient共通）

**定義場所**: `src/mixseek/prompt_builder/models.py`

**フィールド**:

| フィールド名 | 型 | 必須 | デフォルト | 説明 |
|------------|---|-----|----------|------|
| `user_prompt` | `str` | ✅ | - | 元のユーザープロンプト |
| `round_number` | `int` | ✅ | - | 現在のラウンド番号（>=1） |
| `round_history` | `list[RoundState]` | ✅ | - | 過去のRound State履歴 |
| `team_id` | `str` | ✅ | - | チームの一意識別子 |
| `team_name` | `str` | ✅ | - | チーム名 |
| `execution_id` | `str` | ✅ | - | 実行ID（Leader Board取得用） |
| `store` | `AggregationStore \| None` | ❌ | `None` | DuckDBストア（Leader Board取得用） |

**関係性**:
- ✅ UserPromptBuilder.build_team_promptで使用（既存）
- ✅ UserPromptBuilder.build_judgment_promptで使用（新規）
- ✅ JudgmentClient._format_user_promptから呼び出される

**設計根拠**:
- ✅ JudgementClientとTeamで共通利用（DRY原則、Article 10）
- ✅ 既存実装との互換性維持

---

## デフォルト値の定義（constants.py）

### DEFAULT_EVALUATOR_USER_PROMPT

**定義場所**: `src/mixseek/prompt_builder/constants.py`

**値**:
```python
DEFAULT_EVALUATOR_USER_PROMPT = """---
現在日時: {{ current_datetime }}
---

以下のユーザクエリに対するエージェントの提出内容を、あなたの役割に従って評価してください。

# ユーザクエリ
{{ user_query }}

# 提出内容
{{ submission }}
"""
```

**プレースホルダー変数**:
- `user_query`: 元のユーザークエリ
- `submission`: AIエージェントのSubmission
- `current_datetime`: 現在日時（ISO 8601形式、タイムゾーン付き）

**根拠**:
- ✅ FR-005要件に完全準拠
- ✅ 既存LLMJudgeMetric._get_user_promptの日本語化版

---

### DEFAULT_JUDGMENT_USER_PROMPT

**定義場所**: `src/mixseek/prompt_builder/constants.py`

**値**:
```python
DEFAULT_JUDGMENT_USER_PROMPT = """# タスク
以下の提出履歴に基づいて、チームは次のラウンドに進むべきでしょうか？判定、理由、確信度を提供してください。

# ユーザクエリ
{{ user_prompt }}

# 提出履歴
{{ submission_history }}

# リーダーボード
{{ ranking_table }}
"""
```

**プレースホルダー変数**:
- `user_prompt`: 元のユーザープロンプト
- `submission_history`: 過去のSubmission履歴（整形済み文字列）
- `ranking_table`: Leader Boardランキング情報（整形済み文字列）
- `team_position_message`: 当該チームの順位メッセージ（整形済み文字列）
- `current_datetime`: 現在日時（ISO 8601形式、タイムゾーン付き）
- `round_number`: 現在のラウンド番号

**根拠**:
- ✅ FR-012要件に完全準拠
- ✅ 既存JudgmentClient._format_user_promptと同じフォーマット

---

## エンティティ関係図

```
┌─────────────────────────────────────────────────────────────┐
│                    UserPromptBuilder                        │
│  - workspace: Path                                          │
│  - store: AggregationStore | None                           │
│  - settings: PromptBuilderSettings                          │
│  - jinja_env: Environment                                   │
├─────────────────────────────────────────────────────────────┤
│  + build_team_prompt(context: RoundPromptContext) -> str    │
│  + build_evaluator_prompt(context: EvaluatorPromptContext)  │
│    -> str                                                   │
│  + build_judgment_prompt(context: RoundPromptContext)       │
│    -> str                                                   │
└─────────────────────────────────────────────────────────────┘
                           △
                           │ uses
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
┌──────────────┐  ┌─────────────────┐  ┌───────────────┐
│ RoundPrompt  │  │ Evaluator       │  │ PromptBuilder │
│ Context      │  │ PromptContext   │  │ Settings      │
│ (既存)       │  │ (新規)          │  │ (既存拡張)    │
├──────────────┤  ├─────────────────┤  ├───────────────┤
│ user_prompt  │  │ user_query      │  │ team_user_    │
│ round_number │  │ submission      │  │ prompt        │
│ round_history│  │ current_        │  │ evaluator_    │
│ team_id      │  │ datetime        │  │ user_prompt   │
│ team_name    │  └─────────────────┘  │ judgment_     │
│ execution_id │                        │ user_prompt   │
│ store        │                        └───────────────┘
└──────────────┘
       △
       │ uses
       │
       ▼
┌──────────────┐
│ RoundState   │
│ (既存)       │
├──────────────┤
│ round_number │
│ submission_  │
│ content      │
│ evaluation_  │
│ score        │
│ score_details│
└──────────────┘
```

---

## バリデーション戦略

### 1. EvaluatorPromptContext

| バリデーション項目 | ルール | エラーメッセージ |
|------------------|-------|----------------|
| `user_query` 非空 | `not v or v.strip() == ""` → ValueError | `"user_query cannot be empty"` |
| `submission` 非空 | `not v or v.strip() == ""` → ValueError | `"submission cannot be empty"` |

### 2. PromptBuilderSettings

| バリデーション項目 | ルール | エラーメッセージ |
|------------------|-------|----------------|
| `evaluator_user_prompt` 非空 | `not v or v.strip() == ""` → ValueError | `"prompt template cannot be empty"` |
| `judgment_user_prompt` 非空 | `not v or v.strip() == ""` → ValueError | `"prompt template cannot be empty"` |

### 3. Jinja2テンプレート

| バリデーション項目 | ルール | エラーメッセージ |
|------------------|-------|----------------|
| テンプレート構文 | Jinja2解析失敗 → TemplateSyntaxError | `"Jinja2 template error: {error_detail}"` |
| プレースホルダー変数 | 未定義変数 → UndefinedError | `"Jinja2 template error: {error_detail}"` |

---

## 状態遷移図（Evaluatorプロンプト生成）

```
[EvaluationRequest]
        │
        │ user_query, submission
        ▼
[LLMJudgeMetric._get_user_prompt]
        │
        │ 1. EvaluatorPromptContext作成
        │    - user_query
        │    - submission
        │
        ▼ Pydantic ValidationError?
     ┌──┴──┐
     NO   YES → [ValidationError例外]
     │
     ▼
[UserPromptBuilder.build_evaluator_prompt]
        │
        │ 2. テンプレート変数準備
        │    template_vars = {
        │      "user_query": context.user_query,
        │      "submission": context.submission,
        │      "current_datetime": get_current_datetime_with_timezone()  # ← ここで取得
        │    }
        │
        │ 3. Jinja2テンプレート描画
        │    template = jinja_env.from_string(settings.evaluator_user_prompt)
        │    return template.render(template_vars)
        │
        ▼ TemplateSyntaxError/UndefinedError?
     ┌──┴──┐
     NO   YES → [RuntimeError例外]
     │
     ▼
[整形済みプロンプト文字列]
        │
        ▼
[LLM API呼び出し]
```

---

## 状態遷移図（JudgementClientプロンプト生成）

```
[judge_improvement_prospects]
        │
        │ user_query, round_history
        ▼
[JudgmentClient._format_user_prompt]
        │
        │ 1. RoundPromptContext作成
        │    - user_prompt = user_query
        │    - round_number = len(round_history) + 1
        │    - round_history
        │    - team_id, team_name, execution_id
        │    - store
        │
        ▼ Pydantic ValidationError?
     ┌──┴──┐
     NO   YES → [ValidationError例外]
     │
     ▼
[UserPromptBuilder.build_judgment_prompt]
        │
        │ 2. テンプレート変数準備
        │    - user_prompt: context.user_prompt
        │    - round_number: context.round_number
        │    - submission_history: format_submission_history(context.round_history)
        │    - ranking_table: format_ranking_table(...) if store else ""
        │    - team_position_message: generate_position_message(...) if store else ""
        │    - current_datetime: get_current_datetime_with_timezone()
        │
        │ 3. Jinja2テンプレート描画
        │    template = jinja_env.from_string(settings.judgment_user_prompt)
        │    return template.render(template_vars)
        │
        ▼ TemplateSyntaxError/UndefinedError?
     ┌──┴──┐
     NO   YES → [RuntimeError例外]
     │
     ▼
[整形済みプロンプト文字列]
        │
        ▼
[LLM API呼び出し]
```

---

## データフロー図

### Evaluatorプロンプト生成データフロー

```
┌────────────────┐
│  EvaluationRequest  │
│  - user_query       │
│  - submission       │
└────────┬───────────┘
         │
         ▼
┌────────────────────────────────────┐
│  LLMJudgeMetric._get_user_prompt   │
│  ┌──────────────────────────────┐  │
│  │ 1. EvaluatorPromptContext    │  │
│  │    作成                       │  │
│  └──────────────────────────────┘  │
└────────┬───────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  UserPromptBuilder                  │
│  .build_evaluator_prompt()          │
│  ┌───────────────────────────────┐  │
│  │ 2. テンプレート変数準備        │  │
│  │    - user_query               │  │
│  │    - submission               │  │
│  │    - current_datetime         │  │
│  │      (get_current_datetime_   │  │
│  │       with_timezone()で取得)  │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │ 3. Jinja2描画                 │  │
│  │    settings.evaluator_user_   │  │
│  │    prompt                     │  │
│  └───────────────────────────────┘  │
└────────┬────────────────────────────┘
         │
         ▼
┌────────────────────────┐
│  整形済みプロンプト     │
│  文字列                │
└────────────────────────┘
```

### JudgementClientプロンプト生成データフロー

```
┌────────────────────────┐
│  judge_improvement_    │
│  prospects引数         │
│  - user_query          │
│  - round_history       │
└────────┬───────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│  JudgmentClient._format_user_prompt      │
│  ┌────────────────────────────────────┐  │
│  │ 1. RoundPromptContext作成          │  │
│  │    + team_id, team_name,           │  │
│  │      execution_id, store           │  │
│  └────────────────────────────────────┘  │
└────────┬─────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│  UserPromptBuilder                       │
│  .build_judgment_prompt()                │
│  ┌────────────────────────────────────┐  │
│  │ 2. テンプレート変数準備             │  │
│  │    - user_prompt                   │  │
│  │    - round_number                  │  │
│  │    - submission_history            │  │
│  │      (format_submission_history)   │  │
│  │    - ranking_table                 │  │
│  │      (format_ranking_table)        │  │
│  │    - team_position_message         │  │
│  │      (generate_position_message)   │  │
│  │    - current_datetime              │  │
│  └────────────────────────────────────┘  │
│  ┌────────────────────────────────────┐  │
│  │ 3. Jinja2描画                      │  │
│  │    settings.judgment_user_prompt   │  │
│  └────────────────────────────────────┘  │
└────────┬───────────────────────────────────┘
         │
         ▼
┌────────────────────────┐
│  整形済みプロンプト     │
│  文字列                │
└────────────────────────┘
```

---

## まとめ

### 新規エンティティ
- **EvaluatorPromptContext**: Evaluatorプロンプト生成用コンテキスト（2フィールド: user_query, submission）
  - **Note**: current_datetimeはコンテキストに含めず、UserPromptBuilder内でget_current_datetime_with_timezone()を呼び出して取得（RoundPromptContextと同じパターン）

### 拡張エンティティ
- **PromptBuilderSettings**: evaluator_user_prompt、judgment_user_promptフィールド追加

### 既存エンティティ（変更なし）
- **RoundPromptContext**: JudgementClientとTeamで共通利用

### 設計原則の遵守
- ✅ **Article 10（DRY Principle）**: RoundPromptContext再利用、formatters再利用
- ✅ **Article 16（Type Safety）**: 型注釈完備、Pydantic Model活用
- ✅ **Article 9（Data Accuracy）**: field_validatorによる明示的バリデーション、デフォルト値一元管理
