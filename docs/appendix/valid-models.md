# Appendix

## 利用可能モデル一覧

{numref}`table-valid-models` は、mixseek-coreで利用可能なAIモデルの代表例です。

- plain_compatible: テキストのプロンプトが利用可能
- code_exec_compatible: コード実行を含めたプロンプトが利用可能

```{note}
Gemini（Google）については、頻繁に更新されるため一覧には `-latest` エイリアス
（例: `gemini-flash-lite-latest`）のみを掲載しています。具体的なバージョンを含む
最新の完全なモデル一覧は、Google 公式ドキュメントを参照してください。

<https://ai.google.dev/gemini-api/docs/models>

なお `-latest` エイリアスは新モデルのリリースごとに自動で切り替わります（2週間前に
メール通知あり）。再現性・安定性を重視する場合は、具体的なバージョン
（例: `google-gla:gemini-3.1-flash-lite`）を指定してください。
```

```{note}
mixseek はモデルの **テキスト出力のみ** を利用します。画像・音声・動画を生成する
モデル（例: 画像生成、TTS、動画生成モデルなど）は、テキスト応答を返さないため
mixseek で使う意味がありません。テキスト生成に対応したモデルを指定してください。
```

```{csv-table} 利用可能なAIモデル一覧
:name: table-valid-models
:file: ../data/valid-models.csv
:header-rows: 1
:widths: auto
:align: left
```
