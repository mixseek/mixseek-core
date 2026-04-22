# ワークフローモード MVP 実装計画

## 1. Context

**現状**: mixseek は「チームモード」のみ (`Orchestrator → RoundController → LeaderAgent(LLM判断) → MemberAgents`)。Leader が LLM 推論で member を動的選択。

**追加**: **固定ステップでエージェント/関数を順次・並列実行する「ワークフローモード」**。TOML で宣言、各ステップは複数 executor（agent or Python 関数）を束ね、複数なら並列・単一なら直列実行。評価・ラウンド制御・DuckDB 保存・logfire 観測は流用。

### 1.2 ゴール
- TOML `[workflow]` で固定ステップ宣言
- executor: `plain` / `web_search` / `web_fetch` / `code_execution` / `custom` (agent 系) と `function` (Python) を混在可
- DuckDB スキーマ・logfire トレース・Evaluator・Judgment・PromptBuilder はチームモードと**同じ**
- `orchestrator.toml` 無変更。`[[orchestrator.teams]]` の config で `[team]` / `[workflow]` を自動判別

### 1.3 Non-goals
- ステップ間の条件分岐・ループ・スキップ
- executor の TOML 参照 `config = "agents/xxx.toml"`（team の member 参照とは別仕様）— MVP はインライン定義のみ
- ワークフロー専用の停止条件（既存の `max_rounds` / `min_rounds` / 改善判定が効く）
- UI でのワークフロー可視化

---

## 2. User decisions

| # | 決定事項 | 決定値 |
|---|---------|-------|
| D1 | Workflow 識別子 TOML フィールド名 | `workflow_id` / `workflow_name`（内部で `team_id` / `team_name` にマップ） |
| D2 | Executor 識別フィールド名 | `name` / `type`（`MemberAgentSettings` の `agent_name` / `agent_type` とは別スキーマ） |
| D3 | `round_history.message_history` の保存内容 | 全 agent executor の `all_messages` を **ステップ順 × executor TOML 定義順** で連結した `list[ModelMessage]`。並列 executor は TOML 定義順にブロックとして並べ、個別 ModelMessage の timestamp による厳密ソートは行わない |
| D4 | Function executor エラー時 | 即失格（`WorkflowStepFailedError` 昇格 → team mode の `_execute_single_round` 失敗パスに合流） |

---

## 3. Architecture overview

### 3.1 クラス関係

```
orchestrator.toml
  └─ [[orchestrator.teams]] config = "path.toml"
       │
       ├─ [team]     → ConfigurationManager.load_unit_settings() → TeamSettings
       │               → LeaderStrategy（既存のチーム処理を移植）
       │
       └─ [workflow] → ConfigurationManager.load_unit_settings() → WorkflowSettings
                        → WorkflowStrategy → WorkflowEngine
                                              └─ build_executable(cfg)
                                                   ├─ AgentExecutable (既存 BaseMemberAgent をラップ)
                                                   └─ FunctionExecutable (Python callable をラップ)

RoundController.__init__ で strategy を決定し、_execute_single_round で strategy.execute(...) を呼ぶ。
Evaluator / PromptBuilder / Judgment / DuckDB 保存は strategy の外側で動く。
```

### 3.2 主要コンポーネントの責務

- **`Executable` Protocol**: `run(input: str) -> ExecutableResult`。例外を**絶対に漏らさない**契約
- **`AgentExecutable`**: `BaseMemberAgent.execute(task, context=...)` を呼ぶアダプター。logfire は `instrument_pydantic_ai()` で自動トレース。team `tools.py` と同じ 3 キー固定 context（`execution_id`/`team_id`/`round_number`）を合成
- **`FunctionExecutable`**: `Callable[[str], str | Awaitable[str]]` をラップ。`instrument_pydantic_ai()` の自動トレース対象外のため、`_logfire_span("workflow.function", ...)` で手動 span を張る（logfire 非導入時は nullcontext にフォールバック）。logger `mixseek.workflow.function` も併用
- **`WorkflowEngine`**: ステップ順送り+各ステップ内 `asyncio.gather`。`MemberSubmission` 積み・ハード失敗昇格を担当
- **`ExecutionStrategy` Protocol**: `execute(user_prompt, deps) -> StrategyResult`。`LeaderStrategy`（既存チームモード移植） / `WorkflowStrategy`（`WorkflowEngine.run()` 委譲）

---

## 4. Directory structure & file changes

```
src/mixseek/
├── workflow/                            【新規】
│   ├── __init__.py
│   ├── engine.py                        # WorkflowEngine
│   ├── executable.py                    # Executable Protocol, AgentExecutable, FunctionExecutable, build_executable
│   ├── exceptions.py                    # WorkflowStepFailedError
│   └── models.py                        # WorkflowContext, StepResult, WorkflowResult, ExecutableResult, StrategyResult
├── round_controller/
│   ├── strategy.py                      【新規】ExecutionStrategy, LeaderStrategy, WorkflowStrategy
│   ├── controller.py                    【変更】load_team_settings → load_unit_settings、Strategy 経由
│   └── __init__.py                      【変更】strategy を re-export
├── config/
│   ├── schema.py                        【変更】WorkflowSettings 等を追加、既存 `MemberAgentSettings.timeout_seconds` を ge=0→ge=1 に統一（MemberAgentConfig と一致）
│   ├── manager.py                       【変更】load_workflow_settings(), load_unit_settings() 追加
│   ├── member_agent_loader.py           【変更】`_resolve_bundled_system_instruction` 共通ヘルパー抽出（team/workflow 両方から使用）
│   ├── sources/
│   │   └── workflow_toml_source.py      【新規】[workflow] セクション用ソース
│   └── preflight/
│       ├── runner.py                    【変更】team / workflow を判別して dispatch
│       └── validators/
│           ├── workflow.py              【新規】ワークフロー設定 preflight
│           ├── team.py                  【変更】`[team]` 以外は skip
│           └── auth.py                  【変更】list[TeamSettings | WorkflowSettings] 受け取り
└── orchestrator/
    └── orchestrator.py                  【変更】load_team_config() 直呼び3箇所を load_unit_config() 経由に
```

**変更しないもの**: `Evaluator`, `AggregationStore`, `storage/schema.py`, `PromptBuilder`, UI, `BaseMemberAgent`, `MemberAgentFactory`, `MemberSubmission`, `MemberSubmissionsRecord`, `orchestrator.toml` スキーマ

---

## 5. Detailed implementation

### 5.1 `config/schema.py` に追加する Pydantic モデル

既存の `TeamSettings` の後に追加。

#### 5.1.1 `FunctionPluginMetadata`

```python
class FunctionPluginMetadata(BaseModel):
    """Function executor のプラグイン指定。agent 用 `PluginMetadata` は流用不可（フィールド不一致 + extra=forbid）。"""
    module: str = Field(..., description="Python module path (e.g., 'mypackage.formatters')")
    function: str = Field(..., description="Function name (e.g., 'format_as_markdown')")
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
```

#### 5.1.2 `AgentExecutorSettings`

既存 `MemberAgentSettings` とほぼ同形。差分: `name`/`type`（`agent_name`/`agent_type` ではない）、`tool_name`/`tool_description` なし（Leader tool 登録されないため）。

