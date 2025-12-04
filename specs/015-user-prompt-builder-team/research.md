# Research: UserPromptBuilder 技術調査

**Feature**: 092-user-prompt-builder-team
**Date**: 2025-11-19
**Status**: Phase 0 完了

このドキュメントは、UserPromptBuilder実装に必要な技術調査結果をまとめたものです。

---

## 1. Jinja2によるプロンプトテンプレート管理

### 決定事項
- **採用技術**: Jinja2 (>=3.1.0)
- **理由**: Python標準のテンプレートエンジンとして広く採用され、変数埋め込みと制御構文のサポートが充実

### テンプレート設計方針

#### TOML内での変数埋め込み形式
```toml
[prompt_builder]
team_user_prompt = """
# ユーザから指定されたタスク
{{ user_prompt }}

{% if round_number > 1 %}
# 過去の提出履歴
{{ submission_history }}

# 現在のチームランキング
{{ ranking_table }}
{{ team_position_message }}

# 今回のラウンドの目標
{{ improvement_goal }}
{% else %}
現在はラウンド1です。過去のSubmissionとランキング情報はまだありません。
{% endif %}
"""
```

#### プレースホルダー変数
すべての変数はUserPromptBuilder内で事前に整形済み文字列として提供される：

- `user_prompt`: 元のユーザプロンプト（文字列）
- `round_number`: 現在のラウンド番号（整数）
- `submission_history`: 整形済み履歴文字列（ラウンド1では「まだ過去のSubmissionはありません。」）
- `ranking_table`: 整形済みランキング表（空の場合は「現在はランキング情報がありません。」）
- `team_position_message`: 整形済み順位メッセージ
- `current_datetime`: ISO 8601形式の現在日時（タイムゾーン付き）
- `improvement_goal`: 改善目標メッセージ（デフォルト: 「上記のフィードバックを基に提出内容を改善してください。」）

### 検討した代替案

| 代替案 | 評価 | 却下理由 |
|--------|------|----------|
| Python f-strings | シンプルで高速 | テンプレートの外部化が困難、ユーザーカスタマイズ不可 |
| Mustache/Handlebars | 言語非依存 | Pythonエコシステムでは一般的でない、追加依存が必要 |
| 独自テンプレート実装 | 完全制御可能 | 車輪の再発明、保守コストが高い |

---

## 2. タイムゾーン処理（環境変数TZ）

### 決定事項
- **採用方法**: `zoneinfo.ZoneInfo` (Python 3.9+標準ライブラリ)
- **デフォルトタイムゾーン**: UTC
- **Article 9準拠**: 環境変数TZから明示的に取得、デフォルト値を使用

### 実装パターン

```python
import os
from datetime import datetime, UTC
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

def get_current_datetime_with_timezone() -> str:
    """環境変数TZに基づく現在日時を取得する（ISO 8601形式）

    Returns:
        ISO 8601形式の現在日時文字列（タイムゾーン付き）

    Raises:
        ValueError: TZ環境変数が不正な値の場合
    """
    tz_name = os.environ.get("TZ")

    if tz_name is None:
        # TZ未設定の場合はUTCをデフォルト使用
        tz = UTC
    else:
        try:
            tz = ZoneInfo(tz_name)
        except ZoneInfoNotFoundError as e:
            raise ValueError(
                f"Invalid timezone in TZ environment variable: {tz_name}. "
                f"Valid examples: 'UTC', 'Asia/Tokyo', 'America/New_York'"
            ) from e

    now = datetime.now(tz)
    return now.isoformat()
```

### バリデーション戦略
- TZ環境変数が設定されている場合、ZoneInfoでバリデーション
- 不正な値の場合は明確なエラーメッセージとともに例外を発生
- デフォルト（UTC）への暗黙的フォールバックは行わない（Article 9準拠）

### 検討した代替案

