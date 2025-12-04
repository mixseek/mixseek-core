# Feature Specification: Leader Agent - Agent Delegation と Member Agent応答記録

**Feature Branch**: `026-mixseek-core-leader`
**Created**: 2025-10-22
**Status**: Draft
**Input**: User description: "plans/026-leader-agent の情報をもとに Leader Agentの仕様定義を日本語で実施してください、ブランチ名は現行のブランチ名026-mixseek-core-leaderを使ってください"

## Terminology

本仕様で使用する重要な用語を定義します：

- **記録（Record）**: Leader Agentが単一ラウンド内でMember Agent応答を構造化データ（`List[MemberSubmission]`）として保存する処理。前ラウンドを意識せず、現在のラウンドのデータのみを扱う
- **統合処理（Integration）**: Round Controllerが複数ラウンド間でSubmission結果を統合し、次ラウンドプロンプトを生成する処理。前ラウンドの結果と評価フィードバックを引き継ぐ
- **整形処理（Formatting）**: Round Controllerが構造化データ（`List[MemberSubmission]`）をMarkdown連結、JSON出力、表形式などの形式に変換する処理
- **集計（Aggregation）**: リソース使用量（input_tokens、output_tokens、requests）を合計する計算処理。Leader Agentが全Member AgentのRunUsageを合計する

## User Scenarios & Testing

### User Story 1 - Agent Delegationによる動的なMember Agent選択と記録 (Priority: P1)

システム開発者がLeader Agentを使用すると、Leader AgentはタスクをLLMで分析し、適切なMember AgentをToolを通じて動的に選択・実行します。選択されたMember Agentの応答は構造化データとして自動的に記録されます。失敗したAgent応答もエラーステータスと詳細付きで保持され、成功・失敗の両方を追跡できます。

**Why this priority**: これはLeader Agentのコア機能であり、Pydantic AIのAgent Delegationパターンに基づくマルチエージェント協調の基盤となります。全Agent並列実行方式と比較して、リソース効率と柔軟性が大幅に向上します。

**Independent Test**: 3つのMember Agentが定義されたチームで、タスクに応じて2つのMember Agentが選択・実行され、成功・失敗応答がステータスおよびAgent名付きで構造化データとして記録されることで完全にテスト可能です。

**Acceptance Scenarios**:

1. **Given** 複数のMember Agentが設定されたチーム（数は可変、上限あり）、**When** ユーザープロンプトを実行、**Then** Leader AgentがToolを通じて必要なMember Agentのみを選択・実行し、応答を構造化データとして記録する
2. **Given** 記録された構造化データ、**When** Round Controllerが整形処理を実行、**Then** 各Agent応答が用途に応じた形式（Markdown連結、JSON等）で出力される
3. **Given** 3つのMember Agentで1つが失敗、**When** 記録処理を実行、**Then** 失敗応答もエラーメタデータ付きで記録に残り、成功・失敗応答が区別できる
4. **Given** 構造化データ（各MemberSubmissionにAgent名含む）、**When** ユーザーが確認、**Then** どのAgentがどの情報を提供したか明確に区別できる
5. **Given** タスクが単純な場合、**When** Leader Agentが判断、**Then** 1つのMember Agentのみを実行してリソースを節約できる
6. **Given** タスクが複雑な場合、**When** Leader Agentが判断、**Then** 複数のMember Agentを順次実行して包括的な応答を生成できる

---

### User Story 2 - 複数チーム並列実行時のロックフリーデータ永続化 (Priority: P1)

複数チーム（各チームに1つのLeader Agent）が同時並列実行される際、各Leader Agentが生成したMessage HistoryとSubmissionが、ロック競合なく独立してデータベースに保存されます。チーム間でのデータベースロック待機やブロッキングは発生せず、全てのチームが最高速度で実行を継続できます。

**Why this priority**: MixSeek-Coreの仕様（親仕様FR-002）では複数チームの並列実行が必須要件です。データ永続化時のロック競合が発生すると、チーム実行がブロックされ、並列実行の利点が失われます。DuckDB MVCC方式による並列書き込み対応はこの機能の中核です。

**Independent Test**: 複数チームを並列実行し、各チームが複数ラウンド完了後、データベースに全ての履歴レコードが保存されていることで検証可能です（例：10チーム×5ラウンド=50件）。

**Acceptance Scenarios**:

1. **Given** 複数チームが並列実行中（例：10チーム）、**When** 各チームが同時にMessage Historyを保存、**Then** すべてのデータがロック競合なく保存される
2. **Given** あるチームのラウンド1完了、**When** Message HistoryとSubmissionを保存、**Then** データベースに正しいJSON形式で保存される
3. **Given** 同一チームが複数ラウンド実行、**When** 各ラウンドのデータを保存、**Then** チームIDとラウンド番号の組み合わせで一意に識別される
4. **Given** データベース保存完了、**When** 次ラウンドで履歴読み込み、**Then** 元のPydantic AI Message構造に完全復元される

---

### User Story 3 - Leader Boardによるチームパフォーマンス追跡 (Priority: P2)

システム管理者が複数チームの実行結果を比較する際、Leader Boardを通じて各チームのSubmission評価スコア、使用リソース、実行履歴をリアルタイムで確認できます。スコア順のランキング表示により、最も優れたアプローチを即座に特定できます。

**Why this priority**: チーム間の競合評価はTUMIXの重要な要素ですが、コア機能（応答記録とデータ永続化）が動作すれば、Leader Boardの実装は後からでも可能です。

**Independent Test**: 複数チームが複数ラウンド実行後、Leader BoardのAPIで最高スコアチームを取得し、正しいランキングが返されることで検証可能です（例：3チーム×5ラウンド）。

**Acceptance Scenarios**:

1. **Given** 複数チームがSubmissionを完了、**When** Leader Boardを照会、**Then** 評価スコア降順でチームがランキング表示される
2. **Given** 同一スコアの複数チーム、**When** ランキング計算、**Then** 同順位として扱われ、2次ソートは作成日時（早い順）で行われる
3. **Given** Leader Boardデータ、**When** チーム統計を集計、**Then** 総ラウンド数、平均スコア、総トークン使用量が取得できる
4. **Given** 大量の履歴データ（例：100万行）、**When** Leader Board集計クエリ実行、**Then** 1秒以内に結果が返される

---

### User Story 4 - リソース使用量の追跡と集計 (Priority: P3)

