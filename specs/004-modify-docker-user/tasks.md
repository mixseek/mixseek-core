# Tasks: macOS 互換性のための Docker ビルドユーザー設定

**Input**: 設計ドキュメント `/specs/004-modify-docker-user/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md

**テスト戦略**: この機能は手動テストのみです。TDD は適用されません（理由: Article 3 - Docker ビルドテストには実際の macOS/Linux 環境が必要）

**組織**: タスクはユーザーストーリー別にグループ化され、各ストーリーの独立した実装とテストを可能にします。

## フォーマット: `[ID] [P?] [Story] 説明`
- **[P]**: 並列実行可能（異なるファイル、依存関係なし）
- **[Story]**: このタスクが属するユーザーストーリー（US1、US2、US3）
- 説明には正確なファイルパスを含める

## パス規則
- **リポジトリルート**: `dockerfiles/`（Makefile とビルドスクリプト）
- **ドキュメント**: `docs/`（ユーザー向けドキュメント）

---

## Phase 1: Setup（共有インフラストラクチャ）

**目的**: 既存ファイルの確認とバックアップ

- [ ] T001 既存の Makefile.common のバックアップを作成（`dockerfiles/Makefile.common.bak`）
- [ ] T002 [P] 既存の Dockerfile を確認し、MIXSEEK_* ARG の使用状況を把握

**Checkpoint**: 既存の実装を理解し、変更の影響範囲を確認完了

---

## Phase 2: Foundational（ブロッキング前提条件）

**目的**: すべてのユーザーストーリーが依存するコア変更

**⚠️ CRITICAL**: このフェーズが完了するまで、ユーザーストーリーの作業は開始できません

- [ ] T003 Makefile.common の変数定義を更新（`dockerfiles/Makefile.common` 行 23-25）
  - 現在: `MIXSEEK_USERNAME := $(shell whoami)`
  - 新規: `MIXSEEK_USERNAME ?= mixseek_core`
  - 現在: `MIXSEEK_UID := $(shell id -u)`
  - 新規: `MIXSEEK_UID ?= 1000`
  - 現在: `MIXSEEK_GID := $(shell id -g)`
  - 新規: `MIXSEEK_GID ?= 1000`

- [ ] T004 validate_build_args 関数を簡素化（`dockerfiles/Makefile.common` 行 50-54）
  - バリデーションロジックを削除
  - 値の表示のみに変更（"✅ ビルド引数が設定されました" + 3つの変数値）

**Checkpoint**: 基盤準備完了 - ユーザーストーリーの実装を並列開始可能

---

## Phase 3: User Story 1 - macOS で GID 競合なしに Docker イメージをビルド（優先度: P1）🎯 MVP

**目標**: macOS 開発者がデフォルト設定で GID 競合エラーなしに Docker イメージをビルドできるようにする

**独立したテスト**: macOS で `make -C dockerfiles/dev build` を実行し、GID 関連エラーなしでビルドが正常に完了することを確認

### User Story 1 の実装

- [ ] T005 [US1] macOS で環境変数を設定せずにデフォルトビルドをテスト
  - 実行: `unset MIXSEEK_USERNAME MIXSEEK_UID MIXSEEK_GID && make -C dockerfiles/dev validate-build-args`
  - 期待: username=mixseek_core、UID=1000、GID=1000 が表示される

- [ ] T006 [US1] macOS でデフォルト値を使用したフルビルドをテスト
  - 実行: `make -C dockerfiles/dev build`
  - 期待: GID 20 競合エラーなしでビルドが成功

- [ ] T007 [US1] ビルドされたイメージでコンテナユーザーを確認
  - 実行: `docker run --rm <image> id`
  - 期待: uid=1000(mixseek_core) gid=1000(mixseek_core)

**Checkpoint**: この時点で、User Story 1 は完全に機能し、独立してテスト可能

---

## Phase 4: User Story 2 - 環境間で一貫したビルドユーザー設定（優先度: P2）

**目標**: 異なるプラットフォーム（Linux、macOS、Windows）および CI/CD 環境間で一貫したユーザー設定を保証

**独立したテスト**: 複数のプラットフォームで同じイメージをビルドし、コンテナユーザー設定が期待通りであることを確認

### User Story 2 の実装

- [ ] T008 [US2] Linux でデフォルトビルドをテスト
  - 実行: Linux マシンまたは CI で `make -C dockerfiles/ci build`
  - 期待: username=mixseek_core、UID=1000、GID=1000

- [ ] T009 [US2] macOS と Linux で同じイメージをビルドし、ユーザー設定を比較
  - macOS: `make -C dockerfiles/dev build && docker run --rm <image> id > macos_id.txt`
  - Linux: `make -C dockerfiles/ci build && docker run --rm <image> id > linux_id.txt`
  - 比較: `diff macos_id.txt linux_id.txt` → 差分なし

- [ ] T010 [US2] CI/CD パイプラインで環境変数を設定してビルドをテスト
  - 環境変数設定例を `docs/docker-setup.md` に追加（GitHub Actions、GitLab CI、Jenkins の例）
  - CI で環境変数を設定: `MIXSEEK_USERNAME=ci_user MIXSEEK_UID=1100 MIXSEEK_GID=1100`
  - 実行: `make -C dockerfiles/ci build`
  - 期待: CI 指定の値を使用

**Checkpoint**: この時点で、User Story 1 と 2 の両方が独立して動作

---

## Phase 5: User Story 3 - 特殊要件のためのデフォルトユーザー設定の上書き（優先度: P3）

**目標**: 特定のセキュリティや組織要件を持つユーザーがカスタムユーザー ID で Docker イメージを作成できるようにする

**独立したテスト**: カスタム MIXSEEK_USERNAME、MIXSEEK_UID、MIXSEEK_GID 値を設定し、コンテナがこれらの正確な認証情報で実行されることを確認

### User Story 3 の実装

- [ ] T011 [US3] カスタム環境変数でビルドをテスト
  - 設定: `export MIXSEEK_USERNAME=custom_user MIXSEEK_UID=5000 MIXSEEK_GID=5000`
  - 実行: `make -C dockerfiles/dev build`
  - 確認: `docker run --rm <image> id` → uid=5000(custom_user) gid=5000(custom_user)

- [ ] T012 [US3] 一部の変数のみ設定した場合のテスト
  - 設定: `export MIXSEEK_UID=2000` （他は未設定）
  - 実行: `make -C dockerfiles/dev validate-build-args`
  - 期待: UID=2000、USERNAME=mixseek_core、GID=1000（デフォルト使用）

- [ ] T013 [US3] 無効な値でのエラーハンドリングをテスト（Docker ビルド時）
  - 設定: `export MIXSEEK_UID=abc` （非数値）
  - 実行: `make -C dockerfiles/dev build`
  - 期待: Docker ビルドエラー "groupadd: invalid group ID 'abc'"

**Checkpoint**: すべてのユーザーストーリーが独立して機能

---

## Phase 6: ドキュメントと Polish

**目的**: すべてのユーザーストーリーに影響するドキュメントと改善

- [ ] T014 [P] docs/docker-setup.md を作成または更新
  - 環境変数の説明（MIXSEEK_USERNAME、MIXSEEK_UID、MIXSEEK_GID）
  - デフォルト値の説明（mixseek_core、1000、1000）
  - macOS ユーザー向けの使用例（デフォルト推奨）
  - Linux ユーザー向けの使用例
  - CI/CD 設定例（GitHub Actions、GitLab CI、Jenkins）
  - トラブルシューティング（GID 20 競合、無効な値エラー）

- [ ] T015 [P] README.md または CLAUDE.md を更新
  - Docker ビルドのクイックスタートセクションに環境変数の説明を追加
  - macOS ユーザー向けの注意事項を追加

- [ ] T016 Makefile.common のコメントを更新
  - 行 21-26 のコメントを更新：「Host environment information」を「Configurable build user settings」に変更
  - デフォルト値の説明を追加
  - 環境変数でオーバーライド可能であることを明記

- [ ] T017 すべての環境（dev、ci、prod）で validate-build-args ターゲットをテスト
  - `make -C dockerfiles/dev validate-build-args`
  - `make -C dockerfiles/ci validate-build-args`
  - `make -C dockerfiles/prod validate-build-args`
  - 期待: すべてで同じデフォルト値が表示される

- [ ] T018 クロスプラットフォーム互換性の最終確認
  - macOS でビルド → Linux でビルド → 両方のイメージを比較
  - 異なる環境変数設定でテスト → 期待通りの動作を確認

**Checkpoint**: ドキュメント完成、すべてのプラットフォームで動作確認完了

---

## 依存関係と実行順序

### Phase 依存関係

- **Setup（Phase 1）**: 依存関係なし - すぐに開始可能
- **Foundational（Phase 2）**: Setup 完了に依存 - すべてのユーザーストーリーをブロック
- **User Stories（Phase 3-5）**: すべて Foundational フェーズ完了に依存
  - ユーザーストーリーはその後並列実行可能（スタッフがいる場合）
  - または優先順位順に順次実行（P1 → P2 → P3）
- **ドキュメントと Polish（Phase 6）**: すべての希望するユーザーストーリーの完了に依存

### User Story 依存関係

- **User Story 1（P1）**: Foundational（Phase 2）後に開始可能 - 他のストーリーへの依存関係なし
- **User Story 2（P2）**: Foundational（Phase 2）後に開始可能 - US1 と統合する可能性があるが、独立してテスト可能
- **User Story 3（P3）**: Foundational（Phase 2）後に開始可能 - US1/US2 と統合する可能性があるが、独立してテスト可能

### 各 User Story 内

- Foundational の変更が完了するまで実装開始不可
- 手動テストは実装後に実行
- ストーリー完了後、次の優先度に移動

### 並列実行の機会

- Phase 1 の すべての Setup タスクは並列実行可能
- Phase 2 完了後、すべてのユーザーストーリーは並列開始可能（チーム人員がいる場合）
- Phase 6 のドキュメントタスク（T014、T015）は並列実行可能
- 異なるユーザーストーリーは異なるチームメンバーが並列作業可能

---

## 並列実行例: Foundational 完了後

```bash
# Foundational（Phase 2）完了後、すべてのユーザーストーリーテストを並列実行可能:

# 並列実行グループ 1: 各ストーリーのテスト
Task: "T005 [US1] macOS でデフォルトビルドをテスト"
Task: "T008 [US2] Linux でデフォルトビルドをテスト"
Task: "T011 [US3] カスタム環境変数でビルドをテスト"

# 並列実行グループ 2: ドキュメント
Task: "T014 [P] docs/docker-setup.md を作成または更新"
Task: "T015 [P] README.md または CLAUDE.md を更新"
```

---

## 実装戦略

### MVP First（User Story 1 のみ）

1. Phase 1: Setup を完了
2. Phase 2: Foundational を完了（CRITICAL - すべてのストーリーをブロック）
3. Phase 3: User Story 1 を完了
4. **STOP and VALIDATE**: User Story 1 を独立してテスト
5. 準備ができていればデプロイ/デモ

### 段階的デリバリー

1. Setup + Foundational を完了 → 基盤準備完了
2. User Story 1 を追加 → 独立してテスト → デプロイ/デモ（MVP！）
3. User Story 2 を追加 → 独立してテスト → デプロイ/デモ
4. User Story 3 を追加 → 独立してテスト → デプロイ/デモ
5. 各ストーリーが前のストーリーを壊すことなく価値を追加

### 並列チーム戦略

複数の開発者がいる場合:

1. チームで Setup + Foundational を一緒に完了
2. Foundational 完了後:
   - Developer A: User Story 1（macOS テスト）
   - Developer B: User Story 2（Linux + CI/CD テスト）
   - Developer C: User Story 3（カスタム値テスト）
3. ストーリーが独立して完了し統合

---

## タスクサマリー

- **合計タスク数**: 18
- **User Story 1 タスク**: 3（T005-T007）
- **User Story 2 タスク**: 3（T008-T010）
- **User Story 3 タスク**: 3（T011-T013）
- **ドキュメントタスク**: 5（T014-T018）
- **並列実行可能タスク**: 4（T002、T014、T015、一部のテスト）

### 推奨 MVP スコープ

**MVP = User Story 1 のみ**:
- Phase 1: Setup（T001-T002）
- Phase 2: Foundational（T003-T004）
- Phase 3: User Story 1（T005-T007）
- 最小限のドキュメント（T014 の基本バージョン）

これにより、macOS 開発者が即座に Docker イメージをビルドできるようになり、最も重要なブロッキング問題が解決されます。

---

## 注意事項

- [P] タスク = 異なるファイル、依存関係なし
- [Story] ラベルはタスクを特定のユーザーストーリーにマッピング（トレーサビリティ用）
- 各ユーザーストーリーは独立して完了およびテスト可能
- 手動テストは実装後に実行（TDD なし）
- 各タスクまたは論理グループ後にコミット
- 任意のチェックポイントでストーリーを独立して検証するために停止
- 避けるべきこと: 曖昧なタスク、同じファイルの競合、独立性を壊すストーリー間の依存関係
