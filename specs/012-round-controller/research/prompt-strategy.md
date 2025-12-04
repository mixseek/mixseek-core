# プロンプト整形戦略: Round Controller - ラウンドプロンプト統合設計

**作成日**: 2025-11-10
**対象**: 012-round-controller
**ステータス**: 設計ドキュメント

---

## プロンプト整形戦略

### 決定事項

**採用方針**:
1. **プロンプト構築は Leader Agent への入力として統一**
   - 各ラウンド開始時に構造化されたコンテキストを生成
   - Leader Agent の `run()` メソッドへの入力として単一プロンプト文字列を送信
   - Leader Agent は既存の Pydantic AI 統合を通じて、このプロンプトを LLM に送信

2. **段階的な情報統合アプローチ**
   - ラウンド1（初回）: ユーザクエリのみ
   - ラウンド2以上: ユーザクエリ + 過去のSubmission履歴 + 評価フィードバック + ランキング情報

3. **プロンプトテンプレートの実装形式**
   - **短期（現在の実装）**: Python f-string + textwrap.dedent() による構造化テンプレート
   - **長期（外部化対象）**: 将来的に Jinja2 ベースの Prompt Builder コンポーネントへの移行を想定
   - **段階的移行**: インターフェース分離により、テンプレートエンジン切り替えを容易にする設計

4. **構造化データの注入方法**
   - 既存の Evaluator 実装に準ずる **Direct Model Request API** パターン
   - 構造化された評価結果（`EvaluationResult`）を段階的にプロンプトに統合
   - Leader Agent への単一文字列入力に集約（既存アーキテクチャとの整合性維持）

5. **トークン制限対策**
   - **要約フレームワーク**: 過去のSubmission数が多い場合は最新N件に制限（N は設定可能）
   - **段階的情報**: コア情報（最高スコア、現在順位）を優先、詳細フィードバックは背景情報として配置
   - **遅延ロード**: プロンプト生成時にコンテキスト情報をフィルタリング（DuckDB から必要最小限を抽出）

---

## 根拠

### 既存実装との整合性

#### 1. Leader Agent 統合 (`src/mixseek/agents/leader/`)

**現在の実装**:
```python
# agent.py の DEFAULT_LEADER_SYSTEM_INSTRUCTION
DEFAULT_LEADER_SYSTEM_INSTRUCTION = """
あなたは研究チームのリーダーエージェントです。
タスクを分析し、利用可能なMember Agentから適切なものを選択して実行してください。
"""
```

**既存パターン**:
- Leader Agent は `system_instruction` + `system_prompt`（オプション）を受け取る
- ユーザプロンプトは `agent.run(user_prompt, deps=deps)` として単一文字列で入力
- Pydantic AI の `instructions` パラメータは、システムレベルの指導のみ
- ユーザ入力プロンプト内に、動的なコンテキスト情報を統合することは既存パターン

**決定の根拠**:
- Round Controller は既存の Leader Agent API を変更しない（アーキテクチャ整合性）
- プロンプト統合処理は Round Controller 内で実施し、Leader Agent への入力は単一文字列に集約
- 将来的な外部化時も、Leader Agent インターフェースへの変更は最小限に抑える

#### 2. Evaluator の LLM-as-a-Judge パターン (`src/mixseek/evaluator/`)

**参考実装**:
```python
# evaluator/llm_client.py の evaluate_with_llm()
def evaluate_with_llm(
    instruction: str,                    # システムプロンプト
    user_prompt: str,                    # ユーザプロンプト（コンテキスト統合済み）
    model: str,
    response_model: type[BaseModel],
    ...
) -> BaseModel:
    # Model Request APIで構造化出力を取得
    model_response = model_request_sync(
        model, [request], model_settings=..., model_request_parameters=...
    )
```

**既存パターン**:
- システムプロンプト（instruction）とユーザプロンプト（user_prompt）を分離
- ユーザプロンプト内に、評価対象の詳細情報（user_query、submission等）を統合
- `textwrap.dedent()` でテンプレート整形
- Pydantic モデルによる構造化出力検証

