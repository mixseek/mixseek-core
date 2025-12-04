# bitbank Public API カスタムメンバーエージェント

このディレクトリには、bitbank Public APIと統合した暗号通貨市場分析エージェントが含まれています。

## この例で学べること

- 外部API（bitbank Public API）との統合方法
- Pydantic AIを使ったツール登録とエージェント実装
- 財務指標計算（シャープレシオ、ソルティノレシオ、最大ドローダウンなど）
- 非同期HTTPクライアント実装（リトライロジック、レート制限）
- TOML設定ファイルによる柔軟な設定管理

## ファイル構成

```
examples/custom_agents/bitbank/
├── README.md                  # このファイル
├── bitbank_agent.toml         # エージェント設定ファイル
├── agent.py                   # BitbankAPIAgent実装
├── models.py                  # Pydanticモデル定義
├── client.py                  # 非同期HTTPクライアント
├── tools.py                   # API統合ツール関数
├── config.py                  # TOML設定ローダー
└── __init__.py
```

## ⚠️ セキュリティ警告

**重要**: `path`方式は指定されたファイルからPythonコードを実行します。

- **信頼できるソースからのファイルのみを使用してください**
- 未検証のコードを実行すると、セキュリティ脆弱性のリスクがあります
- **本番環境では`agent_module`方式の使用を強く推奨します**

この例はあくまで開発・学習用です。

## 前提条件

1. Python 3.13.9 以上
2. MixSeek-Coreのインストール (`uv sync`)
3. Google Gemini API key

## セットアップ

### 1. API Keyの設定

```bash
export GOOGLE_API_KEY="your-api-key-here"
```

API keyの取得先: https://aistudio.google.com/apikey

### 2. ワークスペースの設定

MixSeek-Coreはワークスペースディレクトリを必要とします：

```bash
# ローカル環境の場合
export MIXSEEK_WORKSPACE=/path/to/your/workspace

# Docker環境の場合（推奨）
export MIXSEEK_WORKSPACE=/app

# または、カスタムエージェントのディレクトリを直接指定
export MIXSEEK_WORKSPACE=$PWD/examples/custom_agents/bitbank/
```

### 3. ファイルパスの確認

`bitbank_agent.toml` ファイルは `agent.py` への絶対パスを使用しています。このディレクトリを移動した場合は、`[agent.plugin]` セクションの `path` フィールドを更新してください：

```toml
[agent.plugin]
path = "/app/examples/custom_agents/bitbank/agent.py"
agent_class = "BitbankAPIAgent"
```

### 4. 設定ファイルのカスタマイズ（オプション）

`bitbank_agent.toml`で以下のパラメータを調整できます：

```toml
[agent.tool_settings.bitbank_api.financial_metrics]
risk_free_rate = 0.001              # リスクフリーレート（年率0.1%、日本10年国債利回り想定）
trading_days_per_year = 365         # 年間取引日数（暗号通貨は365日取引）
minimum_acceptable_return = 0.0     # 最低許容リターン（ソルティノレシオ計算用）
```

## 使い方

### 基本的な実行

```bash
# リポジトリのルートディレクトリから実行
mixseek member "btc_jpyの2024年のパフォーマンスを日足で分析してください" \
  --config examples/custom_agents/bitbank/bitbank_agent.toml
```

### 時間足の指定

エージェントは以下の時間足をサポートしています：

```bash
# 12時間足
mixseek member "btc_jpyの2024年のパフォーマンスを12時間足で分析してください" \
  --config examples/custom_agents/bitbank/bitbank_agent.toml

# 4時間足
mixseek member "btc_jpyの2024年のパフォーマンスを4時間足で分析してください" \
  --config examples/custom_agents/bitbank/bitbank_agent.toml

# 週足
mixseek member "btc_jpyの2024年のパフォーマンスを週足で分析してください" \
  --config examples/custom_agents/bitbank/bitbank_agent.toml
```