システム開発者が各ラウンドの実行コストを分析する際、Pydantic AI RunUsage形式でトークン使用量、リクエスト数、実行時間が自動的に集計され、JSON形式でデータベースに保存されます。チーム単位、ラウンド単位での集計により、コスト最適化の判断材料を得られます。

**Why this priority**: リソース追跡は運用上重要ですが、基本的な応答記録とデータ永続化が機能していれば、リソース情報は後から追加できます。

**Independent Test**: 複数のMember Agentを実行し、記録結果のtotal_usageフィールドに全Agent合計のトークン数が正しく記録されることで検証可能です（例：3つのAgent）。

**Acceptance Scenarios**:

1. **Given** 各Member Agentが実行完了、**When** リソース使用量を集計、**Then** 全Agentのinput_tokens、output_tokens、requests が合計される
2. **Given** 集計されたリソース情報、**When** データベースに保存、**Then** JSON形式で永続化される
3. **Given** 複数ラウンドの履歴、**When** チーム単位で集計、**Then** 全ラウンドの累積リソース使用量が取得できる

---

### User Story 5 - 開発・テスト用チーム実行コマンド (Priority: P2)

開発者は`mixseek team`コマンドを使用して、チーム設定ファイル（TOML）を指定し、Agent Delegationによる動的なMember Agent選択と記録処理をテストします。Leader Agentはタスクを分析し、適切なMember AgentをToolを通じて実行します。コマンドは開発・テスト専用であり、実行時に警告メッセージを表示します。記録結果とリソース使用量がJSON/テキスト形式で出力され、デバッグが容易になります。

**Why this priority**: Member Agentの`mixseek member`コマンドと同様、開発・テスト環境でチーム動作（特にAgent Delegation）を検証するために重要です。本番ではOrchestration Layerを通じて呼び出されるため、直接CLIは使用されません。

**Independent Test**: チーム設定TOMLを指定してコマンド実行し、Leader Agentが選択したMember Agent応答が構造化データとして記録され、JSON/テキスト形式で出力されることで検証可能です。

**Acceptance Scenarios**:

1. **Given** 開発者が`mixseek team "prompt" --config team.toml`を実行、**When** Leader Agentがタスクを分析、**Then** 必要なMember AgentのみがToolを通じて実行され、記録結果（成功/失敗数、構造化データ）が表示され、開発・テスト専用の警告が出力される
2. **Given** チームTOMLに3つのMember Agent定義があり、タスクが単純、**When** コマンド実行、**Then** Leader Agentが1つのMember Agentのみを選択・実行し、成功応答が記録される
2a. **Given** チームTOMLに`[team.leader]`セクションでLeader Agentの`system_instruction`を設定、**When** コマンド実行、**Then** 設定されたsystem_instruction（タスク分析・Agent選択ロジック含む）に従ってLeader Agentが動作する
2b. **Given** 各Member Agentに`tool_name`と`tool_description`を設定、**When** Leader Agentが実行、**Then** Leader AgentがToolの説明を参照してMember Agentを適切に選択する
2c. **Given** チームTOMLにMember Agentが1件も定義されていない、**When** コマンド実行、**Then** Leader Agentが単体で応答を生成し、Member Submissionは空リストとして記録される
3. **Given** チームTOMLで既存Member Agent TOMLファイルを参照（`config = "agents/analyst.toml"`形式）、**When** コマンド実行、**Then** 参照先agent.tomlから設定を読み込み、Toolとして登録され、正常実行される（DRY原則準拠）
4. **Given** `--output-format json`オプション指定、**When** コマンド実行、**Then** 記録結果がJSON形式で出力され、自動化スクリプトから利用可能
5. **Given** `--save-db`オプション指定、**When** コマンド実行、**Then** 記録結果とMessage HistoryがDuckDBに保存される
6. **Given** 選択された全Member Agentが失敗、**When** コマンド実行、**Then** 失敗理由を明示したエラーメッセージを表示して終了する

---

### Edge Cases

- **選択された全Member Agentが失敗した場合**: Leader Agentが選択・実行した全Member Agentが失敗し、成功応答が0件の場合、Leader Agentはエラーを報告する。ただし、Leader Agentは他のMember Agentを選択して再試行する可能性がある（Agent Delegationの柔軟性）
- **非常に長いAgent応答**: 単一Agent応答が10,000文字を超える場合、Round Controllerが整形時に要約処理を適用する選択肢を提供する
- **データベース書き込み失敗**: 一時的な障害でデータベース保存が失敗した場合、エクスポネンシャルバックオフ（1秒、2秒、4秒）で最大3回リトライし、それでも失敗したら明確なエラーメッセージを返す
- **Message History復元エラー**: データベースから読み込んだJSONがPydantic AI形式に復元できない場合、詳細なバリデーションエラーをログに記録し、該当ラウンドをスキップする
- **同時書き込み時のID競合**: 同一チーム・同一ラウンド番号で複数回保存を試みた場合、UPSERT処理により最新データで上書きする
- **データベースディレクトリへのアクセス権限**: `$MIXSEEK_WORKSPACE/`への書き込み権限がない場合、即座にエラー終了し、詳細ログ（試行パス、現在のユーザー権限、必要な権限、ディレクトリ所有者）を出力する。代替パスへのフォールバックは禁止（憲章Article 9準拠）
- **Member Agentタイムアウト**: 個別AgentがTOML設定のタイムアウトを超過した場合、そのAgentのみ失敗として扱い、他のAgent応答は正常に記録される
- **全Member Agentがタイムアウト**: すべてのMember Agentがタイムアウトした場合、成功応答が0件となり、チーム全体が失格となる（FR-002により自動処理）
- **環境変数MIXSEEK_WORKSPACE未設定**: 環境変数が設定されていない場合、即座にエラー終了し、設定例（`export MIXSEEK_WORKSPACE=/path/to/workspace`）を含むエラーメッセージを出力する（憲章Article 9準拠）
- **参照先Member Agent TOML不存在**: `config = "missing.toml"`で指定されたファイルが存在しない場合、即座にエラー終了し、ファイルパスとカレントディレクトリを明示したエラーメッセージを表示する（フォールバック禁止）
- **インライン定義と参照形式の混在**: 同一チーム設定内で、一部Memberがインライン定義、他がファイル参照の場合も正常動作する
- **Leader Agent system_instruction未設定**: `[team.leader]`セクションまたは`system_instruction`フィールドが未設定の場合、従来のデフォルトsystem_instructionを自動適用して正常動作を保証する（Clarifications Session 2025-10-29準拠）
- **Leader Agent system_instructionが空文字列**: `system_instruction = ""`の場合でもバリデーションエラーとはならず、Leader Agentはsystem_instructionを送信せずに実行する。空文字列は「system_instructionなし」を明示する指定として扱う
- **Member Agentのtool_name重複**: 複数のMember Agentが同じ`tool_name`を持つ場合、バリデーションエラーとして即座にエラー終了し、重複しているtool_nameを明示する
- **Member Agentのtool_name未設定**: `tool_name`フィールドが未設定の場合、`agent_name`から自動生成（例: `agent_name="analyst"` → `tool_name="delegate_to_analyst"`）し、正常動作する
- **Leader Agentが1つもMember Agentを選択しない**: タスクが非常に単純でMember Agentが不要とLeader Agentが判断した場合、Leader Agent自身が直接応答を生成し、記録結果には0件のMember Submissionが含まれる
- **Member Agent定義がゼロ**: チームTOMLで`[[team.members]]`セクションが1件も指定されていない場合でも設定エラーとせず、Leader Agentのみでタスク処理を実行し、Member Submissionは空リストとして記録する（Clarifications Session 2025-10-29準拠）
- **Leader Agentが同じMember Agentを複数回呼び出す**: Agent Delegationパターンでは許可される。各呼び出しは独立したMemberSubmissionとして記録され、RunUsageも個別にカウントされる