**決定の根拠**:
- Round Controller も同じパターンで改善見込み判定を実装（FR-005の LLM判定）
- プロンプト整形は既存の `evaluate_with_llm()` 設計に準じ、一貫性を維持
- システムプロンプトと入力プロンプトの分離により、将来的なテンプレート置き換えが容易

---

### テンプレート構造の設計

#### 現在の実装方針（短期）

**形式**: Python f-string + textwrap.dedent()

```python
def build_round_prompt(
    user_query: str,
    round_number: int,
    team_id: str,
    submission_history: list[SubmissionRecord],
    evaluation_feedback: list[EvaluationResult],
    leaderboard_ranking: list[LeaderboardEntry],
    current_team_rank: int,
) -> str:
    """ラウンドプロンプト生成

    Args:
        user_query: 初回ユーザクエリ
        round_number: 現在のラウンド番号
        submission_history: 過去のSubmission履歴（最新N件に制限）
        evaluation_feedback: 対応する評価結果
        leaderboard_ranking: 全チームの最高スコアランキング
        current_team_rank: 当該チームの現在順位

    Returns:
        統合されたプロンプト文字列
    """
    from textwrap import dedent

    # ラウンド1と以降で異なるプロンプト構造
    if round_number == 1:
        # 初回: ユーザクエリのみ
        return dedent(f"""
            ユーザのクエリに対して、最良の回答を提供してください。

            クエリ:
            {user_query}
        """).strip()
    else:
        # 2ラウンド目以降: コンテキスト統合
        # 1. Submission履歴の整形
        history_text = _format_submission_history(submission_history, evaluation_feedback)

        # 2. ランキング情報の整形
        ranking_text = _format_leaderboard_info(leaderboard_ranking, current_team_rank, team_id)

        # 3. 統合プロンプト生成
        return dedent(f"""
            ユーザのクエリに対して、継続的に改善した回答を提供してください。

            元のクエリ:
            {user_query}

            これまでのあなたのSubmission履歴と評価結果:
            {history_text}

            チーム全体のランキング:
            {ranking_text}

            このラウンドでの改善点:
            - 前回の評価フィードバックに基づいて改善してください
            - 自分たちの現在順位（{current_team_rank}位）を念頭に、品質向上に注力してください
        """).strip()


def _format_submission_history(
    records: list[SubmissionRecord],
    feedbacks: list[EvaluationResult]
) -> str:
    """Submission履歴をテキスト形式で整形"""
    lines = []
    for i, (record, feedback) in enumerate(zip(records, feedbacks), 1):
        lines.append(dedent(f"""
            ラウンド {record.round_number}:
            - Submission: {record.content[:200]}...  # 最初200文字に制限
            - スコア: {feedback.overall_score:.1f}/100
            - フィードバック: {feedback.feedback_summary}
        """).strip())
    return "\n\n".join(lines)


def _format_leaderboard_info(
    ranking: list[LeaderboardEntry],
    current_rank: int,
    team_id: str
) -> str:
    """ランキング情報をテキスト形式で整形"""
    lines = ["全チーム最高スコアランキング:"]
    for entry in ranking[:10]:  # 上位10チームのみ表示
        marker = "← あなたのチーム" if entry.team_id == team_id else ""
        lines.append(
            f"  {entry.rank}位: {entry.team_name} "
            f"(スコア: {entry.best_score:.1f}/100) {marker}"
        )
    lines.append(f"\nあなたのチームの現在順位: {current_rank}位")
    return "\n".join(lines)
```

**メリット**:
- 実装が簡潔で、即座に本機能に組み込み可能
- Python 標準機能のみを使用（外部依存なし）
- Evaluator の既存パターンに準拠

**制限事項**:
- テンプレート管理が散在（複数の関数に分散）
- テンプレートエンジン（Jinja2等）による動的な制御フロー不可

---

#### 将来の外部化設計（長期）

**Prompt Builder コンポーネント化の想定**:

1. **インターフェース分離**（依存性注入）

