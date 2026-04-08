# ロギングシステム統一リファクタリング計画

## コンテキスト

mixseek-coreのロギングは以下の問題を抱えている:
1. ログファイルが3種類に分散（mixseek.log / logfire.log / member-agent-*.log）
2. 同一のフォーマット文字列が3箇所で定義
3. logging.toml / logfire.toml のfrom_toml()が存在するが、実際にTOMLファイルを配置して運用している実態がない（コード上は`LogfireConfig.from_toml()`が3箇所で呼ばれている）
4. MemberAgentLoggerが独自ハンドラを持つ
5. ログフォーマットを統一的にjsonに切り替えることができない

## 決定事項（ユーザ承認済み）

- ロガー名: "mixseek" 固定
- コンソール出力先: sys.stderr（CLI の --output-format json が stdout を使うため競合回避）
- 設定: `--log-format` CLIフラグ + `MIXSEEK_LOG_FORMAT` 環境変数でサポート、logging.toml/logfire.toml のfrom_toml()廃止
- MemberAgentLogger: 独自ハンドラ廃止、統一ロガーに集約（API互換不要、完全リファクタ）
- ローカルログファイル: mixseek.log に統一（logfire.log / member-agent-*.log 廃止）
- LogfireLoggingHandler: 維持（標準ログをLogfire cloudに転送）
- exit code: 設定エラー等の失敗は全失敗に該当するため code 2
- **stderr = mixseek.log 完全一致**: コンソール出力とファイル出力は常に同一内容
- **logfireスパンのログ統合**: logfireスパンもmixseek.logおよびstderrに記録する
- **log_format はlogfireフラグに依存しない**: text/json のどちらでも、logfire有無に関わらず適切に動作
- **text + logfire有効時**: ConsoleOptions スパンツリー維持。StreamHandler/FileHandler抑制し、全出力を ConsoleOptions → TeeWriter(stderr + mixseek.log) 経由に統一
- **json + logfire有効時**: ConsoleOptions 無効化。カスタム JsonSpanProcessor でスパンを構造化JSON化し、統一ロガー経由で StreamHandler(stderr) + FileHandler(mixseek.log) に出力
- **extra fields**: text形式では別行 key: value 形式で表示、json形式ではトップレベルフィールドとして出力
- **text/json で記録される情報は完全同一**: フォーマットのみ異なる

## 設計上の制約: exec.py の初期化順序

`exec.py` の `_execute()` は dry-run/プリフライトチェック機能により、以下の順序が確定している:

```
1. Logfireフラグ検証
2. ワークスペースパス解決（ConfigurationManager → CLI fallback）
3. 標準ロギング初期化
4. Logfire初期化
5. config必須チェック
6. プリフライトチェック → dry-run時はここで終了
7. 設定ロード（OrchestratorSettings）
8. Orchestrator初期化・実行
```

この順序により、`OrchestratorSettings` はロガー初期化後に読み込まれるため、
`log_format` を TOML 設定ファイルから取得してロガーに反映することはできない。
`log_format` は CLIフラグ `--log-format` と環境変数 `MIXSEEK_LOG_FORMAT` のみでサポートする。

## ターゲットアーキテクチャ

### 基本原則

- **stderr = mixseek.log 完全一致**: 同一のイベント・フィールドが両方に記録される
- **log_format は logfire フラグに依存しない**: text/json どちらも logfire 有無に関わらず動作
- **text/json で情報は同一**: フォーマット（表現形式）のみが異なる
- **ローカル出力と Logfire cloud の情報同一性**: 標準ログ + スパン（開始・完了）という情報セットはローカル・cloud ともに同一

### 4モードのハンドラ構成

#### Mode 1: logfire無効 + text

```
"mixseek" named logger
  ├─ StreamHandler(sys.stderr)  -- TextFormatter
  ├─ FileHandler(mixseek.log)   -- TextFormatter
  └─ propagate=False
```

#### Mode 2: logfire無効 + json

```
"mixseek" named logger
  ├─ StreamHandler(sys.stderr)  -- JsonFormatter
  ├─ FileHandler(mixseek.log)   -- JsonFormatter
  └─ propagate=False
```

#### Mode 3: logfire有効 + text

**最終状態**（setup_logfire() 完了後）:
```
"mixseek" named logger
  ├─ LogfireLoggingHandler      -- 標準ログをLogfire cloudに転送
  └─ propagate=False
  （StreamHandler/FileHandler は抑制: ConsoleOptionsが一括描画）

logfire.configure(
    console=ConsoleOptions(output=TeeWriter(sys.stderr, log_file_handle)),
    send_to_logfire=config.send_to_logfire,
    additional_span_processors=[],
)
logfire.instrument_pydantic_ai()
```

ConsoleOptionsがスパンツリー+標準ログを一括描画し、TeeWriterが
stderr と mixseek.log の両方に同一内容を書き込む。

**初期化順序とハンドラ付け替え**:

setup_logging() と setup_logfire() の間にはログ発行ウィンドウが存在する。
Mode 3 で最初から StreamHandler/FileHandler を抑制すると、この間のログが
ローカル（stderr/mixseek.log）に記録されない。「stderr = mixseek.log 完全一致」
原則に反するため、**2段階初期化**を採用する:

1. **setup_logging()**: Mode 1 と同様に StreamHandler + FileHandler + LogfireLoggingHandler を
   全て追加する（`use_console_options` フラグは設定するが、ハンドラ抑制はしない）
2. **setup_logfire() 内**: ConsoleOptions + TeeWriter 確立後、"mixseek" ロガーから
   StreamHandler/FileHandler を除去する（`finalize_mode3_handlers()` ヘルパー）

これにより、setup_logfire() 完了前のログも StreamHandler/FileHandler 経由で
ローカルに記録される。ConsoleOptions 有効化後は重複防止のためハンドラを除去する。

#### Mode 4: logfire有効 + json

```
"mixseek" named logger
  ├─ StreamHandler(sys.stderr)  -- JsonFormatter
  ├─ FileHandler(mixseek.log)   -- JsonFormatter
  ├─ LogfireLoggingHandler      -- 標準ログをLogfire cloudに転送
  │   └─ SkipTracesFilter       -- "mixseek.traces" からのレコードをスキップ（ループ防止）
  └─ propagate=False

"mixseek.traces" child logger   -- JsonSpanProcessor が書き込む先
  └─ propagate=True             -- 親 "mixseek" のハンドラに伝搬

logfire.configure(
    console=False,              -- ConsoleOptions無効（統一ロガーがJSON出力）
    send_to_logfire=config.send_to_logfire,
    additional_span_processors=[JsonSpanProcessor(traces_logger)],
)
logfire.instrument_pydantic_ai()
```