**対応している時間足:**
- `4hour` (4時間足)
- `8hour` (8時間足)
- `12hour` (12時間足)
- `1day` (日足)
- `1week` (週足)
- `1month` (月足)

### 対応通貨ペア

- `btc_jpy` (ビットコイン/日本円)
- `xrp_jpy` (リップル/日本円)
- `eth_jpy` (イーサリアム/日本円)

```bash
# XRPの分析
mixseek member "xrp_jpyの2024年のパフォーマンスを日足で分析してください" \
  --config examples/custom_agents/bitbank/bitbank_agent.toml

# ETHの分析
mixseek member "eth_jpyの2023年のパフォーマンスを月足で分析し、リスクを評価してください" \
  --config examples/custom_agents/bitbank/bitbank_agent.toml
```

### リアルタイムティッカー情報の取得

```bash
mixseek member "btc_jpyの現在の価格を教えてください" \
  --config examples/custom_agents/bitbank/bitbank_agent.toml
```

## 機能詳細

### 1. リアルタイムティッカーデータ取得

現在の買値、売値、直近価格、24時間高値/安値、取引量を取得します。

### 2. ローソク足データ分析

指定した年と時間足でローソク足データ（OHLCV）を取得します。

### 3. 財務指標計算

以下の財務指標を自動計算します：

- **リターン指標**
  - 年率リターン（複利計算）
  - トータルリターン

- **リスク指標**
  - 年率ボラティリティ
  - 最大ドローダウン（Running Maximum法）

- **リスク調整後リターン**
  - シャープレシオ（リスクフリーレート考慮）
  - ソルティノレシオ（下方リスクのみ考慮）

- **リターン分布**
  - 歪度（Skewness）：価格変動の非対称性を示す
  - 尖度（Kurtosis）：極端な価格変動の頻度を示す

- **価格統計**
  - 開始価格・終了価格
  - 平均価格
  - 取引日数
  - 総取引量

## 期待される出力例

```
### BTC_JPY 2024年 日次パフォーマンス分析

#### リターン
*   **年率リターン**: 170.06%
*   **トータルリターン**: 136.15%

#### リスク指標
*   **年率ボラティリティ**: 52.19%
*   **最大ドローダウン**: -30.66%

#### リスク調整後リターン
*   **シャープ・レシオ**: 3.256
*   **ソルティノ・レシオ**: 5.333

#### 分布
*   **スキューネス**: 0.655
*   **尖度**: 2.988

#### 価格統計
*   **始値**: 6,239,295 JPY
*   **終値**: 14,734,359 JPY
*   **平均価格**: 10,033,262 JPY
*   **取引日数**: 366日
*   **総取引量**: 96,180.9185 BTC

**分析概要**:
BTC_JPYは2024年に136.15%という驚異的なトータルリターンを記録...
```

## API制限事項

### データ取得制限

bitbank Public APIは**年単位**でのみローソク足データを提供します：

```
エンドポイント: https://public.bitbank.cc/{pair}/candlestick/{candle_type}/{year}
```

**制限事項:**
- ❌ 特定の月（例：2024年10月）を指定できません
- ❌ 特定の日付範囲を指定できません
- ✅ 年単位のみ取得可能（例：2024年全体）

**例:**
```bash
# ❌ 月指定は対応していません（2024年全体のデータが返されます）
mixseek member "btc_jpyの2024年10月のパフォーマンスを分析してください"

# ✅ これは正しく動作します
mixseek member "btc_jpyの2024年のパフォーマンスを日足で分析してください"
```

### レート制限

クライアントは以下のレート制限対策を実装しています：

- リクエスト間隔: 最低1秒（設定可能）
- リトライ回数: 最大3回（設定可能）
- 指数バックオフ: 429エラー時に自動適用
- タイムアウト: 30秒（設定可能）

## コードの理解

### agent.py - エージェント本体