| 代替案 | 評価 | 却下理由 |
|--------|------|----------|
| pytz | 歴史的に広く使用 | Python 3.9+ではzoneinfoが標準、追加依存不要 |
| dateutil | 柔軟性が高い | 過剰な機能、標準ライブラリで十分 |
| システムlocale | OS依存性が低い | Article 9違反（明示的な設定ソースが不明確） |

---

## 3. Configuration Manager統合（仕様051-configuration準拠）

### 決定事項
- **統合方法**: Pydantic Settings (`pydantic-settings>=2.12`)
- **設定ファイルパス**: `$MIXSEEK_WORKSPACE/configs/prompt_builder.toml`
- **階層的フォールバック**: CLI引数 > 環境変数 > TOMLファイル > デフォルト値

### 設計アプローチ

#### Pydantic Settings Model
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class PromptBuilderSettings(BaseSettings):
    """UserPromptBuilder設定

    設定ソース優先順位（高→低）:
    1. CLI引数（未実装、将来的な拡張）
    2. 環境変数（MIXSEEK_プレフィックス）
    3. TOMLファイル（$MIXSEEK_WORKSPACE/configs/prompt_builder.toml）
    4. デフォルト値
    """

    team_user_prompt: str = DEFAULT_TEAM_USER_PROMPT

    model_config = SettingsConfigDict(
        env_prefix="MIXSEEK_",
        toml_file="configs/prompt_builder.toml",
        env_file_encoding="utf-8",
    )
```

### Configuration Managerとの関係
- **既存機能を再利用**: `mixseek.config.manager.ConfigurationManager` を使用してTOML読み込み
- **Pydantic Settingsの利用**: 環境変数オーバーライドとバリデーションを自動化
- **トレーサビリティ**: 設定値の出所を追跡可能（Article 9準拠）

### mixseek config init コマンド拡張

既存の `mixseek config init` コマンドにUserPromptBuilder設定ファイル生成を追加：

```python
# src/mixseek/cli/commands/config.py

def init_command(workspace: Path) -> None:
    """Initialize configuration files"""
    # ... 既存のorchestrator.toml, team.toml生成 ...

    # UserPromptBuilder設定ファイル生成を追加
    prompt_builder_toml = workspace / "configs" / "prompt_builder.toml"
    if not prompt_builder_toml.exists() or force:
        prompt_builder_toml.write_text(DEFAULT_PROMPT_BUILDER_TOML_TEMPLATE)
```

---

## 4. 既存RoundController実装の分析

### 現在の実装（controller.py:207-283行目）

#### _format_prompt_for_round メソッドの責務
1. **ラウンド1**: 元のユーザプロンプトをそのまま返す
2. **ラウンド2以降**:
   - 過去の提出履歴を整形（直近2ラウンド → **仕様では全ラウンド**に変更）
   - Leader Boardランキングを取得・整形
   - チーム順位メッセージを生成
   - 改善目標メッセージを追加

#### 移行対象ロジック

```python
# 既存実装の主要部分（RoundController._format_prompt_for_round）

# 1. 履歴整形
for state in self.round_history[-2:]:  # 直近2ラウンド
    prompt_parts.append(f"## ラウンド {state.round_number}")
    prompt_parts.append(f"スコア: {state.evaluation_score:.2f}/100")
    prompt_parts.append(f"フィードバック: {state.evaluation_feedback}")
    prompt_parts.append(f"あなたの提出内容: {state.submission_content}")

# 2. Leader Board取得
ranking = await self.store.get_leader_board_ranking(self.task.execution_id)

# 3. ランキング整形
for idx, team_entry in enumerate(ranking, start=1):
    if team_id == self.team_config.team_id:
        prompt_parts.append(f"**#{idx} {team_name} (あなたのチーム) - ...")
    else:
        prompt_parts.append(f"#{idx} {team_name} - ...")

# 4. 順位メッセージ
if current_team_position == 1:
    prompt_parts.append("🏆 現在、あなたのチームは1位です！...")