JsonSpanProcessor がスパンを構造化JSONに変換し、"mixseek.traces" ロガーに書き込む。
親 "mixseek" の StreamHandler/FileHandler が JSON として出力。
SkipTracesFilter により LogfireLoggingHandler への再送を防止（フィードバックループ回避）。

### Mode 3/4 でアーキテクチャが分かれる理由

Logfire の `ConsoleOptions` はスパンツリー（開始/終了/ネスト + 標準ログ埋め込み）を
**テキスト形式でのみ**描画する。JSON 出力する機能はない。この Logfire 側の制約により:

- **Mode 3 (logfire+text)**: ConsoleOptions がスパンツリーを描画し、TeeWriter 経由で
  stderr + mixseek.log に同時出力する。ConsoleOptions は標準ログもツリー内に統合するため、
  StreamHandler/FileHandler が生きていると**標準ログが二重出力**される。よって抑制が必要。
- **Mode 4 (logfire+json)**: ConsoleOptions は JSON を出せないため無効化する。
  代わりに StreamHandler/FileHandler を有効にし、JsonSpanProcessor がスパンを
  構造化 JSON に変換して "mixseek.traces" ロガー経由で出力する。SkipTracesFilter で
  LogfireLoggingHandler へのフィードバックループを防止する。

### 子ロガーの伝搬

子ロガー（`logging.getLogger(__name__)`）は "mixseek" 親ロガーに伝搬する。

### 4モードの出力内容一覧

| モード | stderr | mixseek.log | Logfire cloud |
|--------|--------|-------------|---------------|
| logfire無効 + text | TextFormatter による標準ログ | 同左（完全一致） | なし |
| logfire無効 + json | JsonFormatter による標準ログ | 同左（完全一致） | なし |
| logfire有効 + text | ConsoleOptions スパンツリー（標準ログ埋め込み） | 同左（完全一致、TeeWriter経由） | スパン + 標準ログ |
| logfire有効 + json | JsonFormatter 標準ログ + 構造化JSONスパン | 同左（完全一致） | スパン + 標準ログ |

### Logfire有効時の重複防止

- **text**: setup_logging() では StreamHandler/FileHandler を一時的に追加（ログ欠損防止）。
  setup_logfire() 内で ConsoleOptions + TeeWriter 確立後に finalize_mode3_handlers() で除去。
  最終的に ConsoleOptions が TeeWriter 経由で全出力を担当。
  LogfireLoggingHandler が標準ログを Logfire に転送 → ConsoleOptions がスパンツリー内に統合表示。
- **json**: ConsoleOptions 無効。StreamHandler/FileHandler が JSON 出力を担当。
  JsonSpanProcessor → "mixseek.traces" ロガー → 親 "mixseek" のハンドラ。
  SkipTracesFilter が LogfireLoggingHandler でのスパン由来レコード再送を防止。

### フォーマッタ仕様

#### TextFormatter（カスタム logging.Formatter）

メッセージの後に extra fields を別行 key: value 形式で表示:

```
2024-01-01 12:34:57 - mixseek.agents - INFO - Agent evaluation started
  agent: researcher
  score: 0.85
  duration_ms: 1500
```

extra fields がない場合はメッセージ行のみ:

```
2024-01-01 12:34:57 - mixseek - INFO - Starting orchestration
```

#### JsonFormatter

全フィールドをトップレベルキーとして出力。`type` フィールドで標準ログとスパンを区別:

```json
{"timestamp":"2024-01-01T12:34:57.000Z","type":"log","level":"INFO","logger":"mixseek.agents","message":"Agent evaluation started","agent":"researcher","score":0.85,"duration_ms":1500}
```

スパン（JsonSpanProcessor 経由）:

スパン開始（JsonSpanProcessor.on_start 経由）:

```json
{"timestamp":"2024-01-01T12:34:56.800Z","type":"span_start","level":"INFO","logger":"mixseek.traces","message":"orchestrator.run started","span_name":"orchestrator.run","span_id":"abc123","parent_span_id":null,"attributes":{"tag":"orchestrator"}}
```

スパン完了（JsonSpanProcessor.on_end 経由）:

```json
{"timestamp":"2024-01-01T12:34:58.900Z","type":"span_end","level":"INFO","logger":"mixseek.traces","message":"orchestrator.run completed","span_name":"orchestrator.run","span_id":"abc123","parent_span_id":null,"duration_ms":2100,"status":"ok","attributes":{"tag":"orchestrator"}}
```

### log_format の解決優先度（全CLIコマンド共通）:
1. `--log-format` CLIフラグ（最優先、`click.Choice(["text", "json"])` で入力制約）
2. `MIXSEEK_LOG_FORMAT` 環境変数（`LoggingConfig` の `log_format` フィールドで "text"/"json" のみ許可、不正値は `ValidationError`）
3. デフォルト値 "text"

---

## フェーズ1: Config層の修正

### 1.1 `src/mixseek/config/logging.py`

- `logfire_enabled` フィールド維持
- `from_toml()` メソッド削除
- `log_format: LogFormatType = Field(default="text")` 追加
- `from_env()` に `MIXSEEK_LOG_FORMAT` 読み取り追加
- `LevelName` 型に `"critical"` を追加（CLI の `--log-level` との整合性）
- `LOG_LEVEL_MAP` に `"critical": logging.CRITICAL` を追加

```python
LogFormatType = Literal["text", "json"]

class LoggingConfig(BaseModel):
    logfire_enabled: bool = Field(default=False)  # 維持
    console_enabled: bool = Field(default=True)
    file_enabled: bool = Field(default=True)
    log_level: LevelName = Field(default="info")
    log_format: LogFormatType = Field(default="text")  # 追加
    # log_file_path: REMOVED（どこからも使用されていない dead field。
    #   ファイル出力先は workspace/logs/mixseek.log で固定、setup_logging() が workspace 引数から決定）
```

### 1.2 `src/mixseek/config/logfire.py`

