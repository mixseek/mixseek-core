# 機能仕様書: Round Controller - ラウンドライフサイクル管理

**機能ブランチ**: `012-round-controller`
**作成日**: 2025-11-05
**ステータス**: ドラフト
**入力**: ユーザ説明: "Round Controllerの実装"

## 明確化事項

### セッション 2025-11-05

- Q: ラウンド継続判定に最小ラウンド数を追加するか → A: 最小ラウンド数（デフォルト: 2ラウンド）を追加し、最小ラウンド数に達するまではLLM判定を行わず必ず次ラウンドに進む
- Q: Round Promptは将来的に外部化するか → A: 将来的にPrompt Builderコンポーネントとして外部化することを想定し、現時点ではRound Controller内で実装するが拡張可能な設計にする
- Q: 次ラウンド開始時にチームのセッションやコンテキストを維持するか → A: 次ラウンド開始時には、チームのセッションやコンテキストを維持せず、毎回初期化する
- Q: FR-006で次ラウンド開始時にオーケストレータに制御を戻すか → A: Round Controller内で完結し、オーケストレータに制御を戻さない。オーケストレータはRound Controllerにタスクを投げた後は最終結果を受け取るまで待機するだけである
- Q: Entityで使用するタスク定義の名称は → A: `TaskDefinition`ではなく、オーケストレーションコンポーネントから受け取る`OrchestratorTask`を使用する
- Q: Round Controllerの最終的なアウトプットは → A: 最高スコアのSubmissionの`LeaderBoardEntry`をオーケストレータに返す
- Q: ImprovementJudgmentの永続化方法は → A: 当初は`improvement_judgment`テーブルを用意して記録する予定だったが、後に`round_status`テーブルに統合された（2025-11-06セッション参照）
- Q: Configファイルがない場合の動作は → A: 当初はログで警告を出力しつつデフォルト設定を使用する予定だったが、後にTOML設定ファイルを廃止し、オーケストレータからタスクで受け取る方式に変更された（2025-11-06セッション参照）
- Q: Submissionが不正な形式の場合の処理は → A: Submission失敗としてそのラウンドを処理し、LLMによる次ラウンド判定を省略し、次のラウンドを開始する。過去のSubmission履歴に失敗した旨を含める

### セッション 2025-11-06

- Q: 「タスク定義」という用語を統一するか → A: 「タスク定義」を「タスク」に変更し、仕様全体で統一する
- Q: Round ControllerのConfig設定をどう管理するか → A: TOML設定ファイルを廃止し、オーケストレータから受け取るタスク内で設定情報（最大ラウンド数、最小ラウンド数、Submissionタイムアウト、次ラウンド判定タイムアウト）を受け取る。チーム設定の上書き機能も廃止する
- Q: チームに渡すプロンプトにランキング情報を含めるか → A: プロンプトにleader_boardから取得した全チームの最高スコア一覧と、そのチームの現在順位を含める
- Q: オーケストレータから渡すタスク識別子は → A: execution_id（単一のユーザクエリに紐づくID）をタスクに含め、DuckDBテーブルに記録する
- Q: round_statusテーブルのmessage_historyカラムをどう扱うか → A: message_historyカラムを削除し、execution_idカラムを追加する
- Q: leader_boardテーブルにexecution_idを追加するか → A: execution_idカラムを追加する
- Q: improvement_judgmentテーブルを独立して保持するか → A: improvement_judgmentテーブルをround_statusテーブルに統合する（should_continue、reasoning、confidence_scoreカラムを追加）
- Q: RoundConfigとImprovementJudgementエンティティを保持するか → A: 両エンティティを削除する（設定はタスクから受け取り、判定結果はround_statusに統合）

### セッション 2025-11-11

- Q: 最大ラウンド数にシステム的な上限を設けるか → A: システム上限として最大ラウンド数10を設ける。オーケストレータから受け取るタスクの最大ラウンド数がこの上限を超える場合はバリデーションエラーとする
- Q: デフォルト値と上書きの管理方法をどうするべきか → A: 定数デフォルト値（最大ラウンド数=5、最小ラウンド数=2、Submissionタイムアウト=300秒、次ラウンド判定タイムアウト=60秒）を定義し、オーケストレータのTOML設定でデフォルト値を上書き可能にし、最終的な値をタスク経由でRound Controllerに渡す。

### セッション 2025-11-19