## Requirements

### Functional Requirements

**責務範囲**: Leader Agentは単一ラウンド内のMember Agent応答の記録とデータ永続化のみを担当する。複数ラウンド間の統合処理、前ラウンド結果の統合、評価フィードバックの適用、応答の整形処理はラウンドコントローラ（別仕様）の責務である。Leader Agentは前ラウンドを意識しない独立した設計とする。

- **FR-001**: Leader Agentは単一ラウンド内で0件以上のMember Agent実行結果を受け取り、`MemberSubmissionsRecord`モデルに記録しなければならない（Member Agentが存在しない場合は空リストを許容）
- **FR-002**: 記録処理では、失敗したMember Agent応答（`status == ERROR`）も成功応答と同じ構造で保存し、失敗理由（エラーメッセージ、エラー種別）を保持しなければならない
- **FR-003**: すべてのMember Agent応答（成功・失敗）を構造化データ（`List[MemberSubmission]`）として記録しなければならない。各MemberSubmissionには完全なメタデータ（Agent名、種別、コンテンツ、ステータス、リソース使用量、タイムスタンプ、必要に応じたエラー詳細）を含む。Markdown連結などの整形処理はRound Controllerが実施する
- **FR-004**: 各Member Agent応答には、Agent名、Agent種別、実行時間、リソース使用量を含まなければならない
- **FR-005**: 全Member Agentのリソース使用量（input_tokens, output_tokens, requests）を合計し、Pydantic AI RunUsage互換形式で保存しなければならない
- **FR-006**: Message HistoryをDuckDBにネイティブJSON型で保存し、Pydantic AI `ModelMessage`構造をそのまま永続化しなければならない
- **FR-007**: 記録結果（`MemberSubmissionsRecord`）をJSON形式でDuckDBに保存しなければならない
- **FR-007-1**: Message HistoryとMemberSubmissionsRecordは単一トランザクション内で保存し、データ整合性を保証しなければならない
- **FR-008**: データベース保存時、チームIDとラウンド番号の組み合わせで一意性を保証しなければならない（UNIQUE制約）
- **FR-009**: 複数Leader Agentが並列書き込みを行う際、DuckDBのMVCC方式によりロック競合なく処理しなければならない
- **FR-010**: Leader BoardテーブルにSubmission評価結果（スコア、フィードバック、コンテンツ）を保存しなければならない
- **FR-011**: Leader BoardからスコアでDESC降順ランキングを取得できなければならない。同スコアの場合は2次ソートとして作成日時の早い順で並べる
- **FR-012**: データベースから読み込んだJSONを`ModelMessagesTypeAdapter.validate_json()`でPydantic AI Message構造に復元しなければならない
- **FR-013**: チーム統計（総ラウンド数、平均スコア、総トークン使用量）をJSON内部クエリで集計できなければならない
- **FR-014**: 並列書き込みテストで複数チーム・複数ラウンドの同時保存が全て成功しなければならない（例：10チーム×5ラウンド=50件）
- **FR-015**: データベース接続はトランザクション管理（BEGIN/COMMIT/ROLLBACK）をサポートしなければならない
- **FR-016**: データベースファイルは環境変数`MIXSEEK_WORKSPACE`配下（`$MIXSEEK_WORKSPACE/mixseek.db`）に配置されなければならない。環境変数未設定時は即座にエラー終了し、環境変数の設定方法を示すメッセージを出力する（憲章Article 9準拠）
- **FR-017**: Member Agent実行時、各AgentのTOML設定で定義されたタイムアウト時間を尊重し、超過時はそのAgentを失敗として扱わなければならない
- **FR-018**: タイムアウトにより失敗したMember Agent応答は、`status == ERROR`かつエラー種別`timeout`で記録し、関連するエラー詳細を保持しなければならない（FR-002の記録ポリシーに従う）
- **FR-019**: データベース書き込み失敗時、エクスポネンシャルバックオフ（1秒、2秒、4秒の間隔）で最大3回リトライしなければならない
- **FR-020**: 環境変数未設定、ディレクトリアクセスエラー、権限エラー、ディスク容量不足等の回復不可能なエラー発生時、即座に処理を終了し、原因特定可能な詳細ログを出力しなければならない。暗黙のフォールバック、デフォルト値による代替処理は禁止（憲章Article 9: Data Accuracy Mandate準拠）
- **FR-021**: 開発・テスト用に`mixseek team`コマンドを提供しなければならない。チーム設定TOML指定、プロンプト入力、記録結果出力をサポートする（憲章Article 2: CLI Interface Mandate準拠）
- **FR-022**: `mixseek team`コマンドは実行時に開発・テスト専用である旨の警告メッセージを表示しなければならない（本番ではOrchestration Layer使用）
- **FR-023**: コマンド出力形式としてJSON、テキスト、構造化テキストをサポートしなければならない（`--output`オプション）。JSON出力形式では、記録結果（MemberSubmissionsRecord）に加え、Leader AgentとMember AgentのMessage Historyを統合した完全な対話履歴を`message_history`フィールドに含めなければならない。これにより、JSON出力でも完全な対話履歴（Leader AgentとMember Agentの両方のツール呼び出し、中間推論）を取得でき、デバッグ・監査が容易になる
- **FR-024**: `--save-db`オプション指定時、記録結果（MemberSubmissionsRecord）とMessage HistoryをDuckDBに保存しなければならない（デバッグ・検証用）。FR-034により、Message HistoryにはLeader AgentとMember Agentの両方の完全な対話履歴が含まれる
- **FR-025**: チーム設定TOMLは、Member Agent設定を2つの方法でサポートしなければならない: (1) インライン定義（全設定を`[[team.members]]`内に直接記述）、(2) 参照形式（`config = "path/to/agent.toml"`で既存Member Agent TOMLファイルを参照）。両方式の混在も可能とする（憲章Article 10: DRY準拠）
- **FR-026**: Leader Agentの`system_instruction`はTOML設定ファイルでカスタマイズ可能でなければならない。system_instructionにはチームの目的、Member Agentへの指示方針、結果の評価基準等を含むことができる
- **FR-027**: チーム設定TOMLは、Leader Agent固有の`system_instruction`設定（`[team.leader]`セクション）をサポートしなければならない。未設定の場合はデフォルトsystem_instructionを使用する
- **FR-028**: Leader AgentはPydantic AIのAgent Delegationパターンに従い、Toolを通じてMember Agentを動的に選択・実行できなければならない。実行するMember AgentはLeader Agentが自律的に判断する
- **FR-029**: 各Member AgentはLeader AgentのTool定義として登録され、Tool名・説明・パラメータを通じてLeader Agentから呼び出し可能でなければならない
- **FR-030**: Leader Agentの`system_instruction`を設定する場合、タスク分析とMember Agent選択のロジック（各Member Agentの専門性、使用タイミング、協調方法）を含められなければならない。`system_instruction = ""`を指定した場合はsystem_instructionを送信せずに稼働し、暗黙の補完は行わない
- **FR-031**: Member Agent実行時、`ctx.usage`を委譲先Member Agentの`usage`パラメータに渡し、全Member AgentのRunUsageを統合しなければならない（Pydantic AIのAgent Delegation標準パターン準拠）
- **FR-032**: `[team.leader]`セクションに`system_prompt`が指定された場合、Leader Agentはその値をPydantic AIの`system_prompt`として渡し、`system_instruction`（省略時はデフォルト）と併用してエージェントを初期化しなければならない。両方指定されてもバリデーションエラーとはしない。
- **FR-033**: チーム設定TOMLでMember Agentが1件も定義されていない場合でも設定を受理し、Leader Agent単独でタスク処理を行えるようにしなければならない。記録結果のMemberSubmissionsRecordは空リストとし、エラーを返してはならない。
- **FR-034**: Leader AgentはMember Agentから受け取った`all_messages`（Pydantic AI `list[ModelMessage]`型の完全なメッセージ履歴）をLeader Agent自身のメッセージ履歴と統合して記録しなければならない。統合されたメッセージ履歴は、Leader AgentとMember Agentの対話の因果関係（どのLeader Agentのツール呼び出しがどのMember Agentの実行を引き起こしたか）を保持し、デバッグ・監査時に時系列に沿った再現が可能な形式でなければならない。`--save-db`オプション指定時はDuckDBに保存し、`--output-format json`指定時はJSON出力に含める。これにより、Member Agentの内部動作（ツール呼び出し、中間推論、リトライ履歴）を完全に記録でき、デバッグ・監査・改善が可能になる。Member Agent仕様のFR-016（`MemberAgentResult`に`all_messages`フィールド追加）と連携して動作する。