- `file_output` フィールド削除（logfire.log廃止。ファイル出力は LoggingConfig.file_enabled で制御）
- `console_output` フィールド維持（ConsoleOptions制御用）
- `from_toml()` メソッド削除
  - **注意**: `from_toml()` はプロダクションコードから3箇所で呼ばれている（下記）。
    ただし実際にTOMLファイルを配置して運用している実態がないため、廃止する。
    - `cli/utils.py:149` — CLIフラグ指定時の `base_config` 取得 → 分岐削除（`base_config=None` でデフォルト使用）
    - `cli/utils.py:181` — フォールバックでのlogfire有効化 → 分岐ごと削除（CLI or 環境変数でのみ有効化）
    - `cli/commands/ui.py:93` — UI起動時の `base_config` 取得 → 分岐削除（`base_config=None` でデフォルト使用）
  - 置換先は `from_env()` ではなく分岐自体の削除とする。`project_name` / `send_to_logfire` は
    環境変数が設定されている場合のみ `from_env()` 経由で継承し、それ以外はデフォルト値を使用する。
- `from_env()` から `MIXSEEK_LOG_FILE` 読み取り削除（`MIXSEEK_LOG_CONSOLE` は維持）

```python
class LogfireConfig(BaseModel):
    enabled: bool
    privacy_mode: LogfirePrivacyMode
    capture_http: bool
    project_name: str | None
    send_to_logfire: bool
    console_output: bool  # 維持: text モードでの ConsoleOptions スパンツリー表示制御
    # file_output: REMOVED（ファイル出力は LoggingConfig.file_enabled で一元管理）
```

### 1.3 `src/mixseek/config/schema.py` (OrchestratorSettings)

変更なし。初期化順序の制約により `log_format` は追加しない（「設計上の制約」参照）。

### 1.4 `src/mixseek/config/constants.py`

- `DEFAULT_LOG_FORMAT` 削除（フォーマット文字列は `logging_setup.py` の `TEXT_FORMAT` に一元化）
- `DEFAULT_LOG_LEVEL` 削除（デフォルト値は `LoggingConfig.log_level` の Field default に一元化）

ロギング定数の一元管理先:
- **型定義** (`LogFormatType`, `LevelName`): `config/logging.py`
- **デフォルト値** (`"text"`, `"info"`): `LoggingConfig` の Field default
- **フォーマット文字列** (`TEXT_FORMAT`): `observability/logging_setup.py`（TextFormatter の実装詳細）
- **レベルマッピング** (`LOG_LEVEL_MAP`): `observability/logging_setup.py`（setup_logging の実装詳細）

### 1.5 `src/mixseek/models/config.py` -- 完全削除

`ProjectConfig` はプロジェクト全体で**どこからもインスタンス化・インポートされていない dead code**。
`models/__init__.py` でエクスポートされているのみで、プロダクションコード・テストからの参照はゼロ。
spec で設計されたが `ConfigurationManager` 等に置き換わり不要になった経緯。

- `src/mixseek/models/config.py` ファイル削除
- `src/mixseek/models/__init__.py` から `ProjectConfig` エクスポート削除

---

## フェーズ2: Observability層の書き換え

### 2.1 `src/mixseek/observability/logging_setup.py` -- 書き換え

核心となる変更。4モードに対応する `setup_logging()`:

```python
TEXT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

class TextFormatter(logging.Formatter):
    """extra fields を別行 key: value 形式で表示するフォーマッタ"""
    # LogRecord 標準属性セット（ダミー LogRecord から動的導出）
    _STANDARD_FIELDS: ClassVar[frozenset[str]] = frozenset(
        logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
    ) | {"message", "asctime"}  # format() で後付けされるキーも除外

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extra = {k: v for k, v in record.__dict__.items()
                 if k not in self._STANDARD_FIELDS and not k.startswith("_")}
        if not extra:
            return base
        lines = [base]
        for k, v in extra.items():
            lines.append(f"  {k}: {v}")
        return "\n".join(lines)

class JsonFormatter(logging.Formatter):
    """stdlib のみで実装する JSON フォーマッタ。extra fields をトップレベルキーとして出力"""
    # TextFormatter と同一の導出方法
    _STANDARD_FIELDS: ClassVar[frozenset[str]] = frozenset(
        logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
    ) | {"message", "asctime"}

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": ..., "type": "log", "level": ..., "logger": ..., "message": ...
        }
        # extra fields をトップレベルに追加
        extra = {k: v for k, v in record.__dict__.items()
                 if k not in self._STANDARD_FIELDS and not k.startswith("_")}
        log_entry.update(extra)
        return json.dumps(log_entry, ensure_ascii=False, default=str)

class SkipTracesFilter(logging.Filter):
    """LogfireLoggingHandler でのスパン由来レコード再送を防止"""
    def filter(self, record: logging.LogRecord) -> bool:
        return not record.name.startswith("mixseek.traces")

def setup_logging(config: LoggingConfig, workspace: Path | None = None) -> logging.Logger:
    """統一ロガー "mixseek" を初期化。4モードに対応。"""
    logger = logging.getLogger("mixseek")
    for h in logger.handlers:
        h.close()
    logger.handlers.clear()
    logger.propagate = False

    level = LOG_LEVEL_MAP.get(config.log_level, logging.INFO)
    logger.setLevel(level)

    formatter: logging.Formatter
    if config.log_format == "json":
        formatter = JsonFormatter()
    else:
        formatter = TextFormatter(TEXT_FORMAT)

    # --- 全モード共通: StreamHandler/FileHandler を追加 ---
    # Mode 3 (logfire+text) では最終的に ConsoleOptions/TeeWriter に置き換えるが、
    # setup_logfire() 完了前のログ欠損を防ぐため、初期段階では全モードで追加する。
    # setup_logfire() 内の finalize_mode3_handlers() で Mode 3 用のハンドラ除去を行う。

    # コンソール出力
    if config.console_enabled:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # ファイル出力
    if config.file_enabled and workspace:
        log_dir = workspace / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_dir / "mixseek.log", mode="a", encoding="utf-8")
        handler.setLevel(level)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Logfire handler（標準ログをLogfire cloudに転送）
    if config.logfire_enabled:
        try:
            import logfire
            logfire_handler = logfire.LogfireLoggingHandler()
            logfire_handler.setLevel(level)
            # Mode 4 (logfire + json): SkipTracesFilter でスパン由来レコードのループ防止
            if config.log_format == "json":
                logfire_handler.addFilter(SkipTracesFilter())
            logger.addHandler(logfire_handler)
        except ImportError:
            logger.warning("Logfire package not installed, skipping Logfire logging handler")
        except Exception as e:
            logger.warning(f"Failed to add Logfire logging handler: {e}")

    if not logger.handlers:
        logger.addHandler(logging.NullHandler())

    return logger
```

