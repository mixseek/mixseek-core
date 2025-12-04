# 機能仕様書: ラウンド設定のTOML対応

**Feature Branch**: `feature/101-round-config`
**作成日**: 2025-11-18
**ステータス**: Draft
**入力**: ユーザー説明: "OrchestratorTask モデルに定義されている max_rounds min_rounds submission_timeout_seconds judgment_timeout_seconds フィールドを TOML 定義できるようにしてください。具体的には OrchestratorSettings モデルに同等のフィールドを追加し、orchestrator.toml で設定できるようにします。specディレクトリ名: 101-round-config Gitブランチ: feature/101-round-config"

## Clarifications

### Session 2025-11-18

- Q: `mixseek config list`コマンドでの新規ラウンド設定フィールドの表示対応は必要か？ → A: 既存の`mixseek config`インフラの自動検出により、追加作業なしで表示される
- Q: OrchestratorSettingsに追加するラウンド設定フィールドのバリデーション制約（FR-001～FR-004の範囲制約、FR-005の`min_rounds <= max_rounds`相互検証）はどこで実装すべきか？ → A: 両方で実装（OrchestratorSettingsで早期エラー検出、OrchestratorTaskで防御的プログラミング）
- Q: 既存の`timeout_per_team_seconds`と新規の`submission_timeout_seconds`/`judgment_timeout_seconds`の関係は？ → A: 独立したタイムアウト（異なるレイヤーで適用され、相互検証は不要）

## ユーザーシナリオとテスト *(必須)*

### ユーザーストーリー 1 - TOMLファイルによる設定 (優先度: P1)

システム運用者として、orchestrator.tomlでラウンド実行パラメータ（最大ラウンド数、最小ラウンド数、タイムアウト）を設定したい。これにより、コードや環境変数を変更せずにマルチラウンドの動作を調整できる。

**優先度の理由**: これは本機能の中核となる能力であり、ラウンドパラメータのTOMLベース設定を可能にする。これがなければ、ユーザーはラウンド実行設定を宣言的に管理できない。

**独立したテスト**: カスタムラウンド設定を含むorchestrator.tomlを作成し、`mixseek exec` コマンドを実行し、ラウンドコントローラーがハードコードされたデフォルト値ではなく設定値を使用することを確認する。

**受け入れシナリオ**:

1. **前提** orchestrator.tomlに`max_rounds = 10`が含まれる、**実行時** タスクを実行する、**結果** システムは最大10ラウンドの実行を許可する
2. **前提** orchestrator.tomlに`min_rounds = 3`が含まれる、**実行時** タスクを実行する、**結果** システムはLLMベースの終了判定前に最低3ラウンドを保証する
3. **前提** orchestrator.tomlに`submission_timeout_seconds = 600`が含まれる、**実行時** チーム提出が600秒を超える、**結果** システムはそのラウンドをタイムアウトエラーで終了する
4. **前提** orchestrator.tomlに`judgment_timeout_seconds = 120`が含まれる、**実行時** 改善判定が120秒を超える、**結果** システムは次のラウンドへ継続するフォールバックを行う

---

### ユーザーストーリー 2 - 環境変数による上書き (優先度: P2)

異なる環境（dev/staging/prod）で実行するシステム運用者として、環境変数を使用してTOML設定されたラウンドパラメータを上書きしたい。これにより、設定ファイルを変更せずに環境ごとの調整ができる。

**優先度の理由**: 環境固有の調整のための運用上の柔軟性を提供する。feature 051-configurationで確立された標準的な設定優先順位（ENV > TOML > デフォルト値）に従う。

**独立したテスト**: 環境変数（例：`MIXSEEK_MAX_ROUNDS=7`）を設定し、異なる値を含むorchestrator.tomlでタスクを実行し、環境変数が優先されることを確認する。

**受け入れシナリオ**:

1. **前提** `MIXSEEK_MAX_ROUNDS=7`環境変数が設定され、orchestrator.tomlに`max_rounds = 5`が含まれる、**実行時** タスクを実行する、**結果** システムはmax_rounds=7を使用する（環境変数が優先）
2. **前提** `MIXSEEK_MIN_ROUNDS=1`環境変数が設定される、**実行時** タスクを実行する、**結果** システムはTOML設定に関わらずmin_rounds=1を使用する

---

### ユーザーストーリー 3 - バリデーションとエラー処理 (優先度: P1)

システム運用者として、無効なラウンド設定値を提供した場合に明確なバリデーションエラーが表示されるようにしたい。これにより、タスク実行前に設定ミスを迅速に特定して修正できる。