### Non-Functional Requirements

- **NFR-001 パフォーマンス**: Agent Delegation 1回あたりの実行時間（Member Agent実行時間を含む）は5秒未満でなければならない
- **NFR-002 並列書き込み**: 複数チーム並列実行時のロック競合はゼロでなければならない
- **NFR-003 データベース集計**: Leader Board集計クエリは100万行に対して1秒以内に完了しなければならない
- **NFR-004 型安全性**: すべてのモデルはPydantic BaseModelを使用し、mypy strict modeでエラーゼロでなければならない
- **NFR-005 コード品質**: ruff + mypy品質チェックが全て合格しなければならない（Article 8準拠）

### Key Entities

- **MemberSubmission**: 個別Member Agentの応答を表す軽量モデル。Agent名、種別、コンテンツ、ステータス、エラーメッセージ、リソース使用量（Pydantic AI RunUsage型）、タイムスタンプを保持。`MemberAgentResult`から変換される。FR-034により、Member AgentのMessage History（`all_messages`）も保持し、Member Agentの内部動作を完全に記録する。
- **MemberSubmissionsRecord**: 単一ラウンド内の複数Member Agent応答を構造化データとして記録するモデル。ラウンド番号、チームID、全応答リスト（`List[MemberSubmission]`）、成功/失敗応答リスト、統計情報（総数、成功数、失敗数）、合計リソース使用量を保持。構造化データのみを保存し、整形処理（Markdown連結、JSON出力等）はRound Controllerが担当する。
- **TeamConfig（TOML設定）**: チーム全体の設定を定義するTOMLファイル。`[team]`セクション（team_id、team_name等）、`[team.leader]`セクション（Leader Agentの`system_instruction`等）、`[[team.members]]`セクション（Member Agent設定のリスト）を含む。各Member AgentはLeader AgentのToolとして自動登録される。
- **MemberAgentTool**: Leader AgentがMember Agentを呼び出すためのTool定義。各Member AgentのTOML設定（agent_name、agent_type、system_instruction等）から自動生成され、Leader Agentから`@leader_agent.tool`デコレータでアクセス可能。Pydantic AIのAgent Delegationパターンに準拠。
- **RoundHistory（データベーステーブル）**: チームID、ラウンド番号、Message History（JSON型、Leader AgentとMember Agentの完全な対話履歴を含む）、記録結果（MemberSubmissionsRecord、JSON型）、作成日時を保持。チームIDとラウンド番号の組み合わせで一意。単一トランザクションで両データを保存し整合性を保証。FR-034により、Member AgentのMessage Historyも統合して保存される。
- **LeaderBoard（データベーステーブル）**: チームID、チーム名、ラウンド番号、評価スコア、フィードバック、Submissionコンテンツ、リソース使用量（JSON型）、作成日時を保持。評価スコアに降順インデックス。
- **AggregationStore**: DuckDBへの保存・読み込みを管理するストアクラス。並列書き込み対応（MVCC）、トランザクション管理、Pydantic AI型との相互変換機能を提供。

