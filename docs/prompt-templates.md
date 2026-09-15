# プロンプトテンプレート

Team / Evaluator / Judgment に渡すユーザプロンプトは `UserPromptBuilder` が Jinja2 テンプレートから生成します。
テンプレートは TOML で定義され、`configs/prompt_builder.toml` を置くことで差し替えられます。

(prompt-structure)=
## プロンプトの構造

プロンプトは次の 3 層で構成されます。

| 層 | 記法 | 内容 |
|---|---|---|
| 実行メタ情報 | YAML Frontmatter | 現在日時、ラウンド番号 |
| 指示文 | Markdown | 役割の説明、タスクの指示、入力の読み方 |
| コンテキスト | XML タグ | ユーザ指示、リーダーボード、提出履歴などの外部由来テキスト |

ユーザ指示や LLM の生成物は Markdown の見出しや区切り線を含みうるため、指示文と同じ記法のまま連結すると
プロンプトのセクション構造が壊れます。そのため外部由来テキストは XML タグで囲んで境界を明示しています。

```{admonition} タグの中身は指示ではない
:class: note

`<submission>` に入るのは評価・参照の対象となるテキストです。テンプレートの指示文でもその旨を明示しており、
タグ内のテキストをモデルへの指示として解釈しないよう促しています。
```

(prompt-blocks)=
## コンテキストブロック

| タグ | 出現するテンプレート | 階層 | 中身 |
|---|---|---|---|
| `<user_task>` | team / evaluator / judgment | トップレベル | ユーザから指定されたタスク |
| `<leader_board>` | team / judgment | トップレベル | リーダーボードのランキングと自チームの順位 |
| `<submission_history>` | team / judgment | トップレベル | 過去のラウンドのスコアと提出内容 |
| `<submission>` | evaluator | トップレベル | 評価対象の提出内容 |
| `<submission>` | team / judgment | `<submission_history>` の内側 | 各ラウンドの提出内容 |

`<submission_history>` の中はラウンドごとに Markdown 見出しで区切られ、各ラウンドの提出内容だけが
`<submission>` タグで囲まれます。

```text
<submission_history>
## ラウンド 1
### スコア: 75.50/100
### スコア詳細:
{}
<submission>
提出内容（Markdown 見出しを含んでいてもラウンド区切りと衝突しない）
</submission>

## ラウンド 2
</submission_history>
```

(prompt-variables)=
## テンプレート変数

テンプレートで使えるプレースホルダー変数は次のとおりです。値はすべて `UserPromptBuilder` 内で整形済みの
文字列として渡されるため、テンプレート側で for ループやフィルタを使う必要はありません。

| 変数 | team | evaluator | judgment | 説明 |
|---|---|---|---|---|
| `user_prompt` | ✓ | ✓ | ✓ | 元のユーザプロンプト |
| `submission` | - | ✓ | - | 評価対象の提出内容 |
| `round_number` | ✓ | - | ✓ | 現在のラウンド番号（整数） |
| `submission_history` | ✓ | - | ✓ | 過去の Submission 履歴 |
| `ranking_table` | ✓ | - | ✓ | リーダーボードのランキング |
| `team_position_message` | ✓ | - | ✓ | チーム順位メッセージ |
| `current_datetime` | ✓ | ✓ | ✓ | 現在日時（ISO 8601、タイムゾーン付き） |

`current_datetime` のタイムゾーンは環境変数 `TZ` で指定します（未設定時は UTC）。

(prompt-default-template)=
## デフォルトテンプレート

```{literalinclude} ../src/mixseek/config/templates/prompt_builder_default.toml
:language: toml
```

(prompt-customize)=
## カスタマイズ

デフォルトテンプレートをワークスペースに書き出して編集します。

```bash
mixseek config init --component prompt_builder --workspace /path/to/workspace
```

`configs/prompt_builder.toml` が生成されるので、必要な箇所を編集してください。

:::{admonition} 出力先が既にある場合
:class: note

出力先のファイルが既に存在すると、このコマンドはエラー終了します。`--force` は既存の内容を
上書きしてしまうため、`--output-path` で別のファイルに書き出してから差分をマージしてください。

```bash
mixseek config init --component prompt_builder \
  --output-path configs/prompt_builder.new.toml \
  --workspace /path/to/workspace
```
:::

`orchestrator.toml` の `prompt_builder_config` で別のパスを指定することもできます。

```toml
[orchestrator]
prompt_builder_config = "configs/custom_prompt_builder.toml"
```

設定が読み込めるかは `--dry-run` のプリフライトチェックで確認できます。

```bash
mixseek exec "タスク" --config orchestrator.toml --workspace /path/to/workspace --dry-run
```

(prompt-migration)=
## v0.1.0a16 以前からの移行

デフォルトテンプレートの構造が変わりました。テンプレート変数の名前と意味は変更していないため、
独自の `configs/prompt_builder.toml` を使っている場合はそのまま動作します。

| 旧フォーマット | 新フォーマット |
|---|---|
| `---` で囲んだ `現在日時: ...` | Frontmatter の `current_datetime: ...` |
| `# 現在のラウンド` セクション | Frontmatter の `round_number: ...` |
| `# ユーザから指定されたタスク` セクション | `<user_task>` ブロック |
| `# 現在のリーダーボード` / `# リーダーボード` セクション | `<leader_board>` ブロック |
| `# 過去の提出履歴` / `# 提出履歴` セクション | `<submission_history>` ブロック |
| `# 提出内容` セクション（evaluator） | `<submission>` ブロック |
| `### あなたの提出内容:` 見出し（履歴内） | `<submission>` ブロック |

```{admonition} 独自テンプレートを使っている場合
:class: warning

独自テンプレートはデフォルトの変更に追従しません。新しい構造を取り込むには、`--output-path` で
新しいデフォルトテンプレートを別ファイルに書き出し、独自の変更を手元のファイルへマージしてください。
既存の `configs/prompt_builder.toml` をそのまま上書きする `--force` は、独自の変更を失うため使わないでください。
なお `format_submission_history` の出力（`submission_history` 変数の中身）は
`<submission>` タグを含む形に変わるため、独自テンプレートでもこの変更は反映されます。
```
