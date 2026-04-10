# Broadcast Member Dispatch Mode - 設計仕様書

## 概要

Leader Agentが全メンバーエージェントを強制的に並列実行し、その結果をLeader AgentのLLMで集約する新しいメンバーディスパッチモードを追加する。

### 背景

現行の`selective`モード（Agent Delegationパターン）では、Leader AgentのLLMがタスクを分析し、必要なメンバーエージェントのみをToolとして選択・実行する。これはリソース効率に優れるが、全メンバーの実行が保証されない。

`broadcast`モードは、全メンバーの実行を保証した上で、結果の集約にはLLMの判断力を活用するハイブリッド方式である。

### 設計方針

- 既存の`selective`モード（デフォルト）に一切影響しない後方互換設計
- 実行フローの分岐はRoundController内のプライベートメソッドとして実装（YAGNIに準拠し、新クラスは作らない）
- 既存のデータモデル（`MemberSubmission`, `MemberSubmissionsRecord`）、DB保存、Evaluatorは変更なし

## 設定スキーマ

### フィールド定義

`TeamSettings`（`config/schema.py`）に以下を追加:

```python
member_dispatch: Literal["selective", "broadcast"] = Field(
    default="selective",
    description="メンバーエージェント呼び出し方式。selective: LLMが自律的にAgent選択、broadcast: 全Agentを強制実行後にLLMで集約",
)
```

### TOML設定例

```toml
[team]
team_id = "research-team"
team_name = "Research Team"
member_dispatch = "broadcast"

[team.leader]
model = "google-gla:gemini-2.5-flash"
system_instruction = "全メンバーの結果を統合し、最終回答を作成してください。"

[[team.members]]
agent_name = "web-searcher"
agent_type = "web_search"
tool_description = "Web検索エージェント"
model = "google-gla:gemini-2.5-flash-lite"

[[team.members]]
agent_name = "data-analyst"
agent_type = "code_execution"
tool_description = "データ分析エージェント"
model = "google-gla:gemini-2.5-flash-lite"
```

### 環境変数オーバーライド

既存の`SettingsConfigDict(env_prefix="MIXSEEK_TEAM__")`により自動対応:

```bash
MIXSEEK_TEAM__MEMBER_DISPATCH=broadcast
```

### 変更対象ファイル

| ファイル | 変更内容 |
|---------|---------|
| `src/mixseek/config/schema.py` | `TeamSettings`にフィールド追加 |
| `src/mixseek/agents/leader/config.py` | `TeamConfig`にフィールド追加 + `team_settings_to_team_config`変換 |
| `src/mixseek/config/sources/team_toml_source.py` | TOMLマッピングに追加 |

## 実行フロー

### 全体フロー（RoundController._execute_single_round内）

```
_execute_single_round()
  |
  +-- 1. メンバーエージェント生成（共通・既存コード）
  |
  +-- 2. member_dispatch による分岐
  |     +-- "selective" --> create_leader_agent() --> leader_agent.run()  [既存]
  |     |
  |     +-- "broadcast" --> _execute_broadcast()  [新規]
  |           +-- 2a. asyncio.gather(全メンバー.execute(task))
  |           +-- 2b. 結果をMemberSubmissionリストに変換
  |           +-- 2c. Leader Agent（Tool登録なし）に結果を渡して集約
  |
  +-- 3. MemberSubmissionsRecord保存（共通・既存コード）
  +-- 4. Evaluator実行（共通・既存コード）
  +-- 5. RoundState作成（共通・既存コード）
```

分岐するのはステップ2のみ。ステップ1, 3, 4, 5は既存コードを完全に共有する。

### 2a. 全メンバー並列実行

`asyncio.gather(return_exceptions=True)`により全メンバーを同時実行する。

```python
async def _execute_broadcast(
    self,
    member_agents: dict[str, BaseMemberAgent],
    user_prompt: str,
    deps: TeamDependencies,
) -> str:
    """全メンバーを並列実行し、Leader Agentで集約する"""
    tasks = [
        self._run_single_member(name, agent, user_prompt, deps)
        for name, agent in member_agents.items()
    ]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    aggregated = await self._aggregate_with_leader(user_prompt, deps)
    return aggregated
```

並列実行を選択した理由:
- broadcastの目的は「全員を確実に呼ぶ」ことであり、速度を犠牲にする理由がない
- 既存の`orchestrator.py`でチーム間並列に`asyncio.gather`を使用しているパターンと一致
- `max_concurrent_members`によるメンバー数上限は`TeamConfig`バリデーションで保証済み

### スレッドセーフティ

`asyncio.gather`による並列実行時、複数コルーチンが`deps.submissions`リストに`append`する。asyncioはシングルスレッドイベントループであり、`list.append()`はawaitポイント間でアトミックに実行されるため、ロックなしで安全である。

### 2b. 個別メンバー実行

`_run_single_member`プライベートメソッドで、既存の`tools.py:61-126`のTool関数内ロジック（タイミング計測、usage記録、MemberSubmission作成）を再利用する。

対象エージェント型: `BaseMemberAgent`のみ。`MemberAgentFactory.create_agent()`は常に`BaseMemberAgent`サブクラスを返すため、`tools.py`にあるPydantic AI Agentパス（`ma.run()`）はbroadcastモードでは不要。

- 成功 --> `MemberSubmission(status="SUCCESS")`として`deps.submissions`に追加
- 例外発生 --> `MemberSubmission(status="ERROR", error_message=str(e))`として記録

`asyncio.gather(return_exceptions=True)`により、一部のメンバーが失敗しても他のメンバーの結果は取得される。

