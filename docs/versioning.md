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
$ uv run bump2version patch
```

### マイナーバージョン更新（0.1.0 → 0.2.0）

**条件**:
- 新機能追加
- Alpha/Beta/RC 段階では破壊的変更を含む場合あり
- 1.0.0 以上では破壊的変更なし

**コマンド**:
```bash
$ uv run bump2version minor
```

### メジャーバージョン更新（0.x.x → 1.0.0）

**条件**:
- メジャー機能の完成
- API の安定化
- 本番環境対応
- セキュリティ保証の開始

**コマンド**:
```bash
$ uv run bump2version major
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

## bump2version による自動更新

### 動作概要

```bash
$ uv run bump2version minor
```

実行時に以下が自動で行われます：

1. **バージョンの解析**: `.bumpversion.cfg` から現在のバージョンを読込
2. **新バージョンの計算**: 指定したパートでバージョン更新（major/minor/patch）
3. **ファイル更新**:
   - `pyproject.toml`: version フィールド更新
   - `CHANGELOG.md`: 新バージョンセクション追加
4. **Git 操作**:
   - 変更をコミット（メッセージ: `release: bump version to x.x.x`）
   - タグ作成（タグ名: `vx.x.x`）

### 設定ファイル（`.bumpversion.cfg`）

```ini
[bumpversion]
current_version = 0.1.0a1
# バージョン形式を定義
parse = (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)((?P<release>[ab]|rc)(?P<build>\d+))?
serialize =
    {major}.{minor}.{patch}{release}{build}
    {major}.{minor}.{patch}

# 自動コミット・タグ作成
commit = True
tag = True
tag_name = v{new_version}
message = release: bump version to {new_version}

# 管理対象ファイル
[bumpversion:file:pyproject.toml]
[bumpversion:file:CHANGELOG.md]
```

### ドライラン（テスト実行）

変更を適用する前に確認したい場合：

```bash
$ uv run bump2version --dry-run --verbose minor
```

## CHANGELOG.md との連携

### CHANGELOG 構造

```markdown
# Changelog

## [Unreleased]  ← 次のリリース用

### Added
- (新機能追加時にここに記載)

### Fixed
- (バグ修正時にここに記載)

## [0.1.0a1] - 2025-12-04  ← リリース済みバージョン

### Added
- Initial alpha release
- ...
```

### bump2version による更新

**重要**: CHANGELOG.md は **bump2version では更新されません**。手動で管理する必要があります。

**手動更新手順:**

1. リリース前に `## [Unreleased]` セクションに変更内容を記載
2. bump2version 実行後、新しいバージョンセクションを手動で追加

**例 (`0.1.0a1 → 0.2.0` へのバージョンアップ):**

**実行前:**
```markdown
# Changelog

## [Unreleased]

### Added
- Multi-agent orchestration framework
- CLI commands

## [0.1.0a1] - 2025-12-04

### Added
- Initial alpha release
```

**bump2version 実行:**
```bash
$ uv run bump2version minor
# pyproject.toml が 0.1.0a1 → 0.2.0 に更新される
```

**実行後（手動で CHANGELOG.md を更新）:**
```markdown
# Changelog

## [Unreleased]

## [0.2.0] - 2025-12-18  ← 手動で追加

### Added
- Multi-agent orchestration framework
- CLI commands

## [0.1.0a1] - 2025-12-04

### Added
- Initial alpha release
```

**将来の自動化（Issue #16）**: GitHub Actions により、タグ push 時に CHANGELOG.md からバージョンセクションを抽出し、GitHub Release を自動作成する予定です。

## セマンティックバージョニング（参考）

今後 1.0.0 以降で [Conventional Commits](https://www.conventionalcommits.org/) を導入する場合：

```
feat:     → MINOR バージョン更新
fix:      → PATCH バージョン更新
feat!:    → MAJOR バージョン更新（破壊的変更）
```

例：
```bash
$ git commit -m "feat: new agent integration system"   # 0.3.0 → 0.4.0
$ git commit -m "fix: memory leak in processing"       # 0.4.0 → 0.4.1
$ git commit -m "feat!: redesigned API structure"      # 1.0.0 → 2.0.0
```

## トラブルシューティング

### bump2version が動作しない場合

```bash
# 1. インストール確認
$ uv run bump2version --version

# 2. 設定ファイル確認
$ cat .bumpversion.cfg

# 3. ドライラン確認
$ uv run bump2version --dry-run --verbose minor
```

### .bumpversion.cfg を編集した場合

```bash
# 1. キャッシュクリア
$ rm -rf .venv

# 2. 再度インストール
$ uv sync --group dev

# 3. テスト実行
$ uv run bump2version --dry-run --verbose minor
```

## 関連リンク

- [CONTRIBUTING.md](../CONTRIBUTING.md) - コントリビューション ガイドライン
- [CHANGELOG.md](../CHANGELOG.md) - 変更履歴
- [PEP 440](https://peps.python.org/pep-0440/) - Python バージョニング標準
- [Semantic Versioning](https://semver.org/) - セマンティック バージョニング
- [Keep a Changelog](https://keepachangelog.com/) - CHANGELOG 形式
- [bump2version 公式ドキュメント](https://github.com/c4urself/bump2version)
