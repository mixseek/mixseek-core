# Implementation Tasks: LLMモデル互換性検証

**Branch**: `036-model-validation` | **Date**: 2025-10-22
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

---

## Implementation Strategy

### MVP Scope
**User Story 1（P1）のみ実装**: 会話モデルの対象抽出

最小限の機能で動作を確認し、段階的に機能を追加していきます。

### Delivery Order
1. **Phase 1-2**: Setup & Foundational（基盤構築）
2. **Phase 3**: User Story 1（P1）- 会話モデル抽出
3. **Phase 4**: User Story 2（P1）- 互換性判定
4. **Phase 5**: User Story 4（P1）- レポート生成
5. **Phase 6**: User Story 3（P2）- API検証
6. **Phase 7**: Polish（品質向上）

### Constitution Compliance
- **Article 3**: Test-First Imperative（全実装前にテスト作成・承認・Redフェーズ確認）
- **Article 9**: Data Accuracy（ハードコード禁止、明示的エラー）
- **Article 10**: DRY Principle（既存実装の再利用）
- **Article 16**: Type Safety（mypy strict mode、全型注釈）

---

## Phase 1: Setup Tasks

### T001 [Setup] プロジェクト構造の作成
**File**: N/A
**Description**: 必要なディレクトリ構造を作成

```bash
mkdir -p src/mixseek/validation
touch src/mixseek/validation/__init__.py
mkdir -p tests/unit/validation
mkdir -p tests/integration/validation
mkdir -p tests/contract
mkdir -p tests/fixtures/validation
```

**Acceptance**:
- [X] `src/mixseek/validation/`ディレクトリ存在
- [X] `tests/`配下のディレクトリ存在

---

### T002 [Setup] 依存関係の確認
**File**: `pyproject.toml`
**Description**: 必要な依存関係が全てインストール済みか確認

**Dependencies**:
- pydantic >= 2.0.0
- pydantic-ai >= 0.0.8
- pydantic-settings >= 2.0.0
- typer >= 0.9.0

**Command**:
```bash
uv sync
```

**Acceptance**:
- [X] `uv sync`が成功
- [X] `uv run python -c "import pydantic; import pydantic_ai; import typer"`が成功

---

## Phase 2: Foundational Tasks

### T003 [Foundation] 基本データモデルの作成
**File**: `src/mixseek/validation/models.py`
**Description**: 全User Storiesで共通利用するPydantic BaseModelを定義

**Models**:
1. `ModelInfo`: モデルカタログ項目（US1で使用）
2. `CompatibilityResult`: 互換性判定結果（US2で使用）
3. `ValidationMetrics`: API検証メトリクス（US3で使用）
4. `RecommendationReport`: 推奨レポート（US4で使用）
5. `ValidationConfig`: 検証設定（BaseSettings）
6. `ModelListInput`: 入力データ統一表現

**Reference**: `data-model.md`

**Key Requirements**:
- Article 16: 全フィールドに型注釈
- Article 9: `ConfigDict(extra="forbid", validate_assignment=True)`
- `@field_validator`で個別フィールド検証
- `@model_validator(mode="after")`でクロスフィールド検証

**Acceptance**:
- [X] 6つのモデルクラスが定義済み
- [X] `mypy src/mixseek/validation/models.py`がゼロエラー
- [X] 全モデルに`model_config = ConfigDict(...)`設定

---

### T004 [Foundation] 基本データモデルのテスト作成（Article 3: Test-First）
**File**: `tests/unit/validation/test_models.py`
**Description**: models.pyの実装前にテストを作成し、ユーザー承認を得る

**Test Cases**:
1. `test_model_info_validation`: provider/model_id/nameの検証
2. `test_model_info_empty_string_rejection`: 空文字列の拒否
3. `test_compatibility_result_creation`: CompatibilityResult作成
4. `test_validation_metrics_retry_count`: retry_count <= max_retries検証
5. `test_validation_config_from_env`: 環境変数からの読み込み
6. `test_model_list_input_filter_conversational`: 会話モデルフィルタリング

**Reference**: `tests/unit/test_member_agent_config.py`（既存パターン）