- Q: `final_submission`フラグは何を示すべきか（時系列上の最終ラウンドのSubmission vs 最高スコアで最終出力として選択されたSubmission） → A: 最高スコアのSubmissionとして最終出力に選択されたかどうかを示す。どのラウンドで出たかは関係なく、Round Controllerが最終結果としてオーケストレータに返すSubmissionにTRUEを設定する

## ユーザシナリオとテスト *(必須)*

### ユーザストーリー1 - 単一チーム・単一ラウンドの基本実行フロー (優先度: P1)

Round Controllerは、オーケストレータから受け取ったタスク（execution_id、team_id、チーム名、ユーザクエリ、設定情報、メタデータ等）をもとに、対応するチームに初回プロンプトを送信します。チームからSubmissionを受け取り、Evaluatorに評価を依頼し、評価結果をDuckDBの`round_status`および`leader_board`テーブルに保存します。

**この優先度の理由**: これはRound Controllerの最も基本的なフローであり、すべての後続機能の前提条件となります。

**独立テスト**: 単一チーム、単一ラウンドの設定でタスクを実行し、DuckDBにラウンド履歴と評価結果が正しく保存されることで完全にテスト可能です。

**受け入れシナリオ**:

1. **前提** オーケストレータがタスク（execution_id、team_id、チーム名、ユーザクエリ、設定情報、メタデータ）を送信する、**実行** Round Controllerがタスクを受信する、**結果** チームに対して初回プロンプトが整形され送信される
2. **前提** チームがSubmissionを返す、**実行** Round ControllerがEvaluatorに評価を依頼する、**結果** 評価結果（スコア、詳細フィードバック）が返される
3. **前提** 評価結果が返される、**実行** Round ControllerがDuckDBに保存する、**結果** `round_status`テーブルにラウンド情報、`leader_board`テーブルにSubmissionと評価結果が記録される
4. **前提** DuckDBへの保存が完了する、**実行** Round Controllerが次ラウンド判定を開始する、**結果** 次ラウンド判定ロジックが実行される

---

### ユーザストーリー2 - 複数ラウンドの反復改善と終了判定 (優先度: P1)

Round Controllerは、現在および過去のすべてのSubmissionと評価結果をもとに、次のラウンドに進むべきかどうかを判定します。判定は(a) 最小ラウンド数到達確認、(b) LLMによる改善見込み判定、(c) 最大ラウンド数到達確認の3段階で行われます。次ラウンドに進む場合は、前ラウンドのSubmission結果と評価フィードバックを統合したプロンプトを生成してチームに送信します。

**この優先度の理由**: TUMIX論文に基づく反復改善メカニズムの中核であり、品質向上のために不可欠です。

**独立テスト**: 複数ラウンドを必要とする設定（例: 最大5ラウンド）でタスクを実行し、各ラウンドの評価結果が蓄積され、終了判定が正しく機能することで検証可能です。

**受け入れシナリオ**:

1. **前提** ラウンド1の評価結果が保存されている、**実行** Round Controllerが次ラウンド判定を実行する、**結果** LLMが改善見込みを判定し、最大ラウンド数も確認される
2. **前提** 次ラウンドに進むと判定される、**実行** Round Controllerが次ラウンドプロンプトを生成する、**結果** 以前のすべてのラウンドのSubmission結果と評価フィードバックを統合したプロンプトがチームに送信される
3. **前提** 最大ラウンド数に到達する、**実行** Round Controllerが終了判定を実行する、**結果** 最高スコアのSubmissionが最終結果として選択され、`exit_reason`が「max rounds reached」として記録される
4. **前提** LLMが改善見込みなしと判定する、**実行** Round Controllerが終了処理を実行する、**結果** その時点での最高スコアSubmissionが最終結果として選択され、`exit_reason`が「no improvement expected」として記録される

---

### ユーザストーリー3 - DuckDBへの並列書き込みとデータ整合性 (優先度: P2)

Round Controllerは、複数チームが並列実行される環境で動作します。各チームのRound ControllerインスタンスがDuckDBの`round_status`および`leader_board`テーブルに並列書き込みを行う際、MVCC（Multi-Version Concurrency Control）により競合なく記録が完了します。

**この優先度の理由**: 親仕様（001-mixseek-core-specs）のFR-002で定義された複数チーム並列実行を実現するために必須です。

