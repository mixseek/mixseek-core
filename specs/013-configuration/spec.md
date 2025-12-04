# Feature Specification: Pydantic Settings based Configuration Manager

**Feature Branch**: `051-configuration`
**Created**: 2025-11-11
**Status**: Draft
**Input**: User description: "plans/pydantic-settings-configuration-manager-evaluation.md を実装するための要件定義を行ってください。4つの設計原則に基づく統一的な設定管理システム"

**関連Issue**: #51 https://github.com/AlpacaTechSolution/mixseek-core/issues/51

**設計原則**:
- 原則1: 明示性の原則 (Principle of Explicitness) - すべての設定値には明示的な出所が存在しなければならない
- 原則2: 階層的フォールバックの原則 (Hierarchical Fallback) - 優先順位は明確かつ一貫していなければならない
- 原則3: 環境別設定の原則 (Environment-Specific Configuration) - 環境別に設定値を上書き可能でなければならない（デフォルト値は環境を問わず同一）
- 原則4: トレーサビリティの原則 (Traceability) - すべての設定値の出所が追跡可能でなければならない

## Clarifications

### Session 2025-11-11

- Q: 必須設定のバリデーションエラーは本番環境のみで発生するべきか？ → A: 開発・本番を問わず必須設定のエラーは検知されるべき
- Q: デフォルト値は環境別に異なるべきか？ → A: デフォルト値は開発・本番で同一。環境別の上書きは引数や環境変数で実現する
- Q: TOMLファイル設定は誰が管理するのか？ → A: 運用者・ユーザも管理するものとして扱う（開発者だけでなく）
- Q: User Story 6の対象者は誰か？ → A: 開発者以外（運用者・ユーザ）も対象にする
- Q: どのコンポーネントの設定を管理対象にするか？ → A: Orchestrator, RoundController の設定も管理できるようにする
- Q: CLI引数の解析に使用するライブラリは何か？ → A: argparseではなく、typerで実装されている
- Q: User Story 3の例はどのような設定を使うべきか？ → A: TIMEOUT_PER_TEAM_SECONDSなど明確な設定名を使用する
- Q: User Story 3でCLIにどの設定オプションを追加するか？ → A: **未定** - 今後の課題とする（候補: timeout_per_team_seconds, max_concurrent_members, leader/memberモデル設定等）
- Q: User Story 1の対象者と例は何を使うべきか？ → A: 開発者・運用者・ユーザを対象にし、TIMEOUT_PER_TEAM_SECONDSを例に使用する
- Q: Configuration Managerですべてのデフォルト値を参照することは可能か？ → A: 可能。機能要件として追加する
- Q: CLIで設定値を参照できるようにすべきか？ → A: 可能。mixseek config show, mixseek config listなどのコマンドを提供する
- Q: TOMLテンプレートファイルを生成する機能は必要か？ → A: 必要。mixseek config initコマンドで階層構造を意識したテンプレート生成を提供する（team.toml, member.toml等）

### Session 2025-11-12

- Q: MIXSEEK_WORKSPACEとTOMLファイル内の相対パスの扱いは？ → A: MIXSEEK_WORKSPACEは絶対パスで定義される必要があり、TOMLファイルに相対パスが記述されている場合は$MIXSEEK_WORKSPACEを基準としたpathに解決する
- Q: 「後方互換性」の定義は？レガシーコード許容との違いは？ → A: 「後方互換性」は既存TOML形式・環境変数など仕様で定義された公式インターフェースのサポートを指す。Article 9違反のレガシーコード実装の保持ではない。本仕様では「既存TOML形式との互換性維持」「仕様準拠形式サポート」といった明確な表現を優先する
- Q: `--config` オプションで指定するファイルの形式とバリデーション要件は？ → A: orchestrator の TOML ファイルのみを指定可能にし、`[orchestrator]` セクションの存在をバリデーションする。orchestrator にぶら下がる team や member の TOML 設定も再帰的に表示する
- Q: 再帰的表示の出力形式はどうすべきか？ → A: 階層的なインデント表示（orchestrator → team → member の階層構造を視覚化）を使用する
- Q: `mixseek config list` コマンドでも `--config` をサポートすべきか？ → A: ~~両方のコマンド（show と list）で `--config` をサポートする~~ **[2025-12-01 変更]** config list は `--config` をサポートしない。スキーマ情報のみを表示する役割に変更
- Q: orchestrator/team/member の参照チェーンで循環参照が発生した場合の動作は？ → A: 循環参照を検出し、明確なエラーメッセージ（参照パスを含む）を表示する
- Q: 再帰的読み込みの最大深度制限は必要か？ → A: 最大深度10階層の制限を設ける

### Session 2025-11-19

- Q: Evaluator の設定ファイルパスを orchestrator.toml から指定できるようにしたい。どこで対応すべきか？ → A: specs/013-configuration で対応可能。既存の Team 設定参照パターン（FR-032～FR-037）を踏襲し、OrchestratorSettings に `evaluator_config` フィールドを追加する
- Q: Evaluator クラスの初期化方法はどうあるべきか？ → A: `__init__(self, settings: EvaluatorSettings)` の形式で EvaluatorSettings を受け取り、内部で EvaluationConfig に変換する。変換には既存の `evaluator_settings_to_evaluation_config()` ヘルパーを使用する
- Q: 相対パスの解決基準は？ → A: Team 設定と同様に `MIXSEEK_WORKSPACE` を基準として解決する
- Q: ConfigurationManager に新しいメソッドが必要か？ → A: 不要。既存の `load_evaluation_settings(toml_file: Path)` メソッドが任意のパスから読み込めるため、これを使用する

