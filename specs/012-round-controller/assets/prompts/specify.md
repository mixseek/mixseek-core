# 概要

コア仕様に従って、Round Controllerを実装する

# 重要なガイドライン

- あなたの思考過程、設計書等のすべてのアウトプットを日本語で記述すること
- コア仕様 `001-mixseek-core-specs` に忠実に従うこと
- 前提セクションに記述した実装済みコンポーネントの仕様を必ず参照すること

# 前提

- 実装済みコンポーネント
    - コア仕様: `001-mixseek-core-specs`
    - Evaluator: `022-mixseek-core-evaluator`
    - リーダーエージェント: `026-mixseek-core-leader`
    - メンバーエージェント: `009-member`
    - チームオーケストレーション: `025-mixseek-core-orchestration`

# 要件

- 各コンポーネントへの入出力はPydanticモデルで定義されているので、それらを活用する
- Round Controllerは各チームごとにそれぞれオーケストレータによってインスタンス化され、別プロセスで実行される
- ワークフローの概要は以下の通り
    1. オーケストレータからタスク定義（チームID、ユーザクエリ、メタデータ）を受け取る
    2. 対応するチームに入力するプロンプトを、チームの過去のSubmission情報、メタデータを含めて整形し、送信する
    3. チームからのSubmissionを受け取る
    4. SubmissionをEvaluatorに送信し、評価結果を受け取り、DuckDBに保存する
    5. 現在と過去すべてのSubmissionと評価結果をもとに、次のラウンドに進むべきかどうか判定する
        a. 数ラウンド先でこれ以上スコアが改善する見込みがあるかどうかをLLMによって判定
            - この実装は Evaluator コンポーネントの LLM-as-a-Judge 実装を参考にすること
        b. 最大ラウンド数に到達しているかどうかを確認
    6. 次のラウンドに進む場合は2に戻る
    7. 終了する場合は、最終結果を保存し、オーケストレータに通知する
- 各ラウンドの情報はDuckDBに `round_status`, `leader_board` テーブルとして保存する
    - 各ラウンドの進捗状況、ラウンドの開始・終了がわかるようにする
- テーブル定義は以下のカラムは必須だが、それ以外に必要なカラムやテーブルがあれば追加してもよい
- 以下の設定情報と追加で必要な項目をチーム横断のデフォルト値およびチームごとの上書き設定としてサポートする
    - 最大ラウンド数（デフォルト: 5ラウンド）
    - Submissionまでのタイムアウト時間（デフォルト: 5分）
- 設定管理は `022-mixseek-core-evaluator` コンポーネントの設定管理実装を参考にすること

## DuckDB テーブル定義

- `round_status`: テーブルはチームがどのように行動したかを記録する役割であり、以下のカラムを含む
    - `id`: 自動採番される一意なID
    - `team_id`: チームID
    - `team_name`: チーム名
    - `round_number`: ラウンド番号
    - `message_history`: チーム内でのやり取りの履歴（JSON形式）
        - エージェントの実装で実行ログの記録をサポートしているので、それを活用する
    - `created_at`: レコード作成日時
    - `updated_at`: レコード更新日時

- `leader_board`: 各チーム、各ラウンドのSubmissionと評価結果を記録する役割であり、以下のカラムを含む
    - `id`: 自動採番される一意なID
    - `team_id`: チームID
    - `team_name`: チーム名
    - `round_number`: ラウンド番号
    - `submission_content`: チームからのSubmission内容
    - `submission_format`: Submissionのフォーマット情報（デフォルト: md）
    - `score`: Evaluatorからの評価スコア
    - `score_details`: Evaluatorからの各評価指標のスコア内訳、コメント（JSON形式）
    - `final_submission`: 最終ラウンドのSubmissionかどうかを示すフラグ
    - `exit_reason`: ラウンド終了の理由（例: "max rounds reached", "no improvement expected" など）
    - `created_at`: レコード作成日時
    - `updated_at`: レコード更新日時