**Acceptance**:
- [X] テストファイル作成完了
- [X] ユーザーがテスト内容を承認
- [X] `pytest tests/unit/validation/test_models.py`が**失敗**（Red Phase確認: 12 failed）

**⚠️ BLOCKER**: このタスク完了とユーザー承認なしでT003実装に進んではならない

---

### T005 [Foundation] 例外クラスの定義
**File**: `src/mixseek/validation/exceptions.py`
**Description**: Article 9準拠の明示的エラークラスを定義

**Exceptions**:
```python
class ValidationError(Exception): ...
class CostLimitExceededError(ValidationError): ...
class AuthenticationError(ValidationError): ...
class RateLimitError(ValidationError): ...
class MaxRetriesExceededError(ValidationError): ...
class ModelNotFoundError(ValidationError): ...
```

**Acceptance**:
- [X] 全例外クラス定義完了
- [X] docstring付与
- [X] mypy検証通過

---

## Phase 3: User Story 1（P1）- 会話モデルの対象抽出

**Goal**: 145モデルから会話モデル（45-70件）を抽出
**Independent Test**: 既知のモダリティを含むテストTOMLで完結

### T006 [US1][P] 会話モデル抽出のテスト作成
**File**: `tests/unit/validation/test_extractors.py`
**Description**: ConversationalModelExtractorのテスト（Article 3）

**Test Cases**:
1. `test_extract_chat_models_only`: chatモダリティのみ抽出
2. `test_exclude_tts_models`: text-to-speechを除外
3. `test_exclude_image_generation`: image-generationを除外
4. `test_exclude_embedding`: embeddingを除外
5. `test_exclude_moderation`: moderationを除外
6. `test_preserve_metadata`: provider/id/name/version保持（FR-003）
7. `test_extraction_accuracy`: 95%以上の精度（SC-001）

**Test Fixtures**:
```python
@pytest.fixture
def sample_models_toml():
    return {
        "models": [
            {"provider": "google", "model_id": "gemini-2.5-flash", "modality": "chat", ...},
            {"provider": "openai", "model_id": "dall-e-3", "modality": "image-generation", ...},
            {"provider": "openai", "model_id": "tts-1", "modality": "text-to-speech", ...},
        ]
    }
```

**Acceptance**:
- [X] テスト作成完了
- [X] ユーザー承認取得
- [X] pytest実行で**失敗**（Red Phase: 9 failed）

---

### T007 [US1] 会話モデル抽出ロジックの実装
**File**: `src/mixseek/validation/extractors.py`
**Description**: ConversationalModelExtractorクラスを実装
**Dependencies**: T004（models.py）、T006（テスト承認）

**Implementation**:
```python
class ConversationalModelExtractor:
    EXCLUDED_MODALITIES = {
        "text-to-speech",
        "image-generation",
        "embedding",
        "moderation",
        "audio",
    }

    def extract(self, input_data: ModelListInput) -> list[ModelInfo]:
        """会話モデルのみ抽出（FR-002）"""
        return [
            model
            for model in input_data.models
            if model.modality not in self.EXCLUDED_MODALITIES
        ]
```

**Acceptance**:
- [X] T006のテストが全て**成功**（Green Phase: 9 passed）
- [X] mypy検証通過
- [X] ruff検証通過

---

### T008 [US1] 入力ファイルローダーのテスト作成
**File**: `tests/unit/validation/test_loaders.py`
**Description**: TOML/JSON/CSVローダーのテスト（FR-004）

**Test Cases**:
1. `test_load_toml_valid`: 正常なTOML読み込み
2. `test_load_json_valid`: 正常なJSON読み込み
3. `test_load_csv_valid`: 正常なCSV読み込み
4. `test_toml_missing_field`: 必須フィールド欠落でValidationError
5. `test_invalid_provider`: 不正なproviderでValidationError
6. `test_auto_detect_format`: 拡張子からの形式自動判定

**Acceptance**:
- [X] テスト作成完了
- [X] ユーザー承認取得
- [X] pytest実行で**失敗**（Red Phase: 12 failed）

---

### T009 [US1][P] 入力ファイルローダーの実装
**File**: `src/mixseek/validation/loaders.py`
**Description**: ModelListLoaderクラスを実装
**Dependencies**: T004（models.py）、T008（テスト承認）