**独立テスト**: 複数チーム（例: 5チーム）を並列実行し、各チームのRound Controllerが独立してDuckDBに記録を行い、すべてのレコードが正しく保存されることで検証可能です。

**受け入れシナリオ**:

1. **前提** 複数チーム（例: 5チーム）が並列実行中である、**実行** 各Round ControllerがDuckDBに記録を試みる、**結果** すべてのチームのレコードが競合なく保存される
2. **前提** 同一チームの複数ラウンドが連続実行される、**実行** Round Controllerが各ラウンドの記録を順次保存する、**結果** team_idとラウンド番号の組み合わせで一意に識別され、正しい順序で記録される
3. **前提** DuckDBへの書き込みが一時的に失敗する、**実行** Round Controllerがリトライポリシー（3回、エクスポネンシャルバックオフ）で再試行する、**結果** リトライ成功時は正常記録、全リトライ失敗時はエラーを返す

---

### エッジケース

- **Evaluatorが評価に失敗する**: 評価リトライポリシー（3回、エクスポネンシャルバックオフ）で再試行し、全リトライ失敗時はチーム全体を失格とし、`exit_reason`を「evaluator failure」として記録する
- **チームからSubmissionが返らない（タイムアウト）**: タイムアウト時間（タスクで指定される）を超過した場合、チーム全体を失格とし、`exit_reason`を「submission timeout」として記録する
- **DuckDBへの書き込みが全リトライ後も失敗**: チーム全体を失格とし、失敗理由をログに記録し、オーケストレータにエラーを通知する
- **LLMによる改善見込み判定が失敗**: 判定リトライポリシー（3回）で再試行し、全リトライ失敗時は保守的に「改善見込みあり」として次ラウンドに進む（ただし最大ラウンド数制限は維持）
- **最高スコアのSubmissionが複数存在（同点）**: 最も遅いラウンド番号のSubmissionを選択する
- **評価スコアが不正な値（0未満、100超）**: バリデーションエラーとして扱い、Evaluatorに再評価を依頼し、再評価失敗時はチーム失格とする
- **Submissionが不正な形式の場合**: Submission失敗としてそのラウンドを処理し、LLMによる次ラウンド判定を省略して次のラウンドを開始する。過去のSubmission履歴に失敗した旨を含め、チームに再試行を促す
- **オーケストレータが設定値を渡さない（Null/未指定）**: Round Controllerは定数デフォルト値（最大ラウンド数=5、最小ラウンド数=2、Submissionタイムアウト=300秒、次ラウンド判定タイムアウト=60秒）を使用する
- **オーケストレータから受け取った最大ラウンド数がシステム上限（10）を超える**: バリデーションエラーとして即座に失敗し、オーケストレータにエラーを通知する。タスク実行は開始されない

## 要件 *(必須)*

### 機能要件

- **FR-001**: Round Controllerはオーケストレータからタスク（execution_id、team_id、チーム名、ユーザクエリ、設定情報、メタデータ等）を受け取り、対応するチームに初回プロンプトを整形して送信しなければならない。設定情報にはタスクごとの最大ラウンド数、最小ラウンド数、Submissionタイムアウト、次ラウンド判定タイムアウトが含まれる。これらの設定値が未指定の場合、Round Controllerはコード内デフォルト値を使用する（FR-014参照）
- **FR-002**: Round Controllerは各ラウンドで、チームの過去のSubmission情報（すべての前ラウンドのSubmission内容と評価結果）、メタデータ、およびleader_boardから取得した全チームの最高スコアランキングと当該チームの現在順位を含めてプロンプトを整形し、チームに送信しなければならない。プロンプト整形処理は将来的にPrompt Builderコンポーネントとして外部化することを想定し、拡張可能な設計（インターフェース分離、依存性注入等）で実装する
- **FR-003**: Round ControllerはチームからSubmissionを受け取り、Evaluatorに評価を依頼し、評価結果（スコア、詳細フィードバック）を取得しなければならない
- **FR-004**: Round Controllerは評価結果をDuckDBの`round_status`テーブル（execution_id、ラウンド番号、team_id、チーム名、改善見込み判定結果、ラウンド開始・終了日時、作成日時、更新日時）および`leader_board`テーブル（execution_id、ラウンド番号、team_id、チーム名、Submissionコンテンツ、Submissionフォーマット、スコア、スコア詳細、最終Submissionフラグ、終了理由、作成日時、更新日時）に保存しなければならない
- **FR-005**: Round Controllerは現在および過去のすべてのSubmissionと評価結果をもとに、次のラウンドに進むべきかどうかを判定しなければならない。判定は以下の3段階で行う：
  - **(a) 最小ラウンド数到達確認**: タスクから受け取った最小ラウンド数に達していない場合は、LLM判定を行わず必ず次ラウンドに進む
  - **(b) LLMによる改善見込み判定**: 最小ラウンド数に達した後、数ラウンド先でこれ以上スコアが改善する見込みがあるかどうかをLLMに判定させる。判定結果（should_continue、reasoning、confidence_score）は`round_status`テーブルに記録される。この実装はEvaluatorコンポーネントのLLM-as-a-Judge実装を参考にすること
  - **(c) 最大ラウンド数到達確認**: タスクから受け取った最大ラウンド数に到達しているかどうかを確認する。最大ラウンド数はシステム上限（10ラウンド）を超えることができない（FR-014参照）
