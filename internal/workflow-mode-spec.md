## ワークフローモード MVP 設計草案

mixseek/mixseek-core#118 に対する設計提案。

### コンセプト

現在のチームモード（リーダーがLLM判断でメンバーを動的選択）に対し、**ワークフローモードはTOML定義の固定ステップでエージェント/関数を実行**する。ラウンド制御・評価・ストレージ層はそのまま活用。

```
現在:  Orchestrator → RoundController → LeaderAgent(LLM判断) → MemberAgents
新規:  Orchestrator → RoundController → WorkflowEngine(固定ステップ) → Executables
                                         ↑ ここだけ差し替え
```

核心は **ExecutionStrategy パターン** の導入。RoundControllerの実行部分をStrategy化し、チームモードとワークフローモードを同じインターフェースで扱う。

---

### Workflow TOML 形式

```toml
[workflow]
id = "research-pipeline"
name = "Research Pipeline"
include_all_context = true  # デフォ true。false なら各ステップへは直前1ステップの出力のみ伝播（サイズ制御）
final_output_format = "json"       # デフォ "json"。"text" なら最終ステップ出力を Markdown 整形

# Step 1: 情報収集（executors複数 → 並列実行）
[[workflow.steps]]
id = "gather"

[[workflow.steps.executors]]
name = "web-searcher"
type = "web_search"
system_instruction = "与えられたタスクに関する最新情報をWeb検索で収集してください。"
model = "google-gla:gemini-2.5-flash"

[workflow.steps.executors.tool_settings.web_search]
max_results = 15

[[workflow.steps.executors]]
name = "academic-searcher"
type = "custom"
system_instruction = "学術論文を検索し要約してください。"

[workflow.steps.executors.plugin]
agent_module = "mypackage.agents"
agent_class = "AcademicSearchAgent"

# Step 2: 整形（Python関数）
[[workflow.steps]]
id = "format"

[[workflow.steps.executors]]
name = "markdown-formatter"
type = "function"

[workflow.steps.executors.plugin]
module = "mypackage.formatters"
function = "format_as_markdown"

# Step 3: 統合（executors単一 → 直列実行）
[[workflow.steps]]
id = "synthesize"

[[workflow.steps.executors]]
name = "synthesizer"
type = "plain"
system_instruction = "前のステップの全結果を統合し、包括的なレポートを作成してください。"
model = "google-gla:gemini-2.5-flash"
max_tokens = 8192
```

**ルール:**
- `workflow.steps` は配列順に実行（順番）
- 各ステップ内の `executors` が複数なら並列実行、単一なら直列
- executorは `type` によって2系統に分かれ、**discriminated union** で受ける（`StepExecutorConfig = AgentExecutorSettings | FunctionExecutorSettings`）:
  - **Agent系** (`plain` / `web_search` / `custom`): 既存 `MemberAgentSettings` と同形の `AgentExecutorSettings`（`model` 必須、`plugin: PluginMetadata`（`agent_module` / `agent_class`））
  - **Function系** (`function`): 専用の `FunctionExecutorSettings`（`model` 不要、`plugin: FunctionPluginMetadata`（`module` / `function`））
- 既存 `MemberAgentSettings` / `PluginMetadata` をそのまま流用するとバリデーションが通らない（`model` 必須、`PluginMetadata.extra="forbid"`、`agent_class` 必須）。そのため **function executor は別スキーマに分離**する
- **トップレベル設定（`[workflow]` 直下）**:
  - `include_all_context: bool`（デフォ `true`）— 各ステップへ渡す `previous_steps` の範囲。`true` は全累積、`false` は直前1ステップのみ（詳細は「コンテキスト伝搬」節）
  - `final_output_format: "json" | "text"`（デフォ `"json"`）— 最終ステップの出力 = `submission_content` の整形方式（詳細は「最終ステップの出力（submission_content）」節）
- 最終ステップの出力を `final_output_format` に従って整形したものが `submission_content` になる
- MVPでは条件分岐はサポートしない

---

### orchestrator.toml との統合

```toml
[[orchestrator.teams]]
config = "configs/agents/team_general_researcher.toml"    # [team] → チームモード

[[orchestrator.teams]]
config = "configs/workflows/workflow_research.toml"       # [workflow] → ワークフローモード
```

**自動検出方式**: ConfigurationManagerがTOMLのトップレベルキー（`[team]` vs `[workflow]`）で判別。orchestrator.tomlのスキーマ変更は不要。

ただし**自動検出は「読込関数を分岐する」以上の対応が必要**。既存実装は `RoundController.__init__` / `Orchestrator.run` / preflight validator の各所で `load_team_config()` / `load_team_settings()` を**直接呼んでいる**。単に判別APIを足すだけではこれらの箇所が `[workflow]` ファイルで落ちる。詳細は後述「設定基盤への影響範囲」を参照。

---

### アーキテクチャ: Executable アダプターパターン

ワークフローステップの実行単位は「エージェント」ではなく **「`str → str` の変換」**。エージェントはその一種にすぎない。

```
                        ┌─────────────────────────────────┐
                        │  Executable (Protocol)           │
                        │  run(input: str) -> str          │
                        └──────────┬──────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
             AgentExecutable  FunctionExecutable  (将来拡張)
             委譲で保持 ↓      保持 ↓
          BaseMemberAgent    Callable[[str], str]
```

