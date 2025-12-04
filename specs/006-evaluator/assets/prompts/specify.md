# 概要

AIエージェントが出力した結果を評価するためのEvaluatorコンポーネントの実装を行う

ブランチ名: 022-mixseek-core-evaluator
親仕様: specs/001-specs

# 要件

- ブランチ名は上述の命名とする
- 親仕様に厳密に従う
- 評価指標はユーザがtomlを介して複数指定可能
- coreパッケージ組み込みの評価指標として、下記評価指標セクションの観点でLLM-as-a-Judgeを実装する
- LLM-as-a-Judgeによる評価はPydantic AIの評価モジュールを利用して実装する
- 各評価指標はPython関数として実装し、必要に応じてカスタム評価指標をユーザが追加実装できるようにする
- 各評価指標は0~100点のスコアを返す
- 評価指標の集約方法は加重平均とし、ユーザが重みをtomlで指定できるようにする
    - 重みのデフォルト値は均等とする
- 複数のチームの出力を同時に評価できるようにする
- Evaluatorへの入出力はPydanticモデルで定義する

# 組み込み評価指標

- clarity_coherence / coherence
    - 回答が読みやすい構成か
    - 回答の内容が論理的に一貫しているか
- coverage
    - ユーザクエリに対して、期待される情報、必要な情報を漏れなく含んでいるか
- relevance
    - 回答がユーザクエリの内容や意図に合致した内容であるか

# 技術スタック

次のPythonパッケージを検討する

- Pydantic AI: https://ai.pydantic.dev/

---

# 追加要件

- tomlで各評価指標を識別するとき、評価指標群が実装されるのは単一のディレクトリ配下であることを前提とし、クラス名を指定するだけで評価指標を特定できるようにする
- tomlで設定する各評価指標で、metrics.llmとして、オプションとして以下の項目を指定できる
    - `model`: 指定された場合かつLLM-as-a-Judge評価指標が選択されている場合、使用するLLMモデルを上書きできる
    - `system_instruction`: 指定された場合かつLLM-as-a-Judge評価指標が選択されている場合、instructionを上書きできる
    - `temperature`: 指定された場合かつLLM-as-a-Judge評価指標が選択されている場合、temperatureを上書きできる(デフォルト0.0)
    - `max_tokens`: 指定された場合かつLLM-as-a-Judge評価指標が選択されている場合、max_tokensを上書きできる(デフォルトNone)
    - `max_retries`: 指定された場合かつLLM-as-a-Judge評価指標が選択されている場合、max_retriesを上書きできる(デフォルト3)
- metrics.modelが指定されない場合を許容する
    - LLM-as-a-Judge評価指標の場合はすべてデフォルト値を使用する 
- metrics.modelが指定されているが、LLM-as-a-Judge評価指標以外が選択されている場合は無視する
- 既に定義されている3つの評価指標に加えて、instructionを上書きしてカスタマイズする前提の評価指標 `LLMPlain` を追加する
- tomlのグローバル設定として、[llm_default]セクションを追加し、以下の項目を指定できるようにする(すべてオプションで、下記の値はデフォルト値)
    - `model`: anthropic:claude-sonnet-4-5-20250929
    - `temperature`: 0.0
    - `max_tokens`: None
    - `max_retries`: 3
