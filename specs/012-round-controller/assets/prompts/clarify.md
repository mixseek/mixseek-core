以下の項目を明確化してください。

- ラウンド継続判定に最小ラウンド数を追加する
- Round Promptは、将来的に Prompt Builder コンポーネントとして外部化することを想定する
    - 現時点ではRound Controller内で実装するが、拡張可能な設計にする
- 次ラウンド開始時には、チームのセッションやコンテキストを維持せず、毎回初期化することを明記する
- FR-006で、次ラウンド開始時にオーケストレータに制御を戻しているように見えるが、そうではなく、Round Controller内で完結することを確認する
    - オーケストレーションコンポーネントは、Round Controllerにタスクを投げた後は最終結果を受け取るまで待機するだけである
- Entityで、`TaskDefinition` ではなく、オーケストレーションコンポーネントから受け取る `OrchestratorTask` を使用する
- Round Controllerの最終的なアウトプットを明記する。問題なければ最終Submissionの `LeaderBoardEntry` とすれべよさそう？
- Entityで、 `ImprovementJudgement` は対応するテーブルを用意して記録するようにする
- Configファイルがない場合はログで警告しつつデフォルト設定を使用することを明記する
- Submissionが不正な形式の場合は、Submission失敗としてそのラウンドを処理し、LLMによる次ラウンド判定を省略し、次のラウンドを開始する
    - その際、過去のSubmissionの履歴として失敗した旨も含める

---

以下の項目を明確化してください。クリティカルな質問がない限りは、質問を省略してください。

- オーケストレータからの「タスク定義」という用語を「タスク」に変更する
- Round Controllerはconfig設定をもたないように修正する
    - tomlファイルによる設定はなし
    - チーム設定の上書きはなし
    - 設定情報はオーケストレータのタスクから受け取る
        - 受け取る情報は以下(Evaluatorのタイムアウトを除外)
            - 最大ラウンド数
            - 最小ラウンド数
            - 1ラウンドのSubmissionタイムアウト
            - 次ラウンド判定タイムアウト
- チームに渡すプロンプトに以下を含める
    - leader_boardで現在の各チームの最高スコアを並べたもの
    - そのチームが現在何位にいるか
- オーケストレータのタスクでexecution_id (単一のユーザクエリに紐づくID) を渡すようにする
- round_statusテーブルのスキーマを修正
    - message_historyを削除
    - execution_idを追加
- leader_board テーブルのスキーマを修正
    - execution_idを追加
- improvement_judgment テーブルをround_statusに統合
- RoundConfig, ImprovementJudgement Entityは削除

---

以下の項目を明確化してください。クリティカルな質問がない限りは、質問を省略してください。

- 最大ラウンド数のシステム的な上限(=10)を設ける
- Round Controllerに与えられるラウンド数などの追加設定は、デフォルト値が存在し、オーケストレータ設定TOMLで上書き可能にする