変更ポイント:
- root logger → "mixseek" named logger
- `sys.stderr` 維持（CLIのJSON出力との競合回避）
- **4モード対応**: logfire有無 × text/json の組み合わせでハンドラ構成を切り替え
- **全モードで初期段階は StreamHandler/FileHandler を追加**（setup_logfire() 完了前のログ欠損防止）
- **Mode 3 (logfire+text)**: setup_logfire() 内の `finalize_mode3_handlers()` で StreamHandler/FileHandler を除去（ConsoleOptions/TeeWriter が担当）
- **Mode 4 (logfire+json)**: StreamHandler/FileHandler 有効 + SkipTracesFilter でループ防止
- `TextFormatter`: extra fields を別行 key: value 形式で表示
- `JsonFormatter`: extra fields をトップレベルキー、`type: "log"` で標準ログを識別
- `SkipTracesFilter`: LogfireLoggingHandler での "mixseek.traces" レコード再送防止
- LogfireLoggingHandler 維持（logfire有効時）
- FDリーク防止: handler close before clear

### 2.2 `src/mixseek/observability/logfire.py` -- 書き換え（log_format 対応）

text/json で ConsoleOptions の使用/不使用を切り替える。

```python
from mixseek.config.logging import LogFormatType

class JsonSpanProcessor(SpanProcessor):
    """OpenTelemetry スパンを構造化 JSON ログレコードに変換し、"mixseek.traces" ロガーに書き込む。

    SpanProcessor プロトコルを直接実装する（SimpleSpanProcessor + NoOpExporter の不要な間接層を回避）。
    "mixseek.traces" → 親 "mixseek" に伝搬 → StreamHandler + FileHandler で出力。
    LogfireLoggingHandler には SkipTracesFilter で再送防止済み。
    """
    def __init__(self) -> None:
        self._traces_logger = logging.getLogger("mixseek.traces")

    def on_start(self, span: ReadableSpan, parent_context: Any = None) -> None:
        """スパン開始時に構造化 JSON レコードを出力"""
        record_data = {
            "type": "span_start",
            "span_name": span.name,
            "span_id": format(span.context.span_id, "016x"),
            "parent_span_id": format(span.parent.span_id, "016x") if span.parent else None,
            "attributes": dict(span.attributes) if span.attributes else {},
        }
        self._traces_logger.info(
            f"{span.name} started",
            extra=record_data,
        )

    def on_end(self, span: ReadableSpan) -> None:
        """スパン完了時に構造化 JSON レコードを出力"""
        record_data = {
            "type": "span_end",
            "span_name": span.name,
            "span_id": format(span.context.span_id, "016x"),
            "parent_span_id": format(span.parent.span_id, "016x") if span.parent else None,
            "duration_ms": (span.end_time - span.start_time) / 1_000_000 if span.end_time else None,
            "status": span.status.status_code.name if span.status else None,
            "attributes": dict(span.attributes) if span.attributes else {},
        }
        self._traces_logger.info(
            f"{span.name} completed",
            extra=record_data,
        )

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True

def setup_logfire(
    config: LogfireConfig,
    log_format: LogFormatType = "text",
    workspace: Path | None = None,
    file_enabled: bool = True,
) -> None:
    """Logfire初期化。log_format に応じて出力方式を切り替える。

    - text: ConsoleOptions + TeeWriter(stderr + mixseek.log) でスパンツリー表示
    - json: ConsoleOptions無効 + JsonSpanProcessor で構造化JSON出力
    """
    if not config.enabled:
        return

    import logfire
    from logfire import ConsoleOptions

    if config.project_name:
        os.environ["LOGFIRE_PROJECT"] = config.project_name

    additional_processors: list[SpanProcessor] = []
    console: ConsoleOptions | Literal[False] = False
    file_handle: IO[str] | None = None  # atexit でクローズするためモジュールレベルで保持

    if log_format == "text" and config.console_output:
        # Mode 3: ConsoleOptions + TeeWriter(stderr + mixseek.log)
        writers: list[TextIO] = [sys.stderr]
        if file_enabled and workspace:
            log_dir = workspace / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            file_handle = open(log_dir / "mixseek.log", "a", encoding="utf-8")  # noqa: SIM115
            _logfire_file_handles.append(file_handle)
            writers.append(file_handle)
        console = ConsoleOptions(output=TeeWriter(writers))
    elif log_format == "json":
        # Mode 4: ConsoleOptions無効 + JsonSpanProcessor
        console = False
        additional_processors.append(JsonSpanProcessor())

    logfire.configure(
        send_to_logfire=config.send_to_logfire,
        console=console,
        additional_span_processors=additional_processors or None,
    )

    # Mode 3 (logfire + text): ConsoleOptions 確立後に StreamHandler/FileHandler を除去
    # setup_logging() で一時的に追加していたハンドラを除去し、重複出力を防止する
    if log_format == "text" and config.console_output:
        finalize_mode3_handlers()

    # PydanticAI instrumentation（プライバシーモード対応）- 変更なし
    # HTTPX instrumentation - 変更なし


def finalize_mode3_handlers() -> None:
    """Mode 3 (logfire+text) 用: ConsoleOptions 確立後に StreamHandler/FileHandler を除去する.

    setup_logging() は全モードで StreamHandler/FileHandler を追加する（setup_logfire() 完了前の
    ログ欠損防止のため）。Mode 3 では ConsoleOptions + TeeWriter が全出力を担当するので、
    logfire.configure() 完了後にこれらを除去して重複を防止する。
    """
    logger = logging.getLogger("mixseek")
    handlers_to_remove = [
        h for h in logger.handlers
        if isinstance(h, (logging.StreamHandler, logging.FileHandler))
        and not isinstance(h, type(_get_logfire_handler_type()))
    ]
    for h in handlers_to_remove:
        # FileHandler のみクローズ（StreamHandler(stderr) はクローズしない）
        if isinstance(h, logging.FileHandler):
            h.close()
        logger.removeHandler(h)
```

**注意**: `finalize_mode3_handlers()` は LogfireLoggingHandler を除去してはならない。
LogfireLoggingHandler は `logging.Handler` のサブクラスであり `StreamHandler` ではないため、
`isinstance(h, (logging.StreamHandler, logging.FileHandler))` で正しくフィルタされる。
ただし FileHandler は StreamHandler のサブクラスなので、除去対象の判定は
`logging.StreamHandler` チェックで FileHandler も含まれる。実装時は
`type(h) is logging.StreamHandler or isinstance(h, logging.FileHandler)` のように
正確に判定すること。

