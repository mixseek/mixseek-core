# クイックスタート: Docker ビルドユーザー設定

**Feature**: 003-mixseek-core-modify-docker-user
**日付**: 2025-10-17

## 概要

このガイドでは、カスタムユーザーアカウントでの Docker イメージビルドの設定方法を説明し、macOS の GID 競合を解決し、クロスプラットフォームの一貫性を確保します。

## 問題の説明

macOS で Docker イメージをビルドすると、次のエラーが発生する場合があります:

```
groupadd: GID '20' already exists
ERROR: failed to solve: process "/bin/sh -c groupadd -g ${MIXSEEK_GID} ..." did not complete successfully: exit code: 4
```

これは、ビルドシステムがログインユーザーの GID（macOS では 20 = staff グループ）を使用しており、コンテナ内の既存グループと競合するためです。

## クイック解決策

**デフォルトの動作（設定不要）**:

```bash
make -C dockerfiles/dev build
```

システムは安全なデフォルト値を使用します:
- ユーザー名: `mixseek_core`
- UID: `1000`
- GID: `1000`

これらの値は macOS、Linux、Windows で競合なく動作します。

## 使用例

### 例 1: デフォルトでビルド（推奨）

環境変数を設定せずにビルドコマンドを実行するだけです:

```bash
# プロジェクトルートに移動
cd /path/to/mixseek_core

# 開発イメージをビルド
make -C dockerfiles/dev build

# 結果: コンテナユーザー mixseek_core (UID 1000, GID 1000)
```

**使用タイミング**: ほとんどの開発および CI/CD シナリオ。

---

### 例 2: カスタムユーザー設定

環境変数を設定してコンテナユーザーをカスタマイズ:

```bash
# カスタム値を設定
export MIXSEEK_USERNAME=myuser
export MIXSEEK_UID=5000
export MIXSEEK_GID=5000

# カスタム設定でビルド
make -C dockerfiles/dev build

# 結果: コンテナユーザー myuser (UID 5000, GID 5000)
```

**使用タイミング**:
- NFS マウント権限の一致
- 企業の LDAP/Active Directory 統合
- 特定のセキュリティ要件

---

### 例 3: ビルド前の設定検証

フルビルドを実行せずに使用される値を確認:

```bash
# デフォルト値の場合
make -C dockerfiles/dev validate-build-args

# 出力:
# ✅ Build arguments validated
#    MIXSEEK_USERNAME: mixseek_core
#    MIXSEEK_UID: 1000
#    MIXSEEK_GID: 1000

# カスタム値の場合
export MIXSEEK_USERNAME=custom_user
export MIXSEEK_UID=2000
export MIXSEEK_GID=2000
make -C dockerfiles/dev validate-build-args

# 出力:
# ✅ Build arguments validated
#    MIXSEEK_USERNAME: custom_user
#    MIXSEEK_UID: 2000
#    MIXSEEK_GID: 2000
```

**使用タイミング**: 設定の問題のデバッグ、長時間のビルド前の設定確認。

---

### 例 4: 1回限りの上書き（export なし）

シェル環境に影響を与えずに単一のビルドのための変数を設定:

```bash
MIXSEEK_USERNAME=tempuser MIXSEEK_UID=3000 MIXSEEK_GID=3000 make -C dockerfiles/dev build
```

**使用タイミング**: 異なる設定のテスト、一時的なビルド。

---

### 例 5: CI/CD 設定

CI/CD パイプライン設定での使用:

**GitHub Actions**:
```yaml
- name: Build Docker Image
  env:
    MIXSEEK_USERNAME: ci_user
    MIXSEEK_UID: 1100
    MIXSEEK_GID: 1100
  run: make -C dockerfiles/ci build
```

**GitLab CI**:
```yaml
build:
  variables:
    MIXSEEK_USERNAME: ci_user
    MIXSEEK_UID: 1100
    MIXSEEK_GID: 1100
  script:
    - make -C dockerfiles/ci build
```

**Jenkins**:
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

**使用タイミング**: CI/CD エージェント間で一貫したビルドを確保。

---

## 設定リファレンス

### 環境変数

