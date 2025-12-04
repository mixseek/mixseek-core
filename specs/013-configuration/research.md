# Research: Pydantic Settings based Configuration Manager

**Feature**: 051-configuration
**Date**: 2025-11-11
**Status**: Complete

## Overview

本研究では、pydantic-settingsを基盤とした集中型Configuration Managerの実現可能性を評価しました。詳細な技術評価は `assets/pydantic-settings-configuration-manager.md` に記載されています。

## Key Decisions

### Decision 1: アーキテクチャアプローチ

**選択**: Pydantic Settings拡張 + 薄いラッパー層（ハイブリッドアプローチ）

**根拠**:
- pydantic-settingsの標準機能（TOML, ENV, dotenv, secrets）を最大限活用
- カスタムソース（CLISource, TracingSourceWrapper）で不足機能を補完
- ConfigurationManager（薄いラッパー）で統一的なインターフェースを提供

**代替案との比較**:
| アプローチ | 実装コスト | 保守性 | 拡張性 | 型安全性 | トレーサビリティ |
|----------|----------|-------|-------|---------|---------------|
| 完全カスタム実装 | High | Medium | High | Medium | High |
| **Pydantic Settings拡張（採用）** | **Medium** | **High** | **High** | **High** | **Medium** |
| シンプルなPydantic Settings | Low | High | Low | High | Low |

### Decision 2: 優先順位制御

**選択**: `settings_customise_sources()`による優先順位制御

**優先順位**: CLI引数 > 環境変数 > .env > TOML > デフォルト値

**実装方法**:
```python
@classmethod
def settings_customise_sources(cls, ...):
    return (
        CLISource(...),           # 最高優先度
        env_settings,             # 環境変数
        dotenv_settings,          # .envファイル
        TomlConfigSettingsSource(...),  # TOMLファイル
        file_secret_settings,     # 最低優先度
    )
```

### Decision 3: トレーサビリティ実装

**選択**: TracingSourceWrapperパターン

**根拠**:
- 既存ソースをラップし、トレース情報を記録
- SourceTraceデータクラスで値、ソース名、タイムスタンプを保持
- `ConfigurationManager.get_trace_info()`で情報取得

**実装パターン**:
```python
@dataclass
class SourceTrace:
    value: Any
    source_name: str
    source_type: str  # "cli", "env", "toml", "dotenv"
    field_name: str
    timestamp: datetime
```

### Decision 4: 環境別デフォルト戦略

**選択**: field_validatorによる環境別バリデーション

**根拠**:
- 開発環境（dev/staging）: デフォルト値を許可
- 本番環境（prod）: 必須設定の明示的設定を強制

**実装パターン**:
```python
@field_validator("model")
@classmethod
def validate_model(cls, v: str, info) -> str:
    env = info.data.get("environment", "dev")
    if not v and env == "prod":
        raise ValueError("明示的な設定が必要")
    return v or "デフォルト値"  # dev/staging
```

### Decision 5: CLI統合

**選択**: Typer統合（既存CLIフレームワーク）

**根拠**:
- mixseek-coreはtyperを使用（argparseではない）
- CLISourceでtyperの引数を辞書形式で受け取る
- `ConfigurationManager`がCLI引数とENV/TOML/dotenvを統合

**実装パターン**:
```python
@app.command()
def main(
    model: Optional[str] = typer.Option(None, help="LLM model"),
    ...
):
    manager = ConfigurationManager(
        cli_args={"model": model} if model else {}
    )
    settings = manager.load_settings(LeaderAgentSettings)
```

## Technologies Selected

### Core Dependencies

1. **pydantic-settings (>=2.12)**
   - 理由: 設定管理の基盤、型安全性、標準ソース
   - ライセンス: MIT
   - 安定性: Pydantic v2エコシステム

2. **pydantic (>=2.12)**
   - 理由: pydantic-settingsの基盤、バリデーション
   - ライセンス: MIT
   - 安定性: 広く使用されている

3. **tomllib (Python 3.13標準ライブラリ)**
   - 理由: TOMLファイル読み込み（標準ライブラリ）
   - ライセンス: Python Software Foundation License
   - 安定性: Python 3.11+で標準

4. **typer (既存)**
   - 理由: mixseek-coreの既存CLIフレームワーク
   - ライセンス: MIT
   - 安定性: FastAPI作者による、広く使用されている

### Testing Dependencies

1. **pytest (>=8.3.4)** - 既存テストフレームワーク
2. **pytest-mock** - モック機能
3. **pytest-asyncio** - 非同期テスト

## Best Practices

### 1. pydantic-settingsベストプラクティス