```python
# schema.py の top-level に追加 import:
#   from mixseek.config.member_agent_loader import _resolve_bundled_system_instruction
#   from mixseek.models.member_agent import MemberAgentConfig

_EXECUTOR_NAME_RE = re.compile(r"^[A-Za-z0-9_\-\.]+$")


class AgentExecutorSettings(MixSeekBaseSettings):
    """Workflow の agent 系 executor 設定（plain / web_search / web_fetch / code_execution / custom）"""
    model_config = SettingsConfigDict(
        env_prefix="MIXSEEK_WORKFLOW_AGENT__",
        env_file=".env", env_nested_delimiter="__",
        case_sensitive=False, extra="forbid", validate_default=True,
    )

    name: str = Field(..., description="Executor 一意名（ステップ内で重複不可）")
    type: Literal["plain", "web_search", "web_fetch", "code_execution", "custom"] = Field(...)

    model: str | None = Field(default=None, description="省略時は WorkflowSettings.default_model にフォールバック")
    system_instruction: str | None = None
    system_prompt: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)
    timeout_seconds: int | None = Field(default=None, ge=1)   # 下流 MemberAgentConfig と一致（遅延失敗回避）
    max_retries: int = Field(default=3, ge=0)
    stop_sequences: list[str] | None = None
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    seed: int | None = None

    plugin: "PluginMetadata | None" = None     # type="custom" で必須
    tool_settings: "ToolSettings | None" = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("model")
    @classmethod
    def _validate_model(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return validate_model_format(v, allow_empty=False)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        # MemberAgentConfig.validate_name と同じ制約
        if not _EXECUTOR_NAME_RE.match(v):
            raise ValueError(f"Invalid executor name '{v}'. Use alphanumeric, -, _, . only.")
        return v

    def to_member_agent_config(
        self, *, workspace: "Path | None" = None, default_model: str
    ) -> "MemberAgentConfig":
        """MemberAgentFactory.create_agent() 用変換。
        - bundled system_instruction 補完は team の `member_settings_to_config` と同じヘルパー経由（§9）。
        """
        resolved_instruction = _resolve_bundled_system_instruction(
            agent_type=self.type,
            system_instruction=self.system_instruction,
            workspace=workspace,
        )
        return MemberAgentConfig(
            name=self.name,
            type=self.type,
            model=self.model or default_model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout_seconds=self.timeout_seconds,
            max_retries=self.max_retries,
            stop_sequences=self.stop_sequences,
            top_p=self.top_p,
            seed=self.seed,
            system_instruction=resolved_instruction,
            system_prompt=self.system_prompt,
            description="",
            tool_settings=self.tool_settings,
            plugin=self.plugin,
            metadata=self.metadata,
        )
```

> **Import 循環に関する注記**: `member_agent_loader.py` は `schema.py` を TYPE_CHECKING でしか参照しないため、schema.py からの top-level import は循環しない。

#### 5.1.3 `FunctionExecutorSettings`

```python
class FunctionExecutorSettings(MixSeekBaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MIXSEEK_WORKFLOW_FUNCTION__",
        env_file=".env", env_nested_delimiter="__",
        case_sensitive=False, extra="forbid", validate_default=True,
    )
    name: str = Field(...)
    type: Literal["function"] = Field(default="function")
    plugin: FunctionPluginMetadata = Field(...)
    timeout_seconds: int | None = Field(
        default=None, ge=1,
        description="None ならタイムアウトなし。設定時は FunctionExecutable.run が asyncio.wait_for で包む。",
    )

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        # _EXECUTOR_NAME_RE は schema.py top-level で共有
        if not _EXECUTOR_NAME_RE.match(v):
            raise ValueError(f"Invalid executor name '{v}'.")
        return v
```

#### 5.1.4 Discriminated union & Step model

```python
# Pydantic v2 discriminated union。type の Literal 値に重複なし（agent 系 5 種 vs "function"）なので
# discriminator="type" のみで分岐可能。効かない場合は Tag + Discriminator(callable) へ切替。
StepExecutorConfig = Annotated[
    AgentExecutorSettings | FunctionExecutorSettings,
    Field(discriminator="type"),
]


class WorkflowStepSettings(BaseModel):
    id: str = Field(...)
    executors: list[StepExecutorConfig] = Field(..., min_length=1)
    model_config = ConfigDict(extra="forbid")

    @field_validator("id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("step id cannot be empty")
        return v

    @model_validator(mode="after")
    def _validate_executor_names_unique(self) -> "WorkflowStepSettings":
        names = [e.name for e in self.executors]
        if len(names) != len(set(names)):
            dups = [n for n in names if names.count(n) > 1]
            raise ValueError(f"Duplicate executor names within step '{self.id}': {dups}")
        return self
```

#### 5.1.5 `WorkflowSettings`

```python
class WorkflowSettings(MixSeekBaseSettings):
    """Workflow TOML スキーマ。team_id/team_name 互換 @property を持つ（モデルフィールド扱いされず extra=forbid と両立）。"""
    model_config = SettingsConfigDict(
        env_prefix="MIXSEEK_WORKFLOW__",
        env_file=".env", env_nested_delimiter="__",
        case_sensitive=False, extra="forbid", validate_default=True,
    )

    workflow_id: str = Field(..., description="ワークフロー識別子（DuckDB の team_id に流用）")
    workflow_name: str = Field(...)
    default_model: str = Field(
        default="google-gla:gemini-2.5-flash",
        description="全 agent executor のデフォルトモデル（EvaluatorSettings.default_model と同命名・同デフォルト値）。"
                    "省略可。各 executor の `model` 省略時にフォールバックされる。",
    )
    include_all_context: bool = Field(default=True)
    final_output_format: Literal["json", "text"] = Field(default="json")
    steps: list[WorkflowStepSettings] = Field(..., min_length=1)

    @field_validator("workflow_id", "workflow_name")
    @classmethod
    def _validate_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("workflow_id / workflow_name cannot be empty")
        return v

    @field_validator("default_model")
    @classmethod
    def _validate_default_model(cls, v: str) -> str:
        return validate_model_format(v, allow_empty=False)

    @model_validator(mode="after")
    def _validate_unique_step_ids(self) -> "WorkflowSettings":
        ids = [s.id for s in self.steps]
        if len(ids) != len(set(ids)):
            dups = [i for i in ids if ids.count(i) > 1]
            raise ValueError(f"Duplicate step ids: {dups}")
        return self

    @property
    def team_id(self) -> str: return self.workflow_id
    @property
    def team_name(self) -> str: return self.workflow_name
```

---

### 5.2 `workflow/` パッケージ

#### 5.2.1 `workflow/models.py`

