# Research: Mixseek UI ラウンド進捗機能

**Date**: 2025-11-13 | **Feature**: 076-ui | **Phase**: 0

## 1. 可視化ライブラリの選定

### Decision: **Plotly**

### Rationale

**インタラクティブ性**:
- WebGL対応により50チーム×10ラウンド（500データポイント）でも高速レンダリング
- 凡例のクリックで系列の表示/非表示切り替え（ネイティブサポート）
- ホバー情報でラウンド番号・スコア・チーム名を詳細表示
- `legendgroup`により複数グラフ間の連携が可能

**パフォーマンス**:
- 1000行以上のデータで自動的に`render_mode="webgl"`が適用される
- 最大100万データポイントまでサポート（WebGL使用時）
- Streamlit連携で`orjson`により高速シリアライゼーション

**Streamlit統合**:
- `st.plotly_chart()`でネイティブサポート
- Streamlitテーマ自動適用
- レスポンシブデザイン対応（`use_container_width=True`）

**制約事項**:
- ブラウザによるWebGLコンテキスト制限（同一ページで最大8グラフ）
- 50,000データポイント以上で描画が重くなる可能性（サーバー側集約推奨）

### Alternatives Considered

**Altair**:
- ❌ **5000行制限**: デフォルトで`MaxRowsError`が発生
- ✅ 回避策: VegaFusion data transformer（Altair 5.1+）
- ❌ 凡例折りたたみには`selection_point(bind='legend')`が必要（追加実装）
- ❌ パフォーマンスがPlotly WebGLに劣る

**Matplotlib**:
- ❌ 静的画像生成（インタラクティブ性なし）
- ❌ Streamlitでの組み込みが煩雑（`st.pyplot()`）
- ❌ 50チーム分の凡例表示が視認性低下

### Implementation Example

```python
import plotly.express as px
import streamlit as st

# スコア推移データ（50チーム×10ラウンド）
df = fetch_all_teams_score_history(execution_id)

fig = px.line(
    df,
    x="round_number",
    y="score",
    color="team_name",
    title="全チームスコア推移",
    labels={"round_number": "ラウンド", "score": "スコア", "team_name": "チーム"},
    hover_data=["team_id"],
)

# WebGL自動有効化（1000+行）
# fig.update_traces(mode="lines", render_mode="webgl")

st.plotly_chart(fig, use_container_width=True)
```

## 2. DuckDB スキーマ

### 既存テーブル構造

#### `round_status` テーブル（既存・未文書化）

