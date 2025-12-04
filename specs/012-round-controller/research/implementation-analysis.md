# LLM改善見込み判定実装パターン分析

**調査対象**: `src/mixseek/evaluator/` - Evaluator実装のLLM-as-a-Judge手法
**適用先**: `src/mixseek/round_controller/` - RoundControllerの改善見込み判定
**日付**: 2025-11-10

---

## 1. Evaluator実装パターン概要

### 1.1 アーキテクチャ構成

```
src/mixseek/evaluator/
├── llm_client.py                 # Pydantic AI Direct Model Request APIラッパー
├── evaluator.py                  # メイン評価器（メトリクス管理・集約）
├── exceptions.py                 # カスタム例外
└── metrics/
    ├── base.py                   # 基底クラス（BaseMetric、LLMJudgeMetric）
    ├── clarity_coherence.py       # LLM-as-a-Judgeメトリクス実装例
    ├── coverage.py               # 同上
    ├── relevance.py              # 同上
    └── llm_plain.py              # カスタムsystem_instruction対応メトリクス
```

### 1.2 Pydantic AI Direct Model Request APIの使用方法

**主要流れ** (`evaluate_with_llm`関数, `llm_client.py:16-151`):

```python
# 1. 構造化出力モデルの定義
response_model: type[BaseModel]  # Pydantic BaseModelサブクラス
```

```python
# 2. ModelRequest の構築
request = ModelRequest(
    parts=[UserPromptPart(content=user_prompt)],
    instructions=instruction  # システムプロンプト
)
```

```python
# 3. Tool Definitionを使用した構造化出力設定
tool_def = ToolDefinition(
    name="submit_evaluation",
    description="Submit the evaluation result with score and comment",
    parameters_json_schema=response_model.model_json_schema(),
)

parameters = ModelRequestParameters(
    function_tools=[tool_def],
    allow_text_output=False,  # 構造化出力のみを強制
)
```

```python
# 4. ModelSettingsの設定
model_settings = ModelSettings(temperature=temperature)
if max_tokens is not None:
    model_settings["max_tokens"] = max_tokens
```

```python
# 5. model_request_sync呼び出し
model_response = model_request_sync(
    model,  # "provider:model-name" format
    [request],
    model_settings=model_settings,
    model_request_parameters=parameters,
)
```

**重要な設計ポイント:**
- `model_settings` は TypedDict（`total=False`）のため、Noneフィールドは辞書に含めない
- `allow_text_output=False` により、Tool Callを強制する（構造化出力を保証）
- リトライロジックは呼び出し元で実装（`llm_client.py:109-143`）

---

## 2. LLMへのプロンプト構造

### 2.1 構成要素

**① システムプロンプト (instruction)**

```python
# 例: ClarityCoherence.get_instruction()
instruction = """
あなたはUser Queryに対するエージェントのSubmissionについて、
その明瞭性/一貫性を評価する公平な評価者です。

重要なガイドライン:
- 冗長性バイアスを避ける
- 構造、言語のシンプルさ、文章構成、可読性に焦点

評価基準（合計: 100ポイント）:
1. 構造と構成（25ポイント）
2. 言語のシンプルさ（25ポイント）
3. 文章構成（25ポイント）
4. 可読性（25ポイント）

スコアリングガイド:
- 90-100: 非常に明確で、完璧に構造化
- ...
- 0-29: 非常に不明確または理解不能

指示:
1. 分析して推論を提供
2. 0から100の間の最終スコアを提供
3. ユーザにフィードバックコメントを提供
"""
```

**② ユーザープロンプト (user_prompt)**

```python
# 例: LLMJudgeMetric._get_user_prompt()
user_prompt = f"""
以下のUser Queryに対するエージェントのSubmissionを、あなたの役割に従って評価してください。

User Query:
{user_query}

Submission:
{submission}
"""
```

### 2.2 プロンプト構成の特徴

1. **明確な役割定義**: "公平な評価者です"
2. **具体的な評価基準**: 各基準ごとにポイント配分
3. **スコアリングガイド**: スコア範囲とそれぞれの意味
4. **段階的な指示**: 分析→スコア→フィードバック
5. **コンテンツ明示**: User Queryと評価対象のSubmissionを明示的に区分

