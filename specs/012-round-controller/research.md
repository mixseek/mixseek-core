# Research: Round Controller - ラウンドライフサイクル管理

**日付**: 2025-11-10
**ステータス**: 完了

## Phase 0: Outline & Research

本研究フェーズでは、既存の`025-mixseek-core-orchestration`実装を調査し、`012-round-controller`仕様に従って置き換えるための技術的知見を収集しました。

---

## 調査項目

### 1. LLM改善見込み判定実装パターン

既存のEvaluator実装（`src/mixseek/evaluator`）を調査し、LLM-as-a-Judge手法の実装パターンを理解しました。

#### 決定事項

**採用パターン: Evaluatorの直接応用**

RoundControllerで実装する改善見込み判定（should_continue、reasoning、confidence_score）は、Evaluatorの`evaluate_with_llm()`と同じパターンで実装します。

##### 新規コンポーネント

1. **`ImprovementJudgment`モデル** (`round_controller/models.py`)
   ```python
   class ImprovementJudgment(BaseModel):
       should_continue: bool = Field(description="次ラウンドに進むべきか")
       reasoning: str = Field(description="判定理由の詳細説明")
       confidence_score: float = Field(ge=0.0, le=1.0, description="信頼度スコア")
   ```

2. **改善見込み判定クライアント** (`round_controller/judgment_client.py`)
   - Evaluatorの`evaluate_with_llm()`と同じパターンで実装
   - `ToolDefinition`で`ImprovementJudgment`スキーマを指定
   - 同じリトライロジック（3回、エクスポネンシャルバックオフ）を適用

3. **ラウンド継続判定ロジック** (`round_controller/controller.py`)
   ```python
   async def _should_continue_round(...):
       # (a) 最小ラウンド数確認
       if current_round < min_rounds:
           return True, judgment
       # (b) LLM判定
       judgment = await judge_improvement_prospects(...)
       # (c) 最大ラウンド数確認
       if current_round >= max_rounds:
           judgment.should_continue = False
       return judgment.should_continue, judgment
   ```

#### 根拠

Evaluator実装から学んだベストプラクティス：

| 項目 | 評価 | 理由 |
|------|------|------|
| **プロダクション検証** | ✅ | Evaluatorは本番稼働中、422行のコード規模 |
| **型安全性** | ✅ | Pydantic Field制約で自動検証 |
| **エラー処理** | ✅ | 多段階エラー検出、カスタム例外 |
| **テスト容易** | ✅ | 責務分離、DI対応 |
| **既存資産活用** | ✅ | pydantic-ai統合、プロバイダー抽象化 |

##### Pydantic AI Direct Model Request APIの使用方法

1. **ModelRequestの構築**: システムプロンプト（instruction）とユーザープロンプト（parts）を組み合わせ
2. **ToolDefinitionで構造化出力指定**: PydanticモデルのJSONスキーマを使用し、LLMに構造化出力を強制
3. **ModelSettingsで温度・トークン制御**: temperature=0.0（決定的）、max_tokens制限を設定
4. **model_request_sync呼び出し**: プロバイダー抽象化されたAPI呼び出し

##### プロンプト構造の3層構成

- **システムプロンプト**: 役割定義、判定基準、スコアリングガイド、段階的指示
- **ユーザープロンプト**: 現在のラウンド、過去のSubmission履歴、評価スコアを明示的に区分して提示
- **デフォルト実装**: `_get_user_prompt()` で拡張可能な設計

##### Pydantic検証による信頼性

- **Field制約**: `ge=0.0, le=1.0` でスコア範囲を自動検証
- **field_validator**: 出力の正規化
- **model_validate()**: JSON→Pythonオブジェクト変換時に一括検証

#### 検討した代替案