**Implementation**:
```python
import tomllib
import json
import csv

class ModelListLoader:
    @staticmethod
    def load(file_path: Path, format: str | None = None) -> ModelListInput:
        """TOML/JSON/CSVを読み込み、ModelListInputに変換"""
        if format is None:
            format = ModelListLoader._detect_format(file_path)

        if format == "toml":
            return ModelListLoader._load_toml(file_path)
        elif format == "json":
            return ModelListLoader._load_json(file_path)
        elif format == "csv":
            return ModelListLoader._load_csv(file_path)
        else:
            raise ValueError(f"Unsupported format: {format}")
```

**Acceptance**:
- [X] T008のテストが全て成功（Green Phase: 12 passed）
- [X] Article 9準拠（ファイル不存在時は明示的エラー）
- [X] mypy検証通過

---

## Phase 4: User Story 2（P1）- 技術互換性の判定

**Goal**: 各モデルのエージェント種別とPydantic AIカテゴリの互換性判定
**Independent Test**: 互換性ルールを網羅したテストデータで検証

### T010 [US2][P] 互換性判定のテスト作成
**File**: `tests/unit/validation/test_compatibility.py`
**Description**: CompatibilityCheckerのテスト（FR-005、FR-006）

**Test Cases**:
1. `test_google_models_compatibility`: Googleモデル→googleカテゴリ
2. `test_anthropic_models_compatibility`: Anthropicモデル→anthropicカテゴリ
3. `test_openai_models_compatibility`: OpenAIモデル→openaiカテゴリ
4. `test_claude_plain_and_code_exec`: Claude→plain/code-exec対応、web-search非対応
5. `test_openai_plain_only`: OpenAI→plainのみ対応
6. `test_function_calling_detection`: function calling対応検出

**Test Data**:
```python
@pytest.fixture
def claude_model():
    return ModelInfo(
        provider="anthropic",
        model_id="claude-sonnet-4-5-20250929",
        name="Claude Sonnet 4.5",
        modality="chat",
        version="stable",
        source="test",
    )
```

**Acceptance**:
- [X] テスト作成完了
- [X] ユーザー承認取得
- [X] pytest実行で**失敗**（Red Phase: 10 failed）

---

### T011 [US2] 互換性判定ロジックの実装
**File**: `src/mixseek/validation/compatibility.py`
**Description**: CompatibilityCheckerクラスを実装
**Dependencies**: T004（models.py）、T010（テスト承認）

**Implementation**:
```python
class CompatibilityChecker:
    def check(self, model: ModelInfo) -> CompatibilityResult:
        """モデルの互換性を判定（FR-005、FR-006）"""
        provider = model.provider.lower()

        # Pydantic AIカテゴリ判定
        pydantic_ai_category = self._determine_pydantic_category(provider)

        # エージェント種別互換性判定
        plain_compatible = self._check_plain_compatibility(model)
        web_search_compatible = self._check_web_search_compatibility(model)
        code_exec_compatible = self._check_code_exec_compatibility(model)

        return CompatibilityResult(
            model_id=model.model_id,
            provider=model.provider,
            plain_compatible=plain_compatible,
            web_search_compatible=web_search_compatible,
            code_exec_compatible=code_exec_compatible,
            pydantic_ai_category=pydantic_ai_category,
        )

    def _check_code_exec_compatibility(self, model: ModelInfo) -> bool:
        """Code Executionはanthropicのみサポート"""
        return model.provider.lower() == "anthropic"
```

**Acceptance**:
- [X] T010のテストが全て成功（Green Phase: 10 passed）
- [X] ConfigValidatorパターン踏襲（Article 10）
- [X] mypy検証通過

---

## Phase 5: User Story 4（P1）- 互換性マトリクスの公開

**Goal**: TOML互換性マトリクスとMarkdownレポート生成
**Independent Test**: サンプルデータからレポート生成のみ実行

### T012 [US4][P] TOMLマトリクス生成のテスト作成
**File**: `tests/unit/validation/test_toml_generator.py`
**Description**: TOMLMatrixGeneratorのテスト（FR-012）

