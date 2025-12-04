<!--
Sync Impact Report
===================
Version Change: 1.4.1 → 1.5.2
Reason: spec-kit v0.0.88 upgrade with naming convention relaxation and runtime guidance expansion

Modified Principles:
- Article 15: SpecKit Naming Convention
  - Made mixseek-core prefix optional (MUST → SHOULD)
  - Updated naming examples: `002-config` now valid (previously marked as error)
  - Unified terminology: `<number>` → `<issue-number>` throughout
  - Aligned documentation with actual create-new-feature.sh behavior

Modified Sections:
- Governance > Compliance Review > ランタイムガイダンス
  - Added AGENTS.md (generic AI agent guidance)
  - Added GEMINI.md (Google Gemini guidance)
  - Restructured as bullet list for clarity

Templates Requiring Updates:
- ✅ .specify/templates/spec-template.md - Already uses `[###-feature-name]` format (compatible)
- ✅ .specify/scripts/bash/create-new-feature.sh - Generates `<issue-number>-<name>` format
- ✅ All speckit commands updated via spec-kit v0.0.88

Follow-up TODOs:
- None

Impact Summary:
- Relaxed naming convention to match actual tooling behavior
- Both `002-config` and `002-mixseek-core-config` formats are now valid
- Runtime guidance now covers multiple AI tools (Claude, generic agents, Gemini)
- Improved consistency between documentation and implementation
-->

# mixseek-core Constitution

## Core Principles

### Article 1: Library-First Principle

すべての機能は、スタンドアロンのライブラリとして開始しなければならない（MUST）。
アプリケーションコード内に直接実装してはならない（MUST NOT）。

**理由**: モジュール性、再利用性、テストの容易さを保証

### Article 2: CLI Interface Mandate

すべてのライブラリは、コマンドラインインターフェースを通じて機能を公開しなければならない（MUST）。

**必須要件**:
- テキスト入力（stdin、引数、ファイル）をサポートしなければならない（MUST）
- テキスト出力（stdout）を提供しなければならない（MUST）
- エラーはstderrに出力しなければならない（MUST）
- JSON形式をサポートしなければならない（MUST）

**理由**: 観測可能性とテストの容易さを保証

### Article 3: Test-First Imperative

**これは非交渉的である**: すべての実装は厳密なTDD（テスト駆動開発）に従わなければならない（MUST）。

**実装コードを書く前に**:
1. ユニットテストを作成しなければならない（MUST）
2. テストをユーザーに承認してもらわなければならない（MUST）
3. テストが失敗する（Redフェーズ）ことを確認しなければならない（MUST）

**テスト構成の原則**:
1. テストコードは機能毎に作成しなければならない（MUST）
2. 1つの機能に対して1つのテストファイルを対応させなければならない（MUST）
3. テストファイル名は対象機能を明確に反映させなければならない（MUST）
   - 例: `test_google_search.py` ← `google_search.py`
4. 機能が複雑な場合は、サブ機能毎にテストクラスで分離すべきである（SHOULD）

**理由**: AIによる「動くけど正しくない」コード生成を防ぐ

### Article 4: Documentation Integrity

**これは非交渉的である**: すべての実装は、ドキュメント仕様との完全な整合性を保たなければならない（MUST）。

**必須要件**:
1. 実装前の仕様確認を必ず実施しなければならない（MUST）
2. ドキュメント変更時はユーザー承認を取得しなければならない（MUST）
3. ドキュメント更新完了後に実装着手しなければならない（MUST）
4. 仕様が曖昧な場合は実装を停止し、明確化を要求しなければならない（MUST）

**実施プロトコル**:
- **仕様曖昧性検出**: 複数解釈可能な記述を特定し報告する
- **仕様確認チェックリスト**: 実装前に仕様書の該当セクションを必ず確認する

**理由**: AIによる仕様誤認識・独自解釈を防ぎ、意図した通りの実装を保証

