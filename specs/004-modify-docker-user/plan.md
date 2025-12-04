# 実装計画: macOS 互換性のための Docker ビルドユーザー設定

**Branch**: `003-mixseek-core-modify-docker-user` | **Date**: 2025-10-17 | **Spec**: [spec.md](./spec.md)
**Input**: 機能仕様から `/specs/004-modify-docker-user/spec.md`

## 概要

この機能は、ログインユーザーの ID の自動使用を、設定可能な環境変数に置き換えることで、macOS の GID 競合エラーを排除するように Docker ビルドシステムを変更します。システムは、安全な値（UID/GID 1000 の mixseek_core ユーザー）をデフォルトとし、MIXSEEK_USERNAME、MIXSEEK_UID、MIXSEEK_GID 環境変数を通じてカスタマイズを許可します。バリデーションは完全に削除され、Docker 実行時エラーに依存します。

## 技術コンテキスト

**Language/Version**: Shell (Bash), Make (GNU Make 3.8+), Docker (Docker Engine 20.10+)
**Primary Dependencies**: Docker, Make, 既存の Makefile.common インフラストラクチャ
**Storage**: N/A (設定のみ)
**Testing**: macOS、Linux、CI/CD 環境での手動テスト
**Target Platform**: 開発環境 (macOS、Linux、Docker 付き Windows)、CI/CD パイプライン
**Project Type**: ビルドシステム設定 (インフラストラクチャ)
**Performance Goals**: N/A (パフォーマンスへの影響なし)
**Constraints**: 既存の Dockerfile との後方互換性を維持、Linux ビルドを壊さない
**Scale/Scope**: すべての環境（dev、ci、prod）にわたるすべての Docker ビルド操作に影響

## 憲法チェック

*GATE: Phase 0 リサーチ前に合格する必要があります。Phase 1 設計後に再チェック。*

### Article 1: ライブラリ優先原則
**Status**: ✅ N/A - これはインフラストラクチャ設定であり、アプリケーションコードではありません

### Article 2: CLI インターフェース義務
**Status**: ✅ PASS - Makefile ターゲットが CLI インターフェースを提供（make build、make validate-build-args）

### Article 3: テストファースト命令
**Status**: ⚠️ ADAPTED - Docker ビルドは実際の macOS/Linux 環境を必要とし、ユニットテストでは完全に自動化できません

**正当化**: Docker ビルドテストには実際の macOS/Linux 環境が必要であり、ユニットテストでは完全に自動化できません。バリデーションロジックはなくなり、手動テストのみが必要です。

### Article 4: ドキュメント整合性
**Status**: ✅ PASS - 実装は spec.md 要件に従う; ドキュメント更新 (FR-007) が計画に含まれる

### Article 5: シンプルさ
**Status**: ✅ PASS - 変更は既存の Makefile.common に限定され、新しいプロジェクトは不要

### Article 6: 抽象化禁止
**Status**: ✅ PASS - Make の組み込み変数置換を使用し、不必要なラッパーなし

### Article 7: 統合優先テスト
**Status**: ✅ PASS - テスト戦略には複数のプラットフォームでの実際の Docker ビルドが含まれます

### Article 8: コード品質基準
**Status**: ✅ PASS - Makefile 構文が検証されます

### Article 9: データ精度義務
**Status**: ✅ PASS - すべてのデフォルト値が明示的に定義され、マジックナンバーなし

### Article 10: DRY 原則
**Status**: ✅ PASS - Makefile.common での集中化された変数定義

### Article 11: リファクタリングポリシー
**Status**: ✅ PASS - 既存の Makefile.common を直接変更（V2 作成なし）

### Article 12: ドキュメント基準
**Status**: ✅ PASS - docs/ ディレクトリでのドキュメント更新

### Article 13: 環境とインフラストラクチャ
**Status**: ✅ PASS - この機能は Docker 環境の再現性を強化

### Article 14: SpecKit フレームワーク一貫性
**Status**: ✅ PASS - これはインフラストラクチャ修正であり、MixSeek-Core フレームワーク機能ではありません; フレームワーク依存関係なし

### Article 15: SpecKit 命名規則
**Status**: ✅ PASS - ディレクトリは `003-mixseek-core-modify-docker-user` 命名規則に従います

**全体的なゲートステータス**: ✅ PASS（1つの適応：Article 3 - インフラストラクチャに適したテスト戦略）

## プロジェクト構造

### ドキュメント（この機能）

```
specs/004-modify-docker-user/
├── plan.md              # このファイル
├── research.md          # Make 変数置換パターン、Docker ARG/ENV ベストプラクティス
├── data-model.md        # ビルド環境設定エンティティ
├── quickstart.md        # 環境変数設定のユーザーガイド
├── checklists/
│   └── requirements.md  # 仕様検証チェックリスト
└── assets/
    └── prompt.md        # 元の問題説明
```

### ソースコード（リポジトリルート）

```
dockerfiles/
├── Makefile.common      # 変更: デフォルトの変数定義
├── dev/
│   ├── Makefile         # Makefile.common の変数を使用
│   └── Dockerfile       # build args を使用（変更不要）
├── ci/
│   ├── Makefile
│   └── Dockerfile
└── prod/
    ├── Makefile
    └── Dockerfile

docs/
└── docker-setup.md      # 変更: 環境変数ドキュメントの追加
```