**ポイント**: 継承ではなくアダプターパターン。BaseMemberAgentもMemberAgentFactoryも一切変更しない。

#### Executable Protocol

```python
class Executable(Protocol):
    """ワークフローステップで実行可能なもの"""
    @property
    def name(self) -> str: ...

    @property
    def executor_type(self) -> str: ...

    async def run(self, input: str) -> ExecutableResult: ...


@dataclass
class ExecutableResult:
    """Executable実行結果。`MemberSubmission` の必須フィールドを全て満たす形で揃える。

    既存 `MemberSubmission` は status / usage: RunUsage / all_messages: list[ModelMessage]
    を必須で持つため（src/mixseek/agents/leader/models.py）、それらに直接写像できる型を採用する。
    Function executor は LLM呼び出しを伴わないため usage = RunUsage() / all_messages = []
    を既定値とする（後述「Submission契約への対応」参照）。
    """
    # フィールド名・値ドメインは既存 MemberSubmission と完全一致させる
    # （status は "SUCCESS" / "ERROR" の大文字リテラル、エラー文言は error_message）
    content: str
    execution_time_ms: float
    status: Literal["SUCCESS", "ERROR"] = "SUCCESS"
    error_message: str | None = None
    usage: RunUsage = field(default_factory=RunUsage)
    all_messages: list[ModelMessage] = field(default_factory=list)
```

#### AgentExecutable

```python
class AgentExecutable:
    """BaseMemberAgent → Executable アダプター"""
    def __init__(self, agent: BaseMemberAgent):
        self._agent = agent

    @property
    def name(self) -> str:
        return self._agent.agent_name

    @property
    def executor_type(self) -> str:
        return self._agent.agent_type

    async def run(self, input: str) -> ExecutableResult:
        # Executable境界ポリシー: 例外は全てここで吸収して ExecutableResult に変換する。
        # 既存 BaseMemberAgent.execute() は MemberAgentResult を返す契約だが、例外不捕捉
        # 保証はなく custom agent は任意実装のため、Function側と同じ境界で揃える。
        start = time.perf_counter()
        try:
            result = await self._agent.execute(input)
            return ExecutableResult(
                content=result.content,
                execution_time_ms=result.execution_time_ms,
                status=result.status.value.upper(),   # leader/tools.py:88 と同じ正規化
                error_message=result.error_message,
                usage=_to_run_usage(result.usage_info),  # dict → RunUsage 変換
                all_messages=result.all_messages,
            )
        except Exception as e:
            return ExecutableResult(
                content="",
                execution_time_ms=(time.perf_counter() - start) * 1000,
                status="ERROR",
                error_message=str(e),
                usage=RunUsage(),
                all_messages=[],
            )
```

#### FunctionExecutable

```python
class FunctionExecutable:
    """Python関数 → Executable アダプター"""
    def __init__(self, name: str, func: Callable[[str], str | Awaitable[str]]):
        self._name = name
        self._func = func

    @property
    def executor_type(self) -> str:
        return "function"

    async def run(self, input: str) -> ExecutableResult:
        start = time.perf_counter()
        try:
            if asyncio.iscoroutinefunction(self._func):
                content = await self._func(input)
            else:
                content = await asyncio.to_thread(self._func, input)
            return ExecutableResult(
                content=content,
                execution_time_ms=(time.perf_counter() - start) * 1000,
                status="SUCCESS",
                usage=RunUsage(),   # LLM未呼び出し → ゼロ値
                all_messages=[],    # 履歴なし
            )
        except Exception as e:
            # Executable.run は例外を漏らさない契約。ERROR をここで一旦 ExecutableResult に変換するが、
            # function の ERROR は engine 側（_execute_step）で検出され WorkflowStepFailedError に
            # 昇格されてワークフロー中断される（即失格ポリシー。詳細は後述「副作用と例外の境界」参照）
            return ExecutableResult(
                content="",
                execution_time_ms=(time.perf_counter() - start) * 1000,
                status="ERROR",
                error_message=str(e),
                usage=RunUsage(),
                all_messages=[],
            )
```

#### ビルド時にファクトリで振り分け

```python
def build_executable(config: StepExecutorConfig) -> Executable:
    # StepExecutorConfig = AgentExecutorSettings | FunctionExecutorSettings（discriminated union）
    if isinstance(config, FunctionExecutorSettings):
        # FunctionPluginMetadata（module / function）で受ける
        func = load_function(config.plugin.module, config.plugin.function)
        return FunctionExecutable(name=config.name, func=func)
    else:
        # AgentExecutorSettings は MemberAgentSettings と同形 → そのまま Factory に渡せる
        agent = MemberAgentFactory.create_agent(config.to_member_agent_config())
        return AgentExecutable(agent=agent)
```

---

### ExecutionStrategy パターン

```python
# round_controller/strategy.py

class ExecutionStrategy(Protocol):
    """ラウンド内の実行戦略を抽象化"""
    async def execute(
        self,
        user_prompt: str,
        deps: TeamDependencies,
    ) -> StrategyResult: ...

@dataclass
class StrategyResult:
    submission_content: str
    submissions: list[MemberSubmission]
    all_messages: list[ModelMessage]
    usage: Usage
```

