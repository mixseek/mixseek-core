# リサーチドキュメント: UserPromptBuilder - Evaluator/JudgementClient統合

**ブランチ**: `140-user-prompt-builder-evaluator-judgement` | **日付**: 2025-11-25
**Phase**: Phase 0 - Outline & Research

## 概要

本ドキュメントは、UserPromptBuilderをEvaluatorとJudgementClientに統合するために必要な技術的決定、ベストプラクティス、実装パターンを記録します。

## リサーチ項目

### 1. 既存実装の分析

#### 1.1 UserPromptBuilder（specs/015-user-prompt-builder-team）

**調査結果**:
- **実装場所**: `src/mixseek/prompt_builder/builder.py`
- **主要メソッド**: `build_team_prompt(context: RoundPromptContext) -> str`
- **設計パターン**:
  - Jinja2テンプレートエンジンによるプロンプト整形
  - Pydantic Settingsによる設定管理（TOML/環境変数）
  - RoundPromptContext（Pydantic Model）によるコンテキスト情報の型安全な受け渡し
  - formatters モジュールによるヘルパー関数の分離（DRY原則遵守）

**キーとなる実装詳細**:
```python
# builder.py
def build_team_prompt(self, context: RoundPromptContext) -> str:
    template_vars = self._prepare_template_variables(context)
    template = self.jinja_env.from_string(self.settings.team_user_prompt)
    return template.render(template_vars)

# models.py
class RoundPromptContext(BaseModel):
    user_prompt: str
    round_number: int
    round_history: list[RoundState]
    team_id: str
    team_name: str
    execution_id: str
    store: Any = None
```

**適用可能なパターン**:
- ✅ 同じコンテキストモデル設計パターンをEvaluatorPromptContextに適用
- ✅ Jinja2テンプレートエンジンを再利用
- ✅ PromptBuilderSettings拡張による設定追加
- ✅ formatters.pyのヘルパー関数を再利用

#### 1.2 LLMJudgeMetric._get_user_prompt（Evaluator）

**調査結果**:
- **実装場所**: `src/mixseek/evaluator/metrics/base.py`（145-172行目）
- **現在の実装**:
```python
def _get_user_prompt(self, user_query: str, submission: str) -> str:
    return dedent(f"""
        以下のUser Queryに対するエージェントのSubmissionを、あなたの役割に従って評価してください。

        User Query:
        {user_query}

        Submission:
        {submission}

        IMPORTANT: You MUST provide your response using the submit_evaluation tool with BOTH required fields:
        1. score: A numeric score between 0 and 100
        2. evaluator_comment: Detailed explanation with chain-of-thought reasoning and feedback

        Do NOT omit either field. Both are mandatory.
    """).strip()
```

**問題点と改善策**:
- ❌ ハードコードされたプロンプトフォーマット
- ❌ カスタマイズ不可（ユーザが実験できない）
- ❌ current_datetimeプレースホルダーがない（FR-003要件）
- ✅ **改善策**: UserPromptBuilderのbuild_evaluator_promptメソッドに移行し、TOML設定でカスタマイズ可能にする

**仕様要件（FR-005）でのデフォルトプロンプト**:
```
---
現在日時: {{ current_datetime }}
---

以下のユーザクエリに対するエージェントの提出内容を、あなたの役割に従って評価してください。

# ユーザクエリ
{{ user_query }}

# 提出内容
{{ submission }}
```

**移行方針**:
1. EvaluatorPromptContext（user_query, submission）を定義
2. build_evaluator_promptメソッドを実装
   - コンテキストからuser_queryとsubmissionを取得
   - get_current_datetime_with_timezone()でcurrent_datetimeを取得
   - テンプレート変数として埋め込む
3. LLMJudgeMetric._get_user_promptをUserPromptBuilder呼び出しに変更
4. 既存テストケースが100%パスすることを確認

#### 1.3 JudgmentClient._format_user_prompt（Round Controller）

