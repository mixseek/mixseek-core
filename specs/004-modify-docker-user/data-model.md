# データモデル: Docker ビルドユーザー設定

**Feature**: 003-mixseek-core-modify-docker-user
**日付**: 2025-10-17

## 概要

このドキュメントでは、環境変数、検証ルール、状態遷移を含む、Docker ビルドユーザー設定のデータモデルを定義します。

## エンティティ

### ビルド環境設定

ユーザー/グループ作成のための Docker イメージビルドパラメータを制御する環境変数のセットを表します。

**属性**:

| 属性 | 型 | デフォルト | 必須 | 説明 |
|------|------|-----------|------|------|
| MIXSEEK_USERNAME | string | "mixseek_core" | Yes | コンテナユーザー名 |
| MIXSEEK_UID | integer | 1000 | Yes | コンテナユーザー ID |
| MIXSEEK_GID | integer | 1000 | Yes | コンテナグループ ID |

**制約**:

なし - すべてのバリデーションは Docker ビルド時に実行されます。無効な値（非数値の UID/GID、無効なユーザー名形式、既存のグループとの競合など）は Docker 実行時エラーとして報告されます。

**ソース**: ユーザーまたは CI/CD システムによって設定される環境変数

**ライフサイクル**:
1. Make 呼び出し時に環境から読み取り
2. 未設定の場合はデフォルトを適用（`?=` パターン）
3. `--build-arg` として Docker ビルドに渡す
4. Dockerfile の RUN コマンド（groupadd/useradd）で使用
5. 無効な値がある場合は Docker ビルド時にエラーが発生

### コンテナユーザー ID

Docker コンテナ内に作成されるユーザーアカウントを表します。

**属性**:

| 属性 | 型 | ソース | 説明 |
|------|------|--------|------|
| username | string | MIXSEEK_USERNAME | Linux ユーザー名 |
| uid | integer | MIXSEEK_UID | ユーザー ID（数値） |
| gid | integer | MIXSEEK_GID | プライマリグループ ID（数値） |
| home_dir | string | `/home/{username}` | ユーザーホームディレクトリパス |
| shell | string | `/bin/bash` | デフォルトログインシェル |

**関係性**:
- 作成元: ビルド環境設定
- 所有: コンテナファイルとプロセス
- メンバー: プライマリグループ（GID）および潜在的にセカンダリグループ

**状態遷移**:

```
[環境変数]
    ↓ (make validate-build-args で値を表示)
[ビルド設定]
    ↓ (docker build --build-arg)
[Docker ビルドコンテキスト]
    ↓ (RUN groupadd/useradd - ここでバリデーション)
[コンテナユーザー ID]
    ↓ (コンテナランタイム)
[アクティブプロセス所有者]
```

## バリデーション戦略

**重要な設計決定**: この機能は Makefile レベルでのバリデーションを実装しません。すべてのバリデーションは Docker ビルド時に実行され、エラーは Docker の groupadd/useradd コマンドによって報告されます。

### ビルド前の値表示（Makefile）

`make validate-build-args` は検証を行わず、設定された値を表示するのみです：

```makefile
define validate_build_args
    @echo "✅ ビルド引数が設定されました"
    @echo "   MIXSEEK_USERNAME: $(MIXSEEK_USERNAME)"
    @echo "   MIXSEEK_UID: $(MIXSEEK_UID)"
    @echo "   MIXSEEK_GID: $(MIXSEEK_GID)"
endef
```

### ビルド時のバリデーション（Docker）

すべてのバリデーションは Docker によって実行されます：

```dockerfile
# Docker が自動的にバリデーションを行う
RUN groupadd -g ${MIXSEEK_GID} ${MIXSEEK_USERNAME} && \
    useradd -m -u ${MIXSEEK_UID} -g ${MIXSEEK_GID} -s /bin/bash ${MIXSEEK_USERNAME}
```

### エラーハンドリングマトリックス

すべてのエラーは Docker ビルド時に検出されます：

