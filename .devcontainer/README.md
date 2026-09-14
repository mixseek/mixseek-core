# Dev Container

VS Code / Cursor の Dev Containers 拡張から、MixSeek-Core の開発環境をそのまま開くための設定です。

既存の開発コンテナ（`dockerfiles/dev/Dockerfile`）を **そのまま再利用** しているため、
`make -C dockerfiles/dev run` で起動するコンテナと同じツール構成になります。
ツールを追加したい場合は `dockerfiles/dev/Dockerfile` を編集してください（両方に反映されます）。

## 前提条件

- Docker Engine 20.10 以降が起動していること
- VS Code + [Dev Containers 拡張](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
  （または `devcontainer` CLI）

## クイックスタート

1. API キー等を `.env.dev` に記入します。書式は `dockerfiles/dev/.env.dev.template` を参照してください。

   ```bash
   cp dockerfiles/dev/.env.dev.template .env.dev
   vim .env.dev
   ```

   `.env.dev` が無い場合もコンテナは起動します（`initializeCommand` が空ファイルを作成します）が、
   LLM 呼び出しを伴う処理は失敗します。

2. VS Code でリポジトリを開き、コマンドパレットから **Dev Containers: Reopen in Container** を実行します。

   初回はイメージのビルドに数分かかります。

3. コンテナ内で動作確認します。

   ```bash
   python --version   # Python 3.13.x
   uv --version
   gh --version
   claude --version
   ```

## 同梱ツール

| ツール | コマンド | 備考 |
|--------|----------|------|
| GitHub CLI | `gh` | PR / Issue 操作。**必須** |
| Claude Code | `claude` | **必須** |
| OpenAI Codex | `codex` | |
| Gemini CLI | `gemini` | |
| uv | `uv` | Python パッケージ管理 |
| debugpy | `python -m debugpy` | ポート 5678 |
| Streamlit UI | `mixseek ui` | ポート 8501 |

## 初回の認証

いずれもコンテナ内で一度実行すれば、`.config` / `.claude` がホストにバインドマウントされているため、
コンテナを作り直しても認証情報は維持されます（どちらもリポジトリの `.gitignore` 対象です）。

```bash
gh auth login     # 認証情報は .config/gh に保存される
claude            # 初回起動時にブラウザ経由でログイン
```

## ポート

| ポート | 用途 |
|--------|------|
| 5678 | debugpy（リモートデバッグ） |
| 8501 | Streamlit UI（`mixseek ui`） |

## `make -C dockerfiles/dev run` との関係

Dockerfile は共通ですが、コンテナは別物です。

- Dockerfile: 共通（`dockerfiles/dev/Dockerfile`）
- イメージ: devcontainer は独自のタグでビルドする（`mixseek-core/dev:latest` とは別）
- コンテナ名: devcontainer 側は固定名を付けていないため、`make` 側の `mixseek-core-dev` とは衝突しない
  （git worktree ごとに別コンテナを起動できる）
- マウント: `make` 側の `.cache` / `.config` に加えて、devcontainer は `.claude` もマウントする

`make -C dockerfiles/ci lint` などの品質チェックコマンドは、ホスト側（コンテナ外）から実行してください。

## 仮想環境について

Python の仮想環境はコンテナ内の `/venv` にあり、バインドマウントされる `/app` の外に置かれています。
そのためホスト側の `.venv` とは独立しており、ホストの OS/アーキテクチャの影響を受けません。
VS Code のインタプリタは `/venv/bin/python` に設定済みです。

## ユーザー / UID / GID

`Makefile.common` の既定値（`mixseek_core` / `1000` / `1000`）に固定しています。
Linux ホストで UID がズレる場合は Dev Containers の `updateRemoteUserUID`（既定で有効）が
コンテナ起動時に調整するため、通常は設定不要です。

恒久的に変更する場合は、`devcontainer.json` の `build.args` / `remoteUser` / `mounts` の
ホームディレクトリパスを、`.env.local` と同じ値に揃えて書き換えてください。

## トラブルシューティング

### `.cache` や `.config` で権限エラーが出る

Docker が root 所有でディレクトリを作ってしまった場合に発生します。**ホスト側** で修正してください
（コンテナ内のユーザーには sudo 権限がありません）。

```bash
sudo chown -R "$(id -u):$(id -g)" .cache .config .claude
```

### `.env.dev` を編集したのに反映されない

`--env-file` はコンテナ起動時にのみ読み込まれます。
**Dev Containers: Rebuild Container** を実行してください。

### 依存関係を更新したのに反映されない

`postCreateCommand` の `uv sync --frozen --extra ui` はコンテナ作成時にのみ走ります。
`uv.lock` を更新した後は、コンテナ内で手動実行してください。

```bash
uv sync --frozen --extra ui
```