### Session 2025-12-01

- Q: config list と config show のコマンドの役割が不明確。どう整理すべきか？ → A: **config list** はスキーマ情報（設定可能な項目、デフォルト値、型、説明）のみを表示。**config show** は実際の設定値を階層的に表示。config list から --config, --workspace, --environment オプションを削除し、役割を明確化する（Issue #217）
- Q: config show の --workspace オプションは必須にすべきか？ → A: 他の exec コマンドと同様に、--workspace は任意項目とし、MIXSEEK_WORKSPACE 環境変数をサポートする。優先順位: CLI --workspace > MIXSEEK_WORKSPACE 環境変数
- Q: --format オプションの名称を統一すべきか？ → A: exec コマンドと統一し、--output-format / -f に変更する。対応形式: table（デフォルト）, text, json
- Q: config list の table 形式で表示すべき列は何か？ → A: スキーマ情報のみを表示するため、**Key**（設定項目名）、**Default**（デフォルト値）、**Type**（型）、**Description**（説明）の4列を表示する。Value（実際の値）、Source（設定ソース）、Overridden（デフォルトから変更されているか）は config show でのみ表示する

## User Scenarios & Testing

### User Story 1 - 開発者・運用者・ユーザが環境変数で設定を上書き (Priority: P1)

開発者・運用者・ユーザとして、本番環境で環境変数を使って設定値を上書きし、コードやTOMLファイルを変更せずにデプロイできるようにしたい。

**Why this priority**: 最も基本的かつ重要な機能。環境変数による設定上書きができないと、環境別のデプロイが不可能になる。

**Independent Test**: 環境変数 `MIXSEEK_TIMEOUT_PER_TEAM_SECONDS=600` を設定し、アプリケーションを起動して設定値が反映されることを確認する。

**Acceptance Scenarios**:

1. **Given** TOMLファイルに `timeout_per_team_seconds = 300` が設定されている、**When** 環境変数 `MIXSEEK_TIMEOUT_PER_TEAM_SECONDS=600` を設定してアプリケーションを起動する、**Then** 実際のタイムアウト設定は `600` 秒になる
2. **Given** 環境変数が設定されていない、**When** アプリケーションを起動する、**Then** TOMLファイルの設定値が使用される
3. **Given** 環境変数とTOMLの両方に設定がある、**When** 設定の出所を確認する、**Then** 「環境変数から読み込まれた」というトレース情報が表示される

---

### User Story 2 - 開発者が設定値の出所を追跡 (Priority: P1)

開発者として、現在使用されている設定値がどこから来たのか（CLI、環境変数、TOML、デフォルト値）を確認でき、設定の問題をデバッグできるようにしたい。また、すべての設定項目のデフォルト値を参照し、現在の設定がデフォルトから変更されているかを確認できるようにしたい。

**Why this priority**: トレーサビリティ原則（原則4）の中核機能。設定の問題が発生した際、出所を追跡できないとデバッグが困難になる。デフォルト値を参照できることで、意図しない設定変更を検知できる。

**Independent Test**: `--debug` フラグを使ってアプリケーションを起動し、すべての設定値とその出所（ソース名、タイムスタンプ）が表示されることを確認する。また、デフォルト値一覧を取得し、現在値と比較できることを確認する。

**Acceptance Scenarios**:

1. **Given** アプリケーションが起動している、**When** `--debug` フラグを付けて起動する、**Then** 各設定値の出所（source_name, source_type）が識別可能な形で表示される（例: "environment_variables (env)", "config.toml (toml)", "CLI (init)", "default"）
2. **Given** 複数のソースで同じ設定が定義されている、**When** デバッグ情報を表示する、**Then** 実際に採用された値と、その優先順位（どのソースが選ばれたか）が表示される
3. **Given** 設定値が読み込まれた、**When** トレース情報にアクセスする、**Then** タイムスタンプ（いつ読み込まれたか）が記録されている
4. **Given** アプリケーションが起動している、**When** すべてのデフォルト値を取得する、**Then** 各設定項目のデフォルト値が一覧で表示される
5. **Given** 一部の設定が上書きされている、**When** 現在値とデフォルト値を比較する、**Then** デフォルトから変更されている設定項目が明示される

---

### User Story 3 - 開発者がCLI引数で一時的に設定を変更 (Priority: P2)

開発者として、テストやデバッグ時にCLI引数で設定を一時的に変更し、環境変数やTOMLファイルを編集せずに動作確認できるようにしたい。

**Why this priority**: 開発体験の向上に直結。一時的なテストのために設定ファイルを編集する手間を省ける。

**Independent Test**: `mixseek team "タスク" --config team.toml --timeout-per-team-seconds 600` のように実行し、CLI引数で指定したタイムアウト値が使用されることを確認する。

**Acceptance Scenarios**:

1. **Given** TOMLファイルと環境変数の両方に設定がある、**When** CLI引数 `--timeout-per-team-seconds 600` を指定する、**Then** CLI引数の値が優先される
2. **Given** CLI引数で設定を指定した、**When** トレース情報を確認する、**Then** 出所が "CLI引数" と表示される
3. **Given** CLI引数で無効な値を指定した、**When** アプリケーションを起動する、**Then** バリデーションエラーが発生し、明確なエラーメッセージが表示される

