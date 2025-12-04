# 調査: Docker ビルドユーザー設定

このドキュメントは、Docker ビルドユーザー設定を実装するための調査結果と決定事項を提供します。Makefile 変数パターン、Docker ARG ベストプラクティス、UID/GID クロスプラットフォーム互換性をカバーしています。

**重要な注意**: この機能は、Makefile または Dockerfile レベルでのバリデーションを実装しません。すべてのバリデーションは Docker の groupadd/useradd コマンドによって実行されます。このドキュメントは、推奨値とベストプラクティスのガイドラインを提供します。

## 1. Make 変数デフォルト値

### 決定事項

`VAR ?= default` パターンを使用します（シンプルで標準的な Make パターン）。

### 根拠

環境変数のオーバーライドに対して最もシンプルで予測可能な動作を提供します：

- **未定義変数の処理**: `?=` は変数が完全に未定義の場合のみデフォルト値を割り当てる
- **即時評価**: 標準的な Make の動作
- **予測可能な動作**: 環境変数が設定されている場合は常にそれを使用

**例**:
```makefile
# 推奨パターン
MIXSEEK_USERNAME ?= mixseek_core
MIXSEEK_UID ?= 1000
MIXSEEK_GID ?= 1000
```

### 動作の比較

| パターン | 未定義変数 | 空文字列 (`VAR=`) | 設定された変数 |
|---------|-----------|------------------|--------------|
| `VAR ?= default` | デフォルトを使用 | 空を維持 | 値を維持 |
| `VAR := $(or $(VAR),default)` | デフォルトを使用 | デフォルトを使用 | 値を維持 |

**注**: 空文字列の扱いの違いは、この実装では重要ではありません。Docker がすべての無効な値（空を含む）を検出してエラーを返します。

### 参考資料

