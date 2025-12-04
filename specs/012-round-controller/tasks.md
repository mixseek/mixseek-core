# Tasks: Round Controller - ラウンドライフサイクル管理

**入力**: 設計書（`/specs/012-round-controller/`）
**前提条件**: plan.md（必須）、spec.md（ユーザストーリー、必須）、research.md、data-model.md、contracts/

**テスト**: ユーザからの要求により、既存テストの修正と新機能のテストを追加します。

**テストタスクサマリー**:
- **User Story 1 (T042-T046)**: 5個のテストタスク（単一ラウンド、DuckDB保存、LeaderBoardEntry戻り値検証）
- **User Story 2 (T047-T053)**: 7個のテストタスク（複数ラウンド、改善見込み判定、終了判定、プロンプト整形）
- **User Story 3 (T054-T058)**: 5個のテストタスク（並列書き込み、トランザクション、リトライ、UPSERT）
- **合計**: 17個の新規テストタスク

**構成**: タスクはユーザストーリーごとにグループ化され、各ストーリーを独立して実装・テスト可能にします。

## フォーマット: `[ID] [P?] [Story] 説明`
- **[P]**: 並列実行可能（異なるファイル、依存関係なし）
- **[Story]**: どのユーザストーリーに属するか（例: US1, US2, US3）
- 説明には正確なファイルパスを含む

## パス規則
- **単一プロジェクト**: リポジトリルートに`src/`、`tests/`
- このタスクリストは単一プロジェクトを想定（plan.mdの構造に基づく）

---

## Phase 1: Setup（共有インフラ）

**目的**: プロジェクト初期化と基本構造の準備

- [X] T001 プロジェクト構造を実装計画（plan.md）に従って作成する
- [X] T002 Python 3.13.9環境と必要な依存関係（Pydantic AI、DuckDB、Pydantic 2.x）をインストールする
- [X] T003 [P] ruffとmypyの設定を確認し、品質チェックを有効化する

---

## Phase 2: Foundational（ブロッキング前提条件）

**目的**: すべてのユーザストーリーが依存するコアインフラ。このフェーズが完了するまで、ユーザストーリーの作業は開始できません。

**⚠️ クリティカル**: このフェーズが完了するまで、ユーザストーリー作業を開始できません

- [X] T004 DuckDBスキーマ（`round_status`、`leader_board`テーブル）を`src/mixseek/storage/schema.py`に定義する
- [X] T005 [P] `src/mixseek/models/leaderboard.py`に`LeaderBoardEntry` Pydantic Modelを作成する
- [X] T006 [P] `src/mixseek/round_controller/models.py`に`ImprovementJudgment`および`RoundState` Pydantic Modelを作成する
- [X] T007 `src/mixseek/orchestrator/models.py`の`OrchestratorTask`にラウンド設定フィールド（max_rounds、min_rounds、submission_timeout_seconds、judgment_timeout_seconds）を追加する
- [X] T008 [P] `src/mixseek/orchestrator/models.py`の`ExecutionSummary`の`team_results`を`list[LeaderBoardEntry]`に変更し、`best_score`を0-100スケールに変更する
- [X] T009 `src/mixseek/storage/aggregation_store.py`に`initialize_schema()`メソッドを追加し、DuckDBスキーマ初期化を実装する
- [X] T010 [P] `src/mixseek/storage/aggregation_store.py`に`round_status`テーブルへの書き込みメソッドを実装する
- [X] T011 [P] `src/mixseek/storage/aggregation_store.py`に`leader_board`テーブルへの書き込みメソッドを実装する

**チェックポイント**: 基礎準備完了 - ユーザストーリーの実装を並列で開始可能

---

## Phase 3: User Story 1 - 単一チーム・単一ラウンドの基本実行フロー (優先度: P1) 🎯 MVP

**ゴール**: オーケストレータから受け取ったタスクをもとに、対応するチームに初回プロンプトを送信し、Submissionを受け取り、Evaluatorで評価し、DuckDBに保存します。

**独立テスト**: 単一チーム、単一ラウンドの設定でタスクを実行し、DuckDBにラウンド履歴と評価結果が正しく保存されることで完全にテスト可能です。

### 実装（ユーザストーリー1）

