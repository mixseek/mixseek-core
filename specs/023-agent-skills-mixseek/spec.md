# Feature Specification: MixSeek Agent Skills - ワークスペース管理

**Feature Branch**: `023-agent-skills-mixseek`
**Created**: 2026-01-21
**Status**: Draft
**Input**: User description: "draft/spec.mdについて仕様を定義してください"

## Clarifications

### Session 2026-01-21

- Q: スキル配置ディレクトリの構造は？ → A: `.skills/`配下に`mixseek-workspace-init/`、`mixseek-team-config/`等のディレクトリ名を使用
- Q: SKILL.mdフロントマターのオプションフィールドは？ → A: `name`と`description`のみ（必須フィールドのみ）を使用
- Q: メインスキル（スキル一覧）は作成するか？ → A: 作成しない。各スキルは独立して使用
- Q: Agent Skills仕様への準拠はどこで明記するか？ → A: FR-001で必須参照（/specification）と推奨参照（/what-are-skills）を明記、skills-ref検証も要件に追加
- Q: モデル一覧がAPI経由で取得できない場合は？ → A: `docs/data/valid-models.csv` などから取得

## 概要

外部コーディングエージェント（Claude Code、Codex、Gemini CLI など）が、自然言語でMixSeek-Coreのワークスペースを管理できるようにするAgent Skillsを作成する。

