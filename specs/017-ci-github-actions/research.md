# Research: GitHub Actions CI Pipeline

**Feature**: 102-ci-github-actions
**Date**: 2025-11-19
**Status**: Completed

## Overview

このドキュメントは、GitHub Actions CI パイプライン実装に必要な技術調査結果をまとめています。

## Research Topics

### 1. uv Integration with GitHub Actions

**Decision**: GitHub Actions公式ガイドに従った `astral-sh/setup-uv@v6` アクションを使用

**Rationale**:
- uvの公式ドキュメント(https://docs.astral.sh/uv/guides/integration/github/)が推奨する標準的な統合方法
- キャッシング機能が組み込まれており、依存関係インストール時間を大幅に削減
- uv自身がPythonをインストール可能なため、`actions/setup-python`は不要(冗長性排除)
- `.python-version` ファイルから自動的にPythonバージョンを検出し、uv経由でインストール

**Alternatives Considered**:
- **手動uvインストール**: スクリプトでuvをダウンロードしてインストールする方法
  - 却下理由: 公式アクションの方が保守性が高く、キャッシング機能も統合済み
- **pip/pipenvの使用**: 従来のPythonパッケージ管理ツール
  - 却下理由: プロジェクトがuvを標準としているため、一貫性を保つべき
- **actions/setup-python併用**: setup-pythonでPythonをインストール後、uvを使用
  - 却下理由: uvが独自にPythonをインストールできるため冗長。公式ドキュメントでも不要と明記

**Implementation Details**:
```yaml
- name: Set up uv
  uses: astral-sh/setup-uv@v6
  with:
    enable-cache: true
```

**Note**: `astral-sh/setup-uv@v6` は `.python-version` ファイルを自動検出し、必要なPythonバージョンをインストールします。

### 2. Python Version Management

**Decision**: `astral-sh/setup-uv@v6` の自動検出機能を利用(`.python-version` ファイルから自動読み取り)

**Rationale**:
- Article 9(Data Accuracy Mandate)に準拠: ハードコードを回避し、明示的なソースから取得
- プロジェクトルートの `.python-version` ファイルが唯一の真実の情報源(Single Source of Truth)
- CI環境と開発環境の完全な同期を保証
- `astral-sh/setup-uv@v6` が `.python-version` を自動検出するため、追加の設定不要

**Alternatives Considered**:
- **YAMLファイルにPythonバージョンをハードコード**: `python-version: "3.13.7"` を直接記述
  - 却下理由: `.python-version` 更新時にCIファイルも手動更新が必要となり、同期ミスのリスク
- **GitHub Actionsのmatrix戦略で複数バージョンテスト**: Python 3.13, 3.14など複数バージョンでテスト
  - 却下理由: 仕様書の「将来対応」に該当(Clarifications Session 2025-11-19)
- **actions/setup-pythonで明示的にバージョン指定**: `.python-version`を読み取ってsetup-pythonに渡す
  - 却下理由: uvが独自にPythonをインストールするため冗長

**Implementation Details**:
```yaml
- name: Set up uv
  uses: astral-sh/setup-uv@v6
  with:
    enable-cache: true
# .python-version ファイルが自動的に検出され、Pythonがインストールされる
```

### 3. Parallel Job Execution Strategy

**Decision**: 単一ワークフローファイル内で4つの独立したジョブとして並列実行

**Rationale**:
- NFR-002に準拠: 各チェック(ruff, mypy, pytest, docs)は独立して実行され、1つの失敗が他に影響しない
- GitHub Actionsの並列実行機能により、CIパイプライン全体の実行時間を短縮
- 各ジョブが個別のステータスチェックとして表示され、PR画面での視認性が向上

**Alternatives Considered**:
- **複数ワークフローファイルに分割**: 各チェックを独立した `.github/workflows/ruff.yml` などに分割
  - 却下理由: 仕様書のClarifications(2025-11-19)で「単一ワークフローファイル内で複数ジョブとして実行」と明示
- **シーケンシャル実行**: ruff → mypy → pytest → docsの順に実行
  - 却下理由: 並列実行より実行時間が長くなり、NFR-003(5分以内)を達成できない可能性

**Implementation Details**:
```yaml
jobs:
  ruff:
    runs-on: ubuntu-latest
    steps: [...]

  mypy:
    runs-on: ubuntu-latest
    steps: [...]

  pytest:
    runs-on: ubuntu-latest
    steps: [...]

  docs:
    runs-on: ubuntu-latest
    steps: [...]
```

### 4. E2E Tests Exclusion

**Decision**: pytestマーカー `@pytest.mark.e2e` を使用してE2Eテストを除外

**Rationale**:
- FR-006に準拠: API_KEYを必要とするテストは現時点で除外
- プロジェクトに既存の `e2e` マーカーを活用(pyproject.tomlに定義済み)
- E2Eテストは実際のAPIキー(ANTHROPIC_API_KEY, OPENAI_API_KEY)を必要とするため、CI環境では実行しない
- `pytest -m "not e2e"` コマンドで明示的に除外可能

**Alternatives Considered**:
- **新規マーカー `requires_api_key` を追加**: 専用マーカーでAPI_KEYテストを管理
  - 却下理由: 既存の `e2e` マーカーで同じ目的を達成可能。新規マーカー追加は冗長
- **環境変数の有無で動的スキップ**: `@pytest.mark.skipif(not os.getenv("API_KEY"))` を各テストに追加
  - 却下理由: CI環境で意図せずAPI_KEYが設定されている場合、除外されず失敗する可能性
- **テストファイルを分離**: `tests/e2e/` ディレクトリにE2Eテストを配置し、パス指定で除外
  - 却下理由: マーカーベースの方が柔軟性が高く、既存の実装(tests/evaluator/e2e/)と一貫性がある

**Implementation Details**:
```yaml
- name: Run tests (excluding E2E tests)
  run: uv run pytest -m "not e2e"
```

**Note**: `e2e` マーカーは既に `pyproject.toml` に定義されており、追加設定は不要。

### 5. Dependency Caching Strategy

**Decision**: uv公式のキャッシング機能を使用(v6の自動最適化)

**Rationale**:
- `astral-sh/setup-uv@v6` アクションの `enable-cache: true` オプションにより自動的にキャッシュが有効化
- `uv.lock` ファイルのハッシュ値を自動検出し、キャッシュキーとして使用
- 依存関係変更時のみキャッシュが無効化され、NFR-001に準拠(インストール時間最小化)
- `uv sync --locked` により、ロックファイルと完全一致する依存関係のみをインストール

**Alternatives Considered**:
- **actions/cache アクションで手動キャッシング**: `.venv/` ディレクトリを直接キャッシュ
  - 却下理由: uv公式アクションの組み込みキャッシュの方がuvの内部動作に最適化されている
- **キャッシュを使用しない**: 毎回依存関係を再インストール
  - 却下理由: NFR-003(5分以内)の目標を達成できない可能性

**Implementation Details**:
```yaml
- name: Set up uv
  uses: astral-sh/setup-uv@v6
  with:
    enable-cache: true

- name: Install dependencies
  run: uv sync --locked --group dev
```

### 6. PR Target Branch Filtering

**Decision**: GitHub Actionsの `on.pull_request.branches` フィルタを使用してdevelopとmainブランチのみを対象

**Rationale**:
- FR-001に準拠: developまたはmainブランチへのPR作成時にのみCIをトリガー
- Clarifications(2025-11-19)で「developとmainの2つに限定」と明示
- 不要なCI実行を防ぎ、リソース使用を最適化

**Alternatives Considered**:
- **すべてのブランチへのPRでCI実行**: `on: [pull_request]` でフィルタなし
  - 却下理由: 仕様書で明示的に「developとmainの2つに限定」と記載
- **ワークフロー内でif条件による分岐**: `if: github.base_ref == 'develop' || github.base_ref == 'main'`
  - 却下理由: `on.pull_request.branches` フィルタの方が宣言的で可読性が高い

**Implementation Details**:
```yaml
on:
  pull_request:
    branches:
      - develop
      - main
```

### 7. CI Timeout Configuration

**Decision**: ジョブレベルで `timeout-minutes: 15` を設定

**Rationale**:
- NFR-005に準拠: CIジョブの最大実行時間は15分
- Clarifications(2025-11-18)で「15分」と明示
- タイムアウト後は自動的に失敗として扱い、無限ループやハングアップを防止

**Alternatives Considered**:
- **ワークフローレベルでのタイムアウト設定**: すべてのジョブ合計で15分
  - 却下理由: 並列実行される各ジョブが独立して15分以内に完了すべき
- **タイムアウト設定なし**: GitHub Actionsのデフォルト(6時間)に依存
  - 却下理由: 仕様書で明示的に15分と指定されている

**Implementation Details**:
```yaml
jobs:
  ruff:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps: [...]
```

### 8. Branch Protection Rules

**Decision**: GitHub Branch Protection Rulesを使用してマージポリシーを強制

**Rationale**:
- FR-013に準拠: すべての必須チェック成功までマージを禁止
- GitHub UIまたはAPIで設定される外部設定であり、CIワークフローファイルには含まれない
- 4つのステータスチェック(ruff, mypy, pytest, docs)すべてがrequiredとして設定される

**Alternatives Considered**:
- **CIワークフロー内でマージ制御**: マージコマンドを実行するステップを追加
  - 却下理由: GitHubの標準的なBranch Protection機能を使用する方が安全で保守性が高い

**Implementation Details**:
GitHub リポジトリ設定での手動設定:
1. Settings → Branches → Branch protection rules
2. `develop` と `main` に対してルール作成
3. "Require status checks to pass before merging" を有効化
4. Required checks: `ruff`, `mypy`, `pytest`, `docs` を選択

**Note**: この設定はCIワークフローファイルの実装後に手動で実施する必要がある。quickstart.mdに手順を記載する。

### 9. Documentation Build Verification

**Decision**: Sphinxの `sphinx-build` コマンドを使用してドキュメントをビルド

**Rationale**:
- FR-007に準拠: Sphinxを使用してドキュメントをビルド
- プロジェクトに既存のSphinx設定(`docs/conf.py`)を使用
- ビルドエラー(構文エラー、壊れたリンク)を早期に検出

**Alternatives Considered**:
- **make html**: Makefileを使用したビルド
  - 却下理由: `uv run sphinx-build` の方がuvの依存関係管理と統合されている
- **ドキュメントビルドをスキップ**: ドキュメント検証なし
  - 却下理由: User Story 3でドキュメントビルド検証が明示的に要求されている

**Implementation Details**:
```yaml
- name: Build documentation
  run: uv run sphinx-build -W --keep-going -b html docs docs/_build/html
```

**Options**:
- `-W`: 警告をエラーとして扱い、ビルドを失敗させる
- `--keep-going`: エラー後も可能な限りビルドを継続し、すべてのエラーを表示
- `-b html`: HTML形式でビルド

### 10. Concurrency Control

**Decision**: `concurrency` キーを使用して、同一PRに対する古いCIジョブを自動キャンセル

**Rationale**:
- FR-012に準拠: PRが更新された際、実行中の古いCIジョブをキャンセルし、最新のコミットに対してのみCIを実行
- リソースの無駄遣いを防止し、CI実行キューの混雑を軽減
- SC-004に準拠: 古いCIジョブが自動的にキャンセルされる

**Alternatives Considered**:
- **手動キャンセル**: ユーザーがGitHub UIで古いジョブを手動キャンセル
  - 却下理由: 自動化により開発者の負担を削減
- **並列実行を許可**: 同一PRの複数コミットに対してCI並列実行
  - 却下理由: 最終結果に関係ない古いコミットのCI実行は無駄

**Implementation Details**:
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true
```

## Summary

すべての技術調査項目について、仕様書の要件とconstitution.mdの原則に基づいた決定を行いました。主な技術選択:

- **uv統合**: GitHub Actions公式ガイドの `astral-sh/setup-uv@v6` アクション
- **Pythonバージョン**: `.python-version` から自動検出(uvの組み込み機能、`actions/setup-python` 不要)
- **並列実行**: 単一ワークフロー内で4つの独立ジョブ
- **テスト除外**: pytestマーカー `@pytest.mark.e2e` (既存マーカーを活用)
- **キャッシング**: uv公式のキャッシング機能(v6の自動最適化)
- **依存関係インストール**: `uv sync --locked` でロックファイルと完全一致
- **ブランチフィルタ**: develop/mainのみ対象
- **タイムアウト**: ジョブレベルで15分
- **マージ制御**: GitHub Branch Protection Rules
- **ドキュメントビルド**: `sphinx-build` コマンド
- **同時実行制御**: `concurrency` キーで古いジョブを自動キャンセル
- **アクションバージョン**: 最新版を使用(`actions/checkout@v5`, `astral-sh/setup-uv@v6`)

これらの技術決定により、NFR-003(5分以内の実行時間)、NFR-005(15分の最大実行時間)、およびすべての機能要件を満たすCIパイプラインを実装可能です。
