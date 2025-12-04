# Contract: Input Format

**Date**: 2025-10-22
**Feature**: 036-model-validation
**Purpose**: TOML/JSON/CSV入力ファイルの構造仕様

## Functional Requirements
- FR-001: TOML形式のモデルリストを必須入力として受け取る
- FR-004: TOML・JSON・CSVを選択可能

## 入力ファイルの生成

入力ファイルは`llm-discovery`コマンドで生成します：

```bash
# TOML形式で生成
uvx llm-discovery export --format toml --output models.toml

# JSON形式で生成
uvx llm-discovery export --format json --output models.json

# CSV形式で生成
uvx llm-discovery export --format csv --output models.csv
```

**重要**: 最新のモデル情報を取得するため、検証の直前に実行することを推奨します。

---

## 1. TOML Input Format

### Structure
```toml
[metadata]
source = "llm-discovery"
version = "1.0.0"
generated_at = "2025-10-22T10:00:00Z"
total_models = 143

[[models]]
provider = "google"
model_id = "gemini-2.5-flash"
name = "Gemini 2.5 Flash"
modality = "chat"
version = "stable"

[[models]]
provider = "openai"
model_id = "gpt-4o"
name = "GPT-4o"
modality = "chat"
version = "stable"

[[models]]
provider = "anthropic"
model_id = "claude-sonnet-4-5-20250929"
name = "Claude Sonnet 4.5"
modality = "chat"
version = "stable"
```

### Required Fields per Model
| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `provider` | string | プロバイダー名 | `google` \| `openai` \| `anthropic` |
| `model_id` | string | モデル識別子 | 空文字列禁止 |
| `name` | string | モデル表示名 | 空文字列禁止 |
| `modality` | string | モダリティ | `chat` \| `text-to-speech` \| `image-generation` \| `embedding` \| `moderation` |
| `version` | string | バージョン分類 | `stable` \| `preview` \| `experimental` |

### Optional Fields (Metadata)
| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `source` | string | データソース | `"unknown"` |
| `generated_at` | string (ISO 8601) | 生成日時 | 現在時刻 |
| `total_models` | int | 総モデル数 | 配列長 |

### Validation Rules (FR-001, FR-003)
1. **必須フィールドの存在**: `provider`, `model_id`, `name`, `modality`, `version`が全て存在
2. **provider検証**: `google`, `openai`, `anthropic`のいずれか（大文字小文字不問）
3. **空文字列禁止**: `model_id`, `name`が空文字列またはホワイトスペースのみでない
4. **version検証**: `stable`, `preview`, `experimental`のいずれか

### Error Examples

#### Missing Required Field
```toml
[[models]]
provider = "google"
# model_id field missing
name = "Gemini 2.5 Flash"
modality = "chat"
version = "stable"
```
**Error**:
```
ValidationError: Field 'model_id' is required for models[0]
```

#### Invalid Provider
```toml
[[models]]
provider = "azure"  # Not supported
model_id = "gpt-4"
name = "GPT-4"
modality = "chat"
version = "stable"
```
**Error**:
```
ValidationError: provider must be one of {'google', 'openai', 'anthropic'}, got: 'azure'
```

---

## 2. JSON Input Format

### Structure
```json
{
  "metadata": {
    "source": "llm-discovery",
    "version": "1.0.0",
    "generated_at": "2025-10-22T10:00:00Z",
    "total_models": 143
  },
  "models": [
    {
      "provider": "google",
      "model_id": "gemini-2.5-flash",
      "name": "Gemini 2.5 Flash",
      "modality": "chat",
      "version": "stable"
    },
    {
      "provider": "openai",
      "model_id": "gpt-4o",
      "name": "GPT-4o",
      "modality": "chat",
      "version": "stable"
    }
  ]
}
```

### Required Top-Level Keys
- `models`: Array of model objects

### Optional Top-Level Keys
- `metadata`: Object with metadata fields

### Validation Rules
- Same as TOML format
- JSON syntax must be valid
- UTF-8 encoding

---

## 3. CSV Input Format

