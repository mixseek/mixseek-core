# MixSeek Agent Skills

MixSeek-Core用のAgent Skillsコレクションです。AIコーディングエージェント（Claude Code、Codex、Gemini CLI等）がMixSeekのワークスペースを自然言語で管理できるようにします。

## スキル一覧

| スキル名 | 説明 | トリガーワード例 |
|---------|------|------------------|
| `mixseek-workspace-init` | ワークスペース初期化 | 「ワークスペースを初期化」「mixseekのセットアップ」 |
| `mixseek-team-config` | チーム設定生成 | 「チームを作成」「エージェント設定を生成」 |
| `mixseek-orchestrator-config` | オーケストレーター設定 | 「オーケストレーターを設定」「チーム競合設定」 |
| `mixseek-evaluator-config` | 評価設定生成 | 「評価設定を作成」「スコアリング設定」 |
| `mixseek-config-validate` | 設定検証 | 「設定を検証」「TOMLをチェック」 |
| `mixseek-model-list` | モデル一覧取得 | 「使えるモデル」「モデル一覧」 |
| `detect-python-command` | Pythonコマンド判別・実行 | 「Pythonコマンドを確認」「どのpythonを使う」 |

## 使い方

### 1. ワークスペースの初期化

```
User: MixSeekのワークスペースを初期化して

Agent: ワークスペースパスを確認します。
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

Agent: チーム設定を生成します。以下の構成でよろしいですか？

       - Leader Agent: gemini-2.5-pro
       - Member Agents:
         - web_researcher (web_search): Web検索担当
         - analyst (plain): 分析担当

User: はい

Agent: configs/agents/team-web-research.toml を生成しました。
       実行コマンド: mixseek team "質問" --config configs/agents/team-web-research.toml
```

### 3. 設定の検証

```
User: team.tomlを検証して

Agent: configs/agents/team-web-research.toml を検証します...

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

```bash
# skills-ref CLIのインストール
pip install skills-ref

# 単一スキル検証
agentskills validate .skills/mixseek-workspace-init

# 全スキル検証
for skill in .skills/mixseek-*; do
    agentskills validate "$skill"
done
```

## ディレクトリ構造

```
.skills/
├── README.md                      # このファイル
├── detect-python-command/         # Pythonコマンド判別・実行
│   ├── SKILL.md
│   └── scripts/
│       ├── detect-python.sh       # コマンド判別（情報提供用）
│       └── run-python.sh          # スクリプト実行（推奨）
├── mixseek-workspace-init/        # ワークスペース初期化
│   ├── SKILL.md
│   └── scripts/
│       └── init-workspace.sh
├── mixseek-team-config/           # チーム設定生成
│   ├── SKILL.md
│   └── references/
│       ├── TOML-SCHEMA.md
│       └── MEMBER-TYPES.md
├── mixseek-orchestrator-config/   # オーケストレーター設定
│   ├── SKILL.md
│   └── references/
│       └── TOML-SCHEMA.md
├── mixseek-evaluator-config/      # 評価設定生成
│   ├── SKILL.md
│   └── references/
│       ├── TOML-SCHEMA.md
│       └── METRICS.md
├── mixseek-config-validate/       # 設定検証
│   ├── SKILL.md
│   └── scripts/
│       └── validate-config.py
└── mixseek-model-list/            # モデル一覧
    ├── SKILL.md
    └── references/
        └── VALID-MODELS.md
```

## 仕様

これらのスキルは [Agent Skills仕様](https://agentskills.io/specification) に準拠しています。

## 関連ドキュメント

- [MixSeek-Core ドキュメント](https://mixseek.github.io/mixseek-core/)
- [クイックスタートガイド](../specs/023-agent-skills-mixseek/quickstart.md)