- [X] T012 [P] [US1] `src/mixseek/round_controller/controller.py`にRound Controllerクラスの基本構造を作成する（__init__、タスク受信処理）
- [X] T013 [US1] `src/mixseek/round_controller/controller.py`に初回プロンプト整形ロジックを実装する（ユーザクエリ、メタデータを統合）
- [X] T014 [US1] `src/mixseek/round_controller/controller.py`にLeader Agentへのプロンプト送信処理を実装する（既存のLeader Agent APIを利用）
- [X] T015 [US1] `src/mixseek/round_controller/controller.py`にチームからのSubmission受信処理を実装する（タイムアウト処理含む）
- [X] T016 [US1] `src/mixseek/round_controller/controller.py`にEvaluatorへの評価依頼処理を実装する（既存のEvaluator APIを利用、リトライポリシー含む）
- [X] T017 [US1] `src/mixseek/round_controller/controller.py`に評価結果のDuckDB保存処理を実装する（`round_status`および`leader_board`テーブルに記録）
- [X] T018 [P] [US1] `src/mixseek/round_controller/controller.py`にエラーハンドリングを追加する（Submission失敗、Evaluator失敗、DuckDB書き込み失敗）
- [X] T019 [US1] `src/mixseek/orchestrator/orchestrator.py`を変更し、各チームから`LeaderBoardEntry`を受け取るように修正する

### テスト（ユーザストーリー1）

- [X] T042 [P] [US1] `tests/unit/round_controller/test_round_controller.py`を修正し、既存のrun_round()テストがLeaderBoardEntry戻り値を検証するように更新する
- [X] T043 [P] [US1] `tests/unit/round_controller/test_round_controller.py`に単一ラウンドのDuckDB保存テストを追加する（round_status、leader_boardテーブルへの記録を検証）
- [X] T044 [P] [US1] `tests/unit/orchestrator/test_orchestrator.py`を修正し、各チームからLeaderBoardEntryを受け取るテストを追加する
- [X] T045 [P] [US1] `tests/unit/storage/test_aggregation_store.py`を修正し、round_status、leader_boardテーブルへの書き込みテストを追加する
- [X] T046 [US1] `tests/integration/test_orchestrator_e2e.py`を修正し、単一ラウンドのE2Eテストが新DuckDBスキーマで動作することを検証する

**チェックポイント**: この時点で、ユーザストーリー1は完全に機能し、独立してテスト可能です

---

## Phase 4: User Story 2 - 複数ラウンドの反復改善と終了判定 (優先度: P1)

**ゴール**: 現在および過去のすべてのSubmissionと評価結果をもとに、次のラウンドに進むべきかどうかを判定します。判定は(a) 最小ラウンド数到達確認、(b) LLMによる改善見込み判定、(c) 最大ラウンド数到達確認の3段階で行われます。

**独立テスト**: 複数ラウンドを必要とする設定（例: 最大5ラウンド）でタスクを実行し、各ラウンドの評価結果が蓄積され、終了判定が正しく機能することで検証可能です。

### 実装（ユーザストーリー2）

- [X] T020 [P] [US2] `src/mixseek/round_controller/judgment_client.py`にLLM-as-a-Judgeによる改善見込み判定クライアントを作成する（Pydantic AI Direct Model Request API使用）
- [X] T021 [US2] `src/mixseek/round_controller/judgment_client.py`に改善見込み判定プロンプト整形ロジックを実装する（過去のSubmission履歴、評価スコアを統合）
- [X] T022 [US2] `src/mixseek/round_controller/judgment_client.py`にリトライポリシー（3回、エクスポネンシャルバックオフ）を実装する
- [X] T023 [US2] `src/mixseek/round_controller/controller.py`にラウンド継続判定ロジックを実装する（最小ラウンド数確認、LLM判定、最大ラウンド数確認の3段階）
- [X] T024 [US2] `src/mixseek/round_controller/controller.py`に次ラウンドプロンプト整形ロジックを実装する（過去のSubmission履歴、評価フィードバック、leader_boardランキング情報を統合）
- [X] T025 [US2] `src/mixseek/storage/aggregation_store.py`に`leader_board`テーブルから全チームの最高スコアランキングを取得するクエリを実装する
- [X] T026 [US2] `src/mixseek/round_controller/controller.py`に複数ラウンドループ処理を実装する（最大max_roundsまで反復）
- [X] T027 [US2] `src/mixseek/round_controller/controller.py`に終了時の最高スコアSubmission特定処理を実装する（同点時は最も遅いラウンド番号を選択）
- [X] T028 [US2] `src/mixseek/round_controller/controller.py`に`leader_board`テーブルの`final_submission`フラグと`exit_reason`の更新処理を実装する
- [X] T029 [US2] `src/mixseek/round_controller/controller.py`に最終的な`LeaderBoardEntry`をオーケストレータに返す処理を実装する（FR-007準拠）

### テスト（ユーザストーリー2）