```python
# src/mixseek/prompt_builder/protocol.py
from typing import Protocol

class PromptBuilder(Protocol):
    """プロンプト生成のプロトコル（将来の外部化に対応）"""

    def build_initial_prompt(
        self,
        user_query: str,
        team_id: str,
        metadata: dict[str, Any] = None,
    ) -> str:
        """初回プロンプト生成"""
        ...

    def build_continuation_prompt(
        self,
        user_query: str,
        round_number: int,
        team_id: str,
        submission_history: list[SubmissionRecord],
        evaluation_feedback: list[EvaluationResult],
        leaderboard_ranking: list[LeaderboardEntry],
        current_team_rank: int,
        metadata: dict[str, Any] = None,
    ) -> str:
        """継続プロンプト生成"""
        ...
```

2. **複数の実装の可能性**

```python
# 短期実装（現在）
class PlainTextPromptBuilder(PromptBuilder):
    """f-string + textwrap.dedent ベースの実装"""
    ...

# 長期実装（将来）
class Jinja2PromptBuilder(PromptBuilder):
    """Jinja2テンプレートエンジンベースの実装"""

    def __init__(self, template_dir: Path):
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def build_continuation_prompt(self, ...) -> str:
        template = self.env.get_template("continuation_prompt.jinja2")
        return template.render(
            user_query=user_query,
            round_number=round_number,
            submission_history=submission_history,
            # ...
        )
```

3. **Jinja2テンプレート例** (`templates/continuation_prompt.jinja2`)

```jinja2
ユーザのクエリに対して、継続的に改善した回答を提供してください。

元のクエリ:
{{ user_query }}

これまでのあなたのSubmission履歴と評価結果:
{% for record in submission_history %}
ラウンド {{ record.round_number }}:
- Submission: {{ record.content[:200] }}...
- スコア: {{ record.score }}/100
- フィードバック: {{ record.feedback }}

{% endfor %}

チーム全体のランキング:
全チーム最高スコアランキング:
{% for ranking in leaderboard_ranking[:10] %}
  {{ ranking.rank }}位: {{ ranking.team_name }} (スコア: {{ ranking.best_score }}/100)
  {% if ranking.team_id == team_id %}← あなたのチーム{% endif %}
{% endfor %}

あなたのチームの現在順位: {{ current_team_rank }}位

このラウンドでの改善点:
- 前回の評価フィードバックに基づいて改善してください
- 自分たちの現在順位（{{ current_team_rank }}位）を念頭に、品質向上に注力してください
```

4. **Round Controller での使用方法**（DI パターン）

```python
class RoundController:
    def __init__(
        self,
        team_config_path: Path,
        workspace: Path,
        round_number: int = 1,
        prompt_builder: PromptBuilder | None = None,
    ):
        self.team_config = load_team_config(team_config_path, workspace)
        self.workspace = workspace
        self.round_number = round_number

        # デフォルトはPlainTextPromptBuilder、テスト時はMockに置き換え可能
        self.prompt_builder = prompt_builder or PlainTextPromptBuilder()

    async def _build_team_prompt(
        self,
        user_query: str,
        context: RoundContext,
    ) -> str:
        """チームへのプロンプト生成"""
        if context.round_number == 1:
            return self.prompt_builder.build_initial_prompt(
                user_query=user_query,
                team_id=self.team_config.team_id,
            )
        else:
            return self.prompt_builder.build_continuation_prompt(
                user_query=user_query,
                round_number=context.round_number,
                team_id=self.team_config.team_id,
                submission_history=context.submission_history,
                evaluation_feedback=context.evaluation_feedback,
                leaderboard_ranking=context.leaderboard_ranking,
                current_team_rank=context.current_team_rank,
            )
```

**移行戦略**:
1. **フェーズ1**: `PlainTextPromptBuilder` を実装、Round Controller に統合
2. **フェーズ2**: `Jinja2PromptBuilder` を実装し、並行運用
3. **フェーズ3**: テンプレートファイルをスキーマ化し、ユーザがカスタマイズ可能にする

---

### コンテキスト情報の注入方法

#### 1. Submission履歴の取得フロー