| エラー条件 | 検出ポイント | アクション | エラーメッセージ |
|-----------|-------------|-----------|----------------|
| 空のユーザー名 | Docker ビルド | Exit 1 | Docker エラー（groupadd/useradd 失敗） |
| 空の UID/GID | Docker ビルド | Exit 1 | Docker エラー（groupadd/useradd 失敗） |
| 非数値の UID/GID | Docker ビルド | Exit 1 | Docker エラー（groupadd/useradd 失敗） |
| 無効なユーザー名形式 | Docker ビルド | Exit 1 | Docker エラー（groupadd/useradd 失敗） |
| GID が既に存在 | Docker ビルド | Exit 4 | "groupadd: GID 'X' already exists" |
| UID が既に存在 | Docker ビルド | Exit 4 | "useradd: UID 'X' already exists" |

## データフロー

### シナリオ 1: デフォルト値（環境変数なし）

```
ユーザー: make build
  ↓
Makefile: MIXSEEK_USERNAME ?= mixseek_core（デフォルト適用）
Makefile: MIXSEEK_UID ?= 1000（デフォルト適用）
Makefile: MIXSEEK_GID ?= 1000（デフォルト適用）
  ↓
Docker: groupadd -g 1000 mixseek_core（バリデーションと実行）
Docker: useradd -m -u 1000 -g 1000 -s /bin/bash mixseek_core
  ↓
コンテナ: ユーザー mixseek_core (1000:1000) 作成完了
```

### シナリオ 2: 環境変数経由のカスタム値

```
ユーザー: export MIXSEEK_USERNAME=custom_user
ユーザー: export MIXSEEK_UID=5000
ユーザー: export MIXSEEK_GID=5000
ユーザー: make build
  ↓
Makefile: MIXSEEK_USERNAME ?= custom_user（環境変数値を使用）
Makefile: MIXSEEK_UID ?= 5000（環境変数値を使用）
Makefile: MIXSEEK_GID ?= 5000（環境変数値を使用）
  ↓
Docker: groupadd -g 5000 custom_user（バリデーションと実行）
Docker: useradd -m -u 5000 -g 5000 -s /bin/bash custom_user
  ↓
コンテナ: ユーザー custom_user (5000:5000) 作成完了
```

### シナリオ 3: 無効な値（Docker ビルドエラー）

```
ユーザー: export MIXSEEK_UID=abc
ユーザー: make build
  ↓
Makefile: MIXSEEK_UID ?= abc（環境変数値を使用）
  ↓
Docker: groupadd -g abc mixseek_core
  ↓
Docker エラー: "groupadd: invalid group ID 'abc'"
終了: 1（Docker ビルド失敗）
```

## プラットフォーム考慮事項

### macOS 固有の動作

**問題**: macOS のデフォルトユーザーは GID 20（staff グループ）を持つ
- `id -g` を実行すると 20 が返される
- Docker で GID 20 を使用すると「GID '20' already exists」エラーが発生
- Linux では多くのシステムプロセスが GID 20 を使用（dialout など）

**解決策**: 代わりに GID 1000 をデフォルトにする
- GID 1000 はシステム範囲（0-999）より上
- Linux コンテナで競合なし
- macOS ユーザーは権限問題を見ない（Docker がマッピングを処理）

### Linux 固有の動作

**標準**: 最初のユーザーは通常 UID/GID 1000 を持つ
- デフォルトが Linux の慣習と一致
- Linux 開発者に驚きなし
- ほとんどのベースイメージと整合

### CI/CD 環境

**典型的な要件**:
- エージェント間で一貫したビルド
- ホストユーザーへの依存なし
- 予測可能なファイル所有権

**解決策**: CI/CD が明示的な値を設定
```bash
export MIXSEEK_USERNAME=ci_user
export MIXSEEK_UID=1100
export MIXSEEK_GID=1100
make build
```

## 実装参照

- **Makefile パターン**: research.md § Make 変数デフォルト値
- **UID/GID 範囲**: research.md § UID/GID 範囲とクロスプラットフォーム互換性
- **Docker ARG 使用法**: research.md § Docker Build ARG ベストプラクティス

**注**: 検証正規表現は実装されません。すべてのバリデーションは Docker によって実行されます。