## Key Design Decisions

本仕様の重要な設計決定を以下にまとめます：

### 責務の明確化

- **Leader Agentの責務**: 単一ラウンド内のMember Agent応答の**記録のみ**を担当。前ラウンドを意識しない独立した設計
- **Round Controllerの責務**: 複数ラウンド間の統合処理、前ラウンド結果の統合、評価フィードバックの適用、応答の整形処理（Markdown連結、JSON出力等）
- **Evaluatorの責務**: Submission評価結果の登録、Leader Board管理、スコアランキング表示

### Agent実行方式

- **Agent Delegation採用**: Leader AgentがToolを通じて必要なMember Agentのみを動的に選択・実行する方式を採用
- **全Agent並列実行破棄**: TUMIX論文は参考にするが遵守しない。Pydantic AIのAgent Delegationパターンに従い、リソース効率と柔軟性を優先
- **非決定的動作**: Leader AgentのLLMが自律的に判断するため、同じプロンプトでも選択されるMember Agentが異なる可能性がある
- **Member Agentゼロ許容**: チーム構成にMember Agentが存在しない場合でもLeader Agent単体で処理を完遂できるよう設計し、Agent Delegationの初期化時に空リストを許容する。

### LLM指示戦略

- **system_instruction優先**: Leader AgentはPydantic AIの`instructions` APIを使用し、MixSeekでは`system_instruction`としてTOMLに定義する。`system_instruction`はPydantic AIの`instructions`にマッピングし、旧称の`system_prompt`が指定された場合はPydantic AIの`system_prompt`としてそのまま渡す（Clarifications Session 2025-10-29準拠）。
- **デフォルトsystem_instruction管理**: `system_instruction`を省略した場合は既存デフォルトを自動適用し、`system_instruction = ""`を指定した場合は指示なしで実行する。暗黙の補完は行わない。

### データ管理

- **構造化データのみ保存**: `List[MemberSubmission]`形式で保存し、整形処理はRound Controllerに委譲
- **DuckDB採用**: ネイティブJSON型、MVCC並列書き込み対応、高速分析クエリのため
- **単一トランザクション保存**: Message HistoryとMemberSubmissionsRecordを単一トランザクションで保存し、データ整合性を保証

### 削除された機能（Out of Scope）

- **Round 2シミュレーション**: 前ラウンド結果の読み込み・整形処理はRound Controllerの責務（User Story 6削除）
- **Leader Board機能**: Submission評価結果の登録・ランキング表示はEvaluatorの責務（User Story 3削除）

## Clarifications

### Session 2025-10-22

- Q: DuckDBとSQLiteのどちらをデータストアとして使用するか？ → A: DuckDBを採用。理由：ネイティブJSON型、並列書き込み（MVCC）、高速分析クエリ、Pandas統合。
- Q: SQLAlchemyを使用してデータベースマッピングを行うか？ → A: 初期段階では不要。DuckDBに直接SQL実行する方がシンプル。将来PostgreSQL移行時に検討。
- Q: データベース分割（チームごとに別DBファイル）を検討するか？ → A: 不採用。Leader Board統合が困難、管理が煩雑。DuckDBのMVCCで並列書き込み対応する。
- Q: Message Historyの保存形式はどうするか？ → A: DuckDBのネイティブJSON型を使用。Pydantic AIの`to_jsonable_python()`でJSON化し、`ModelMessagesTypeAdapter.validate_json()`で復元。
- Q: Member Agent数は固定か可変か？ → A: 可変。チームごとにMember Agent数は異なり、TOMLファイルで設定される。上限は親仕様（001-mixseek-core-specs）のFR-014で定義されたmember_agent_limit（デフォルト15）に従う。
- Q: Parquetエクスポートのファイル管理戦略はどうすべきか？ → A: 日付パーティショニング（1日1ファイル、retention設定可能）。ただし、エクスポート実行判定と自動削除はOrchestration Layerの責務であり、本仕様ではエクスポート可能なデータ構造提供のみを扱う。
- Q: オーケストレーション処理完了の定義は？ → A: Orchestration Layerの責務であり、本仕様の範囲外。本仕様ではデータ保存・読み込みインターフェースのみ提供する。
- Q: Member Agent応答待機の最大時間はどうすべきか？ → A: Member Agent個別にタイムアウト設定。各Member AgentのTOML設定で実行タイムアウトを定義可能とし、タイムアウト超過時はそのAgentを失敗として扱う。
- Q: データベース書き込み失敗時のリトライ間隔はどうすべきか？ → A: エクスポネンシャルバックオフ（1秒、2秒、4秒）。一時的な競合は短時間で回復し、深刻な障害は早期検出できる。
- Q: Leader Boardで同スコアの場合の表示順序は？ → A: 作成日時（早い順）。先に完了したチームを優先表示し、実行順序の公平性を保つ。
- Q: 仕様書内の具体的な数値（10チーム、5ラウンド等）は固定値か？ → A: すべて例示であり、設定可能。チーム数は親仕様のmax_concurrent_teams設定に従い、ラウンド数はmax_rounds設定に従う。仕様書内の数値はテストシナリオの代表例。
- Q: データベースファイルとアーカイブディレクトリのパスは？ → A: 環境変数`MIXSEEK_WORKSPACE`で管理。データベース: `$MIXSEEK_WORKSPACE/mixseek.db`、アーカイブ: `$MIXSEEK_WORKSPACE/archive/`。環境変数未設定時は即座にエラー終了し、設定方法を示すメッセージを出力（憲章Article 9準拠、specs/005-command準拠）。
- Q: ディレクトリアクセス失敗時の処理方針は？ → A: フォールバック禁止（憲章Article 9準拠）。書き込み権限エラー、ディスク容量不足等の場合は、即座にエラー終了し、原因特定可能な詳細ログ（パス、権限、利用可能容量等）を出力する。暗黙の代替処理は一切行わない。
- Q: 複数チームの並列実行は本仕様のスコープか？ → A: はい。親仕様（001-mixseek-core-specs FR-002）で定義された複数チーム並列実行を前提とし、本仕様ではDuckDB MVCCによる並列書き込み対応（ロック競合なし）を実現する。これはLeader Agent データ永続化の中核要件。
- Q: Leader Agentが生成するSubmissionには、個別Member応答が含まれるか？ → A: はい。SubmissionのcontentフィールドにはMemberSubmissionsRecordの構造化データ（`List[MemberSubmission]`）がJSON形式で格納される。ラウンドコントローラがこれを整形（Markdown連結等）して次ラウンドで各Memberに共有することで、実質的にTUMIX論文のメッセージ共有方式と同等となる（親仕様FR-006の「Submissionの結果」の解釈）。
- Q: ParquetエクスポートでJSON型カラムはどう扱われるか？ → A: JSON型カラム（message_history、member_submissions_record等）は、JSON文字列（STRING型）としてParquetファイルに保存される。Parquetから直接クエリする際は、`json_extract()`関数または`CAST(column AS JSON)`でJSON型に変換すればJSON演算子（`->`, `->>`）が使用可能。DuckDBはParquetファイルを直接クエリできるため、アーカイブデータへの分析クエリも実行可能（`FROM 'archive/*/history.parquet'`）。
- Q: デバッグ・テスト用のCLIコマンドは必要か？ → A: はい。Member Agent（specs/027）と同様に、`mixseek team`コマンドを実装する。チーム単位での記録・永続化をテストできる。開発・テスト専用である旨を実行時に警告表示（憲章Article 2準拠）。
- Q: Parquetエクスポート機能の実装スコープは？ → A: 本仕様ではスコープ外。DuckDB構造がエクスポート可能であることは保証するが、COPY文実行、ファイル管理、日付パーティショニング等はOrchestration Layerの責務（Out of Scope明記）。
- Q: チーム設定TOMLでMember Agent TOMLファイルを参照できるか？ → A: はい（DRY原則、憲章Article 10準拠）。`[[team.members]]`セクションで、インライン定義（全設定を直接記述）と参照形式（`config = "path/to/agent.toml"`）の両方をサポート。既存のMember Agent TOMLファイルを再利用でき、設定の重複を避ける。参照形式では、agent.tomlのパスを指定するだけでMember Agent設定を読み込む。

