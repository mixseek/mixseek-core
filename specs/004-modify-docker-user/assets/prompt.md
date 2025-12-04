# Mac OS 上で docker build すると gid エラーが発生する不具合の対応

ブランチ名: 003-mixseek-core-modify-docker-user
親仕様: specs/003-dockerfiles

## 概要

親仕様で作成した Dockerfile を Mac OS で実行するとエラーが発生します。

### エラーメッセージ抜粋

```
 > [stage-0  3/14] RUN groupadd -g 20 xxx &&     useradd -m -u 502 -g 20 -s /bin/bash xxx:
0.117 groupadd: GID '20' already exists
------
Dockerfile:76
--------------------
  75 |     # install them in the root section above or use USER root temporarily in this file.
  76 | >>> RUN groupadd -g ${MIXSEEK_GID} ${MIXSEEK_USERNAME} && \
  77 | >>>     useradd -m -u ${MIXSEEK_UID} -g ${MIXSEEK_GID} -s /bin/bash ${MIXSEEK_USERNAME}
  78 |     
--------------------
ERROR: failed to build: failed to solve: process "/bin/sh -c groupadd -g ${MIXSEEK_GID} ${MIXSEEK_USERNAME} &&     useradd -m -u ${MIXSEEK_UID} -g ${MIXSEEK_GID} -s /bin/bash ${MIXSEEK_USERNAME}" did not complete successfully: exit code: 4
```

### 原因

`dockerfiles/Makefile.common` にある下記変数で、ログイン中のユーザを利用していることが原因。

```dockerfiles/Makefile.common
MIXSEEK_USERNAME := $(shell whoami)
MIXSEEK_UID := $(shell id -u)
MIXSEEK_GID := $(shell id -g)
```

## 対応内容

ログイン中のユーザは利用せず、環境変数で設定可能とする。
環境変数未設定でも利用できるように下記のようなデフォルト値を設けること。
```
MIXSEEK_USERNAME = mixseek_core
MIXSEEK_UID = 1000
MIXSEEK_GID = 1000
```