```python
from pydantic_ai import RunUsage
from pydantic_ai.messages import ModelMessage

@dataclass
class ExecutableResult:
    """Executable.run() 返り値。status は ResultStatus.upper()。
    WARNING は successful/failed どちらの集計にも入らないが submission 保存は行う（既存 team と同じ）。
    FunctionExecutable は SUCCESS / ERROR のみ発行。"""
    content: str
    execution_time_ms: float
    status: Literal["SUCCESS", "ERROR", "WARNING"] = "SUCCESS"
    error_message: str | None = None
    usage: RunUsage = field(default_factory=RunUsage)
    all_messages: list[ModelMessage] = field(default_factory=list)

@dataclass
class StepResult:
    step_id: str
    outputs: list["ExecutableOutput"]

@dataclass
class ExecutableOutput:
    name: str
    executor_type: str
    result: ExecutableResult

class WorkflowContext:
    """ステップ間のデータ伝搬。step_results は挿入順保持 dict。"""
    def __init__(self, user_prompt: str):
        self.user_prompt = user_prompt
        self.step_results: dict[str, StepResult] = {}

    def add_step_result(self, step_id: str, result: StepResult) -> None:
        self.step_results[step_id] = result

    def build_task_prompt(self, *, include_all: bool) -> str:
        previous = self._all_previous_steps() if include_all else self._last_previous_step()
        payload = {"user_prompt": self.user_prompt, "previous_steps": previous}
        return json.dumps(payload, ensure_ascii=False)

    def _all_previous_steps(self) -> dict[str, list[dict]]:
        return {
            step_id: [self._serialize(o) for o in result.outputs]
            for step_id, result in self.step_results.items()
        }

    def _last_previous_step(self) -> dict[str, list[dict]]:
        """直前1ステップのみ。Step 1 実行時は {} を返す。"""
        if not self.step_results:
            return {}
        last_id, last_result = next(reversed(self.step_results.items()))
        return {last_id: [self._serialize(o) for o in last_result.outputs]}

    @staticmethod
    def _serialize(out: ExecutableOutput) -> dict:
        """4 フィールド固定: executor_name / status / content / error_message。
        agent は system_instruction でこのスキーマを明示、function は json.loads して参照。"""
        return {
            "executor_name": out.name,
            "status": out.result.status,
            "content": out.result.content,
            "error_message": out.result.error_message,
        }

@dataclass
class WorkflowResult:
    submission_content: str
    all_messages: list[ModelMessage]  # D3: step 順 × executor 定義順で連結
    total_usage: RunUsage

@dataclass
class StrategyResult:
    """RoundController 統一戻り値。submissions は deps.submissions 経由で team と同じ。"""
    submission_content: str
    all_messages: list[ModelMessage]
```

#### 5.2.2 `workflow/executable.py`

```python
from pydantic_ai import RunUsage

from mixseek.agents.member.factory import MemberAgentFactory
from mixseek.config.schema import AgentExecutorSettings, FunctionExecutorSettings

# logfire は optional dependency
try:
    import logfire as _logfire
    _LOGFIRE_AVAILABLE = True
except ImportError:
    _logfire = None
    _LOGFIRE_AVAILABLE = False

logger = logging.getLogger("mixseek.workflow.function")


def _logfire_span(name: str, **attrs):
    """logfire 未導入時は nullcontext。WorkflowEngine.run / FunctionExecutable.run 共有。"""
    if _LOGFIRE_AVAILABLE:
        return _logfire.span(name, **attrs)
    return nullcontext()


@runtime_checkable
class Executable(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def executor_type(self) -> str: ...
    async def run(self, input: str) -> ExecutableResult: ...

class AgentExecutable:
    """BaseMemberAgent → Executable。team `tools.py` と同じ 3 キー context (execution_id/team_id/round_number) 合成用に TeamDependencies 保持。"""
    def __init__(self, agent: "BaseMemberAgent", deps: "TeamDependencies"):
        self._agent = agent
        self._deps = deps

    @property
    def name(self) -> str: return self._agent.agent_name
    @property
    def executor_type(self) -> str: return self._agent.agent_type

    async def run(self, input: str) -> ExecutableResult:
        start = time.perf_counter()
        context = {
            "execution_id": self._deps.execution_id,
            "team_id": self._deps.team_id,
            "round_number": self._deps.round_number,
        }
        try:
            result = await self._agent.execute(input, context=context)  # MemberAgentResult
            return ExecutableResult(
                content=result.content,
                execution_time_ms=float(result.execution_time_ms or ((time.perf_counter()-start)*1000)),
                status=result.status.value.upper(),
                error_message=result.error_message,
                usage=_to_run_usage(result.usage_info),
                all_messages=result.all_messages or [],
            )
        except Exception as e:  # custom agent は例外保証なし
            return ExecutableResult(
                content="", execution_time_ms=(time.perf_counter()-start)*1000,
                status="ERROR", error_message=str(e),
            )

def _to_run_usage(usage_info: dict | None) -> RunUsage:
    if not usage_info:
        return RunUsage()
    return RunUsage(
        input_tokens=usage_info.get("input_tokens", 0),
        output_tokens=usage_info.get("output_tokens", 0),
        requests=usage_info.get("requests", 1),
    )

class FunctionExecutable:
    def __init__(
        self,
        name: str,
        func: Callable[[str], str | Awaitable[str]],
        timeout_seconds: int | None = None,
    ):
        self._name = name
        self._func = func
        self._timeout_seconds = timeout_seconds

    @property
    def name(self) -> str: return self._name
    @property
    def executor_type(self) -> str: return "function"

    async def run(self, input: str) -> ExecutableResult:
        start = time.perf_counter()
        with _logfire_span("workflow.function", function_name=self._name, timeout_seconds=self._timeout_seconds):
            logger.info("function_execution_start", extra={"function_name": self._name})
            try:
                # 同期関数も to_thread で coroutine 化 → asyncio.wait_for を統一適用（分岐なし）
                if asyncio.iscoroutinefunction(self._func):
                    coro = self._func(input)
                else:
                    coro = asyncio.to_thread(self._func, input)
                if self._timeout_seconds is not None:
                    content = await asyncio.wait_for(coro, timeout=self._timeout_seconds)
                else:
                    content = await coro
                elapsed = (time.perf_counter()-start)*1000
                logger.info("function_execution_complete", extra={"function_name": self._name, "execution_time_ms": elapsed})
                return ExecutableResult(content=str(content), execution_time_ms=elapsed, status="SUCCESS")
            except TimeoutError:
                elapsed = (time.perf_counter()-start)*1000
                msg = f"function timed out after {self._timeout_seconds}s"
                logger.error("function_execution_timeout",
                             extra={"function_name": self._name, "timeout_seconds": self._timeout_seconds}, exc_info=True)
                return ExecutableResult(content="", execution_time_ms=elapsed, status="ERROR", error_message=msg)
            except Exception as e:
                elapsed = (time.perf_counter()-start)*1000
                logger.error("function_execution_error",
                             extra={"function_name": self._name, "error": str(e)}, exc_info=True)
                return ExecutableResult(content="", execution_time_ms=elapsed, status="ERROR", error_message=str(e))


def build_executable(
    cfg,
    deps: "TeamDependencies",
    *,
    workspace: Path | None = None,
    default_model: str,
) -> Executable:
    """StepExecutorConfig → Executable。
    - `workspace` は AgentExecutor の bundled 補完に必要。
    - ValueError / TypeError を raise しうる（呼び出し側で捕捉し `WorkflowStepFailedError` へ昇格、§10）。
    """
    if isinstance(cfg, FunctionExecutorSettings):
        func = _load_function(cfg.plugin.module, cfg.plugin.function)
        return FunctionExecutable(name=cfg.name, func=func, timeout_seconds=cfg.timeout_seconds)
    if isinstance(cfg, AgentExecutorSettings):
        agent = MemberAgentFactory.create_agent(
            cfg.to_member_agent_config(workspace=workspace, default_model=default_model)
        )
        return AgentExecutable(agent=agent, deps=deps)
    raise TypeError(f"Unsupported executor config: {type(cfg).__name__}")


def _load_function(module: str, function: str) -> Callable:
    try:
        mod = importlib.import_module(module)
    except ImportError as e:
        raise ValueError(f"Failed to import module '{module}': {e}") from e
    if not hasattr(mod, function):
        raise ValueError(f"Module '{module}' has no attribute '{function}'")
    fn = getattr(mod, function)
    if not callable(fn):
        raise ValueError(f"'{module}.{function}' is not callable")
    return fn
```

#### 5.2.3 `workflow/exceptions.py`

```python
class WorkflowStepFailedError(Exception):
    """Function executor のエラー等、ワークフロー継続不能な失敗の昇格用。"""
    def __init__(self, *, step_id: str, executor_name: str, error_message: str | None):
        self.step_id = step_id
        self.executor_name = executor_name
        self.error_message = error_message
        super().__init__(f"Workflow step '{step_id}' failed at executor '{executor_name}': {error_message}")
```