```python
class BitbankAPIAgent(BaseMemberAgent):
    """bitbank Public API統合カスタムエージェント"""

    def __init__(self, config: MemberAgentConfig) -> None:
        # TOML設定をロード
        self.bitbank_config = load_bitbank_config(config_path)

        # Pydantic AI Agentを初期化
        self.agent: Agent[BitbankAPIConfig, str] = Agent(
            model=self.config.model,
            deps_type=BitbankAPIConfig,
            system_prompt=(...)
        )

        # ツールを登録
        @self.agent.tool
        async def fetch_ticker(ctx: RunContext[BitbankAPIConfig], pair: str) -> str:
            """ティッカーデータ取得ツール"""
            ...
```

**重要なポイント:**
- `BaseMemberAgent`を継承
- `execute()` メソッドで実際の処理を実装
- Pydantic AIでツール（ticker取得、candlestick取得、財務指標分析）を登録
- すべての設定値はTOMLファイルで管理

### models.py - Pydanticモデル

```python
class FinancialSummary(BaseModel):
    """財務指標分析結果（投資家向け）"""
    annualized_return: float = Field(..., description="年率リターン（複利）")
    annualized_volatility: float = Field(..., ge=0, description="年率ボラティリティ")
    max_drawdown: float = Field(..., le=0, description="最大ドローダウン")
    sharpe_ratio: float = Field(..., description="シャープレシオ")
    sortino_ratio: float = Field(..., description="ソルティノレシオ")
    # ... その他の指標
```

**重要なポイント:**
- Pydanticでデータモデルを定義
- バリデーション機能でデータ整合性を保証（例：volatility >= 0）
- 型ヒントで可読性とエディタサポートを向上

### client.py - 非同期HTTPクライアント

```python
class BitbankAPIClient:
    """bitbank Public API用非同期HTTPクライアント"""

    async def _request_with_retry(self, url: str) -> dict[str, Any]:
        """指数バックオフリトライ付きHTTPリクエスト"""
        for attempt in range(self.config.max_retries):
            try:
                await self._enforce_rate_limit()
                async with httpx.AsyncClient(timeout=...) as client:
                    response = await client.get(url)
                    if response.status_code == 429:
                        # Rate limit時のリトライロジック
                        wait_time = self.config.retry_delay_seconds * (2**attempt)
                        await asyncio.sleep(wait_time)
                        continue
                    response.raise_for_status()
                    return cast(dict[str, Any], response.json())
```

**重要なポイント:**
- 非同期I/O（httpx）で効率的なAPI呼び出し
- 指数バックオフリトライで一時的なエラーに対応
- レート制限を自動的に遵守

### tools.py - API統合ツール

```python
def calculate_financial_metrics(
    candlestick_data: BitbankCandlestickData,
    config: BitbankAPIConfig
) -> FinancialSummary:
    """ローソク足データから財務指標を計算"""

    # 終値データを抽出
    closes = np.array([entry.close for entry in candlestick_data.ohlcv])
    daily_returns = np.diff(closes) / closes[:-1]

    # 年率リターン（複利計算）
    daily_mean_return = np.mean(daily_returns)
    annualized_return = (1 + daily_mean_return) ** config.trading_days_per_year - 1

    # シャープレシオ
    annualized_volatility = np.std(daily_returns) * np.sqrt(config.trading_days_per_year)
    sharpe_ratio = (annualized_return - config.risk_free_rate) / annualized_volatility
```

**重要なポイント:**
- NumPyで効率的な統計計算
- 金融工学の標準的な計算手法を実装
- すべての定数（risk_free_rateなど）は設定ファイルから取得

## トラブルシューティング

### "Invalid candle type: 12h"

AIが略語（12h）を使用しています。より明示的な指示を試してください：

```bash
mixseek member "btc_jpyの2024年のパフォーマンスを12時間足（12hour）で分析してください"
```

### "Config file not found"

設定ファイルのパスを環境変数で指定できます：