変更ポイント:
- `log_format` パラメータ追加: text/json で出力方式を切り替え
- `workspace` パラメータ維持（text モードで TeeWriter が mixseek.log に書き込むため）
- `file_enabled` パラメータ追加（LoggingConfig.file_enabled と連動）
- `_build_console_options()` 関数削除（setup_logfire 内にインライン化）
- `_logfire_file_handles` / `_cleanup_file_handles()` / atexit 維持（text モードのファイルハンドル管理）
- `JsonSpanProcessor` クラス追加（json モード用）
- `TeeWriter` 維持（text モードで stderr + mixseek.log へ同時出力）
- **`finalize_mode3_handlers()` 追加**: Mode 3 でのログ欠損防止のための2段階初期化

### 2.3 `src/mixseek/observability/tee_writer.py` -- 維持

text + logfire モードで ConsoleOptions の出力を stderr + mixseek.log に同時書き込みするために必要。
**削除しない。** 現行実装をそのまま維持。

### 2.4 `src/mixseek/observability/__init__.py` -- 更新

```python
from mixseek.observability.logfire import setup_logfire
from mixseek.observability.logging_setup import setup_logging
from mixseek.observability.tee_writer import TeeWriter
__all__ = ["setup_logfire", "setup_logging", "TeeWriter"]
```

`TeeWriter` エクスポート維持。

---

## フェーズ3: CLI層の修正

### 3.1 `src/mixseek/cli/common_options.py`

`--log-format` オプション追加:

```python
LOG_FORMAT_OPTION = typer.Option(
    None,
    "--log-format",
    click_type=click.Choice(["text", "json"]),
    help="ログ出力形式 (text/json, デフォルト: text)",
)
```

### 3.2 `src/mixseek/cli/utils.py`

**`setup_logging_from_cli()`**: `log_format` パラメータ追加（`logfire_enabled` は維持）

```python
def setup_logging_from_cli(
    log_level: str,
    no_log_console: bool,
    no_log_file: bool,
    logfire_enabled: bool,  # 維持: StreamHandler抑制 + LogfireLoggingHandler制御
    workspace: Path | None,
    verbose: bool,
    log_format: str = "text",  # 追加
) -> None:
    """CLIフラグからロギングを初期化する。

    設定の優先度: CLIフラグ > 環境変数 > デフォルト値
    （環境変数の解決は呼び出し元で行い、log_format引数に渡される）
    """
    try:
        config = LoggingConfig(
            logfire_enabled=logfire_enabled,
            console_enabled=not no_log_console,
            file_enabled=not no_log_file,
            log_level=log_level,
            log_format=log_format,
        )
    except ValidationError as e:
        typer.echo(f"Error: ログ設定が不正です: {e}", err=True)
        raise typer.Exit(code=2)  # 設定エラー = 全失敗
    setup_logging(config, workspace)
```

**`setup_logfire_from_cli()`**: log_format 対応
- `workspace` パラメータ維持（text モードで TeeWriter が mixseek.log に書き込むため）
- `log_format` パラメータ追加
- `file_enabled` パラメータ追加
- `LogfireConfig` 構築時に `file_output` 削除（`console_output` は維持）
- `LogfireConfig.from_toml()` の2箇所の呼び出しを削除:
  - L149 (`elif workspace: base_config = LogfireConfig.from_toml(workspace)`) → 分岐削除
  - L181 (`elif workspace: logfire_config = LogfireConfig.from_toml(workspace)`) → 分岐ごと削除
  - `project_name`/`send_to_logfire` は環境変数がある場合のみ `from_env()` 経由で取得し、
    それ以外はデフォルト値（`project_name=None`, `send_to_logfire=True`）を使用

```python
def setup_logfire_from_cli(
    logfire: bool,
    logfire_metadata: bool,
    logfire_http: bool,
    verbose: bool,
    log_format: str = "text",      # 追加
    workspace: Path | None = None,  # 維持（text モードの TeeWriter 用）
    file_enabled: bool = True,      # 追加
) -> None:
    # ... LogfireConfig構築ロジック（console_output維持）...
    setup_logfire(logfire_config, log_format=log_format, workspace=workspace, file_enabled=file_enabled)
```

### 3.3 `src/mixseek/cli/commands/exec.py`

**方針**: 現在の初期化順序を維持し、dry-runコード（`DRY_RUN_OPTION`,
`_output_preflight_result()`, プリフライトチェック、`close_all_auth_clients()` 等）を
すべて保持したまま、ロギング変更のみ適用する。

**変更点**:

1. **インポート追加**: `LOG_FORMAT_OPTION` を既存の `common_options` importブロックに追加

2. **`exec_command()` シグネチャ** -- `log_format` パラメータ追加:
   ```python
   def exec_command(
       ...
       dry_run: bool = DRY_RUN_OPTION,
       log_format: str | None = LOG_FORMAT_OPTION,  # 追加
       ...
   ) -> None:
   ```

3. **`_execute()` 内** -- ロギング呼び出しのみ変更（初期化順序は維持）:

   ```python
   # 3. 標準logging初期化（CHANGED: log_format追加）
   logfire_enabled = logfire or logfire_metadata or logfire_http  # 維持
   effective_log_format = log_format or os.getenv("MIXSEEK_LOG_FORMAT", "text")
   setup_logging_from_cli(
       log_level, no_log_console, no_log_file,
       logfire_enabled, workspace_path, verbose, effective_log_format,
   )

   # 4. Logfire初期化（CHANGED: log_format + file_enabled 追加）
   setup_logfire_from_cli(
       logfire, logfire_metadata, logfire_http, verbose,
       log_format=effective_log_format,
       workspace=workspace_path,
       file_enabled=not no_log_file,
   )
   ```

4. **他の関数はすべて変更なし**

### 3.4 `src/mixseek/cli/commands/evaluate.py`, `team.py`, `member.py`

各コマンドに共通の変更:

- `LOG_FORMAT_OPTION` インポート追加
- `log_format: str | None = LOG_FORMAT_OPTION` パラメータ追加
- `logfire_enabled` 変数は維持（`setup_logging_from_cli` に引き続き渡す）
- `setup_logging_from_cli()` 呼び出しに `effective_log_format` 追加:
  ```python
  effective_log_format = log_format or os.getenv("MIXSEEK_LOG_FORMAT", "text")
  setup_logging_from_cli(log_level, no_log_console, no_log_file, logfire_enabled, workspace_resolved, verbose, effective_log_format)
  ```