---

### User Story 3.5 - 開発者・運用者・ユーザがCLIで設定値を参照 (Priority: P2)

開発者・運用者・ユーザとして、CLIコマンドで現在の設定値、デフォルト値、設定の出所を参照し、設定の状態を確認できるようにしたい。

**Why this priority**: 設定の透明性を高め、デバッグやトラブルシューティングを容易にする。`--debug`フラグを使わずに設定を確認できることで、運用効率が向上する。

**Independent Test**: `mixseek config show`コマンドを実行し、すべての設定値とその出所が表示されることを確認する。`mixseek config list`コマンドですべての設定項目（デフォルト値含む）が一覧表示されることを確認する。

**Acceptance Scenarios**:

1. **Given** orchestrator.tomlとワークスペースが存在する、**When** `mixseek config show --config orchestrator.toml --workspace /path/to/workspace` を実行する、**Then** すべての現在の設定値が階層的なインデント形式で表示される
2. **Given** orchestrator.tomlとMIXSEEK_WORKSPACE環境変数が設定されている、**When** `mixseek config show --config orchestrator.toml` を実行する、**Then** 環境変数で指定されたワークスペースの設定値が表示される
3. **Given** アプリケーションが設定されている、**When** `mixseek config list` を実行する、**Then** すべての設定項目（必須/オプション、デフォルト値、型、説明）のスキーマ情報が一覧表示される
4. **Given** orchestrator.tomlとワークスペースが存在する、**When** `mixseek config show timeout_per_team_seconds --config orchestrator.toml --workspace /path/to/workspace` を実行する、**Then** 指定した設定項目の詳細（現在値、デフォルト値、出所、型）が表示される
5. **Given** orchestrator.toml（`[orchestrator]`セクション形式）が存在する、**When** `mixseek config show --config orchestrator.toml --workspace /path/to/workspace` を実行する、**Then** orchestrator.toml内のOrchestratorSettings設定値（timeout_per_team_seconds等）が階層的に表示される
6. **Given** orchestrator.tomlが参照するteam.toml/member.tomlが存在する、**When** `mixseek config show --config orchestrator.toml --workspace /path/to/workspace` を実行する、**Then** orchestrator設定に加えて、再帰的に読み込まれたteam/member設定も階層的なインデント形式で表示される
7. **Given** `--config` に orchestrator セクションを持たないファイルを指定した、**When** `mixseek config show --config invalid.toml --workspace /path/to/workspace` を実行する、**Then** バリデーションエラーが発生し、「指定されたファイルは orchestrator 設定ファイルではありません」というエラーメッセージが表示される
8. **Given** MIXSEEK_WORKSPACE環境変数が未設定で--workspaceも指定されていない、**When** `mixseek config show --config orchestrator.toml` を実行する、**Then** エラーが発生し、「Workspace path must be specified via --workspace or MIXSEEK_WORKSPACE env var」というエラーメッセージが表示される

---

### User Story 4 - 開発者・運用担当者が必須設定の未設定を検知 (Priority: P1)

開発者・運用担当者として、必須の設定が未設定の場合、開発・本番を問わずアプリケーション起動時に明確なエラーメッセージで通知され、誤った設定での起動を防ぎたい。

**Why this priority**: 原則1（明示性の原則）の中核。必須設定の未設定は開発・本番を問わず重大な問題であり、早期に検知する必要がある。

**Independent Test**: 必須設定を未設定の状態でアプリケーションを起動し、dev/prod環境を問わず起動失敗と明確なエラーメッセージが表示されることを確認する。

**Acceptance Scenarios**:

1. **Given** 本番環境（`prod`）で必須設定（例: `MIXSEEK_WORKSPACE`または`MIXSEEK_WORKSPACE_PATH`）が未設定、**When** アプリケーションを起動する、**Then** 起動が失敗し、「MIXSEEK_WORKSPACE または MIXSEEK_WORKSPACE_PATH の明示的な設定が必要です」というエラーメッセージが表示される
2. **Given** 開発環境（`dev`）で同じ必須設定が未設定、**When** アプリケーションを起動する、**Then** 同様に起動が失敗し、明確なエラーメッセージが表示される
3. **Given** 必須設定が欠けている、**When** エラーメッセージを確認する、**Then** どの環境変数またはTOMLキーを設定すべきかが明示されている
4. **Given** デフォルト値を持つオプション設定が未設定、**When** 開発・本番を問わず起動する、**Then** デフォルト値が使用され、起動が成功する
5. **Given** デフォルト値を持つオプション設定、**When** 開発・検証時に引数や環境変数で上書き指定する、**Then** 指定した値が優先される

---

### User Story 5 - 開発者・運用者・ユーザがTOMLファイルで設定を一元管理 (Priority: P2)

開発者・運用者・ユーザとして、プロジェクトの標準設定をTOMLファイルで管理し、バージョン管理システムでチーム内で共有したり、運用環境ごとにカスタマイズできるようにしたい。

**Why this priority**: チーム開発や運用環境での一貫性を保つための基本機能。設定ファイルを通じてチーム全体や運用者・ユーザが設定を共有・管理できる。

