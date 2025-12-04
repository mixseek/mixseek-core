# 設計思想: 公開API vs 実装詳細

## 目的

mixseek-coreの設定システムにおいて、**ユーザー向けAPI**と**内部実装詳細**を明確に区別し、設計思想を文書化します。

## 設計原則

### 1. レイヤーアーキテクチャ

```
┌─────────────────────────────────────────┐
│  公開API層 (ユーザー向け)                │
│  - 環境変数: MIXSEEK_WORKSPACE           │
│  - TOMLキー: workspace                   │
│  - CLI引数: --workspace                  │
└─────────────────┬───────────────────────┘
                  │ 正規化
┌─────────────────┴───────────────────────┐
│  正規化層 (内部処理)                     │
│  - 環境変数マッピング                    │
│  - TOMLキーマッピング                    │
└─────────────────┬───────────────────────┘
                  │ 変換
┌─────────────────┴───────────────────────┐
│  実装詳細層 (Pydantic)                   │
│  - Pydanticフィールド: workspace_path    │
│  - 内部環境変数: MIXSEEK_WORKSPACE_PATH  │
└─────────────────────────────────────────┘
```

### 2. 公開API（ユーザー向け）

| カテゴリ | OrchestratorSettings | UISettings | 定義場所 |
|---------|---------------------|-----------|---------|
| **環境変数** | `MIXSEEK_WORKSPACE` | `MIXSEEK_UI__WORKSPACE` | `CLAUDE.md`, `environment-variable-priority.md` |
| **TOMLキー** | `workspace` | `workspace` | `templates.py` (project.toml) |
| **CLI引数** | `--workspace` | `--workspace` | コマンド定義 |

**特徴**:
- ユーザー向けドキュメントに記載される
- 直感的で分かりやすい名前
- 仕様として定義・保証される
- セマンティックバージョニングで保護される

### 3. 実装詳細（内部）

| カテゴリ | OrchestratorSettings | UISettings | 用途 |
|---------|---------------------|-----------|------|
| **Pydanticフィールド** | `workspace_path: Path` | `workspace_path: Path` | 内部データモデル |
| **内部環境変数** | `MIXSEEK_WORKSPACE_PATH` | `MIXSEEK_UI__WORKSPACE_PATH` | Pydanticのenv_prefix機構 |

**特徴**:
- ユーザー向けドキュメントには記載しない
- Pydanticの技術的要件に従う命名
- 内部実装として自由に変更可能
- 公開APIとの整合性は正規化層で保証

## 正規化層の実装

### 環境変数正規化 (`schema.py:76-94`)

```python
# 公式環境変数を内部フィールド名にマッピング
#
# 設計思想:
#   - ユーザー向けAPI: MIXSEEK_WORKSPACE, MIXSEEK_UI__WORKSPACE (公式環境変数)
#   - 内部Pydanticフィールド: workspace_path (実装詳細)
#   - Pydanticのenv_prefix機構: MIXSEEK_WORKSPACE_PATH, MIXSEEK_UI__WORKSPACE_PATH を要求
#
# このマッピングにより、公式環境変数を内部的にPydanticが認識できる形式に正規化します。
if settings_cls.__name__ == "OrchestratorSettings":
    if "MIXSEEK_WORKSPACE" in os.environ and "MIXSEEK_WORKSPACE_PATH" not in os.environ:
        os.environ["MIXSEEK_WORKSPACE_PATH"] = os.environ["MIXSEEK_WORKSPACE"]
elif settings_cls.__name__ == "UISettings":
    if "MIXSEEK_UI__WORKSPACE" in os.environ and "MIXSEEK_UI__WORKSPACE_PATH" not in os.environ:
        os.environ["MIXSEEK_UI__WORKSPACE_PATH"] = os.environ["MIXSEEK_UI__WORKSPACE"]
```

**処理フロー**:
1. ユーザーが`MIXSEEK_WORKSPACE`を設定
2. 正規化層が`MIXSEEK_WORKSPACE_PATH`に変換
3. Pydanticが`workspace_path`フィールドとして処理

### TOMLキー正規化 (`toml_source.py:153-165`)

```python
# 公式TOMLキー 'workspace' を内部フィールド 'workspace_path' にマッピング
#
# 設計思想:
#   - ユーザー向けAPI: TOMLキー 'workspace' (公式キー)
#   - 内部Pydanticフィールド: 'workspace_path' (実装詳細)
#
# このマッピングにより、ユーザーはTOMLファイルで直感的な 'workspace' キーを使用でき、
# 内部的にはPydanticのフィールド名 'workspace_path' に正規化されます。
if section_name in ("OrchestratorSettings", "UISettings"):
    if "workspace" in self.toml_data and "workspace_path" not in self.toml_data:
        self.toml_data["workspace_path"] = self.toml_data["workspace"]
        # extra="forbid"対策: 元のキーを削除（Pydanticは'workspace'を認識しないため）
        del self.toml_data["workspace"]
```

**処理フロー**:
1. ユーザーがTOMLファイルで`workspace = "/path"`を記述
2. 正規化層が`workspace_path`に変換
3. Pydanticが`workspace_path`フィールドとして処理

## 優先順位

環境変数の優先順位（`environment-variable-priority.md`より）:

1. **CLI引数**: `--workspace /path/to/workspace` (最優先、明示的指定)
2. **公式環境変数**: `MIXSEEK_WORKSPACE` (推奨、primary)
3. **内部環境変数**: `MIXSEEK_WORKSPACE_PATH` (非推奨、technical alternative)
4. **エラー発生**: Article 9準拠（暗黙的フォールバックなし）

**Note**: `MIXSEEK_WORKSPACE_PATH`が設定されている場合は優先されますが、これは内部実装詳細であり、ユーザーに推奨されません。

## 用語ガイドライン

### ✅ 使用すべき表現

| 概念 | 推奨表現 | 例 |
|-----|---------|---|
| 公式インターフェース | "公式環境変数"、"公式TOMLキー" | MIXSEEK_WORKSPACEは公式環境変数 |
| 内部実装 | "内部実装詳細"、"Pydanticフィールド" | workspace_pathは内部実装詳細 |
| 変換処理 | "正規化"、"マッピング" | 公式環境変数を内部フィールド名にマッピング |
| 優先度 | "推奨"、"非推奨" | MIXSEEK_WORKSPACEが推奨 |

### ❌ 避けるべき表現

| 非推奨表現 | 理由 | 代替表現 |
|-----------|-----|---------|
| "後方互換性" | MIXSEEK_WORKSPACEは最初から公式 | "公式環境変数のサポート" |
| "legacy" | 誤解を招く（古いものではない） | "公式API" |
| "新しい環境変数" vs "古い環境変数" | 時系列の誤認識 | "内部環境変数" vs "公式環境変数" |
| "deprecated" | 非推奨ではなく実装詳細 | "内部実装詳細（非公開）" |

## 実装時の注意点

### 1. ドキュメント作成時

**ユーザー向けドキュメント** (`CLAUDE.md`, `docs/*.md`):
- ✅ 公式環境変数のみ言及: `MIXSEEK_WORKSPACE`
- ❌ 内部環境変数は記載しない: `MIXSEEK_WORKSPACE_PATH`

**開発者向けドキュメント** (コメント、設計文書):
- ✅ 正規化層の存在を説明
- ✅ Pydantic実装詳細との関係を明記

### 2. コメント記述時

**Good Example**:
```python
# 公式環境変数を内部フィールド名にマッピング
# MIXSEEK_WORKSPACE (公式) → MIXSEEK_WORKSPACE_PATH (内部)
```

**Bad Example**:
```python
# 後方互換性のためMIXSEEK_WORKSPACEをサポート
# MIXSEEK_WORKSPACE (古い) → MIXSEEK_WORKSPACE_PATH (新しい)
```

### 3. エラーメッセージ作成時

**Good Example**:
```
Workspace path not specified. Use --workspace option or set MIXSEEK_WORKSPACE environment variable.
```

**Bad Example**:
```
Workspace path not specified. Use MIXSEEK_WORKSPACE_PATH or MIXSEEK_WORKSPACE (legacy) environment variable.
```

## Article 9準拠性の検証

**検証日**: 2025-11-12
**検証タスク**: T099 (specs/013-configuration/tasks.md)

### 環境変数正規化層のArticle 9準拠性

正規化層の実装（`schema.py:76-94`）は、以下の理由によりArticle 9に準拠すると判定されました：

#### ✅ 準拠の根拠

1. **新しい値を生成していない**
   - 既存の環境変数`MIXSEEK_WORKSPACE`の値を`MIXSEEK_WORKSPACE_PATH`にコピーするのみ
   - データの変換や推測を行わない

2. **暗黙的フォールバックではない**
   - 明示的な条件チェック: `if "MIXSEEK_WORKSPACE" in os.environ and "MIXSEEK_WORKSPACE_PATH" not in os.environ`
   - 両方が設定されている場合は`MIXSEEK_WORKSPACE_PATH`を優先（ユーザーの明示的指定を尊重）

3. **データソースの透明性を維持**
   - コードコメントで設計思想を明示
   - 正規化処理を明示的に記述（隠蔽していない）

4. **設計の一貫性**
   - TOML正規化層（`toml_source.py:153-165`）と同じパターン
   - 公開API ↔ 内部実装の橋渡しという統一された設計思想

#### 決定

- **Status**: Article 9の正当な例外として承認
- **Action**: 修正不要
- **Rationale**: データソースの透明性を損なわず、明示的な正規化処理として実装されている

### TOMLキー正規化層のArticle 9準拠性

TOML正規化層（`toml_source.py:153-165`）も同様にArticle 9に準拠：
- ユーザーが記述したTOMLキー`workspace`を内部フィールド`workspace_path`に変換
- データソースは明確（TOMLファイル）
- 値の生成や推測を行わない

## 参照

- **公式環境変数定義**: `CLAUDE.md` (Environment Variables section)
- **優先順位仕様**: `specs/013-configuration/checklists/environment-variable-priority.md`
- **実装**: `src/mixseek/config/schema.py` (正規化層), `src/mixseek/config/sources/toml_source.py` (TOML正規化)
- **タスク**: `specs/013-configuration/tasks.md` (T090, T099)
- **Article 9**: `.specify/memory/constitution.md` (Data Accuracy Mandate)