**参考**: [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

**推奨事項**:
- `SettingsConfigDict`で設定を集中管理
- `env_prefix`で環境変数の名前空間を分離
- `env_nested_delimiter="__"`でネスト構造をサポート
- `extra="forbid"`で未知の設定項目を拒否
- `validate_default=True`でデフォルト値もバリデーション

### 2. カスタムソース実装ベストプラクティス

**参考**: [Pydantic Settings - Custom Settings Sources](https://docs.pydantic.dev/latest/concepts/pydantic_settings/#custom-settings-sources)

**推奨事項**:
- `PydanticBaseSettingsSource`を継承
- `get_field_value()`で値取得ロジックを実装
- `prepare_field_value()`で値の前処理を実装
- `__call__()`ですべてのフィールドの値を返す

### 3. 型安全性ベストプラクティス

**参考**: Python Type Hints（PEP 484, 585, 604）

**推奨事項**:
- すべての関数・メソッドに型注釈
- `mypy strict mode`でチェック
- Pydantic Modelで複雑な型を定義
- `Any`型を避け、具体的な型を使用

## Integration Patterns

### Pattern 1: ConfigurationManager統合

すべてのモジュールで統一的なConfiguration Managerを使用：

```python
from mixseek.config.manager import ConfigurationManager
from mixseek.config.schema import LeaderAgentSettings

manager = ConfigurationManager(cli_args={...})
settings = manager.load_settings(LeaderAgentSettings)
```

### Pattern 2: TOMLファイル構造

階層的なTOML構造をサポート：

```toml
# team.toml
name = "my-team"

[leader]
model = "openai:gpt-4o"
timeout_seconds = 300

[member]
model = "anthropic:claude-sonnet-4-5"
```

### Pattern 3: 環境変数上書き

ネスト構造を環境変数で上書き：

```bash
export MIXSEEK_LEADER__MODEL="custom:model"
export MIXSEEK_LEADER__TIMEOUT_SECONDS=600
```

## Risks and Mitigation

### Risk 1: pydantic-settings APIの変更

**リスク**: 将来のpydantic-settings更新でカスタムソースAPIが変更される可能性

**軽減策**:
- pydantic-settingsのバージョンを固定（>=2.12, <3.0）
- カスタムソースを薄く保つ（複雑なロジックを避ける）
- 包括的なテストで破壊的変更を検出

### Risk 2: 既存コードの移行コスト

**リスク**: 80箇所のArticle 9違反の修正に時間がかかる

**軽減策**:
- 段階的移行（モジュール単位で順次移行）
- 後方互換性の維持（既存TOMLファイルを引き続き使用可能）
- 移行スクリプトの作成（自動化）

### Risk 3: トレーサビリティのパフォーマンス影響

**リスク**: トレース情報記録がメモリ使用量を増加させる可能性

**軽減策**:
- トレース情報を最小限に抑える（値、ソース、タイムスタンプのみ）
- NFR-002で制約（メモリオーバーヘッド <1MB）
- パフォーマンステストで検証

## Alternatives Considered

### Alternative 1: Dynaconf

**説明**: Python設定管理ライブラリ

**却下理由**:
- pydantic-settingsほど型安全ではない
- Pydanticエコシステムとの統合が弱い
- mixseek-core既存コードとの親和性が低い

### Alternative 2: python-decouple

**説明**: シンプルな環境変数管理ライブラリ

**却下理由**:
- 機能が限定的（型安全性、バリデーション、トレーサビリティ不足）
- TOMLサポートが弱い
- 拡張性が低い

### Alternative 3: 完全カスタム実装

**説明**: pydantic-settingsを使わず、ゼロから実装

**却下理由**:
- 実装コストが高い
- 保守負担が大きい
- 標準技術の恩恵を受けられない

## Unknowns Resolved

すべての「NEEDS CLARIFICATION」項目は、仕様策定時の10回の明確化セッションで解決済みです：

1. ✅ 必須設定のバリデーションタイミング → すべての環境で検知
2. ✅ デフォルト値の環境別扱い → 環境を問わず同一、上書きはENV/CLIで実現
3. ✅ TOMLファイル管理者 → 開発者・運用者・ユーザ
4. ✅ CLI引数解析ライブラリ → typer（既存）
5. ✅ Configuration Managerのデフォルト値参照 → 可能、FR-021/FR-022で実装
6. ✅ CLI設定値参照機能 → mixseek config show/list コマンドで実装
7. ✅ TOMLテンプレート生成機能 → mixseek config init コマンドで実装

## References

1. [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
2. [Pydantic Settings - Custom Settings Sources](https://docs.pydantic.dev/latest/concepts/pydantic_settings/#custom-settings-sources)
3. [Typer Documentation](https://typer.tiangolo.com/)
4. [Python Type Hints (PEP 484)](https://peps.python.org/pep-0484/)
5. [TOML Specification (v1.0.0)](https://toml.io/en/v1.0.0)
6. `assets/pydantic-settings-configuration-manager.md` - 詳細な技術評価

## Conclusion

pydantic-settingsを基盤とした集中型Configuration Managerは、実現可能であり、推奨されるアプローチです。すべての技術的unknownsが解決され、実装の準備が整いました。Phase 1（design & contracts）に進行可能です。
