# Quickstart: GitHub Actions CI Pipeline

**Feature**: 102-ci-github-actions
**Date**: 2025-11-19

このガイドでは、GitHub Actions CIパイプラインを実装し、動作を検証する手順を説明します。

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Implementation Steps](#implementation-steps)
3. [Branch Protection Configuration](#branch-protection-configuration)
4. [Verification](#verification)
5. [Troubleshooting](#troubleshooting)

---

## Prerequisites

以下の条件が満たされていることを確認してください:

- [ ] GitHub リポジトリへの管理者権限(Branch Protection設定のため)
- [ ] プロジェクトルートに `.python-version` ファイルが存在する
- [ ] `pyproject.toml` に ruff, mypy, pytest, Sphinx の設定が含まれている
- [ ] `uv.lock` ファイルが生成されている(`uv sync` 実行済み)
- [ ] ローカル環境でコード品質チェックが通ること:
  ```bash
  ruff check --fix . && ruff format . && mypy .
  ```

---

## Implementation Steps

### Step 1: Create Workflow Directory

```bash
# リポジトリルートで実行
mkdir -p .github/workflows
```

### Step 2: Create CI Workflow File

`.github/workflows/ci.yml` を以下の内容で作成します:

```yaml
name: CI Pipeline

on:
  pull_request:
    branches:
      - develop
      - main

concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true

jobs:
  ruff:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - name: Checkout code
        uses: actions/checkout@v5

      - name: Set up uv
        uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true

      - name: Install dependencies
        run: uv sync --locked --group dev

      - name: Run ruff check
        run: uv run ruff check .

      - name: Run ruff format check
        run: uv run ruff format --check .

  mypy:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - name: Checkout code
        uses: actions/checkout@v5

      - name: Set up uv
        uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true

      - name: Install dependencies
        run: uv sync --locked --group dev

      - name: Run mypy
        run: uv run mypy src tests

  pytest:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - name: Checkout code
        uses: actions/checkout@v5

      - name: Set up uv
        uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true

      - name: Install dependencies
        run: uv sync --locked --group dev

      - name: Run tests (excluding E2E tests)
        run: uv run pytest -m "not e2e"

  docs:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - name: Checkout code
        uses: actions/checkout@v5

      - name: Set up uv
        uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true

      - name: Install dependencies
        run: uv sync --locked --group docs

      - name: Build documentation
        run: uv run sphinx-build -W --keep-going -b html docs docs/_build/html
```

### Step 3: Commit and Push Workflow

```bash
git add .github/workflows/ci.yml
git commit -m "feat(ci): Add GitHub Actions CI pipeline with ruff, mypy, pytest, and docs

- Implement automated code quality checks (ruff, mypy)
- Add automated testing with pytest (excluding E2E tests)
- Add Sphinx documentation build verification
- Configure uv caching for fast dependency installation
- Set 15-minute timeout and parallel job execution
- Support develop and main branch PRs

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
git push origin 102-ci-github-actions
```

---

## Branch Protection Configuration

CIワークフローを実装した後、GitHub リポジトリ設定でBranch Protection Rulesを設定します。

### Step 1: Navigate to Branch Protection Settings

1. GitHubリポジトリページを開く
2. **Settings** タブをクリック
3. 左サイドバーの **Branches** をクリック
4. **Branch protection rules** セクションの **Add rule** ボタンをクリック

### Step 2: Configure `develop` Branch Protection

1. **Branch name pattern** に `develop` と入力
2. 以下のオプションを有効化:
   - ✅ **Require a pull request before merging**
     - ✅ Require approvals: `1` (推奨)
     - ✅ Dismiss stale pull request approvals when new commits are pushed (オプション)
   - ✅ **Require status checks to pass before merging**
     - ✅ Require branches to be up to date before merging (推奨)
     - Required status checks(検索ボックスで以下を追加):
       - `ruff`
       - `mypy`
       - `pytest`
       - `docs`
   - ✅ **Require conversation resolution before merging** (推奨)
   - ❌ **Require signed commits** (オプション)
   - ❌ **Require linear history** (オプション)
3. **Create** ボタンをクリック

### Step 3: Configure `main` Branch Protection

1. **Add rule** ボタンをクリック
2. **Branch name pattern** に `main` と入力
3. Step 2と同じオプションを設定
4. **Create** ボタンをクリック

**注意**: Required status checksは、CIが一度実行されてステータスチェックがGitHub APIに登録された後にのみ選択可能になります。初回のPRを作成してCIを実行した後に設定してください。

---

## Verification

CIパイプラインが正しく動作していることを検証します。

### Test 1: Trigger CI on PR Creation

1. テストブランチを作成:
   ```bash
   git checkout -b test-ci-pipeline
   ```

2. 小さな変更を追加(例: README.mdの更新):
   ```bash
   echo "# CI Test" >> README.md
   git add README.md
   git commit -m "test: Verify CI pipeline execution"
   git push origin test-ci-pipeline
   ```

3. GitHub UIでdevelopブランチへのPRを作成

4. **期待される結果**:
   - PRページに4つのステータスチェックが表示される:
     - ✅ ruff
     - ✅ mypy
     - ✅ pytest
     - ✅ docs
   - すべてのチェックが緑色のチェックマークで成功

### Test 2: Verify Parallel Execution

1. PR作成後、**Actions** タブを開く
2. 最新のワークフロー実行をクリック
3. **期待される結果**:
   - 4つのジョブ(ruff, mypy, pytest, docs)が並列実行されている
   - 各ジョブの開始時刻がほぼ同時
   - 総実行時間が5分以内(キャッシュ有効時)

### Test 3: Verify Cache Effectiveness

1. PRに新しいコミットをプッシュ(`uv.lock`は変更しない):
   ```bash
   echo "# CI Test 2" >> README.md
   git add README.md
   git commit -m "test: Verify cache effectiveness"
   git push origin test-ci-pipeline
   ```

2. **期待される結果**:
   - "Set up uv" ステップのログに "Cache restored" メッセージが表示される
   - "Install dependencies" ステップの実行時間が短い(数秒程度)

### Test 4: Verify Failure Detection

1. 意図的にruffエラーを追加:
   ```python
   # src/test_ci.py (新規作成)
   def test_function(  ):  # 余分なスペース → ruffエラー
       pass
   ```

2. コミットしてプッシュ:
   ```bash
   git add src/test_ci.py
   git commit -m "test: Verify ruff failure detection"
   git push origin test-ci-pipeline
   ```

3. **期待される結果**:
   - `ruff` ジョブが失敗(赤色のX)
   - 他のジョブ(mypy, pytest, docs)は成功(独立性の確認)
   - PRのマージボタンが無効化される

4. クリーンアップ:
   ```bash
   git rm src/test_ci.py
   git commit -m "test: Clean up test file"
   git push origin test-ci-pipeline
   ```

### Test 5: Verify Concurrency Control

1. PRに最初のコミットをプッシュ:
   ```bash
   echo "# CI Test 3" >> README.md
   git add README.md
   git commit -m "test: First commit"
   git push origin test-ci-pipeline
   ```

2. CIが実行開始したら、すぐに2つ目のコミットをプッシュ:
   ```bash
   echo "# CI Test 4" >> README.md
   git add README.md
   git commit -m "test: Second commit"
   git push origin test-ci-pipeline
   ```

3. **期待される結果**:
   - **Actions** タブで古いワークフロー実行が自動的にキャンセルされる
   - 最新のコミットに対してのみCIが実行される

### Test 6: Verify Branch Protection

1. すべてのチェックが成功しているPRで、**Merge pull request** ボタンを確認
2. **期待される結果**:
   - マージボタンが有効化されている
   - "All checks have passed" メッセージが表示される

3. 1つでもチェックが失敗している場合:
   - マージボタンが無効化される
   - "Some checks were not successful" メッセージが表示される

---

## Troubleshooting

### Issue: CI not triggered on PR creation

**Symptoms**: PRを作成してもCIが実行されない

**Possible Causes**:
- ワークフローファイルのパスが間違っている(`.github/workflows/ci.yml` であることを確認)
- YAMLシンタックスエラー(GitHub Actionsタブでエラーメッセージを確認)
- ターゲットブランチがdevelopまたはmain以外

**Solution**:
1. `.github/workflows/ci.yml` が正しいパスに存在するか確認
2. YAML構文をオンラインバリデータで検証
3. PRのベースブランチがdevelopまたはmainであることを確認

---

### Issue: Python version mismatch

**Symptoms**: "Set up Python" ステップでエラー

**Possible Causes**:
- `.python-version` ファイルが存在しない
- `.python-version` の形式が不正(例: `3.13.7` ではなく `python-3.13.7`)

**Solution**:
1. `.python-version` ファイルが存在することを確認:
   ```bash
   cat .python-version
   ```
2. 内容が `3.13.7` のようなバージョン番号のみであることを確認(プレフィックスなし)

---

### Issue: Cache not working

**Symptoms**: 毎回依存関係が再インストールされ、実行時間が長い

**Possible Causes**:
- `uv.lock` ファイルが頻繁に変更されている
- キャッシュが7日間アクセスされず自動削除された

**Solution**:
1. `uv.lock` ファイルが不必要に変更されていないか確認
2. キャッシュの有効期限(7日)を考慮し、定期的にPRを作成してキャッシュを更新

---

### Issue: Documentation build fails

**Symptoms**: `docs` ジョブが失敗し、Sphinxエラーが表示される

**Possible Causes**:
- ドキュメントに構文エラーまたは壊れたリンクがある
- Sphinx拡張の依存関係が不足している

**Solution**:
1. ローカルでドキュメントビルドを実行し、エラーを確認:
   ```bash
   uv run sphinx-build -W --keep-going -b html docs docs/_build/html
   ```
2. エラーメッセージを基にドキュメントを修正
3. `pyproject.toml` の `[dependency-groups.docs]` にすべての必要な依存関係が含まれていることを確認

---

### Issue: Job timeout

**Symptoms**: ジョブが15分でタイムアウトし、失敗する

**Possible Causes**:
- テストの実行時間が長すぎる
- 依存関係のインストールに時間がかかりすぎる(キャッシュ無効時)

**Solution**:
1. テストの実行時間を短縮する(重いテストをマークして除外)
2. キャッシュが有効であることを確認
3. タイムアウト時間の延長が必要な場合は、仕様書を確認してチームと協議

---

## Next Steps

CIパイプラインの動作確認が完了したら:

1. **tasks.md生成**: `/speckit.tasks` コマンドを実行してタスクリストを生成
2. **実装開始**: `tasks.md` に従って実装を進める
3. **継続的改善**: CIパイプラインのパフォーマンスを監視し、必要に応じて最適化

---

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [uv GitHub Actions Guide](https://docs.astral.sh/uv/guides/integration/github/)
- [Branch Protection Rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [Feature Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Research Document](./research.md)