```python
# Round Controller でのプロンプト生成ロジック
async def run_round(
    self,
    user_prompt: str,
    execution_id: str,
    round_number: int,
) -> RoundResult:
    """複数ラウンド対応版"""

    # コンテキスト情報を段階的に取得
    context = await self._gather_round_context(execution_id, round_number)

    # ラウンドプロンプト生成
    team_prompt = await self._build_team_prompt(user_prompt, context)

    # Leader Agent に送信（既存インターフェース不変）
    result = await leader_agent.run(team_prompt, deps=deps)

    return result


async def _gather_round_context(
    self,
    execution_id: str,
    current_round: int,
) -> RoundContext:
    """ラウンドコンテキスト情報を DuckDB から取得"""

    store = AggregationStore(db_path=self.workspace / "mixseek.db")

    # 1. 過去のSubmission履歴取得（DuckDB query）
    submission_history = await store.get_team_submission_history(
        execution_id=execution_id,
        team_id=self.team_config.team_id,
        limit=current_round - 1,  # 前ラウンドまでのみ
    )

    # 2. 対応する評価結果を取得
    evaluation_feedback = await store.get_evaluation_results_by_execution(
        execution_id=execution_id,
        team_id=self.team_config.team_id,
    )

    # 3. leader_board から全チームランキング取得
    leaderboard_ranking = await store.get_leaderboard_ranking_by_execution(
        execution_id=execution_id,
        limit=10,  # 上位10チーム
    )

    # 4. 当該チームの現在順位を計算
    current_rank = await store.get_team_current_rank(
        execution_id=execution_id,
        team_id=self.team_config.team_id,
    )

    return RoundContext(
        round_number=current_round,
        submission_history=submission_history,
        evaluation_feedback=evaluation_feedback,
        leaderboard_ranking=leaderboard_ranking,
        current_team_rank=current_rank,
    )
```

#### 2. DuckDB クエリの最適化

**要件（FR-002, SC-007）**:
- プロンプトにranking情報および当該チームの順位を **100%正確** に含める
- ランキングは leader_board テーブルの `best_score` と `round_number DESC` で計算

```sql
-- leader_board から全チーム最高スコアランキングを取得
SELECT
    team_id,
    team_name,
    MAX(score) as best_score,
    MAX(round_number) as latest_round
FROM leader_board
WHERE execution_id = :execution_id
GROUP BY team_id, team_name
ORDER BY best_score DESC, latest_round DESC
LIMIT :limit
```

```sql
-- 当該チームの現在順位を計算
WITH team_rankings AS (
    SELECT
        team_id,
        team_name,
        ROW_NUMBER() OVER (ORDER BY MAX(score) DESC, MAX(round_number) DESC) as rank
    FROM leader_board
    WHERE execution_id = :execution_id
    GROUP BY team_id, team_name
)
SELECT rank FROM team_rankings WHERE team_id = :team_id
```

---

### トークン制限対策

#### 1. 段階的情報配置

**優先順位**（トークン制約下での情報保持）:

```
レベル1（必須、必ず含める）:
  - 元のユーザクエリ
  - 当該チームの現在順位
  - 最新ラウンドのスコア

レベル2（推奨、可能な限り含める）:
  - 前ラウンドのフィードバック（要約）
  - 上位3チームのランキング情報
  - 改善トレンド（スコア推移）

レベル3（補足、容量に余裕がある場合のみ）:
  - 過去全ラウンドのSubmission
  - 全チーム（トップ10）のランキング詳細
  - 各メトリクスの詳細スコア
```

#### 2. Submission 履歴の圧縮戦略

```python
def _compress_submission_history(
    records: list[SubmissionRecord],
    max_tokens: int = 2000,  # Submission部分の最大トークン数
) -> str:
    """Submission履歴をトークン制限内に圧縮"""

    if not records:
        return "（過去のSubmissionはありません）"

    # 最新N件（デフォルト: 5件）に制限
    recent_records = records[-5:]

    compressed_items = []
    token_count = 0

    for record in recent_records:
        # Submissionを要約（最初200文字 + 末尾100文字）
        if len(record.content) > 300:
            summary = f"{record.content[:200]}...[中略]...{record.content[-100:]}"
        else:
            summary = record.content

        item = f"ラウンド {record.round_number}: {summary[:200]}..."

        estimated_tokens = len(item.split()) + 50  # 概算
        if token_count + estimated_tokens > max_tokens:
            break

        compressed_items.append(item)
        token_count += estimated_tokens

    return "\n".join(compressed_items)
```

#### 3. 設定可能なトークン予算