```sql
CREATE TABLE round_status (
    id INTEGER PRIMARY KEY DEFAULT nextval('round_status_id_seq'),
    execution_id VARCHAR NOT NULL,
    team_id VARCHAR NOT NULL,
    team_name VARCHAR NOT NULL,
    round_number INTEGER NOT NULL,
    should_continue BOOLEAN,
    reasoning VARCHAR,
    confidence_score FLOAT,
    round_started_at TIMESTAMP,      -- ラウンド開始時刻
    round_ended_at TIMESTAMP,        -- ラウンド終了時刻
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**用途**: ラウンド進捗追跡（FR-022, FR-023対応）
- `round_started_at` / `round_ended_at` でタイムライン表示可能（FR-020）
- `round_number` で現在ラウンドを取得（FR-022）
- `execution_id` + `team_id` でチーム別進捗一覧（FR-023）

**サンプルデータ**:
```
team-a, Round 1: 2025-11-12 08:32:03 → 08:33:22
team-a, Round 2: 2025-11-12 08:33:22 → 08:35:02
team-b, Round 1: 2025-11-12 08:32:04 → 08:33:25
...
```

#### `leader_board` テーブル（既存・スキーマ差異あり）

**実際のスキーマ** (database-schema.sqlと異なる):
```sql
CREATE TABLE leader_board (
    id INTEGER PRIMARY KEY DEFAULT nextval('leader_board_id_seq'),
    execution_id VARCHAR NOT NULL,
    team_id VARCHAR NOT NULL,
    team_name VARCHAR NOT NULL,
    round_number INTEGER NOT NULL,
    submission_content VARCHAR NOT NULL,
    submission_format VARCHAR DEFAULT 'md',
    score FLOAT NOT NULL,                    -- カラム名が異なる！
    score_details JSON NOT NULL,
    final_submission BOOLEAN DEFAULT FALSE,
    exit_reason VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**重要**: `evaluation_score` ではなく `score` カラムを使用
- `score_details` JSON: 評価の詳細情報（未分析）
- `final_submission` フラグ: 最終サブミッション判定

**用途**: スコア推移グラフ（FR-009, FR-020）
- `score` でY軸プロット
- `round_number` でX軸プロット
- `team_id` / `team_name` でグループ化

**サンプルデータ**:
```
team-a, Round 1: 37.37点
team-a, Round 2: 41.68点（最終）
team-b, Round 1: 18.34点
team-b, Round 2: 68.67点
team-b, Round 3: 85.00点（最終）
```

### 新規テーブル: **不要**

**発見**: `round_progress` / `round_scores` テーブルは不要。
既存の `round_status` + `leader_board` で全要件を満たす。

### データベースクエリ仕様

#### クエリ1: 現在のラウンド番号取得（FR-022）

```sql
-- 実行ページ上部表示
SELECT team_id, team_name, round_number
FROM round_status
WHERE execution_id = ?
ORDER BY updated_at DESC
LIMIT 1;
```

#### クエリ2: チーム進捗一覧（FR-023）

```sql
-- 実行ページ進捗領域
SELECT team_id, team_name, round_number, round_started_at, round_ended_at
FROM round_status
WHERE execution_id = ?
ORDER BY team_name, round_number;
```

#### クエリ3: ラウンドタイムライン（FR-020）

```sql
-- 結果ページタイムライン
SELECT round_number, round_started_at, round_ended_at
FROM round_status
WHERE execution_id = ? AND team_id = ?
ORDER BY round_number;
```

#### クエリ4: 全チームスコア推移（FR-009, FR-020）

```sql
-- 結果ページ折れ線グラフ
SELECT team_id, team_name, round_number, score
FROM leader_board
WHERE execution_id = ?
ORDER BY team_id, round_number;
```

#### クエリ5: チーム最終サブミッション（FR-024）

```sql
-- 実行ページタブ内表示
SELECT submission_content, score, score_details, created_at
FROM leader_board
WHERE execution_id = ? AND team_id = ? AND final_submission = TRUE
ORDER BY round_number DESC
LIMIT 1;
```

## 3. Streamlit タブ実装パターン

### Decision: `st.tabs()` + 50チーム対応

### Rationale

**仕様理解**:
- Streamlitネイティブの`st.tabs()`は動的タブ生成に対応
- **制約**: タブ幅が画面を超えるとスクロールバーなし（GitHub Issue #5552）
- **回避策**: Shift+マウスホイール / マウス中ボタンクリックで水平スクロール可能

**50チーム対応**:
- タブラベルを短縮（例: "Team A", "Team B", ...）
- 最初のタブを"タスク"専用、2番目以降を各チーム
- ユーザーは矢印キーでナビゲーション可能

**パフォーマンス**:
- ⚠️ **全タブのコンテンツが事前計算される**（条件付きレンダリング不可）
- 対策: 各タブ内で遅延ロード（`st.spinner`使用）

### Alternatives Considered

**streamlit-dynamic-tabs** (サードパーティ):
- ✅ タブ追加/削除が動的
- ❌ メンテナンス状況不明、依存追加のリスク
- ❌ ネイティブ機能で十分

**st.segmented_control** (条件付きレンダリング):
- ✅ 選択されたコンテンツのみレンダリング
- ❌ タブUIではなくボタン形式（UX劣化）
- ❌ 50チームでボタン配置が困難

### Implementation Pattern

```python
import streamlit as st
from mixseek_ui.services.leaderboard_service import fetch_team_submission

# タスクプロンプト + チームタブ
teams = fetch_team_list(execution_id)
tab_labels = ["タスク"] + [f"{team.team_name}" for team in teams]

tabs = st.tabs(tab_labels)

# タスクタブ
with tabs[0]:
    st.markdown("### タスク")
    st.text_area("ユーザプロンプト", value=user_prompt, disabled=True)

# チームタブ（動的生成）
for idx, team in enumerate(teams, start=1):
    with tabs[idx]:
        st.markdown(f"### {team.team_name}")
        submission = fetch_team_submission(execution_id, team.team_id)
        if submission:
            st.markdown(f"**スコア**: {submission.score:.2f}")
            st.markdown("**最終サブミッション**")
            st.text_area("内容", value=submission.submission_content, height=300, disabled=True)
        else:
            st.info("サブミッションがありません")
```

**Edge Case対応**:
- チーム数0: "タスク"タブのみ表示
- チーム数50+: スクロール前提、キーボード操作を案内

## 4. 既存UIコードの再利用

### ディレクトリ構造

**注**: 既存UIは`build/lib/mixseek_ui/`（別パッケージ・ビルド成果物）にあり、今回の実装対象は`src/mixseek/ui/`です。既存UIからパターンを参照します。

```
# 既存UI (参考用・別パッケージ)
build/lib/mixseek_ui/                # ビルド成果物 (gitignore対象)
├── app.py                           # エントリーポイント
├── pages/
│   ├── 1_execution.py               # 実行ページ（パターン参照）
│   ├── 2_results.py                 # 結果ページ（パターン参照）
│   └── 3_history.py                 # 履歴ページ
├── components/
│   ├── leaderboard_table.py         # テーブル表示パターン参照
│   ├── history_table.py             # 参考
│   └── orchestration_selector.py    # 参考
├── services/
│   ├── leaderboard_service.py       # DuckDBアクセスパターン参照
│   ├── execution_service.py         # 参考
│   └── config_service.py            # 参考
└── models/
    ├── leaderboard.py               # モデル定義パターン参照
    └── execution.py                 # 参考

# 実装対象 (今回作成)
src/mixseek/ui/                      # mixseekパッケージ内のuiサブパッケージ
├── pages/
│   ├── 1_execution.py               # 実行ページ (MODIFY)
│   ├── 2_results.py                 # 結果ページ (MODIFY)
│   └── 3_history.py                 # 履歴ページ (既存)
├── components/                       # 新規コンポーネント
│   ├── round_progress.py            # NEW
│   ├── team_progress.py             # NEW
│   ├── submission_tabs.py           # NEW
│   ├── round_timeline.py            # NEW
│   └── score_chart.py               # NEW
├── services/
│   └── round_service.py             # NEW
├── models/
│   └── round_models.py              # NEW
└── utils/
    └── db_utils.py                  # NEW
```

### 再利用可能なコンポーネント

#### 1. `leaderboard_table.py` - テーブル表示パターン

**現状機能**:
- Pandas DataFrame → Streamlit `st.dataframe()`
- トップチームハイライト（背景色変更）
- カラム設定（非表示カラム指定）

**再利用箇所**:
- チーム進捗一覧テーブル（FR-023）
- ラウンドタイムラインテーブル（FR-020）

**共通化すべきロジック**:
```python
# mixseek_ui/components/common_table.py (新規)
def render_dataframe_with_highlight(
    df: pd.DataFrame,
    highlight_condition: Callable[[pd.Series], bool],
    hidden_columns: list[str] = []
) -> None:
    """共通テーブルレンダリング"""
    ...
```

#### 2. `leaderboard_service.py` - DuckDB アクセスパターン

**現状機能**:
- `fetch_leaderboard(execution_id)`: leader_board全件取得
- `fetch_top_submission(execution_id)`: 最高スコア取得
- `fetch_team_submission(execution_id, team_id)`: チーム別サブミッション

**再利用パターン**:
```python
# 接続管理
workspace = get_workspace_path()
conn = duckdb.connect(str(workspace / "mixseek.db"))

# クエリ実行
result = conn.execute("SELECT ... FROM leader_board WHERE ...").fetchall()

# モデル変換
return [LeaderboardEntry.from_db_row(row) for row in result]
```

**拡張対象**:
- `fetch_round_status(execution_id)` 追加
- `fetch_all_teams_score_history(execution_id)` 追加

#### 3. セッション状態管理パターン

**現状パターン**:
```python
# 1_execution.py
if "current_execution_result" not in st.session_state:
    st.session_state.current_execution_result = None

# 実行後
st.session_state.current_execution_id = execution.execution_id
```

**再利用**:
- 実行中フラグ（`is_running`）
- 実行ID保持（`current_execution_id`）
- セッション状態初期化関数を共通化

### データ取得パターン統一

**既存パターン** (`leaderboard_service.py`):
1. `get_workspace_path()` でワークスペース取得
2. `duckdb.connect()` で接続
3. SQLクエリ実行
4. Pydanticモデルに変換
5. 例外処理（`ValueError` / `RuntimeError`）

**新規実装時の統一ルール**:
- 環境変数 `MIXSEEK_WORKSPACE` 必須（憲章Article 9）
- 接続はコンテキストマネージャ不使用（既存コードに合わせる）
- クエリは生SQLで記述（ORMレイヤーなし）
- モデル変換は `from_db_row()` クラスメソッド

### UI配置パターン

**既存パターン** (`2_results.py`):
```python
# ヘッダー
st.title("実行結果")

# トップハイライト
st.subheader("🏆 最高スコアサブミッション")
col1, col2 = st.columns([2, 1])
...

# セクション区切り
st.divider()

# メインコンテンツ
st.subheader("リーダーボード")
...
```

**再利用**:
- `st.columns()` レイアウト（2カラム、3カラム）
- `st.divider()` セクション区切り
- `st.metric()` KPI表示
- `st.expander()` 詳細折りたたみ

## 次のステップ

Phase 0完了。Phase 1（Design & Contracts）へ進む:

1. `data-model.md` 作成
   - `RoundProgress` モデル定義
   - `TeamScoreHistory` モデル定義
   - 既存 `LeaderboardEntry` 拡張

2. `contracts/db_queries.yaml` 更新
   - 5つのクエリ仕様を正式定義
   - パラメータと戻り値の型を明記

3. `quickstart.md` 作成
   - 開発環境セットアップ
   - UIコンポーネント追加手順
   - テスト実行方法

4. Phase 2タスク分解（`/speckit.tasks`）

---

**Research Version**: 1.0
**Completed**: 2025-11-13
**Next Phase**: `/speckit.plan` でPhase 1実行