**優先度の理由**: ランタイム障害を防ぎ、設定の正確性を保証するために重要。無効な設定（例：min_rounds > max_rounds）は起動時に検出される必要がある。

**独立したテスト**: 無効な設定（例：`max_rounds = 0`、`max_rounds = 5`で`min_rounds = 10`）を提供し、設定読み込みを試み、明確なエラーメッセージが表示されることを確認する。

**受け入れシナリオ**:

1. **前提** orchestrator.tomlに`max_rounds = 0`が含まれる、**実行時** 設定を読み込む、**結果** システムはバリデーションエラー「max_roundsは1から10の間でなければなりません」を表示する
2. **前提** orchestrator.tomlに`min_rounds = 5`と`max_rounds = 3`が含まれる、**実行時** 設定を読み込む、**結果** システムはバリデーションエラー「min_rounds (5) は max_rounds (3) 以下でなければなりません」を表示する
3. **前提** orchestrator.tomlに`submission_timeout_seconds = -100`が含まれる、**実行時** 設定を読み込む、**結果** システムはバリデーションエラー「submission_timeout_secondsは正の値でなければなりません」を表示する

---

### エッジケース

- orchestrator.tomlにラウンド設定フィールドが一切指定されていない場合はどうなるか？（システムはOrchestratorSettingsのデフォルト値を使用すべき）
- 一部のラウンドフィールドのみがTOMLで指定されている場合はどうなるか？（システムは指定されたフィールドにはTOML値を、未指定フィールドにはデフォルト値を使用すべき）
- システムがラウンド設定に対して非整数または非数値を扱う場合はどうなるか？（Pydanticバリデーションが明確なエラーメッセージで拒否すべき）
- max_roundsが許可された最大値（10）に設定され、タスクが実際に10ラウンドに達した場合はどうなるか？（システムはexit_reason="max_rounds_reached"でラウンド10で正常に終了すべき）

## 要件 *(必須)*

### 機能要件

- **FR-001**: OrchestratorSettingsモデルは、デフォルト値5、制約範囲[1, 10]の`max_rounds`フィールドをPydanticバリデーション制約付きで含む必要がある（OrchestratorTaskの既存制約と一致）
- **FR-002**: OrchestratorSettingsモデルは、デフォルト値2、制約範囲[1, max_rounds]の`min_rounds`フィールドをPydanticバリデーション制約付きで含む必要がある（OrchestratorTaskの既存制約と一致）
- **FR-003**: OrchestratorSettingsモデルは、デフォルト値300、正の整数に制約された`submission_timeout_seconds`フィールドをPydanticバリデーション制約付きで含む必要がある（OrchestratorTaskの既存制約と一致）
- **FR-004**: OrchestratorSettingsモデルは、デフォルト値60、正の整数に制約された`judgment_timeout_seconds`フィールドをPydanticバリデーション制約付きで含む必要がある（OrchestratorTaskの既存制約と一致）
- **FR-005**: システムは設定読み込み時（OrchestratorSettings）およびタスク作成時（OrchestratorTask）の両方で`min_rounds <= max_rounds`を検証する必要がある（二重検証による早期エラー検出と防御的プログラミング）
- **FR-006**: Orchestratorはタスク作成時にOrchestratorSettingsからOrchestratorTaskへラウンド設定値を渡す必要がある
- **FR-007**: orchestrator.tomlはTOML構文を使用してラウンド設定フィールドの指定をサポートする必要がある（例：`max_rounds = 10`）
- **FR-008**: ラウンド設定フィールドの読み込みは優先順位に従う必要がある：環境変数 > TOMLファイル > デフォルト値（ラウンド設定専用のCLI引数はサポートしない）
- **FR-009**: システムはラウンド設定制約が違反された場合に明確なバリデーションエラーメッセージを提供する必要がある
- **FR-010**: すべてのラウンド設定フィールドはOrchestratorTaskフィールドの説明と一致する説明でOrchestratorSettingsに文書化される必要がある
- **FR-011**: Orchestratorクラスは`OrchestratorSettings`を直接受け取る（アーキテクチャの簡素化：OrchestratorSettingsがworkspaceとteamsを含むため、中間モデルは不要。以前の`OrchestratorConfig`は削除済み）

### 主要エンティティ

