# Mixseek UI - Logfire統合実装計画

## 概要

`mixseek ui` コマンドにLogfire観測機能を追加する実装計画。

### 目的
- UIからの実行にもLogfireトレースを適用
- `mixseek team` コマンドと同等の観測機能を提供
- Article 9（Data Accuracy Mandate）準拠の実装

### スコープ
- CLIオプション追加（`--logfire`, `--logfire-metadata`, `--logfire-http`）
- Streamlit app起動時のLogfire初期化
- 環境変数経由の設定受け渡し
- 既存のOrchestrator Logfireトレースの活用

### 除外事項
- Streamlit UI上でのLogfire設定変更（将来的な拡張）
- リアルタイムトレース表示（Logfire Webコンソールで対応）

---

## アーキテクチャ設計

### 現状の課題

```
mixseek ui [--port PORT] [--workspace WORKSPACE]
  ↓
  subprocess.run(["streamlit", "run", "app.py", ...])
    ↓
    app.py: Logfire未初期化
      ↓
      execution_service.py: Orchestrator実行（Logfire無効）
```

**問題点:**
- Streamlitプロセスが独立しているため、CLIフラグを直接渡せない
- 環境変数経由での設定受け渡しが必要

### 提案アーキテクチャ

```
mixseek ui --logfire [--workspace WORKSPACE]
  ↓
  1. LogfireConfig作成（team.pyと同様のロジック）
  ↓
  2. 環境変数に設定を書き込み
     - LOGFIRE_ENABLED=1
     - LOGFIRE_PRIVACY_MODE=full/metadata_only
     - LOGFIRE_CAPTURE_HTTP=1 (--logfire-httpの場合)
  ↓
  3. subprocess.run(["streamlit", "run", "app.py", ...])
    ↓
    app.py: 環境変数からLogfireConfig読み込み → setup_logfire()
      ↓
      execution_service.py: Orchestrator実行（Logfireトレース有効）
```

### 設定の優先順位

`team.py` と同様のロジックを適用：
1. **CLIフラグ** （最高優先度）
2. **環境変数** （`LOGFIRE_ENABLED`, `LOGFIRE_PROJECT`, etc.）
3. **TOML設定** （`$MIXSEEK_WORKSPACE/configs/*.toml`）
4. **デフォルト** （無効）

---

## 実装ステップ（Test-First / Article 3準拠）

### Phase 1: テスト設計（Red Phase）

#### 1.1. ユニットテスト設計
**ファイル:** `tests/cli/commands/test_ui_logfire.py`

テストケース:
- `test_ui_command_with_logfire_flag()`: `--logfire` フラグでLOGFIRE_ENABLED=1が設定される
- `test_ui_command_with_logfire_metadata_flag()`: `--logfire-metadata` でmetadata_onlyモードが設定される
- `test_ui_command_with_logfire_http_flag()`: `--logfire-http` でHTTPキャプチャが有効化される
- `test_ui_command_exclusive_flags()`: 複数のlogfireフラグ指定時にエラー
- `test_ui_command_without_logfire()`: Logfireフラグなしでは環境変数が設定されない

#### 1.2. 統合テスト設計
**ファイル:** `tests/ui/integration/test_logfire_integration.py`

テストケース:
- `test_app_logfire_initialization()`: app.pyでsetup_logfire()が正しく呼ばれる
- `test_orchestrator_logfire_tracing()`: Orchestrator実行時にLogfireトレースが記録される
- `test_logfire_privacy_modes()`: 各プライバシーモードが正しく動作する

#### 1.3. テスト実装（Red Phase）

```python
# tests/cli/commands/test_ui_logfire.py
import os
from unittest.mock import MagicMock, patch

import pytest

from mixseek.cli.commands.ui import ui


def test_ui_command_with_logfire_flag(tmp_path, monkeypatch):
    """--logfire フラグでLOGFIRE_ENABLED=1が設定される"""
    # Setup
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "configs").mkdir()

    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))

    # Mock subprocess.run to prevent actual streamlit launch
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        # Execute (CLIコマンドを直接呼び出し)
        ui(port=None, workspace=str(workspace), logfire=True, logfire_metadata=False, logfire_http=False)

        # Verify: 環境変数が設定されている
        assert os.getenv("LOGFIRE_ENABLED") == "1"
        assert os.getenv("LOGFIRE_PRIVACY_MODE") == "full"
        assert os.getenv("LOGFIRE_CAPTURE_HTTP") is None or os.getenv("LOGFIRE_CAPTURE_HTTP") != "1"


def test_ui_command_exclusive_flags():
    """複数のlogfireフラグ指定時にエラー"""
    with pytest.raises(SystemExit):
        ui(port=None, workspace=None, logfire=True, logfire_metadata=True, logfire_http=False)
```

