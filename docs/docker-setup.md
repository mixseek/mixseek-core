# Docker ビルドユーザー設定ガイド

このドキュメントでは、MixSeek-Core の Docker イメージビルド時のユーザー設定方法を説明します。

## 概要

Docker イメージをビルドする際、コンテナ内で使用するユーザーアカウント（ユーザー名、UID、GID）をカスタマイズできます。デフォルトでは、macOS の GID 競合を回避し、クロスプラットフォームの一貫性を確保するために安全な値が使用されます。

## デフォルト設定

設定不要でビルドできます：

```bash
make -C dockerfiles/dev build
```

デフォルト値：
- ユーザー名: `mixseek_core`
- UID: `1000`
- GID: `1000`

これらの値は macOS、Linux、Windows で競合なく動作します。

## 環境変数

以下の環境変数で設定をカスタマイズできます：

| 変数 | デフォルト | 説明 |
|------|----------|------|
| MIXSEEK_USERNAME | mixseek_core | コンテナユーザー名 |
| MIXSEEK_UID | 1000 | コンテナユーザー ID |
| MIXSEEK_GID | 1000 | コンテナグループ ID |

## 使用例

### デフォルトでビルド（推奨）

```bash
cd /path/to/mixseek_core
make -C dockerfiles/dev build
```

結果: コンテナユーザー `mixseek_core` (UID 1000, GID 1000)

### カスタムユーザー設定

```bash
export MIXSEEK_USERNAME=myuser
export MIXSEEK_UID=5000
export MIXSEEK_GID=5000
make -C dockerfiles/dev build
```

結果: コンテナユーザー `myuser` (UID 5000, GID 5000)

使用タイミング:
- NFS マウント権限の一致
- 企業の LDAP/Active Directory 統合
- 特定のセキュリティ要件

### ビルド前の設定確認

```bash
make -C dockerfiles/dev validate-build-args
```

出力例:
```
✅ ビルド引数が設定されました
   MIXSEEK_USERNAME: mixseek_core
   MIXSEEK_UID: 1000
   MIXSEEK_GID: 1000
```

### 1回限りの上書き

```bash
MIXSEEK_USERNAME=tempuser MIXSEEK_UID=3000 MIXSEEK_GID=3000 make -C dockerfiles/dev build
```

### CI環境専用イメージ

MixSeek-Coreには、GitHub Actions CIと同じ環境をローカルで再現できるCI専用の最小構成Dockerfileが用意されています：

```bash
# CI専用イメージのビルド
make -C dockerfiles/ci build

# または直接Docker buildを使用
docker build -f dockerfiles/ci/Dockerfile -t mixseek-core/ci:latest .
```

CI環境の特徴：
- Python 3.13.9を明示的に固定（再現性確保）
- Node.js、AI toolsなど開発環境専用の要素を排除
- セキュリティ重視（最小パッケージ、setuidビット除去）
- 高速ビルド（不要なレイヤーなし）
- **GitHub Actions CI環境と完全に一致**

#### ローカルでのCI検証

PR作成前にローカルでGitHub Actions CIと同じチェックを実行：

```bash
# コードリンティング
make -C dockerfiles/ci lint

# フォーマットチェック
make -C dockerfiles/ci format-check

# 型チェック
make -C dockerfiles/ci type-check

# テスト実行（E2E除く）
make -C dockerfiles/ci test-fast

# すべてのチェック実行
make -C dockerfiles/ci check
```

詳細は`dockerfiles/ci/README.md`を参照してください。

### CI/CD パイプラインでの使用

**GitHub Actions:**

現在のCI設定（`.github/workflows/ci.yml`）では、以下のワークフローでCI Dockerコンテナを使用しています：

```yaml
jobs:
  build-ci-image:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v6
        with:
          context: .
          file: dockerfiles/ci/Dockerfile
          tags: mixseek-core/ci:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

  ruff:
    needs: build-ci-image
    steps:
      - run: make -C dockerfiles/ci lint
      - run: make -C dockerfiles/ci format-check

  mypy:
    needs: build-ci-image
    steps:
      - run: make -C dockerfiles/ci type-check

  pytest:
    needs: build-ci-image
    steps:
      - run: make -C dockerfiles/ci test-fast
```

**GitLab CI:**
```yaml
build:
  variables:
    MIXSEEK_USERNAME: ci_user
    MIXSEEK_UID: 1100
    MIXSEEK_GID: 1100
  script:
    - make -C dockerfiles/ci build
```

**Jenkins:**
```groovy
environment {
    MIXSEEK_USERNAME = 'ci_user'
    MIXSEEK_UID = '1100'
    MIXSEEK_GID = '1100'
}
stages {
    stage('Build') {
        steps {
            sh 'make -C dockerfiles/ci build'
        }
    }
}
```

## 推奨値ガイドライン

### ユーザー名形式（Docker が検証）

- ✅ 推奨: `mixseek_core`, `_app`, `user-123`, `myservice`
- ❌ 避けるべき: `123user`（数字で開始）, `User`（大文字）, `user@host`（特殊文字）, `my user`（スペース）

### UID/GID 範囲（Docker が検証）

- ✅ 推奨: 1000-65533（一般ユーザー範囲）
- ⚠️ 非推奨: 0（root）, 1-999（システムアカウント）, 65534（nobody）
- ❌ 避けるべき: 非数値、負の数

**注意**: バリデーションは Makefile では実行されません。無効な値は Docker ビルド時にエラーとして報告されます。

## トラブルシューティング

### エラー: "GID '20' already exists"