#### 5.2.4 `workflow/engine.py`

```python
from pydantic_ai import RunUsage
from pydantic_ai.messages import ModelMessage

from mixseek.agents.leader.models import MemberSubmission
from mixseek.config.schema import WorkflowSettings
from mixseek.workflow.exceptions import WorkflowStepFailedError
from mixseek.workflow.executable import Executable, _logfire_span, build_executable
from mixseek.workflow.models import (
    ExecutableOutput, StepResult, WorkflowContext, WorkflowResult,
)


class WorkflowEngine:
    def __init__(self, settings: WorkflowSettings, workspace: Path | None = None):
        # workspace は AgentExecutor の bundled system_instruction 解決に使う（team モードと同じ経路）。
        self.settings = settings
        self.workspace = workspace

    async def run(self, user_prompt: str, deps: "TeamDependencies") -> WorkflowResult:
        # team の Leader span 相当を補い可観測性の対称性を保つ。
        # logfire 非導入環境では nullcontext が返るため、span ツリーなしでも正常動作する（controller.py と同じ方針）。
        with _logfire_span("workflow.engine.run",
                          workflow_id=deps.team_id, workflow_name=deps.team_name,
                          round_number=deps.round_number, step_count=len(self.settings.steps)):
            context = WorkflowContext(user_prompt=user_prompt)
            for step in self.settings.steps:
                step_result = await self._execute_step(step, context, deps)
                context.add_step_result(step.id, step_result)

            submission_content = self._build_submission_content(
                context,
                include_all=self.settings.include_all_context,
                fmt=self.settings.final_output_format,
            )
            # D3: step 順 × executor 定義順で all_messages を連結
            merged_messages: list[ModelMessage] = []
            total_usage = RunUsage()
            for step_id, r in context.step_results.items():
                for out in r.outputs:
                    merged_messages.extend(out.result.all_messages)
                    total_usage = _add_usage(total_usage, out.result.usage)
            return WorkflowResult(
                submission_content=submission_content,
                all_messages=merged_messages,
                total_usage=total_usage,
            )

    async def _execute_step(self, step, context, deps) -> StepResult:
        # build_executable の例外（動的 import 失敗等）は WorkflowStepFailedError に昇格（§10）
        executables: list[Executable] = []
        for cfg in step.executors:
            try:
                executables.append(
                    build_executable(
                        cfg, deps,
                        workspace=self.workspace,
                        default_model=self.settings.default_model,
                    )
                )
            except Exception as e:
                raise WorkflowStepFailedError(
                    step_id=step.id,
                    executor_name=getattr(cfg, "name", "<unknown>"),
                    error_message=f"failed to build executable: {e}",
                ) from e
        task_prompt = context.build_task_prompt(include_all=self.settings.include_all_context)

        results = await asyncio.gather(
            *[self._run_one(exe, task_prompt, deps) for exe in executables],
            return_exceptions=False,   # Executable.run は例外を漏らさない契約
        )

        # D4: function ERROR はハード失敗で即昇格（WARNING は対象外）
        for exe, result in zip(executables, results):
            if exe.executor_type == "function" and result.status == "ERROR":
                raise WorkflowStepFailedError(
                    step_id=step.id,
                    executor_name=exe.name,
                    error_message=result.error_message,
                )

        return StepResult(
            step_id=step.id,
            outputs=[ExecutableOutput(name=e.name, executor_type=e.executor_type, result=r)
                    for e, r in zip(executables, results)],
        )

    async def _run_one(self, exe, task: str, deps) -> ExecutableResult:
        result = await exe.run(task)
        # 副作用の所在を Engine に集約
        deps.submissions.append(MemberSubmission(
            agent_name=exe.name,
            agent_type=exe.executor_type,
            content=result.content,
            status=result.status,
            error_message=result.error_message,
            usage=result.usage,
            execution_time_ms=result.execution_time_ms,
            timestamp=datetime.now(UTC),
            all_messages=result.all_messages or None,
        ))
        return result

    def _build_submission_content(self, context, *, include_all: bool, fmt: str) -> str:
        """4 ケース分岐（include_all × fmt）。ERROR: JSON は _serialize で status/error_message 込み、
        Text は ERROR 見出しに `(ERROR: <msg>)` 併記、本文は部分出力 or 空。
        **`user_prompt` は含めない**（Round 再帰膨張回避、§10）。steps 内容のみ返す。"""
        final_step_id = self.settings.steps[-1].id
        final_outputs = context.step_results[final_step_id].outputs

        if fmt == "json":
            if include_all:
                steps = {sid: [WorkflowContext._serialize(o) for o in r.outputs]
                         for sid, r in context.step_results.items()}
            else:
                steps = {final_step_id: [WorkflowContext._serialize(o) for o in final_outputs]}
            return json.dumps({"steps": steps}, ensure_ascii=False)

        # fmt == "text"
        def _format_executor(out: "ExecutableOutput", *, heading: str) -> str:
            if out.result.status == "ERROR":
                header = f"{heading} {out.name} (ERROR: {out.result.error_message})"
            else:
                header = f"{heading} {out.name}"
            return f"{header}\n\n{out.result.content}"

        if include_all:
            sections = [f"## {sid}\n\n" + "\n\n".join(_format_executor(o, heading="###") for o in r.outputs)
                        for sid, r in context.step_results.items()]
            return "\n\n".join(sections)
        return "\n\n".join(_format_executor(o, heading="##") for o in final_outputs)


def _add_usage(a: RunUsage, b: RunUsage) -> RunUsage:
    return RunUsage(
        input_tokens=(a.input_tokens or 0) + (b.input_tokens or 0),
        output_tokens=(a.output_tokens or 0) + (b.output_tokens or 0),
        requests=(a.requests or 0) + (b.requests or 0),
    )
```

**整形 4 ケース**（いずれも user_prompt は含まない — Round 再帰膨張回避のため）:
- A (json+all): `{"steps":{<step_id>:[{executor_name,status,content,error_message},...]}}` 全ステップ分
- B (json+last): `{"steps":{<final_step_id>:[...]}}`（最終ステップのみ）
- C (text+all): `## <step_id>` + `### <executor_name>` 2階層。ERROR 時は見出しに `(ERROR: msg)` 併記、本文空
- D (text+last): 最終ステップの `## <executor_name>` のみ
- 並列は配列/見出し並列、全 ERROR でも本関数は呼ばれる（function hard failure は `WorkflowStepFailedError` 昇格で非呼び出し）

> **NOTE**: `WorkflowContext.build_task_prompt` は step 内 agent への**入力**用 JSON（`{user_prompt, previous_steps}`）で、こちらは `user_prompt` を含めて良い。submission_history に漏れない閉じたパスのため膨張しない。

---

### 5.3 `round_controller/strategy.py`（新規）