**構造決定**: この機能は、新しいソースコードを作成するのではなく、既存のビルドインフラストラクチャファイルを変更します。変更は `dockerfiles/Makefile.common` に集中され、すべての環境（dev、ci、prod）で一貫性が確保されます。

## 複雑性追跡

*違反なし - すべての憲法チェックに合格または適切に適応*

## Phase 0: 調査

### 調査トピック

1. **Make 変数デフォルト値**
   - パターン: `VAR ?= default` vs `VAR := $(or $(VAR),default)`
   - 環境変数オーバーライドのベストプラクティス
   - 空 vs 未定義変数の処理

2. **Docker Build ARG ベストプラクティス**
   - Make から Docker への build 引数の渡し方
   - Dockerfile での ARG vs ENV
   - groupadd/useradd 前の ARG 値の検証（注: バリデーション削除により不要）

3. **macOS vs Linux UID/GID の違い**
   - 一般的な macOS ユーザー GID (20 = staff)
   - 一般的な Linux ユーザー GID (1000 = 最初のユーザー)
   - GID 1000 が両方のプラットフォームで安全な理由

**出力**: 調査結果と決定を文書化した research.md

## Phase 1: 設計とコントラクト

### データモデル

**エンティティ**: ビルド環境設定

```
ビルド環境設定:
  - MIXSEEK_USERNAME: string (default: "mixseek_core")
  - MIXSEEK_UID: integer (default: 1000)
  - MIXSEEK_GID: integer (default: 1000)

バリデーションルール: なし（バリデーションは Docker 実行時エラーに依存）
```

### 実装コンポーネント

1. **Makefile.common の変更**
   ```makefile
   # 現在の実装（置き換え予定）:
   MIXSEEK_USERNAME := $(shell whoami)
   MIXSEEK_UID := $(shell id -u)
   MIXSEEK_GID := $(shell id -g)

   # 新しい実装:
   MIXSEEK_USERNAME ?= mixseek_core
   MIXSEEK_UID ?= 1000
   MIXSEEK_GID ?= 1000
   ```

2. **バリデーション関数の簡素化**
   ```makefile
   define validate_build_args
       @echo "✅ ビルド引数が設定されました"
       @echo "   MIXSEEK_USERNAME: $(MIXSEEK_USERNAME)"
       @echo "   MIXSEEK_UID: $(MIXSEEK_UID)"
       @echo "   MIXSEEK_GID: $(MIXSEEK_GID)"
   endef
   ```

3. **ドキュメント更新**
   - `docs/docker-setup.md` を環境変数の使用例で更新
   - 一般的な UID/GID 競合のトラブルシューティングセクションを追加
   - デフォルト値といつオーバーライドするかを文書化

### テスト戦略

**テストシナリオ**（spec.md エッジケースごと）:

1. **デフォルト値テスト** (FR-004)
   - すべての MIXSEEK_* 変数を未設定にする
   - `make validate-build-args` を実行
   - 確認: username=mixseek_core、UID=1000、GID=1000

2. **カスタム値テスト** (FR-001、FR-002、FR-003)
   - カスタム MIXSEEK_USERNAME、MIXSEEK_UID、MIXSEEK_GID を設定
   - `make validate-build-args` を実行
   - 確認: カスタム値を使用

3. **macOS ビルドテスト** (SC-001)
   - デフォルト値で macOS でフルビルドを実行
   - 確認: GID 関連エラーなしでビルドが完了

4. **クロスプラットフォーム一貫性テスト** (SC-003)
   - macOS と Linux で同じカスタム値でビルド
   - 確認: 同一のコンテナユーザー設定

### コントラクト

**Makefile インターフェースコントラクト**:

```makefile
# 入力: 環境変数（オプション）
#   MIXSEEK_USERNAME - コンテナユーザー名（デフォルト: mixseek_core）
#   MIXSEEK_UID - コンテナユーザー ID（デフォルト: 1000）
#   MIXSEEK_GID - コンテナグループ ID（デフォルト: 1000）

# ターゲット:
#   validate-build-args - 解決された値を表示
#   build - 検証済みユーザー設定で Docker イメージをビルド

# 出力:
#   BUILD_ARGS - docker build コマンドに渡される
#   コンソール出力 - 検証成功/失敗と明確なメッセージ

# エラーハンドリング:
#   - バリデーションなし - すべてのエラーは Docker 実行時に発生
```

**出力**: data-model.md、quickstart.md

## Phase 2: タスク生成

*このフェーズは `/speckit.tasks` コマンドによって処理され、この計画出力の一部ではありません。*

tasks.md ファイルは、実装を TDD ワークフローに従う特定のテスト可能なタスクに分解します:
1. Makefile.common の変更を実装
2. ドキュメントの更新
3. クロスプラットフォーム互換性の検証

## 次のステップ

1. Phase 0 を実行: 調査エージェントを実行して Make パターンを文書化
2. Phase 1 を実行: data-model.md と quickstart.md を作成
3. この計画情報でエージェントコンテキストを更新
4. `/speckit.tasks` に進み、実行可能な実装タスクを生成
