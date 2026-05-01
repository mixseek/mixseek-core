# MixSeek-Core Workflow Mode サンプル

このサンプルは MixSeek の **workflow mode** (固定ステップで agent / function を順次・並列実行)
の最小構成です。3 ステップの research pipeline を題材に、

- workflow TOML の書き方 (`[workflow]` / `[[workflow.steps]]` / `[[workflow.steps.executors]]`)
- function executor のプラグイン指定方式 (**`path`** / **`module`** / カスタムメンバーエージェントと同じ流儀)
- DuckDB に保存される workflow 実行履歴の確認方法
- logfire span の確認方法

を示します。

## 📋 概要

### 処理フロー

```
User Prompt
    ↓
[Step 1: gather] web_search agent ─┐
                                   ├─ asyncio.gather で並列実行
                  plain agent ─────┘
    ↓
[Step 2: format] Python function (Markdown 整形)
    ↓
[Step 3: synthesize] plain agent (最終回答生成)
    ↓
DuckDB / logfire に記録
```

### ファイル構成

```
examples/workflow-sample/
├── configs/
│   ├── orchestrator.toml                # orchestrator 設定 (workflow を 1 件登録)
│   └── workflows/
│       └── workflow_research.toml       # 3 ステップ workflow 定義
└── mypackage/
    └── formatters.py                    # function executor 実装 (path 方式)
```

`mypackage/__init__.py` は **作成しません**。`path` 方式
(`_load_module_from_path`) は `importlib.util.spec_from_file_location` でファイルを
直接ロードするため、`mypackage/` を Python package にする必要がありません。

## 🚀 Quick start

```bash
# 1. ワークスペースを準備
cp -rp examples/workflow-sample workspaces/
export MIXSEEK_WORKSPACE="$PWD/workspaces/workflow-sample"
export GOOGLE_API_KEY="..."   # GEMINI_API_KEY でも可

# 2. 必ず workspace ディレクトリへ移動する (path 方式の cwd 起点解決のため)
cd "$MIXSEEK_WORKSPACE"

# 3. 設定ファイルの dry-run (preflight) で TOML 構文 / schema を検証
mixseek exec --dry-run --config configs/orchestrator.toml

# 4. 本実行
mixseek exec "量子コンピュータの最新動向をまとめて" --config configs/orchestrator.toml
```

> **`cd "$MIXSEEK_WORKSPACE"` を忘れない**
>
> `workflow_research.toml` の function plugin は `path = "mypackage/formatters.py"` という
> 相対 path で書かれています。相対 path は **cwd を起点に解決される** ため、
> workspace 以外のディレクトリで `mixseek exec` を呼ぶと
> `Failed to load function from path 'mypackage/formatters.py'` で実行時エラーになります。
> 詳細は下記の「Function plugin の指定方式」セクション参照。

## 🔧 Function plugin の指定方式

Function executor は `[workflow.steps.executors.plugin]` で **`path`** または **`module`** を排他指定で渡します。
カスタムメンバーエージェント (`examples/custom_agents/`) と同じく、ファイルパス指定とモジュール指定の
2 通りに対応しているため、用途に応じて使い分けてください。`function` は呼び出す関数名です。

| 方式 | TOML 例 | 何を指定するか | 使いどころ |
|---|---|---|---|
| `path` | `path = "mypackage/formatters.py"` | Python ファイルへのパス (絶対 / 相対) | サンプルや単発スクリプト。`PYTHONPATH` / `pip install` 不要 |
| `module` | `module = "mypackage.formatters"` | `sys.path` から解決可能な Python module | `pip install -e .` 済みのパッケージや本番運用 |

排他制約は `FunctionPluginMetadata` (`src/mixseek/config/schema.py`) で検証されます。

### `path` 方式 (本サンプルで採用)

```toml
[workflow.steps.executors.plugin]
path = "mypackage/formatters.py"
function = "format_as_markdown"
```

- `PYTHONPATH` の設定や `pip install` は **不要** です。
- ロード処理: `mixseek.workflow.executable._load_module_from_path` が
  `importlib.util.spec_from_file_location` で対象ファイルを直接読み込みます
  (member 側 `load_agent_from_path` と同じ流儀)。
- 相対 path は **cwd 起点** で解釈されます。よって本サンプル実行時は必ず
  `cd "$MIXSEEK_WORKSPACE"` してから `mixseek exec` を呼んでください。
- 絶対 path で書きたい場合は `path = "/abs/path/to/mypackage/formatters.py"` のように
  指定すれば cwd 制約を外せます (環境差で値をハードコードできないため、本サンプルでは
  相対 path を採用)。
- **`mixseek exec --dry-run` は path のファイル存在を検証しません**。
  preflight は `WorkflowSettings` の Pydantic schema 検証
  (`module` / `path` 排他制約等) のみで、`_load_module_from_path` は本実行時にしか
  走りません (`src/mixseek/config/preflight/validators/workflow.py` 参照)。
  dry-run が OK でも cwd を間違えれば本実行で `WorkflowStepFailedError` で落ちるため、
  Quick start の `cd "$MIXSEEK_WORKSPACE"` は必須です。
