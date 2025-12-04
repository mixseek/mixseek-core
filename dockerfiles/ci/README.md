# MixSeek-Core CI Environment

CI専用の最小構成Docker環境です。GitHub Actions CIで使用することを想定しています。

## 目的

- **セキュリティ重視**: 攻撃面を最小化した構成
- **高速ビルド**: 不要なソフトウェアを排除し、ビルド時間を短縮
- **再現性**: バージョン固定により、常に同じ環境を提供
- **軽量**: 必要最小限のパッケージのみインストール

## 開発環境との違い

| 項目 | CI環境 (`ci/`) | 開発環境 (`dev/`) |
|------|---------------|------------------|
| **目的** | GitHub Actions CI | ローカル開発 |
| **Node.js** | ❌ なし | ✅ あり (22.20.0) |
| **AI Tools** | ❌ なし | ✅ あり (claude-code, codex, gemini-cli) |
| **エディタ** | ❌ なし | ✅ あり (vim, nano) |
| **ネットワークツール** | ❌ なし | ✅ あり (ping, netcat) |
| **デバッグポート** | ❌ なし | ✅ あり (5678) |
| **Pythonバージョン** | 3.13.9 (固定) | 3.13系最新 |

## 構成

### ベースイメージ

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
```

Python 3.13系最新パッチバージョンを使用し、再現性と安全性のセキュリティパッチを確保しています。具体的なバージョンは `.python-version` ファイルで固定されます。

### インストールパッケージ

**ビルドツール**:
- git
- build-essential
- cmake
- pkg-config

**Protocol Buffers** (Python依存関係のビルド用):
- libprotobuf-dev
- protobuf-compiler

**ロケール**:
- ja_JP.UTF-8

### Python環境

- **パッケージマネージャー**: uv
- **Python依存関係**: dev, docsグループ
- **仮想環境**: `/venv`

## 使用方法

### ローカルビルド

```bash
cd /path/to/mixseek-core
docker build -f dockerfiles/ci/Dockerfile -t mixseek-core-ci:latest .
```

### CIチェックの実行

#### 統合チェック（推奨）

```bash
# Docker環境で実行（ローカルと同じCI環境）
make -C dockerfiles/ci check

# より詳細なテスト（高速版、E2E除く）
make -C dockerfiles/ci quality-gate-fast
```

**`make -C dockerfiles/ci check`の実行内容**:
1. Ruff linting
2. コードフォーマットチェック
3. mypy型チェック

**`make -C dockerfiles/ci quality-gate-fast`の実行内容**:
1. Ruff linting
2. コードフォーマットチェック
3. pytestテスト実行（E2E除く）

#### 個別チェック

```bash
# Ruff linting
make -C dockerfiles/ci lint

# Ruff format check
make -C dockerfiles/ci format-check

# Mypy type checking
make -C dockerfiles/ci type-check

# Pytest tests（E2Eを除く）
make -C dockerfiles/ci test-fast
```

## セキュリティ

CI環境では以下のセキュリティ対策を実施:

- **非rootユーザー**: すべての処理を非rootユーザーで実行
- **setuidビット除去**: 不要な特権実行可能ファイルを削除
- **最小パッケージ**: 必要最小限のパッケージのみインストール

## トラブルシューティング

### ビルドが遅い

uvのキャッシュマウントを使用:

```bash
docker build \
  --cache-from mixseek-core-ci:latest \
  -f dockerfiles/ci/Dockerfile \
  -t mixseek-core-ci:latest \
  .
```

### テストが失敗する

ローカル環境とCI環境の差異を確認:

```bash
# CI環境で対話的にシェルを開く
docker run --rm -it -v $(pwd):/app -w /app mixseek-core-ci:latest bash

# 環境を確認
python --version
uv --version
```

## 関連ドキュメント

- [開発環境Dockerfile](../dev/README.md) - ローカル開発用
- [GitHub Actions CI](.github/workflows/ci.yml) - CI設定
- [Makefile](../../Makefile) - ビルドとテストコマンド