**期待結果:** テストが失敗（Red Phase確認）

---

### Phase 2: CLIコマンド実装（Green Phase）

#### 2.1. `ui.py` の修正

**ファイル:** `src/mixseek/cli/commands/ui.py`

変更内容:
1. Logfireオプション追加（`--logfire`, `--logfire-metadata`, `--logfire-http`）
2. `team.py` のLogfire初期化ロジックを再利用
3. 環境変数に設定を書き込み
4. subprocess起動前にLogfire設定を完了

```python
# src/mixseek/cli/commands/ui.py
import os
import subprocess
from pathlib import Path

import typer

from mixseek.config import ConfigurationManager, UISettings, OrchestratorSettings
from mixseek.config.logfire import LogfireConfig, LogfirePrivacyMode


def ui(
    port: int | None = typer.Option(None, help="Port to run Streamlit on (overrides config)"),
    workspace: str | None = typer.Option(None, help="Override workspace path"),
    logfire: bool = typer.Option(False, "--logfire", help="Enable Logfire observability (full mode)"),
    logfire_metadata: bool = typer.Option(False, "--logfire-metadata", help="Enable Logfire (metadata only)"),
    logfire_http: bool = typer.Option(False, "--logfire-http", help="Enable Logfire (full + HTTP capture)"),
) -> None:
    """Launch Mixseek UI (Streamlit application).

    Workspace and port are configured via ConfigurationManager with priority:
    CLI args > Environment variables > .env file > TOML config > Defaults
    """
    # 排他的チェック（複数のlogfireフラグは指定できない）
    logfire_flags_count = sum([logfire, logfire_metadata, logfire_http])
    if logfire_flags_count > 1:
        typer.echo(
            "ERROR: Only one of --logfire, --logfire-metadata, or --logfire-http can be specified.",
            err=True,
        )
        raise typer.Exit(1)

    # Resolve workspace and port using ConfigurationManager (Phase 12)
    try:
        workspace_path = None
        if workspace:
            workspace_path = Path(workspace)

        config_manager = ConfigurationManager(workspace=workspace_path)
        ui_settings: UISettings = config_manager.load_settings(UISettings)

        # Use CLI-provided port if given, otherwise use settings (Phase 12)
        final_port = port if port is not None else ui_settings.port

    except Exception as e:
        typer.echo(f"Error: Failed to load configuration: {e}", err=True)
        raise typer.Exit(1)

    # Logfire設定（CLIフラグが指定された場合のみ）
    if logfire or logfire_metadata or logfire_http:
        workspace_resolved = workspace_path or ui_settings.workspace_path

        # 1. 環境変数/TOMLから基本設定を読み取る
        base_config = None
        if os.getenv("LOGFIRE_PROJECT") or os.getenv("LOGFIRE_SEND_TO_LOGFIRE"):
            base_config = LogfireConfig.from_env()
        elif workspace_resolved:
            base_config = LogfireConfig.from_toml(workspace_resolved)

        # 2. CLIフラグでプライバシーモードとHTTPキャプチャを決定
        if logfire:
            privacy_mode = LogfirePrivacyMode.FULL
            capture_http_flag = False
        elif logfire_metadata:
            privacy_mode = LogfirePrivacyMode.METADATA_ONLY
            capture_http_flag = False
        elif logfire_http:
            privacy_mode = LogfirePrivacyMode.FULL
            capture_http_flag = True
        else:
            privacy_mode = LogfirePrivacyMode.DISABLED
            capture_http_flag = False

        # 3. 環境変数に書き込み（Streamlitプロセスに渡すため）
        os.environ["LOGFIRE_ENABLED"] = "1"
        os.environ["LOGFIRE_PRIVACY_MODE"] = privacy_mode.value
        if capture_http_flag:
            os.environ["LOGFIRE_CAPTURE_HTTP"] = "1"

        # project_name/send_to_logfireは既存の環境変数/TOMLから継承
        if base_config and base_config.project_name:
            os.environ["LOGFIRE_PROJECT"] = base_config.project_name
        if base_config is not None:
            os.environ["LOGFIRE_SEND_TO_LOGFIRE"] = "1" if base_config.send_to_logfire else "0"

    app_path = Path(__file__).parent.parent.parent / "ui" / "app.py"

    if not app_path.exists():
        typer.echo(f"Error: Streamlit app not found at {app_path}", err=True)
        raise typer.Exit(1)

    try:
        subprocess.run(
            ["streamlit", "run", str(app_path), "--server.port", str(final_port)],
            check=True,
        )
    except KeyboardInterrupt:
        typer.echo("\nStreamlit server stopped.")
    except subprocess.CalledProcessError as e:
        typer.echo(f"Error: Streamlit failed to start: {e}", err=True)
        raise typer.Exit(1)
    except FileNotFoundError:
        typer.echo("Error: streamlit command not found. Please install streamlit.", err=True)
        raise typer.Exit(1)
```

