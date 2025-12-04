# Quickstart Guide: UserPromptBuilder

**Feature**: 092-user-prompt-builder-team
**Date**: 2025-11-19
**Audience**: 開発者・研究者・運用者

このガイドでは、UserPromptBuilderの基本的な使用方法、設定カスタマイズ、トラブルシューティングを説明します。

---

## 目次

1. [インストールと初期設定](#1-インストールと初期設定)
2. [基本的な使用方法](#2-基本的な使用方法)
3. [プロンプトのカスタマイズ](#3-プロンプトのカスタマイズ)
4. [タイムゾーン設定](#4-タイムゾーン設定)
5. [トラブルシューティング](#5-トラブルシューティング)
6. [よくある質問（FAQ）](#6-よくある質問faq)

---

## 1. インストールと初期設定

### 1.1 前提条件

- Python 3.13.9以上
- mixseek-coreパッケージがインストール済み
- 環境変数 `MIXSEEK_WORKSPACE` が設定済み

### 1.2 設定ファイルの初期化

UserPromptBuilder用の設定ファイルを生成します：

```bash
# ワークスペースを設定
export MIXSEEK_WORKSPACE=/path/to/your/workspace

# 設定ファイルを初期化（既存ファイルがある場合は --force を使用）
mixseek config init

# 生成されたファイルを確認
cat $MIXSEEK_WORKSPACE/configs/prompt_builder.toml
```

これにより、以下のファイルが生成されます：

```
$MIXSEEK_WORKSPACE/
└── configs/
    └── prompt_builder.toml  # UserPromptBuilder設定ファイル
```

---

## 2. 基本的な使用方法

### 2.1 デフォルト設定での使用

UserPromptBuilderはRoundControllerから自動的に呼び出されます。通常、手動で呼び出す必要はありません。

```bash
# 通常のmixseekコマンド実行
mixseek team "データ分析タスク" --config team.toml --save-db
```

RoundControllerが内部でUserPromptBuilderを使用してプロンプトを整形します。

### 2.2 プログラムからの使用

Pythonコードから直接UserPromptBuilderを使用する場合：

```python
from pathlib import Path
from mixseek.prompt_builder import UserPromptBuilder
from mixseek.prompt_builder.models import RoundPromptContext
from mixseek.round_controller.models import RoundState
from mixseek.storage.aggregation_store import AggregationStore

# UserPromptBuilderインスタンス作成
workspace = Path("/path/to/workspace")
store = AggregationStore(db_path=workspace / "mixseek.db")
prompt_builder = UserPromptBuilder(workspace=workspace, store=store)

# コンテキスト作成
context = RoundPromptContext(
    user_prompt="データ分析タスク",
    round_number=1,
    round_history=[],
    team_id="team1",
    team_name="Alpha",
    execution_id="exec1",
    store=store,
)

# プロンプト整形
formatted_prompt = await prompt_builder.build_team_prompt(context)
print(formatted_prompt)
```

---

## 3. プロンプトのカスタマイズ

### 3.1 TOML設定ファイルの編集

`$MIXSEEK_WORKSPACE/configs/prompt_builder.toml` を編集してプロンプトをカスタマイズします。

#### 利用可能なプレースホルダー変数

| 変数名 | 説明 | 型 |
|--------|------|-----|
| `{{ user_prompt }}` | 元のユーザプロンプト | 文字列 |
| `{{ round_number }}` | 現在のラウンド番号 | 整数 |
| `{{ submission_history }}` | 過去のSubmission履歴（整形済み） | 文字列 |
| `{{ ranking_table }}` | Leader Boardランキング情報（整形済み） | 文字列 |
| `{{ team_position_message }}` | チーム順位メッセージ（整形済み） | 文字列 |
| `{{ current_datetime }}` | 現在日時（ISO 8601形式、タイムゾーン付き） | 文字列 |

#### カスタマイズ例1: シンプルなプロンプト

```toml
[prompt_builder]
team_user_prompt = """
タスク: {{ user_prompt }}

{% if round_number > 1 %}
前回の結果:
{{ submission_history }}
{% endif %}

実行日時: {{ current_datetime }}
"""
```

#### カスタマイズ例2: 詳細なフィードバック重視

```toml
[prompt_builder]
team_user_prompt = """
# 📋 タスク概要
{{ user_prompt }}

{% if round_number > 1 %}
# 📊 過去のパフォーマンス
{{ submission_history }}

# 🏆 現在の順位
{{ ranking_table }}

{{ team_position_message }}

# 🎯 改善のポイント
上記のフィードバックを基に、以下の点に焦点を当ててください：
1. 前回の弱点を克服する
2. 評価スコアを向上させる
3. フィードバックで指摘された問題を修正する
{% else %}
# 🚀 初回ラウンド
現在はラウンド1です。最高の結果を目指して頑張りましょう！
{% endif %}

---
実行日時: {{ current_datetime }}
"""
```

### 3.2 環境変数による上書き

TOML設定をコード変更せずに上書きできます：

```bash
# 環境変数でプロンプトを上書き
export MIXSEEK_TEAM_USER_PROMPT='{{ user_prompt }} - Round {{ round_number }}'

# 実行
mixseek team "タスク" --config team.toml
```

---

## 4. タイムゾーン設定

### 4.1 デフォルト（UTC）

環境変数TZが設定されていない場合、UTCがデフォルトで使用されます：

```bash
# TZ未設定の場合
mixseek team "タスク" --config team.toml

# プロンプト内の current_datetime は UTC タイムゾーン
# 例: 2025-11-19T12:34:56.789012+00:00
```

### 4.2 タイムゾーンのカスタマイズ

環境変数TZを設定して、任意のタイムゾーンを使用できます：

```bash
# 日本時間（JST）
export TZ="Asia/Tokyo"
mixseek team "タスク" --config team.toml
# 出力例: 2025-11-19T21:34:56.789012+09:00

# 米国東部時間（EST）
export TZ="America/New_York"
mixseek team "タスク" --config team.toml
# 出力例: 2025-11-19T07:34:56.789012-05:00

# ヨーロッパ中央時間（CET）
export TZ="Europe/Paris"
mixseek team "タスク" --config team.toml
# 出力例: 2025-11-19T13:34:56.789012+01:00
```

### 4.3 有効なタイムゾーン名

有効なタイムゾーン名は、IANAタイムゾーンデータベースに基づきます。主な例：

- **UTC**: `"UTC"`
- **アジア**: `"Asia/Tokyo"`, `"Asia/Shanghai"`, `"Asia/Seoul"`
- **米国**: `"America/New_York"`, `"America/Los_Angeles"`, `"America/Chicago"`
- **ヨーロッパ**: `"Europe/London"`, `"Europe/Paris"`, `"Europe/Berlin"`

全タイムゾーンリストは以下で確認できます：

```python
from zoneinfo import available_timezones
print(sorted(available_timezones()))
```

---

## 5. トラブルシューティング

### 5.1 エラー: "team_user_prompt cannot be empty"

**原因**: 設定ファイルの `team_user_prompt` が空または存在しない

**解決策**:

```bash
# 設定ファイルを再生成
mixseek config init --force

# または手動で設定を追加
echo '[prompt_builder]
team_user_prompt = "{{ user_prompt }}"' > $MIXSEEK_WORKSPACE/configs/prompt_builder.toml
```

---

### 5.2 エラー: "Invalid timezone in TZ environment variable"

**原因**: 環境変数TZに不正なタイムゾーン名が設定されている

**エラーメッセージ例**:

```
ValueError: Invalid timezone in TZ environment variable: Invalid/Timezone.
Valid examples: 'UTC', 'Asia/Tokyo', 'America/New_York'
```

**解決策**:

```bash
# 有効なタイムゾーン名を設定
export TZ="Asia/Tokyo"

# またはTZをアンセット（デフォルトのUTCを使用）
unset TZ
```

---

### 5.3 エラー: "Jinja2 template syntax error"

**原因**: TOML設定ファイルのJinja2テンプレート構文にエラーがある

**エラーメッセージ例**:

```
TemplateError: Jinja2 template syntax error at line 5: unexpected end of template
```

**解決策**:

1. TOMLファイルの該当行を確認
2. Jinja2構文のミス（`{% if %}`に対する`{% endif %}`の不足など）を修正
3. デフォルト設定に戻す：

```bash
mixseek config init --force
```

---

### 5.4 プロンプトに履歴が含まれない

**原因**: ラウンド1、またはstoreが設定されていない

**確認ポイント**:

```python
# RoundControllerの初期化時に save_db=True を設定
controller = RoundController(
    team_config_path=team_config,
    workspace=workspace,
    task=task,
    save_db=True,  # これがFalseだとstoreがNone
)
```

**解決策**:

```bash
# CLIで --save-db フラグを使用
mixseek team "タスク" --config team.toml --save-db
```

---

## 6. よくある質問（FAQ）

### Q1: プロンプト内でforループを使用できますか？

**A**: 技術的には可能ですが、推奨されません。すべてのプレースホルダー変数はUserPromptBuilder内で事前に整形されているため、テンプレート内でforループを使用する必要はありません。

```toml
# 非推奨（動作はするが推奨されない）
team_user_prompt = """
{% for state in round_history %}
Round {{ state.round_number }}: {{ state.evaluation_score }}
{% endfor %}
"""

# 推奨（整形済み変数を使用）
team_user_prompt = """
{{ submission_history }}
"""
```

---

### Q2: カスタムプレースホルダー変数を追加できますか？

**A**: 現時点では未対応です。将来的な拡張として検討されています（仕様28-29行目参照）。

---

### Q3: Evaluator用のプロンプトもカスタマイズできますか？

**A**: 現時点では未対応です。本ブランチではTeam用プロンプトのみをサポートしています。EvaluatorとJudgementClient用のプロンプトは今後のブランチで対応予定です（仕様19-20行目参照）。

---

### Q4: デフォルトプロンプトを確認する方法は？

**A**: 以下のコマンドで確認できます：

```bash
# 設定ファイルを生成
mixseek config init --force

# デフォルトプロンプトを確認
cat $MIXSEEK_WORKSPACE/configs/prompt_builder.toml
```

または、Pythonコードから：

```python
from mixseek.prompt_builder.constants import DEFAULT_TEAM_USER_PROMPT
print(DEFAULT_TEAM_USER_PROMPT)
```

---

### Q5: プロンプト整形のパフォーマンスは？

**A**: 以下のパフォーマンス目標を満たしています（95パーセンタイル）：

- **ラウンド1**: <10ms
- **ラウンド2以降**: <50ms（履歴・ランキング情報含む）

パフォーマンスが遅い場合は、以下を確認してください：

1. DuckDBのインデックスが正しく設定されているか
2. Leader Boardのデータ量が適切か
3. テンプレート内で複雑な制御構文を使用していないか

---

## まとめ

本ガイドでは、以下の内容を説明しました：

1. **インストールと初期設定**: `mixseek config init` による設定ファイル生成
2. **基本的な使用方法**: RoundControllerからの自動呼び出し
3. **プロンプトのカスタマイズ**: TOML設定ファイルと利用可能なプレースホルダー変数
4. **タイムゾーン設定**: 環境変数TZによるカスタマイズ
5. **トラブルシューティング**: よくあるエラーと解決策
6. **FAQ**: よくある質問と回答

さらに詳しい情報は、以下のドキュメントを参照してください：

- [Data Model](./data-model.md): データモデル詳細
- [API Contract](./contracts/prompt-builder-api.md): API仕様
- [Research](./research.md): 技術調査結果