- **`LeaderStrategy`**: 現在のcreate_leader_agent + runをラップ（既存動作の移植）
- **`WorkflowStrategy`**: WorkflowEngineを呼び出す

---

### WorkflowEngine

```python
class WorkflowEngine:
    async def run(self, user_prompt: str, deps: TeamDependencies) -> WorkflowResult:
        context = WorkflowContext(user_prompt=user_prompt)

        for step in self.config.steps:
            step_result = await self._execute_step(step, context, deps)
            context.add_step_result(step.id, step_result)

        # submission_content は include_all_context / final_output_format に従って整形
        # （詳細は「最終ステップの出力（submission_content）」節）
        submission_content = self._build_submission_content(
            context,
            include_all=self.config.include_all_context,
            fmt=self.config.final_output_format,
        )
        return WorkflowResult(
            final_output=submission_content,
            submissions=deps.submissions,
            all_messages=context.all_messages,
            total_usage=context.total_usage,
        )

    async def _execute_step(self, step, context, deps) -> StepResult:
        executables = [build_executable(cfg) for cfg in step.executors]
        task_prompt = context.build_task_prompt(
            include_all=self.config.include_all_context,
        )

        # 単一/並列いずれも「全 executor の完了を待ってから失敗判定」方針で統一。
        # Executable.run は例外を漏らさない契約のため return_exceptions=False で安全。
        # 1 executor の失敗で他をキャンセルしない（観測性・submission 記録を優先）
        results = await asyncio.gather(*[
            self._run_one(exe, task_prompt, deps) for exe in executables
        ])

        # Function executor の ERROR は即失格。全完了後に検出して WorkflowStepFailedError に
        # 昇格し、ワークフロー中断 → team モードの _execute_single_round 失敗パスに合流する
        # （詳細は後述「副作用と例外の境界」「ステップ間の伝播」参照）。
        # Agent ERROR はここでは昇格せず、次ステップへコンテキストとして伝播させる（ソフト失敗）
        for exe, result in zip(executables, results):
            if exe.executor_type == "function" and result.status == "ERROR":
                raise WorkflowStepFailedError(
                    step_id=step.id,
                    executor_name=exe.name,
                    error_message=result.error_message,
                )

        return StepResult(outputs=list(results))

    async def _run_one(self, exe: Executable, task: str, deps) -> ExecutableResult:
        result = await exe.run(task)
        # 副作用（Submission記録）はEngine側が管理。
        # ExecutableResult は MemberSubmission の必須フィールドを全て満たす形で揃えているので
        # フィールドを省略せず全て埋める（保存層・on_round_complete 契約との整合のため）。
        # Agent ERROR もここで submission に積む（ソフト失敗扱いで次ステップへ伝播）。
        # Function ERROR も一旦 append されるが、直後に _execute_step で昇格判定されラウンド全体が
        # 廃棄されるため、結果的に DB には保存されない（team モードの Leader 失敗時と同じ挙動）
        deps.submissions.append(MemberSubmission(
            agent_name=exe.name,
            agent_type=exe.executor_type,
            content=result.content,
            status=result.status,                   # "SUCCESS" | "ERROR"
            error_message=result.error_message,
            usage=result.usage,
            execution_time_ms=result.execution_time_ms,
            all_messages=result.all_messages,
        ))
        return result
```

---

### コンテキスト伝搬

各ステップへの入力は **parse 可能な JSON 文字列**（`str`）で統一する。スキーマは `{user_prompt: str, previous_steps: dict[step_id, list[output]]}` の2フィールド固定。累積範囲は `include_all_context` フラグで切り替える。

```python
class WorkflowContext:
    """ステップ間の出力を蓄積し、次ステップへの入力（JSON文字列）を構築。"""

    def build_task_prompt(self, *, include_all: bool) -> str:
        # Round 2以降は PromptBuilder が前ラウンド submission + score + feedback を
        # 埋め込んだ拡張プロンプトが self.user_prompt に入る
        if include_all:
            # include_all_context = true（デフォ）: 全ステップ累積
            previous_steps = self._all_previous_steps()
        else:
            # include_all_context = false: 直前1ステップのみ
            previous_steps = self._last_previous_step()

        payload = {
            "user_prompt": self.user_prompt,
            "previous_steps": previous_steps,
        }
        return json.dumps(payload, ensure_ascii=False)

    def _all_previous_steps(self) -> dict[str, list[dict]]:
        return {
            step_id: [self._serialize(o) for o in result.outputs]
            for step_id, result in self.step_results.items()
        }

    def _last_previous_step(self) -> dict[str, list[dict]]:
        if not self.step_results:
            return {}
        # step_results は挿入順を保つ dict（Python 3.7+ 保証）
        last_id, last_result = next(reversed(self.step_results.items()))
        return {last_id: [self._serialize(o) for o in last_result.outputs]}

    @staticmethod
    def _serialize(output: ExecutableResult) -> dict:
        return {
            "executor_name": output.name,
            "status": output.status,            # "SUCCESS" | "ERROR"
            "content": output.content,
            "error_message": output.error_message,
        }
```