| 代替案 | 採用判定 | 理由 |
|--------|---------|------|
| langchain統合 | ❌ 非採用 | 既存のpydantic-ai依存と競合、過度な複雑性 |
| 汎用LLMPlainメトリクス流用 | ❌ 非採用 | 出力形式（スコア0-100 vs bool判定）の不整合 |
| 手動テキストパース | ❌ 非採用 | 信頼性低い、Fragile |
| Raw Anthropic SDK | ❌ 非採用 | 既存パターンと不統一、プロバイダー非抽象化 |

---

### 2. DuckDB並列書き込み戦略

DuckDB 1.0以降のMVCC（Multi-Version Concurrency Control）による並列書き込みのベストプラクティスを調査しました。

#### 決定事項

Round Controllerの`round_status`および`leader_board`テーブルには、以下の戦略を採用します：

1. **スレッドローカルコネクション管理**
   - 各スレッドが独立したDuckDBコネクション保持
   - MVCCにより各スレッドが独立したスナップショット操作

2. **asyncio.to_threadによるブロッキングAPI対応**
   - DuckDB同期APIをスレッドプール実行
   - 真の非同期並列実行を実現

3. **明示的トランザクション管理**
   - BEGIN/COMMIT/ROLLBACKによる一貫性保証
   - コンテキストマネージャで自動ロールバック

4. **エクスポネンシャルバックオフリトライ**
   - 1秒 → 2秒 → 4秒のリトライ間隔
   - ValidationErrorは即座に再発生（リトライ対象外）

5. **ON CONFLICTによる重複対応**
   - UNIQUE制約で重複検出
   - 重複時は最新データで上書き（UPSERT）

6. **複合INDEX設計**
   - `(execution_id, team_id, round_number)` コンポジットINDEX
   - スコア順ランキングINDEX
   - 実行識別INDEX

#### 根拠

DuckDB MVCCの特性とベストプラクティス：

- **技術**: DuckDB MVCCはロック競合なし、Snapshot Isolationで一貫性保証
- **実績**: 既存実装AggregationStoreで検証済み（10チーム並列1.5秒）
- **DRY**: 既存パターンの踏襲（Article 10準拠）
- **パフォーマンス**: SC-001～SC-003達成可能

##### 既存実装の分析（`aggregation_store.py`）

- **スレッドローカルコネクション管理**: 各スレッドが独立したコネクションを保持
- **トランザクション管理パターン**: BEGIN/COMMIT/ROLLBACKによる一貫性保証
- **asyncio.to_threadによるブロッキングAPI対応**: 同期APIを非同期実行
- **実測パフォーマンス**: 10チーム並列で1.5秒

##### DuckDB MVCC の基本特性

- **MVCC**: Multi-Version Concurrency Control
- **Snapshot Isolation**: 各トランザクションが独立したスナップショットで動作
- **ロック競合なし**: 読み取りと書き込みが互いにブロックしない

##### `round_status`テーブル用戦略

- テーブルスキーマとUNIQUE制約
- 複数チーム・複数ラウンド並列実行シナリオ
- タイムアウト/リトライ時の重複書き込み対応
- ON CONFLICTによるUPSERT処理

##### `leader_board`テーブル用戦略

- INDEX設計による読み取り最適化
- 複数チーム同時評価結果保存
- 既存実装で実現済みの機能の再利用

#### 検討した代替案

| 代替案 | 採用判定 | 理由 |
|--------|---------|------|
| PostgreSQL + コネクションプール | ❌ 非採用 | セットアップ複雑、外部サーバー依存 |
| BEGIN EXCLUSIVEロック | ❌ 非採用 | MVCC利点喪失、並列性低下 |
| Celeryタスクキュー | ❌ 非採用 | 外部依存、遅延増加 |

---

### 3. プロンプト整形戦略

各ラウンドでチームに送信するプロンプトの整形戦略を調査しました。

#### 決定事項

##### 採用するプロンプト整形手法