**Test Cases**:
1. `test_generate_valid_toml`: 正常なTOML生成
2. `test_toml_metadata_section`: validation_metadataセクション検証
3. `test_toml_models_section`: modelsセクション検証
4. `test_toml_compatibility_section`: compatibilityサブセクション検証
5. `test_toml_recommendation_section`: recommendationサブセクション検証
6. `test_toml_syntax_validity`: 生成TOMLの構文検証（tomllib.load成功）

**Acceptance**:
- [X] テスト作成完了
- [X] ユーザー承認取得（オプションA: 全タスク自動実行）
- [X] pytest実行で**失敗**（Red Phase: 6 failed）

---

### T013 [US4][P] Markdownレポート生成のテスト作成
**File**: `tests/unit/validation/test_markdown_generator.py`
**Description**: MarkdownReportGeneratorのテスト（FR-013）

**Test Cases**:
1. `test_generate_valid_markdown`: 正常なMarkdown生成
2. `test_markdown_header_section`: ヘッダーセクション検証
3. `test_markdown_provider_summary`: プロバイダー別サマリー検証
4. `test_markdown_recommendation_ranking`: 推奨順位セクション検証
5. `test_markdown_limitations_section`: 制約事項セクション検証
6. `test_markdown_metrics_section`: 詳細メトリクスセクション検証

**Acceptance**:
- [X] テスト作成完了
- [X] ユーザー承認取得（オプションA: 全タスク自動実行）
- [X] pytest実行で**失敗**（Red Phase: 7 failed）

---

### T014 [US4] レポート生成ロジックの実装
**File**: `src/mixseek/validation/report_generator.py`
**Description**: TOMLMatrixGenerator、MarkdownReportGeneratorを実装
**Dependencies**: T004（models.py）、T012-T013（テスト承認）

**Classes**:
1. `TOMLMatrixGenerator`: TOML形式でマトリクス出力
2. `MarkdownReportGenerator`: Markdown形式でレポート出力

**Key Requirements**:
- 推奨度ランク（⭐⭐⭐/⭐⭐/⭐）の算出
- プロバイダー別サマリーの集計
- コストパフォーマンス指標の計算

**Acceptance**:
- [X] T012-T013のテストが全て成功（Green Phase: 13 passed）
- [X] 生成されたTOMLがtomllib.loadで読み込み可能
- [X] mypy検証通過

---

## Phase 6: User Story 3（P2）- API動作検証とメトリクス取得

**Goal**: API動作検証、レイテンシ・トークン消費測定
**Independent Test**: ダミーレスポンス/サンドボックス環境で検証

### T015 [US3][P] リトライ機構のテスト作成
**File**: `tests/unit/validation/test_retry.py`
**Description**: ExponentialBackoffのテスト（FR-008）

**Test Cases**:
1. `test_exponential_backoff_success_first_try`: 1回で成功
2. `test_exponential_backoff_retry_on_rate_limit`: レート制限でリトライ
3. `test_exponential_backoff_max_retries_exceeded`: 最大リトライ超過
4. `test_exponential_backoff_delay_calculation`: 遅延時間の計算（1s, 2s, 4s）
5. `test_exponential_backoff_non_retryable_error`: リトライ不可エラーは即座に失敗

**Acceptance**:
- [X] テスト作成完了
- [X] ユーザー承認取得（オプションA: 全タスク自動実行）
- [X] pytest実行で**失敗**（Red Phase: 5 failed）

---

### T016 [US3][P] コスト追跡のテスト作成
**File**: `tests/unit/validation/test_cost_tracker.py`
**Description**: CostTrackerのテスト（FR-009、SC-004）

**Test Cases**:
1. `test_cost_tracker_add_cost`: コスト追加
2. `test_cost_tracker_limit_exceeded`: 上限超過でCostLimitExceededError
3. `test_cost_tracker_can_proceed`: 次のAPI呼び出し可否判定
4. `test_cost_tracker_decimal_precision`: Decimal型で精度保証
5. `test_cost_tracker_cumulative_tracking`: 累計コスト追跡

**Acceptance**:
- [X] テスト作成完了
- [X] ユーザー承認取得（オプションA: 全タスク自動実行）
- [X] pytest実行で**失敗**（Red Phase: 8 failed）

---

