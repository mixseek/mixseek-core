# Contract: CLI Interface

**Date**: 2025-10-22
**Feature**: 036-model-validation
**Purpose**: `mixseek validate-models`コマンドの引数・オプション仕様

## Command Specification

### Command Name
```bash
mixseek validate-models
```

### Functional Requirements
- FR-014: CLI経由で実行できる単一の検証コマンドを提供
- FR-004: 入力形式（TOML/JSON/CSV）を指定可能
- FR-009: コスト上限などのパラメータを指定可能

---

## Required Arguments

### `--input` / `-i`
- **Type**: `Path`
- **Required**: Yes
- **Description**: 入力ファイルパス（TOML/JSON/CSV）。llm-discoveryコマンドで生成したモデルリストを指定します。
- **Validation**:
  - ファイルが存在すること
  - 読み取り権限があること
  - 拡張子が`.toml`、`.json`、`.csv`のいずれかであること
- **生成方法**:
  ```bash
  uvx llm-discovery export --format toml --output models.toml
  ```
- **Example**:
  ```bash
  mixseek validate-models --input models.toml
  ```

---

## Optional Arguments

### `--output` / `-o`
- **Type**: `Path`
- **Required**: No
- **Default**: `./validation-output`
- **Description**: 出力ディレクトリパス
- **Validation**:
  - 親ディレクトリが存在すること
  - 書き込み権限があること
- **Example**:
  ```bash
  mixseek validate-models -i models.toml -o results/
  ```

### `--format` / `-f`
- **Type**: `Literal["toml", "json", "csv"]`
- **Required**: No
- **Default**: Auto-detect from file extension
- **Description**: 入力ファイル形式の明示的指定
- **Example**:
  ```bash
  mixseek validate-models -i data.txt --format json
  ```

### `--cost-limit`
- **Type**: `Decimal`
- **Required**: No
- **Default**: `1.00`（環境変数`MIXSEEK_COST_LIMIT_USD`で上書き可能）
- **Description**: 累計APIコスト上限（USD）
- **Validation**:
  - 正の数値であること
  - 小数点以下2桁まで
- **Example**:
  ```bash
  mixseek validate-models -i models.toml --cost-limit 5.00
  ```

### `--max-retries`
- **Type**: `int`
- **Required**: No
- **Default**: `3`（環境変数`MIXSEEK_MAX_RETRIES`で上書き可能）
- **Description**: 最大リトライ回数
- **Validation**:
  - 0以上の整数
  - 推奨範囲: 1〜5
- **Example**:
  ```bash
  mixseek validate-models -i models.toml --max-retries 5
  ```

### `--skip-api-validation`
- **Type**: `bool` (flag)
- **Required**: No
- **Default**: `False`
- **Description**: API動作検証をスキップ（互換性判定のみ実行）
- **Use Case**: コストを発生させずに互換性判定のみ行いたい場合
- **Example**:
  ```bash
  mixseek validate-models -i models.toml --skip-api-validation
  ```

### `--parallel` / `-p`
- **Type**: `int`
- **Required**: No
- **Default**: `5`（環境変数`MIXSEEK_MAX_CONCURRENT_VALIDATIONS`で上書き可能）
- **Description**: 最大並列検証数
- **Validation**:
  - 1以上の整数
  - 推奨範囲: 1〜10
- **Example**:
  ```bash
  mixseek validate-models -i models.toml --parallel 10
  ```

### `--timeout`
- **Type**: `int`
- **Required**: No
- **Default**: `120`（環境変数`MIXSEEK_VALIDATION_TIMEOUT`で上書き可能）
- **Description**: 検証タイムアウト（秒）
- **Validation**:
  - 正の整数
  - 推奨範囲: 30〜600
- **Example**:
  ```bash
  mixseek validate-models -i models.toml --timeout 300
  ```

### `--verbose` / `-v`
- **Type**: `bool` (flag, count)
- **Required**: No
- **Default**: `False`
- **Description**: 詳細ログ出力（複数回指定で冗長度増加）
- **Levels**:
  - デフォルト: INFO
  - `-v`: DEBUG
  - `-vv`: TRACE（全API呼び出し詳細）
- **Example**:
  ```bash
  mixseek validate-models -i models.toml -vv
  ```

---

## Output Specification

### Exit Codes
- **0**: 検証成功（全モデル検証完了）
- **1**: 検証失敗（エラー発生、コスト上限超過等）
- **2**: 入力エラー（ファイル不存在、構文エラー等）