### Session 2025-10-23

- Q: `mixseek team`の`team_id`生成方式は？ → A: タイムスタンプベース（`dev-test-{timestamp}`）。各実行が独立したレコードとして保存され、UNIQUE制約による上書きを防ぐ。本番環境では固定team_idを使用するが、テストコマンドでは各実行を独立管理する。
- Q: DuckDBのIDENTITY構文は？ → A: `CREATE SEQUENCE` + `DEFAULT nextval()`を使用。`GENERATED BY DEFAULT AS IDENTITY`構文はDuckDB 1.4.1で非対応のため、シーケンスベースの自動インクリメントに変更。
- Q: 統合処理の責務範囲はどうすべきか？ → A: ラウンドコントローラが統合処理（複数ラウンド間の統合、応答整形）全体を管理し、Leader Agentは単一ラウンド内のMember応答の記録のみ担当。Leader Agentは前ラウンドを意識しない独立した設計とする。
- Q: MemberSubmissionのリソース使用量フィールドの型は？ → A: Pydantic AI RunUsageモデルをそのまま使用。型安全性と互換性が保証され、Pydantic AIエコシステムとのシームレスな統合が可能。カスタム型定義による変換コストを回避。
- Q: 単一ラウンド内の記録を表すモデル名は？ → A: `MemberSubmissionsRecord`を使用。「Aggregated」は統合処理を連想させるため、Leader Agentの責務（記録のみ）を明確にする名前に変更。ラウンドコントローラの統合処理との混同を回避。
- Q: データ永続化のトランザクションスコープは？ → A: Message HistoryとMemberSubmissionsRecordを単一トランザクションで保存。データ整合性を保証し、片方のみ保存される不整合状態を防ぐ。DuckDB MVCCにより並列書き込みはブロックされない。
- Q: Member Agent並列実行の失敗処理戦略は？ → A: 個別Agentの失敗を許容し、最低1つ成功すれば継続（現在の仕様と一貫）。部分的な成功から価値を得られる。全Agent失敗時のみチーム失格とし、堅牢性と品質のバランスを保つ。
- Q: Member応答の保存形式は連結文字列か構造化データか？ → A: 構造化データ（`List[MemberSubmission]`）のみを保存。Pydantic AIにとって理想的な型安全性、メタデータ完全保持、JSON互換性を実現。Markdown連結などの整形処理はRound Controllerに委譲し、Leader Agentは構造化データの記録のみを担当。
- Q: 「集約」という用語の使い方は？ → A: 用語を責務に応じて明確化。Leader Agentの責務は「記録」、Round Controllerの責務は「統合処理」「整形処理」。リソース使用量の合計は「集計」。「集約」は曖昧なため、文脈に応じて適切な用語を使用する。
- Q: Leader Agentのsystem_instructionはTOML設定可能か？ → A: はい。チーム設定TOMLの`[team.leader]`セクションでLeader Agent固有のsystem_instructionを定義可能。未設定の場合はデフォルトsystem_instructionを使用する。Member Agent（specs/027）と同様の設計で、旧称のsystem_promptは指定時にPydantic AIの`system_prompt`へ渡す。
- Q: Member Agent実行方式は全Agent並列実行か動的選択か？ → A: 動的選択（Agent Delegation）を採用。Leader AgentがToolを通じて必要なMember Agentのみを選択・実行する。TUMIX論文は参考にするが遵守しない。Pydantic AIのAgent Delegationパターンに従い、リソース効率と柔軟性を優先。全Agent並列実行方式は破棄。

### Session 2025-10-24

- Q: FR-027（前ラウンド指定時の整形処理）はLeader Agentの責務か？ → A: いいえ。前ラウンド結果の整形処理（Markdown連結、評価フィードバック統合等）はRound Controllerの責務である。Leader Agentは単一ラウンド内の構造化データ記録のみを担当し、前ラウンドを意識しない独立した設計とする。FR-027を削除し、FR-028以降の番号を繰り上げた。
- Q: User Story 6（Round 2シミュレーション）とFR-026の取り扱いについて → A: 完全に削除し、Out of Scopeに移動する。Round 2シミュレーション機能（前ラウンド結果の読み込み・整形・統合）はRound Controllerの責務であり、Leader Agent仕様には含めない。Round Controllerの実装後にシミュレーション可能とする。
- Q: Success Criteria SC-010（Round 2シミュレーション）の取り扱いは？ → A: 削除する。User Story 6削除に伴い、対応するSuccess Criteriaも削除し、番号を再採番した。SC-003、SC-007（Leader Board関連）もEvaluator責務のため削除した。
- Q: Clarifications Session 2025-10-22の「Round 2シミュレーション」記述について → A: 削除する。User Story 6削除により、Session 2025-10-22の関連記述（`--previous-round`、`--load-from-db`オプション等）は矛盾するため、Session 2025-10-24の決定で完全に置き換えた。