**Independent Test**: TOMLファイルに設定を記述し、環境変数を設定せずにアプリケーションを起動して、TOMLの設定が使用されることを確認する。運用者・ユーザが独自のTOMLファイルを作成し、それが正しく読み込まれることを確認する。

**Acceptance Scenarios**:

1. **Given** 開発者が `config.toml` に設定を記述している、**When** 環境変数が未設定の状態でアプリケーションを起動する、**Then** TOMLファイルの設定が使用される
2. **Given** 運用者・ユーザが独自の `custom.toml` を作成している、**When** `--config custom.toml` で起動する、**Then** カスタムTOMLファイルの設定が使用される
3. **Given** ネストした設定（例: `[leader] model = "..."`）がTOMLに記述されている、**When** 設定を読み込む、**Then** 正しく階層構造が解釈される
4. **Given** TOMLファイルが存在しない、**When** アプリケーションを起動する、**Then** エラーが発生せず、デフォルト値または環境変数が使用される
5. **Given** orchestrator.toml に `evaluator_config = "configs/custom-evaluator.toml"` が記述されている、**When** Orchestrator を起動する、**Then** 指定されたパスから Evaluator 設定が読み込まれ、デフォルトの `configs/evaluator.toml` ではなくカスタム設定が使用される
6. **Given** orchestrator.toml に `evaluator_config = "custom-eval.toml"`（相対パス）が記述されている、**When** `MIXSEEK_WORKSPACE=/workspace` で起動する、**Then** `/workspace/custom-eval.toml` として解決され、正しく読み込まれる
7. **Given** orchestrator.toml に `evaluator_config = "/absolute/path/evaluator.toml"`（絶対パス）が記述されている、**When** Orchestrator を起動する、**Then** 絶対パスがそのまま使用され、正しく読み込まれる
8. **Given** orchestrator.toml に `evaluator_config` が記述されておらず、`{workspace}/configs/evaluator.toml` も存在しない、**When** Orchestrator を起動する、**Then** デフォルト値で EvaluatorSettings が生成され、Evaluator が正常に初期化される（エラーにならない）

---

### User Story 6 - 開発者・運用者・ユーザが統一的な優先順位で設定を管理 (Priority: P1)

開発者・運用者・ユーザとして、すべての設定値が「CLI > 環境変数 > .env > TOML > デフォルト値」という一貫した優先順位で解決されることを理解し、設定の動作を予測可能にしたい。

**Why this priority**: 原則2（階層的フォールバック）の中核。優先順位が一貫していないと、設定の動作が予測不可能になる。すべてのユーザーが同じルールで設定を管理できる必要がある。

**Independent Test**: 同じ設定を複数のソース（CLI、ENV、TOML）で定義し、最も優先度が高いソースの値が採用されることを確認する。開発者・運用者・ユーザのいずれが設定を行っても同じ優先順位ルールが適用されることを確認する。

**Acceptance Scenarios**:

1. **Given** CLI引数、環境変数、TOMLファイルの3つで同じ設定が定義されている、**When** アプリケーションを起動する、**Then** CLI引数の値が採用される
2. **Given** 環境変数とTOMLファイルで同じ設定が定義されている（CLI引数なし）、**When** アプリケーションを起動する、**Then** 環境変数の値が採用される
3. **Given** すべてのソースで必須設定が未定義、**When** アプリケーションを起動する、**Then** 開発・本番を問わずエラーが発生する
4. **Given** すべてのソースでデフォルト値を持つオプション設定が未定義、**When** 開発・本番を問わず起動する、**Then** デフォルト値が使用され、起動が成功する

---

### User Story 7 - 開発者・運用者・ユーザがTOMLテンプレートを生成 (Priority: P3)

開発者・運用者・ユーザとして、設定項目のTOMLテンプレートファイルを生成し、必須設定を確認したり、オプション設定のデフォルト値を参照できるようにしたい。また、コンポーネント別（team、orchestrator、ui等）の階層構造を意識したテンプレートを生成できるようにしたい。

**Why this priority**: 新規ユーザーのオンボーディング支援、設定の発見性向上、移行作業の容易化。ドキュメントとしても機能する。

**Independent Test**: `mixseek config init`コマンドを実行し、すべての設定項目（必須/オプション、デフォルト値、型、説明）を含むTOMLテンプレートが生成されることを確認する。コンポーネント別のテンプレート生成も確認する。

**Acceptance Scenarios**:

1. **Given** workspace が指定されている、**When** `mixseek config init --workspace /path/to/workspace` を実行する、**Then** `workspace/configs/config.toml` テンプレートが生成され、すべての設定項目がコメント付きで記載される
2. **Given** Team設定が必要、**When** `mixseek config init --component team --workspace /path/to/workspace` を実行する、**Then** `workspace/configs/team.toml` テンプレートが生成され、Team設定（leader、memberを含む階層構造）が記載される
3. **Given** Orchestrator設定が必要、**When** `mixseek config init --component orchestrator --workspace /path/to/workspace` を実行する、**Then** `workspace/configs/orchestrator.toml` テンプレートが生成される
4. **Given** カスタム出力先が指定されている、**When** `mixseek config init --component orchestrator --output-path my-configs/orchestrator.toml --workspace /path/to/workspace` を実行する、**Then** `workspace/my-configs/orchestrator.toml` にテンプレートが生成される
5. **Given** 絶対パスが指定されている、**When** `mixseek config init --component orchestrator --output-path /tmp/orchestrator.toml` を実行する、**Then** `/tmp/orchestrator.toml` にテンプレートが生成される（workspace 不要）
6. **Given** 生成されたteam.tomlテンプレート、**When** ファイル内容を確認する、**Then** `[leader]`セクションと`[member]`セクションが階層構造で記載され、各設定項目にコメントと説明が含まれる
7. **Given** 生成されたテンプレート、**When** ファイル内容を確認する、**Then** 必須設定項目は `workspace = ""` のように値が空で記載され、オプション設定項目は `# timeout_per_team_seconds = 300` のようにコメントアウトされてデフォルト値が表示される
8. **Given** 既存の設定ファイルが存在する、**When** `mixseek config init --component orchestrator --workspace /path/to/workspace --force` を実行する、**Then** 既存ファイルを上書きしてテンプレートが生成される
9. **Given** workspace が指定されていない（かつ絶対パス指定もない）、**When** `mixseek config init --component orchestrator` を実行する、**Then** 「Workspace path must be specified via --workspace or MIXSEEK_WORKSPACE env var.」というエラーメッセージが表示される（Issue #175）

---

### Edge Cases

- **複数の.envファイルが存在する場合**: どの.envファイルが優先されるか？（想定: カレントディレクトリの `.env` を優先）
- **環境変数に不正な値が設定された場合**: バリデーションエラーが発生し、どのフィールドでエラーが起きたかが明示される
- **TOMLファイルの構文エラー**: アプリケーション起動時にTOML解析エラーが明確に表示され、エラー箇所（行番号）が示される
- **CLI引数とTOMLキー名の不一致**: CLI引数名（例: `--timeout`）がTOMLキー名（例: `timeout_seconds`）と異なる場合、適切にマッピングされる
- **ネストした設定の環境変数表現**: 環境変数 `MIXSEEK_LEADER__MODEL` が `leader.model` にマッピングされる（区切り文字: `__`）
- **設定値のリロード**: アプリケーション起動後に環境変数が変更された場合、リロードされない（再起動が必要）
- **MIXSEEK_WORKSPACEが相対パスで定義された場合**: 動作は未定義。ユーザーは絶対パスで定義する必要がある
- **TOMLファイル内の相対パス**: `config="agents/xxx.toml"`のような相対パスは`MIXSEEK_WORKSPACE`を基準として解決される。絶対パスが指定された場合はそのまま使用される
- **MIXSEEK_WORKSPACEが未設定でTOMLに相対パスが記述された場合**: 相対パス解決が失敗し、明確なエラーメッセージが表示される
- **`--config` に非orchestratorファイルを指定した場合**: `[orchestrator]` セクションが存在しないファイルを指定すると、バリデーションエラーが発生し、明確なエラーメッセージが表示される
- **`--config` で参照されるteam.tomlが存在しない場合**: orchestrator.tomlが参照するteam設定ファイルが見つからない場合、ファイルパスを含む明確なエラーメッセージが表示される
- **`--config` と `MIXSEEK_CONFIG_FILE` の両方が指定された場合**: `--config` CLI引数が優先される（優先順位: CLI > 環境変数の原則に従う）
- **設定ファイルの循環参照**: orchestrator.toml → team-a.toml → team-b.toml → team-a.toml のような循環参照が検出された場合、エラーメッセージに参照パス全体（例: "orchestrator.toml → team-a.toml → team-b.toml → team-a.toml"）を含めて表示し、処理を中止する
- **再帰的読み込みの最大深度超過**: 設定ファイルの参照チェーンが最大深度（10階層）を超えた場合、エラーメッセージに現在の深度と参照パスを含めて表示し、処理を中止する
- **`evaluator_config` が相対パスで `MIXSEEK_WORKSPACE` 未設定の場合**: 相対パス解決が失敗し、「MIXSEEK_WORKSPACE が未設定のため evaluator_config の相対パスを解決できません」という明確なエラーメッセージが表示される
- **`evaluator_config` で明示的に指定されたファイルが存在しない場合**: FileNotFoundError が発生し、指定されたパスを含む明確なエラーメッセージが表示される
- **`Evaluator.__init__` に `settings` を指定しない場合**: TypeError が発生する（`settings` は必須引数のため）
- **`orchestrator.toml` に `evaluator_config` が指定されておらず、デフォルトの `{workspace}/configs/evaluator.toml` も存在しない場合**: ConfigurationManager はデフォルト値で EvaluatorSettings を生成し、Evaluator はそれを使って初期化される（Article 9 準拠: 暗黙のフォールバックではなく、明示的なデフォルト値生成）

## Requirements

### Functional Requirements