---

## 3. レスポンスのパースとPydantic Modelへのマッピング

### 3.1 構造化出力モデル

```python
# base.py:12-28
class BaseLLMEvaluation(BaseModel):
    """LLM-as-a-Judgeの評価結果のための共通の構造化出力モデル"""
    score: float = Field(ge=0.0, le=100.0, description="0から100の間の評価スコア")
    evaluator_comment: str = Field(description="スコアの連鎖思考推論とフィードバック")
```

### 3.2 レスポンスの抽出とパース

```python
# llm_client.py:119-130
# ツール呼び出しを抽出して検証
if not model_response.parts:
    raise ValueError("No response parts returned from LLM")

tool_call = model_response.parts[0]

# tool_call.argsが文字列の場合はJSON解析が必要
args = tool_call.args
if isinstance(args, str):
    args = json.loads(args)

# Pydantic Model検証
return response_model.model_validate(args)
```

### 3.3 Pydantic検証の活用

```python
# evaluation_result.py:39-69
class MetricScore(BaseModel):
    score: float = Field(..., ge=0.0, le=100.0)
    evaluator_comment: str = Field(...)

    @field_validator("score")
    @classmethod
    def round_score_to_two_decimals(cls, v: float) -> float:
        """一貫性のためにスコアを小数点以下2桁に丸めます"""
        return round(v, 2)
```

**重要な設計ポイント:**
- `model_validate()` で自動的にバリデーション実行
- フィールドバリデータで値の正規化（丸め、トリム）
- 制約違反時は `ValidationError` 例外を発生

---

## 4. エラーハンドリングとリトライロジック

### 4.1 リトライ実装パターン

```python
# llm_client.py:107-143
last_exception = None
for attempt in range(max_retries):
    try:
        # LLMリクエスト実行
        model_response = model_request_sync(...)

        # 検証・パース
        tool_call = model_response.parts[0]
        args = json.loads(tool_call.args) if isinstance(tool_call.args, str) else tool_call.args

        return response_model.model_validate(args)

    except Exception as e:
        last_exception = e
        if attempt < max_retries - 1:
            continue  # リトライ
        else:
            # すべてのリトライを使い果たした
            raise EvaluatorAPIError(
                f"Failed to evaluate after {max_retries} retries: {str(e)}",
                provider=provider,
                metric_name=None,
                retry_count=max_retries,
            ) from e
```

### 4.2 エラーハンドリング戦略

**エラーの分類:**

1. **API呼び出し段階** (model_request_sync)
   - ネットワークエラー
   - 認証エラー（API キー無効）
   - レート制限

2. **レスポンス構造検証段階** (response.parts)
   - 空のレスポンス
   - Tool Callの不在

3. **JSON解析段階** (json.loads)
   - JSONフォーマットエラー

4. **Pydantic検証段階** (model_validate)
   - スコア範囲外（< 0または > 100）
   - 必須フィールド欠落
   - 型ミスマッチ

### 4.3 カスタム例外

```python
# exceptions.py:55-107
class EvaluatorAPIError(Exception):
    """評価中のLLM APIエラーの基底例外"""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        metric_name: str | None = None,
        retry_count: int | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.metric_name = metric_name
        self.retry_count = retry_count

    def __str__(self) -> str:
        """コンテキストを含むフォーマット済みエラーメッセージ"""
        parts = [super().__str__()]
        if self.provider:
            parts.append(f"Provider: {self.provider}")
        if self.metric_name:
            parts.append(f"Metric: {self.metric_name}")
        if self.retry_count is not None:
            parts.append(f"Retries: {self.retry_count}")
        return " | ".join(parts)
```

### 4.4 リトライポリシーの不在

**現在の実装では:**
- 単純な「指数関数的バックオフなし」の即座リトライ
- `max_retries` 回数だけ同じタイミングで再試行

**仕様要求との対比:**
- Round Controller仕様 (FR-010) では「エクスポネンシャルバックオフ (1秒、2秒、4秒)」を要求

---

## 5. Evaluatorの全体フロー