### Session 2025-10-28

- Q: 失敗したMember Agent応答を記録結果に含めるべきか？ → A: はい。成功・失敗の両方を記録し、失敗にはERRORステータスとエラー詳細を保持する。
- Q: Leader Agentのsystem_instructionが空文字列の場合の扱いは？ → A: 空文字列を許容し、Leader Agentはsystem_instructionなしで実行する。暗黙のデフォルト文言は補わない。

### Session 2025-10-29

- Q: Leader Agentの`system_instruction`をTOML設定で省略した場合の挙動は？ → A: 既存のデフォルトsystem_instructionを自動適用し、後方互換性を維持したまま正常動作させる。
- Q: `system_instruction`と旧`system_prompt`が両方指定された場合の扱いは？ → A: `system_instruction`はPydantic AIの`instructions`として適用し、`system_prompt`値も同時にPydantic AIの`system_prompt`へ渡す。両方を指定した場合でもエラーとせず併用を許可する。
- Q: Leader AgentはMember Agentが未定義（0件）のチーム設定を受理すべきか？ → A: はい。Member Agentが0件でも設定エラーとせず、Leader Agent単体で処理し、記録結果のMemberSubmissionsRecordは空リストとして保存する。

### Session 2025-10-30

- Q: `--output-format json`にMessage Historyを含めるべきか？ → A: `--output-format json`に`message_history`フィールドを追加し、Leader AgentのMessage History（`result.all_messages_json()`）を含める。これにより、JSON出力でも完全な対話履歴（ツール呼び出し、中間推論）を取得でき、デバッグ・監査が容易になる。
- Q: Member AgentのMessage HistoryをLeader Agentでどう扱うべきか？ → A: Member AgentのMessage Historyを統合して記録する（`--save-db`でDuckDB保存、`--output-format json`で出力に含める）。これにより、Member Agentの内部動作（ツール呼び出し、中間推論、リトライ履歴）を完全に記録でき、デバッグ・監査・改善が可能になる。
- Q: FR-023の`message_history`フィールドは何を含むべきか？ → A: Leader AgentとMember AgentのMessage Historyを統合した完全な対話履歴を単一の`message_history`フィールドに含める。実装詳細（`result.all_messages_json()`）ではなく、要求事項として明確に記述することで誤読を防ぐ。
- Q: FR-034のMessage History「統合」の具体的な方法は？ → A: Leader AgentとMember Agentの対話の因果関係（どのツール呼び出しがどのMember Agent実行を引き起こしたか）を保持し、デバッグ・監査時に時系列に沿った再現が可能な形式で統合する。タイムスタンプソートやネスト構造などの具体的な実装方法は要求事項（因果関係保持+時系列再現性）を満たす範囲で実装者に委ねる。
- Q: MemberSubmission.all_messagesはRoundHistory.message_historyと重複するのでは？ → A: 重複しない。Pydantic AIのAgent Delegationパターンでは、Leader AgentのMessage HistoryにはMember Agent内部のメッセージ（SystemPrompt、ツール呼び出し、中間推論等）は含まれず、Tool Returnとして応答テキストのみが記録される。MemberSubmission.all_messagesはLeader Agentでは見えないMember Agent内部の動作を補完するために必要であり、完全なデバッグ・監査のために両方の履歴が必要となる。

## Success Criteria

### Measurable Outcomes

- **SC-001**: 複数チームが並列実行時、全てのMessage History（Leader AgentとMember Agentの完全な対話履歴）がロック競合なくデータベースに保存される（例：10チーム×5ラウンド=50件）
- **SC-002**: 複数のMember Agent（一部失敗含む）実行時、成功・失敗の両応答がステータス付きで記録結果に含まれ、Agent名ラベル付きで区別できる（例：3 Agent中1失敗→3件記録、失敗1件はERRORステータス）
- **SC-003**: データベースから読み込んだMessage HistoryがPydantic AI形式に100%正確に復元される（型チェック含む）
- **SC-004**: 複数チームが同時実行時、全てのデータが正常に保存される（並列書き込みが機能的に動作）
- **SC-005**: 記録処理において、全Member Agentのトークン使用量が正しく合計され、Pydantic AI RunUsage互換形式で記録される
- **SC-006**: `mixseek team`コマンドが、チーム設定TOMLを読み込み、Agent Delegationで必要なMember Agentのみを実行し、記録結果を出力する
- **SC-007**: コマンド出力（JSON/テキスト）が、記録結果の全必須情報（成功数、失敗数、構造化データ、リソース使用量）を含む。JSON出力形式では、さらにLeader AgentとMember Agentの両方のMessage History（完全な対話履歴）も含む
- **SC-008**: Member Agentが0件のチーム設定で`mixseek team`コマンドを実行した場合、Leader Agentが単体で応答を生成し、MemberSubmissionsRecordが空リストとして保存される

## Assumptions

- DuckDBバージョン1.0以降を使用（安定版、MVCC完全サポート）
- 仕様書内の具体的な数値（10チーム、5ラウンド、50件等）はテストシナリオの代表例であり、実際の値はTOML設定で可変
- 同時実行チーム数は通常5-50の範囲内（それ以上の場合はPostgreSQL移行を検討）
- 各Member Agent応答は通常1,000-5,000文字程度（10,000文字超は例外的）
- データベースファイルは単一ノードで実行（分散環境は想定外）
- Pydantic AIのMessage History構造は後方互換性を維持（マイナーバージョンアップで構造変更なし）
- Leader Boardの可視化はJupyter NotebookまたはDashboard経由（Web UIは別機能）
- JSON内部クエリ機能はDuckDB標準機能のみ使用（拡張なし）
- ParquetエクスポートはOrchestration Layerが実行する（本仕様はエクスポート可能なインターフェース提供のみ）
- 環境変数`MIXSEEK_WORKSPACE`は必ず設定されている前提（未設定時は即座にエラー終了、デフォルト値による暗黙の代替処理は禁止）
- SubmissionのcontentフィールドにはMemberSubmissionsRecordの構造化データ（`List[MemberSubmission]`）がJSON形式で格納され、ラウンドコントローラが整形して次ラウンドで活用する
- TUMIX論文は参考にするが、全Member Agent並列実行方式は採用しない。Agent Delegationによる動的選択を優先し、リソース効率と柔軟性を重視する
- Leader AgentのLLMがMember Agent選択を自律的に判断するため、同じプロンプトでも選択されるMember Agentが異なる可能性がある（非決定的動作）

