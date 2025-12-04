# 用語集

```{glossary}
Team（チーム）
  1名のLeader Agentと複数名のMember Agentで構成される分析単位。複数チームが同一タスクに並列参加する。

Leader Agent
  User Promptを受けてタスク分解・割当・進捗管理・統合を担当するチーム責任者。
  Pydantic AIのAgent Delegationパターンに従い、Toolを通じて必要なMember Agentを動的に選択・実行する。
  選択されたMember Agentの成果を統合し、所定フォーマットの最終回答（Submission）を作成する。

Member Agent
  データ取得、Web検索、思考など、単一の限定領域に特化した作業担当エージェント。
  すべてのMember AgentはBaseMemberAgent基底クラスを継承し、Pydantic AI Toolとして登録される。
  Leader AgentがAgent Delegationパターンで動的に選択・実行し、その成果を返す。
  システム標準型（plain、web-search、code-exec）とユーザー作成型がある。

BaseMemberAgent
  すべてのMember Agentが継承する抽象基底クラス。
  execute(task, context)メソッドを実装し、Leader AgentからのToolset呼び出しに対応する。
  システム標準型とユーザー作成型の両方で共通のインターフェースを提供する。

`system_prompt`
  Pydantic AIに渡されるシステムプロンプト文字列。メッセージ履歴に保持され、他エージェントに引き継がれる永続的なガイドラインを定義する。Agentの設定ファイル(TOML)では、オプションの`system_prompt`フィールドとして設定し、未指定の場合は省略可能。

`instructions`
  Pydantic AIで推奨される指示設定API。各実行時に現在のエージェントへ適用され、履歴引き継ぎ時は常に最新値で再評価される。MixSeek-CoreではLLM挙動制御の主経路として扱い、具体的な役割・制約・出力方針を記述する。

`system_instruction`
  MixSeekで`instructions`を指す別名。チームTOMLの`system_instruction`フィールドからPydantic AIの`instructions`にマッピングされ、`system_prompt`と併用した場合でも両方の指示がモデルに渡される。

Tool / Toolset
  Pydantic AIにおけるエージェント間通信の仕組み。
  各Member AgentはToolとして登録され、Leader Agentが@leader_agent.toolデコレータでアクセスする。
  Agent Delegationパターンの基盤となる。

Agent Delegation
  Leader AgentがToolを通じて必要なMember Agentを動的に選択・実行するPydantic AIパターン。
  全Member Agent並列実行ではなく、タスクに応じた必要最小限のAgent選択によりリソース効率と柔軟性を実現する。

User Prompt
  ユーザが課すタスクの定義。目的、入力条件、制約、期待する出力形式などを含み得る。

Submission
  チームが1回の提出として出す最終アウトプット。User Promptの指定に応じて、回答本文となるmd・csv・jsonといった形式が想定される。
  contentフィールドにはMemberSubmissionsRecordの構造化データ（各Member Agent応答のリスト）がJSON形式で格納される。
  Round Controllerに送られ、Evaluatorによる評価対象となる。

MemberSubmission
  個別Member Agent応答を表す軽量データモデル。
  Agent名、種別、コンテンツ、ステータス、エラーメッセージ、リソース使用量（Run Usage）、タイムスタンプを保持する。

MemberSubmissionsRecord
  単一ラウンド内の複数Member Agent応答を構造化データとして記録するモデル。
  ラウンド番号、チームID、全応答リスト（List[MemberSubmission]）、成功/失敗応答リスト、統計情報、合計リソース使用量を保持する。
  Markdown連結などの整形処理はRound Controllerが実施し、Leader Agentは構造化データの記録のみを担当する。

Round（ラウンド）
  各チームが分析を行い、Submissionを1回行うまでの一連の過程。
  チームごとに独立に進行し、各ラウンドの状態（Submission、評価スコア、フィードバック、Message History）はRound Stateとして保持される。
  Message HistoryはDuckDBにJSON形式で永続化され、次ラウンドでは前ラウンドのSubmission結果と評価フィードバックのみを引き継ぐ。

Round State
  各ラウンドの完全な状態を保持するdataclass。
  Submission、評価スコア、フィードバック、Message Historyを含み、DuckDBに永続化される。
  長期実行時のメモリ負荷を削減する。

Message History
  Pydantic AI形式のメッセージ履歴。
  Leader AgentとMember Agent間のやり取り、ツール実行結果などを記録する。
  DuckDBのネイティブJSON型で永続化され、ModelMessagesTypeAdapter.validate_json()でPydantic AI Message構造に復元される。

Round Controller
  各チームに対して個別にインスタンス化され、ラウンド制御を担う。
  対応するチームの各ラウンドで、Submissionの受領、Evaluatorを経由した採点済みスコアおよび評価コメントの返却を行う。
  Message HistoryとMemberSubmissionsRecordをDuckDBに単一トランザクションで永続化し、MVCCにより並列実行チームとのロック競合を回避する。
  グローバルなラウンド継続の設定に従ってラウンドの継続/終了を判定するほか、チームから終了シグナルを受け取った場合にもラウンドを終了し、Orchestration Layerに通知する。

Evaluator
  指定した複数の評価観点・アルゴリズムによってSubmissionの定量・定性評価を行い、評価値と評価コメントを返す。
  定性評価はLLM as a Judge形式でAPIによって行う。
  評価コメントは定性評価時のみ提供される。

Leader Board
  チーム、ラウンドごとの提出内容・スコア・評価コメントの履歴を管理。
  全チーム横断で最高スコアのランキングを保持・提供する。

LB MCP
  各チームに対し、自チームのSubmission履歴と、横断の最高スコアランキング表を提供するMCPサーバ。

Orchestration Layer
  全チームへ同一のUser Promptを配布し、並列実行・リソース配分・タイムアウト・再試行などの実行管理を行う。

Viewer
  ユーザに各チームの稼働状況、提出物、スコア、評価コメント、最終出力、ランキング、Verificatorのレポートといった情報を可視化して提供するUI。

Score（スコア）
  Evaluatorによって採点されたSubmissionの評価値。Leader Boardに記録されランキングの基礎となる。

Evaluator Comment（評価コメント）
  採点に付随する講評・改善提案。次ラウンドの方針更新やタスク再割当てに利用。

Ranking（ランキング）
  Leader Boardが管理する、各チームの最高スコアに基づく順位。

Verificator
  エージェントの挙動に問題がないかをログを元に診断する。
  MCP呼び出し成功/失敗回数、Member Agentの呼び出し回数やそのラウンドごとの変遷、スコア履歴の可視化といった内容が含まれうる。
  あくまでも挙動の診断に特化し、Submissionの評価に関する内容はEvaluatorの責務として分離する。

Pydantic AI
  エージェント実装の基盤フレームワーク。
  Agent Delegation、Tool、Usage Limits、Run Usageなどの機能を提供し、型安全なエージェント開発を実現する。
  Leader AgentおよびMember Agentの実装に使用される。

DuckDB
  データ永続化に使用する分析指向データベース。
  ネイティブJSON型、MVCC（並列書き込み対応）、高速分析クエリ、Pandas統合を提供する。
  Message HistoryやMemberSubmissionsRecordをJSON形式で永続化する。

MVCC
  Multi-Version Concurrency Controlの略。
  DuckDBが採用する並列書き込み制御方式で、複数チームが同時にデータベースへ書き込む際のロック競合を回避する。

Usage Limits
  Pydantic AIのリソース使用量制限機能。
  1回のagent.run()呼び出しに対するトークン数、リクエスト数、ツール呼び出し数を制限する。
  超過時は警告とリトライ、リトライ失敗でラウンド失敗となる。

Run Usage
  Pydantic AIのリソース使用量測定データ。
  input_tokens、output_tokens、requestsなどを記録し、各Member Agentのリソース使用量を集計する。

MIXSEEK_WORKSPACE
  ワークスペースディレクトリを指定する環境変数。
  データベースファイル（$MIXSEEK_WORKSPACE/mixseek.db）、ログ、設定ファイル、テンプレートなどが配置される。

Docker
  開発環境の構築に使用するコンテナ技術。
  Python 3.13.9、uv、AI開発ツール（Claude Code、Codex、Gemini CLI）を含む再現可能な開発環境を提供する。

uv
  Pythonパッケージマネージャー。
  高速な依存関係解決とインストールを実現し、MixSeek-Coreのパッケージ管理に使用される。

TOML
  設定ファイル形式。
  チーム設定、Member Agent設定、System Promptなどをproject.toml、agent.tomlとして定義する。

ruff
  Pythonのリンターおよびフォーマッター。
  憲章Article 8のコード品質基準に従い、ruff check --fix . && ruff format . の実行が必須。

mypy
  Pythonの静的型チェッカー。
  憲章Article 16の型安全性要件に従い、strict modeでの型チェックが必須。

Web Search Tool
  Pydantic AIが提供するWeb検索機能。
  Member Agent（web-search）に統合され、最新情報の取得とリアルタイムデータ分析を可能にする。

Code Execution Tool
  Pydantic AIが提供するコード実行機能。
  Member Agent（code-exec）に統合され、数値計算やデータ分析タスクを実行する。
  現在はAnthropic Claudeモデルのみで利用可能。

Modality
  モデルの機能分類（chat、image-generation、embedding、audio等）。
  MixSeek-Coreでは会話モデル（chat modality）のみを使用し、他のモダリティは検証時に自動的に除外される。

Compatibility
  モデルがMixSeek-Coreの各エージェント種別（plain/web-search/code-exec）に対応しているかの互換性判定。
  プロバイダー別、Pydantic AIカテゴリ別に技術的な利用可否を事前評価する。

Validation Metrics
  モデル検証の測定値。
  成功/失敗ステータス、レイテンシ統計（P50/P95/P99）、入出力トークン数、再試行回数、推定コストを含む。