- [X] T047 [P] [US2] `tests/unit/round_controller/test_improvement_judgment.py`を新規作成し、LLMによる改善見込み判定クライアントのユニットテストを実装する（4テスト: 継続判定、終了判定、リトライ、例外投げ確認）
- [X] T048 [P] [US2] `tests/unit/round_controller/test_round_controller.py`に複数ラウンド実行テストを追加する（最大5ラウンド、各ラウンドのDuckDB記録を検証）
- [X] T049 [P] [US2] `tests/unit/round_controller/test_round_controller.py`にラウンド継続判定テストを追加する（最小ラウンド数確認、LLM判定、最大ラウンド数確認の3段階を検証）
- [X] T050 [P] [US2] `tests/unit/round_controller/test_round_controller.py`に次ラウンドプロンプト整形テストを追加する（過去のSubmission履歴、評価フィードバック、ランキング情報の統合を検証）
- [X] T051 [P] [US2] `tests/unit/round_controller/test_round_controller.py`に終了時の最高スコアSubmission特定テストを追加する（同点時は最も遅いラウンド番号を選択）
- [X] T052 [P] [US2] `tests/unit/storage/test_aggregation_store.py`にleader_boardランキング取得テストを追加する
- [X] T053 [US2] `tests/integration/test_orchestrator_e2e.py`に複数ラウンドのE2Eテストを追加する（反復改善の動作を検証）

**チェックポイント**: この時点で、ユーザストーリー1とユーザストーリー2の両方が独立して動作します

---

## Phase 5: User Story 3 - DuckDBへの並列書き込みとデータ整合性 (優先度: P2)

**ゴール**: 複数チームが並列実行される環境で、各チームのRound ControllerインスタンスがDuckDBの`round_status`および`leader_board`テーブルに並列書き込みを行う際、MVCC（Multi-Version Concurrency Control）により競合なく記録が完了します。

**独立テスト**: 複数チーム（例: 5チーム）を並列実行し、各チームのRound Controllerが独立してDuckDBに記録を行い、すべてのレコードが正しく保存されることで検証可能です。

### 実装（ユーザストーリー3）

- [X] T030 [P] [US3] `src/mixseek/storage/aggregation_store.py`にスレッドローカルコネクション管理を実装する（各スレッドが独立したDuckDBコネクションを保持）
- [X] T031 [US3] `src/mixseek/storage/aggregation_store.py`にasyncio.to_threadによるブロッキングAPI対応を実装する（同期APIをスレッドプール実行）
- [X] T032 [US3] `src/mixseek/storage/aggregation_store.py`に明示的トランザクション管理を実装する（BEGIN/COMMIT/ROLLBACKによる一貫性保証）
- [X] T033 [US3] `src/mixseek/storage/aggregation_store.py`にエクスポネンシャルバックオフリトライを実装する（1秒、2秒、4秒のリトライ間隔、最大3回）
- [X] T034 [US3] `src/mixseek/storage/aggregation_store.py`にON CONFLICT（UPSERT）による重複対応を実装する（UNIQUE制約で重複検出、重複時は最新データで上書き）
- [X] T035 [P] [US3] `src/mixseek/round_controller/controller.py`にDuckDB書き込み失敗時のエラーハンドリングを追加する（全リトライ失敗時はチーム全体を失格として扱う）

### テスト（ユーザストーリー3）

- [ ] T054 [P] [US3] `tests/unit/storage/test_aggregation_store.py`にスレッドローカルコネクション管理テストを追加する
- [ ] T055 [P] [US3] `tests/unit/storage/test_aggregation_store.py`にトランザクション管理テストを追加する（BEGIN/COMMIT/ROLLBACKの動作を検証）
- [ ] T056 [P] [US3] `tests/unit/storage/test_aggregation_store.py`にエクスポネンシャルバックオフリトライテストを追加する（1秒、2秒、4秒のリトライ間隔を検証）
- [ ] T057 [P] [US3] `tests/unit/storage/test_aggregation_store.py`にON CONFLICT（UPSERT）による重複対応テストを追加する
- [ ] T058 [US3] `tests/integration/test_concurrent_writes.py`を修正し、複数チーム並列実行時のDuckDB並列書き込みテストを追加する（5チーム並列、競合なく記録完了を検証）

**チェックポイント**: すべてのユーザストーリーが独立して機能します

---

## Phase 6: Polish & Cross-Cutting Concerns

**目的**: 複数のユーザストーリーに影響する改善

- [X] T036 [P] `docs/`にRound Controller機能のドキュメントを追加する
- [X] T037 コードのクリーンアップとリファクタリングを実施する
- [X] T038 すべてのユーザストーリーにわたるパフォーマンス最適化を実施する（SC-001～SC-007の達成確認）
- [X] T039 セキュリティ強化を実施する（Article 9準拠、ハードコードされた値をすべて名前付き定数に置き換え）
- [X] T040 quickstart.mdの検証を実行する（手順通りに動作することを確認）
- [X] T041 品質チェックを実行する（`ruff check --fix . && ruff format . && mypy .`）