- [GNU Make: 条件関数](https://www.gnu.org/software/make/manual/html_node/Conditional-Functions.html)
- [Stack Overflow: ENV または デフォルトを使用した Makefile 変数の定義](https://stackoverflow.com/questions/24263291/define-a-makefile-variable-using-a-env-variable-or-a-default-value)

---

## 2. Docker Build ARG ベストプラクティス

### 決定事項

デフォルト値を持つ ARG を使用し、バリデーションは Docker の groupadd/useradd コマンドに依存します。

### 推奨パターン

```dockerfile
# 1. デフォルト値を持つ ARG を宣言
ARG MIXSEEK_USERNAME=mixseek_core
ARG MIXSEEK_UID=1000
ARG MIXSEEK_GID=1000

# 2. ARG 値を使用（Docker が自動的にバリデーション）
RUN groupadd -g ${MIXSEEK_GID} ${MIXSEEK_USERNAME} && \
    useradd -m -u ${MIXSEEK_UID} -g ${MIXSEEK_GID} -s /bin/bash ${MIXSEEK_USERNAME}

# 3. 必要に応じて ENV に変換（ランタイムで必要な場合）
ENV MIXSEEK_USERNAME=${MIXSEEK_USERNAME}
```

### 根拠

1. **デフォルト値を持つ ARG**: `--build-arg` によるオーバーライドを許可しながら、適切なデフォルトを提供
2. **Docker によるバリデーション**: groupadd/useradd が無効な値を検出し、明確なエラーメッセージで早期に失敗
3. **ENV への変換**: 必要に応じてランタイム用に値を永続化（オプション）

### ARG vs ENV

| 特徴 | ARG | ENV |
|------|-----|-----|
| **スコープ** | ビルド時のみ | ビルド時 AND ランタイム |
| **オーバーライド** | `docker build --build-arg` | `docker run -e` または Dockerfile |
| **永続性** | 最終イメージには含まれない | 最終イメージに含まれる |
| **セキュリティ** | コンテナ内にない | コンテナ内で可視 |
| **ユースケース** | ビルド設定 | ランタイム設定 |

### Makefile からの渡し方

```makefile
# 変数を Docker ビルドに渡す
docker build \
    --build-arg MIXSEEK_USERNAME=$(MIXSEEK_USERNAME) \
    --build-arg MIXSEEK_UID=$(MIXSEEK_UID) \
    --build-arg MIXSEEK_GID=$(MIXSEEK_GID) \
    -t $(IMAGE_NAME):$(IMAGE_TAG) .
```

### 参考資料

- [Docker ベストプラクティス: ARG と ENV の使用](https://www.docker.com/blog/docker-best-practices-using-arg-and-env-in-your-dockerfiles/)
- [Docker ドキュメント: 変数](https://docs.docker.com/build/building/variables/)

---

## 3. Linux ユーザー名推奨ガイドライン

### 推奨パターン

正規表現: `^[a-z_][a-z0-9_-]*$`、長さ制限 32 文字

### 根拠

このパターンは、Linux ディストリビューション全体で最も広く互換性のある標準を表します：

- **最初の文字**: 小文字のアルファベットまたはアンダースコア `[a-z_]`
- **後続の文字**: 小文字のアルファベット、数字、アンダースコア、ハイフン `[a-z0-9_-]*`
- **長さ**: 最大 32 文字（31 + null 終端文字）
- **大文字なし**: すべてのディストリビューションで移植可能
- **特殊文字なし**: シェルエスケープ問題を回避

### 推奨ルール

| ルール | 要件 | 例 |
|------|------|-----|
| **最初の文字** | `[a-z_]` のみ | `mixseek`, `_test` ✓ / `1user`, `Test` ✗ |
| **後続文字** | `[a-z0-9_-]` | `user-123`, `my_app` ✓ / `user@host` ✗ |
| **長さ** | ≤ 32 文字 | `thisusernameiswaytoolongandwillnotwork` ✗ |
| **予約名** | `.` または `..` でない | `user` ✓ / `.`, `..` ✗ |
| **数字のみ** | 許可されない | `user1`, `u2` ✓ / `123` ✗ |

**注**: これらのルールは推奨事項です。実際のバリデーションは Docker の useradd コマンドによって実行されます。

### ディストリビューション固有のパターン

| ディストリビューション | 正規表現パターン | 注記 |
|------------------|---------------|------|
| **Shadow-utils** | `^[a-z_][a-z0-9_-]*[$]?$` | 末尾に `$` を許可（システムアカウント） |
| **Debian/Ubuntu** | `^[a-z][-a-z0-9]*$` | 最初の文字としてアンダースコア不可 |
| **CentOS/RHEL** | `^[a-z_][a-z0-9_-]*[$]?$` | 一部のバージョンで大文字を許可 |
| **POSIX** | `^[a-z_][a-z0-9_-]*$` | 移植可能なファイル名文字セット |

選択したパターン（`^[a-z_][a-z0-9_-]*$`）は、これらの標準の共通部分であり、すべてのディストリビューションで動作します。

### 参考資料

- [Unix StackExchange: Linux ユーザーを検証する正規表現](https://unix.stackexchange.com/questions/157426/what-is-the-regex-to-validate-linux-users)
- [systemd.io: ユーザー/グループ名の構文](https://systemd.io/USER_NAMES/)
- [Baeldung: Linux ユーザー名が数字で始められない理由](https://www.baeldung.com/linux/usernames-no-digit-prefix)

---

## 4. Linux UID/GID 範囲とクロスプラットフォーム互換性

### 推奨範囲

UID/GID 範囲: **1000-65533**（システム予約値と特別な値を除く）

### 根拠

この範囲は、システム競合を避けながら最大のクロスプラットフォーム互換性を提供します：

- **下限（1000）**: システムアカウント範囲（0-999）を回避
- **上限（65533）**: 特別な値（65534、65535、4294967295）を回避
- **Linux 標準**: 通常のユーザーは通常 1000 から開始
- **macOS 互換**: システムグループ GID 20（staff）より上

### 特別な UID/GID 値

| 値 | 意味 | 回避する理由 |
|----|------|------------|
| **0** | root/wheel | セキュリティリスク、スーパーユーザー用に予約 |
| **1-99** | 静的システムアカウント | LSB Core Spec: 静的に割り当て |
| **100-999** | 動的システムアカウント | システムデーモン/サービス用に予約 |
| **65534** | nobody/nogroup | マッピング不可ユーザー用のオーバーフロー UID（NFS、名前空間） |
| **65535** | 無効（16 ビット -1） | レガシー 16 ビット UID システムでは無効として扱われる |
| **4294967295** | 無効（32 ビット -1） | setresuid()、chown() によって「変更なし」として扱われる |

### ディストリビューション別システム予約範囲

| ディストリビューション | システム UID | システム GID | 通常のユーザー |
|-------------------|-------------|-------------|--------------|
| **LSB Core Spec** | 0-99（静的）、100-499（動的） | 0-99（静的）、100-499（動的） | 500+ |
| **モダン Linux** | 0-999 | 0-999 | 1000-65533, 65536-4294967294 |
| **古い Linux** | 0-499 | 0-499 | 500+ |
| **macOS** | 0-500 | 0-500（GID 20 = staff） | 501+ |

**注**: これらの範囲は推奨事項です。実際のバリデーションは Docker の groupadd/useradd コマンドによって実行されます。

### 参考資料

- [systemd.io: UID と GID](https://systemd.io/UIDS-GIDS/)
- [Wikipedia: ユーザー識別子](https://en.wikipedia.org/wiki/User_identifier)
- [Linux Standard Base Core Specification](https://refspecs.linuxfoundation.org/LSB_3.0.0/LSB-PDA/LSB-PDA/usernames.html)

---

## 5. macOS vs Linux UID/GID の違い

### 決定事項

クロスプラットフォーム Docker コンテナの安全なデフォルトとして **GID 1000** を使用します。

### 根拠

GID 1000 は macOS と Linux の両方で競合を回避します：

- **Linux**: GID 1000 は標準の最初のユーザーグループ（UID 1000 と一致）
- **macOS**: GID 1000 はシステムグループより十分上（最高システム GID ~500）
- **Docker ボリューム**: ホストファイルシステムをマウントする際の権限問題を最小化

### プラットフォームの違い

| 側面 | Linux | macOS |
|-----|-------|-------|
| **最初のユーザー UID** | 1000 | 501 |
| **最初のユーザー GID** | 1000（プライベートグループ） | 20（staff グループ） |
| **システム UID 範囲** | 0-999 | 0-500 |
| **システム GID 範囲** | 0-999 | 0-500 |
| **ユーザー哲学** | ユーザーごとのプライベートグループ | 共有 staff グループ |

### macOS が GID 20（staff）を使用する理由

macOS は BSD スタイルのグループ哲学に従います：
- **GID 20 = staff**: 通常のユーザーのデフォルトグループ
- **共有グループ**: すべての通常のユーザーが同じ「staff」グループに属する
- **歴史的**: BSD Unix の伝統から継承
- **影響**: ユーザーはデフォルトでグループ権限を共有

### Linux が UID/GID 1000 を使用する理由

Linux はプライベートグループ哲学に従います：
- **ユーザープライベートグループ（UPG）**: 各ユーザーは一致する GID を持つ独自のグループを取得
- **最初の通常ユーザー**: UID 1000、GID 1000（ユーザー名 = グループ名）
- **システムアカウント**: 0-999 はサービス/デーモン用に予約
- **影響**: より良い分離、より安全なデフォルト権限

### GID 1000 がクロスプラットフォームで安全な理由

1. **システム範囲より上**: GID 1000 > 999（Linux）および > 500（macOS）
2. **競合なし**: macOS staff（20）またはシステムグループと衝突しない
3. **Linux での標準**: 最初のユーザー規約と一致
4. **Docker ベストプラクティス**: クロスプラットフォームコンテナに推奨

### 避けるべき GID

| GID | グループ | プラットフォーム | 回避する理由 |
|-----|---------|--------------|------------|
| **0** | root/wheel | すべて | セキュリティリスク |
| **20** | staff | macOS | macOS デフォルトユーザーグループと競合 |
| **1-99** | システムグループ | すべて | 静的に割り当てられたシステムグループ |
| **100-999** | システムグループ | Linux | デーモン用に動的に割り当て |
| **100-500** | システムグループ | macOS | システムサービス |

### Docker ボリューム権限問題

UID/GID の不一致は Docker ボリューム権限問題を引き起こします：

```
# macOS ホスト上
ホストユーザー:  UID 501、GID 20（staff）

# Linux コンテナ内
デフォルト:      UID 1000、GID 1000

# 結果: マウントされたボリュームにアクセスする際に権限拒否
```

**解決策**: ビルド引数を使用してホスト UID/GID に一致させるか、1000:1000 で標準化します。

### 実装の推奨事項

```makefile
# Makefile デフォルト
MIXSEEK_UID ?= 1000
MIXSEEK_GID ?= 1000

# macOS ユーザーはホストに一致するようにオーバーライドすべき
# export MIXSEEK_UID=$(id -u)
# export MIXSEEK_GID=1000  # 安全なクロスプラットフォーム選択、20 ではない
```

### 検討した代替案

1. **ホスト UID/GID を直接使用**
   ```makefile
   MIXSEEK_UID := $(shell id -u)
   MIXSEEK_GID := $(shell id -g)
   ```
   - **長所**: ホストと正確に一致、ボリューム権限に最適
   - **短所**: ユーザーがシステム UID の場合、Linux で失敗（まれ）、GID 20 が Linux コンテナ内で競合
   - **考慮事項**: 開発には良いが、ドキュメント化が必要

2. **常に 1000:1000 を使用**
   - **長所**: すべてのプラットフォームで一貫、シンプル
   - **短所**: macOS ホストファイルシステムで権限問題を引き起こす可能性
   - **デフォルトとして選択**: 互換性とシンプルさの最良のバランス

3. **プラットフォームごとに異なるデフォルトを使用**
   ```makefile
   ifeq ($(shell uname),Darwin)
       MIXSEEK_GID := 1000  # 競合を避けるため 20 ではない
   else
       MIXSEEK_GID := 1000
   endif
   ```
   - **短所**: 複雑、1000 がどこでも機能するため不要
   - **却下**: 過度に設計

### 参考資料

- [Fullstaq: Docker とホストファイルシステム所有者マッチング問題](https://www.fullstaq.com/knowledge-hub/blogs/docker-and-the-host-filesystem-owner-matching-problem)
- [Medium: Docker コンテナでの UID と GID の理解](https://blog.devops.dev/understanding-how-uid-and-gid-work-in-docker-containers-9e043f6405c1)
- [GitHub Issue: Docker addgroup GID 20 が mac で既に存在](https://github.com/newsboat/newsboat/issues/2932)

---

## 決定事項の要約

| トピック | 決定事項 | 主な根拠 |
|---------|---------|---------|
| **Make 変数** | `VAR ?= default` | シンプルで標準的な Make パターン |
| **Docker ARG** | デフォルト値を持つ ARG、Docker によるバリデーション | 柔軟、安全、Docker が明確なエラーを提供 |
| **ユーザー名推奨** | `^[a-z_][a-z0-9_-]{0,31}$` | すべての Linux ディストリビューションで移植可能 |
| **UID/GID 推奨範囲** | 1000-65533 | システムアカウントと特別な値を回避 |
| **デフォルト GID** | 1000 | macOS と Linux の両方で安全、競合なし |

---

## 実装チェックリスト

- [ ] Makefile を更新してデフォルトに `?=` パターンを使用
- [ ] デフォルト値を持つ Docker ARG 宣言を追加
- [ ] macOS ユーザー向けのオーバーライド手順を文書化
- [ ] クロスプラットフォーム互換性をテスト（Linux と macOS）
- [ ] 実行可能なガイダンスを含むエラーメッセージを追加（Docker から）

**注**: バリデーション実装タスクはこのチェックリストから削除されました。すべてのバリデーションは Docker によって処理されます。