```python
# module-level import: テストの patch 先を mixseek.round_controller.strategy.create_leader_agent に合わせるため関数内ローカル import にしない
from mixseek.agents.leader.agent import create_leader_agent
from mixseek.agents.leader.config import team_settings_to_team_config
from mixseek.agents.member.factory import MemberAgentFactory
from mixseek.config.member_agent_loader import member_settings_to_config
from mixseek.config.schema import TeamSettings, WorkflowSettings
from mixseek.workflow.engine import WorkflowEngine
from mixseek.workflow.models import StrategyResult


class ExecutionStrategy(Protocol):
    async def execute(self, user_prompt: str, deps: "TeamDependencies") -> "StrategyResult": ...


class LeaderStrategy:
    """既存チームモード動作を carve-out（controller.py の Member 生成〜Leader 実行相当を移植）。"""
    def __init__(self, team_settings: TeamSettings, workspace: Path):
        self._team_settings = team_settings
        self._team_config = team_settings_to_team_config(team_settings)
        self._workspace = workspace

    async def execute(self, user_prompt: str, deps) -> StrategyResult:
        member_agents: dict[str, object] = {}
        for member_settings in self._team_settings.members:
            member_config = member_settings_to_config(
                member_settings, agent_data=None, workspace=self._workspace
            )
            member_agents[member_settings.agent_name] = MemberAgentFactory.create_agent(member_config)

        leader_agent = create_leader_agent(self._team_config, member_agents)
        result = await leader_agent.run(user_prompt, deps=deps)
        # 既存 controller.py の `submission_content: str = result.output` / `result.all_messages()` と完全互換。
        # Leader Agent は `Agent[TeamDependencies, str]` のため str() キャスト不要。
        return StrategyResult(
            submission_content=result.output,
            all_messages=result.all_messages(),
        )


class WorkflowStrategy:
    def __init__(self, workflow_settings: "WorkflowSettings", workspace: Path):
        # workspace は bundled system_instruction 解決に伝搬する（team LeaderStrategy と対称）。
        self._settings = workflow_settings
        self._engine = WorkflowEngine(workflow_settings, workspace=workspace)

    async def execute(self, user_prompt: str, deps) -> StrategyResult:
        wf_result = await self._engine.run(user_prompt, deps)
        return StrategyResult(
            submission_content=wf_result.submission_content,
            all_messages=wf_result.all_messages,
        )
```

---

### 5.4 `round_controller/controller.py` の修正

1. **`__init__`** (既存 L52-107): `team_config_path` 引数名は維持（呼び出し側互換）。`load_team_settings()` → `load_unit_settings()` へ差し替え、戻り値の型で strategy を決定:

   ```python
   unit_settings = config_manager.load_unit_settings(team_config_path)
   self._unit_settings = unit_settings
   self.team_id = unit_settings.team_id
   self.team_name = unit_settings.team_name
   if isinstance(unit_settings, TeamSettings):
       self._strategy: ExecutionStrategy = LeaderStrategy(unit_settings, workspace)
       self.team_config = team_settings_to_team_config(unit_settings)  # LeaderStrategy 内部でのみ使用
   elif isinstance(unit_settings, WorkflowSettings):
       self._strategy = WorkflowStrategy(unit_settings, workspace)
       self.team_config = None  # workflow には Leader/TeamConfig の概念がない
   else:
       raise TypeError(...)
   ```

   `get_team_id()` / `get_team_name()` は `self.team_id` / `self.team_name` を返すように変更。

2. **`self.team_config.team_id` / `.team_name` 参照の差し替え** (重要):

   controller.py に約 30 箇所（正確な件数は `grep -n "self\.team_config" controller.py` で確認）。workflow では `self.team_config = None` になるため、全参照を `self.team_id` / `self.team_name` に差し替え。

   **一括置換禁止**: `self.team_config.members` / `.leader` など他アクセスが紛れる。手順: (1) `grep` で全件目視 → (2) `Edit` で 1 ヶ所ずつ → (3) 各修正後に `grep` で残件確認 → (4) `self.team_config` 単独参照（L88, L300 の `create_leader_agent(self.team_config, ...)`）は LeaderStrategy に移植されるため workflow 到達しない経路と確認。

3. **`_execute_single_round`** (既存 L266-413):
   - 「Member Agents 作成」「Leader Agent 実行」部分を `strategy.execute(user_prompt, deps)` 1呼び出しに置換
   - それ以降（`MemberSubmissionsRecord` 生成 → `save_aggregation` → Evaluator → `save_to_leader_board` → `save_round_status` → `on_round_complete`）は **#2 置換以外無変更**
   - `message_history` は `StrategyResult.all_messages` 経由（team: Leader の all_messages / workflow: D3 連結）
   - **`on_round_complete` hook と `run_round(user_prompt, timeout_seconds)` シグネチャは変更しない**

4. **`_format_prompt_for_round` / `_should_continue_round` / `_finalize_and_return_best`**: **#2 置換以外無変更**。PromptBuilder / JudgmentClient は `team_id`/`team_name` のみ使うので透過的に動く。UserPromptBuilder の Round 2 以降拡張（前ラウンド submission/score/feedback 埋め込み）は workflow 側で `user_prompt` フィールドとして JSON payload の外側に入る。各 agent executor は system_instruction で「入力は `{user_prompt, previous_steps}` JSON 文字列、json.loads して参照」を明示する責務は設計者側。

5. **進捗ファイル (`_write_progress_file` の `current_agent`)**: workflow mode は MVP で `None` 統一（UI 影響最小化）

---

### 5.5 `orchestrator/orchestrator.py` の修正

**3 箇所の `load_team_config()` 直呼びを差し替え**（既存 L186-218）:

```python
from mixseek.config.manager import ConfigurationManager
cm = ConfigurationManager(workspace=self.workspace)

# auth 確認 (L186-197): primary_model を _primary_model_of() 経由で取得して get_auth_info()
for team_config_path in task.team_configs:
    unit_settings = cm.load_unit_settings(team_config_path)
    primary_model = _primary_model_of(unit_settings)  # team → leader.model、workflow → 先頭 agent executor の model
    if primary_model:
        auth_info = get_auth_info(primary_model)
        logger.debug(f"Unit {unit_settings.team_id}: Model={primary_model}, ...")

# team_id 重複チェック (L199-208): unit_settings.team_id で既存 team ロジックを再利用
# TeamStatus 初期化 (L210-218): TeamStatus(team_id=unit_settings.team_id, team_name=unit_settings.team_name)
```

**`_primary_model_of` ヘルパー**:

```python
def _primary_model_of(unit_settings: "TeamSettings | WorkflowSettings") -> str | None:
    """代表モデル ID を取得（`get_auth_info` 用）。
    - Team: `leader.model`（TOML 未指定時は `LeaderAgentSettings` のデフォルト）。
    - Workflow: `WorkflowSettings.default_model`。
    """
    if isinstance(unit_settings, TeamSettings):
        return unit_settings.leader.get("model") or LeaderAgentSettings.model_fields["model"].default
    if isinstance(unit_settings, WorkflowSettings):
        return unit_settings.default_model
    return None
```

`from mixseek.agents.leader.config import load_team_config`（L12）は削除、代わりに `from mixseek.config.schema import LeaderAgentSettings, TeamSettings, WorkflowSettings` を追加。

---

### 5.6 `config/manager.py` の追加 API

**top-level import に追加**（既存の TYPE_CHECKING ブロック外、絶対 import で統一）:

```python
from mixseek.config.schema import TeamSettings, WorkflowSettings
from mixseek.config.sources.workflow_toml_source import WorkflowTomlSource
```

> 既存 `manager.py` は `TYPE_CHECKING` ブロックで schema 型を参照しているが、ランタイムで必要な上記シンボルは top-level に置く。相対 import（`from .schema import ...`）は使用しない。

**メソッド追加**:

```python
def load_workflow_settings(self, toml_file: Path, **extra) -> WorkflowSettings:
    return self._load_settings_with_tracing(
        WorkflowSettings, WorkflowTomlSource, toml_file, str(toml_file.name), **extra
    )

def load_unit_settings(self, toml_file: Path, **extra) -> TeamSettings | WorkflowSettings:
    """[team] / [workflow] トップレベルキーで判別。
    判別用に一度パスを解決してパースするが、下流ローダーには元の toml_file を渡す（内部で workspace 基準に再解決、二重解決は起きない）。"""
    resolved = toml_file if toml_file.is_absolute() else (self.workspace / toml_file if self.workspace else toml_file)
    with open(resolved, "rb") as f:
        data = tomllib.load(f)
    has_team = "team" in data
    has_workflow = "workflow" in data
    if has_team and has_workflow:
        raise ValueError(f"Config {toml_file} contains both [team] and [workflow].")
    if has_team:
        return self.load_team_settings(toml_file, **extra)
    if has_workflow:
        return self.load_workflow_settings(toml_file, **extra)
    raise ValueError(f"Config {toml_file} contains neither [team] nor [workflow].")
```

---

### 5.7 `config/sources/workflow_toml_source.py`（新規）

既存 `team_toml_source.py` を雛形に実装:

- `[workflow]` セクション必須（`if "workflow" not in data: raise`）
- `workflow` 配下を平坦化:
  ```python
  wf = data["workflow"]
  self.toml_data = {
      "workflow_id": wf.get("workflow_id"),
      "workflow_name": wf.get("workflow_name"),
      "include_all_context": wf.get("include_all_context", True),
      "final_output_format": wf.get("final_output_format", "json"),
      "steps": wf.get("steps", []),   # 各 step は {id, executors: [...]}
  }
  ```
- MVP: executor の `config = "..."` 参照解決は**しない**（Non-goal）
- `get_field_value` / `prepare_field_value` / `__call__` は team_toml_source と同形

---

### 5.8 Preflight 対応

現行 `_validate_teams` の「全 config が必ずどこかの validator で ERROR 化される」性質を維持する（§10）。

#### 5.8.1 `validators/workflow.py`（新規）

`_validate_workflows(settings, workspace, unit_kind_map) -> (CategoryResult, list[WorkflowSettings])`。`unit_kind_map[config] == "workflow"` のエントリのみ `ConfigurationManager.load_workflow_settings()` で検証し `CheckResult` を積む。それ以外は skip（`_validate_teams` 側で処理される）。

#### 5.8.2 `validators/team.py`（変更）

`_validate_teams(settings, workspace, *, unit_kind_map=None)`。`unit_kind_map` で `kind == "workflow"` のみ skip、**それ以外（"team" / "unknown"）は全て `load_unit_settings()` で検証**（`FileNotFoundError` / `TOMLDecodeError` / `ValueError` を ERROR 化）。戻りは `isinstance(result, TeamSettings)` を assert（想定外の `WorkflowSettings` を検出）。`unit_kind_map` 未指定時は既存挙動（全 config を `load_team_settings` で検証）。

#### 5.8.3 `runner.py`（変更）

```python
unit_kind_map = {
    entry.get("config"): _detect_unit_kind(Path(entry["config"]), resolved_workspace)
    for entry in orch_settings.teams
}
team_result, team_settings_list = _validate_teams(orch_settings, resolved_workspace, unit_kind_map=unit_kind_map)
wf_result, workflow_settings_list = _validate_workflows(orch_settings, resolved_workspace, unit_kind_map=unit_kind_map)
categories.extend([team_result, wf_result])
auth_result = _validate_auth(team_settings_list, evaluator_settings, judgment_settings,
                             workflow_settings_list=workflow_settings_list)
```

**`_detect_unit_kind`** (`validators/__init__.py`、`tomllib` は module top-level で import):

```python
def _detect_unit_kind(config_path: Path, workspace: Path) -> Literal["team", "workflow", "unknown"]:
    """TOML dispatch 先判定。"unknown" は team validator 側で ERROR 化（§10）。"""
    resolved = config_path if config_path.is_absolute() else (workspace / config_path)
    try:
        with open(resolved, "rb") as f:
            data = tomllib.load(f)
    except (FileNotFoundError, tomllib.TOMLDecodeError, OSError):
        return "unknown"  # team validator 側で load_unit_settings が例外を出し ERROR 化
    has_team = "team" in data
    has_workflow = "workflow" in data
    if has_team and not has_workflow: return "team"
    if has_workflow and not has_team: return "workflow"
    return "unknown"  # 両方あり / どちらもなし → team validator 側でエラー化
```

#### 5.8.4 `validators/auth.py`（変更）

`_collect_model_ids(...)` と `_validate_auth(...)` に `*, workflow_settings_list: list[WorkflowSettings] | None = None` を追加。workflow からは **`default_model`** と各 agent executor の `model`（指定されている場合のみ）を収集（function は model なしで無視）:

```python
for wf in (workflow_settings_list or []):
    model_ids.add(wf.default_model)  # デフォルトモデルも必ず認証検証対象に含める
    for step in wf.steps:
        for exe in step.executors:
            if isinstance(exe, AgentExecutorSettings) and exe.model:
                model_ids.add(exe.model)
```

既存 positional 呼び出しは互換維持（キーワード引数 + default）。team 側の dict/Pydantic 両対応（既存 `auth.py:50-67` 参照）は触らない。workflow 側は Pydantic validation 経由のため `AgentExecutorSettings` インスタンス前提で OK。

---

### 5.9 その他の修正ポイント

- `src/mixseek/workflow/__init__.py`: `WorkflowEngine`, `WorkflowStepFailedError`, `AgentExecutable`, `Executable`, `FunctionExecutable`, `build_executable`, `ExecutableOutput`, `ExecutableResult`, `StepResult`, `StrategyResult`, `WorkflowContext`, `WorkflowResult` を re-export
- `src/mixseek/round_controller/__init__.py`: `ExecutionStrategy`, `LeaderStrategy`, `WorkflowStrategy` を追加
- `src/mixseek/config/__init__.py`: `WorkflowSettings` 等を追加 export（optional）
- `src/mixseek/config/member_agent_loader.py`: `_resolve_bundled_system_instruction(agent_type, system_instruction, workspace) -> str` を抽出（既存 `member_settings_to_config` の L54-78 を切り出し）。`member_settings_to_config` / `AgentExecutorSettings.to_member_agent_config` の両方から呼ぶことで team/workflow の bundled 補完挙動を一致させる（DRY原則）。本ヘルパーは `schema.py` から **top-level import** される（`member_agent_loader.py` は `schema.py` を TYPE_CHECKING でしか参照しないため循環しない）
- `load_team_config()`・CLI (`cli/commands/team.py` 等): **無変更**（legacy として残す）

---

## 6. DuckDB persistence mapping

| 保存先 | チームモード | ワークフローモード |
|-------|-----------|------------------|
| `round_history.member_submissions_record` | `MemberSubmissionsRecord(submissions=list[MemberSubmission])` | **同一形式**。各 executor 結果を `MemberSubmission` として積む。`agent_name`=executor 名、`agent_type`=`"plain"`/`"web_search"`/`"custom"`/`"function"` |
| `round_history.message_history` | Leader の `result.all_messages()` | **全 agent executor の all_messages を step 順 × executor 定義順で連結**（D3）。function は空なので影響なし |
| `leader_board.submission_content` | Leader の `result.output`（str） | `_build_submission_content()` の整形結果（`include_all_context` と `final_output_format` 依存） |
| `leader_board.score` / `score_details` | Evaluator の結果 | **同一**（Evaluator は submission_content を見るだけ） |
| `leader_board.final_submission` / `exit_reason` | `_finalize_and_return_best` | **同一** |
| `round_status` | `_should_continue_round` + `_finalize_and_return_best` | **同一** |
| `execution_summary` | Orchestrator | **同一** |