- **FR-001**: システムは設定値を以下の優先順位で解決しなければならない: CLI引数 > 環境変数 > .envファイル > TOMLファイル > デフォルト値
- **FR-002**: システムはpydantic-settingsの `settings_customise_sources()` を使用して優先順位を制御しなければならない
- **FR-003**: システムは各設定値について、その出所（ソース名、ソースタイプ、タイムスタンプ）を記録しなければならない
- **FR-004**: 開発者はトレース情報にアクセスし、各設定値がどのソースから読み込まれたかを確認できなければならない
- **FR-005**: システムはCLI引数を読み込むカスタム設定ソース（`CLISource`）を提供しなければならない
- **FR-006**: システムは設定ソースをラップしてトレース情報を記録する `TracingSourceWrapper` を提供しなければならない
- **FR-007**: システムはデフォルト値を持つオプション設定について、環境（dev/staging/prod）を問わず同じデフォルト値を使用しなければならない
- **FR-008**: すべての環境（dev/staging/prod）において、必須設定が未設定の場合にバリデーションエラーを発生させなければならない
- **FR-009**: システムはデフォルト値を持つオプション設定が未設定の場合、スキーマで定義されたデフォルト値を使用しなければならない
- **FR-010**: システムは環境変数のプレフィックス（`MIXSEEK_`）を自動的に付与し、設定を読み込まなければならない
- **FR-011**: システムは`.env`ファイルから設定を読み込まなければならない
- **FR-012**: システムはTOMLファイルから設定を読み込まなければならない
- **FR-013**: システムはネストした設定（例: `leader.model`）を環境変数（例: `MIXSEEK_LEADER__MODEL`）で上書きできなければならない
- **FR-014**: システムはPydanticバリデーションを使用して、設定値の型と制約をチェックしなければならない
- **FR-015**: システムは不正な設定値（型違反、範囲外）に対して明確なエラーメッセージを表示しなければならない
- **FR-016**: システムは `ConfigurationManager` クラスを提供し、設定の読み込みとトレース情報の取得を統一的なインターフェースで行えなければならない
- **FR-017**: `ConfigurationManager` はデバッグ情報を出力する機能（`print_debug_info()`）を提供しなければならない
- **FR-018**: デバッグ情報には各設定値、その値、出所、タイムスタンプが含まれなければならない
- **FR-019**: システムは既存の設定スキーマ（`LeaderAgentSettings`, `MemberAgentSettings`, `EvaluatorSettings`, `OrchestratorSettings` 等）を `BaseSettings` ベースに移行しなければならない
- **FR-020**: 移行後の設定スキーマは既存TOML形式との互換性を維持し、Feature 027等で定義された既存のTOMLファイル（team.toml、orchestrator.toml等）が引き続き使用できなければならない
- **FR-021**: `ConfigurationManager` はすべての設定項目のデフォルト値を取得するメソッド（`get_all_defaults()`）を提供しなければならない
- **FR-022**: 開発者は現在の設定値とデフォルト値を比較し、どの設定がデフォルトから上書きされているかを確認できなければならない
- **FR-023**: システムは `mixseek config show` コマンドを提供し、すべての現在の設定値とその出所を表示しなければならない（対象: OrchestratorSettings, UISettings, LeaderAgentSettings, MemberAgentSettings, EvaluatorSettings, JudgmentSettings, PromptBuilderSettings, TeamSettings）
- **FR-024**: システムは `mixseek config show <KEY>` コマンドを提供し、指定した設定項目の詳細（現在値、デフォルト値、出所、タイムスタンプ）を表示しなければならない
- **FR-025**: システムは `mixseek config list` コマンドを提供し、すべての設定項目（必須/オプション、デフォルト値、型、説明）を一覧表示しなければならない
- **FR-027**: システムは `mixseek config init` コマンドを提供し、設定スキーマに基づいたTOMLテンプレートファイルを生成しなければならない
- **FR-028**: `mixseek config init` コマンドは `--component` オプションを受け付け、特定のコンポーネント（team, orchestrator, ui, evaluator等）用のテンプレートを生成できなければならない
- **FR-029**: 生成されるTOMLテンプレートには、各設定項目の型、デフォルト値、必須/オプション区分、説明がコメントとして記載されなければならない
- **FR-030**: team.toml用のテンプレートは、階層構造（[leader]と[member]セクション）を含み、各セクションの設定項目が適切に配置されなければならない
- **FR-031**: 必須設定項目はテンプレート内で `key = ""` のように値が空の状態で記載し、オプション設定項目は `# key = "default_value"` のようにコメントアウトしてデフォルト値を示すことで、両者を明確に区別しなければならない

#### Team設定統合

- **FR-032**: システムは `TeamSettings` クラスを提供し、Team全体の設定（team_id, team_name, max_concurrent_members, leader設定, 可変数のmember設定）を統合管理しなければならない
- **FR-033**: システムは `TeamTomlSource` を提供し、Feature 027で定義されたteam.toml形式（参照形式 `config="agents/xxx.toml"` を含む）を仕様準拠形式として読み込めなければならない。TOMLファイル内の相対パスは`MIXSEEK_WORKSPACE`を基準として解決されなければならない
- **FR-034**: `ConfigurationManager` は `load_team_settings()` メソッドを提供し、Team設定を参照解決付きで読み込めなければならない
- **FR-035**: 参照形式（`config="agents/xxx.toml"`）で指定された外部Member Agent設定ファイルは、自動的に読み込まれ、TeamSettings.membersに統合されなければならない。相対パスは`MIXSEEK_WORKSPACE`起点で解決されなければならない
- **FR-036**: 参照形式で読み込まれたMember Agent設定は、team.toml側で tool_name/tool_description を上書き可能でなければならない（Feature 027互換性）
- **FR-037**: TeamSettings.members は可変数（0～max_concurrent_members）のMember Agent設定を保持でき、Pydantic Settingsの型安全性を維持しなければならない

#### Orchestrator設定ファイル参照機能