- **FR-006**: 次のラウンドに進む場合、Round Controllerは前のすべてのラウンドのSubmission結果と評価フィードバックを統合したプロンプトを生成し、Round Controller内でユーザストーリー1のステップ1に戻らなければならない。オーケストレータに制御を戻さず、Round Controller内で全ラウンドを完結させる。チームのセッションやコンテキストは次ラウンド開始時に初期化され、維持されない
- **FR-007**: 終了する場合、Round Controllerは最高スコアのSubmissionを最終結果として選択し、`leader_board`テーブルの該当レコードの`final_submission`フラグをTRUEに設定し、`exit_reason`（例: "max rounds reached", "no improvement expected"）を記録しなければならない。最終結果として該当する`LeaderBoardEntry`をオーケストレータに返す
- **FR-008**: Round Controllerは`round_status`テーブルにラウンドの進捗状況（ラウンド開始・終了）を記録し、各ラウンドの開始時刻と終了時刻を保持しなければならない
- **FR-009**: Round ControllerはDuckDBへの書き込み失敗時、エクスポネンシャルバックオフ（1秒、2秒、4秒）で最大3回リトライし、全リトライ失敗時はチーム全体を失格として扱い、オーケストレータにエラーを通知しなければならない
- **FR-010**: Round Controllerはチームからのsubmissionタイムアウト、Evaluator評価失敗、DuckDB書き込み失敗など、回復不可能なエラー発生時、チーム全体を失格として扱い、失敗理由とステータスを記録しなければならない
- **FR-011**: Round Controllerは複数チームが並列実行される環境で動作し、DuckDBのMVCC（Multi-Version Concurrency Control）により競合なく記録を完了しなければならない
- **FR-012**: Round Controllerは最高スコアのSubmissionが複数存在する場合、最も遅いラウンド番号のSubmissionを選択しなければならない
- **FR-013**: Round ControllerはSubmissionが不正な形式の場合、Submission失敗としてそのラウンドを処理し、LLMによる次ラウンド判定を省略して次のラウンドを開始しなければならない。過去のSubmission履歴に失敗した旨を含め、チームに再試行を促すプロンプトを生成する
- **FR-014**: Round Controllerに渡される設定値は以下のデフォルト値を定義し、オーケストレータのTOML設定から設定値が渡されない場合にこれらの値を使用しなければならない：
  - 最大ラウンド数: 5ラウンド（システム上限: 10ラウンド。この上限を超える値を受け取った場合はバリデーションエラー）
  - 最小ラウンド数: 2ラウンド
  - Submissionタイムアウト: 300秒
  - 次ラウンド判定タイムアウト: 60秒

  オーケストレータはTOML設定ファイルでこれらのデフォルト値を上書き可能である。設定の優先順位は「オーケストレータTOML設定 > 定数デフォルト値」の順とする

### DuckDBテーブル定義

#### `round_status`テーブル

チームがどのように行動したかを記録する役割を持つ。