- **入出力は `str` の1引数で統一**（Executable Protocol の契約は変えない）。その str は **全ステップで上記スキーマの JSON 文字列**
- **Step 1**: `previous_steps = {}` となる JSON（フラグ問わず）。`user_prompt` フィールドに（Round 2以降はPromptBuilderで拡張済みの）ユーザプロンプトが入る
- **Step 2以降**:
  - `include_all_context = true`（デフォ）: これまで実行した全ステップの累積
  - `include_all_context = false`: **直前1ステップのエントリのみ**。キー名・構造は同じ `previous_steps` を流用する（executor 側の parse 規約は変わらない）
- Executor側の利用規約:
  - **Function executor**: `json.loads(input)` して構造的に参照するのが標準
  - **Agent executor**: `system_instruction` で「入力は `{user_prompt, previous_steps}` 形式のJSON」であることを明示する（各ワークフロー設計者の責務）。共通テンプレートが必要ならプロジェクト側で提供
- ペイロード schema（`user_prompt: str` / `previous_steps: dict[step_id, list[{executor_name, status, content, error_message}]]`）は**方針書で固定**。独自拡張する場合は schema ごとバージョニングする

#### 中間 JSON の例

TOML 例（`gather` 並列2 executor → `format` 単一 → `synthesize` 単一）で、`include_all_context` の両値における各ステップ入力 JSON を示す。Round 1 / Step 1 実行時は常に `previous_steps = {}`。

**共通: Step 1 (`gather`) への入力**

```json
{
  "user_prompt": "量子コンピュータの最新動向をまとめて",
  "previous_steps": {}
}
```

**`include_all_context = true`（デフォ）**

Step 2 (`format`) への入力:

```json
{
  "user_prompt": "量子コンピュータの最新動向をまとめて",
  "previous_steps": {
    "gather": [
      {"executor_name": "web-searcher",      "status": "SUCCESS", "content": "...web検索結果...",   "error_message": null},
      {"executor_name": "academic-searcher", "status": "SUCCESS", "content": "...学術検索結果...", "error_message": null}
    ]
  }
}
```

Step 3 (`synthesize`) への入力（`gather` と `format` の両方を累積）:

```json
{
  "user_prompt": "量子コンピュータの最新動向をまとめて",
  "previous_steps": {
    "gather": [
      {"executor_name": "web-searcher",      "status": "SUCCESS", "content": "...web検索結果...",   "error_message": null},
      {"executor_name": "academic-searcher", "status": "SUCCESS", "content": "...学術検索結果...", "error_message": null}
    ],
    "format": [
      {"executor_name": "markdown-formatter", "status": "SUCCESS", "content": "# 量子コンピュータ...", "error_message": null}
    ]
  }
}
```

**`include_all_context = false`**

Step 2 (`format`) への入力（直前 = `gather`。true の場合と同じ）:

```json
{
  "user_prompt": "量子コンピュータの最新動向をまとめて",
  "previous_steps": {
    "gather": [
      {"executor_name": "web-searcher",      "status": "SUCCESS", "content": "...web検索結果...",   "error_message": null},
      {"executor_name": "academic-searcher", "status": "SUCCESS", "content": "...学術検索結果...", "error_message": null}
    ]
  }
}
```

Step 3 (`synthesize`) への入力（**`gather` は含まれず、直前の `format` のみ**）:

```json
{
  "user_prompt": "量子コンピュータの最新動向をまとめて",
  "previous_steps": {
    "format": [
      {"executor_name": "markdown-formatter", "status": "SUCCESS", "content": "# 量子コンピュータ...", "error_message": null}
    ]
  }
}
```

#### サイズ制御方針

`previous_steps` を累積し続けると**Web検索系や長文出力が混ざった場合に最終ステップ入力が急速に肥大化**し、モデルのコンテキスト上限超過・タイムアウト・コスト急増を引き起こす。MVP での制御方針:

- **`include_all_context = false` が唯一の Engine 側サイズ制御**。直前1ステップ以外を捨てる単純なウィンドウ化を提供する
- それ以上のトリミング・要約・明示的ウィンドウ幅指定はMVPでは行わない。必要なら Function executor で「直前ステップ出力を圧縮する中間ステップ」を設計者が挟む
- 各 executor 出力のサイズ制御は **executor 側（Agent の `max_tokens` / Function 実装）と TOML 設計者（ステップ数・executor 数の設計）**の責務

---

### 最終ステップの出力（submission_content）

最終ステップの出力を `final_output_format` に従って整形し、`submission_content`（Evaluator への入力、DuckDB への保存対象）として返す。最終ステップは executor が単一でも並列（複数）でも扱える。

| ケース | `include_all_context` | `final_output_format` | `submission_content` の形 |
|-------|------------------------------|-----------------------|---------------------------|
| **A** | `true`  | `"json"` | **全ステップ累積 JSON**。中間ステップ + 最終ステップ全 executor を含む |
| **B** | `false` | `"json"` | **最終ステップのみ JSON**。`steps` キー配下は最終ステップID 1件のみ |
| **C** | `true`  | `"text"` | **全ステップ Markdown**。`## <step_id>` で各ステップを区切り、配下に `### <executor_name>` で各 executor を列挙。ERROR 時のみ見出しに `(ERROR: <message>)` を併記（非対称設計） |
| **D** | `false` | `"text"` | **最終ステップのみ Markdown**。`## <executor_name>` 区切りで各 executor を連結（step_id 階層は省略）。ERROR 時のみ見出しに `(ERROR: <message>)` を併記 |

**構築ロジック**:

`WorkflowEngine.run` の最後で `_build_submission_content()` を呼ぶ。`WorkflowContext` が保持する全 `step_results` と最終ステップ ID、2つのフラグを受けて整形する。

```python
def _build_submission_content(
    self,
    context: WorkflowContext,
    *,
    include_all: bool,
    fmt: Literal["json", "text"],
) -> str:
    final_step_id = self.config.steps[-1].id
    final_outputs = context.step_results[final_step_id].outputs

    if fmt == "json":
        if include_all:
            steps = {
                step_id: [WorkflowContext._serialize(o) for o in r.outputs]
                for step_id, r in context.step_results.items()
            }
        else:
            steps = {
                final_step_id: [WorkflowContext._serialize(o) for o in final_outputs]
            }
        return json.dumps(
            {"user_prompt": context.user_prompt, "steps": steps},
            ensure_ascii=False,
        )

    # fmt == "text"
    # SUCCESS は executor_name のみ。ERROR 時は (ERROR: <message>) を見出しに併記する（非対称設計）
    def _format_executor(o: ExecutableResult, *, heading: str) -> str:
        if o.status == "ERROR":
            header = f"{heading} {o.name} (ERROR: {o.error_message})"
        else:
            header = f"{heading} {o.name}"
        return f"{header}\n\n{o.content}"

    if include_all:
        # 全ステップを `## <step_id>` + `### <executor_name>` の2階層で連結
        sections = []
        for step_id, r in context.step_results.items():
            executors_md = "\n\n".join(
                _format_executor(o, heading="###") for o in r.outputs
            )
            sections.append(f"## {step_id}\n\n{executors_md}")
        return "\n\n".join(sections)

    # include_all=false: 最終ステップのみ。step_id 階層は冗長なので `## <executor_name>` で列挙
    return "\n\n".join(
        _format_executor(o, heading="##") for o in final_outputs
    )
```

#### 各ケースの具体例

research-pipeline（`gather` 並列2 executor → `format` 単一 → `synthesize` 単一）における `submission_content` の実例を示す。

**ケース A (`include_all=true`, `fmt="json"`)** — 全累積 JSON

```json
{
  "user_prompt": "量子コンピュータの最新動向をまとめて",
  "steps": {
    "gather": [
      {"executor_name": "web-searcher",      "status": "SUCCESS", "content": "...", "error_message": null},
      {"executor_name": "academic-searcher", "status": "SUCCESS", "content": "...", "error_message": null}
    ],
    "format": [
      {"executor_name": "markdown-formatter", "status": "SUCCESS", "content": "...", "error_message": null}
    ],
    "synthesize": [
      {"executor_name": "synthesizer", "status": "SUCCESS", "content": "# 量子コンピュータの最新動向\n...", "error_message": null}
    ]
  }
}
```

**ケース B (`include_all=false`, `fmt="json"`)** — 最終ステップのみ JSON

```json
{
  "user_prompt": "量子コンピュータの最新動向をまとめて",
  "steps": {
    "synthesize": [
      {"executor_name": "synthesizer", "status": "SUCCESS", "content": "# 量子コンピュータの最新動向\n...", "error_message": null}
    ]
  }
}
```

**ケース C (`include_all=true`, `fmt="text"`)** — 全ステップ Markdown（`## <step_id>` + `### <executor_name>` の2階層）:

```markdown
## gather

### web-searcher

...web検索結果...

### academic-searcher

...学術検索結果...

## format

### markdown-formatter

...整形済みMarkdown...

## synthesize

### synthesizer

# 量子コンピュータの最新動向
...
```

ERROR 混在例（`academic-searcher` がソフト失敗した場合の `gather` ステップ部分）:

```markdown
## gather

### web-searcher

...web検索結果...

### academic-searcher (ERROR: rate limit exceeded)


```

**ケース D (`include_all=false`, `fmt="text"`)** — 最終ステップのみ Markdown

```markdown
## synthesizer

# 量子コンピュータの最新動向
...
```

#### 最終ステップが executor 並列（複数）の場合

例: 最終ステップに `reviewer_a` と `reviewer_b` の2 executor がある場合:

- **ケース A / B** (`fmt="json"`): `steps[<final_step_id>]` が当該 executor 全員分の配列になる（executor の並び順は TOML 定義順）
- **ケース C** (`fmt="text"`): `## <final_step_id>` 配下に `### reviewer_a\n\n<本文>\n\n### reviewer_b\n\n<本文>` のように `### <executor_name>` 区切りで連結
- **ケース D** (`fmt="text"`): `## reviewer_a\n\n<本文>\n\n## reviewer_b\n\n<本文>` のように `## <executor_name>` 区切りで連結（step_id 階層は省略）

#### 空出力・エラー時の扱い

- **最終ステップ全 executor が `status="ERROR"`（= agent のソフト失敗が最終ステップで発生）**: JSON系（A / B）は ERROR エントリ付き JSON がそのまま `submission_content` となる。Text系（C / D）は executor 見出しに `(ERROR: <message>)` が併記され、その下に空の本文（部分出力があればそれ）が続く Markdown となる。`submission_content` が実質空の場合の挙動は Evaluator 側の既存仕様に従う（team モードで Leader 出力が空になる場合と同じ扱い）
- **Function ERROR / その他ハード失敗**: そもそも `WorkflowStepFailedError` が昇格してワークフロー中断 → `_build_submission_content` は呼ばれない（詳細は「副作用と例外の境界」節）