---

## 依存関係と実行順序

### フェーズ依存関係

- **Setup (Phase 1)**: 依存関係なし - 即座に開始可能
- **Foundational (Phase 2)**: Setupフェーズ完了に依存 - すべてのユーザストーリーをブロック
- **User Stories (Phase 3-5)**: すべてFoundationalフェーズ完了に依存
  - ユーザストーリーは並列実行可能（スタッフが確保できれば）
  - または優先度順に順次実行（P1 → P1 → P2）
- **Polish (Final Phase)**: すべての必要なユーザストーリー完了に依存

### ユーザストーリー依存関係

- **User Story 1 (P1)**: Foundational (Phase 2) 完了後に開始可能 - 他のストーリーへの依存なし
- **User Story 2 (P1)**: Foundational (Phase 2) 完了後に開始可能 - US1と統合するが、独立してテスト可能（US1の基本構造に依存）
- **User Story 3 (P2)**: Foundational (Phase 2) 完了後に開始可能 - US1/US2と統合するが、独立してテスト可能

### 各ユーザストーリー内

- モデルはサービスより先に実装
- サービスはエンドポイントより先に実装
- コア実装は統合より先に実装
- ストーリー完了後、次の優先度に移行

### 並列実行機会

- Setupフェーズでは、すべての[P]マークのタスクを並列実行可能
- Foundationalフェーズでは、Phase 2内のすべての[P]マークのタスクを並列実行可能
- Foundationalフェーズ完了後、すべてのユーザストーリーを並列開始可能（チーム人員が確保できれば）
- 各ユーザストーリー内で、[P]マークのタスクを並列実行可能
- 異なるユーザストーリーは異なるチームメンバーが並列作業可能

---

## 並列実行例: User Story 1

```bash
# User Story 1のすべてのモデルを同時に起動:
Task: "src/mixseek/models/leaderboard.pyにLeaderBoardEntry Pydantic Modelを作成する"
Task: "src/mixseek/round_controller/models.pyにImprovementJudgmentおよびRoundState Pydantic Modelを作成する"

# User Story 1のエラーハンドリングを並列で追加:
Task: "src/mixseek/round_controller/controller.pyにエラーハンドリングを追加する（Submission失敗、Evaluator失敗、DuckDB書き込み失敗）"

# User Story 1のテストを並列で実行:
Task: "tests/unit/round_controller/test_round_controller.pyを修正し、既存のrun_round()テストがLeaderBoardEntry戻り値を検証するように更新する"
Task: "tests/unit/round_controller/test_round_controller.pyに単一ラウンドのDuckDB保存テストを追加する"
Task: "tests/unit/orchestrator/test_orchestrator.pyを修正し、各チームからLeaderBoardEntryを受け取るテストを追加する"
Task: "tests/unit/storage/test_aggregation_store.pyを修正し、round_status、leader_boardテーブルへの書き込みテストを追加する"
```

---

## 実装戦略

### MVP First（ユーザストーリー1のみ）

1. Phase 1: Setup を完了
2. Phase 2: Foundational を完了（クリティカル - すべてのストーリーをブロック）
3. Phase 3: User Story 1 を完了
4. **停止して検証**: ユーザストーリー1を独立してテスト
5. 準備ができていればデプロイ/デモ

### 段階的デリバリー

1. Setup + Foundational を完了 → 基盤準備完了
2. User Story 1 を追加 → 独立してテスト → デプロイ/デモ（MVP!）
3. User Story 2 を追加 → 独立してテスト → デプロイ/デモ
4. User Story 3 を追加 → 独立してテスト → デプロイ/デモ
5. 各ストーリーが前のストーリーを壊すことなく価値を追加

### 並列チーム戦略

複数の開発者がいる場合:

1. チームでSetup + Foundationalを一緒に完了
2. Foundational完了後:
   - 開発者A: User Story 1
   - 開発者B: User Story 2
   - 開発者C: User Story 3
3. ストーリーが完了し、独立して統合

---

## 注意事項

- [P] タスク = 異なるファイル、依存関係なし
- [Story] ラベルはタスクを特定のユーザストーリーにマッピングし、トレーサビリティを確保
- 各ユーザストーリーは独立して完了・テスト可能であるべき
- 各タスクまたは論理的なグループ後にコミット
- どのチェックポイントでも停止してストーリーを独立して検証可能
- 避けるべき: 曖昧なタスク、同じファイルの競合、ストーリーの独立性を壊すクロスストーリー依存
