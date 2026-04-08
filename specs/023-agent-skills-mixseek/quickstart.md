# Quickstart: MixSeek Agent Skills

**Feature**: 023-agent-skills-mixseek
**Date**: 2026-01-21

## 概要

MixSeek Agent Skillsは、AIコーディングエージェント（Claude Code、Codex、Gemini CLI等）がMixSeek-Coreのワークスペースを自然言語で管理できるようにするスキルセットです。

## 前提条件

### 必須

- AIコーディングエージェント（Claude Code、Codex、Gemini CLI等）
- MixSeek-Coreがインストールされた環境（TOML検証用）

### 推奨

- skills-ref CLIツール（スキル検証用）

```bash
# skills-ref のインストール
pip install skills-ref
# または
uv add skills-ref
```

## インストール

### Claude Code

```bash
# プラグインとして登録（マーケットプレイス経由）
/plugin marketplace add mixseek/skills

# または直接インストール
/plugin install mixseek-skills@mixseek
```

### 手動インストール

`.skills/`ディレクトリをプロジェクトルートに配置します:

```bash
# リポジトリから.skills/ディレクトリをコピー
cp -r <mixseek-core-repo>/.skills/ ./.skills/
```

## 利用可能なスキル

| スキル名 | 説明 | トリガーワード例 |
|---------|------|------------------|
| `mixseek-workspace-init` | ワークスペース初期化 | 「ワークスペースを初期化」「mixseekのセットアップ」 |
| `mixseek-team-config` | チーム設定生成 | 「チームを作成」「エージェント設定を生成」 |
| `mixseek-orchestrator-config` | オーケストレーター設定 | 「オーケストレーターを設定」「チーム競合設定」 |
| `mixseek-evaluator-config` | 評価設定生成 | 「評価設定を作成」「スコアリング設定」 |
| `mixseek-config-validate` | 設定検証 | 「設定を検証」「TOMLをチェック」 |
| `mixseek-model-list` | モデル一覧取得 | 「使えるモデル」「モデル一覧」 |

## 基本的な使い方

### 1. ワークスペースの初期化

```
User: MixSeekのワークスペースを初期化して

Agent: [mixseek-workspace-init スキルを使用]
       ワークスペースパスを確認させてください。
       現在のディレクトリ（/path/to/project）で良いですか？

User: はい

Agent: 以下のディレクトリ構造を作成しました:
       configs/agents/
       configs/evaluators/
       configs/judgment/
       logs/
       templates/

       環境変数の設定を推奨します:
       export MIXSEEK_WORKSPACE=/path/to/project
```

### 2. チーム設定の生成

```
User: Web検索と分析ができるチームを作って

Agent: [mixseek-team-config スキルを使用]
       チーム設定を生成します。以下の構成でよろしいですか？

       - Leader Agent: gemini-2.5-pro
       - Member Agents:
         - web_researcher (web_search): Web検索担当
         - analyst (plain): 分析担当

       モデルはデフォルト（Google Gemini）を使用しますか？

User: はい、それでOK

Agent: configs/agents/team-web-research.toml を生成しました。
       実行コマンド: mixseek team "質問" --config configs/agents/team-web-research.toml
```

### 3. 設定の検証

```
User: team.tomlを検証して

Agent: [mixseek-config-validate スキルを使用]
       configs/agents/team-web-research.toml を検証します...

       ✅ TOML構文: OK
       ✅ 必須フィールド: OK
       ✅ モデル形式: OK
       ✅ Member Agent数: OK (2/15)

       検証成功: この設定ファイルは有効です。
```

## 環境変数

| 変数名 | 説明 | 例 |
|--------|------|-----|
| `MIXSEEK_WORKSPACE` | ワークスペースパス | `/path/to/workspace` |
| `GOOGLE_API_KEY` | Google AI API キー | `AIza...` |
| `ANTHROPIC_API_KEY` | Anthropic API キー | `sk-ant-...` |
| `OPENAI_API_KEY` | OpenAI API キー | `sk-...` |

## スキル検証

作成したスキルの検証:

```bash
# 単一スキル検証
agentskills validate .skills/mixseek-workspace-init

# 全スキル検証
for skill in .skills/mixseek-*; do
    echo "Validating $skill..."
    agentskills validate "$skill"
done
```

## トラブルシューティング

### スキルが認識されない

1. `.skills/`ディレクトリがプロジェクトルートにあることを確認
2. SKILL.mdファイルの存在を確認
3. フロントマターの`name`フィールドがディレクトリ名と一致していることを確認

### TOML生成エラー

1. 環境変数`MIXSEEK_WORKSPACE`が設定されていることを確認
2. 書き込み権限があることを確認
3. `mixseek-config-validate`スキルで検証を実行

### モデル一覧が取得できない

1. 対応するAPIキー環境変数が設定されていることを確認
2. ネットワーク接続を確認
3. オフライン時は`docs/data/valid-models.csv`を参照

## 次のステップ

1. **チーム実行**: `mixseek team "質問" --config team.toml`
2. **オーケストレーター実行**: `mixseek exec --config orchestrator.toml`
3. **UI起動**: `mixseek ui`

詳細なドキュメントは以下を参照:

- [MixSeek-Core ドキュメント](https://mixseek.github.io/mixseek-core/)
- [Agent Skills 仕様](https://agentskills.io/specification)