## Out of Scope

以下は本仕様の対象外です：

### Orchestration Layer責務（別仕様で定義）

- **セッション完了判定**: オーケストレーション処理完了のタイミング定義
- **Parquetエクスポート機能**: DuckDB COPY文によるParquetエクスポート、日付パーティショニング管理、APPENDモード制御、JSON型カラムの扱い（本仕様ではエクスポート可能なDB構造提供のみ）
- **データベース初期化の実行**: エクスポート後のDELETE + VACUUM実行タイミング
- **アーカイブ自動削除**: 保持期間超過ディレクトリの削除ポリシーと実行
- **セッションライフサイクル管理**: セッション開始・完了の全体フロー

### Round Controller責務（別仕様で定義）

- **複数ラウンド間の統合処理**: 前ラウンド結果の統合、評価フィードバックの適用、次ラウンドプロンプトの生成
- **ラウンド間状態管理**: 前ラウンドデータの読み込み、ラウンド進行制御
- **応答整形処理**: 構造化データ（`List[MemberSubmission]`）からMarkdown連結、JSON出力、表形式などの整形済みコンテンツを生成
- **最終統合コンテンツの生成**: 複数ラウンドのSubmissionを統合した最終コンテンツの生成
- **Round 2シミュレーション機能**: 前ラウンド結果の読み込み、整形処理、評価フィードバック統合はRound Controllerの責務であり、Leader Agent仕様には含まない（User Story 6削除、FR-026/FR-027削除に伴う）

### 他コンポーネント責務

- **Leader Agentのタスク分解ロジック**: 別仕様で定義（親仕様FR-004の詳細）
- **Evaluatorの実装**: 評価スコアとフィードバック生成は別機能（親仕様FR-008, FR-009）
- **Leader Board機能**: Submission評価結果の登録、スコアランキング表示、チーム統計集計はEvaluatorの責務であり、Leader Agent仕様には含まない（User Story 3削除に伴う）
- **Round Controllerの終了判定**: ラウンド終了条件は別仕様（親仕様FR-011）

### 将来拡張・技術選択

- **PostgreSQLへの移行**: 初期段階ではDuckDBのみ対応
- **SQLAlchemyによるORM**: 直接SQL実行のみ対応
- **Message Historyの要約処理**: 長文応答の自動要約は将来拡張
- **Leader Boardの可視化UI**: Pandas DataFrameまでサポート、グラフ描画は利用者側で実装
- **リソース制限の強制**: リソース使用量の記録のみ、上限超過時の強制停止は別機能（親仕様FR-012）
- **データベースバックアップ**: ファイルシステムレベルのバックアップに依存
- **マルチノード分散実行**: 単一ノードのみ対応

## Configuration Example

### チーム設定TOML例

```toml
[team]
team_id = "research-team-001"
team_name = "Advanced Research Team"
max_concurrent_members = 5

[team.leader]
# Leader Agent固有のsystem_instruction（オプション）
system_instruction = """
あなたは研究チームのリーダーエージェントです。
タスクを分析し、以下のMember Agentから適切なものを選択して実行してください：

- delegate_to_analyst: 論理的分析・データ解釈が必要な場合に使用
- delegate_to_web_searcher: 最新情報のWeb検索が必要な場合に使用
- delegate_to_summarizer: 情報を簡潔にまとめる必要がある場合に使用

各Member Agentは独立して実行されます。必要に応じて複数のAgentを順次呼び出すことができます。
"""

# Member Agent 1: インライン定義
[[team.members]]
agent_name = "analyst"
agent_type = "plain"
tool_name = "delegate_to_analyst"  # Leader AgentのTool名
tool_description = "論理的な分析・データ解釈を実行します。統計分析や論理推論が必要な場合に使用してください。"
model = "gemini-2.5-flash-lite"
temperature = 0.7
max_tokens = 2048
system_instruction = "あなたは論理的な分析を得意とするアナリストです。"

# Member Agent 2: 参照形式（DRY準拠）
[[team.members]]
config = "configs/agents/web-search.toml"
tool_name = "delegate_to_web_searcher"  # Tool名は上書き可能
tool_description = "Web検索で最新情報を収集します。"

# Member Agent 3: インライン定義
[[team.members]]
agent_name = "summarizer"
agent_type = "plain"
tool_name = "delegate_to_summarizer"
tool_description = "情報を簡潔にまとめます。長文の要約や重要ポイントの抽出に使用してください。"
model = "gemini-2.5-flash-lite"
temperature = 0.3
max_tokens = 1024
system_instruction = "あなたは情報を簡潔にまとめる専門家です。"
```

**注意事項**:
- `[team.leader]`セクションは**オプション**です。未設定の場合はデフォルトsystem_instructionが使用されます。
- `system_instruction = ""`を指定した場合、Leader Agentはsystem_instructionなしで実行する（空文字列は明示的に許容され、暗黙の補完は行わない）。
- `[[team.members]]`は配列セクションで、複数のMember Agentを定義できます。
- Member Agentはインライン定義（全設定を直接記述）と参照形式（`config = "path/to/agent.toml"`）の両方をサポートします。
- Member Agentを1件も指定しない構成も許容され、その場合はLeader Agent単独で実行される。
- **Agent Delegation（重要）**: 各Member AgentはLeader AgentのToolとして自動登録されます。`tool_name`と`tool_description`でToolの名前と説明を定義します。Leader Agentはタスクを分析し、適切なToolを選択してMember Agentを動的に実行します。
- **並列実行からの変更**: 従来の「全Member Agentを並列実行」方式は破棄され、Leader Agentが必要なMember Agentのみを動的に選択・実行する方式（Agent Delegation）に変更されました。リソース効率と柔軟性が向上します。