### Article 5: Simplicity

**最小プロジェクト構造**:
- 初期実装では最大3プロジェクトまでとしなければならない（MUST）
- 追加プロジェクトには文書化された正当な理由が必要である（MUST）

**理由**: 過剰設計と不必要な複雑さを防ぐ

### Article 6: Anti-Abstraction

**フレームワーク信頼の原則**:
- フレームワークの機能を直接使用しなければならない（MUST）
- 不必要なラッパーを作成してはならない（MUST NOT）

**理由**: 「車輪の再発明」を防ぎ、標準的なパターンを活用

### Article 7: Integration-First Testing

テストは現実的な環境を使用しなければならない（MUST）:
- モックより実際のデータベースを優先すべきである（SHOULD）
- スタブより実際のサービスインスタンスを優先すべきである（SHOULD）
- 実装前にコントラクトテストが必須である（MUST）

**理由**: 実環境での動作保証とインテグレーション問題の早期発見

## Quality Assurance & Constraints

### Article 8: Code Quality Standards

**これは非交渉的である**: すべてのコードは、品質基準に完全に準拠しなければならない（MUST）。
いかなる理由があっても品質基準の例外化を認めない。

**必須要件**:
- 品質基準の完全遵守が必要である（MUST）
- コミット前の品質チェックが必須である（MUST）
- 時間制約、進捗圧力、緊急性を理由とした品質妥協は禁止である（MUST NOT）
- リンター、フォーマッター、型チェッカーの全エラーを解消しなければならない（MUST）

**実施プロトコル**:
- **コミット前**: `ruff check --fix . && ruff format . && mypy .` を実行する
- **CI/CD**: すべての品質チェック（ruff、mypy）をパイプラインで自動実行する
- **品質基準違反時**: 作業を完全停止し、修正完了まで次工程に進まない

**理由**: 技術的負債の蓄積を防ぎ、長期的な保守性とコード品質を保証

### Article 9: Data Accuracy Mandate

**これは非交渉的である**: すべてのデータは、明示的なソースから取得しなければならない（MUST）。
推測、フォールバック、ハードコードは一切認めない。

**必須要件**:

1. **一次データの推測禁止**
   - マジックナンバーや固定文字列の直接埋め込みを禁止する（MUST NOT）
   - 環境依存値の埋め込みを禁止する（MUST NOT）
   - 認証情報・APIキーのコード内保存を禁止する（MUST NOT）

2. **暗黙的フォールバック禁止**
   - データ取得失敗時の自動デフォルト値割り当てを禁止する（MUST NOT）
   - エラーを隠蔽する自動補完を禁止する（MUST NOT）
   - 推測に基づく値の生成を禁止する（MUST NOT）

3. **設定値ハードコード禁止**
   - すべての固定値は名前付き定数として定義しなければならない（MUST）
   - 設定値は専用の設定モジュールで一元管理しなければならない（MUST）
   - 環境固有値は環境変数または設定ファイルで管理しなければならない（MUST）

**実装例**:

```python
# 悪い例（禁止）
timeout = 30  # ハードコードされた値
if not data:
    data = "default"  # 暗黙的フォールバック

# 良い例（推奨）
TIMEOUT_SECONDS = int(os.environ["API_TIMEOUT"])  # 環境変数から取得
if not data:
    raise ValueError("Required data is missing")  # 明示的エラー処理
```

**理由**: データの正確性とトレーサビリティを保証し、潜在的なバグを防ぐ

### Article 10: DRY Principle

**これは非交渉的である**: すべての実装において、コードの重複を避けなければならない（MUST）。
Don't Repeat Yourself - 同じ知識を複数の場所で表現してはならない（MUST NOT）。

**必須要件**:

1. **実装前の事前調査必須**
   - 既存の実装を必ず検索・確認しなければならない（MUST）（Glob, Grepツールの活用）
   - 類似機能の存在を確認しなければならない（MUST）
   - 再利用可能なコンポーネントを特定しなければならない（MUST）

