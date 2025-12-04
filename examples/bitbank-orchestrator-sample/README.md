# Bitbank Orchestrator Sample

bitbankカスタムエージェントをオーケストレーションで使用するサンプル。

## 前提条件

- [bitbankカスタムエージェント](../custom_agents/bitbank/)のセットアップ完了
- `GOOGLE_API_KEY` 環境変数

## クイックスタート

1. ワークスペースにコピー:
   ```bash
   mkdir -p workspaces && cp -r examples/bitbank-orchestrator-sample workspaces/
   ```

2. 環境変数設定:
   ```bash
   export MIXSEEK_WORKSPACE=$PWD/workspaces/bitbank-orchestrator-sample
   export GOOGLE_API_KEY="your-key"
   ```

3. 実行:
   ```bash
   mixseek exec "BTCの最新価格を分析" --config configs/orchestrator.toml
   ```

## チーム構成

| Agent | Type | 役割 |
|-------|------|------|
| bitbank_analyst | custom | 暗号通貨市場データ取得・分析 |
| web_search | web_search | 最新ニュース検索 |

## カスタマイズ

### plugin path の調整（ローカル環境の場合）

デフォルトはDocker環境向けです。ローカル環境で実行する場合は `configs/agents/team-bitbank-analysis.toml` を編集:

```toml
# 変更前（Docker環境）
plugin = { path = "/app/examples/custom_agents/bitbank/agent.py", ... }

# 変更後（ローカル環境）
plugin = { path = "examples/custom_agents/bitbank/agent.py", ... }
```

## 関連ドキュメント

- [bitbank Agent実装詳細](../custom_agents/bitbank/)
- [Orchestrator使用法](../orchestrator-sample/)