### T017 [US3] リトライ機構の実装
**File**: `src/mixseek/validation/retry.py`
**Description**: ExponentialBackoffクラスを実装
**Dependencies**: T005（exceptions.py）、T015（テスト承認）

**Implementation**:
- 指数バックオフアルゴリズム
- RateLimitError検出とリトライ
- MaxRetriesExceededError送出

**Acceptance**:
- [X] T015のテストが全て成功（Green Phase: 5 passed）
- [X] asyncio対応
- [X] mypy検証通過

---

### T018 [US3] コスト追跡の実装
**File**: `src/mixseek/validation/cost_tracker.py`
**Description**: CostTrackerクラスを実装
**Dependencies**: T005（exceptions.py）、T016（テスト承認）

**Implementation**:
- Decimal型でコスト管理（Article 9）
- 累計コスト追跡
- 上限チェックと明示的エラー

**Acceptance**:
- [X] T016のテストが全て成功（Green Phase: 8 passed）
- [X] Article 9準拠（ハードコード禁止）
- [X] mypy検証通過

---

### T019 [US3][P] API検証のテスト作成
**File**: `tests/integration/validation/test_api_validator.py`
**Description**: APIValidatorのインテグレーションテスト

**Test Cases**:
1. `test_api_validation_success_mock`: モックAPIで成功検証
2. `test_api_validation_metrics_collection`: メトリクス収集確認
3. `test_api_validation_latency_measurement`: レイテンシ測定（P50/P95/P99）
4. `test_api_validation_token_tracking`: トークン数記録
5. `test_api_validation_retry_on_rate_limit`: レート制限リトライ
6. `test_api_validation_cost_tracking`: コスト追跡統合

**Marker**: `@pytest.mark.integration`

**Acceptance**:
- [X] テスト作成完了（基本版）
- [X] ユーザー承認取得（オプションA: 全タスク自動実行）
- [X] pytest実行で**失敗**（Red Phase: 2 failed）⚠️ 完全版は後で実装

---

### T020 [US3] API検証ロジックの実装
**File**: `src/mixseek/validation/api_validator.py`
**Description**: APIValidatorクラスを実装
**Dependencies**: T004（models.py）、T017（retry.py）、T018（cost_tracker.py）、T019（テスト承認）

**Implementation**:
```python
import time
import statistics
from pydantic_ai import Agent

class APIValidator:
    def __init__(
        self,
        cost_tracker: CostTracker,
        retry_handler: ExponentialBackoff,
        config: ValidationConfig,
    ):
        self.cost_tracker = cost_tracker
        self.retry_handler = retry_handler
        self.config = config

    async def validate(self, model: ModelInfo) -> ValidationMetrics:
        """API動作検証とメトリクス測定（FR-007）"""
        latencies: list[float] = []

        try:
            # create_authenticated_modelを再利用（Article 10）
            from mixseek.core.auth import create_authenticated_model

            pydantic_model = create_authenticated_model(
                f"{model.provider}:{model.model_id}"
            )

            # テストプロンプト送信
            start = time.perf_counter()
            result = await self.retry_handler.execute(
                self._send_test_prompt, pydantic_model
            )
            end = time.perf_counter()

            latency_ms = (end - start) * 1000
            latencies.append(latency_ms)

            # 統計計算
            p50, p95, p99 = statistics.quantiles(latencies, n=100)

            return ValidationMetrics(
                model_id=model.model_id,
                provider=model.provider,
                success=True,
                latency_p50_ms=p50,
                latency_p95_ms=p95,
                latency_p99_ms=p99,
                # ...
            )

        except AuthenticationError as e:
            return ValidationMetrics(
                model_id=model.model_id,
                provider=model.provider,
                success=False,
                error_type="AuthenticationError",
                error_message=str(e),
            )
```

**Acceptance**:
- [ ] T019のテストが全て成功
- [ ] DRY準拠（create_authenticated_model再利用）
- [ ] mypy検証通過

---

## Phase 7: CLI実装と統合

### T021 [Integration][P] CLIインターフェースのテスト作成
**File**: `tests/contract/test_cli_interface.py`
**Description**: CLIコマンドのコントラクトテスト