#### 2.2. `app.py` の修正

**ファイル:** `src/mixseek/ui/app.py`

変更内容:
1. 起動時にLogfire設定を確認
2. 環境変数からLogfireConfigを読み込み
3. `setup_logfire()` を呼び出し

```python
# src/mixseek/ui/app.py
"""Mixseek UI - Streamlit application entrypoint."""

import streamlit as st

from mixseek.ui.utils.workspace import get_workspace_path

# Validate MIXSEEK_WORKSPACE environment variable (Article 9)
try:
    workspace_path = get_workspace_path()
except ValueError as e:
    st.error(str(e))
    st.stop()

# Initialize Logfire if enabled (environment variable check)
import os
if os.getenv("LOGFIRE_ENABLED") == "1":
    try:
        from mixseek.config.logfire import LogfireConfig
        from mixseek.observability import setup_logfire

        logfire_config = LogfireConfig.from_env()
        setup_logfire(logfire_config)

        # サイドバーに観測状態を表示
        st.sidebar.success(f"Logfire enabled ({logfire_config.privacy_mode.value})")
    except ImportError:
        st.sidebar.warning("Logfire not installed (uv sync --extra logfire)")
    except Exception as e:
        st.sidebar.error(f"Logfire initialization failed: {e}")

# Initialize global session state
if "workspace_path" not in st.session_state:
    st.session_state.workspace_path = workspace_path

# Define pages using st.Page()
execution_page = st.Page(
    "pages/1_execution.py",
    title="実行",
    icon=":material/play_arrow:",
    default=True,
)

results_page = st.Page(
    "pages/2_results.py",
    title="結果",
    icon=":material/leaderboard:",
)

history_page = st.Page(
    "pages/3_history.py",
    title="履歴",
    icon=":material/history:",
)

# Create navigation
pg = st.navigation([execution_page, results_page, history_page])

# Display workspace path in sidebar
with st.sidebar:
    st.markdown("### ワークスペース")
    st.code(str(workspace_path), language="text")

# Run the selected page
pg.run()
```

#### 2.3. テスト実行（Green Phase確認）

```bash
# ユニットテスト
pytest tests/cli/commands/test_ui_logfire.py -v

# 統合テスト
pytest tests/ui/integration/test_logfire_integration.py -v
```

**期待結果:** すべてのテストが成功（Green Phase確認）

---

### Phase 3: リファクタリング（Refactor Phase）

#### 3.1. 共通化可能なコードの抽出

`team.py` と `ui.py` のLogfire初期化ロジックが重複している場合、共通関数に抽出。

**候補:**
- `mixseek/cli/utils/logfire_cli.py`: CLIフラグからLogfireConfig作成ロジック

#### 3.2. コード品質チェック

```bash
# Linting
ruff check src/mixseek/cli/commands/ui.py src/mixseek/ui/app.py

# Formatting
ruff format src/mixseek/cli/commands/ui.py src/mixseek/ui/app.py

# Type checking
mypy src/mixseek/cli/commands/ui.py src/mixseek/ui/app.py
```

**期待結果:** エラーゼロ（Article 8準拠）

---

## テスト戦略

### ユニットテスト

| テストケース | 目的 | ファイル |
|-------------|------|---------|
| `test_ui_command_with_logfire_flag` | `--logfire` フラグが環境変数に正しく反映される | `tests/cli/commands/test_ui_logfire.py` |
| `test_ui_command_with_logfire_metadata_flag` | `--logfire-metadata` フラグが正しく動作する | 同上 |
| `test_ui_command_with_logfire_http_flag` | `--logfire-http` フラグが正しく動作する | 同上 |
| `test_ui_command_exclusive_flags` | 複数のlogfireフラグ指定時にエラーが発生する | 同上 |
| `test_ui_command_without_logfire` | Logfireフラグなしでは環境変数が設定されない | 同上 |

### 統合テスト

| テストケース | 目的 | ファイル |
|-------------|------|---------|
| `test_app_logfire_initialization` | `app.py` でLogfireが正しく初期化される | `tests/ui/integration/test_logfire_integration.py` |
| `test_orchestrator_logfire_tracing` | Orchestrator実行時にLogfireトレースが記録される | 同上 |
| `test_logfire_privacy_modes` | 各プライバシーモードが正しく動作する | 同上 |

### E2Eテスト（手動）

```bash
# 1. Full mode
export LOGFIRE_PROJECT=mixseek-test
mixseek ui --logfire

# 2. Metadata only mode
mixseek ui --logfire-metadata

# 3. Full + HTTP capture
mixseek ui --logfire-http

# 4. Logfireなし（通常動作確認）
mixseek ui
```

