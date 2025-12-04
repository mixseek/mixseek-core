# クイックスタートガイド: UserPromptBuilder - Evaluator/JudgementClient統合

**ブランチ**: `140-user-prompt-builder-evaluator-judgement` | **日付**: 2025-11-25

## 概要

本ガイドは、UserPromptBuilderを使用してEvaluatorとJudgementClientのプロンプトをカスタマイズする方法を説明します。

## 前提条件

- mixseek-coreがインストール済み（`uv sync`実行済み）
- `MIXSEEK_WORKSPACE`環境変数が設定済み
- Pythonバージョン: 3.13.9以上

## 基本的な使用方法

### 1. デフォルト設定の生成

最初に、`mixseek config init`コマンドでデフォルト設定ファイルを生成します。

```bash
# ワークスペース設定
export MIXSEEK_WORKSPACE=/path/to/workspace

# デフォルト設定ファイル生成
mixseek config init
```

これにより、以下のファイルが生成されます:
- `$MIXSEEK_WORKSPACE/configs/prompt_builder.toml`

### 2. デフォルトプロンプトの確認

生成された`prompt_builder.toml`を開くと、以下の3つのプロンプトテンプレートが含まれています:

```toml
[prompt_builder]

# Team Agent用プロンプトテンプレート
team_user_prompt = """
...（既存のTeamプロンプト）...
"""

# Evaluator用プロンプトテンプレート
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

# JudgementClient用プロンプトテンプレート
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

## プロンプトのカスタマイズ

### 3. Evaluatorプロンプトのカスタマイズ

Evaluatorプロンプトをカスタマイズして、評価基準を明確化する例:

```toml
# カスタムEvaluatorプロンプト
evaluator_user_prompt = """
---
現在日時: {{ current_datetime }}
---

以下の基準でエージェントの提出内容を評価してください：
1. **正確性**: 事実関係は正しいか
2. **完全性**: 必要な情報が網羅されているか
3. **明瞭性**: 分かりやすく説明されているか

# ユーザクエリ
{{ user_query }}

# 提出内容
{{ submission }}

**評価基準**:
- 0-25点: 大幅な改善が必要
- 26-50点: 改善の余地あり
- 51-75点: 良好
- 76-100点: 優秀
"""
```

### 4. JudgementClientプロンプトのカスタマイズ

JudgementClientプロンプトをカスタマイズして、継続判定基準を調整する例:

```toml
# カスタムJudgementClientプロンプト
judgment_user_prompt = """
# タスク
以下の提出履歴を分析し、次のラウンドに進むべきかを判定してください。

## 判定基準
- **継続推奨**: スコアが前回から5点以上向上している場合
- **継続検討**: スコアが微増または横ばいの場合
- **停止推奨**: スコアが3ラウンド連続で改善していない場合

# ユーザクエリ
{{ user_prompt }}

# 提出履歴（ラウンド {{ round_number }}まで）
{{ submission_history }}

# リーダーボード
{{ ranking_table }}

# あなたのチームの順位
{{ team_position_message }}

現在時刻: {{ current_datetime }}
"""
```

## 利用可能なプレースホルダー変数

### Evaluatorプロンプト

| 変数名 | 型 | 説明 | 例 |
|-------|---|------|---|
| `user_query` | `str` | 元のユーザークエリ | `"Pythonとは何ですか？"` |
| `submission` | `str` | AIエージェントのSubmission | `"Pythonはプログラミング言語です..."` |
| `current_datetime` | `str` | 現在日時（ISO 8601形式、UserPromptBuilder内で自動取得） | `"2025-11-25T14:30:00+09:00"` |

### JudgementClientプロンプト

| 変数名 | 型 | 説明 | 例 |
|-------|---|------|---|
| `user_prompt` | `str` | 元のユーザープロンプト | `"データ分析レポートを作成"` |
| `round_number` | `int` | 現在のラウンド番号 | `3` |
| `submission_history` | `str` | 過去のSubmission履歴（整形済み） | `"## ラウンド 1\n**提出内容:**\n..."` |
| `ranking_table` | `str` | Leader Boardランキング情報（整形済み） | `"順位 \| チームID \| スコア\n1 \| team-001 \| 95.50\n..."` |
| `team_position_message` | `str` | 当該チームの順位メッセージ（整形済み） | `"あなたのチームは2位です"` |
| `current_datetime` | `str` | 現在日時（ISO 8601形式） | `"2025-11-25T14:30:00+09:00"` |

## プログラムからの使用方法

### 5. Pythonコードでの使用例

#### Evaluatorプロンプト生成

```python
from pathlib import Path
from mixseek.prompt_builder import UserPromptBuilder, EvaluatorPromptContext

# ワークスペースパス
workspace = Path("/path/to/workspace")

# UserPromptBuilderインスタンス化
builder = UserPromptBuilder(workspace=workspace)

# コンテキスト作成
context = EvaluatorPromptContext(
    user_query="Pythonとは何ですか？",
    submission="Pythonはプログラミング言語です。動的型付け言語で、可読性が高く..."
)

# プロンプト整形（current_datetimeは内部で取得されます）
formatted_prompt = builder.build_evaluator_prompt(context)
print(formatted_prompt)
```

**出力例**:
```
---
現在日時: 2025-11-25T14:30:00+09:00
---

