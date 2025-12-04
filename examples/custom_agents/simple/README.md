# シンプルなカスタムメンバーエージェントの例

このディレクトリには、MixSeek-Core用の最もシンプルなカスタムメンバーエージェント実装が含まれています。

## この例で学べること

- カスタムエージェントの最小限の実装要件
- `BaseMemberAgent`の継承方法
- `execute()` メソッドの実装方法
- TOMLを使ったカスタムエージェントの設定方法
- `path`方式での動的ロード方法（開発・テスト用）

## ファイル構成

- `simple_agent.py` - カスタムエージェントのPython実装
- `simple_agent.toml` - TOML設定ファイル
- `README.md` - このファイル

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
export MIXSEEK_WORKSPACE=/app/path/to/your/workspace

# または、カスタムエージェントのディレクトリを直接指定
export MIXSEEK_WORKSPACE=$PWD/examples/custom_agents/simple/
```

### 3. ファイルパスの確認

`simple_agent.toml` ファイルは `simple_agent.py` への絶対パスを使用しています。このディレクトリを移動した場合は、`[agent.plugin]` セクションの `path` フィールドを更新してください：

```toml
[agent.plugin]
path = "/absolute/path/to/simple_agent.py"
agent_class = "SimpleCustomAgent"
```

## 使い方

### 基本的な実行

```bash
# リポジトリのルートディレクトリから実行
mixseek member "Hello, custom agent!" \
  --config examples/custom_agents/simple/simple_agent.toml
```

### 詳細出力付き実行

```bash
mixseek member "Test question" \
  --config examples/custom_agents/simple/simple_agent.toml \
  --verbose
```

### JSON形式での出力

```bash
mixseek member "Test question" \
  --config examples/custom_agents/simple/simple_agent.toml \
  --format json
```

### タイムアウトのカスタマイズ

```bash
mixseek member "Complex question" \
  --config examples/custom_agents/simple/simple_agent.toml \
  --timeout 60
```

## 期待される出力

エージェントは入力をエコーバックし、プレフィックスを付けます：

```
[SimpleCustomAgent] Received task: Hello, custom agent!
```

## コードの理解

### simple_agent.py

```python
class SimpleCustomAgent(BaseMemberAgent):
    """BaseMemberAgentを継承します。"""

    async def execute(self, task: str, context: dict[str, Any] | None = None, **kwargs: Any) -> MemberAgentResult:
        """必須メソッド - タスクを処理して結果を返します。"""
        response = f"[SimpleCustomAgent] Received task: {task}"

        return MemberAgentResult.success(
            content=response,
            agent_name=self.agent_name,
            agent_type=self.agent_type,
        )
```

**重要なポイント:**
- `BaseMemberAgent`を継承する必要があります
- `async def execute()`を実装する必要があります
- `MemberAgentResult`を返す必要があります
- 成功時は`MemberAgentResult.success()`を使用します
- エラー時は`MemberAgentResult.error()`を使用します

### simple_agent.toml

```toml
[agent]
type = "custom"  # すべてのカスタムエージェントで必ず "custom" を指定

[agent.plugin]
path = "/absolute/path/to/simple_agent.py"  # Pythonファイルへのパス
agent_class = "SimpleCustomAgent"  # インスタンス化するクラス名
```

**重要なポイント:**
- `type`は必ず`"custom"`を指定します（カスタム識別子は使用不可）
- エージェントの一意識別には`agent.name`を使用します
- `path`方式は開発・テスト用です
- 本番環境では`agent_module`方式を使用してください

## 次のステップ

### 開発環境から本番環境への移行

本番環境で使用する場合は、`agent_module`方式に変換してください：

1. エージェントをPythonパッケージとしてパッケージ化
2. インストール: `pip install your-package`
3. `simple_agent.toml`を更新:

```toml
[agent.plugin]
agent_module = "your_package.agents.simple"  # モジュールパス
agent_class = "SimpleCustomAgent"
```

### 機能の追加

実際の処理ロジックでエージェントを拡張：

```python
async def execute(self, task: str, context: dict[str, Any] | None = None, **kwargs: Any) -> MemberAgentResult:
    # Pydantic AI agentを使用して実際の処理を実行
    result = await self._agent.run(task)

    return MemberAgentResult.success(
        content=result.data,
        agent_name=self.agent_name,
        agent_type=self.agent_type,
    )
```

### エラーハンドリング

適切なエラーハンドリングを追加：

```python
try:
    result = await self._agent.run(task)
    return MemberAgentResult.success(...)
except Exception as e:
    return MemberAgentResult.error(
        error_message=str(e),
        agent_name=self.agent_name,
        agent_type=self.agent_type,
    )
```

## トラブルシューティング

### "Error: Custom agent must have plugin configuration"

- TOMLで`type = "custom"`が指定されているか確認
- `[agent.plugin]`セクションが存在するか確認
- `path`または`agent_module`が指定されているか確認

### "FileNotFoundError: File not found"

- `simple_agent.toml`内の`path`が正しいか確認
- 相対パスではなく絶対パスを使用
- ファイルのパーミッションを確認

### "AttributeError: Custom agent class 'SimpleCustomAgent' not found"

- `agent_class`がPythonファイル内のクラス名と一致しているか確認
- クラス名のタイプミスをチェック

### "Authentication failed"

- `GOOGLE_API_KEY`が正しく設定されているか確認
- API keyが有効か確認: https://aistudio.google.com/apikey

### "Workspace configuration error"

- `MIXSEEK_WORKSPACE`環境変数が設定されているか確認
- ワークスペースディレクトリが存在するか確認
- ディレクトリのパーミッションを確認

## 参考資料

- [Member Agentガイド](../../../docs/member-agents.md)
- [カスタムエージェント開発ガイド](../../../docs/member-agents.md#カスタムエージェント開発ガイド)
- [クイックスタートガイド](../../../specs/009-member/quickstart.md)
- [仕様書](../../../specs/114-custom-member/spec.md)
