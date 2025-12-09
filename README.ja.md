<p align="center">
  <img src="docs/assets/mixseek700x144_Navy.svg" alt="MixSeek" width="350">
</p>

<p align="center">
  <a href="https://github.com/mixseek/mixseek-core/actions/workflows/ci.yml"><img src="https://github.com/mixseek/mixseek-core/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://mixseek.github.io/mixseek-core/"><img src="https://img.shields.io/badge/docs-GitHub%20Pages-blue" alt="Documentation"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.13+-blue.svg" alt="Python"></a>
</p>

<p align="center">
  <a href="README.md">English</a> | 日本語
</p>

LLMを活用したマルチエージェントオーケストレーションフレームワークです。Leader/Member階層によるタスク委譲、ラウンド制評価、並列チーム実行を提供します。

## 機能

- Leader/Member階層によるマルチエージェントオーケストレーション
- 複数LLMプロバイダー対応（Google、OpenAI、Anthropic、xAI）
- カスタマイズ可能な判定基準によるラウンド制評価
- リーダーボードランキング付き並列チーム実行
- 実行モニタリング用Streamlit Web UI
- ワークスペース管理・エージェント実行用CLIツール

## インストール

### CLIツールとしてインストール（推奨）

`uv`を使ってグローバルにコマンドラインツールとしてインストール：

```bash
# CLIツールとしてインストール（uvが必要）
uv tool install git+https://github.com/mixseek/mixseek-core.git

# またはクローンしたリポジトリからインストール
git clone https://github.com/mixseek/mixseek-core.git
cd mixseek-core
uv tool install .
```

インストール後、`mixseek`コマンドがグローバルに使用可能になります：

```bash
mixseek --version
```

### Pythonパッケージとしてインストール

プログラムから使用するライブラリとしてインストール：

```bash
# pip を使用
pip install git+https://github.com/mixseek/mixseek-core.git

# uv を使用
uv pip install git+https://github.com/mixseek/mixseek-core.git

# プロジェクト依存関係に追加（uv）
uv add git+https://github.com/mixseek/mixseek-core.git
```

開発環境のセットアップは[開発者ガイド](docs/developer-guide.md)を参照してください。

## クイックスタート

### 環境変数の設定

LLMプロバイダーを選択し、対応するAPIキーを設定します：

```bash
# ワークスペースディレクトリ（必須）
export MIXSEEK_WORKSPACE=$HOME/mixseek-workspace

# Google Gemini（サンプル設定のデフォルト）
export GOOGLE_API_KEY=your-api-key

# OpenAI
export OPENAI_API_KEY=your-api-key

# Anthropic
export ANTHROPIC_API_KEY=your-api-key

# xAI (Grok)
export GROK_API_KEY=your-api-key
```

### ワークスペースの初期化

```bash
mixseek init
```

ワークスペースにサンプル設定ファイルが作成されます：
- `configs/search_news.toml` - シンプルなオーケストレーター
- `configs/search_news_multi_perspective.toml` - マルチチームオーケストレーター
- `configs/agents/` - チーム設定

### オーケストレーションの実行

```bash
# オーケストレーター設定で実行
mixseek exec "最新のAIニュースを検索してください" \
  --config $MIXSEEK_WORKSPACE/configs/search_news.toml

# 単一チームで実行
mixseek team "このトピックを分析してください" \
  --config $MIXSEEK_WORKSPACE/configs/agents/team_general_researcher.toml

# Web UIを起動
mixseek ui
```

## 対応LLMプロバイダー

| プロバイダー | モデル形式 | 環境変数 |
|------------|-----------|---------|
| Google Gemini | `google-gla:gemini-2.5-flash` | `GOOGLE_API_KEY` |
| Google Vertex AI | `google-vertex:gemini-2.5-flash` | `GOOGLE_APPLICATION_CREDENTIALS` |
| OpenAI | `openai:gpt-4o` | `OPENAI_API_KEY` |
| Anthropic | `anthropic:claude-sonnet-4-5-20250929` | `ANTHROPIC_API_KEY` |
| xAI | `xai:grok-3` | `GROK_API_KEY` |

## ドキュメント

ドキュメントサイト: https://mixseek.github.io/mixseek-core/

- [はじめに（基本編）](docs/getting-started.md) - 5分で完了するクイックスタート
- [はじめに（発展編）](docs/getting-started-advanced.md) - 多視点検索とカスタマイズ
- [クイックスタートガイド](docs/quickstart.md) - 詳細なセットアップ手順
- [Member Agentガイド](docs/member-agents.md) - エージェントの種類と設定
- [Teamガイド](docs/team-guide.md) - チーム実行と委譲
- [Orchestratorガイド](docs/orchestrator-guide.md) - マルチチーム並列実行
- [設定リファレンス](docs/configuration-reference.md) - 全設定オプション
- [Docker環境セットアップ](docs/docker-setup.md) - コンテナベースの開発

## コントリビューション

コントリビューションを歓迎します。プルリクエストを送信する前に、コントリビューションガイドラインをお読みください。

## ライセンス

Apache License 2.0 - 詳細は[LICENSE](LICENSE)を参照してください。