- **FR-038**: システムは `mixseek config show` および `mixseek config list` コマンドの両方に `--config` オプションを提供し、指定されたorchestrator TOMLファイル（`[orchestrator]`セクション形式）から設定を読み込んで表示しなければならない
- **FR-039**: `--config` オプション使用時、システムは指定されたファイルに `[orchestrator]` セクションが存在することをバリデーションし、存在しない場合は明確なエラーメッセージを表示しなければならない
- **FR-040**: `--config` で指定されたorchestrator.tomlファイルが参照する team.toml および member.toml の設定を再帰的に読み込み、階層的なインデント表示（orchestrator → team → member の階層構造を視覚化）で表示しなければならない
- **FR-041**: `--config` と `--workspace` オプションを同時に指定した場合、相対パスは `--workspace` を基準に解決されなければならない
- **FR-042**: システムは設定ファイル読み込み時に循環参照を検出し、循環参照が発見された場合は参照パス全体を含む明確なエラーメッセージを表示して処理を中止しなければならない
- **FR-043**: システムは設定ファイルの再帰的読み込みに最大深度制限（10階層）を設け、制限を超えた場合は現在の深度と参照パスを含む明確なエラーメッセージを表示して処理を中止しなければならない

#### Evaluator設定参照機能

- **FR-044**: `OrchestratorSettings` は `evaluator_config` フィールド（オプション、文字列型）を提供し、orchestrator.toml内でEvaluator設定ファイルのパス（相対パスまたは絶対パス）を指定できなければならない
- **FR-045**: `evaluator_config` フィールドに相対パスが指定された場合、システムは `MIXSEEK_WORKSPACE` を基準として絶対パスに解決しなければならない
- **FR-046**: `Evaluator` クラスは `__init__(self, settings: EvaluatorSettings)` の形式で、`settings` 引数（`EvaluatorSettings` インスタンス、必須）のみを受け付けなければならない
- **FR-047**: `Evaluator.__init__()` は内部で `evaluator_settings_to_evaluation_config()` ヘルパー関数を使用して、`EvaluatorSettings` を `EvaluationConfig` に変換しなければならない
- **FR-048**: システムは `evaluator_config` で明示的に指定されたファイルが存在しない場合、ファイルパスを含む明確なエラーメッセージを表示しなければならない
- **FR-049**: システムは `evaluator_config` が未指定で、デフォルトの `{workspace}/configs/evaluator.toml` も存在しない場合、デフォルト値で `EvaluatorSettings` を生成しなければならない（Article 9 準拠: 明示的なデフォルト値使用）
- **FR-050**: `ConfigurationManager` は `get_evaluator_settings(evaluator_config)` メソッドを提供し、フォールバックロジック（明示的パス → デフォルトパス → デフォルト値）を共通化しなければならない
- **FR-051**: `get_evaluator_settings()` は、デフォルト値を使用する際に、Pydantic モデルの JSON 表現をログ出力しなければならない（透明性確保）
- **FR-052**: `EvaluationConfig.from_toml_file(workspace_path)` メソッドは後方互換性のために維持され、内部的には `ConfigurationManager.load_evaluation_settings()` を呼び出さなければならない（既存実装のまま）

### Key Entities

- **BaseSettings**: pydantic-settingsの基底クラス。すべての設定スキーマはこれを継承する
- **ConfigurationManager**: 設定の読み込みとトレース情報の管理を担当する薄いラッパークラス
- **CLISource**: CLI引数から設定を読み込むカスタム設定ソース
- **TracingSourceWrapper**: 既存の設定ソースをラップし、トレース情報を記録するクラス
- **SourceTrace**: 設定値のトレース情報を表すデータクラス（値、ソース名、ソースタイプ、フィールド名、タイムスタンプ）
- **LeaderAgentSettings**: Leader Agent用の設定スキーマ（BaseSettingsを継承）
- **MemberAgentSettings**: Member Agent用の設定スキーマ（BaseSettingsを継承）
- **EvaluatorSettings**: Evaluator用の設定スキーマ（BaseSettingsを継承）
- **OrchestratorSettings**: Orchestrator用の設定スキーマ（BaseSettingsを継承）
- **TeamSettings**: Team全体の設定スキーマ（team_id, team_name, leader設定, 可変数のmember設定を統合管理、BaseSettingsを継承）
- **TeamTomlSource**: Team設定専用のTOMLソース（参照形式の自動解決機能を提供、PydanticBaseSettingsSourceを継承）

## Success Criteria

### Measurable Outcomes