### Structure
```csv
provider,model_id,name,modality,version
google,gemini-2.5-flash,Gemini 2.5 Flash,chat,stable
openai,gpt-4o,GPT-4o,chat,stable
anthropic,claude-sonnet-4-5-20250929,Claude Sonnet 4.5,chat,stable
```

### Required Headers (First Row)
```csv
provider,model_id,name,modality,version
```

### Validation Rules
- Header row must exactly match required field names
- No empty cells in required columns
- UTF-8 encoding with BOM support
- Comma delimiter (`,`)
- Optional quoting for fields containing commas or newlines

### Error Examples

#### Missing Header
```csv
google,gemini-2.5-flash,Gemini 2.5 Flash,chat,stable
```
**Error**:
```
ValidationError: CSV file must have a header row with columns: provider, model_id, name, modality, version
```

#### Empty Cell
```csv
provider,model_id,name,modality,version
google,,Gemini 2.5 Flash,chat,stable
```
**Error**:
```
ValidationError: model_id must not be empty (row 2)
```

---

## 4. Auto-Detection Logic

### Detection Order
1. **File Extension**: `.toml` → TOML, `.json` → JSON, `.csv` → CSV
2. **CLI Option**: `--format` overrides extension
3. **Content Sniffing** (fallback):
   - First non-whitespace char `{` → JSON
   - First non-whitespace char `[` or contains `[[` → TOML
   - Contains comma in first line → CSV

### Examples
```bash
# Extension-based
mixseek validate-models -i models.toml  # → TOML
mixseek validate-models -i models.json  # → JSON
mixseek validate-models -i models.csv   # → CSV

# Override with --format
mixseek validate-models -i data.txt --format json  # → JSON
```

---

## 5. Pydantic Model Mapping

### TOML/JSON → Pydantic
```python
from pydantic import BaseModel, Field, field_validator

class ModelListInput(BaseModel):
    models: list[ModelInfo]
    metadata: dict[str, str] = Field(default_factory=dict)

class ModelInfo(BaseModel):
    provider: str
    model_id: str
    name: str
    modality: str
    version: Literal["stable", "preview", "experimental"]

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        allowed = {"google", "openai", "anthropic"}
        if v.lower() not in allowed:
            raise ValueError(f"Provider must be one of {allowed}")
        return v.lower()
```

### CSV → Pydantic
```python
import csv
from pathlib import Path

def load_csv(csv_path: Path) -> ModelListInput:
    models = []
    with csv_path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != ["provider", "model_id", "name", "modality", "version"]:
            raise ValueError("CSV header mismatch")

        for row in reader:
            models.append(ModelInfo.model_validate(row))

    return ModelListInput(models=models)
```

---

## 6. Sample Input Files

### Sample TOML (143 models)
```toml
[metadata]
source = "llm-discovery"
total_models = 143

# Google Models (43 models)
[[models]]
provider = "google"
model_id = "gemini-2.5-flash"
name = "Gemini 2.5 Flash"
modality = "chat"
version = "stable"

[[models]]
provider = "google"
model_id = "gemini-2.5-pro"
name = "Gemini 2.5 Pro"
modality = "chat"
version = "stable"

# ... (remaining 41 Google models)

# OpenAI Models (97 models)
[[models]]
provider = "openai"
model_id = "gpt-4o"
name = "GPT-4o"
modality = "chat"
version = "stable"

# ... (remaining 96 OpenAI models)

# Anthropic Models (3 models)
[[models]]
provider = "anthropic"
model_id = "claude-sonnet-4-5-20250929"
name = "Claude Sonnet 4.5"
modality = "chat"
version = "stable"

# ... (remaining 2 Anthropic models)
```

---

## 7. Contract Tests

### Test Cases
1. **T-IN-001**: Valid TOML input → Successful parsing
2. **T-IN-002**: Valid JSON input → Successful parsing
3. **T-IN-003**: Valid CSV input → Successful parsing
4. **T-IN-004**: TOML with missing `model_id` → ValidationError
5. **T-IN-005**: JSON with invalid `provider` → ValidationError
6. **T-IN-006**: CSV without header → ValidationError
7. **T-IN-007**: Auto-detection from `.toml` extension → TOML parser
8. **T-IN-008**: Override with `--format json` → JSON parser

**Implementation**: `tests/contract/test_input_format.py`