```bash
export BITBANK_CONFIG_PATH=examples/custom_agents/bitbank/bitbank_agent.toml
mixseek member "..." --config $BITBANK_CONFIG_PATH
```

### "Rate limit exceeded after X retries"

APIレート制限に達しました。`bitbank_agent.toml`で待機時間を調整：

```toml
[agent.tool_settings.bitbank_api]
min_request_interval_seconds = 2  # 1秒から2秒に変更
max_retries = 5                   # リトライ回数を増やす
retry_delay_seconds = 2           # リトライ間隔を延ばす
```

### "Authentication failed"

Google Gemini API keyが設定されているか確認：

```bash
echo $GOOGLE_API_KEY  # 空の場合は未設定
export GOOGLE_API_KEY="your-api-key-here"
```

### "Request timeout after Xs"

タイムアウト時間を延長：

```toml
[agent.tool_settings.bitbank_api]
timeout_seconds = 60  # 30秒から60秒に変更
```

### "Invalid currency pair: xxx"

対応している通貨ペアは `btc_jpy`, `xrp_jpy`, `eth_jpy` のみです。

### "No candlestick data available for {pair}"

指定した年のデータが存在しない可能性があります。より最近の年を試してください：

```bash
# 2024年や2023年など、データが存在する年を指定
mixseek member "btc_jpyの2024年のパフォーマンスを分析してください"
```

## テスト

### 単体テスト

```bash
# モデルテスト
uv run pytest tests/examples/custom_agents/test_bitbank_models.py -v

# クライアントテスト（モック使用）
uv run pytest tests/examples/custom_agents/test_bitbank_client.py -v

# 全テスト実行
uv run pytest tests/examples/custom_agents/ -v
```

### 統合テスト

```bash
# API統合テスト（実際にbitbank APIを呼び出します）
uv run pytest tests/examples/custom_agents/test_bitbank_integration.py -v
```

### E2Eテスト

```bash
# エンドツーエンドテスト（完全なエージェント実行）
uv run pytest tests/examples/custom_agents/test_bitbank_e2e.py -v
```

## オーケストレーションでの使用

このエージェントをチームオーケストレーションで使用するサンプル:
→ [examples/bitbank-orchestrator-sample/](../../bitbank-orchestrator-sample/)

このサンプルでは、bitbank_analyst と web_search エージェントを組み合わせて、市場データと最新ニュースの統合分析を行います。

## 次のステップ

### 開発環境から本番環境への移行

本番環境で使用する場合は、`agent_module`方式に変換してください：

1. エージェントをPythonパッケージとしてパッケージ化
2. インストール: `pip install your-bitbank-agent-package`
3. `bitbank_agent.toml`を更新:

```toml
[agent.plugin]
agent_module = "your_package.agents.bitbank"  # モジュールパス
agent_class = "BitbankAPIAgent"
```

### 機能拡張アイデア

1. **月次・日次フィルタリング**
   - 年間データから特定月を抽出
   - タイムスタンプベースのフィルタリング実装

2. **複数通貨ペア比較**
   - BTC/XRP/ETHのパフォーマンス比較
   - 相関分析

3. **テクニカル指標追加**
   - 移動平均（SMA, EMA）
   - RSI, MACD
   - ボリンジャーバンド

4. **チャート生成**
   - 価格推移グラフ
   - ローソク足チャート
   - ドローダウン可視化

5. **アラート機能**
   - 価格しきい値アラート
   - ボラティリティアラート

## 参考資料

- [Member Agentガイド](../../../docs/member-agents.md)
- [カスタムエージェント開発ガイド](../../../docs/custom-member-agent.md)
- [bitbank Public API仕様](https://github.com/bitbankinc/bitbank-api-docs/blob/master/public-api.md)
- [Pydantic AI公式ドキュメント](https://ai.pydantic.dev/)
- [httpx公式ドキュメント](https://www.python-httpx.org/)
- [NumPy公式ドキュメント](https://numpy.org/doc/)