| カラム名 | データ型 | 制約 | 説明 |
|---------|---------|------|------|
| id | INTEGER | PRIMARY KEY, AUTO INCREMENT | 自動採番される一意なID |
| execution_id | VARCHAR | NOT NULL | タスクID（単一のユーザクエリに紐づくID） |
| team_id | VARCHAR | NOT NULL | team_id |
| team_name | VARCHAR | NOT NULL | チーム名 |
| round_number | INTEGER | NOT NULL | ラウンド番号 |
| should_continue | BOOLEAN | NULL | 改善見込み判定結果（TRUE: 継続すべき、FALSE: 終了すべき、NULL: 未判定） |
| reasoning | TEXT | NULL | 判定理由の詳細説明 |
| confidence_score | FLOAT | NULL | 信頼度スコア（0-1の範囲） |
| round_started_at | TIMESTAMP | NULL | ラウンド開始日時 |
| round_ended_at | TIMESTAMP | NULL | ラウンド終了日時 |
| created_at | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | レコード作成日時 |
| updated_at | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | レコード更新日時 |

**UNIQUE制約**: `(execution_id, team_id, round_number)` の組み合わせで一意性を保証

**INDEX**: `execution_id, team_id, round_number DESC` でラウンド履歴照会を最適化

#### `leader_board`テーブル

各チーム、各ラウンドのSubmissionと評価結果を記録する役割を持つ。

| カラム名 | データ型 | 制約 | 説明 |
|---------|---------|------|------|
| id | INTEGER | PRIMARY KEY, AUTO INCREMENT | 自動採番される一意なID |
| execution_id | VARCHAR | NOT NULL | タスクID（単一のユーザクエリに紐づくID） |
| team_id | VARCHAR | NOT NULL | team_id |
| team_name | VARCHAR | NOT NULL | チーム名 |
| round_number | INTEGER | NOT NULL | ラウンド番号 |
| submission_content | TEXT | NOT NULL | チームからのSubmission内容 |
| submission_format | VARCHAR | NOT NULL DEFAULT 'md' | Submissionのフォーマット情報（デフォルト: md） |
| score | FLOAT | NOT NULL | Evaluatorからの評価スコア（0-100） |
| score_details | JSON | NOT NULL | Evaluatorからの各評価指標のスコア内訳、コメント（JSON形式） |
| final_submission | BOOLEAN | NOT NULL DEFAULT FALSE | 最高スコアのSubmissionとして最終出力に選択されたかどうかを示すフラグ（Round Controllerがオーケストレータに返すSubmission） |
| exit_reason | VARCHAR | NULL | ラウンド終了の理由（例: "max rounds reached", "no improvement expected"） |
| created_at | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | レコード作成日時 |
| updated_at | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | レコード更新日時 |

**INDEX**: `execution_id, score DESC, round_number DESC` でタスクごとのランキング照会とタイブレークを最適化

**UNIQUE制約**: `(execution_id, team_id, round_number)` の組み合わせで一意性を保証

### 主要エンティティ *(機能がデータを含む場合に含める)*

- **OrchestratorTask**: オーケストレーションコンポーネント（specs/007-orchestration）から受け取るタスク。execution_id（単一のユーザクエリに紐づくID）、team_id、ユーザクエリ、設定情報（最大ラウンド数、最小ラウンド数、Submissionタイムアウト、次ラウンド判定タイムアウト）、メタデータ、タイムスタンプを保持する。設定情報が未指定の場合、Round ControllerはFR-014で定義されたデフォルト値を使用する。オーケストレータはTOML設定でデフォルト値を上書き可能である（親仕様の025-mixseek-core-orchestrationで定義）
- **RoundPrompt**: 各ラウンドでチームに送信するプロンプト。ユーザクエリ、過去のSubmission情報、評価フィードバック、leader_boardから取得した全チームの最高スコアランキングおよび当該チームの現在順位、メタデータを統合したもの。将来的にPrompt Builderコンポーネントとして外部化することを想定し、拡張可能な設計で実装される
- **Submission**: チームから返される応答。コンテンツ、フォーマット（デフォルト: markdown）、生成日時、team_id、ラウンド番号を含む（親仕様のPydanticモデルに準拠）
- **EvaluationResult**: Evaluatorからの評価結果。スコア（0-100）、スコア詳細（各評価指標のスコア内訳、コメント、JSON形式）、評価日時を含む（Evaluator仕様のPydanticモデルに準拠）
- **RoundStatus**: `round_status`テーブルのレコード。execution_id、ラウンド番号、team_id、チーム名、改善見込み判定結果（should_continue、reasoning、confidence_score）、ラウンド開始・終了日時、作成・更新日時を保持
- **LeaderBoardEntry**: `leader_board`テーブルのレコード。execution_id、ラウンド番号、team_id、チーム名、Submission内容・フォーマット、スコア、スコア詳細（JSON）、最終Submissionフラグ、終了理由、作成・更新日時を保持。Round Controllerの最終アウトプットとしてオーケストレータに返される

