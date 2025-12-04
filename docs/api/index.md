# API リファレンス

MixSeek-Core フレームワークの包括的なAPIリファレンスです。

## 概要

MixSeek-Coreは、TUMIXアルゴリズムに基づくマルチエージェントフレームワークです。Leader AgentとMember Agentが協調してタスクを実行し、評価とフィードバックを通じて反復的に改善します。

## API カテゴリ

```{toctree}
:maxdepth: 2

agents/index
framework/index
orchestrator/index
models/index
```

### Agents

エージェント関連のAPIです。

- **[Member Agents](agents/member-agents.md)** - 特定ドメインに特化したエージェント（実装済み）
- **Leader Agents** - タスク調整とMember Agent管理（将来実装予定）

詳細は [Agents API](agents/index.md) を参照してください。

### Framework

フレームワークのコアコンポーネントです。

- **[Orchestrator](orchestrator/index.md)** - 複数チームの並列実行管理（実装済み）
- **[Round Controller](orchestrator/index.md#roundcontroller-api)** - ラウンドライフサイクル管理（実装済み）
- **Evaluator** - Submission評価とフィードバック（既存実装使用）

詳細は [Framework API](framework/index.md) を参照してください。

### Models

データモデルとPydantic定義です。

- **Submission** - チーム出力の構造（将来実装予定）
- **EvaluationResult** - 評価結果の構造（将来実装予定）
- **Configuration Models** - 設定モデル

詳細は [Models API](models/index.md) を参照してください。

## クイックリンク

### 現在利用可能

- [Member Agent API](agents/member-agents.md) - Member Agentの詳細なAPIリファレンス

### ガイドとチュートリアル

- [Member Agent ガイド](../member-agents.md) - Member Agentの使用方法
- [開発者ガイド](../developer-guide.md) - 開発環境のセットアップ
- [Docker セットアップ](../docker-setup.md) - Docker環境での開発

## アーキテクチャ概要

MixSeek-Coreのアーキテクチャは以下の層で構成されます：

1. **Orchestration Layer** - 最上位の管理層
   - 複数チームの並列実行管理
   - システム全体のリソース管理
   - 最終結果の選択

2. **Team Layer** - チーム単位の協調
   - Leader Agent: タスク分解と調整
   - Member Agents: 専門タスクの実行
   - Round Controller: ラウンド管理

3. **Evaluation Layer** - 品質評価
   - Evaluator: Submissionの評価
   - Leader Board: ランキング管理

## 開発ロードマップ

### 実装済み

- ✅ Member Agent (Plain, Web Search, Code Execution)
- ✅ Member Agent設定ローダー
- ✅ Leader Agent
- ✅ Orchestrator
- ✅ Round Controller
- ✅ Evaluator
- ✅ 認証システム
- ✅ ロギングシステム

### 実装予定

- ⏳ 複数ラウンド対応
- ⏳ Leader Board（UI）
- ⏳ Streamlit UI

## 参考資料

- [TUMIX論文](https://arxiv.org/html/2510.01279v1) - MixSeek-Coreの理論的基盤
- [仕様書](https://github.com/your-org/mixseek-core/specs/001-specs/spec.md) - 詳細な機能仕様
- [用語集](https://github.com/your-org/mixseek-core/specs/glossary.md) - MixSeek-Core用語集