**調査結果**:
- **実装場所**: `src/mixseek/round_controller/judgment_client.py`（59-93行目）
- **現在の実装**:
```python
def _format_user_prompt(self, user_query: str, round_history: list[RoundState]) -> str:
    prompt_parts = ["# タスク"]
    prompt_parts.append(
        "以下のラウンド履歴に基づいて、チームは次のラウンドに進むべきでしょうか？"
        "判定、理由、確信度を提供してください。"
    )
    prompt_parts.append("")
    prompt_parts.append("# ユーザクエリ")
    prompt_parts.append(user_query)
    prompt_parts.append("")
    prompt_parts.append("# ラウンド履歴\n")

    for state in round_history:
        prompt_parts.append(f"## ラウンド {state.round_number}")
        prompt_parts.append("**提出内容:**")
        prompt_parts.append(state.submission_content)
        prompt_parts.append("")
        prompt_parts.append(f"**スコア:** {state.evaluation_score:.2f}/100")
        prompt_parts.append("**スコア詳細:**")
        prompt_parts.append(json.dumps(state.score_details, ensure_ascii=False, indent=2))
        prompt_parts.append("")

    return "\n".join(prompt_parts)
```

**問題点と改善策**:
- ❌ ハードコードされたプロンプトフォーマット
- ❌ カスタマイズ不可（ユーザが判定基準を調整できない）
- ❌ 現在日時、ランキング情報などの追加コンテキストがない（FR-009要件）
- ✅ **改善策**: UserPromptBuilderのbuild_judgment_promptメソッドに移行し、RoundPromptContextを利用

**仕様要件（FR-012）でのデフォルトプロンプト**:
```
# タスク
以下の提出履歴に基づいて、チームは次のラウンドに進むべきでしょうか？判定、理由、確信度を提供してください。

# ユーザクエリ
{{ user_query }}

# 提出履歴
{{ submission_history }}

# リーダーボード
{{ ranking_table }}
```

**移行方針**:
1. 既存のRoundPromptContextを利用（JudgementClientとTeamプロンプトで共通）
2. build_judgment_promptメソッドを実装（formatters.pyのformat_submission_historyを再利用）
3. JudgmentClient._format_user_promptをUserPromptBuilder呼び出しに変更
4. 既存テストケースが100%パスすることを確認

### 2. Jinja2テンプレートエンジンのベストプラクティス

#### 2.1 テンプレート構文

**調査結果**:
- **変数埋め込み**: `{{ variable_name }}`
- **条件分岐**: `{% if condition %}...{% endif %}`
- **ループ**: `{% for item in list %}...{% endfor %}`
- **エラーハンドリング**: UndefinedError（未定義変数の検出）

**ベストプラクティス**:
- ✅ autoescape=Falseを使用（プレーンテキストプロンプト）
- ✅ Environment.from_string()で動的テンプレート生成
- ✅ TemplateSyntaxError、UndefinedErrorを明示的にキャッチ
- ✅ デフォルト値は設定側で管理（テンプレート内では使用しない）

**実装例（既存のbuild_team_prompt）**:
```python
try:
    template = self.jinja_env.from_string(self.settings.team_user_prompt)
    return template.render(template_vars)
except (TemplateSyntaxError, UndefinedError) as e:
    msg = f"Jinja2 template error: {e}"
    raise RuntimeError(msg) from e
```

#### 2.2 プレースホルダー変数の命名規則

**決定事項**:
- ✅ snake_case命名（user_query, submission, current_datetime）
- ✅ TeamプロンプトとJudgementClientで共通の変数名を使用（submission_history, ranking_table, team_position_message, current_datetime）
- ✅ 仕様書（FR-003、FR-009）に明記された変数のみを提供

### 3. Pydantic Modelのベストプラクティス

#### 3.1 EvaluatorPromptContextの設計