2. **共通パターンの認識必須**
   - 3回以上の繰り返しパターンを抽出しなければならない（MUST）
   - 同一ロジックの関数化・モジュール化を行わなければならない（MUST）
   - 設定駆動アプローチを検討すべきである（SHOULD）

3. **重複検出時の強制停止**
   - 重複実装を検出した場合は作業を停止しなければならない（MUST）
   - 既存実装の拡張可能性を評価しなければならない（MUST）
   - リファクタリング計画を立案し、ユーザー承認を取得しなければならない（MUST）

4. **ドキュメント駆動DRY原則**
   - 仕様書レベルでの重複を検出しなければならない（MUST）
   - 設計段階での共通化を検討すべきである（SHOULD）
   - アーキテクチャレビューを実施すべきである（SHOULD）

**実施プロトコル**:

実装前チェックリスト:
- ☐ 類似機能の既存実装を検索したか？
- ☐ 共通化可能なパターンを特定したか？
- ☐ DRY原則に違反していないか？
- ☐ ドキュメントで重複仕様を確認したか？

**理由**: コードの保守性を向上させ、バグの混入リスクを低減

### Article 11: Refactoring Policy

既存のコードに問題がある場合、新しいバージョンを作成するのではなく、
既存のコードを直接修正しなければならない（MUST）。

**必須要件**:

1. **既存クラス修正優先**
   - V2、V3などのバージョン付きクラス作成を禁止する（MUST NOT）
   - 既存クラスの直接修正を優先しなければならない（MUST）
   - 後方互換性よりも設計の正しさを優先しなければならない（MUST）

2. **破壊的変更の推奨条件**
   - アーキテクチャが改善される場合（SHOULD）
   - 技術的負債を解消できる場合（SHOULD）
   - 長期的な保守性が向上する場合（SHOULD）
   - コードの一貫性が保たれる場合（SHOULD）

3. **リファクタリング前チェックリスト**
   - 影響範囲を特定しなければならない（MUST）（依存関係の分析）
   - テストカバレッジを確認しなければならない（MUST）（既存テストの実行）
   - 段階的移行計画を立案すべきである（SHOULD）（必要な場合）
   - ドキュメントの更新計画を立案しなければならない（MUST）

**実施プロトコル**:
- **V2クラス作成禁止**: 既存クラスが不適切な場合でも、V2を作らず既存を修正する
- **破壊的変更の実施**: テストを維持しながら既存実装を書き換える
- **移行期間の設定**: 大規模変更の場合は段階的移行計画を立案する

**理由**: 技術的負債の蓄積を防ぎ、コードベースの一貫性と品質を維持

## Project Standards

### Article 12: Documentation Standards

すべてのドキュメントは、統一された場所と形式で管理しなければならない（MUST）。

**必須要件**:

1. **ドキュメント配置**
   - `docs/` ディレクトリ配下でドキュメントを一元管理しなければならない（MUST）
   - プロジェクトルートからの一貫したパス構造を維持しなければならない（MUST）

2. **ドキュメント構成**
   - 機能毎にドキュメントを作成しなければならない（MUST）
   - 1つの機能に対して1つのドキュメントファイルを対応させなければならない（MUST）
   - ドキュメント名は対象機能を明確に反映させなければならない（MUST）

3. **フォーマット**
   - ドキュメントのフォーマットはMarkdownを使用しなければならない（MUST）
   - 拡張子は `.md` を使用しなければならない（MUST）
   - MyST（Markedly Structured Text）構文に準拠しなければならない（MUST）（Sphinx連携時）

**理由**: ドキュメントの一元管理により、検索性、保守性、一貫性を保証

### Article 13: Environment & Infrastructure

すべての開発環境は、再現可能で一貫性のある方法で構築しなければならない（MUST）。

**必須要件**:

1. **コンテナ化の徹底**
   - すべての環境をDockerで構築しなければならない（MUST）
   - ホスト環境への依存を排除しなければならない（MUST）
   - 完全な再現性を保証しなければならない（MUST）

2. **Dockerfile管理**
   - `dockerfiles/` ディレクトリ配下で一元管理しなければならない（MUST）
   - アプリケーション毎にサブディレクトリを作成しなければならない（MUST）
   - 構造: `dockerfiles/<application>/Dockerfile`
   - 例: `dockerfiles/dev/Dockerfile`, `dockerfiles/prod/Dockerfile`

3. **コマンド管理**
   - build、run等の主要コマンドはMakefileに集約しなければならない（MUST）
   - 複雑なDockerコマンドを隠蔽しなければならない（MUST）
   - 一貫したインターフェースを提供しなければならない（MUST）

4. **開発環境**
   - 開発はdevコンテナで実施しなければならない（MUST）
   - 本番環境との明確な分離を維持しなければならない（MUST）
   - 開発ツール・デバッガを統合すべきである（SHOULD）

5. **ビルド最適化**
   - テストコードはリリース向けDockerfileに含めてはならない（MUST NOT）
   - 本番イメージのサイズを最小化すべきである（SHOULD）
   - セキュリティリスクを低減しなければならない（MUST）

**理由**: 環境の標準化により、「私の環境では動く」問題を排除し、チーム全体の生産性を向上

### Article 14: SpecKit Framework Consistency

**これは非交渉的である**: すべてのSpecKitコマンドは、`specs/001-specs`ディレクトリと整合性を保たなければならない（MUST）。
フレームワークの一貫性を損なういかなる実装も許可しない。

**必須要件**:

1. **MixSeek-Core仕様参照必須**
   - すべてのSpecKitコマンド（speckit.analyze、speckit.plan、speckit.tasks等）はspecs/001-specsを参照しなければならない（MUST）
   - 実行時にMixSeek-Coreアーキテクチャとの整合性を検証しなければならない（MUST）
   - 仕様との矛盾を検出した場合は実行を停止し、明確な理由を報告しなければならない（MUST）

2. **アーキテクチャ整合性検証**
   - Leader Agent、Member Agent、Round Controller、Evaluatorの関係性がMixSeek-Core仕様に準拠しているか確認しなければならない（MUST）
   - TUMIXアルゴリズムの実装要件に従っているか検証しなければならない（MUST）
   - マルチチーム競合メカニズムが仕様通りに設計されているか確認しなければならない（MUST）

3. **仕様逸脱時の処理**
   - MixSeek-Core仕様からの逸脱が検出された場合、実装を停止しなければならない（MUST）
   - 逸脱の理由と影響を明確に文書化しなければならない（MUST）
   - ユーザーに明示的な承認を求め、承認なしには実装を継続してはならない（MUST NOT）

4. **SpecKitコマンド実装基準**
   - 各SpecKitコマンドはMixSeek-Core仕様の該当セクションを明確に参照しなければならない（MUST）
   - フレームワーク要素（Team、Agent、Round等）の定義は仕様と一致していなければならない（MUST）
   - 機能要件（FR-001からFR-019）との整合性を常に確認しなければならない（MUST）

**実施プロトコル**:
- **仕様参照チェック**: 各SpecKitコマンド実行前にspecs/001-specs/spec.mdを読み込み、関連要件を確認する
- **整合性検証**: 実装中に仕様との矛盾を検出した場合は即座に停止し、ユーザーに報告する
- **文書化**: 仕様逸脱の理由、影響、対応策を明確に記録する

**理由**: MixSeek-Core多エージェントフレームワークの設計整合性を保護し、システム全体の一貫性と品質を保証

### Article 15: SpecKit Naming Convention

すべてのSpecKitで生成されるディレクトリとブランチ名は、標準化された命名規則に従わなければならない（MUST）。
一貫性のない命名は、プロジェクトの可読性と保守性を著しく損なう。