- `setup_logfire_from_cli()` 呼び出しに `log_format` + `workspace` + `file_enabled` 追加:
  ```python
  setup_logfire_from_cli(logfire, logfire_metadata, logfire_http, verbose,
                         log_format=effective_log_format, workspace=workspace_resolved, file_enabled=not no_log_file)
  ```

### 3.5 `src/mixseek/cli/commands/ui.py`

- `LOG_FORMAT_OPTION` インポート追加
- `log_format: str | None = LOG_FORMAT_OPTION` パラメータ追加
- `effective_log_format` 解決ロジック追加
- `os.environ["MIXSEEK_LOG_FORMAT"] = effective_log_format` を既存のenv var書き込みブロックに追加
- `LogfireConfig.from_toml(workspace_resolved)` の分岐（L92-93）を削除
  - `base_config` は環境変数がある場合のみ `from_env()` 経由で取得し、
    それ以外はデフォルト値（`project_name=None`, `send_to_logfire=True`）を使用
- `LogfireConfig` 構築時に `file_output` 削除（`console_output` は維持）

### 3.6 `src/mixseek/ui/app.py` -- 修正

- `log_format=os.getenv("MIXSEEK_LOG_FORMAT", "text")` 追加
- `setup_logfire()` 呼び出しに `log_format` + `workspace` + `file_enabled` を渡す

```python
try:
    log_format = os.getenv("MIXSEEK_LOG_FORMAT", "text")
    file_enabled = os.getenv("MIXSEEK_LOG_FILE", "1") in ("true", "1")
    logging_config = LoggingConfig(
        logfire_enabled=os.getenv("LOGFIRE_ENABLED") == "1",  # 維持
        log_level=os.getenv("MIXSEEK_LOG_LEVEL", "info"),
        console_enabled=os.getenv("MIXSEEK_LOG_CONSOLE", "1") in ("true", "1"),
        file_enabled=file_enabled,
        log_format=log_format,  # 追加
    )
except ValidationError as e:
    st.error(f"ログ設定エラー: {e}")
    st.stop()

# setup_logfire に log_format + workspace + file_enabled を渡す
setup_logfire(logfire_config, log_format=log_format, workspace=workspace, file_enabled=file_enabled)
```

### 3.7 `src/mixseek/ui/services/execution_service.py`

#### 3.7a バックグラウンド実行時の `setup_logfire()` 呼び出し修正

L276 の `setup_logfire(logfire_config)` は新シグネチャに対応していない。
バックグラウンドスレッドでの Logfire 初期化時に `log_format`, `workspace`, `file_enabled` を
渡す必要がある。環境変数から取得して渡す:

```python
if os.getenv("LOGFIRE_ENABLED") == "1":
    try:
        from mixseek.config.logfire import LogfireConfig
        from mixseek.observability import setup_logfire

        logfire_config = LogfireConfig.from_env()
        log_format = os.getenv("MIXSEEK_LOG_FORMAT", "text")
        file_enabled = os.getenv("MIXSEEK_LOG_FILE", "1") in ("true", "1")
        setup_logfire(
            logfire_config,
            log_format=log_format,
            workspace=workspace,
            file_enabled=file_enabled,
        )
    except Exception as e:
        logger.warning(f"Logfire initialization failed in background thread: {e}")
```

#### 3.7b ログ解析のJSON対応

`get_recent_logs()` メソッドがテキスト形式前提（`"- INFO -"` 文字列マッチ）でログを解析している。
`--log-format json` 使用時にファイルに書かれるログがJSON形式になるため、解析が機能しなくなる。

対応: ログ行がJSON形式（`{` で始まる）かテキスト形式かを判定し、JSONの場合は `level` キーで
ログレベルをフィルタするロジックを追加する。

---

## フェーズ4: Agent ロギング層の整理

### 4.1 `src/mixseek/agents/leader/logging.py` -- 削除

**dead code**: プロジェクト全体でどこからもインポートされていない（定義のみ）。
`extra` dict パターンの実装としては正しいが、呼び出し元がないため削除する。
将来 leader agent に構造化ログが必要になった場合は、その時点で再作成する。

### 4.2 `src/mixseek/utils/logging.py` → `src/mixseek/agents/member/logging.py` に移動

`MemberAgentLogger` は `agents/member/base.py` からのみ使用されており、
汎用 util ではなく member agent ドメイン固有のログヘルパーである。
`agents/member/logging.py` に移動し、`utils/logging.py` は完全削除。

リファクタ内容:
  - `__init__(self)`: 引数なし。`self.logger = logging.getLogger("mixseek.member_agents")` のみ
  - `setup_logging()` メソッド削除
  - `log_level` / `enable_file_logging` パラメータ削除
  - **`log_*` メソッドの構造化ログ方式を変更**: `json.dumps()` による手動JSON文字列化を廃止し、
    `extra` dict 方式に統一する。現状の `self.logger.info(f"Execution started: {json_data}")` は
    JsonFormatter 使用時に**JSON内にJSON文字列が埋め込まれる二重エンコード**を引き起こすため、
    削除された `leader/logging.py` が使っていたパターンに揃える:
    ```python
    # Before (現状): メッセージ内にJSON文字列を埋め込み
    json_data = json.dumps(log_data, default=str, ensure_ascii=False)
    self.logger.info(f"Execution started: {json_data}")

    # After: extra dict でフィールドを渡し、フォーマッタに委譲
    self.logger.info(
        "Execution started",
        extra={"execution_id": execution_id, "agent_name": agent_name, ...},
    )
    ```
  - `json` インポート削除（不要になる。`uuid` は `execution_id` 生成に引き続き使用）
  - `_sanitize_parameters()` は維持（extra dict 内の値サニタイズに引き続き使用）

### 4.3 `src/mixseek/agents/member/base.py`

- import先を変更: `from mixseek.utils.logging import MemberAgentLogger` → `from mixseek.agents.member.logging import MemberAgentLogger`
- `MemberAgentLogger()` を引数なしで呼び出しに変更

### 4.4 `src/mixseek/utils/__init__.py`

- `setup_logging` エクスポート削除

### 4.5 `src/mixseek/utils/logging.py` -- 完全削除

`setup_logging()` 関数は `observability/logging_setup.py` に一元化済み。
`MemberAgentLogger` は `agents/member/logging.py` に移動済み。ファイル自体を削除。

### 4.6 `src/mixseek/config/manager.py`

`logging.warning()` の直呼びが3箇所（lines 543, 655, 807）で使用されている。
root logger → named logger 移行により、これらは `"mixseek"` ロガーのハンドラに到達しなくなる。
モジュール先頭に `logger = logging.getLogger(__name__)` を追加し、
`logging.warning(...)` → `logger.warning(...)` に置換する。