- **OrchestratorSettings**: オーケストレータ動作の設定スキーマ、ラウンド実行パラメータを含むように拡張（max_rounds、min_rounds、submission_timeout_seconds、judgment_timeout_seconds）
- **OrchestratorTask**: インスタンス化時にOrchestratorSettingsからラウンド設定を受け取るランタイムタスク表現
- **orchestrator.toml**: 既存のオーケストレータ設定（timeout_per_team_seconds、teams）に加えてラウンド実行パラメータをサポートする設定ファイル形式

## 成功基準 *(必須)*

### 測定可能な成果

- **SC-001**: 運用者はorchestrator.toml経由でmax_roundsを設定でき、システムが設定された制限を尊重することを観察できる（制限に達するタスクを実行して検証）
- **SC-002**: 運用者はorchestrator.toml経由でmin_roundsを設定でき、システムがLLMベースの終了前に最低その数のラウンドを保証することを観察できる（round_statusテーブルを調査して検証）
- **SC-003**: 運用者はorchestrator.toml経由でタイムアウト値を設定でき、タイムアウト適用を観察できる（意図的にタイムアウトをトリガーして検証）
- **SC-004**: 設定バリデーションは無効な設定（min_rounds > max_rounds、負のタイムアウト、範囲外の値）を読み込み後1秒以内に明確なエラーメッセージで拒否する
- **SC-005**: 環境変数はTOML設定値を正常に上書きする（競合する値を設定して使用される値を検査して検証）
- **SC-006**: すべての4つのラウンド設定フィールドはorchestrator.tomlで指定されていない場合にデフォルト値で正しく動作する（明示的な設定なしでタスクを実行して検証）
- **SC-007**: `mixseek config list`コマンドを実行すると、新規追加された4つのラウンド設定フィールド（max_rounds、min_rounds、submission_timeout_seconds、judgment_timeout_seconds）がOrchestratorSettings配下に表示される（追加実装なしでPydantic Settingsの自動検出により実現）

## 前提条件

- 既存のConfigurationManagerインフラストラクチャ（051-configurationから）がTOML読み込み、環境変数優先順位、バリデーションを処理する - 新しい設定読み込みメカニズムは不要
- OrchestratorTaskのデフォルト値（max_rounds=5、min_rounds=2、submission_timeout_seconds=300、judgment_timeout_seconds=60）は妥当なデフォルト値であり、OrchestratorSettingsでも保持すべき
- orchestrator.tomlファイル形式は既に追加フィールドをサポートしており、既存機能を壊さない
- バリデーション制約はOrchestratorSettingsとOrchestratorTaskの両方で定義され、同一の制約を維持する（max_rounds: 1-10、min_rounds: >= 1、タイムアウト: 正の整数、min_rounds <= max_rounds）。OrchestratorSettingsで早期エラー検出、OrchestratorTaskで防御的プログラミングを実現
- RoundController実装は既にOrchestratorTaskのラウンド設定フィールドを正しく使用している - ラウンド実行ロジックの変更は不要
- 本機能はラウンド設定のためのCLI引数を必要としない（TOMLと環境変数で十分）
- `mixseek config list`および`mixseek config show`コマンドは、Pydantic Settingsの自動フィールド検出機能により、OrchestratorSettingsに追加された新規フィールド（max_rounds、min_rounds、submission_timeout_seconds、judgment_timeout_seconds）を追加実装なしで自動的に表示する
- 既存の`timeout_per_team_seconds`（オーケストレータレベル）と新規の`submission_timeout_seconds`/`judgment_timeout_seconds`（ラウンドレベル）は異なるレイヤーで独立に適用されるタイムアウトであり、相互バリデーション（例：ラウンドタイムアウト合計がチームタイムアウトを超えないこと）は不要

## 依存関係

- Feature 051-configuration: ConfigurationManager、OrchestratorSettings基底モデル、TOML読み込みインフラストラクチャを提供
- Feature 012-round-controller: 本機能がTOML経由で公開する既存のラウンド設定フィールドを持つOrchestratorTaskモデルを定義
- Pydantic Settings: フィールドバリデーション、環境変数サポート、設定優先順位を提供

## スコープ外

- ラウンド設定のためのCLI引数（--max-rounds、--min-rounds等） - TOMLと環境変数のみサポート
- チームごとのラウンド設定（オーケストレーション内のすべてのチームが同じラウンド設定を使用）
- 実行中のラウンド設定の動的調整（設定は起動時に一度だけ読み込まれる）
- 既存のorchestrator.tomlファイルの移行（新しいフィールドは後方互換性のあるデフォルト値でオプション）
- ラウンド設定を編集するためのUI（運用者はorchestrator.tomlを直接編集）