---

### 実行フロー全体

**正常系**:

```
orchestrator.toml
  └─ config = "workflow_research.toml"  ← [workflow] を自動検出
       ↓
RoundController(strategy=WorkflowStrategy)
       ↓
Round 1:
  WorkflowEngine.run(user_prompt)
    ├─ Step "gather" (並列)
    │    ├─ AgentExecutable(web-searcher).run(user_prompt)
    │    └─ AgentExecutable(academic-searcher).run(user_prompt)
    ├─ Step "format"
    │    └─ FunctionExecutable(markdown-formatter).run(user_prompt + gather結果)
    └─ Step "synthesize"
         └─ AgentExecutable(synthesizer).run(JSON payload)
              ↓
       _build_submission_content(include_all, final_output_format)
              → submission_content  ※整形仕様は「最終ステップの出力（submission_content）」節
       ↓
Evaluator.evaluate(submission_content) → score
       ↓
DuckDB保存 → LeaderBoardEntry → ラウンド継続判定 → Round 2...
```

**失敗系（ハード失敗時のフロー）**:

```
Round N:
  WorkflowEngine.run(user_prompt)
    ├─ Step "gather" (並列)
    │    ├─ AgentExecutable(web-searcher)     → ERROR  ← ソフト失敗。submission に積んで継続
    │    └─ AgentExecutable(academic-searcher) → SUCCESS
    ├─ Step "format"
    │    └─ FunctionExecutable(markdown-formatter) → ERROR  ← ハード失敗。即失格
    │         ↓
    │    WorkflowStepFailedError raise（"synthesize" は実行されない）
    ↓
  WorkflowStrategy / _execute_single_round が catch せず propagate
    ↓
  _run_team (orchestrator.py) が catch
    ├─ round_history 非空 → PartialTeamFailureError で best_round 採用（部分成功リカバリ）
    └─ round_history 空   → 元の例外が propagate → TeamStatus="failed"
```

---

### ファイル構成（新規・変更）

```
src/mixseek/
├── workflow/                    # 新規パッケージ
│   ├── __init__.py
│   ├── engine.py               # WorkflowEngine
│   ├── executable.py           # Executable Protocol, AgentExecutable, FunctionExecutable
│   ├── exceptions.py           # WorkflowStepFailedError(function/その他のハード失敗昇格用)
│   └── models.py               # WorkflowContext, StepResult, WorkflowResult
├── round_controller/
│   ├── strategy.py             # 新規: ExecutionStrategy, LeaderStrategy, WorkflowStrategy
│   │                           #   ※ team / workflow 両モードを抽象化する上位概念のため round_controller 配下
│   └── controller.py           # 変更: load_team_settings() 直呼びをやめ load_unit_settings()
│                               #       の戻り値型で Strategy を決定する
├── config/
│   ├── schema.py               # 変更: WorkflowSettings (`include_all_context: bool = True`,
│   │                           #       `final_output_format: Literal["json","text"] = "json"`),
│   │                           #       WorkflowStepSettings, AgentExecutorSettings,
│   │                           #       FunctionExecutorSettings, FunctionPluginMetadata,
│   │                           #       StepExecutorConfig 追加
│   ├── manager.py              # 変更: load_workflow_settings() / load_unit_settings()
│   │                           #       （TOMLトップレベルで [team] / [workflow] 判別）
│   ├── sources/
│   │   └── workflow_toml_source.py  # 新規: [workflow] セクション用ソース
│   │                                #       （既存 team_toml_source.py と対）
│   └── preflight/validators/
│       └── workflow.py          # 新規: ワークフロー設定の preflight 検証
│                                #       （validators/team.py と対、dispatch は type 判別）
└── orchestrator/
    └── orchestrator.py          # 変更: load_team_config() 直呼びの3箇所
                                 #       （auth確認 / team_id重複チェック / TeamStatus初期化）を
                                 #       load_unit_config() 経由に差し替え
```

**変更しないもの**: Evaluator、Storage (`AggregationStore` / スキーマ)、PromptBuilder、UI、BaseMemberAgent、MemberAgentFactory、MemberSubmission

**影響を受けるもの**: ConfigurationManager、Orchestrator（読込系の直呼び3箇所）、config/sources、config/preflight/validators

---

### 設計の狙い

| 観点 | 説明 |
|------|------|
| **最小侵襲** | 既存チームモードは `LeaderStrategy` に移植。既存テスト・動作は壊れない。ただし設定読込系（ConfigurationManager / Orchestrator / preflight）は `[team]` 前提に固定されているため、type 判別のための最小限の追加改修が必要（下記「設定基盤への影響範囲」参照） |
| **再利用最大化** | MemberAgentFactory、BaseMemberAgent はそのまま。Executableアダプターで統合 |
| **意味論の一貫性** | 関数はAgentを継承しない。アダプターパターンで `str → str` に統一 |
| **関心の分離** | Executable は純粋な変換。副作用管理（Submission記録）はEngine側 |
| **対称的構造** | リーダー: 「Agent → Tool にアダプト」 / ワークフロー: 「Agent/Function → Executable にアダプト」 |
| **失敗挙動の整合性** | Agent ERROR = ソフト失敗（次ステップへ伝播。team モードの member 失敗と等価）、Function / その他 = ハード失敗（team の `_execute_single_round` 失敗パスに合流、`PartialTeamFailureError` で best_round 救済）。ワークフロー専用の停止条件は追加しない |
| **拡張性** | Strategy パターン + Executable Protocol により将来の拡張（条件分岐、新Executor種別等）が容易 |