- **SC-001**: 開発者が環境変数で設定を上書きでき、アプリケーションの再ビルドなしに環境別のデプロイが可能になる
- **SC-002**: 開発者がデバッグモード（`--debug`）で起動し、すべての設定値の出所を3秒以内に確認できる
- **SC-003**: すべての環境（dev/staging/prod）で必須設定が未設定の場合、起動失敗と明確なエラーメッセージが100%表示される
- **SC-004**: すべての環境でデフォルト値を持つオプション設定が未設定の場合、デフォルト値で起動が100%成功する
- **SC-005**: 開発・検証時に引数や環境変数で設定を上書きでき、デフォルト値より優先される
- **SC-006**: CLI引数、環境変数、TOMLファイルの優先順位が一貫しており、開発者が設定の動作を100%予測できる
- **SC-007**: 既存のTOMLファイルが新しい設定システムで引き続き動作し、移行時の設定ファイル書き換えが不要である
- **SC-008**: プロジェクト憲法Article 9（Data Accuracy Mandate：データ精度義務）違反箇所（ハードコードされたデフォルト値）が現在の80箇所から10箇所以下に削減される
- **SC-009**: 設定関連のユニットテストカバレッジが100%に達する
- **SC-010**: 設定値のトレーサビリティにより、設定関連のデバッグ時間が平均50%削減される
- **SC-011**: すべてのモジュール（Leader, Member, Evaluator, Orchestrator, RoundController, UI, CLI）で統一的なConfiguration Managerが使用される
- **SC-012**: 開発者がすべてのデフォルト値を3秒以内に取得でき、現在値との差分を確認できる
- **SC-013**: 開発者・運用者・ユーザが `mixseek config show` コマンドで1秒以内にすべての設定値を確認できる
- **SC-014**: 開発者・運用者・ユーザが `mixseek config list` コマンドで利用可能なすべての設定項目を確認できる
- **SC-015**: 開発者・運用者・ユーザが `mixseek config init` コマンドで1秒以内にTOMLテンプレートを生成でき、必須設定項目が未コメント、オプション設定項目がコメントアウトされた状態で出力される
- **SC-016**: Feature 027定義のteam.tomlファイル（複雑な階層構造、参照形式を含む）がConfigurationManager経由で100%正確に読み込め、ユーザー側の修正作業が不要である
- **SC-017**: load_team_config()（レガシー）の全機能がload_team_settings()（新）で再現され、Agent実装が新システムに完全移行できる
- **SC-018**: TeamSettings.membersで可変数（0～max_concurrent_members）のMember Agent設定を型安全に管理でき、実行時エラーが0件になる
- **SC-019**: orchestrator.toml で `evaluator_config = "configs/custom-evaluator.toml"` のように指定し、カスタムパスから Evaluator 設定を読み込める
- **SC-020**: `Evaluator` クラスは `settings` 引数（`EvaluatorSettings` インスタンス、必須）のみを受け付け、内部で `EvaluationConfig` に変換する（責任の明確化）。`EvaluationConfig.from_toml_file()` は後方互換性のために維持される
- **SC-021**: Evaluator 設定の読み込みエラー（明示的に指定されたファイルの未存在、相対パス解決失敗等）は、すべてのケースで明確なエラーメッセージを表示する
- **SC-022**: 設定ファイルが存在しない場合（`evaluator_config` 未指定かつデフォルトファイルなし）でも、デフォルト値で Evaluator が初期化され、100%正常動作する

## Assumptions

- pydantic-settingsライブラリがプロジェクトに既にインストールされている、または追加できる
- TOML、環境変数、CLI引数は設定値として文字列、数値、真偽値、リストをサポートすれば十分である
- 設定ファイルの暗号化やシークレット管理は別の機構（K8s Secrets、AWS Secrets Manager等）で行われる
- 設定値のリロード（ホットリロード）は初期実装では不要で、アプリケーション再起動で対応する
- 環境変数のネスト区切り文字は `__`（アンダースコア2つ）を使用する
- TOMLファイルのパスはデフォルトで `config.toml`、環境変数 `MIXSEEK_CONFIG_FILE` で上書き可能とする
- `.env`ファイルはカレントディレクトリに配置される
- `MIXSEEK_WORKSPACE`環境変数は絶対パスで定義されなければならない。相対パスで定義された場合の動作は未定義とする
- TOMLファイル内で相対パスが記述されている場合（例: `config="agents/xxx.toml"`）、それらは`MIXSEEK_WORKSPACE`を基準ディレクトリとして解決される
- 本仕様における「後方互換性」「互換性維持」は、Feature 027等の仕様で定義された既存TOML形式・環境変数といった公式インターフェースのサポートを指す。Article 9に違反するレガシーコード実装の保持を意味しない

## Dependencies

- **pydantic** (>=2.12): pydantic-settingsの基盤
- **pydantic-settings** (>=2.12): BaseSettingsと標準設定ソース
- **tomllib** (Python 3.11+標準ライブラリ): TOMLファイルの読み込み
- **typer**: CLI引数の解析（mixseek-coreの既存CLIフレームワーク）
- 既存の設定スキーマ（`LeaderAgentConfig`, `EvaluationConfig` 等）

## Out of Scope

- 設定値の暗号化機能（別の機構で実現）
- 設定値のホットリロード（アプリケーション再起動で対応）
- GUIベースの設定エディタ
- 設定値の履歴管理やバージョニング
- K8s ConfigMapやAWS SSMとの直接統合（将来的な拡張として検討）
- 複雑な条件付き優先順位（例: 「環境がprodの場合のみENVを優先」）

## Non-Functional Requirements

- **NFR-001**: 設定の読み込み時間は100ms以内でなければならない
- **NFR-002**: トレース情報の記録によるメモリオーバーヘッドは1MB以下でなければならない
- **NFR-003**: バリデーションエラーメッセージは、どのフィールドでエラーが発生したか、期待される値の形式、実際の値を含まなければならない
- **NFR-004**: コードは既存のmixseek-coreのコーディング規約（ruff, mypy）に準拠しなければならない
- **NFR-005**: すべての公開API（`ConfigurationManager`, カスタムソース）にはGoogle-style docstringが含まれなければならない
- **NFR-006**: 既存の設定スキーマからの移行は段階的に行い、破壊的変更を最小限に抑えなければならない