elif current_team_position <= 3:
    prompt_parts.append(f"現在、{total_teams}チーム中{current_team_position}位です。素晴らしい成績です！")
else:
    prompt_parts.append(f"現在、{total_teams}チーム中{current_team_position}位です。")
```

### UserPromptBuilderへの移行戦略

#### 設計方針
- **既存ロジックを100%移植**: 出力が完全に一致することを保証
- **責務分離**: Leader Board取得はUserPromptBuilder内部で実行
- **フォーマッター分離**: 履歴整形・ランキング整形・順位メッセージ生成を独立関数化

#### ファイル構成
```
src/mixseek/prompt_builder/
├── builder.py         # UserPromptBuilderクラス（メインロジック）
├── formatters.py      # 整形関数（format_submission_history, format_ranking_table, generate_position_message）
└── models.py          # Pydantic Models
```

#### RoundControllerの修正
```python
# 修正前
formatted_prompt = await self._format_prompt_for_round(user_prompt, round_number)

# 修正後
from mixseek.prompt_builder import UserPromptBuilder

prompt_builder = UserPromptBuilder(workspace=self.workspace, store=self.store)
formatted_prompt = await prompt_builder.build_team_prompt(
    user_prompt=user_prompt,
    round_number=round_number,
    round_history=self.round_history,
    team_id=self.team_config.team_id,
    team_name=self.team_config.team_name,
    execution_id=self.task.execution_id,
)
```

---

## 5. テスト戦略

### 既存テストとの互換性保証

#### 対象テスト
- `tests/unit/round_controller/test_round_controller.py`
- RoundControllerの既存プロンプト整形テストが100%パスすることを確認

### 新規テストの設計

#### ユニットテスト
1. **test_builder.py**:
   - ラウンド1のプロンプト整形（履歴なし）
   - ラウンド2以降のプロンプト整形（履歴あり）
   - カスタムテンプレート使用時の動作
   - デフォルトテンプレート使用時の動作

2. **test_formatters.py**:
   - `format_submission_history()`: 履歴文字列の整形
   - `format_ranking_table()`: ランキング表の整形
   - `generate_position_message()`: 順位メッセージ生成
   - `get_current_datetime_with_timezone()`: タイムゾーン処理

3. **test_models.py**:
   - PromptBuilderSettings のバリデーション
   - RoundPromptContext のバリデーション

#### 統合テスト
- **test_prompt_builder_integration.py**:
  - RoundControllerとUserPromptBuilderの統合動作
  - Leader Board取得を含むエンドツーエンドテスト
  - 環境変数TZの設定変更による動作確認

---

## 6. 実装優先順位

### Phase 1: コア機能実装
1. **models.py**: Pydantic Models定義
2. **formatters.py**: 整形関数実装
3. **builder.py**: UserPromptBuilderクラス実装

### Phase 2: 統合
4. **RoundController修正**: `_format_prompt_for_round` をUserPromptBuilder呼び出しに置き換え
5. **CLI拡張**: `mixseek config init` コマンド修正

### Phase 3: テスト
6. **ユニットテスト作成**: Phase 1の各モジュールをテスト
7. **統合テスト作成**: Phase 2の統合動作をテスト
8. **既存テスト検証**: RoundControllerの既存テストが100%パスすることを確認

---

## まとめ

すべての技術調査が完了し、以下の決定事項が確定しました：

| 項目 | 採用技術 | 理由 |
|------|----------|------|
| テンプレートエンジン | Jinja2 (>=3.1.0) | Python標準、変数埋め込みと制御構文のサポート |
| タイムゾーン処理 | zoneinfo.ZoneInfo | Python 3.9+標準ライブラリ、Article 9準拠 |
| 設定管理 | Pydantic Settings | 仕様051-configuration準拠、階層的フォールバック |
| テスト戦略 | pytest | 既存プロジェクトのテスト戦略に準拠 |

次のPhase 1（Design & Contracts）で、これらの技術的決定事項に基づいてデータモデルとAPI契約を定義します。