以下のユーザクエリに対するエージェントの提出内容を、あなたの役割に従って評価してください。

# ユーザクエリ
Pythonとは何ですか？

# 提出内容
Pythonはプログラミング言語です。動的型付け言語で、可読性が高く...
```

#### JudgementClientプロンプト生成

```python
from pathlib import Path
from mixseek.prompt_builder import UserPromptBuilder, RoundPromptContext
from mixseek.round_controller.models import RoundState

# ワークスペースパス
workspace = Path("/path/to/workspace")

# UserPromptBuilderインスタンス化（storeなし）
builder = UserPromptBuilder(workspace=workspace, store=None)

# ラウンド履歴
round_history = [
    RoundState(
        round_number=1,
        submission_content="初回提出: データ分析レポート草稿",
        evaluation_score=75.5,
        score_details={"accuracy": 80.0, "completeness": 71.0}
    ),
    RoundState(
        round_number=2,
        submission_content="改善版: データ可視化を追加",
        evaluation_score=82.3,
        score_details={"accuracy": 85.0, "completeness": 79.6}
    )
]

# コンテキスト作成
context = RoundPromptContext(
    user_prompt="データ分析レポートを作成してください",
    round_number=3,
    round_history=round_history,
    team_id="team-001",
    team_name="Team Alpha",
    execution_id="exec-123",
    store=None  # storeなしの場合、ランキング情報は空文字列
)

# プロンプト整形
formatted_prompt = builder.build_judgment_prompt(context)
print(formatted_prompt)
```

**出力例**:
```
# タスク
以下の提出履歴に基づいて、チームは次のラウンドに進むべきでしょうか？判定、理由、確信度を提供してください。

# ユーザクエリ
データ分析レポートを作成してください

# 提出履歴

## ラウンド 1
**提出内容:**
初回提出: データ分析レポート草稿

**スコア:** 75.50/100
**スコア詳細:**
{
  "accuracy": 80.0,
  "completeness": 71.0
}

## ラウンド 2
**提出内容:**
改善版: データ可視化を追加

**スコア:** 82.30/100
**スコア詳細:**
{
  "accuracy": 85.0,
  "completeness": 79.6
}

# リーダーボード

```

## トラブルシューティング

### エラー: "Jinja2 template error: 'variable_name' is undefined"

**原因**: プロンプトテンプレートに存在しないプレースホルダー変数を使用しています。

**解決策**: 利用可能な変数のリストを確認し、正しい変数名を使用してください。

```toml
# 誤り
evaluator_user_prompt = """
{{ invalid_variable }}
"""

# 正しい
evaluator_user_prompt = """
{{ user_query }}
{{ submission }}
{{ current_datetime }}
"""
```

### エラー: "ValidationError: user_query cannot be empty"

**原因**: EvaluatorPromptContextのuser_queryまたはsubmissionフィールドが空文字列です。

**解決策**: 必須フィールドに有効な値を設定してください。

```python
# 誤り
context = EvaluatorPromptContext(
    user_query="",  # 空文字列
    submission="..."
)

# 正しい
context = EvaluatorPromptContext(
    user_query="Pythonとは何ですか？",
    submission="..."
)
```

**Note**: `current_datetime`はEvaluatorPromptContextに含まれません。UserPromptBuilder内部で自動的に取得されます。

### エラー: "FileNotFoundError: prompt_builder.toml not found"

**原因**: 設定ファイルが存在しません。

**解決策**: `mixseek config init`を実行して設定ファイルを生成してください。

```bash
export MIXSEEK_WORKSPACE=/path/to/workspace
mixseek config init
```

## 高度な使用例

### カスタムプロンプトでの条件分岐

Jinja2の条件分岐を使用して、ラウンド番号に応じたメッセージを表示:

```toml
judgment_user_prompt = """
# タスク
{% if round_number == 1 %}
初回ラウンドです。提出履歴はまだありません。
{% elif round_number < 3 %}
ラウンド {{ round_number }} です。前回の提出を改善しましょう。
{% else %}
ラウンド {{ round_number }} です。大幅な改善が見られない場合は終了を検討してください。
{% endif %}

# ユーザクエリ
{{ user_prompt }}

# 提出履歴
{{ submission_history }}
"""
```

### プロンプトの動的切り替え

環境変数でプロンプトを動的に切り替える:

```bash
# 開発環境: 詳細な評価プロンプト
export MIXSEEK_EVALUATOR_USER_PROMPT="詳細評価プロンプト..."

# 本番環境: 簡潔な評価プロンプト
export MIXSEEK_EVALUATOR_USER_PROMPT="簡潔評価プロンプト..."
```

## まとめ

本ガイドでは、以下の内容を説明しました:

1. ✅ デフォルト設定の生成（`mixseek config init`）
2. ✅ Evaluatorプロンプトのカスタマイズ
3. ✅ JudgementClientプロンプトのカスタマイズ
4. ✅ 利用可能なプレースホルダー変数
5. ✅ Pythonコードでの使用例
6. ✅ トラブルシューティング
7. ✅ 高度な使用例

次のステップ:
- 実際のプロジェクトでプロンプトをカスタマイズ
- 評価精度の向上を実験
- ラウンド継続判定基準の調整

詳細な仕様については、[spec.md](./spec.md)と[data-model.md](./data-model.md)を参照してください。