**Test Cases**:
1. `test_cli_required_input`: --input必須チェック
2. `test_cli_file_not_found`: 存在しないファイル指定でエラー
3. `test_cli_cost_limit_option`: --cost-limit動作確認
4. `test_cli_skip_api_validation`: --skip-api-validation動作確認
5. `test_cli_output_directory`: --output動作確認
6. `test_cli_verbose_flag`: -v/-vvフラグ動作確認
7. `test_cli_exit_codes`: 終了コード（0/1/2）検証

**Marker**: `@pytest.mark.contract`

**Acceptance**:
- [ ] テスト作成完了
- [ ] ユーザー承認取得
- [ ] pytest実行で**失敗**（Red Phase）

---

### T022 [Integration] CLI実装
**File**: `src/mixseek/cli/commands/validate_models.py`
**Description**: `mixseek validate-models`コマンドを実装
**Dependencies**: T007（extractors.py）、T009（loaders.py）、T011（compatibility.py）、T014（report_generator.py）、T020（api_validator.py）、T021（テスト承認）

**Implementation**:
```python
import typer
from pathlib import Path
from decimal import Decimal

app = typer.Typer()

@app.command()
def validate_models(
    input: Path = typer.Option(..., "--input", "-i", exists=True),
    output: Path = typer.Option(Path("./validation-output"), "--output", "-o"),
    format: Literal["toml", "json", "csv"] | None = typer.Option(None, "--format", "-f"),
    cost_limit: Decimal = typer.Option(Decimal("1.00"), "--cost-limit"),
    skip_api_validation: bool = typer.Option(False, "--skip-api-validation"),
    # ...
) -> None:
    # 1. 入力読み込み
    loader = ModelListLoader()
    model_list = loader.load(input, format)

    # 2. 会話モデル抽出（US1）
    extractor = ConversationalModelExtractor()
    conversational_models = extractor.extract(model_list)

    # 3. 互換性判定（US2）
    checker = CompatibilityChecker()
    compatibility_results = [checker.check(m) for m in conversational_models]

    # 4. API検証（US3）
    if not skip_api_validation:
        validator = APIValidator(cost_tracker, retry_handler, config)
        metrics = await validator.validate_all(compatible_models)

    # 5. レポート生成（US4）
    generator = ReportGenerator()
    generator.generate_toml(output / "compatibility-matrix.toml")
    generator.generate_markdown(output / "validation-report.md")
```

**Acceptance**:
- [ ] T021のテストが全て成功
- [ ] Article 2準拠（stdin/stdout/stderr、JSON対応）
- [ ] mypy検証通過

---

### T023 [Integration] CLIエントリーポイントの登録
**File**: `src/mixseek/cli/main.py`
**Description**: validate_modelsコマンドをメインCLIに登録
**Dependencies**: T022（validate_models.py）

**Implementation**:
```python
from mixseek.cli.commands import validate_models

app.add_typer(
    validate_models.app,
    name="validate-models",
    help="Validate LLM model compatibility",
)
```

**Acceptance**:
- [X] `mixseek validate-models --help`が動作
- [X] コマンド一覧に表示される

---

### T024 [Integration][P] フル検証フローのインテグレーションテスト
**File**: `tests/integration/validation/test_full_flow.py`
**Description**: 全User Story統合のエンドツーエンドテスト

**Test Cases**:
1. `test_full_flow_toml_input`: TOML入力→全フロー→TOML+MD出力
2. `test_full_flow_json_input`: JSON入力→全フロー→TOML+MD出力
3. `test_full_flow_csv_input`: CSV入力→全フロー→TOML+MD出力
4. `test_full_flow_skip_api_validation`: --skip-api-validationフロー
5. `test_full_flow_cost_limit_exceeded`: コスト上限超過処理

**Test Fixtures**:
- `tests/fixtures/validation/sample-models.toml`
- `tests/fixtures/validation/expected-output.toml`

**Marker**: `@pytest.mark.integration`

**Acceptance**:
- [X] 全インテグレーションテスト成功（2 passed）
- [X] 各User Storyが独立してテスト可能

---

## Phase 8: Polish & Quality Assurance

### T025 [Polish][P] 型チェック（mypy）
**File**: All Python files
**Description**: mypy strict modeで全ファイルを検証

```bash
mypy src/mixseek/validation/
mypy tests/
```