### 4.6b `src/mixseek/evaluator/evaluator.py`

`logging.warning()` の直呼びが1箇所（line 395、カスタムメトリクスロードエラー時）で使用されている。
4.6 と同様の理由で `"mixseek"` ロガーのハンドラに到達しなくなる。
モジュール先頭に `logger = logging.getLogger(__name__)` を追加し、
`logging.warning(...)` → `logger.warning(...)` に置換する。

### 4.7 `examples/custom_agents/adk_research/agent.py` -- ロガー名維持 + コメント追加

`logger = logging.getLogger(__name__)` のまま維持する。
examples はユーザがカスタムエージェントを作成する際の参考コードであり、
`__name__` を使うのが自然な書き方。`"mixseek.*"` 名前空間を強制しない。

ただし、統一ロガーへの伝搬についてコメントで案内する:
```python
# NOTE: このロガーは "mixseek" 統一ロガーの名前空間外のため、
# mixseek のハンドラ（stderr/mixseek.log）には伝搬しません。
# 統一ロガーへの伝搬が必要な場合は以下を使用してください:
#   logger = logging.getLogger("mixseek.custom_agents.adk_research")
logger = logging.getLogger(__name__)
```

### 4.8 `examples/custom_agents/adk_research/runner.py` -- 同上

`runner.py` にも同様のコメントを追加する。ロガー名は `__name__` のまま維持。

---

## フェーズ5: テスト

### TDD: 先にテストを書く

#### 新規: `tests/observability/test_logging_setup.py`（書き換え）

- "mixseek" ロガーに対してテスト（root logger ではない）
- `propagate=False` を検証
- FDリーク防止（close before clear）のテスト
- NullHandler（サイレントモード）のテスト

**4モード対応テスト:**

- **Mode 1 (logfire無効 + text)**:
  - StreamHandler(stderr) + FileHandler(mixseek.log) が存在
  - TextFormatter が使用されている
  - extra fields が別行 key: value 形式で出力される
- **Mode 2 (logfire無効 + json)**:
  - StreamHandler(stderr) + FileHandler(mixseek.log) が存在
  - JsonFormatter が使用されている
  - extra fields が JSON トップレベルキーとして出力される
  - `"type": "log"` フィールドが含まれる
- **Mode 3 (logfire有効 + text)**:
  - setup_logging() 直後: StreamHandler + FileHandler + LogfireLoggingHandler が全て存在する
  - finalize_mode3_handlers() 呼び出し後: StreamHandler/FileHandler が除去されている
  - LogfireLoggingHandler のみ残っている
  - 2段階初期化のテスト: setup_logging() 後にログ出力し、finalize_mode3_handlers() 後に
    StreamHandler/FileHandler が除去されていることを検証
- **Mode 4 (logfire有効 + json)**:
  - StreamHandler(stderr) + FileHandler(mixseek.log) が存在
  - JsonFormatter が使用されている
  - LogfireLoggingHandler に SkipTracesFilter が設定されている

**TextFormatter テスト:**
- extra fields なし: メッセージ行のみ出力
- extra fields あり: 別行 key: value 形式で出力
- 複数 extra fields: 全フィールドが個別行で出力

**JsonFormatter テスト:**
- 基本フィールド（timestamp, type, level, logger, message）が含まれる
- extra fields がトップレベルキーとして出力される
- `type: "log"` が設定される

**SkipTracesFilter テスト:**
- "mixseek.traces" ロガーのレコードがフィルタされる
- "mixseek.agents" ロガーのレコードはフィルタされない

#### 修正: `tests/config/test_logging.py`

- `from_toml` テスト削除
- `log_format` フィールドテスト追加
- `MIXSEEK_LOG_FORMAT` 環境変数テスト追加
- `logfire_enabled` テストは維持

#### 修正: `tests/config/test_logfire_config.py`

- `file_output` テスト削除
- `console_output` テスト維持
- `from_toml` テスト削除

#### 修正: `tests/integration/test_logfire_integration.py`

**text モード テスト:**
- `ConsoleOptions(output=TeeWriter(...))` の検証（TeeWriter で stderr + file に同時出力）
- workspace パラメータ維持（TeeWriter がファイルハンドルを必要とする）
- `send_to_logfire` 検証は維持
- **`finalize_mode3_handlers()` テスト**:
  - 呼び出し前: StreamHandler + FileHandler + LogfireLoggingHandler が存在
  - 呼び出し後: StreamHandler/FileHandler が除去、LogfireLoggingHandler のみ残存
  - FileHandler が close されていること（FDリーク防止）

**json モード テスト:**
- `ConsoleOptions` が `False` に設定されることを検証
- `additional_span_processors` に `JsonSpanProcessor` が含まれることを検証
- JsonSpanProcessor が "mixseek.traces" ロガーに構造化JSONを出力することを検証
- JsonSpanProcessor.on_start が `type: "span_start"` で開始イベントを出力することを検証
- JsonSpanProcessor.on_end が `type: "span_end"` + `duration_ms` + `status` で完了イベントを出力することを検証

#### 追加: `tests/agents/member/test_logging.py`

MemberAgentLogger の `log_*` メソッドが `extra` dict 方式で構造化データを渡すことを検証:
- `log_execution_start()`: `extra` に `execution_id`, `agent_name` 等が含まれる
- `log_execution_complete()`: ステータスに応じたログレベル（info/error/warning）
- `log_tool_invocation()`: `_sanitize_parameters()` がセンシティブキーを REDACT
- JSON二重エンコードが発生しないこと（メッセージ内に `{` を含まない）

#### 維持: `tests/observability/test_tee_writer.py`

TeeWriter は text + logfire モードで引き続き使用するため、既存テストを維持。

#### dry-runテストの互換性

`tests/unit/cli/test_exec_dry_run.py` と `tests/unit/cli/test_exec_exit_code.py` は
`setup_logging_from_cli` と `setup_logfire_from_cli` をモジュールレベルでモックしている。
`unittest.mock.patch` はデフォルトでシグネチャを検証しないため、パラメータ変更
（`log_format` 追加、`file_enabled` 追加）によるテスト破壊は発生しない。コード変更不要。

#### 修正: `tests/cli/commands/test_exec_logfire.py`