Agent Skills (https://agentskills.io/) は、AIエージェントに新しい機能と専門知識を提供するためのオープンで軽量なフォーマット。`SKILL.md`という標準Markdownファイルで定義され、手続き知識と組織固有のコンテキストをオンデマンドで提供する。

### スキルディレクトリ構造

Agent Skills仕様（agentskills.io/specification）に準拠し、以下のディレクトリ構造を採用する：

```
mixseek-core/
└── .skills/
    ├── mixseek-workspace-init/
    │   └── SKILL.md
    ├── mixseek-team-config/
    │   └── SKILL.md
    ├── mixseek-orchestrator-config/
    │   └── SKILL.md
    ├── mixseek-evaluator-config/
    │   └── SKILL.md
    ├── mixseek-config-validate/
    │   └── SKILL.md
    └── mixseek-model-list/
        └── SKILL.md
```

各ディレクトリ名は、対応するSKILL.mdの`name`フィールドと一致する（小文字英数字とハイフンのみ）。メインスキル（スキル一覧）は作成せず、各スキルは独立して使用される。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - ワークスペース初期化 (Priority: P1)

開発者として、自然言語で「mixseekのワークスペースを作成して」と依頼し、必要なディレクトリ構造と初期設定を自動生成したい。

**Why this priority**: ワークスペースの初期化はすべての機能の前提条件であり、最初に動作する必要がある基盤機能。

**Independent Test**: 空のディレクトリで「ワークスペースを初期化して」と依頼し、必要な`configs/`、`logs/`、`templates/`ディレクトリが作成されることを確認できる。

**Acceptance Scenarios**:

1. **Given** 空のディレクトリがある状態で、**When** ユーザーが「mixseekのワークスペースを作成して」と依頼した、**Then** `configs/agents/`、`configs/evaluators/`、`configs/judgment/`、`logs/`、`templates/`ディレクトリが作成される
2. **Given** ワークスペースパスが指定されていない状態で、**When** ユーザーがワークスペース初期化を依頼した、**Then** システムはユーザーにパスの確認を求める
3. **Given** ワークスペースが初期化された状態で、**When** 環境変数MIXSEEK_WORKSPACEが未設定の場合、**Then** 設定方法の案内が表示される

---

### User Story 2 - チーム設定生成 (Priority: P1)

開発者として、「Web検索と分析ができるチームを作って」のような自然言語でチーム設定を生成し、有効なTOML設定ファイルを取得したい。

**Why this priority**: チーム設定はMixSeekの中核機能であり、ユーザーが最も頻繁に使用する機能。

**Independent Test**: 「Web検索エージェントを持つチームを作成して」と依頼し、有効なteam.tomlとmember agent設定ファイルが生成されることを確認できる。

**Acceptance Scenarios**:

1. **Given** 初期化済みワークスペースがある状態で、**When** ユーザーが「Web検索と分析ができるチームを作って」と依頼した、**Then** Leader Agentとweb_search、plain タイプのMember Agentを含むTOML設定が生成される
2. **Given** チーム設定生成時に、**When** ユーザーがモデルを指定しなかった、**Then** システムはデフォルトモデル（Leader: gemini-2.5-pro, Member: gemini-2.5-flash）の使用確認を求める
3. **Given** 生成されたTOML設定で、**When** `mixseek team`コマンドを実行した、**Then** エラーなく実行できる

---

### User Story 3 - オーケストレーター設定生成 (Priority: P2)

開発者として、複数チームを並列実行して競合させるオーケストレーター設定を自然言語で生成したい。

**Why this priority**: オーケストレーターは高度な機能であり、基本的なチーム機能が動作した後に利用される。

**Independent Test**: 「2つのチームで競合させる設定を作って」と依頼し、orchestrator.tomlが生成されることを確認できる。

**Acceptance Scenarios**:

1. **Given** 複数のチーム設定ファイルが存在する状態で、**When** ユーザーが「3つのチームで競合させるオーケストレーターを設定」と依頼した、**Then** 3つのチームを参照するorchestrator.tomlが生成される
2. **Given** オーケストレーター設定生成時に、**When** 参照するチーム設定ファイルが存在しない、**Then** エラーメッセージと共に新規チーム作成を提案する

---

### User Story 4 - 評価設定生成 (Priority: P2)

開発者として、Submissionを評価するための評価基準と判定ロジックの設定を自然言語で生成したい。

**Why this priority**: 評価設定はオーケストレーターと連携する機能であり、チーム設定の次に重要。

**Independent Test**: 「正確性を重視した評価設定を作って」と依頼し、evaluator.tomlとjudgment.tomlが生成されることを確認できる。

**Acceptance Scenarios**:

1. **Given** 初期化済みワークスペースがある状態で、**When** ユーザーが「デフォルトの評価設定を作成」と依頼した、**Then** ClarityCoherence、Coverage、Relevanceの3つの評価基準を含むevaluator.tomlが生成される
2. **Given** 評価設定生成時に、**When** カスタム基準が指定された、**Then** 指定された基準を反映した設定が生成される

---

### User Story 5 - 設定検証 (Priority: P2)

開発者として、生成または手動編集した設定ファイルがMixSeekスキーマに準拠しているか検証したい。

**Why this priority**: 設定の検証は設定生成後に行われる補助機能であり、エラー防止に重要。

**Independent Test**: 「team.tomlを検証して」と依頼し、TOML構文エラーや必須フィールド欠落が報告されることを確認できる。

**Acceptance Scenarios**:

1. **Given** 有効なTOML設定ファイルがある状態で、**When** ユーザーが「この設定を検証して」と依頼した、**Then** 「検証成功」と表示される
2. **Given** 必須フィールドが欠落した設定ファイルがある状態で、**When** ユーザーが検証を依頼した、**Then** 欠落フィールドと修正方法が明示される
3. **Given** TOML構文エラーがある設定ファイルで、**When** 検証を実行した、**Then** エラー箇所と正しい構文例が表示される

---

### User Story 6 - モデル一覧取得 (Priority: P3)

開発者として、利用可能なLLMモデルの一覧を取得し、用途に適したモデルを選択したい。

**Why this priority**: モデル選択は他のスキルから参照される補助機能。

**Independent Test**: 「今使えるモデルを教えて」と依頼し、プロバイダー別のモデル一覧が表示されることを確認できる。

**Acceptance Scenarios**:

1. **Given** 環境変数（GOOGLE_API_KEY、ANTHROPIC_API_KEY、OPENAI_API_KEY）が設定されている状態で、**When** ユーザーが「使えるモデル一覧を教えて」と依頼した、**Then** Google Gemini、Anthropic Claude、OpenAIのモデルがカテゴリ別に表示される
2. **Given** 特定の環境変数（例：OPENAI_API_KEY）が未設定の場合、**When** モデル一覧を取得した、**Then** 設定されているプロバイダーのモデルと、未設定プロバイダーの警告が表示される

---

### Edge Cases

- ワークスペースディレクトリに書き込み権限がない場合、明確なエラーメッセージを表示する
- 既存の設定ファイルを上書きしようとした場合、確認を求める
- TOMLファイルに予約語と衝突する文字列が含まれる場合、適切にエスケープする
- ネットワーク接続がない状態でモデル一覧を取得しようとした場合、既知のモデルリストを提供する
- 循環参照のあるチーム設定を検出し、警告する

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: すべてのスキルはAgent Skills仕様に準拠しなければならない
  - **必須参照**: https://agentskills.io/specification （フロントマター形式、フィールド制約）
  - **推奨参照**: https://agentskills.io/what-are-skills （Progressive Disclosure、ディレクトリ構造）
  - 準拠要件：
    - YAMLフロントマター + Markdownボディ形式
    - 必須フィールド: `name`（小文字英数字とハイフンのみ、1-64文字）、`description`（1-1024文字）
    - ディレクトリ名は`name`フィールドと一致すること
    - オプションフィールド（`license`、`compatibility`、`metadata`、`allowed-tools`）は使用しない
  - 検証: `skills-ref validate <path>` で検証可能であること
- **FR-002**: workspace-initスキルは、`configs/agents/`、`configs/evaluators/`、`configs/judgment/`、`logs/`、`templates/`ディレクトリを作成できなければならない
- **FR-003**: team-configスキルは、Leader AgentとMember Agentを含む有効なTOML設定を生成できなければならない
- **FR-004**: team-configスキルは、web_search、plain、code_execution、web_fetch、customの5つのMember Agentタイプをサポートしなければならない
- **FR-005**: orchestrator-configスキルは、複数チームを参照するオーケストレーター設定を生成できなければならない
- **FR-006**: evaluator-configスキルは、評価基準と重み付けを含む評価設定を生成できなければならない
- **FR-007**: config-validateスキルは、TOML構文とMixSeekスキーマの検証を行えなければならない
- **FR-008**: model-listスキルは、Google Gemini、Anthropic Claude、OpenAIの各プロバイダーから利用可能なモデル一覧を取得できなければならない
  - API経由で取得できない場合は、 `docs/data/valid-models.csv` などから取得する
- **FR-009**: すべてのスキルは自然言語入力を受け付けなければならない
- **FR-010**: 生成される設定ファイルは`<provider>:<model-name>`形式のモデル指定をサポートしなければならない
- **FR-011**: すべてのスキルは環境変数参照を推奨し、ハードコードされた認証情報を含めてはならない
- **FR-012**: 各スキルの`description`フィールドは、スキルの機能と使用タイミングを明確に記述しなければならない（タスク識別用キーワードを含む）

### Key Entities

- **Skill**: Agent Skillsフォーマットで定義されたスキル。YAMLフロントマター（`name`と`description`のみ）とMarkdownボディで構成される
- **Team設定**: Leader AgentとMember Agentの構成を定義するTOML設定ファイル
- **Member Agent**: web_search、plain、code_execution、web_fetch、customのいずれかのタイプを持つエージェント設定
- **Orchestrator設定**: 複数チームの並列実行と評価を管理する設定ファイル
- **Evaluator設定**: 評価基準、重み付け、LLM設定を含む評価設定ファイル
- **Judgment設定**: ラウンド継続判定のロジックを定義する設定ファイル

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: ユーザーは自然言語で「ワークスペースを初期化して」と依頼し、必要なディレクトリ構造を生成できる
- **SC-002**: ユーザーは自然言語でチーム構成を説明し、有効なTOML設定ファイルを取得できる
- **SC-003**: 生成されたすべての設定ファイルは、`mixseek team`または`mixseek exec`コマンドでエラーなく実行できる
- **SC-004**: 設定検証スキルは、TOML構文エラーを100%検出し、明確なエラーメッセージを提供する
- **SC-005**: モデル一覧取得は、APIキーが設定されているすべてのプロバイダーからモデル情報を取得できる
- **SC-006**: すべてのスキルは、Claude Code、Codex、Gemini CLIの少なくとも2つのエージェントで動作確認される
- **SC-007**: ユーザーがモデルを指定しない場合、デフォルトモデルの提案と確認フローが提供される

## Assumptions

- AIコーディングエージェント（Claude Code、Codex、Gemini CLI等）がSKILL.md形式を読み取り、手順に従って実行できる
- ユーザーはbashコマンドとPythonスクリプトを実行できる環境を持っている
- MixSeek-Coreパッケージがインストールされているか、TOML設定を手動で作成して利用する
- 各LLMプロバイダーのAPIキーは環境変数で提供される（GOOGLE_API_KEY、ANTHROPIC_API_KEY、OPENAI_API_KEY）
- デフォルトモデルとしてGoogle Gemini（gemini-2.5-pro、gemini-2.5-flash）を使用する