```
┌─────────────────────────────────────────┐
│ Evaluator.evaluate(request)             │
│ (evaluator.py:104-186)                  │
├─────────────────────────────────────────┤
│ 1. 入力検証                              │
│    (Pydantic バリデータで既に処理済み)   │
│                                         │
│ 2. 使用する設定を決定                    │
│    config = request.config or self.config
│                                         │
│ 3. 各メトリクスを順次評価                │
│    for metric_config in config.metrics: │
│        metric = self._get_metric(...)   │
│        if isinstance(metric, LLMJudge): │
│            score = metric.evaluate(     │
│                user_query,              │
│                submission,              │
│                model=...,               │
│                temperature=...,         │
│                max_tokens=...,          │
│                max_retries=...,         │
│                system_instruction=...   │
│            )                            │
│        else:                            │
│            score = metric.evaluate(...) │
│                                         │
│ 4. 重み付き総合スコアを計算              │
│    overall_score = sum(               │
│        score.score * weight             │
│        for score, weight                │
│    )                                    │
│                                         │
│ 5. 結果を返却                           │
│    return EvaluationResult(...)        │
└─────────────────────────────────────────┘
```

### 5.1 LLMJudgeMetricの評価フロー

```
┌──────────────────────────────────────────┐
│ LLMJudgeMetric.evaluate(...)             │
│ (base.py:166-236)                        │
├──────────────────────────────────────────┤
│ 1. システムプロンプトを取得               │
│    instruction = system_instruction or  │
│                  self.get_instruction() │
│                                         │
│ 2. ユーザープロンプトを生成               │
│    user_prompt = self._get_user_prompt()│
│                                         │
│ 3. evaluate_with_llm()呼び出し          │
│    result = evaluate_with_llm(          │
│        instruction=instruction,         │
│        user_prompt=user_prompt,         │
│        model=model,                     │
│        response_model=BaseLLMEvaluation,│
│        temperature=temperature,         │
│        max_tokens=max_tokens,           │
│        max_retries=max_retries,         │
│    )                                    │
│                                         │
│ 4. MetricScoreに変換                    │
│    return MetricScore(                 │
│        metric_name=type(self).__name__,│
│        score=result.score,              │
│        evaluator_comment=result.comment │
│    )                                    │
└──────────────────────────────────────────┘
```

---

## 決定事項

### RoundControllerの改善見込み判定実装

#### 採用パターン: Evaluatorパターンの直接応用

**実装戦略:**

1. **専用の改善見込み判定モデル定義** (`src/mixseek/round_controller/models.py`):

```python
from pydantic import BaseModel, Field

class ImprovementJudgment(BaseModel):
    """LLMによる改善見込み判定結果"""
    should_continue: bool = Field(
        description="次のラウンドに進むべきか (True: 継続、False: 終了)"
    )
    reasoning: str = Field(
        description="判定理由の詳細説明（連鎖思考推論）"
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="判定の信頼度スコア（0-1の範囲）"
    )
```

2. **改善見込み判定専用クライアント** (`src/mixseek/round_controller/judgment_client.py`):