| 変数 | デフォルト | 説明 | 推奨値 |
|------|----------|------|------|
| MIXSEEK_USERNAME | `mixseek_core` | コンテナユーザー名 | 小文字で始まる英数字、アンダースコア、ハイフン |
| MIXSEEK_UID | `1000` | コンテナユーザー ID | 1000-65533（一般ユーザー範囲） |
| MIXSEEK_GID | `1000` | コンテナグループ ID | 1000-65533（一般グループ範囲） |

**注**: バリデーションは Makefile では実行されません。無効な値は Docker ビルド時にエラーとして報告されます。

### 推奨値ガイドライン

**ユーザー名形式**（Docker が検証）:
- ✅ 推奨: `mixseek_core`, `_app`, `user-123`, `myservice`
- ❌ 避けるべき: `123user`（数字で開始）, `User`（大文字）, `user@host`（特殊文字）, `my user`（スペース）

**UID/GID 範囲**（Docker が検証）:
- ✅ 推奨: 1000-65533（一般ユーザー範囲）
- ⚠️ 非推奨: 0（root）, 1-999（システムアカウント）, 65534（nobody）
- ❌ 避けるべき: 非数値、負の数

## トラブルシューティング

### エラー: "GID '20' already exists"

**原因**: macOS で古い設定がログインユーザーの GID（20）を使用していた。

**解決策**:
```bash
# 古い変数エクスポートがあれば削除
unset MIXSEEK_USERNAME MIXSEEK_UID MIXSEEK_GID

# デフォルトでビルド（GID 1000 を使用）
make -C dockerfiles/dev build
```

---

### エラー: "groupadd: invalid group ID 'abc'" または "useradd: invalid user ID 'xyz'"

**原因**: UID または GID に非数値を設定した。

**解決策**:
```bash
# 現在の値を確認
echo "UID: $MIXSEEK_UID, GID: $MIXSEEK_GID"

# 正しい数値を設定
export MIXSEEK_UID=1000
export MIXSEEK_GID=1000

# 再ビルド
make -C dockerfiles/dev build
```

---

### エラー: "useradd: invalid user name" または類似のユーザー名エラー

**原因**: ユーザー名に無効な文字が含まれているか、数字で始まっている。

**解決策**:
```bash
# 無効な例（Docker がエラーを返す）:
# export MIXSEEK_USERNAME="123user"  # 数字で開始
# export MIXSEEK_USERNAME="User"     # 大文字を含む
# export MIXSEEK_USERNAME="user@app" # 特殊文字を含む

# 有効な例:
export MIXSEEK_USERNAME="user123"   # ✅
export MIXSEEK_USERNAME="_app"      # ✅
export MIXSEEK_USERNAME="my-service" # ✅

# 再ビルド
make -C dockerfiles/dev build
```

---

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

---

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

---

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

---

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

---

## ベストプラクティス

1. **可能な限りデフォルトを使用**: デフォルト値（mixseek_core、1000、1000）は全プラットフォームで動作
2. **ビルド前に設定を確認**: `make validate-build-args` を実行して使用される値を確認
3. **カスタム値を文書化**: デフォルト以外の値を使用する場合、プロジェクト内で理由を文書化
4. **CI/CD の一貫性**: パイプライン設定ファイルで明示的な値を設定
5. **システム範囲を回避**: 1000 未満の UID/GID を使用しない（システムアカウント用に予約）
6. **クロスプラットフォームでテスト**: カスタム値を使用する場合、macOS と Linux の両方でテスト
7. **エラーは早期に検出**: 無効な値がある場合、Docker ビルドの早い段階でエラーが発生するため、エラーメッセージを注意深く読む

## 関連ドキュメント

- **技術詳細**: バリデーション戦略とデータフローについては [data-model.md](./data-model.md) を参照
- **調査背景**: Make パターンと UID/GID 調査については [research.md](./research.md) を参照
- **実装計画**: 完全な技術コンテキストについては [plan.md](./plan.md) を参照

## ヘルプ

ここで対応されていない問題が発生した場合:

1. 設定値を確認: `make validate-build-args`
2. Docker ビルドエラーメッセージを注意深く確認（具体的なガイダンスが含まれています）
3. [data-model.md](./data-model.md) § エラーハンドリングマトリックスを参照
4. Docker ログを確認: `docker logs <container-name>`