### 2c. Leader Agent集約

```python
async def _aggregate_with_leader(self, user_prompt: str, deps: TeamDependencies) -> str:
    """broadcastの結果をLeader Agentで集約する"""
    leader_agent = create_leader_agent(self.team_config, member_agents={})
    
    aggregation_prompt = self._build_aggregation_prompt(
        original_prompt=user_prompt,
        submissions=deps.submissions,
    )
    
    result = await leader_agent.run(aggregation_prompt, deps=deps)
    return result.output
```

集約用Leader Agentの特徴:
- `member_agents={}`（空辞書）でToolが一切登録されない
- LLMは「複数の結果を読んで最終回答を合成する」だけの役割
- `system_instruction`はTOMLの`[team.leader]`設定をそのまま使用

### 集約プロンプトの構造

```
以下は各メンバーエージェントの実行結果です。
これらを統合して、最終的な回答を作成してください。

## 元のタスク
{original_prompt}

## メンバーエージェント結果

### web-searcher (SUCCESS)
{content}

### data-analyst (SUCCESS)
{content}

### code-executor (ERROR)
エラー: Timeout exceeded
```

## データフロー互換性

### MemberSubmission記録（完全互換）

broadcastモードでもMemberSubmissionの構造は同一。既存の`tools.py:113-123`と同じフィールドを記録する。

| フィールド | selective | broadcast |
|-----------|-----------|-----------|
| agent_name | 同一 | 同一 |
| agent_type | 同一 | 同一 |
| content | 同一 | 同一 |
| status | 同一 | 同一 |
| error_message | 同一 | 同一 |
| usage (RunUsage) | 同一 | 同一 |
| execution_time_ms | 同一 | 同一 |
| all_messages | 同一（FR-034維持） | 同一（FR-034維持） |

`MemberSubmissionsRecord`、`AggregationStore`、DuckDBスキーマは変更不要。

### selectiveモードとの出力比較

| 観点 | selective | broadcast |
|------|-----------|-----------|
| `deps.submissions`の件数 | 0~N（LLM判断） | 常にN（全メンバー） |
| 実行順序 | 逐次（LLMのTool呼び出し順） | 並列（同時開始） |
| message_history | Leader + Member混在 | Leader集約分 + 各Memberの履歴（個別） |
| Evaluatorへの入力 | `result.output`（Leader最終出力） | 集約後の`result.output`（同じ型） |

### Leader Agentのmessage_history

broadcastモードでは2段階:
1. 各メンバーの`all_messages` --> `MemberSubmission`ごとに個別保存（FR-034維持）
2. 集約用Leader Agentの`all_messages()` --> `controller.py`の`message_history`として保存

既存の`store.save_aggregation()`は両方を受け取れるため変更不要。

### RoundState・LeaderBoardEntry（変更なし）

`_execute_broadcast`の戻り値は`str`であり、selectiveモードの`result.output`と同じ型。以降のEvaluator、Judgment、DB保存、進捗ファイルはすべて共通パスを通る。

## テスト戦略

### テスト対象

| テスト | 種別 | 内容 |
|--------|------|------|
| 設定読み込み | unit | `member_dispatch`フィールドのパース・バリデーション・デフォルト値 |
| 分岐ロジック | unit | `selective`で既存パス、`broadcast`で新パスの分岐確認 |
| 並列実行 | unit | `asyncio.gather`で全メンバーが呼ばれること、部分エラー時の挙動 |
| 集約プロンプト | unit | `_build_aggregation_prompt`の出力フォーマット |
| 集約実行 | unit | Tool登録なしLeader Agentへの集約プロンプト受け渡し |
| 後方互換性 | unit | `member_dispatch`未指定時にselectiveモードで動作すること |

### テストケース

**1. 正常系: 全メンバー成功**
- 3つのメンバーを登録しbroadcast実行
- `asyncio.gather`で3つとも呼ばれることを確認
- `deps.submissions`が3件であることを確認
- Leader Agent集約が呼ばれることを確認

**2. 部分エラー: 一部メンバー失敗**
- 3つのうち1つが例外を送出
- 成功2件 + ERROR 1件の`MemberSubmission`が記録される
- 集約プロンプトにERRORメンバーの情報が含まれる
- 集約自体は続行される

**3. 全メンバー失敗**
- 全メンバーが例外を送出
- 全件ERROR記録
- 集約Leader Agentにはエラー情報のみが渡される

**4. 後方互換性**
- `member_dispatch`未指定のTOML --> `selective`として動作
- 既存テストが全て通ること（回帰なし）

**5. 設定バリデーション**
- `member_dispatch = "invalid"` --> `ValidationError`
- `member_dispatch = "broadcast"` + `members = []`（メンバー0件）--> 許容する

### テストファイル配置

```
tests/unit/round_controller/test_broadcast.py     # broadcastモード専用テスト
tests/unit/config/test_member_dispatch.py          # 設定バリデーションテスト
```

### モックパターン

既存の`tests/unit/round_controller/test_round_controller_hooks.py`に準拠:

```python
@patch("mixseek.round_controller.controller.create_leader_agent")
# + BaseMemberAgent.execute() を AsyncMock で差し替え
```

## 規模見積もり

| 対象 | 推定行数 |
|------|---------|
| 設定スキーマ（3ファイル） | ~15行 |
| RoundController分岐 + _execute_broadcast | ~80行 |
| _run_single_member | ~40行 |
| _aggregate_with_leader + _build_aggregation_prompt | ~40行 |
| テスト（2ファイル） | ~200行 |
| **合計** | **~375行** |