```python
from pydantic_ai.direct import model_request_sync
from pydantic_ai import ModelRequest
from pydantic_ai.messages import UserPromptPart
from pydantic_ai.tools import ToolDefinition
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.settings import ModelSettings

def judge_improvement_prospects(
    submission_history: list[dict],  # 過去のSubmission履歴
    model: str,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    max_retries: int = 3,
) -> ImprovementJudgment:
    """LLMによる改善見込み判定を実行する

    Args:
        submission_history: 過去のSubmissionと評価結果
        model: LLMモデル識別子 ("provider:model-name")
        temperature: LLM温度設定
        max_tokens: トークン上限
        max_retries: リトライ回数

    Returns:
        改善見込み判定結果
    """

    # 1. プロンプト構築
    instruction = _build_system_prompt()  # スコア改善見込み判定用システムプロンプト
    user_prompt = _build_user_prompt(submission_history)  # 履歴統合プロンプト

    # 2. ModelRequest構築
    request = ModelRequest(
        parts=[UserPromptPart(content=user_prompt)],
        instructions=instruction
    )

    # 3. Tool Definition設定
    tool_def = ToolDefinition(
        name="submit_judgment",
        description="Submit the improvement judgment decision",
        parameters_json_schema=ImprovementJudgment.model_json_schema(),
    )

    parameters = ModelRequestParameters(
        function_tools=[tool_def],
        allow_text_output=False,
    )

    # 4. ModelSettings
    model_settings = ModelSettings(temperature=temperature)
    if max_tokens is not None:
        model_settings["max_tokens"] = max_tokens

    # 5. リトライロジック
    last_exception = None
    for attempt in range(max_retries):
        try:
            model_response = model_request_sync(
                model,
                [request],
                model_settings=model_settings,
                model_request_parameters=parameters,
            )

            # レスポンス抽出・パース
            tool_call = model_response.parts[0]
            args = tool_call.args
            if isinstance(args, str):
                args = json.loads(args)

            return ImprovementJudgment.model_validate(args)

        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                continue
            else:
                raise RoundControllerError(
                    f"Failed to judge improvement prospects after {max_retries} retries: {str(e)}",
                    retry_count=max_retries,
                ) from e
```

3. **RoundControllerへの統合** (`src/mixseek/round_controller/controller.py`):

```python
async def _should_continue_round(
    self,
    team_id: str,
    submission_history: list[dict],
    current_round: int,
    max_rounds: int,
    min_rounds: int,
) -> tuple[bool, ImprovementJudgment]:
    """ラウンド継続判定ロジック (FR-005)

    Returns:
        (継続するかどうか, 判定結果)
    """

    # (a) 最小ラウンド数到達確認
    if current_round < min_rounds:
        return True, ImprovementJudgment(
            should_continue=True,
            reasoning=f"Minimum rounds ({min_rounds}) not reached yet. Continuing...",
            confidence_score=1.0
        )

    # (b) LLMによる改善見込み判定
    try:
        judgment = await judge_improvement_prospects(
            submission_history=submission_history,
            model=self.config.llm_model,
            temperature=0.0,  # 決定的な判定用
            max_tokens=1000,
            max_retries=3,
        )
    except Exception as e:
        # リトライ全失敗時は保守的に「改善見込みあり」
        logger.warning(f"Improvement judgment failed, assuming continuation: {e}")
        judgment = ImprovementJudgment(
            should_continue=True,
            reasoning="Judgment failed, defaulting to continuation for safety",
            confidence_score=0.0
        )

    # (c) 最大ラウンド数到達確認
    if current_round >= max_rounds:
        judgment.should_continue = False
        judgment.reasoning += f" [Max rounds ({max_rounds}) reached]"

    return judgment.should_continue, judgment
```

---

## 根拠

### 1. プロダクション検証済み

- **Evaluator実装は既に本番稼働中**: `src/mixseek/evaluator/` は422行以上のコード規模で、複数メトリクス対応の実装済み
- **Pydantic AI統合**: pydantic-ai >=0.1.0 を活用した確実なAPI呼び出しパターン
- **リトライ・エラーハンドリング**: 複数段階のエラー検出（API呼び出し、JSON解析、Pydantic検証）

### 2. 型安全性の確保

- **Pydantic BaseModelによる型強制**: Field制約（ge, le）により自動検証
- **field_validatorによる正規化**: スコアの丸め、コメントのトリムなど
- **model_validateによる一括検証**: 複数エラーの検出

### 3. テスト容易性

- **責務の分離**:
  - `llm_client.py`: LLM通信とリトライロジック
  - `metrics/base.py`: プロンプト構築とメトリクス仕様
  - `evaluator.py`: メトリクス管理と集約
- **DIパターン**: システムプロンプト、ユーザープロンプト、モデルを注入可能

### 4. 拡張性

- **カスタムメトリクス対応**: `LLMJudgeMetric`を継承して新メトリクス追加可能
- **system_instruction上書き**: LLMPlainメトリクスのように外部から指定可能
- **フォールバックロジック**: メトリクス設定、llm_default設定のフォールバック階層

---

## 検討した代替案と採用しなかった理由

### 代替案1: langchain-ai.langchain統合