**必須要件**:

1. **命名規則の強制**
   - `speckit.specify`コマンドで生成されるディレクトリ名は`<issue-number>-<name>`形式でなければならない（MUST）
   - 対応するGitブランチ名も同一の命名規則に従わなければならない（MUST）
   - `<issue-number>`は3桁ゼロパディング形式（001、002、003...）を使用しなければならない（MUST）
   - `<name>`は機能を表す簡潔な英語名（ハイフン区切り）でなければならない（MUST）
   - プロジェクトプレフィックス（例: `mixseek-core-`）は不要である（SHOULD NOT use）

2. **命名例**
   - 標準例: `002-config`, `003-dockerfiles`, `004-command`（簡潔で明確）
   - 禁止例: `auth-feature`, `evaluation-system`（番号なし）

3. **自動生成の保証**
   - `.specify/scripts/bash/create-new-feature.sh`スクリプトは命名規則を自動適用しなければならない（MUST）
   - スクリプト経由での統一的な生成を推奨する（SHOULD）
   - 既存の番号付けシステムとの連続性を保持しなければならない（MUST）

4. **一意性の保証**
   - 同一番号の重複使用を防止しなければならない（MUST）
   - 既存ディレクトリとの名前衝突を回避しなければならない（MUST）
   - 番号の自動インクリメントにより一意性を保証しなければならない（MUST）

**実施プロトコル**:
- **既存確認**: 新規作成前に既存のディレクトリ番号を確認し、次の番号を自動決定する
- **検証**: 生成されたディレクトリ名とブランチ名が`<issue-number>-<name>`形式に準拠していることを確認する

**理由**: MixSeek-Coreプロジェクトの機能追加における一貫性と識別性を保証し、開発チーム全体の効率性と可読性を向上させる

### Article 16: Python Type Safety Mandate

**これは非交渉的である**: すべてのPythonコードは、包括的な型注釈と静的型チェックを必須とする（MUST）。
型安全性を犠牲にしたコードは一切許可しない。

**必須要件**:

1. **型注釈の強制**
   - すべての関数・メソッドの引数に型注釈を付与しなければならない（MUST）
   - すべての関数・メソッドの戻り値に型注釈を付与しなければならない（MUST）
   - クラス属性・インスタンス変数に型注釈を付与しなければならない（MUST）
   - グローバル変数・モジュール変数に型注釈を付与しなければならない（MUST）

2. **mypy静的型チェック必須**
   - すべてのPythonファイルでmypy型チェックを実行しなければならない（MUST）
   - mypy.iniで`strict = True`設定を使用しなければならない（MUST）
   - 型チェックエラーが存在する状態でのコミットを禁止する（MUST NOT）
   - `# type: ignore`コメントの使用を最小限に抑えなければならない（MUST）

3. **型注釈品質基準**
   - `Any`型の使用を避け、具体的な型を指定しなければならない（MUST）
   - `Union`より`|`構文（Python 3.10+）を優先すべきである（SHOULD）
   - `Optional`より`| None`構文を優先すべきである（SHOULD）
   - 型エイリアスを適切に使用して複雑な型を簡潔に表現すべきである（SHOULD）

4. **型安全性パターン**
   - 型ガードを使用してランタイム型安全性を確保しなければならない（MUST）
   - Protocol使用時は構造的サブタイピングを適切に実装しなければならない（MUST）
   - Generic使用時は型パラメータを適切に制約しなければならない（MUST）
   - NewType使用で型安全性を向上させるべきである（SHOULD）

**実装例**:

```python
# 良い例（推奨）
from decimal import Decimal
from typing import Protocol

# Note: Item はプレースホルダー。実際のプロジェクトでは適切な型定義が必要
def calculate_total(items: list[Item], tax_rate: float) -> Decimal:
    """商品リストの税込み合計を計算する"""
    total = sum(item.price for item in items)
    return total * (1 + tax_rate)

class Drawable(Protocol):
    def draw(self) -> None: ...

# 悪い例（禁止）
def calculate_total(items, tax_rate):  # 型注釈なし
    return items[0] + tax_rate  # 型安全でない操作

def process_data(data: Any) -> Any:  # Any型の多用
    return data
```

**実施プロトコル**:
- **開発環境設定**: mypy.iniでstrict設定を有効化する
- **エディタ統合**: IDE/エディタでmypyリアルタイム型チェックを設定する
- **コミット前チェック**: 型チェックエラーゼロを確認してからコミットする
- **CI/CD統合**: 型チェック失敗時はビルドを停止する

**理由**: 静的型チェックによりバグの早期発見、コード可読性向上、リファクタリング安全性を保証し、
Python開発の品質と保守性を大幅に改善する

### Article 17: Python Docstring Standards

すべてのPythonコードには、Google-styleのdocstring形式による包括的なドキュメントを強く推奨する（SHOULD）。
高品質なドキュメントはコード品質と保守性を大幅に向上させる。

**推奨要件**:

1. **Docstring推奨対象**
   - すべてのpublicモジュールにmodule-level docstringを記述すべきである（SHOULD）
   - すべてのpublic関数・メソッドにdocstringを記述すべきである（SHOULD）
   - すべてのpublicクラスにclass-level docstringを記述すべきである（SHOULD）
   - 複雑なprivate関数（10行以上）にもdocstringを記述すべきである（SHOULD）

2. **Google-style形式推奨**
   - docstringはGoogle-style形式に従うべきである（SHOULD）
   - セクション見出し（Args、Returns、Raises等）は正確なスペルと書式を使用すべきである（SHOULD）
   - インデントは一貫して4スペースを使用すべきである（SHOULD）
   - 一行目は簡潔な概要（動詞で開始）であるべきである（SHOULD）

3. **内容推奨事項**
   - 関数の目的と動作を明確に説明すべきである（SHOULD）
   - すべてのパラメータを`Args:`セクションで説明すべきである（SHOULD）
   - 戻り値を`Returns:`セクションで説明すべきである（SHOULD）（void以外）
   - 発生する可能性のある例外を`Raises:`セクションで説明すべきである（SHOULD）
   - 使用例を`Example:`セクションで提供すべきである（SHOULD）

4. **品質ガイドライン**
   - 型注釈と矛盾する記述は避けるべきである（SHOULD）
   - 実装詳細ではなく、インターフェースの説明に焦点を当てるべきである（SHOULD）
   - 曖昧な表現や技術用語の説明なしの使用は避けるべきである（SHOULD）
   - 日本語コメント内での英語docstringを使用する場合は、一貫性を保つべきである（SHOULD）

**実装例**:

```python
# 良い例（推奨）
from decimal import Decimal

def calculate_tax_amount(price: Decimal, tax_rate: float, region: str) -> Decimal:
    """指定された価格と税率から税額を計算する。

    地域別の税制ルールを適用して、正確な税額を算出します。
    消費税、地方税、特別税を考慮した計算を行います。

    Args:
        price: 税抜き価格（正の数値である必要があります）
        tax_rate: 税率（0.0-1.0の範囲）
        region: 地域コード（'JP', 'US', 'EU'のいずれか）

    Returns:
        計算された税額（小数点以下第2位まで）

    Raises:
        ValueError: 価格が負の値または税率が範囲外の場合
        KeyError: 対応していない地域コードが指定された場合

    Example:
        >>> calculate_tax_amount(Decimal('1000'), 0.10, 'JP')
        Decimal('100.00')
    """
    if price < 0:
        raise ValueError("価格は正の値である必要があります")
    # 実装...

class DataProcessor:
    """データ処理を行うためのクラス。

    様々な形式のデータを統一的に処理し、変換・検証・出力を行います。
    バッチ処理とリアルタイム処理の両方をサポートしています。

    Attributes:
        batch_size: バッチ処理時の一回あたりの処理件数
        timeout: 処理タイムアウト（秒）
    """

# 改善推奨例
def calc(p, r):  # docstringなし → docstring追加を推奨
    return p * r

def process_data(data):
    """データを処理する"""  # 曖昧で不完全 → 詳細説明を推奨
    return data

def complex_calculation(x, y, z):
    """
    Calculates something complex
    x: number
    y: another number
    """  # Google形式でない、不完全 → 標準形式を推奨
```