**既存スキーマ変更なし**。`agent_type` は JSON 内の文字列なので `"function"` を追加しても DB スキーマ影響なし。集計クエリ（`get_leader_board_ranking` 等）は `agent_type` を直接参照しないため UI 改修不要。

---

## 7. Logging & observability

- **Agent executor**: `AgentExecutable` → `BaseMemberAgent.execute()` → `Agent.run()` → `instrument_pydantic_ai()` 自動 span。team モード（Leader の tool 経由）と**同じ機構**。`MemberAgentLogger` も既存通り
- **Function executor**: `instrument_pydantic_ai()` 対象外 → `FunctionExecutable.run` 内で `logfire.span("workflow.function", ...)` を手動で張る
- **WorkflowEngine**: `logfire.span("workflow.engine.run", workflow_id=..., workflow_name=..., round_number=..., step_count=...)` で Leader span 階層を補完
- **logger**: `mixseek.workflow.function`（start/complete/timeout/error）と `mixseek.workflow.engine`（MVP は warning/error のみ）。親 `mixseek` logger に `LogfireLoggingHandler` が addHandler されているため Logfire クラウドに送られる

---

## 8. Test plan

### 8.1 単体テスト（新規）

| テストファイル | 対象 |
|-------------|-----|
| `tests/unit/workflow/test_executable.py` | `AgentExecutable` の正常/例外、`FunctionExecutable` の sync/async/例外、`build_executable` の型分岐、`_load_function` のエラー |
| `tests/unit/workflow/test_engine.py` | 単一/並列ステップ、include_all=true/false、fmt=json/text の 4 ケース（A/B/C/D）、agent soft failure（submission 積まれる、継続）、function hard failure（`WorkflowStepFailedError` 昇格）、submission 積み順 |
| `tests/unit/workflow/test_models.py` | `WorkflowContext.build_task_prompt` の JSON スキーマ、`_serialize` |
| `tests/unit/config/test_workflow_settings.py` | `WorkflowSettings` validation（workflow_id/name 必須、step ids 重複、executor names 重複、`default_model` 省略可、agent executor の `model` 省略時 `default_model` フォールバック、type="function" で model 不要）、`team_id`/`team_name` プロパティ |
| `tests/unit/config/test_workflow_toml_source.py` | `[workflow]` 読み込み、`[team]` 混在時の挙動 |
| `tests/unit/config/test_unit_settings.py` | `load_unit_settings()` で team/workflow 振り分け、両方 or どちらも無い TOML は ValueError |
| `tests/unit/round_controller/test_strategy.py` | `LeaderStrategy` が既存挙動を再現、`WorkflowStrategy.execute` が WorkflowEngine を呼ぶ |

### 8.2 統合テスト（新規）

| テスト | 内容 |
|-------|-----|
| `tests/integration/test_workflow_round_controller.py` | 2 step（agent 並列 → function → agent）で `RoundController.run_round` を走らせ、`round_history` / `leader_board` / `round_status` が team と同じ形式で保存されることを確認。モデルは既存 test_model を使用 |
| `tests/integration/test_workflow_orchestrator.py` | `orchestrator.toml` に `[team]` と `[workflow]` を混在させ並列実行で両方成功、`execution_summary` に両方入ることを確認 |
| `tests/integration/test_workflow_hard_failure.py` | 最初のラウンドで function 例外 → `TeamStatus="failed"`、2 ラウンド目成功後に function 失敗 → `PartialTeamFailureError` で best_round 採用 |

### 8.3 既存テストの影響

`LeaderStrategy.execute` が `create_leader_agent` を呼ぶため、patch 先が `controller` から `strategy` に移動する。実装前に `grep -rn "mixseek.round_controller.controller\." tests/` で全箇所洗う。

- **`create_leader_agent` patch**: `mixseek.round_controller.controller.create_leader_agent` → `mixseek.round_controller.strategy.create_leader_agent`（unit/round_controller 配下・integration の prompt_builder/orchestrator_e2e に計 15 箇所）
- **`load_team_settings` patch**: `mixseek.round_controller.controller.*` → `load_unit_settings` に差し替え
- **`orchestrator.load_team_config` patch**: `load_unit_settings` ベースのモックに差し替え
- **その他**: controller → strategy に移動する `team_settings_to_team_config`, `MemberAgentFactory` 等も patch パス見直し
- **除外**: CLI 層（`tests/unit/cli/test_team_command.py`）、patch していない `test_leader_agent_e2e.py` / `test_http_timeout.py`

### 8.4 サンプル config の追加

実装者が E2E 動作確認できるよう `examples/workflow-sample/` を追加:

```
examples/workflow-sample/
├── configs/
│   ├── orchestrator.toml
│   └── workflows/
│       └── workflow_research.toml
└── mypackage/
    ├── __init__.py
    └── formatters.py
```

**`configs/orchestrator.toml`**:

```toml
[orchestrator]
task = "量子コンピュータの最新動向をまとめて"
max_rounds = 3
min_rounds = 1

[[orchestrator.teams]]
config = "configs/workflows/workflow_research.toml"

[orchestrator.evaluator]
model = "google-gla:gemini-2.5-flash"

[orchestrator.judgment]
model = "google-gla:gemini-2.5-flash"
```

**`configs/workflows/workflow_research.toml`**:

```toml
[workflow]
workflow_id = "research-pipeline"
workflow_name = "Research Pipeline"
default_model = "google-gla:gemini-2.5-flash"
include_all_context = true
final_output_format = "json"

# Step 1: 情報収集（agent executors 複数 → 並列）
[[workflow.steps]]
id = "gather"

[[workflow.steps.executors]]
name = "web-searcher"
type = "web_search"
...

[[workflow.steps.executors]]
name = "academic-searcher"
type = "plain"
...

# Step 2: 整形（Python 関数）
[[workflow.steps]]
id = "format"

[[workflow.steps.executors]]
name = "markdown-formatter"
type = "function"

[workflow.steps.executors.plugin]
module = "mypackage.formatters"
function = "format_as_markdown"

# Step 3: 統合（model を個別に上書きする例）
[[workflow.steps]]
id = "synthesize"

[[workflow.steps.executors]]
name = "synthesizer"
type = "plain"
...
```

**`mypackage/formatters.py`**:

```python
"""Workflow function executor サンプル。入力: `{user_prompt, previous_steps}` JSON 文字列、出力: str。"""
import json

def format_as_markdown(input: str) -> str:
    payload = json.loads(input)
    user_prompt: str = payload["user_prompt"]
    previous: dict = payload.get("previous_steps", {})
    lines: list[str] = [f"# {user_prompt}\n"]
    ...
```

**注意**: `mypackage` は `importlib.import_module` 解決 → `PYTHONPATH=examples/workflow-sample` か `pip install -e examples/workflow-sample/` 必要（§10）。

---

## 9. Verification

- **静的**: `make -C dockerfiles/ci lint format-check`、`make -C dockerfiles/ci type-check`
- **テスト**: `make -C dockerfiles/ci test-fast`、`pytest tests/unit/workflow tests/integration/test_workflow_round_controller.py -v`
- **E2E**: `cp -rp examples/workflow-sample workspaces/` → `export MIXSEEK_WORKSPACE=...` → `mixseek exec "<prompt>" --config $MIXSEEK_WORKSPACE/configs/orchestrator.toml`
  - 期待: `round_history` に `team_id="research-pipeline"` が round_number=1..N 分、`member_submissions_record` に `agent_type="web_search"/"plain"/"function"` 混在、`leader_board.final_submission=true` が 1 件、`execution_summary.status="completed"`
  - `LOGFIRE_ENABLED=1`: `orchestrator.execute` → `round_controller.run_round` → `pydantic-ai` spans + `mixseek.workflow.function` log レコード