**実装方法:**
```python
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field

class Judgment(BaseModel):
    should_continue: bool = Field(description="...")
    reasoning: str = Field(description="...")
    confidence_score: float = Field(description="...")

llm = ChatOpenAI(model="gpt-4", temperature=0.0)
structured_llm = llm.with_structured_output(Judgment)
result = structured_llm.invoke(prompt)
```

**採用しなかった理由:**
1. **既存依存関係との競合**: `pydantic-ai`はすでに`src/mixseek/evaluator/`で使用中。langchainの導入は新たな依存を追加
2. **pydantic-aiの方が軽量**: Evaluatorの実装規模から、pydantic-aiで十分
3. **Chain構造の複雑性**: langchainのChainパイプラインは単一の判定用途では過度

---

### 代替案2: 汎用UtilityMetricの流用

**実装方法:**
```python
# LLMPlainメトリクスをそのまま改善見込み判定用に使用
metric = LLMPlain()
score = metric.evaluate(
    user_query="...",  # 改善見込み判定用クエリ
    submission="...",  # 提出履歴
    model="...",
    system_instruction="判定用システムプロンプト"
)
```

**採用しなかった理由:**
1. **出力形式の不整合**: MetricScoreはスコア（0-100）を返すが、判定結果には`should_continue` (bool)が必要
2. **意図の明確さ**: Evaluatorは「品質評価」の責務を持つが、改善見込み判定は「戦略的継続判定」の責務
3. **保守性**: 独立した`ImprovementJudgment`モデルにより、判定ロジックの変更がスコア評価に影響しない

---

### 代替案3: 簡易的なPrompt + 手動パース

**実装方法:**
```python
def judge_improvement_manually(submission_history):
    prompt = "判定用プロンプト..."
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    # 手動パース
    text = response.choices[0].message.content
    should_continue = "yes" in text.lower()
    confidence = 0.8 if "confident" in text.lower() else 0.5

    return should_continue, confidence
```

**採用しなかった理由:**
1. **信頼性の低さ**: 文字列パターンマッチングはFragile（LLMの出力形式変化で破損）
2. **再現性の欠如**: 同じ判定条件でも異なる出力形式が返される可能性
3. **スキーマバリデーション不可**: 予期しない出力形式をキャッチできない

---

### 代替案4: JSON Schema + LLM Function Calling（raw Anthropic SDK）

**実装方法:**
```python
from anthropic import Anthropic

client = Anthropic()
tools = [{
    "name": "submit_judgment",
    "description": "...",
    "input_schema": {
        "type": "object",
        "properties": {
            "should_continue": {"type": "boolean"},
            "reasoning": {"type": "string"},
            "confidence_score": {"type": "number", "minimum": 0, "maximum": 1}
        },
        "required": ["should_continue", "reasoning", "confidence_score"]
    }
}]

response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    tools=tools,
    messages=[{"role": "user", "content": "..."}]
)
```

**採用しなかった理由:**
1. **既存パターンとの不統一**: Evaluatorはpydantic-aiを使用しており、raw Anthropic SDKは異なるパターン
2. **プロバイダー固有化**: pydantic-aiはプロバイダー抽象化（anthropic、openaiなど）をサポートが、raw SDKはProvoderに限定
3. **エラーハンドリングの重複実装**: リトライロジック、検証ロジックを独立して実装する必要がある

---

## まとめ

| 判定項目 | 評価 |
|---------|------|
| **プロダクション検証** | ✅ Evaluatorで既に実装済み、本番稼働 |
| **型安全性** | ✅ Pydantic BaseModelによる自動検証 |
| **エラーハンドリング** | ✅ 多段階エラー検出、リトライロジック完備 |
| **テスト容易性** | ✅ 責務分離、DI対応 |
| **保守性** | ✅ 既存パターン活用で学習曲線低い |
| **拡張性** | ✅ カスタムメトリクス/プロンプト対応可能 |

**最終結論**: Evaluator実装のLLM-as-a-Judge手法をそのまま改善見込み判定に適用することで、既存実装資産の活用、型安全性の確保、エラーハンドリングの堅牢性を実現できます。