```python
@dataclass
class RoundPromptConfig:
    """ラウンドプロンプト設定（トークン制限対応）"""

    max_submission_history_items: int = 5      # Submission履歴の最大数
    max_leaderboard_display_teams: int = 10    # 表示するランキングチーム数
    submission_preview_chars: int = 200        # Submission表示最大文字数
    enable_trend_analysis: bool = True         # スコア推移分析の有効化

    # トークン予算（LLM model_request_sync の max_tokens と連動）
    estimated_prompt_tokens: int = 3000        # プロンプト部分の最大推定トークン


# Round Controller での使用例
class RoundController:
    def __init__(self, ..., prompt_config: RoundPromptConfig | None = None):
        self.prompt_config = prompt_config or RoundPromptConfig()

    async def _build_team_prompt(self, ...) -> str:
        context = await self._gather_round_context(...)

        # 設定に基づいてコンテキスト情報を制限
        history = context.submission_history[
            -self.prompt_config.max_submission_history_items:
        ]
        ranking = context.leaderboard_ranking[
            :self.prompt_config.max_leaderboard_display_teams
        ]

        # プロンプト生成
        return self.prompt_builder.build_continuation_prompt(
            user_query=context.user_query,
            round_number=context.round_number,
            submission_history=history,
            leaderboard_ranking=ranking,
            ...
        )
```

---

## 検討した代替案

### 1. テンプレートエンジン選択肢

| 方式 | 採用 | 理由 |
|------|------|------|
| **f-string + textwrap** | ✅ 短期採用 | 実装迅速、外部依存なし、既存パターン準拠 |
| **Jinja2** | ⭕ 長期予定 | 複雑なテンプレート制御、ユーザカスタマイズ可能 |
| **Mustache** | ❌ 非採用 | Python環境では標準的でない、Jinja2より汎用性が低い |
| **str.format()** | ❌ 非採用 | f-string より可読性が劣る |
| **Template String (Django)** | ❌ 非採用 | Django 依存、プロジェクト構成に合わない |

**決定理由**:
- **短期**: f-string の即座の実装可能性（本機能のFR-002-FR-013の実装時間を短縮）
- **長期**: Jinja2 への段階的移行により、テンプレート管理の柔軟性を確保

---

### 2. コンテキスト情報の集約方式

| 方式 | 採用 | 理由 |
|------|------|------|
| **単一プロンプト文字列** | ✅ 採用 | 既存 Leader Agent API との整合性、Prompt Engineer 最適化範囲を集約 |
| **構造化データ（JSON）** | ❌ 非採用 | LLM 入力を JSON に限定すると、自然言語プロンプティング活動を制限 |
| **複数メッセージ履歴** | ⭕ 将来検討 | Pydantic AI の Message History 機能を活用した改善見込み判定時に適用 |
| **Tool 経由での情報注入** | ❌ 非採用 | Tool は Member Agent のタスク選択用であり、プロンプト統合には不適切 |

**決定理由**:
- **統一プロンプト**: Leader Agent の既存 `run(user_prompt)` インターフェースを変更しない
- **将来性**: Message History は改善見込み判定（LLM-as-a-Judge）に適用可能

---

### 3. Submission 履歴の保存方式

| 方式 | 採用 | 理由 |
|------|------|------|
| **DuckDB `leader_board` テーブル** | ✅ 採用 | 仕様（FR-004）で定義、並列書き込み対応（MVCC） |
| **メモリキャッシュ** | ❌ 非採用 | 複数チーム並列実行時のデータ整合性が保証できない |
| **Redis** | ❌ 非採用 | 外部依存、プロジェクト構成に追加負担 |
| **ファイルシステム（JSON）** | ❌ 非採用 | 並列書き込み時のロック競合問題 |

**決定理由**:
- **DuckDB**: 既存ストレージインフラの活用、MVCC による並列安全性（仕様 SC-003）

---

### 4. トークン制限対策の方式