**原因**: macOS で古い設定がログインユーザーの GID（20）を使用していた。

**解決策**:
```bash
unset MIXSEEK_USERNAME MIXSEEK_UID MIXSEEK_GID
make -C dockerfiles/dev build
```

### エラー: "groupadd: invalid group ID 'abc'" または "useradd: invalid user ID 'xyz'"

**原因**: UID または GID に非数値を設定した。

**解決策**:
```bash
# 現在の値を確認
echo "UID: $MIXSEEK_UID, GID: $MIXSEEK_GID"

# 正しい数値を設定
export MIXSEEK_UID=1000
export MIXSEEK_GID=1000
make -C dockerfiles/dev build
```

### エラー: "useradd: invalid user name"

**原因**: ユーザー名に無効な文字が含まれているか、数字で始まっている。

**解決策**:
```bash
# 有効な例:
export MIXSEEK_USERNAME="user123"   # ✅
export MIXSEEK_USERNAME="_app"      # ✅
export MIXSEEK_USERNAME="my-service" # ✅

make -C dockerfiles/dev build
```

### 問題: コンテナでのファイル権限エラー

**症状**: コンテナによって作成されたファイルがホスト上で間違った所有権を持つ。

**原因**: ホストとコンテナ間の UID/GID ミスマッチ。

**解決策**:
```bash
# オプション 1: デフォルトを使用（ほとんどの場合に推奨）
make -C dockerfiles/dev build

# オプション 2: ホストの UID/GID に一致させる（ボリュームマウント用）
export MIXSEEK_UID=$(id -u)
export MIXSEEK_GID=$(id -g)
make -C dockerfiles/dev build
```

**注意**: macOS では、GID が 20 の場合、オプション 2 は失敗する可能性があります。代わりにオプション 1 を使用してください。

## プラットフォーム固有のメモ

### macOS

- **デフォルト GID**: 20（staff グループ）- Linux コンテナと競合
- **解決策**: システムはデフォルトで GID 1000（全プラットフォームで安全）
- **ボリュームマウント**: Docker Desktop が自動的に UID/GID マッピングを処理
- **推奨**: デフォルト設定を使用

### Linux

- **デフォルト UID/GID**: 1000（最初のユーザー）
- **整合性**: デフォルトが Linux の慣習と一致
- **ボリュームマウント**: 正しい権限のために正確な UID/GID 一致が必要
- **推奨**: デフォルトを使用するか、ホストの UID/GID に一致させる

### Windows（Docker Desktop）

- **UID/GID**: Windows ホストでは適用不可
- **コンテナの動作**: コンテナを Linux システムとして扱う
- **推奨**: デフォルト設定を使用

### CI/CD 環境

- **要件**: エージェント間で一貫したビルド
- **推奨**: パイプライン設定で明示的な値を設定
- **典型的な値**: UID/GID 1100-1200（1000 との競合を回避）

## 高度な設定

### 永続的な設定（プロファイル設定）

シェルプロファイル（`~/.bashrc`、`~/.zshrc`、または `~/.bash_profile`）に追加:

```bash
# MixSeek-Core Docker ビルド設定
export MIXSEEK_USERNAME=myuser
export MIXSEEK_UID=2000
export MIXSEEK_GID=2000
```

プロファイルをリロード:
```bash
source ~/.bashrc  # または ~/.zshrc
```

### プロジェクト固有の設定（.env ファイル）

プロジェクトルートに `.env` ファイルを作成:

```bash
# .env
MIXSEEK_USERNAME=project_user
MIXSEEK_UID=3000
MIXSEEK_GID=3000
```

ビルド前にロード:
```bash
source .env
make -C dockerfiles/dev build
```

### 複数環境のサポート

環境固有のファイルを作成:

```bash
# .env.dev
MIXSEEK_USERNAME=dev_user
MIXSEEK_UID=1000
MIXSEEK_GID=1000

# .env.prod
MIXSEEK_USERNAME=prod_user
MIXSEEK_UID=2000
MIXSEEK_GID=2000
```

必要に応じて使用:
```bash
# 開発環境
source .env.dev
make -C dockerfiles/dev build

# 本番環境
source .env.prod
make -C dockerfiles/prod build
```

## ベストプラクティス

1. **可能な限りデフォルトを使用**: デフォルト値（mixseek_core、1000、1000）は全プラットフォームで動作
2. **ビルド前に設定を確認**: `make validate-build-args` を実行して使用される値を確認
3. **カスタム値を文書化**: デフォルト以外の値を使用する場合、プロジェクト内で理由を文書化
4. **CI/CD の一貫性**: パイプライン設定ファイルで明示的な値を設定
5. **システム範囲を回避**: 1000 未満の UID/GID を使用しない（システムアカウント用に予約）
6. **クロスプラットフォームでテスト**: カスタム値を使用する場合、macOS と Linux の両方でテスト
7. **エラーは早期に検出**: 無効な値がある場合、Docker ビルドの早い段階でエラーが発生するため、エラーメッセージを注意深く読む

## 関連ドキュメント

- **技術詳細**: 詳細は `/specs/004-modify-docker-user/` を参照
- **実装計画**: `../specs/004-modify-docker-user/plan.md`
- **データモデル**: `../specs/004-modify-docker-user/data-model.md`

## ヘルプ

問題が発生した場合:

1. 設定値を確認: `make validate-build-args`
2. Docker ビルドエラーメッセージを注意深く確認（具体的なガイダンスが含まれています）
3. Docker ログを確認: `docker logs <container-name>`