---

### 設定基盤への影響範囲

既存の設定読込系が `[team]` 前提に固定されているため、以下の4点で `[workflow]` 経路を明示的に通す必要がある。

#### 1. ConfigurationManager に `load_workflow_settings()` / `load_unit_settings()` を新設

既存の `load_team_settings()` は `TeamTomlSource` が `[team]` セクション必須となっているため（`src/mixseek/config/sources/team_toml_source.py`）、`[workflow]` ファイルはそのままでは読めない。以下のAPIを新設する。

```python
# config/manager.py
class ConfigurationManager:
    def load_workflow_settings(self, config_path: Path) -> WorkflowSettings:
        """[workflow] セクション専用のローダー。"""
        ...

    def load_unit_settings(self, config_path: Path) -> TeamSettings | WorkflowSettings:
        """TOMLトップレベルキーで自動判別して返す上位API。"""
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        # 実際には、どちらか片方のみがトップレベルキーにあることを検証する
        if "team" in data:
            return self.load_team_settings(config_path)
        if "workflow" in data:
            return self.load_workflow_settings(config_path)
        raise ConfigurationError(
            f"Neither [team] nor [workflow] section found in {config_path}"
        )
```

#### 2. Orchestrator の `load_team_config()` 直呼び3箇所を差し替え

`src/mixseek/orchestrator/orchestrator.py` では以下の3箇所で `load_team_config()` を直接呼び、`team_id` / `team_name` / Leader モデル情報を取り出している:

- auth 情報確認（デバッグログ）
- `team_id` 重複チェック（data integrity）
- TeamStatus 初期化

`[workflow]` ファイルに対しても同等のメタ情報（`workflow_id` → `team_id` 相当、代表モデル）が取れるよう、以下のいずれかを行う:

- **案A**: `load_unit_config()` を介して共通の軽量メタ型（`UnitMeta(team_id, team_name, primary_model)`）を返す
- **案B**: `WorkflowSettings` に `team_id` / `team_name` プロパティを委譲で持たせ、`TeamConfig` 互換として扱う

いずれの場合も Orchestrator は `load_team_config()` の直呼びをやめ、統一APIを経由する。

#### 3. Preflight バリデータの追加と auth 検証経路の拡張

`src/mixseek/config/preflight/validators/team.py` は `load_team_settings()` で全チーム設定を検証しており、`[workflow]` ファイルが混在すると落ちる。以下を行う:

- `validators/workflow.py` を新設し、`[workflow]` TOML 用の検証（plugin 解決、function ロード可能性、step順序など）を行う
- preflight の dispatch 部分で TOML の type 判別を挟み、team / workflow を振り分ける

**さらに auth 検証経路の拡張が必要（ハマりポイント）**:

現状 `validators/auth.py` の `_collect_model_ids()` / `_validate_auth()` は `team_settings_list: list[TeamSettings]` を受け取り、各 team の `leader.model` と `members[*].model` からモデルIDを集めている。`preflight/runner.py` も `_validate_teams()` の戻りをそのまま `_validate_auth()` に渡す構造。

このまま workflow を足しても **ワークフロー側の executor モデル認証情報は preflight で検出されず、本番実行時に初めて落ちる** リスクがある。以下のいずれかで対応する:

- **案A**: `_collect_model_ids()` のシグネチャを `list[TeamSettings | WorkflowSettings]` に拡張し、`WorkflowSettings` の場合は全 `AgentExecutorSettings.model` を収集する分岐を追加（`FunctionExecutorSettings` は `model` を持たないため除外）
- **案B**: `_validate_workflows()` を新設して workflow 側からモデルIDを別経路で集め、`runner.py` で team / workflow 両方の結果をマージして `_validate_auth()` に渡す

いずれにせよ **「auth 検証は team / workflow の両方を対象にする」** という方針。

#### 4. RoundController の入口

`src/mixseek/round_controller/controller.py` の `__init__` は現在 `config_manager.load_team_settings()` を直接呼んで `team_settings` に束縛している。ワークフローモード対応後は:

```python
unit_settings = config_manager.load_unit_settings(team_config_path)
if isinstance(unit_settings, TeamSettings):
    self._strategy = LeaderStrategy(unit_settings, ...)
elif isinstance(unit_settings, WorkflowSettings):
    self._strategy = WorkflowStrategy(unit_settings, ...)
```

のように戻り値の型で `ExecutionStrategy` を決定する。

---

### Submission契約への対応（レビュー指摘対応）

ワークフロー実行結果は最終的に既存の `MemberSubmission` / `AggregationStore` に載る。ストレージ層を変更しない前提を維持するため、`ExecutableResult` を `MemberSubmission` の必須フィールドに過不足なく対応させる。

#### Function executor の既定値

LLM呼び出しを伴わない Function executor では、以下の値で `MemberSubmission` を埋める。