## 成功基準 *(必須)*

### 測定可能な成果

- **SC-001**: 単一チーム・単一ラウンドの実行において、タスク受信からDuckDB保存完了までが30秒以内に完了する（95パーセンタイル）
- **SC-002**: 複数ラウンド（5ラウンド）の実行において、各ラウンドの評価結果およびexecution_idがDuckDBに100%正確に記録される
- **SC-003**: 複数チーム（5チーム）並列実行において、すべてのチームのレコードが競合なくDuckDBに保存される（成功率100%）
- **SC-004**: LLMによる改善見込み判定の精度が80%以上である（手動評価との一致率）。判定結果は`round_status`テーブルに正確に記録される
- **SC-005**: 最大ラウンド数到達による終了が100%正確に機能する（タスクから受け取った最大ラウンド数と実際のラウンド数の一致）
- **SC-006**: DuckDB書き込みリトライが一時的な障害から95%以上の確率で回復する
- **SC-007**: チームに渡すプロンプトにleader_boardのランキング情報および当該チームの順位が100%正確に含まれる
- **SC-008**: システム上限（10ラウンド）を超える最大ラウンド数を受け取った場合、バリデーションエラーとして100%検出され、タスク実行が開始されない
- **SC-009**: オーケストレータから設定値が渡されない場合、デフォルト値（最大ラウンド数=5、最小ラウンド数=2、Submissionタイムアウト=300秒、次ラウンド判定タイムアウト=60秒）が100%正確に適用される

## 前提

- DuckDBのスキーマ（`round_status`, `leader_board`テーブル）は本仕様で定義され、実装時に作成される。
- チーム構成（TOML形式の`TeamConfig`、親仕様の001-mixseek-core-specs FR-014および関連仕様026-mixseek-core-leader参照）は既に設定済みであり、Round Controllerは既存設定を利用する
- Evaluatorコンポーネント（specs/006-evaluator）は既に実装済みであり、Round ControllerはEvaluatorのAPIを呼び出す
- Leader AgentおよびMember Agentの実装（specs/008-leader, specs/009-member）は既に完了しており、Round ControllerはこれらのエージェントAPIを利用する
- オーケストレータ（specs/007-orchestration）は既に実装済みであり、Round Controllerはオーケストレータから呼び出される。オーケストレータはタスク（execution_id、設定情報含む）をRound Controllerに渡す
- 環境変数`MIXSEEK_WORKSPACE`は設定済みであり、DuckDBファイルは`$MIXSEEK_WORKSPACE/mixseek.db`に配置される（憲章Article 9準拠）
- DuckDBバージョン1.0以降を使用し、MVCC（Multi-Version Concurrency Control）による並列書き込みが完全サポートされている
- LLMによる改善見込み判定は、Pydantic AIのDirect Model Request API（`model_request_sync`）を使用し、Evaluator実装と同様の手法で実装される。判定結果は`round_status`テーブルに記録される
- Round Controllerに渡される設定値は定数デフォルト値を持ち、オーケストレータはTOML設定でこれらを上書き可能である。最終的な設定値はタスク経由でRound Controllerに渡される。設定の優先順位は「オーケストレータTOML設定 > 定数デフォルト値」の順である（FR-014参照）

## 依存関係

- **親仕様**: specs/001-specs
  - FR-002 (複数チーム並列実行)
  - FR-006 (ラウンドベース処理)
  - FR-007 (Round Controllerの責務)
  - FR-011 (ラウンド終了インターフェース)
  - FR-014 (チーム設定構造)
- **関連仕様**:
  - specs/006-evaluator (Evaluator API、LLM-as-a-Judge実装)
  - specs/008-leader (Leader Agent API、TeamConfig、RoundStatus定義)
  - specs/009-member (Member Agent API)
  - specs/007-orchestration (Orchestrator API、OrchestratorTask定義、execution_id仕様)
- **技術依存**:
  - DuckDB 1.0以降（MVCC並列書き込み、ネイティブJSON型）
  - Pydantic AI Direct Model Request API（LLMによる改善見込み判定）
  - Pydanticモデル（型安全性、バリデーション）