### Standard Output (stdout)
```
[INFO] Loading models from: models.toml
[INFO] Found 145 models
[INFO] Extracting conversational models...
[INFO] Extracted 65 conversational models
[INFO] Starting compatibility check...
[INFO] Compatibility check completed: 62/65 compatible
[INFO] Starting API validation... (estimated cost: $0.45)
[INFO] API validation progress: 10/62 completed
[INFO] API validation progress: 20/62 completed
...
[INFO] API validation completed: 59/62 successful
[INFO] Total cost: $0.42
[INFO] Generating reports...
[INFO] ✓ TOML matrix: results/compatibility-matrix.toml
[INFO] ✓ Markdown report: results/validation-report.md
[SUCCESS] Validation completed successfully
```

### Standard Error (stderr)
```
[WARNING] Model google/gemini-ultra not available in API
[ERROR] Authentication failed for provider: openai
[ERROR] Rate limit exceeded, retrying in 2.0s... (attempt 1/3)
```

### Output Files
1. **`{output_dir}/compatibility-matrix.toml`**
   - TOML互換性マトリクス
   - 詳細: `output-format.md`参照

2. **`{output_dir}/validation-report.md`**
   - Markdownレポート
   - 詳細: `output-format.md`参照

3. **`{output_dir}/validation-log.json`** (optional, with `--verbose`)
   - JSON形式の詳細ログ
   - タイムスタンプ、リクエスト/レスポンス、メトリクス等

---

## Usage Examples

### Basic Usage
```bash
mixseek validate-models --input models.toml
```

### With Custom Cost Limit
```bash
mixseek validate-models -i models.toml --cost-limit 10.00 -o custom-results/
```

### Compatibility Check Only (No API Calls)
```bash
mixseek validate-models -i models.toml --skip-api-validation
```

### High Parallelism with Verbose Logging
```bash
mixseek validate-models -i models.json --parallel 10 --timeout 300 -vv
```

### Environment Variable Override
```bash
export MIXSEEK_COST_LIMIT_USD=5.00
export MIXSEEK_MAX_RETRIES=5
mixseek validate-models -i models.toml
```

---

## Error Handling

### Input File Errors
```
Error: Input file not found: models.toml
Suggestion: Check the file path and ensure the file exists
Exit code: 2
```

### Cost Limit Exceeded
```
Error: Cost limit $1.00 exceeded: $1.05
Info: Validation stopped at 45/65 models
Info: Partial results saved to: results/
Exit code: 1
```

### Authentication Failure
```
Error: Authentication failed for provider: google
Info: Please set environment variable: GOOGLE_API_KEY
Info: Continuing with remaining providers...
Exit code: 1 (if all providers fail), 0 (if at least one succeeds)
```

---

## Type Contract (Typer Implementation)

```python
import typer
from pathlib import Path
from decimal import Decimal
from typing import Literal

app = typer.Typer()

@app.command()
def validate_models(
    input: Path = typer.Option(
        ...,
        "--input",
        "-i",
        help="Input file path (TOML/JSON/CSV)",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    output: Path = typer.Option(
        Path("./validation-output"),
        "--output",
        "-o",
        help="Output directory path",
    ),
    format: Literal["toml", "json", "csv"] | None = typer.Option(
        None,
        "--format",
        "-f",
        help="Input file format (auto-detect if not specified)",
    ),
    cost_limit: Decimal = typer.Option(
        Decimal("1.00"),
        "--cost-limit",
        help="Cumulative API cost limit (USD)",
    ),
    max_retries: int = typer.Option(
        3,
        "--max-retries",
        help="Maximum retry count",
        min=0,
        max=10,
    ),
    skip_api_validation: bool = typer.Option(
        False,
        "--skip-api-validation",
        help="Skip API validation (compatibility check only)",
    ),
    parallel: int = typer.Option(
        5,
        "--parallel",
        "-p",
        help="Maximum concurrent validations",
        min=1,
        max=20,
    ),
    timeout: int = typer.Option(
        120,
        "--timeout",
        help="Validation timeout (seconds)",
        min=10,
        max=3600,
    ),
    verbose: int = typer.Option(
        0,
        "--verbose",
        "-v",
        count=True,
        help="Verbose logging (-v: DEBUG, -vv: TRACE)",
    ),
) -> None:
    """Validate LLM model compatibility with mixseek agents."""
    # Implementation...
```

---

## Contract Tests

### Test Cases
1. **T-CLI-001**: 必須引数なしで実行 → エラーメッセージ表示
2. **T-CLI-002**: 存在しないファイルを指定 → エラーメッセージ表示
3. **T-CLI-003**: 正常な入力ファイル → 検証実行、出力ファイル生成
4. **T-CLI-004**: `--cost-limit 0.01`で実行 → コスト上限超過エラー
5. **T-CLI-005**: `--skip-api-validation`で実行 → API呼び出しなし、互換性判定のみ
6. **T-CLI-006**: `-vv`で実行 → DEBUG/TRACEログ出力
7. **T-CLI-007**: 環境変数でコスト上限設定 → CLI引数より優先度低い

**Implementation**: `tests/contract/test_cli_interface.py`