- **リグレッション**: `examples/orchestrator-sample` (team モード)、`mixseek preflight` で team/workflow 混在 TOML 確認

---

## 10. Risks / Edge cases

| リスク | 対応 |
|------|----|
| `WorkflowSettings.@property team_id` と `extra="forbid"` の衝突 | `@property` はフィールド扱いされず安全。serialize 非出力なので DB 保存時は `workflow_id` または property 経由で明示 |
| `AgentExecutorSettings` / `MemberAgentSettings` の二重管理 | MVP は並立、共通ベース抽出は将来 Refactor |
| Function `Callable` 署名が `(str) -> str` から外れる | `run` 内で `str(content)` 強制。型不一致は TOML 設計者責任 |
| 並列 executor 両方失敗 | Engine は全 executor 完了後に昇格判定。agent submission は append されるがラウンド廃棄で DB に残らない（team と同じ） |
| `FunctionPluginMetadata.module` の import 解決 | `importlib.import_module` → `sys.path` 依存。MVP は `pip install -e .` か `PYTHONPATH` 前提。`path = "<file>"` は将来拡張 |
| `MemberSubmission.all_messages` 空リスト | team mode でも None/list 両方来る（custom→None、pydantic-ai→空 list）。正規化せず渡す（DB の to_jsonable_python が両方処理） |
| Function ハング | `timeout_seconds`（default None=無制限）。設定時は `asyncio.wait_for` で包み TimeoutError → `ERROR` で即昇格 |
| `timeout_seconds` の下限スキーマ不整合 | 既存 `MemberAgentSettings.timeout_seconds: ge=0` / `MemberAgentConfig.timeout_seconds: ge=1` のギャップが「設定段階で通るが実行段階で落ちる」遅延失敗を生んでいた。本プランで**両方 `ge=1` に統一**（`AgentExecutorSettings` および既存 `MemberAgentSettings` の両方）。既存 TOML に `timeout_seconds=0` の用例は無いため回帰なし。team/workflow 対称性も維持 |
| `submission_content` の Round 再帰膨張 | `_build_submission_content` で `user_prompt` フィールドを**絶対に含めない**設計で回避（§5.2.4）。`UserPromptBuilder` が `format_submission_history` で次ラウンド以降の prompt に `submission_content` を埋め込むため、`submission_content` 側に `user_prompt` を含めると指数膨張する |
| `logfire` 非導入環境での workflow 死 | `WorkflowEngine.run` / `FunctionExecutable.run` は `_logfire_span` ヘルパー経由で `try/except ImportError` + `nullcontext` fallback。`round_controller/controller.py:34` の `LOGFIRE_AVAILABLE` と同じ方針で team モードと対称 |
| `build_executable` / `_load_function` の例外漏れ | Preflight でも `_load_function` 検証するが、動的 import は実行時まで解決しない。`WorkflowEngine._execute_step` で `build_executable` を try/except し、失敗時は `WorkflowStepFailedError` に昇格（function ハード失敗と同じ経路） |
| Agent executor の bundled `system_instruction` 補完欠落 | `AgentExecutorSettings.to_member_agent_config()` から共通ヘルパー `_resolve_bundled_system_instruction`（`config/member_agent_loader.py` に抽出）経由で bundled 読み込み。team の `member_settings_to_config` と**同じ**経路を通る |
| Preflight の判別失敗 skip 回帰 | `_detect_unit_kind` は `"team"` / `"workflow"` / `"unknown"` を返す。`"unknown"`（TOML 解析失敗・両方あり・どちらもなし）は team validator 側で `load_unit_settings` を呼び `ValueError` / `FileNotFoundError` を ERROR CheckResult 化（現行の全 failure 検出性を維持） |

---

## 11. 実装順序の推奨

1. **Schema**: `config/schema.py` に `FunctionPluginMetadata` / `AgentExecutorSettings`（`model` は Optional）/ `FunctionExecutorSettings`（`timeout_seconds: ge=1`）/ `WorkflowStepSettings` / `WorkflowSettings`（`default_model` フィールドあり）を追加 + 単体テスト。**併せて既存 `MemberAgentSettings.timeout_seconds` を `ge=0` → `ge=1` に揃える**（下流 `MemberAgentConfig` と一致、遅延失敗回避）。`tests/` 配下に `timeout_seconds=0` の MemberAgent 用例が無いことを確認済み
2. **member_agent_loader 共通化**: `_resolve_bundled_system_instruction(agent_type, system_instruction, workspace)` を切り出し、既存 `member_settings_to_config` をそのヘルパー経由にリファクタ（回帰防止テストを先に通す）
3. **Source/Manager**: `workflow_toml_source.py` + `load_workflow_settings` + `load_unit_settings` + テスト
4. **Workflow package**: `models.py` → `executable.py`（`_logfire_span` ヘルパー含む）→ `engine.py` → `exceptions.py` の順、各段階でテスト
5. **Strategy**: `round_controller/strategy.py` に `LeaderStrategy` / `WorkflowStrategy`。LeaderStrategy は既存 controller.py の切り出しなので壊れにくい
6. **RoundController 差し替え**: `__init__` と `_execute_single_round` を差し替え。**既存テストが通ることを最初に確認**
   - `self.team_config.team_id` / `.team_name` 約30箇所は**一括置換禁止**（`self.team_config.members` など他アクセスが紛れる）。1 ヶ所ずつ `Edit`、各段階で `grep -n "self\.team_config\.team_id" ...` 残件確認
7. **Orchestrator 差し替え**: 3 箇所の `load_team_config` を `load_unit_settings` 経由へ
8. **Preflight**: team validator（`load_unit_settings` に切り替え）→ workflow validator → runner dispatch → auth 拡張の順。`_detect_unit_kind` の `"unknown"` が team validator でエラー化されることを必ずテスト
9. **Sample & E2E**: `examples/workflow-sample` 追加 → 実機実行 → DuckDB / logfire 確認

---

## 12. Critical files reference

行番号は変動する可能性があるため grep/読込で位置を再確認してから使う。

- `src/mixseek/agents/leader/models.py` — `MemberSubmission` / `MemberSubmissionsRecord`
- `src/mixseek/agents/leader/dependencies.py` — `TeamDependencies`
- `src/mixseek/agents/leader/tools.py` — member 実行時の `MemberSubmission` 構築
- `src/mixseek/agents/member/base.py` / `plain.py` — `BaseMemberAgent.execute` の契約
- `src/mixseek/agents/member/factory.py` — `MemberAgentFactory.create_agent`
- `src/mixseek/config/member_agent_loader.py` — `member_settings_to_config` 変換
- `src/mixseek/config/schema.py` — `MemberAgentSettings`（AgentExecutorSettings 雛形）/ `TeamSettings`（WorkflowSettings 雛形）
- `src/mixseek/config/sources/team_toml_source.py` — `WorkflowTomlSource` の雛形
- `src/mixseek/config/manager.py` — `load_team_settings` / `_load_settings_with_tracing`
- `src/mixseek/round_controller/controller.py` — `_execute_single_round`（差し替え対象、L266-413 付近）
- `src/mixseek/orchestrator/orchestrator.py` — `load_team_config` 直呼び 3 箇所（L186-218 付近）
- `src/mixseek/storage/aggregation_store.py` — 既存テーブル DDL（変更不要）
- `src/mixseek/observability/logfire.py` — `instrument_pydantic_ai`（変更不要）