| 方式 | 採用 | 理由 |
|------|------|------|
| **固定トークン予算制** | ✅ 採用 | 構成可能、実装が簡潔 |
| **動的トークン計測** | ⭕ 将来検討 | LLM API の token counting service 活用（コスト増加の可能性） |
| **スライディングウィンドウ** | ⭕ 将来検討 | 最新情報の優先度制御、複雑な実装 |
| **ハードコードの固定値** | ❌ 非採用 | 憲章 Article 9（Data Accuracy Mandate）違反 |

**決定理由**:
- **短期**: RoundPromptConfig の設定値管理により柔軟性を確保
- **長期**: トークン計測の必要性が判明次第、段階的に対応

---

## 将来的な外部化の考慮点

### 1. Prompt Builder コンポーネント化の段階

#### Phase 1: インターフェース定義（現在）

```python
# src/mixseek/prompt_builder/__init__.py
from mixseek.prompt_builder.protocol import PromptBuilder
from mixseek.prompt_builder.plain_text import PlainTextPromptBuilder

__all__ = ["PromptBuilder", "PlainTextPromptBuilder"]
```

**成果物**:
- `PromptBuilder` プロトコルの定義（DI対応）
- `PlainTextPromptBuilder` の実装
- Round Controller への統合

#### Phase 2: テンプレートエンジン導入

```
specs/
├── 040-mixseek-core-prompt-builder/
│   ├── spec.md              # 仕様書
│   ├── plan.md
│   ├── data-model.md
│   └── contracts/
│       └── jinja2_templates/
│           ├── initial_prompt.jinja2
│           ├── continuation_prompt.jinja2
│           └── improvement_judgment_system.jinja2

src/mixseek/
└── prompt_builder/
    ├── __init__.py
    ├── protocol.py           # PromptBuilder プロトコル
    ├── plain_text.py         # PlainTextPromptBuilder（現在の実装）
    ├── jinja2_builder.py     # Jinja2PromptBuilder
    └── models.py             # PromptContext等
```

#### Phase 3: ユーザカスタマイズ対応

```python
# ユーザワークスペース内でテンプレートをカスタマイズ
$MIXSEEK_WORKSPACE/
├── configs/
│   ├── orchestrator.toml
│   └── prompt_templates/
│       ├── initial_prompt.jinja2      # ユーザがカスタマイズ可能
│       └── continuation_prompt.jinja2
├── mixseek.db
└── results/

# Round Controller での読み込み例
class RoundController:
    def __init__(self, ..., template_dir: Path | None = None):
        template_dir = template_dir or (
            self.workspace / "configs" / "prompt_templates"
        )
        if template_dir.exists():
            self.prompt_builder = Jinja2PromptBuilder(template_dir)
        else:
            self.prompt_builder = PlainTextPromptBuilder()  # フォールバック
```

---

### 2. API 安定性の確保

#### 後方互換性の維持

```python
# Future API（Phase 2）
class Jinja2PromptBuilder(PromptBuilder):
    """既存の PromptBuilder インターフェースを維持"""

    def build_continuation_prompt(self, ...) -> str:
        """既存シグネチャを保持"""
        # 内部実装は Jinja2 に置き換わるが、外部インターフェースは変わらない
        ...

# Round Controller のコード変更なし
# 既存コード: self.prompt_builder.build_continuation_prompt(...)
# → PlainTextPromptBuilder から Jinja2PromptBuilder への置き換えは自動
```

#### バージョニング戦略

```python
# src/mixseek/prompt_builder/__init__.py

__version__ = "0.1.0"  # Phase 1
# __version__ = "0.2.0"  # Phase 2（Jinja2対応）
# __version__ = "1.0.0"  # Phase 3（ユーザカスタマイズ対応）

# Semantic Versioning
# MAJOR: Breaking changes to PromptBuilder protocol
# MINOR: New features (e.g., new template variables)
# PATCH: Bug fixes, performance improvements
```

---

### 3. テスト戦略

#### Phase 1: PromptBuilder のモック化

```python
# tests/unit/round_controller/test_prompt_integration.py

class MockPromptBuilder(PromptBuilder):
    """テスト用Mock実装"""

    def build_continuation_prompt(self, ...) -> str:
        # テスト用の固定プロンプトを返す
        return "Mock prompt for testing"


def test_round_controller_uses_prompt_builder():
    """Round Controller が PromptBuilder を正しく使用すること"""
    mock_builder = MockPromptBuilder()
    controller = RoundController(..., prompt_builder=mock_builder)

    result = controller.run_round(...)

    # PromptBuilder が呼ばれたことを検証
    # (通常のテストではビヘイビア検証)
```