**実施プロトコル**:
- **開発環境設定**: pydocstyleやdarglintツールの統合を推奨し、docstring品質の向上を支援する
- **エディタ統合**: IDE/エディタでdocstring自動生成とリアルタイム検証の設定を推奨する
- **品質向上**: docstring品質の改善を継続的に推奨するが、必須ではない
- **CI/CD推奨**: docstring品質チェックの統合を推奨するが、ビルド失敗は強制しない

**理由**: 統一されたドキュメント形式により、コードの理解性、保守性、新規参加者のオンボーディング効率を大幅に向上させ、
チーム全体の開発生産性と品質を保証する

## Governance

### Amendment Procedure

この憲法の改正は、以下のプロセスに従わなければならない（MUST）:

1. **改正提案**: 文書化された改正案を作成し、変更理由を明記する
2. **影響分析**: 依存テンプレート（plan.md、spec.md、tasks.md）への影響を評価する
3. **承認**: プロジェクトオーナーまたは指定された承認者の承認を取得する
4. **移行計画**: 既存コードへの影響がある場合、段階的移行計画を立案する
5. **バージョン更新**: セマンティックバージョニングに従ってバージョンを更新する

### Versioning Policy

憲法のバージョンは、セマンティックバージョニング（MAJOR.MINOR.PATCH）に従う:

- **MAJOR**: 後方互換性のないガバナンス/原則の削除または再定義
- **MINOR**: 新しい原則/セクションの追加または重要な拡張ガイダンス
- **PATCH**: 明確化、文言修正、誤字修正、非セマンティックな改善

### Compliance Review

すべてのプルリクエストとコードレビューは、この憲法への準拠を検証しなければならない（MUST）。

**必須チェック項目**:
- テストファーストが遵守されているか（Article 3）
- ドキュメントとの整合性が保たれているか（Article 4）
- コード品質基準に準拠しているか（Article 8）
- DRY原則に違反していないか（Article 10）
- Python型安全性基準を満たしているか（Article 16）

**推奨チェック項目**:
- Python docstring標準が適用されているか（Article 17）

**複雑性の正当化**: 憲法の原則に違反する複雑性は、明確に正当化されなければならない（MUST）。

**ランタイムガイダンス**: AI開発支援のランタイムガイダンスは、以下のファイルで管理される:
- `CLAUDE.md`（プロジェクトルート）- Claude Code用ガイダンス
- `.claude/CLAUDE.md`（ユーザーグローバル設定）- Claude Code用グローバル設定
- `AGENTS.md`（プロジェクトルート）- 汎用AIエージェント用ガイダンス
- `GEMINI.md`（プロジェクトルート）- Google Gemini用ガイダンス

### Application Principles

この憲法のすべてのArticleは、以下の原則に基づいて適用される:

1. **非交渉的遵守**: 「これは非交渉的である」と明記されたArticleは、いかなる理由があっても例外を認めない
2. **優先順位**: Articleの番号順ではなく、プロジェクトの目的に応じて適切に適用する
3. **相互補完**: Development PatternsとQuality Assuranceは、相互に補完し合う関係にある
4. **継続的改善**: この憲法自体も、プロジェクトの成長に合わせて進化させる

---

**Version**: 1.5.2 | **Ratified**: 2025-10-14 | **Last Amended**: 2025-12-02