**決定事項**:
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
        RoundPromptContextと同じパターンに従います。
    """
    user_query: str
    submission: str

    @field_validator("user_query", "submission")
    @classmethod
    def validate_not_empty(cls, v: str, info: ValidationInfo) -> str:
        """文字列フィールドが空でないことを検証。"""
        if not v or v.strip() == "":
            field_name = info.field_name
            msg = f"{field_name} cannot be empty"
            raise ValueError(msg)
        return v
```

**根拠**:
- ✅ RoundPromptContext設計パターンを完全に踏襲（Article 10: DRY Principle）
  - RoundPromptContextにもcurrent_datetimeフィールドは含まれていない
  - 時刻は使用直前にUserPromptBuilder内で取得
- ✅ field_validatorによる明示的バリデーション（Article 9: Data Accuracy）
- ✅ 型注釈完備（Article 16: Type Safety）
- ✅ formatters.pyの既存実装を活用（get_current_datetime_with_timezone）

#### 3.2 PromptBuilderSettingsの拡張

**決定事項**:
```python
class PromptBuilderSettings(BaseSettings):
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
        if not v or v.strip() == "":
            msg = "prompt template cannot be empty"
            raise ValueError(msg)
        return v
```

**根拠**:
- ✅ 既存のteam_user_promptと同じ設計パターン
- ✅ pydantic-settings準拠（TOML/環境変数優先順位）
- ✅ デフォルト値をconstants.pyで一元管理

### 4. デフォルトプロンプトの設計

#### 4.1 DEFAULT_EVALUATOR_USER_PROMPT

**決定事項**:
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

**根拠**:
- ✅ FR-005要件に完全準拠
- ✅ 既存LLMJudgeMetric._get_user_promptの英語部分を日本語化
- ✅ current_datetimeプレースホルダーを追加（Teamプロンプトと同様）

#### 4.2 DEFAULT_JUDGMENT_USER_PROMPT

**決定事項**:
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

**根拠**:
- ✅ FR-012要件に完全準拠
- ✅ 既存JudgmentClient._format_user_promptと同じフォーマット
- ✅ Teamプロンプトと共通のプレースホルダー変数（submission_history, ranking_table）

### 5. formatters.pyの既存実装の再利用

#### 5.1 format_submission_history

**調査結果**:
- **実装場所**: `src/mixseek/prompt_builder/formatters.py`
- **機能**: RoundState履歴を整形済み文字列に変換
- **出力例**:
```
## ラウンド 1
**提出内容:**
[submission_content]

**スコア:** 85.50/100
**スコア詳細:**
{
  "metric1": 90.0,
  "metric2": 81.0
}
```

**再利用方針**:
- ✅ build_judgment_promptでそのまま使用（FR-010要件）
- ✅ 既存の出力フォーマットを維持（既存テストケース100%パス）

#### 5.2 format_ranking_table、generate_position_message

**調査結果**:
- **実装場所**: `src/mixseek/prompt_builder/formatters.py`
- **機能**: Leader Boardランキング情報を整形
- **出力例**:
```
順位 | チームID | チーム名 | スコア
1    | team-001 | Team Alpha | 95.50
2    | team-002 | Team Beta  | 90.25 ← あなたのチーム
```

**再利用方針**:
- ✅ build_judgment_promptでそのまま使用（FR-010要件）
- ✅ RoundPromptContext.storeからランキング情報を取得

### 6. エラーハンドリング戦略

#### 6.1 Jinja2エラー

**決定事項**:
```python
try:
    template = self.jinja_env.from_string(self.settings.evaluator_user_prompt)
    return template.render(template_vars)
except (TemplateSyntaxError, UndefinedError) as e:
    msg = f"Jinja2 template error: {e}"
    raise RuntimeError(msg) from e
```

**根拠**:
- ✅ 既存のbuild_team_promptと同じエラーハンドリング
- ✅ TemplateSyntaxError（構文エラー）とUndefinedError（未定義変数）を明示的に処理

#### 6.2 Pydanticバリデーションエラー

**決定事項**:
- ✅ field_validatorによる明示的バリデーション
- ✅ ValidationErrorは自動的に発生（Pydanticの標準動作）
- ✅ エラーメッセージにフィールド名を含める

### 7. テスト戦略

#### 7.1 ユニットテスト設計

**test_builder_evaluator.py**:
```python
def test_build_evaluator_prompt_default():
    """デフォルトテンプレートでプロンプトを整形"""

def test_build_evaluator_prompt_custom():
    """カスタムテンプレートでプロンプトを整形"""

def test_build_evaluator_prompt_placeholder_validation():
    """プレースホルダー変数の検証"""

def test_build_evaluator_prompt_template_syntax_error():
    """Jinja2構文エラーの処理"""
```

**test_builder_judgment.py**:
```python
def test_build_judgment_prompt_default():
    """デフォルトテンプレートでプロンプトを整形"""

def test_build_judgment_prompt_with_history():
    """複数ラウンド履歴の整形"""

def test_build_judgment_prompt_with_ranking():
    """ランキング情報の整形"""

def test_build_judgment_prompt_placeholder_validation():
    """プレースホルダー変数の検証"""
```

#### 7.2 統合テスト戦略

**test_base_metric.py（既存テスト修正）**:
```python
def test_llm_judge_metric_integration():
    """LLMJudgeMetric._get_user_prompt -> UserPromptBuilder統合テスト"""
    # 既存テストケースが100%パスすることを確認
```

**test_improvement_judgment.py（既存テスト修正）**:
```python
def test_judgment_client_integration():
    """JudgmentClient._format_user_prompt -> UserPromptBuilder統合テスト"""
    # 既存テストケースが100%パスすることを確認
```

### 8. 設定ファイル初期化（mixseek config init）

#### 8.1 現在の実装

**調査結果**:
- **実装場所**: `src/mixseek/config/initializer.py`
- **現在の機能**: prompt_builder.tomlのteam_user_promptを生成

#### 8.2 拡張方針

**決定事項**:
```toml
# prompt_builder.toml

[prompt_builder]
# Team Agent用プロンプトテンプレート（既存）
team_user_prompt = """
...
"""

# Evaluator用プロンプトテンプレート（新規）
# 利用可能なプレースホルダー変数: user_query, submission, current_datetime
evaluator_user_prompt = """
---
現在日時: {{ current_datetime }}
---