#### Phase 2: テンプレート単体テスト

```python
# tests/unit/prompt_builder/test_jinja2_builder.py

def test_jinja2_template_renders_correctly():
    """Jinja2テンプレートが正しくレンダリングされること"""
    builder = Jinja2PromptBuilder(Path("specs/015-user-prompt-builder-team/contracts"))

    prompt = builder.build_continuation_prompt(
        user_query="Test query",
        round_number=2,
        submission_history=[...],
        ...
    )

    # プロンプトが必須情報を含むことを検証
    assert "Test query" in prompt
    assert "ラウンド" in prompt
    # ...
```

---

### 4. 拡張ポイント

#### テンプレート変数の固定化

```python
# 仕様: 040-mixseek-core-prompt-builder
# テンプレートで使用可能な変数の仕様定義

TEMPLATE_VARIABLES = {
    # 初回プロンプト
    "initial": {
        "user_query": "str",
        "team_id": "str",
        "team_name": "str",
    },

    # 継続プロンプト
    "continuation": {
        "user_query": "str",
        "round_number": "int",
        "team_id": "str",
        "team_name": "str",
        "submission_history": "list[SubmissionRecord]",
        "evaluation_feedback": "list[EvaluationResult]",
        "leaderboard_ranking": "list[LeaderboardEntry]",
        "current_team_rank": "int",
    },
}
```

#### カスタムフィルタ・テスト

```python
# src/mixseek/prompt_builder/jinja2_builder.py

def setup_jinja2_environment(env: jinja2.Environment) -> None:
    """Jinja2カスタムフィルタの登録"""

    # スコア表示用フィルタ
    env.filters["format_score"] = lambda s: f"{s:.1f}/100"

    # テキスト要約フィルタ
    env.filters["summarize"] = lambda t, max_len=200: (
        t[:max_len] + "..." if len(t) > max_len else t
    )

    # ランキング順位フィルタ（メダル表示）
    env.filters["medal"] = lambda rank: (
        "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else str(rank)
    )

# テンプレート内での使用例
# {{ submission.score | format_score }}
# {{ submission.content | summarize(150) }}
# {{ ranking.rank | medal }}
```

---

## 実装ロードマップ

### タスク概要

```
012-round-controller 実装時間割:

[Phase 1 実装] 本機能の FR-001～FR-013 実装（現在）
├─ RoundPromptBuilder の基本実装（PlainTextPromptBuilder）
├─ Round Controller への統合
├─ DuckDB コンテキスト取得
└─ トークン制限対策（設定値による）

[Phase 2 計画] Prompt Builder コンポーネント化（別途仕様）
├─ PromptBuilder プロトコルの抽出
├─ Jinja2PromptBuilder の実装
├─ テンプレートファイル管理
└─ テスト整備

[Phase 3 計画] ユーザカスタマイズ（別途仕様）
├─ ユーザテンプレートディレクトリの定義
├─ テンプレート検証ロジック
└─ ドキュメント作成
```

---

## 結論

**本戦略の要点**:

1. **短期（037実装）**: f-string + textwrap による実装で、FR-002のプロンプト統合要件を満たす
2. **中期（040仕様）**: PromptBuilder プロトコルを通じて、Jinja2への段階的移行を実現
3. **長期（ユーザカスタマイズ）**: テンプレートファイルの外部化により、ユーザによるカスタマイズを支援

**憲章整合性**:
- **Article 9 (Data Accuracy)**: 環境変数・設定値から明示的にコンテキスト情報を取得
- **Article 10 (DRY)**: Evaluator の既存パターンを再利用
- **Article 14 (SpecKit Consistency)**: 001仕様の FR-002（複数チーム並列実行）とFR-006（ラウンドベース処理）に準拠

**拡張性**:
- Protocol ベースの DI により、テンプレートエンジン切り替えが容易
- 設定値（RoundPromptConfig）によるトークン予算の柔軟な管理
- ユーザテンプレートのカスタマイズに対応予定