**短期実装（本機能037）**
- **形式**: Python f-string + `textwrap.dedent()` による構造化テンプレート
- **方式**: 既存のLeader Agent統合を維持し、Round Controller内で段階的なコンテキスト情報を集約
- **プロンプト送信**: Leader Agentの`run(user_prompt)`へ単一文字列として入力（既存インターフェース不変）

**長期化対象（将来のPrompt Builderコンポーネント化）**
- **プロトコルベース設計**: `PromptBuilder`インターフェースにより、テンプレートエンジン切り替えを容易化
- **段階的移行**: Jinja2ベースの実装へ段階的に置き換え可能
- **ユーザカスタマイズ対応**: テンプレートファイルの外部化を想定

##### コンテキスト情報の統合方法

```
ラウンド1（初回）: ユーザクエリのみ
ラウンド2以上: 以下の情報を段階的に統合
  ├─ ユーザクエリ
  ├─ 過去のSubmission履歴（最新N件に制限）
  ├─ 対応する評価フィードバック
  ├─ leader_boardから取得した全チーム最高スコアランキング
  └─ 当該チームの現在順位
```

##### トークン制限対策

- **固定トークン予算制**: `RoundPromptConfig`で設定可能な上限値
- **情報優先度の階別化**: コア情報（スコア、順位）→ 詳細フィードバック → 全履歴
- **Submission要約**: 最初200文字 + 末尾100文字による圧縮

#### 根拠

既存実装とベストプラクティス：

**1. Leader Agentパターン準拠** (`src/mixseek/agents/leader/`)
- 既存の`system_instruction` + `system_prompt`の設計と統一
- `agent.run(user_prompt)`インターフェースを変更しない

**2. EvaluatorのLLM-as-a-Judgeパターン継承** (`src/mixseek/evaluator/`)
- `evaluate_with_llm()`の実装パターンを参考（instruction + user_promptの分離）
- `textwrap.dedent()`を用いたテンプレート整形の統一

**3. 憲章Article 9 (Data Accuracy Mandate)準拠**
- 環境変数・DuckDBから明示的にコンテキスト情報を取得
- ハードコードされた値は`RoundPromptConfig`で名前付き定数として管理

#### 検討した代替案

| 代替案 | 採用判定 | 理由 |
|--------|---------|------|
| Jinja2テンプレートエンジン | 🔄 長期予定 | 複雑なプロンプト制御に適していますが、本機能の実装時間短縮のため短期はf-stringで対応 |
| 構造化データ（JSON）入力 | ❌ 非採用 | LLMへの自然言語プロンプティング活動を制限するため不適切 |
| 複数メッセージ履歴（Message History） | 🔄 将来検討 | 改善見込み判定（LLM-as-a-Judge）で活用予定 |
| メモリキャッシュ / Redis | ❌ 非採用 | 複数チーム並列実行時のデータ整合性が保証できない |

#### 将来的な外部化の考慮点

##### 段階的移行戦略

```
Phase 1（現在）:
  └─ PlainTextPromptBuilder（f-string実装）
     Round Controllerに統合

Phase 2（仕様040計画）:
  ├─ PromptBuilderプロトコル抽出
  ├─ Jinja2PromptBuilder実装
  └─ テンプレートファイル管理

Phase 3（カスタマイズ対応）:
  ├─ ユーザテンプレートディレクトリ
  └─ テンプレート検証ロジック
```

##### DIパターンによる拡張性

```python
# 既存Round Controller
class RoundController:
    def __init__(self, ..., prompt_builder: PromptBuilder | None = None):
        self.prompt_builder = prompt_builder or PlainTextPromptBuilder()
```

このパターンにより：
- テンプレートエンジン切り替えが容易（`PlainTextPromptBuilder` → `Jinja2PromptBuilder`）
- テスト時はMock実装に置き換え可能
- 後方互換性を維持したまま長期展開が可能

---

## 調査完了

Phase 0リサーチは完了しました。次のPhase 1（Design & Contracts）に進みます。