以下のユーザクエリに対するエージェントの提出内容を、あなたの役割に従って評価してください。

# ユーザクエリ
{{ user_query }}

# 提出内容
{{ submission }}
"""

# JudgementClient用プロンプトテンプレート（新規）
# 利用可能なプレースホルダー変数: user_prompt, round_number, submission_history, ranking_table, team_position_message, current_datetime
judgment_user_prompt = """
# タスク
以下の提出履歴に基づいて、チームは次のラウンドに進むべきでしょうか？判定、理由、確信度を提供してください。

# ユーザクエリ
{{ user_prompt }}

# 提出履歴
{{ submission_history }}

# リーダーボード
{{ ranking_table }}
"""
```

**根拠**:
- ✅ FR-015、FR-016要件に完全準拠
- ✅ コメント付きでプレースホルダー変数を明記
- ✅ ドキュメントとしても機能

## 技術的決定の要約

| 決定事項 | 選択した方針 | 根拠 |
|---------|------------|------|
| **コンテキストモデル** | EvaluatorPromptContext（新規: user_query, submission）、RoundPromptContext（既存再利用） | RoundPromptContextはJudgementClientとTeamで共通利用（DRY原則）。current_datetimeはコンテキストに含めず、UserPromptBuilder内で取得（既存パターン踏襲） |
| **テンプレートエンジン** | Jinja2（既存実装を踏襲） | UserPromptBuilderで実績あり、柔軟なカスタマイズ可能 |
| **設定管理** | PromptBuilderSettings拡張、TOML/環境変数サポート | Pydantic Settings準拠、既存パターンを踏襲 |
| **デフォルトプロンプト** | constants.pyで一元管理 | Article 9（Data Accuracy）遵守、ハードコード回避 |
| **formatters再利用** | format_submission_history、format_ranking_table、generate_position_message | Article 10（DRY Principle）遵守、既存実装の品質活用 |
| **エラーハンドリング** | TemplateSyntaxError、UndefinedError、ValidationError明示的処理 | Article 9（Data Accuracy）遵守、明確なエラーメッセージ |
| **テスト戦略** | ユニットテスト+統合テスト、既存テスト100%パス | Article 3（Test-First）遵守、後方互換性維持 |

## 次のステップ（Phase 1）

1. **data-model.md作成**: EvaluatorPromptContextの詳細設計
2. **quickstart.md作成**: ユーザー向けクイックスタートガイド
3. **agent context更新**: `.specify/scripts/bash/update-agent-context.sh claude`実行
4. **Constitution Check再評価**: Phase 1設計後の整合性確認