**確認項目:**
- Logfire Webコンソールでトレースが表示される
- プライバシーモードに応じてプロンプト/応答が除外される
- HTTPキャプチャが有効な場合、HTTPリクエストが記録される

---

## ドキュメント更新

### 更新対象ファイル

1. **`docs/ui-guide.md`**: Logfireオプションの使用方法を追加
2. **`docs/observability.md`**: UIコマンドでのLogfire統合を追記
3. **`CLAUDE.md`**: Mixseek UI実行例にLogfireオプションを追加
4. **`specs/014-ui/spec.md`**: Logfire統合を機能仕様に追記

### 追加内容例（`docs/ui-guide.md`）

```markdown
## Logfire観測機能

Mixseek UIでもLogfireによるリアルタイム観測が利用可能です。

### 使用方法

```bash
# Full mode（すべてキャプチャ）
export LOGFIRE_PROJECT=your-project-name
mixseek ui --logfire

# Metadata only mode（本番推奨）
mixseek ui --logfire-metadata

# Full + HTTP capture
mixseek ui --logfire-http
```

### プライバシーモード

| モード | オプション | 内容 |
|--------|-----------|------|
| Full | `--logfire` | プロンプト、応答、メトリクスをすべて記録 |
| Metadata only | `--logfire-metadata` | メトリクスのみ記録（プロンプト/応答除外） |
| Full + HTTP | `--logfire-http` | Full + HTTPリクエスト/レスポンスをキャプチャ |

詳細は[observability.md](observability.md)を参照してください。
```

---

## Constitution Article準拠チェックリスト

### Article 3: Test-First Imperative
- [x] テスト設計を先行実施（Phase 1）
- [x] Red-Green-Refactorサイクルを明示
- [ ] ユーザー承認（実装前にテスト設計をレビュー）

### Article 4: Documentation Integrity
- [x] 実装計画文書を作成
- [x] ドキュメント更新計画を含む
- [ ] spec.mdとの整合性確認

### Article 8: Code Quality Standards
- [x] Ruff/mypy実行を明記
- [x] リファクタリングフェーズを含む

### Article 9: Data Accuracy Mandate
- [x] 環境変数への明示的書き込み
- [x] デフォルト値の暗黙的使用なし
- [x] エラー時の明示的メッセージ

### Article 10: DRY Principle
- [x] 既存実装（team.py）の調査完了
- [x] リファクタリングによる共通化を検討

### Article 16: Type Safety Mandate
- [x] mypy実行を計画に含む
- [x] 型アノテーション追加を前提とした設計

---

## スケジュールと見積もり

| Phase | タスク | 見積もり時間 | 依存関係 |
|-------|--------|-------------|---------|
| Phase 1 | テスト設計・実装（Red Phase） | 2時間 | なし |
| Phase 2.1 | `ui.py` 実装 | 1.5時間 | Phase 1 |
| Phase 2.2 | `app.py` 実装 | 1時間 | Phase 1 |
| Phase 2.3 | テスト実行（Green Phase） | 0.5時間 | Phase 2.1, 2.2 |
| Phase 3.1 | リファクタリング | 1時間 | Phase 2.3 |
| Phase 3.2 | コード品質チェック | 0.5時間 | Phase 3.1 |
| ドキュメント更新 | 4ファイル更新 | 1時間 | Phase 3.2 |
| E2Eテスト（手動） | 動作確認 | 0.5時間 | Phase 3.2 |

**合計見積もり時間**: 8時間

---

## リスクと対策

| リスク | 影響 | 対策 |
|--------|------|------|
| Streamlit起動前の環境変数設定が反映されない | 高 | subprocess.run()の`env`パラメータを使用 |
| 既存のLogfire設定と競合 | 中 | 優先順位を明確化（CLI > 環境変数 > TOML） |
| Logfire未インストール時のエラー | 低 | graceful degradation（警告のみ表示） |
| テスト環境でのLogfire初期化失敗 | 中 | モック使用、LOGFIRE_SEND_TO_LOGFIRE=0でテスト |

---

## 次のステップ

1. **ユーザー承認**: この計画をレビューし、承認を得る
2. **Phase 1実行**: テスト設計・実装（Red Phase）
3. **Phase 2実行**: 実装（Green Phase）
4. **Phase 3実行**: リファクタリング
5. **ドキュメント更新**: 4ファイルの更新
6. **E2Eテスト**: 手動動作確認
7. **コミット**: 実装完了後にコミット

---

## 参考資料

- `src/mixseek/cli/commands/team.py:90-190` - Logfire初期化の既存実装
- `src/mixseek/observability/logfire.py:15-92` - setup_logfire()実装
- `src/mixseek/config/logfire.py:0-80` - LogfireConfig定義
- `docs/observability.md` - Logfire統合ガイド
- `.specify/memory/constitution.md` - Project Constitution
