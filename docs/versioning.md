# バージョニング戦略

このドキュメントは、MixSeek-Core のバージョニング戦略とリリースプロセスについて説明します。

## バージョン体系

MixSeek-Core は [PEP 440](https://peps.python.org/pep-0440/) に準拠したバージョニングを採用しています。

### バージョン形式

```
MAJOR.MINOR.PATCH[PRE-RELEASE]
```

例：
- `0.1.0a1` - Alpha リリース（バージョン 0.1.0 の 1 番目のアルファ版）
- `0.2.0b2` - Beta リリース（バージョン 0.2.0 の 2 番目のベータ版）
- `0.2.0rc1` - Release Candidate（バージョン 0.2.0 のリリース候補版）
- `1.0.0` - 正式リリース

### リリースステージ

| ステージ | 形式 | 安定性 | セキュリティ | 破壊的変更 |
|---------|------|--------|----------|----------|
| **Alpha** | `0.x.ya*` | 低 | なし | あり |
| **Beta** | `0.x.yb*` | 中 | 最善努力 | あり |
| **RC** | `0.x.yrc*` | 高 | 最善努力 | なし |
| **Stable** | `x.y.z` | 高 | 保証 | 1.0.0 以上のみ |

## 開発サイクル

### Alpha 段階（0.x.ya*）

**状況**: 開発中、実験的機能の追加

**リリース頻度**: 2週間ごと

**特徴**:
- 破壊的変更が頻繁に発生
- API 設計が不安定
- セキュリティ保証なし
- バグ修正のみの運用ではない

**例**:
```
0.1.0a1 → 0.1.0a2 → 0.2.0a1 → 0.2.0a2 → ...
```

### Beta 段階（0.x.yb*）

**状況**: 機能はほぼ完成、テスト・洗練中

**条件**:
- 主要機能が実装完了
- 複数エンジニアでのテスト完了
- API がほぼ安定

**例**:
```
0.3.0b1 (機能完成版) → 0.3.0b2 (バグ修正) → 0.3.0rc1
```

### Release Candidate（0.x.yrc*）

**状況**: 本番環境テスト前の最終確認

**条件**:
- Beta での問題が解決
- 本番環境でのテスト予定
- API が確定

**リリース頻度**: 問題発見時のみ

### Stable（1.0.0+）

**状況**: 本番環境対応版

**条件**:
- RC での全問題が解決
- 本番環境で十分なテスト実施
- セキュリティ対応体制確立
- サポート体制確立

**破壊的変更**: MAJOR バージョン更新のみ

## バージョン更新ルール

### パッチバージョン更新（0.1.0 → 0.1.1）

**条件**:
- バグ修正のみ
- API 変更なし
- 破壊的変更なし

**コマンド**:
```bash
# Alpha 版の場合 (0.1.0a1 → 0.1.1a1)
$ uv run cz bump --prerelease alpha --increment PATCH --yes

# Stable 版の場合 (0.1.0 → 0.1.1)
$ uv run cz bump --increment PATCH --yes
```

### マイナーバージョン更新（0.1.0 → 0.2.0）

**条件**:
- 新機能追加
- Alpha/Beta/RC 段階では破壊的変更を含む場合あり
- 1.0.0 以上では破壊的変更なし

**コマンド**:
```bash
# Alpha 版の場合 (0.1.0a1 → 0.2.0a1)
$ uv run cz bump --prerelease alpha --increment MINOR --yes

# Stable 版の場合 (0.1.0 → 0.2.0)
$ uv run cz bump --increment MINOR --yes
```

### メジャーバージョン更新（0.x.x → 1.0.0）

**条件**:
- メジャー機能の完成
- API の安定化
- 本番環境対応
- セキュリティ保証の開始

**コマンド**:
```bash
# Alpha 版の場合 (0.1.0a1 → 1.0.0a1)
$ uv run cz bump --prerelease alpha --increment MAJOR --yes

# Stable 版の場合 (0.x.x → 1.0.0)
$ uv run cz bump --increment MAJOR --yes
```

## リリーススケジュール

### 標準リリースサイクル

| フェーズ | 期間 | バージョン | リリース頻度 |
|---------|------|-----------|----------|
| Alpha | 0.1.0 - 0.9.x | 0.x.ya* | 2 週間ごと |
| Beta | - | 0.x.yb* | 必要に応じて |
| RC | - | 0.x.yrc* | 必要に応じて |
| Stable | 1.0.0+ | x.y.z | 月 1 回程度 |

### リリース日時

- **リリース決定**: 毎週金曜日
- **リリース実施**: 翌月曜日
- **公式発表**: リリース当日

## commitizen による自動更新

### 動作概要

**現在 Alpha 版のため、`--prerelease alpha` オプションが必須です。**

```bash
# Alpha 版のビルド番号をインクリメント (0.1.0a1 → 0.1.0a2)
$ uv run cz bump --prerelease alpha --yes
```

実行時に以下が自動で行われます：

1. **コミット解析**: Conventional Commits 形式のコミットメッセージを解析
2. **バージョン決定**: コミットタイプに基づいて自動的にバージョン更新レベルを決定
   - `feat:` → MINOR バージョン更新（stable 版）/ **ビルド番号更新**（prerelease 版）
   - `fix:` → PATCH バージョン更新（stable 版）/ **ビルド番号更新**（prerelease 版）
   - `feat!:`, `fix!:` → MAJOR バージョン更新（破壊的変更）
   - **注**: `--prerelease alpha` 使用時は、コミットタイプに関わらずビルド番号のみインクリメント（0.1.0a1 → 0.1.0a2）
3. **ファイル更新**:
   - `pyproject.toml`: version フィールド更新
   - `CHANGELOG.md`: Conventional Commits から自動生成
4. **Git 操作**:
   - 変更をコミット（メッセージ: `release: bump version to x.x.x`）
   - 注釈付きタグ作成（タグ名: `vx.x.x`）

### 設定ファイル（`pyproject.toml`）

```toml
[tool.commitizen]
name = "cz_conventional_commits"
version = "0.1.0a1"
version_files = [
    "pyproject.toml:project.version"
]
tag_format = "v$version"
update_changelog_on_bump = true
annotated_tag = true
bump_message = "release: bump version to $new_version"
changelog_file = "CHANGELOG.md"
changelog_incremental = true
version_scheme = "pep440"
```

### ドライラン（テスト実行）

変更を適用する前に確認したい場合：

```bash
# Alpha 版の場合
$ uv run cz bump --prerelease alpha --dry-run --yes
```

### 手動でのバージョン制御

自動判定を上書きしたい場合：

```bash
# Alpha 版でマイナーバージョン強制更新 (0.1.0a1 → 0.2.0a1)
$ uv run cz bump --prerelease alpha --increment MINOR --yes

# Alpha 版でパッチバージョン強制更新 (0.1.0a1 → 0.1.1a1)
$ uv run cz bump --prerelease alpha --increment PATCH --yes

# Alpha 版でメジャーバージョン強制更新 (0.1.0a1 → 1.0.0a1)
$ uv run cz bump --prerelease alpha --increment MAJOR --yes

# Alpha 版から正式版へ昇格 (0.1.0a1 → 0.1.0)
$ uv run cz bump --yes
```

## CHANGELOG.md との連携

### CHANGELOG 自動生成

**重要**: CHANGELOG.md は **commitizen により Conventional Commits から自動生成**されます。手動編集は不要です。

### 生成ロジック

commitizen は以下のルールで CHANGELOG を生成します：

- `feat:` コミット → **Feat** セクション
- `fix:` コミット → **Fix** セクション
- `docs:` コミット → **Docs** セクション
- `refactor:` コミット → **Refactor** セクション
- `test:` コミット → **Test** セクション
- `BREAKING CHANGE` → **BREAKING CHANGES** セクション

### 例: Conventional Commits から CHANGELOG 生成

**コミット履歴:**
```bash
$ git log --oneline
abc1234 feat: add multi-agent orchestration framework
def5678 feat(cli): add mixseek exec command
ghi9012 fix: resolve memory leak in agent cleanup
jkl3456 docs: update getting-started guide
```

**commitizen 実行:**
```bash
$ uv run cz bump --yes
# → 自動的に CHANGELOG.md が生成される
```

**生成された CHANGELOG.md:**
```markdown
## v0.2.0 (2025-12-18)

### Feat

- add multi-agent orchestration framework
- **cli**: add mixseek exec command

### Fix

- resolve memory leak in agent cleanup

### Docs

- update getting-started guide

## v0.1.0a1 (2025-12-04)

### Feat

- Initial alpha release
- Multi-agent orchestration framework with Leader/Member agent hierarchy
- ...
```

### Alpha 版での CHANGELOG 生成

Alpha 版でも MINOR/PATCH バージョンが正しく更新されます：

```bash
# feat: コミット複数回
$ git commit -m "feat: add feature A"
$ git commit -m "feat: add feature B"
$ git commit -m "fix: fix bug C"

# commitizen 実行
$ uv run cz bump --yes
# → 0.1.0a1 → 0.2.0 (MINOR バージョン更新)
# → CHANGELOG に上記3つのコミットがまとめて記載される
```

## Conventional Commits によるバージョン制御

このプロジェクトでは [Conventional Commits](https://www.conventionalcommits.org/) が**必須**です。

### バージョンアップルール

| コミットタイプ | Stable 版（1.0.0+） | Prerelease 版（0.x.ya*） |
|-------------|------------------|----------------------|
| `feat:` | MINOR バージョン更新 | build 番号更新 |
| `fix:` | PATCH バージョン更新 | build 番号更新 |
| `feat!:`, `fix!:` | MAJOR バージョン更新 | build 番号更新 |
| `docs:`, `refactor:`, `test:` | 影響なし | 影響なし |

### 例: Alpha 版（現在）

```bash
# 現在のバージョン: 0.1.0a1

$ git commit -m "feat: new agent integration system"
$ uv run cz bump --prerelease alpha --yes
# → 0.1.0a1 → 0.1.0a2 (build 番号のみインクリメント)

$ git commit -m "fix: memory leak in processing"
$ uv run cz bump --prerelease alpha --yes
# → 0.1.0a2 → 0.1.0a3 (build 番号のみインクリメント)

# マイナーバージョンアップを強制したい場合
$ uv run cz bump --prerelease alpha --increment MINOR --yes
# → 0.1.0a3 → 0.2.0a1
```

### 例: Stable 版（1.0.0 以降）

```bash
# 現在のバージョン: 1.2.3

$ git commit -m "feat: new agent integration system"
$ uv run cz bump --yes
# → 1.2.3 → 1.3.0 (MINOR バージョン更新)

$ git commit -m "fix: memory leak in processing"
$ uv run cz bump --yes
# → 1.3.0 → 1.3.1 (PATCH バージョン更新)

$ git commit -m "feat!: redesigned API structure"
$ uv run cz bump --yes
# → 1.3.1 → 2.0.0 (MAJOR バージョン更新)
```

## トラブルシューティング

### commitizen が動作しない場合

```bash
# 1. インストール確認
$ uv run cz version

# 2. 設定ファイル確認
$ grep -A 20 "\[tool.commitizen\]" pyproject.toml

# 3. ドライラン確認
$ uv run cz bump --dry-run --yes
```

### Conventional Commits フォーマットエラー

```bash
# エラー例: commitizen がバージョンを決定できない
# 原因: Conventional Commits 形式に従っていないコミットメッセージ

# ✅ 正しい形式
$ git commit -m "feat: add new feature"
$ git commit -m "fix: resolve bug"

# ❌ 間違った形式
$ git commit -m "Add new feature"  # タイプがない
$ git commit -m "feat add feature"  # コロンがない
$ git commit -m "Feat: add feature"  # 大文字（小文字を使用）
```

### プレリリース版の作成方法

Beta 版や Release Candidate 版を作成する場合：

```bash
# Alpha リリース作成
$ uv run cz bump --prerelease alpha --yes
# → 0.1.0 → 0.2.0a1

# Beta リリース作成
$ uv run cz bump --prerelease beta --yes
# → 0.2.0a1 → 0.2.0b1

# Release Candidate 作成
$ uv run cz bump --prerelease rc --yes
# → 0.2.0b1 → 0.2.0rc1

# プレリリースを正式版に昇格
$ uv run cz bump --yes
# → 0.2.0rc1 → 0.2.0
```

## 関連リンク

- [CONTRIBUTING.md](../CONTRIBUTING.md) - コントリビューション ガイドライン
- [CHANGELOG.md](../CHANGELOG.md) - 変更履歴
- [PEP 440](https://peps.python.org/pep-0440/) - Python バージョニング標準
- [Semantic Versioning](https://semver.org/) - セマンティック バージョニング
- [Keep a Changelog](https://keepachangelog.com/) - CHANGELOG 形式
- [Conventional Commits](https://www.conventionalcommits.org/) - コミットメッセージ形式
- [commitizen 公式ドキュメント](https://commitizen-tools.github.io/commitizen/)