- **SECURITY**: `_load_module_from_path` は module レベルコードを実行するため、
  信頼できないファイルを `path` に指定しないでください (member 側の制約と同じ)。

### `module` 方式 (代替)

`pip install -e .` などで `sys.path` 上に置いてあるパッケージから関数をロードしたい場合は
`path` の代わりに `module` を指定します。カスタムメンバーエージェントの `agent_module` と
同じ感覚で書けます。

```toml
[workflow.steps.executors.plugin]
module = "mypackage.formatters"
function = "format_as_markdown"
```

- ロード処理: `importlib.import_module(module)` で解決します。
- `module` 方式では対象を Python package として import 可能にする必要があるため、
  `mypackage/__init__.py` を用意してください (`path` 方式では不要)。
- cwd への依存がなくなるため、`cd "$MIXSEEK_WORKSPACE"` は必須ではありません。代わりに
  `mypackage` を `sys.path` から import 可能にする責務がユーザ側に移ります
  (`pip install -e .` / `PYTHONPATH` 等)。
- `module` と `path` は同時指定不可です（`FunctionPluginMetadata` で排他検証）。

## 📊 DuckDB で実行結果を確認

```bash
duckdb "$MIXSEEK_WORKSPACE/mixseek.db"
```

```sql
-- 1. 各ラウンドの member submissions 件数 (web-searcher / academic-summarizer /
--    markdown-formatter / synthesizer の 4 件が並ぶはず)
SELECT
    team_id,
    round_number,
    json_array_length(member_submissions_record::JSON, '$.submissions') AS n
FROM round_history
WHERE team_id = 'research-pipeline'
ORDER BY round_number;

-- 2. agent_type の混在 (web_search / plain / function が出るはず)
SELECT DISTINCT json_extract_string(s.value, '$.agent_type') AS agent_type
FROM round_history,
     LATERAL json_each(member_submissions_record::JSON, '$.submissions') AS s
WHERE team_id = 'research-pipeline';

-- 3. 最終 submission (final_submission = TRUE) が 1 件
SELECT round_number, score, exit_reason
FROM leader_board
WHERE team_id = 'research-pipeline' AND final_submission = TRUE;

-- 4. execution_summary が `completed` で記録されている
SELECT status, best_team_id, best_score
FROM execution_summary
ORDER BY created_at DESC
LIMIT 1;
-- 期待: status = 'completed', best_team_id = 'research-pipeline'
```

## 📡 Logfire span 確認 (任意)

```bash
export LOGFIRE_ENABLED=1
export LOGFIRE_TOKEN="..."
mixseek exec "..." --config configs/orchestrator.toml
```

期待する span 階層:

```
orchestrator.execute (execution_id, team_count=1)
  └ round_controller.run_round (team_id="research-pipeline")
      └ workflow.engine.run (workflow_id="research-pipeline", step_count=3)
          ├ pydantic_ai (gather: web-searcher)         # instrument_pydantic_ai による自動 span
          ├ pydantic_ai (gather: academic-summarizer)  # 同上
          ├ workflow.function (function_name="markdown-formatter", timeout_seconds=30)
          └ pydantic_ai (synthesize: synthesizer)
```

`mixseek.workflow.function` logger には `function_execution_start` /
`function_execution_complete` のレコードが出ます。

## 🐛 トラブルシューティング

### `Failed to load function from path 'mypackage/formatters.py'`

```
Failed to load function from path 'mypackage/formatters.py'.
FileNotFoundError: File not found or is not a regular file. Check file path in TOML config.
```

- **原因**: `cd "$MIXSEEK_WORKSPACE"` を忘れて他のディレクトリから実行している。
- **対処**: `cd "$MIXSEEK_WORKSPACE"` してから再実行する。
- **注意**: `mixseek exec --dry-run` はこのエラーを検出できません (preflight は schema
  検証のみ)。本実行で初めて顕在化します。

### `auth: ... 認証に失敗`

- **原因**: `GOOGLE_API_KEY` (または `GEMINI_API_KEY`) が未設定。
- **対処**: `export GOOGLE_API_KEY="..."` してから再実行。

### `LOGFIRE_ENABLED=1` で span が見えない

- `logfire` パッケージが未インストールの場合は `nullcontext()` にフォールバックし、
  span は出力されません。`pip install logfire` を確認してください。
- `LOGFIRE_TOKEN` が未設定の場合、ローカルだけで span は記録されますが Logfire UI
  には送られません。

## 📚 関連ドキュメント

- 設計: `internal/workflow-mode/workflow-mode-plan.md`
- PR5 計画: `.logs/plans/internal-workflow-mode-workflow-mode-pl-piped-dream.md`
- function plugin の path 方式: PR4.5 (`FunctionPluginMetadata.path`) で追加
- team mode サンプル: `examples/orchestrator-sample/`

---

**Happy Workflow Mode! 🚀**