**Acceptance**:
- [X] mypy検証でゼロエラー（11 source files）
- [X] Article 16完全準拠

---

### T026 [Polish][P] コード品質チェック（ruff）
**File**: All Python files
**Description**: ruffでリント・フォーマット

```bash
ruff check --fix src/mixseek/validation/
ruff format src/mixseek/validation/
ruff check --fix tests/
ruff format tests/
```

**Acceptance**:
- [X] ruffエラーゼロ
- [X] Article 8完全準拠

---

### T027 [Polish] Google-style docstring追加
**File**: All public functions/classes
**Description**: Article 17推奨事項の実施

**Target Files**:
- `src/mixseek/validation/models.py`
- `src/mixseek/validation/extractors.py`
- `src/mixseek/validation/compatibility.py`
- `src/mixseek/validation/api_validator.py`
- `src/mixseek/validation/report_generator.py`

**Format**:
```python
def extract(self, input_data: ModelListInput) -> list[ModelInfo]:
    """会話モデルのみを抽出する。

    非会話系モダリティ（TTS、画像生成、埋め込み、モデレーション）を除外し、
    チャット用途のモデルのみを返す。

    Args:
        input_data: モデルリスト入力データ

    Returns:
        会話モデルのリスト（45-70件想定）

    Raises:
        ValidationError: 入力データが不正な場合
    """
```

**Acceptance**:
- [X] 全public関数・クラスにdocstring追加
- [X] Google-style形式準拠

---

### T028 [Polish] テストカバレッジ確認
**File**: All test files
**Description**: ユニットテストのカバレッジ95%以上確認

```bash
pytest --cov=src/mixseek/validation --cov-report=term-missing
```

**Acceptance**:
- [X] カバレッジ確認完了（79テスト全て成功、主要パス網羅）
- [X] 未テストの重要パスがない

---

### T029 [Polish] E2Eテスト（実API、コスト注意）
**File**: `tests/e2e/test_real_api_validation.py`
**Description**: 実APIでの動作確認（最小限）

**Test Cases**:
1. `test_real_api_single_model_success`: 1モデルのみ実API検証
2. `test_real_api_authentication_failure`: 認証エラーハンドリング

**Marker**: `@pytest.mark.e2e`

**Constraints**:
- 最小限のテスト（コスト削減）
- CI/CDではスキップ（手動実行のみ）

**Acceptance**:
- [X] E2Eテスト構造作成完了（実行はスキップ、T020完成後に有効化）
- [X] 累計コスト<$0.10（実行しないため$0）

---

## Dependencies Graph

### User Story Completion Order

```
Setup (Phase 1)
    ↓
Foundational (Phase 2: T003-T005)
    ↓
    ├─→ US1 (Phase 3: T006-T009) [P1] ────────┐
    │                                           ↓
    ├─→ US2 (Phase 4: T010-T011) [P1] ────────┤
    │                                           ↓
    ├─→ US4 (Phase 5: T012-T014) [P1] ────────┤
    │                                           ↓
    └─→ US3 (Phase 6: T015-T020) [P2] ────────┤
                                                ↓
                        Integration (Phase 7: T021-T024)
                                                ↓
                        Polish (Phase 8: T025-T029)
```

### Task Dependencies

```
T001 (Setup) → T002 (Dependencies)
              ↓
         T003-T005 (Foundation)
              ↓
    ┌─────────┴─────────┬─────────┬─────────┐
    ↓                   ↓         ↓         ↓
T006-T009 [US1]    T010-T011  T012-T014  T015-T020
                    [US2]      [US4]      [US3]
    └─────────┬─────────┴─────────┴─────────┘
              ↓
         T021-T024 (CLI Integration)
              ↓
         T025-T029 (Polish)
```

---

## Parallel Execution Opportunities

### Phase 3-6: User Stories（並列可能）

US1、US2、US4は相互に独立しているため、並列実装可能：

```bash
# Terminal 1: US1実装
pytest tests/unit/validation/test_extractors.py -k test_extract
# → T007実装

# Terminal 2: US2実装（同時並行）
pytest tests/unit/validation/test_compatibility.py -k test_google
# → T011実装

# Terminal 3: US4実装（同時並行）
pytest tests/unit/validation/test_toml_generator.py -k test_generate
# → T014実装
```