| フィールド | Function executor での値 |
|-----------|------------------------|
| `status` | `"SUCCESS"` / 例外発生時 `"ERROR"`（既存 `MemberSubmission` の大文字ドメインに準拠） |
| `error_message` | 例外時の文字列表現、それ以外は `None` |
| `usage` | `RunUsage()`（ゼロ値：input/output tokens ともに 0） |
| `execution_time_ms` | `time.perf_counter()` 計測値 |
| `all_messages` | `[]`（LLMメッセージ履歴なし） |
| `agent_type` | `"function"` |

※ フィールド名・値ドメインは全て **既存 `MemberSubmission` (`src/mixseek/agents/leader/models.py`) と完全一致** させる。独自命名を持ち込むと集計ロジック（`successful_submissions` / `failed_submissions` は `status == "SUCCESS"` / `"ERROR"` で判定）が壊れる。

#### 副作用と例外の境界（ハマりポイント）

**副作用の所在**:
- `deps.submissions.append(...)` は WorkflowEngine の `_run_one` でのみ行い、Executable 自身は副作用を持たない
- ただし**ハード失敗でラウンドが廃棄された場合、そのラウンド分の submission は `round_history` / DB に残らない**。これは team モードの既存挙動（`_execute_single_round` が成功完了した時のみ `round_history.append` → storage save される）と完全に一致する

**例外境界ポリシー（Executable レベルでは統一、engine レベルで非対称に昇格）**:
- `Executable.run` は **例外を絶対に外に漏らさない契約** とする。`AgentExecutable` / `FunctionExecutable` のいずれも実装内で try/except し、失敗は `ExecutableResult(status="ERROR", error_message=...)` に変換する
- これは custom agent が任意実装であり `BaseMemberAgent.execute` が例外不捕捉保証を持たない（`src/mixseek/agents/member/base.py` の abstractmethod docstring に保証記述なし）ための防衛線
- 失敗の**昇格判定は engine 側（`_execute_step`）が executor_type に応じて行う**:
  | executor種別 | ERROR 時の扱い | 分類 |
  |-------------|--------------|------|
  | **Agent** (`plain` / `web_search` / `custom`) | `submission` に積んで次ステップへコンテキスト伝播。ワークフロー継続 | **ソフト失敗**（team モードの member 失敗と等価） |
  | **Function** | `WorkflowStepFailedError` に昇格してワークフロー中断 | **ハード失敗**（即失格） |
  | **その他** (plugin ロード失敗 / engine 内想定外例外 / Timeout 等) | 例外がそのまま上位へ伝播 | **ハード失敗**（即失格） |
- この非対称性は意図的: **「LLM は失敗しても後続 step / 次ラウンドで吸収できる」「決定的コード（function）の失敗は仕様違反」** という役割分担に基づく。Agent は Pydantic AI の `max_retries`（デフォ 3）で既にリトライ済みの最終結果が ERROR なので、リトライ不要

**ステップ並列時の伝播**:
- `_execute_step` の並列実行は `asyncio.gather(..., return_exceptions=False)` を使用。Executable.run が例外を漏らさない契約のため安全
- **全 executor の完了を待ってから失敗判定する**（1 つ失敗しても他をキャンセルしない）。観測性を優先し、同一ステップ内の他 executor の submission は全て記録する
- 並列ステップに function / agent が混在して両方 ERROR だった場合、agent ERROR の submission も一旦 `deps.submissions.append` されるが、その後 function ERROR で `WorkflowStepFailedError` が昇格しラウンド全体が廃棄されるため、結果的に DB には残らない（team モードの `_execute_single_round` 失敗時と同じ挙動）

**ステップ間の伝播**:
- **Agent ERROR のみの場合（ソフト失敗）**: 次ステップはコンテキスト（ERROR 出力を含む）を受けて継続実行する。最終ステップの出力が空（全 executor が agent ERROR）になった場合は、既存 team mode で Leader 出力が空になるケースと同じ扱い（RoundController 側の責務、Evaluator に空文字を渡すか Skip するかは既存仕様に従う）
- **Function ERROR / その他ハード失敗の場合**: ワークフロー中断 → `WorkflowEngine.run` から例外 throw → `WorkflowStrategy` / `_execute_single_round` が catch せず propagate → **team モードの既存失敗パスに合流する**:
  - `_run_team` (`orchestrator.py:397-475`) が catch
  - `round_history` 非空（= 過去ラウンドで 1 回以上完走している） → `_try_recover_partial_failure()` → `PartialTeamFailureError` で **best_round を採用**（部分成功リカバリ）
  - `round_history` 空（初回ラウンドからハード失敗） → 元の例外がそのまま propagate → `TeamStatus="failed"`
- **ワークフロー専用の停止条件は追加しない**。team モードと同じ `_execute_single_round` 失敗経路に合流することで、部分成功リカバリ・timeout 処理・ReadError リトライ等の既存機構がそのまま機能する

#### Storage 層へのインパクト

- `AggregationStore` は `MemberSubmissionsRecord + list[ModelMessage]` を前提としている（`src/mixseek/storage/aggregation_store.py`）。上記の既定値で Function の submission を構築すれば、**既存スキーマに変更を入れずに保存可能**
- ただし `agent_type = "function"` は新種別となるため、UI / 集計側で想定外キーが来ても落ちないことは確認する（読み取り専用なら問題ない見込み）

Created by 🤖Claude
