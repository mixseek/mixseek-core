# mixseekコマンド

ブランチ名: 004-mixseek-core-command
親仕様: specs/001-specs

## 概要

`mixseek` コマンドは、プロジェクトの初期化、エージェントの実行、プロジェクト設定などを実行する
Python+Typerで実装し、pyproject.tomlにエントリーポイントを設定する

サブコマンド:

- init: プロジェクトの初期化
- execute: エージェントの実行
- config: 設定の参照・変更など

今回はinitコマンドだけにフォーカスし、executeとconfigコマンドは将来実装とし、仕様・計画・実装のスコープから外す

## mixseek initコマンド

サブコマンド、 `mixseek init` コマンドは次を実行する

- 環境変数: `MIXSEEK_WORKSPACE` に指定されたディレクトリを作成する
- 環境変数が設定されていない場合は `--workspace` (-w) オプションでワークスペースのpathを指定できる
- ワークスペースにディレクトリを作成する
  - ログディレクトリ: `MIXSEEK_WORKSPACE/logs`
  - 設定ディレクトリ: `MIXSEEK_WORKSPACE/configs`
  - テンプレートディレクトリ: `MIXSEEK_WORKSPACE/templates` 
- 設定ファイル(TOML)のサンプルファイルを生成する

ワークスペースについては、specs/002-config/spec.md を参照

## mixseek executeコマンド

仕様詳細は別途検討する

## mixseek configコマンド

仕様詳細は別途検討する

## 技術スタック

次のPythonパッケージを検討する

- typer: https://typer.tiangolo.com/
- pydantic-settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