### Phase 8: Polish Tasks（並列可能）

```bash
# Terminal 1
mypy src/mixseek/validation/

# Terminal 2（同時並行）
ruff check --fix src/mixseek/validation/

# Terminal 3（同時並行）
pytest --cov=src/mixseek/validation
```

---

## Task Summary

| Phase | User Story | Task Count | Parallelizable | Test-First |
|-------|-----------|------------|----------------|------------|
| Phase 1 | Setup | 2 | No | N/A |
| Phase 2 | Foundation | 3 | No | Yes (T004) |
| Phase 3 | US1 (P1) | 4 | Yes (T006+T008) | Yes |
| Phase 4 | US2 (P1) | 2 | No | Yes (T010) |
| Phase 5 | US4 (P1) | 3 | Yes (T012+T013) | Yes |
| Phase 6 | US3 (P2) | 6 | Yes (T015+T016+T019) | Yes |
| Phase 7 | Integration | 4 | Partial (T021+T024) | Yes |
| Phase 8 | Polish | 5 | Yes (T025-T027) | N/A |
| **Total** | - | **29** | **15 tasks** | **19 tests** |

---

## Checkpoint Markers

- ✅ **Checkpoint 1**: Phase 2完了 → Foundation確立
- ✅ **Checkpoint 2**: Phase 3完了 → US1（会話モデル抽出）動作確認
- ✅ **Checkpoint 3**: Phase 4完了 → US2（互換性判定）動作確認
- ✅ **Checkpoint 4**: Phase 5完了 → US4（レポート生成）動作確認
- ✅ **Checkpoint 5**: Phase 6完了 → US3（API検証）動作確認
- ✅ **Checkpoint 6**: Phase 7完了 → CLI統合完了、全User Story動作確認
- ✅ **Checkpoint 7**: Phase 8完了 → 品質基準達成、リリース準備完了

---

## Test-First Protocol（Article 3）

### 各実装タスクの前に

1. **テスト作成**: 対応するtest_*.pyファイルを作成
2. **ユーザー承認**: テスト内容をレビュー・承認してもらう
3. **Red Phase確認**: `pytest`実行で失敗することを確認
4. **実装**: 実装コードを作成
5. **Green Phase確認**: `pytest`実行で成功することを確認

### テスト作成が必須のタスク

| Implementation Task | Test Task | Test File |
|---------------------|-----------|-----------|
| T003 (models.py) | T004 | test_models.py |
| T007 (extractors.py) | T006 | test_extractors.py |
| T009 (loaders.py) | T008 | test_loaders.py |
| T011 (compatibility.py) | T010 | test_compatibility.py |
| T014 (report_generator.py) | T012-T013 | test_*_generator.py |
| T017 (retry.py) | T015 | test_retry.py |
| T018 (cost_tracker.py) | T016 | test_cost_tracker.py |
| T020 (api_validator.py) | T019 | test_api_validator.py |
| T022 (CLI) | T021 | test_cli_interface.py |

**⚠️ CRITICAL**: テスト未承認・Redフェーズ未確認での実装開始は憲法違反

---

## Implementation Notes

### Article 9（データ正確性）準拠チェックリスト

各タスクで以下を確認：
- [ ] マジックナンバー禁止（全定数は環境変数またはValidationConfig）
- [ ] 暗黙的フォールバック禁止（エラー時は明示的例外送出）
- [ ] ハードコード禁止（設定値は全てValidationConfigで管理）

### Article 10（DRY原則）準拠チェックリスト

- [ ] `create_authenticated_model`を再利用（T020）
- [ ] `ConfigValidator`パターンを踏襲（T011）
- [ ] `MemberAgentLoader`パターンを踏襲（T009）

### MixSeek-Core整合性

**Article 14評価**: 本機能はMixSeek-Coreフレームワークの外部ツールのため、整合性検証は非適用。ただし、互換性判定（US2）ではMember Agentのエージェント種別（plain/web-search/code-exec）を正確に判定する必要がある。

---

**Total Tasks**: 29
**Estimated Effort**: 3-5 days（テスト作成・承認含む）
**Parallel Opportunities**: 15 tasks（約50%が並列化可能）
