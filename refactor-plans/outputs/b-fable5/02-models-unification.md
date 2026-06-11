# 設定モデル統一計画（M1〜M3）— 本計画で最も影響の大きいテーマ

調査の結果、リポジトリ最大の構造課題は「**新旧二重設定モデル**」である。
pydantic-settings ベースの新モデル（`config/schema.py` の `*Settings` 群）への移行は
完了済みと明記されている（`agents/leader/config.py:3` "IMPORTANT (移行完了)"）にもかかわらず、
旧モデル（`*Config` 群）が公開 API として残り、**3系統の変換関数**が新→旧の橋渡しを続けている。

## 現状の二重化マップ

| 系統 | 新モデル（schema.py） | 旧モデル | 変換関数 |
| --- | --- | --- | --- |
| Evaluator | `EvaluatorSettings` | `EvaluationConfig` ほか2クラス（875行） | `evaluator_settings_to_evaluation_config` |
| Team/Leader | `TeamSettings` ほか | `TeamConfig` ほか2クラス（251行） | `team_settings_to_team_config` |
| MemberAgent | `MemberAgentSettings` ほか | `MemberAgentConfig`（487行の一部） | `member_agent_loader.py:204` ほか |

（旧モデルの所在: Evaluator 系は `models/evaluation_config.py`（`MetricConfig`／
`LLMDefaultConfig` を含む）、Team 系は `agents/leader/config.py`（`LeaderAgentConfig`／
`TeamMemberAgentConfig`）、MemberAgent 系は `models/member_agent.py`。
`AgentExecutorSettings.to_member_agent_config` も MemberAgent 系の変換経路。）

（Evaluator 系の旧モデルは `MetricConfig`／`LLMDefaultConfig` を含む。Team 系は
`LeaderAgentConfig`／`TeamMemberAgentConfig`。MemberAgent 系は
`AgentExecutorSettings.to_member_agent_config` も変換経路。）

旧モデルの利用は広範囲: `MemberAgentConfig` は agents 配下ほぼ全部＋CLI 2コマンド＋
`framework/integration_hooks.py` の計16ファイル、`EvaluationConfig` は evaluator 本体・
`evaluation_request.py`・round_controller・CLI evaluate が参照。

### この構造が生むコスト

1. **フィールド追加が最大4箇所**（新 Settings・旧 Config・変換関数・バリデータ）に波及する
2. バリデーションが新旧で重複・微妙に乖離（例: `timeout_seconds` の制約が
   `LeaderAgentConfig` は `ge=10, le=600`、`LeaderAgentSettings` は `ge=0` のみ）
3. 875行の `evaluation_config.py` はほぼ全体が旧モデル維持のためだけに存在

---

## M1: 新旧二重設定モデルの統一（旧 Config 群の廃止）

- **対象**: 上表の旧モデル3系統と全利用箇所（約20ファイル）
- **影響度: 高 / リスク: 中 / 工数: L**

### 問題（分析観点: 重複・密結合・古いパターン）

上記の通り。「段階的移行期間中は維持」とコメントされたまま移行が止まっており、
新規コードも旧モデルを参照し続けるため、放置すると乖離が広がる一方。

### 推奨アプローチ（系統ごとに独立した PR で段階実施）

**ステップ1 — Evaluator 系（効果最大）**
`Evaluator` は受け取った `EvaluatorSettings` を即座に旧 `EvaluationConfig` へ変換して
内部利用している（`evaluator/evaluator.py:96`）。内部実装を `EvaluatorSettings` 直接参照に
書き換え、`get_*_for_metric` 系のフォールバックは新モデル側のヘルパー（M3 参照）として実装する。
`EvaluationRequest.config`（`models/evaluation_request.py:81`）の型も差し替える。
完了時に `models/evaluation_config.py`（875行）を削除でき、**1ファイルで約3.4%のコード削減**。

**ステップ2 — Team/Leader 系**
`team_settings_to_team_config` の利用箇所（`cli/commands/team.py:199` ほか）を
`TeamSettings` 直接利用に変更し、`agents/leader/config.py` の旧3クラスを削除。
`create_leader_agent` のシグネチャ変更が必要なため、leader agent のテスト
（`tests/integration/test_leader_agent_e2e.py` 等）を回しながら進める。

**ステップ3 — MemberAgent 系（最も慎重に）**
`MemberAgentConfig` は実行時モデル（`MemberAgentResult` と同居）としての性格もあり、
単純削除ではなく「設定は `MemberAgentSettings` に一本化し、`MemberAgentConfig` は
実行時 DTO としての必要最小フィールドに縮小 or `MemberAgentSettings` を直接受け取る」の
二択を設計判断する。`agents/member/factory.py`・各 agent 実装・dynamic_loader が対象。

各ステップ共通の進め方:

- 旧モデルに `DeprecationWarning` を入れる中間リリースを挟む（外部利用者向け配慮。
  本パッケージは 0.1.0a 系のため、破壊的変更の許容度はチームで確認する）
- 変換関数のテスト（`tests/unit/models/` 等）は「変換が正しい」ことを保証している資産なので、
  統一後は「新モデルが旧モデルの制約を引き継いだ」ことを示すテストへ移植してから削除する

### 関連テスト（安全網）

models 参照テスト56ファイル・agents 39ファイル・evaluator 22ファイルと厚い。
ただし旧モデルを直接構築しているテストは書き換えが必要で、これが工数の過半を占める見込み。

---

## M2: LLM パラメータ共通基底モデルの導入

- **対象**: `config/schema.py`（`LeaderAgentSettings`/`MemberAgentSettings`/`EvaluatorSettings`/
  `JudgmentSettings`/`AgentExecutorSettings`）、`models/evaluation_config.py`
  （`MetricConfig`/`LLMDefaultConfig`）、`agents/leader/config.py`、`models/member_agent.py`
- **影響度: 高 / リスク: 低 / 工数: M**

### 問題（分析観点: DRY 違反）

LLM 呼び出しパラメータ10項目（`model` / `temperature` / `max_tokens` / `timeout_seconds` /
`max_retries` / `stop_sequences` / `top_p` / `seed` / `model_settings` /
`google_model_settings`）が、Field 定義・制約・description ごと**少なくとも9クラス**に
コピーされている（`schema.py:367-426` と `agents/leader/config.py:24-51` はほぼ同一文面）。
制約の乖離（M1 で挙げた `timeout_seconds` の例）はこのコピーが直接の原因。

### 推奨アプローチ

1. `config/llm_params.py`（または `schema/base.py` 内）に共通モデルを定義する:

   ```python
   class LLMParamsMixin(BaseModel):
       model: str | None = Field(default=None, ...)
       temperature: float | None = Field(default=None, ge=0.0, le=2.0, ...)
       # ...10項目を1箇所で定義。modelバリデータ（validate_model_format）も同居
   ```

2. 各 Settings クラスは Mixin を継承し、デフォルト値の差分（Leader のみ
   `model="google-gla:gemini-2.5-flash-lite"` 等）だけをオーバーライドする。
   pydantic-settings は BaseModel Mixin との多重継承で問題なくフィールドを合成できる。
3. `pydantic-ai` の `ModelSettings` へ変換する共通メソッド（`to_model_settings()`）も
   Mixin に置けば、agents 各所に散在する settings 組み立てコードも縮む
   （`core/model_settings.py` 107行が既にこの責務の一部を担っており、統合先候補）。
4. M1 を見据え、まず新モデル側（schema.py 系）にだけ適用し、旧モデルは触らない
   （どうせ削除するため）。

### 関連テスト（安全網）

各 Settings のバリデーションテストが `tests/unit/config/` にあり、制約値（ge/le）の
退行はそこで検知される。Mixin 化で制約を「正」とする値に統一する際、意図的な挙動変更
（例: timeout の下限）はテストも更新し、PR に明記する。

---

## M3: `get_*_for_metric` 10メソッドの統合（クイックウィン）

- **対象**: `src/mixseek/models/evaluation_config.py:578-820`
- **影響度: 中 / リスク: 低 / 工数: S**

### 問題（分析観点: DRY 違反）

`get_model_for_metric` / `get_temperature_for_metric` / `get_max_tokens_for_metric` /
`get_max_retries_for_metric` / `get_system_instruction_for_metric` /
`get_timeout_seconds_for_metric` / `get_stop_sequences_for_metric` / `get_top_p_for_metric` /
`get_seed_for_metric` の各約20行が、「メトリクス個別値が None なら `llm_default` の値」という
同一2行ロジックの繰り返し（計約240行）。

### 推奨アプローチ

ジェネリックなフォールバック1メソッドに集約する:

```python
def _resolve_for_metric(self, metric_name: str, attr: str) -> Any:
    metric = self._get_metric_config(metric_name)
    value = getattr(metric, attr)
    return value if value is not None else getattr(self.llm_default, attr)
```

既存の公開メソッドは型を保つ1行委譲として残す（呼び出し側変更ゼロ、約240行 → 約60行）。

**M1 ステップ1 との関係**: 本候補は M1 完了時にファイルごと消える。ただし工数 S・リスク低で
即実施でき、M1 着手まで期間が空く場合の保守コストを下げるため、先行実施を推奨
（M1 を直近スプリントでやるならスキップ可）。

### 関連テスト（安全網）

`tests/evaluator/unit/` にフォールバック挙動のテストあり。委譲化なら既存テストが
そのまま通ることが完了条件。