`from_toml()` 廃止に伴い、`TestLogfireConfigPriority` 等の TOML 優先順位前提テストケースを
修正する。`logfire.toml` 作成テストは削除し、設定の優先度テストは
「CLIフラグ > 環境変数 > デフォルト値」に更新する。
`assert True` プレースホルダーは実質的なアサーションに置き換える。

#### 追加: `tests/ui/test_execution_service.py` -- JSONログ解析テスト

`get_recent_logs()` がJSONフォーマットのログ行を正しく解析・フィルタできることを検証。
テキスト形式とJSON形式が混在するケースも含める。

---

## フェーズ6: ドキュメント・サンプル更新

### `docs/observability.md` -- 更新

- `logging.toml` / `logfire.toml` の `from_toml()` 廃止を反映
- 新しい設定優先度（CLIフラグ > 環境変数 > デフォルト値）を明記
- `--log-format` オプションのドキュメント追加
- `logfire.log` / `member-agent-*.log` 廃止と `mixseek.log` への統一を記述
- Logfire有効/無効時のコンソール出力の違いを明記
- カスタムエージェントのロガー名ガイド追加:
  `logging.getLogger("mixseek.custom_agents.<name>")` を使用することで統一ロガーのハンドラに伝搬する旨を記述

---

## PydanticAI Logfire統合への影響

| 項目 | 変更 | リスク |
|------|------|--------|
| `logfire.instrument_pydantic_ai()` | 変更なし | なし |
| `logfire.span()` (orchestrator/round_controller) | 変更なし | なし |
| `logfire.configure(console=...)` | text: `ConsoleOptions(TeeWriter(stderr, file))` / json: `False` | なし: text はツリー表示維持、json は構造化JSONで代替 |
| `logfire.configure(additional_span_processors=...)` | json: `JsonSpanProcessor` 追加 | 低: カスタムプロセッサ追加のみ |
| `LogfireLoggingHandler` | 維持（json 時に SkipTracesFilter 追加） | なし: 標準ログのLogfire cloud転送は現行通り |
| `logfire.log` ファイル | 廃止（mixseek.log に統合） | 低: スパンは mixseek.log に記録されるため情報損失なし |

**`send_to_logfire=false` 時の観測性について**:
- `send_to_logfire=false` の場合、Logfire cloudにスパンは送信されない
- text モード: `ConsoleOptions(TeeWriter)` により、スパンツリーが stderr + mixseek.log に表示される
- json モード: `JsonSpanProcessor` により、スパンが構造化JSONで stderr + mixseek.log に記録される
- いずれのモードでも、logfire.log 廃止による情報損失はない

---

## 破壊的変更一覧

| 変更 | 影響 |
|------|------|
| root logger → "mixseek" named logger | mixseek外のロガーがハンドラを継承しなくなる |
| logfire.log 廃止 | logfire.log を読んでいたワークフローに影響（mixseek.log に統合） |
| member-agent-*.log 廃止 | member-agent ログを個別に読んでいたワークフローに影響 |
| MemberAgentLogger API変更 | `log_level`/`enable_file_logging` パラメータ削除（引数なし）。`log_*` メソッドの出力方式が `json.dumps` 文字列埋め込みから `extra` dict に変更 |
| MemberAgentLogger 移動 | `utils/logging.py` → `agents/member/logging.py`（import先変更） |
| leader/logging.py 削除 | dead code（呼び出し元なし） |
| ProjectConfig / models/config.py 削除 | dead code（参照元なし）。`constants.py` の `DEFAULT_LOG_FORMAT` / `DEFAULT_LOG_LEVEL` も同時削除 |
| DEFAULT_LOG_FORMAT / DEFAULT_LOG_LEVEL 削除 | `constants.py` からの参照元がなくなる |
| LogfireConfig.file_output 削除 | 直接このフィールドを使用するコード |
| LoggingConfig.log_file_path 削除 | dead field（どこからも使用されていない） |
| from_toml() 削除 | `LoggingConfig.from_toml()` は呼び出し元なし。`LogfireConfig.from_toml()` は3箇所（`cli/utils.py` x2, `cli/commands/ui.py` x1）から呼ばれているが、TOMLファイル運用の実態がないため廃止。環境変数に一元化 |
| setup_logfire() シグネチャ変更 | `log_format`, `file_enabled` パラメータ追加 |
| setup_logfire_from_cli() シグネチャ変更 | `log_format`, `file_enabled` パラメータ追加 |
| evaluator.py logging.warning() 修正 | root logger 直呼び → named logger に変更（ハンドラ到達性の修正） |
| logfire+text 時の FileHandler 抑制 | setup_logfire() 内の finalize_mode3_handlers() で除去（2段階初期化によりログ欠損なし） |

---

## 品質チェック

```bash
make -C dockerfiles/ci quality-gate-fast
```

各フェーズの実装後に実行し、ruff lint + format + mypy + tests をパスさせる。

---

## 実装順序

1. **Phase 5 (テスト先行)**: Article 3 準拠で先にテストを書く
   - `tests/observability/test_logging_setup.py` 書き換え（4モード対応、TextFormatter、JsonFormatter、SkipTracesFilter）
   - `tests/config/test_logging.py` 修正
   - `tests/config/test_logfire_config.py` 修正
   - Red phase 確認（テスト失敗を確認）
2. **Phase 1 (Config層)**: LoggingConfig（log_file_path削除, log_format追加）, LogfireConfig（file_output削除, from_toml削除）, constants（DEFAULT_LOG_FORMAT/DEFAULT_LOG_LEVEL削除）, models/config.py削除
3. **Phase 2 (Observability層)**: logging_setup.py 書き換え（全モードでStreamHandler/FileHandler追加）、logfire.py 書き換え（finalize_mode3_handlers追加）（tee_writer.py は維持）
4. **Phase 4 (Utils/Agent層)**: MemberAgentLogger移動, utils/__init__.py, base.py, config/manager.py（logging.warning修正）, evaluator/evaluator.py（logging.warning修正）, examples/コメント追加
5. **Phase 3 (CLI層)**: common_options, utils（from_toml分岐削除）, exec, evaluate, team, member, ui（from_toml分岐削除）, app.py, execution_service.py
6. **Phase 5 続き**: 残りのテスト修正
   - `tests/integration/test_logfire_integration.py` 修正（text/json 両モード）
   - `tests/observability/test_tee_writer.py` 維持（変更不要）
   - `tests/cli/commands/test_exec_logfire.py` 修正
   - `tests/ui/test_execution_service.py` 追加
7. **Phase 6 (ドキュメント)**: docs/observability.md 更新
8. **品質チェック**: `make -C dockerfiles/ci quality-gate-fast`
