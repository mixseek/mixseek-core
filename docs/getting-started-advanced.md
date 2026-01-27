# はじめに（発展編） - 多視点検索とカスタマイズ

このガイドでは、[基本編](./getting-started.md)で学んだシンプルなニュース検索から一歩進んで、より高度な機能を学びます。

## 前提条件

- [はじめに（基本編）](./getting-started.md)を完了していること
- ワークスペースが初期化されていること
- API認証が設定されていること（基本編のGOOGLE_API_KEYに加えて、GROK_API_KEYも必要）

### 追加のAPI認証設定

多視点検索では、SNS特化チームがxAI社のGrokモデルを使用するため、Grok APIキーが必要です。

```bash
# Grok APIキーを設定
export GROK_API_KEY=your-grok-api-key
```

Grok APIキーの取得方法については [xAI Console](https://console.x.ai/) を参照してください。

> **補足**: GOOGLE_API_KEYのみで実行することも可能ですが、SNS特化チームがエラーとなり、汎用調査チームと学術特化チームのみが動作します。

## 多視点検索

より詳細な調査が必要な場合は、3つの異なる視点から調査する `search_news_multi_perspective.toml` を使用します。

```bash
mixseek exec \
  --workspace $HOME/mixseek-workspace \
  --config configs/search_news_multi_perspective.toml \
  "ソフトバンクのニュースを調べてください。"
```

> **注意**: 基本編で方法2（Pythonパッケージ）でインストールした場合は`uv run mixseek exec ...`としてください。

### 多視点検索の特徴

**3つのチームが競争**:

1. **汎用調査チーム** (`team_general_researcher`)
   - バランスの取れた一般的なニュース検索
   - 主要メディアからの情報収集

2. **SNS特化チーム** (`team_sns_researcher`)
   - X（Twitter）、Reddit、SNSでの話題性を重視
   - Grok-4-1-fastモデルを使用してトレンド分析
   - バズっている情報や人々の反応を収集

3. **学術特化チーム** (`team_academic_researcher`)
   - 専門性と信頼性を重視
   - 論文、公式発表、専門家の見解を優先
   - 詳細な背景と因果関係の説明

**評価と判定**:

- 各チームの成果物を4つのメトリクスで評価
- 最高スコアのチームの回答を採用
- 複数ラウンド（最大3ラウンド）で改善を競争

**実行時間**: 約3〜5分（3チーム並行実行）

### search_news.toml との違い

| 項目 | search_news.toml | search_news_multi_perspective.toml |
|------|------------------|-------------------------------------|
| チーム数 | 1チーム | 3チーム（並行実行） |
| 視点 | 汎用的 | 多角的（汎用/SNS/学術） |
| 評価 | デフォルト | カスタム評価設定 |
| 判定 | デフォルト | カスタム判定設定 |
| ラウンド数 | 1〜2ラウンド | 1〜3ラウンド |
| 実行時間 | 〜1分 | 〜5分 |
| 情報の質 | 標準 | 高品質・多角的 |

### 使い分けの目安

**`search_news.toml` を使う場合**:
- 素早く情報を得たい
- 一般的なニュース検索で十分
- コストを抑えたい

**`search_news_multi_perspective.toml` を使う場合**:
- より詳細で多角的な分析が必要
- SNSの反応や専門家の見解も知りたい
- 複数の視点から情報を比較したい
- 品質重視で時間とコストは許容範囲

### カスタム評価設定 - `evaluator_search_news.toml`

多視点検索では、カスタム評価設定を使用して各チームの成果物を評価します。

**4つの評価メトリクス**:

| メトリクス | 重み | 説明 |
|-----------|------|------|
| Coverage | 30% | 情報の網羅性（トピックのカバー範囲） |
| Relevance | 25% | クエリへの関連性（ユーザーの質問に直接回答） |
| Novelty (LLMPlain) | 25% | 新規性・意外性（外れ値や独自情報の評価） |
| ClarityCoherence | 20% | 明瞭性と一貫性（構造と可読性） |

> **補足**: `Coverage`、`Relevance`、`ClarityCoherence` は組み込みメトリクスですが、`Novelty` は `LLMPlain` メトリクスを使用したカスタム評価指標です。`evaluator_search_news.toml` で評価プロンプトをカスタマイズすることで、新規性・意外性に特化した評価を実現しています。

**評価の流れ**:
1. 各チームが成果物を提出
2. 評価システムが4つのメトリクスで各成果物をスコアリング
3. 重み付き合計スコアで最高得点のチームを選出

**参考**: 詳細は [設定リファレンス](./configuration-reference.md) を参照

### カスタム判定設定 - `judgment_search_news.toml`

複数ラウンドの実行時に、ラウンド間の改善を判定します。

**判定基準**:
- 前回ラウンドと今回ラウンドの成果物を比較
- 情報の追加、質の向上、鮮度、整理の改善を評価
- 改善が見られない場合は早期終了（無駄なAPI呼び出しを削減）

**判定の流れ**:
1. ラウンド1終了後、判定エージェントが成果物を評価
2. 改善の余地がある場合はラウンド2へ
3. 改善が見られない、または最大ラウンド到達で終了

**参考**: 詳細は [設定ガイド](./configuration-guide.md) を参照

## カスタマイズ

### 1. 設定のカスタマイズ

生成された設定ファイルを編集して、動作をカスタマイズできます：

```bash
# チーム設定を編集
vim $HOME/mixseek-workspace/configs/agents/team_general_researcher.toml

# 評価メトリクスの重みを調整
vim $HOME/mixseek-workspace/configs/evaluators/evaluator_search_news.toml
```

### 2. 独自のチーム作成

`configs/agents/` に新しいチーム設定を追加できます。

**方法A: config init コマンドを使用（推奨）**

```bash
# テンプレートから新しいチーム設定を生成
mixseek config init \
  --workspace $HOME/mixseek-workspace \
  --component team \
  --output-path configs/agents/team_custom.toml

# 生成されたファイルを編集
vim $HOME/mixseek-workspace/configs/agents/team_custom.toml
```

**方法B: 既存ファイルをコピー**

```bash
# テンプレートをコピー
cp $HOME/mixseek-workspace/configs/agents/team_general_researcher.toml \
   $HOME/mixseek-workspace/configs/agents/team_custom.toml

# 編集して独自のチームを作成
vim $HOME/mixseek-workspace/configs/agents/team_custom.toml
```

同様に、独自のオーケストレーター設定や評価設定も作成できます：

```bash
# オーケストレーター設定を生成
mixseek config init \
  --workspace $HOME/mixseek-workspace \
  --component orchestrator \
  --output-path configs/my_orchestrator.toml

# 評価設定を生成
mixseek config init \
  --workspace $HOME/mixseek-workspace \
  --component evaluator \
  --output-path configs/evaluators/my_evaluator.toml

# 判定設定を生成
mixseek config init \
  --workspace $HOME/mixseek-workspace \
  --component judgment \
  --output-path configs/judgment/my_judgment.toml
```

### 3. Web UIの使用

ブラウザから実行履歴や結果を確認できます：

```bash
mixseek ui --workspace $HOME/mixseek-workspace
```

ブラウザで `http://localhost:8501` を開いてください。

### 4. データベース分析

実行結果はDuckDBに保存されます。

**DuckDB CLIのインストール**:

DuckDBコマンドラインツールをインストールすることで、SQLクエリによるデータ分析が可能になります。

インストール方法については [DuckDB公式ドキュメント](https://duckdb.org/docs/installation/) を参照してください。

**主要なインストール方法**:

```bash
# macOS (Homebrew)
brew install duckdb

# Windows (Chocolatey)
choco install duckdb

# Linux (wget)
wget https://github.com/duckdb/duckdb/releases/latest/download/duckdb_cli-linux-amd64.zip
unzip duckdb_cli-linux-amd64.zip
```

**使用例**:

```bash
# データベースに接続
duckdb $HOME/mixseek-workspace/mixseek.db

# 実行履歴を確認
SELECT execution_id, status, created_at FROM executions ORDER BY created_at DESC LIMIT 10;
```

## 関連ドキュメント

- [はじめに（基本編）](./getting-started.md) - 5分で完了する基本ステップ
- [オーケストレーターガイド](./orchestrator-guide.md) - オーケストレーション設定の詳細
- [チームガイド](./team-guide.md) - チーム設定とカスタマイズ
- [設定リファレンス](./configuration-reference.md) - 全設定項目の詳細
- [設定ガイド](./configuration-guide.md) - 設定ファイルの書き方
- [UIガイド](./ui-guide.md) - Web UIの使い方

---

**Version**: 1.0.0
**Last Updated**: 2025-12-04
