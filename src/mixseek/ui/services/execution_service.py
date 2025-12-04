"""Execution service for running orchestrations."""

import asyncio
import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import duckdb

from mixseek.core.auth import clear_auth_caches
from mixseek.orchestrator import Orchestrator, load_orchestrator_settings
from mixseek.ui.models.config import OrchestrationOption
from mixseek.ui.models.execution import Execution, ExecutionState, ExecutionStatus, FailedTeamInfo, TeamProgressState
from mixseek.ui.utils.workspace import get_workspace_path

logger = logging.getLogger(__name__)

# グローバル辞書: execution_id → ExecutionState
# Streamlitのセッション間で状態を共有するために使用
_execution_states: dict[str, ExecutionState] = {}

# グローバル辞書: execution_id → Execution
# 完了後の実行結果を保存
_execution_results: dict[str, Execution] = {}

# グローバル辞書: execution_id → Exception
# バックグラウンドタスクのエラーを保存
_execution_errors: dict[str, Exception] = {}


def _read_progress_from_file(execution_id: str) -> ExecutionState | None:
    """進捗ファイルから実行状態を読み取る（全チーム集約）.

    Args:
        execution_id: 実行ID

    Returns:
        ExecutionState | None: 実行状態（全チームの最大ラウンド）、またはNone（ファイル不在時）

    Note:
        複数チームが並列実行される場合、各チームの進捗ファイルを読み取り、
        最も進んでいるラウンド情報を返す
    """
    workspace = get_workspace_path()
    logs_dir = workspace / "logs"

    if not logs_dir.exists():
        return None

    try:
        # execution_idに一致するすべての進捗ファイルを検索
        progress_files = list(logs_dir.glob(f"{execution_id}.*.progress.json"))
        logger.debug(f"Found {len(progress_files)} progress files for execution_id={execution_id}")

        if not progress_files:
            return None

        # 全チームの進捗を読み取り
        all_progress = []
        for progress_file in progress_files:
            try:
                with open(progress_file) as f:
                    data = json.load(f)
                    all_progress.append(data)
                    logger.debug(f"Read progress from {progress_file.name}: round={data.get('current_round')}")
            except Exception as e:
                logger.warning(f"Failed to read {progress_file.name}: {e}")
                continue

        if not all_progress:
            return None

        # 最も進んでいるチームの情報を使用
        latest_progress = max(all_progress, key=lambda x: x.get("current_round", 0))

        # 全チームが完了（completed または failed）しているか確認
        all_completed_or_failed = all(p.get("status") in ["completed", "failed"] for p in all_progress)

        # デバッグログ：各チームのステータス
        for p in all_progress:
            logger.debug(
                f"Team {p.get('team_id')} ({p.get('team_name')}): "
                f"status={p.get('status')}, round={p.get('current_round')}/{p.get('total_rounds')}"
            )
        logger.debug(f"All teams completed or failed: {all_completed_or_failed}")

        if all_completed_or_failed:
            # 全チーム完了：失敗チームの有無でステータスを決定
            failed_teams = [p for p in all_progress if p.get("status") == "failed"]
            completed_teams = [p for p in all_progress if p.get("status") == "completed"]

            if failed_teams and not completed_teams:
                # 全チーム失敗
                overall_status = "failed"
            elif failed_teams and completed_teams:
                # 一部失敗、一部成功
                overall_status = "partial_failure"
            else:
                # 全チーム成功
                overall_status = "completed"

            # 失敗したチームのエラーメッセージを収集
            if failed_teams:
                error_messages = [p.get("error_message", "Unknown error") for p in failed_teams]
                error_message = "; ".join(error_messages) if error_messages else None
            else:
                error_message = None
        else:
            # 実行中のチームがある場合
            overall_status = "running"
            # 既に失敗しているチームがある場合はエラーメッセージを表示
            failed_teams = [p for p in all_progress if p.get("status") == "failed"]
            if failed_teams:
                error_messages = [p.get("error_message", "Unknown error") for p in failed_teams]
                error_message = "; ".join(error_messages) if error_messages else None
            else:
                error_message = None

        return ExecutionState(
            execution_id=latest_progress["execution_id"],
            status=ExecutionStatus(overall_status),
            current_round=latest_progress.get("current_round"),
            total_rounds=latest_progress.get("total_rounds"),
            error_message=error_message,
        )
    except Exception as e:
        logger.warning(f"Failed to read progress files: {e}", exc_info=True)
        return None


def _get_failed_teams_from_progress_files(execution_id: str, workspace: Path) -> list[FailedTeamInfo]:
    """進捗ファイルから失敗チーム情報を取得.

    Args:
        execution_id: 実行ID
        workspace: ワークスペースパス

    Returns:
        list[FailedTeamInfo]: 失敗したチームの情報リスト
    """
    logs_dir = workspace / "logs"
    if not logs_dir.exists():
        return []

    failed_teams: list[FailedTeamInfo] = []
    progress_files = list(logs_dir.glob(f"{execution_id}.*.progress.json"))

    for progress_file in progress_files:
        try:
            with open(progress_file) as f:
                data = json.load(f)
                if data.get("status") == "failed" and data.get("error_message"):
                    # 必須フィールドに直接アクセス（KeyErrorは外側のexceptで捕捉）
                    failed_teams.append(
                        FailedTeamInfo(
                            team_id=data["team_id"],
                            team_name=data["team_name"],
                            error_message=data["error_message"],
                        )
                    )
        except (KeyError, json.JSONDecodeError) as e:
            logger.warning(f"Invalid progress file {progress_file}: {e}")
            continue
        except Exception as e:
            logger.debug(f"Failed to read progress file {progress_file}: {e}")
            continue

    return failed_teams


def get_all_teams_execution_status(execution_id: str) -> list[TeamProgressState]:
    """全チームの実行状態を取得（ポーリング用）.

    Args:
        execution_id: 実行ID

    Returns:
        list[TeamProgressState]: チーム別進捗状態のリスト（team_nameでソート済み）

    Note:
        - 進捗ファイル（{execution_id}.*.progress.json）から全チーム情報を読み取り
        - 各チームの進捗を個別に返却（集約しない）
        - ファイル読み取り失敗したチームはスキップ
    """
    workspace = get_workspace_path()
    logs_dir = workspace / "logs"

    if not logs_dir.exists():
        return []

    try:
        # execution_idに一致するすべての進捗ファイルを検索
        progress_files = list(logs_dir.glob(f"{execution_id}.*.progress.json"))
        logger.debug(f"Found {len(progress_files)} progress files for execution_id={execution_id}")

        if not progress_files:
            return []

        # 全チームの進捗を読み取り
        team_progress_list = []
        for progress_file in progress_files:
            try:
                with open(progress_file) as f:
                    data = json.load(f)

                    team_progress = TeamProgressState(
                        team_id=data["team_id"],
                        team_name=data["team_name"],
                        current_round=data["current_round"],
                        total_rounds=data["total_rounds"],
                        status=data["status"],
                        current_agent=data.get("current_agent"),  # current_agentフィールドを読み取り
                        updated_at=data["updated_at"],
                        error_message=data.get("error_message"),  # エラーメッセージを読み取り
                    )
                    team_progress_list.append(team_progress)
                    logger.debug(
                        f"Read team progress: {team_progress.team_name} - round={team_progress.current_round}"
                    )
            except Exception as e:
                logger.warning(f"Failed to read team progress file {progress_file.name}: {e}")
                continue

        # team_nameでソート
        team_progress_list.sort(key=lambda x: x.team_name)
        return team_progress_list

    except Exception as e:
        logger.warning(f"Failed to get all teams execution status: {e}", exc_info=True)
        return []


def run_orchestration(
    prompt: str, orchestration_option: OrchestrationOption, execution_id: str | None = None
) -> Execution:
    """オーケストレーションを実行.

    Args:
        prompt: タスクプロンプト
        orchestration_option: 選択されたオーケストレーション
        execution_id: 実行ID（指定しない場合は自動生成）

    Returns:
        Execution: 実行レコード

    Raises:
        ValueError: プロンプトが空の場合
    """
    if not prompt.strip():
        raise ValueError("Task prompt cannot be empty")

    # execution_idをキャプチャ（クロージャー用）
    _execution_id = execution_id

    created_at = datetime.now()

    async def _execute() -> Execution:
        """非同期実行処理."""
        try:
            # ワークスペースパスを取得
            workspace = get_workspace_path()

            # Logfire初期化（バックグラウンドスレッド用）
            # メインプロセスで初期化されていても、スレッドで再初期化が必要
            if os.getenv("LOGFIRE_ENABLED") == "1":
                try:
                    from mixseek.config.logfire import LogfireConfig
                    from mixseek.observability import setup_logfire

                    logfire_config = LogfireConfig.from_env()
                    setup_logfire(logfire_config)
                except Exception as e:
                    # Logfire初期化失敗は警告のみ（実行は継続）
                    logger.warning(f"Logfire initialization failed in background thread: {e}")

            # 設定ファイルのフルパスを構築
            config_path = workspace / "configs" / orchestration_option.config_file_name

            if not config_path.exists():
                raise FileNotFoundError(f"Config file not found: {config_path}")

            # Orchestrator設定を読み込み（FR-011: OrchestratorSettings直接返却）
            orchestrator_settings = load_orchestrator_settings(config_path, workspace=workspace)

            # Orchestratorを初期化（FR-011: OrchestratorSettings直接受け取り）
            orchestrator = Orchestrator(
                settings=orchestrator_settings,
            )

            # オーケストレーションを実行
            summary = await orchestrator.execute(
                user_prompt=prompt,
                timeout_seconds=orchestrator_settings.timeout_per_team_seconds,
                execution_id=_execution_id,
            )

            # ExecutionSummaryからExecutionオブジェクトを構築
            completed_at = datetime.now()
            duration = (completed_at - created_at).total_seconds()

            # ステータスの判定
            if summary.failed_teams == 0:
                status = ExecutionStatus.COMPLETED
            elif summary.completed_teams > 0:
                status = ExecutionStatus.PARTIAL_FAILURE
            else:
                status = ExecutionStatus.FAILED

            # ExecutionSummaryからExecutionモデルへ変換
            from mixseek.ui.models.execution import FailedTeamInfo

            failed_teams_info = [
                FailedTeamInfo(team_id=team.team_id, team_name=team.team_name, error_message=team.error_message)
                for team in summary.failed_teams_info
            ]

            return Execution(
                execution_id=summary.execution_id,
                prompt=prompt,
                status=status,
                best_team_id=summary.best_team_id,
                best_score=summary.best_score,
                duration_seconds=duration,
                created_at=created_at,
                completed_at=completed_at,
                failed_teams_info=failed_teams_info,
            )

        except Exception as e:
            logger.error(f"Orchestration execution failed: {e}", exc_info=True)
            completed_at = datetime.now()
            duration = (completed_at - created_at).total_seconds()

            # エラー時は渡されたexecution_id、または新規生成
            error_execution_id = _execution_id if _execution_id else str(uuid.uuid4())

            return Execution(
                execution_id=error_execution_id,
                prompt=prompt,
                status=ExecutionStatus.FAILED,
                best_team_id=None,
                best_score=None,
                duration_seconds=duration,
                created_at=created_at,
                completed_at=completed_at,
            )

    # asyncio.run()で同期的に実行
    # Issue #197: Clear auth caches before asyncio.run() to prevent stale event loop references
    # asyncio.run() closes the event loop after execution, but cached httpx clients
    # retain references to the closed loop, causing 'Event loop is closed' errors on subsequent runs
    clear_auth_caches()

    logger.debug(f"Starting asyncio.run() for execution_id={_execution_id}")
    try:
        result = asyncio.run(_execute())
        logger.debug(
            f"Orchestration completed: execution_id={result.execution_id}, status={result.status}, "
            f"best_score={result.best_score}"
        )
        return result
    except Exception as e:
        logger.error(f"asyncio.run() failed: {e}", exc_info=True)
        raise


def run_orchestration_in_background(prompt: str, orchestration_option: OrchestrationOption) -> str:
    """オーケストレーションをバックグラウンドスレッドで実行.

    Args:
        prompt: タスクプロンプト
        orchestration_option: 選択されたオーケストレーション

    Returns:
        str: 生成されたexecution_id

    Raises:
        ValueError: プロンプトが空の場合
    """
    if not prompt.strip():
        raise ValueError("Task prompt cannot be empty")

    # execution_idを事前生成
    execution_id = str(uuid.uuid4())

    # 初期状態を登録
    _execution_states[execution_id] = ExecutionState(
        execution_id=execution_id,
        status=ExecutionStatus.RUNNING,
        current_round=None,
        total_rounds=None,
        error_message=None,
    )

    def _background_task() -> None:
        """バックグラウンドで実行されるタスク."""
        try:
            # 別スレッドで定期的に進捗を更新
            def _update_progress() -> None:
                """進捗を定期的に更新（ポーリングループ用）."""
                logger.debug(f"Progress update thread started for execution_id={execution_id}")
                while execution_id in _execution_states:
                    state = _execution_states[execution_id]
                    # RUNNINGでない場合は更新停止
                    if state.status != ExecutionStatus.RUNNING:
                        logger.debug(f"Progress update stopped: status={state.status}")
                        break

                    # 進捗ファイルから読み取り
                    file_state = _read_progress_from_file(execution_id)
                    if file_state:
                        # ファイルから読み取った状態で更新
                        logger.debug(f"Progress updated: round={file_state.current_round}/{file_state.total_rounds}")
                        _execution_states[execution_id] = file_state
                    else:
                        logger.debug(f"No progress file found for execution_id={execution_id}")
                    # ファイルが存在しない場合は何もしない（Orchestrator未対応時）

                    # 2秒待機
                    time.sleep(2)
                logger.debug(f"Progress update thread finished for execution_id={execution_id}")

            # 進捗更新スレッドを起動
            progress_thread = threading.Thread(target=_update_progress, daemon=True)
            progress_thread.start()

            # run_orchestration()を実行（同期的に完了を待つ）
            logger.debug(f"Calling run_orchestration() for execution_id={execution_id}")
            execution = run_orchestration(prompt, orchestration_option, execution_id)
            logger.debug(f"run_orchestration() returned: execution_id={execution.execution_id}")

            # 実行結果を保存
            _execution_results[execution_id] = execution
            logger.debug(f"Saved execution result to _execution_results for execution_id={execution_id}")

            # 完了状態を更新
            _execution_states[execution_id] = ExecutionState(
                execution_id=execution_id,
                status=execution.status,
                current_round=None,  # 完了時はNone
                total_rounds=None,
                error_message=None,
            )
            logger.debug(f"Updated execution state to {execution.status} for execution_id={execution_id}")

        except Exception as e:
            logger.error(f"Background execution failed: {e}", exc_info=True)
            # エラーを保存
            _execution_errors[execution_id] = e
            # エラー状態を更新
            _execution_states[execution_id] = ExecutionState(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                current_round=None,
                total_rounds=None,
                error_message=str(e),
            )

    # スレッドを起動（daemon=Trueでメインプロセス終了時に自動終了）
    thread = threading.Thread(target=_background_task, daemon=True)
    thread.start()

    logger.info(f"Started background execution: {execution_id}")
    return execution_id


def get_execution_status(execution_id: str) -> ExecutionState:
    """実行状態を取得（ポーリング用）.

    グローバル辞書から実行状態を取得。
    進捗情報はバックグラウンドスレッドで定期的に更新される。

    Args:
        execution_id: 実行ID

    Returns:
        ExecutionState: 実行状態

    Note:
        - グローバル辞書に状態が存在しない場合、PENDINGステータスで返す
        - データベースアクセスは行わない（バックグラウンドスレッドで更新）
    """
    # グローバル辞書から状態を取得
    if execution_id not in _execution_states:
        # 状態が存在しない場合はPENDINGとして返す
        return ExecutionState(
            execution_id=execution_id,
            status=ExecutionStatus.PENDING,
            current_round=None,
            total_rounds=None,
            error_message=None,
        )

    # バックグラウンドスレッドで更新された状態をそのまま返す
    return _execution_states[execution_id]


def get_execution_result(execution_id: str) -> Execution | None:
    """実行結果を取得（完了後）.

    Args:
        execution_id: 実行ID

    Returns:
        Execution | None: 実行結果（完了後のみ）、未完了時はNone
    """
    # まずグローバル辞書から取得を試みる
    if execution_id in _execution_results:
        return _execution_results[execution_id]

    # 実行中の場合はDuckDBにアクセスしない（接続競合を回避）
    # 方法1: グローバル辞書チェック
    if execution_id in _execution_states:
        state = _execution_states[execution_id]
        if state.status == ExecutionStatus.RUNNING:
            logger.debug(
                f"Execution is still running (from state dict), skipping DuckDB access: execution_id={execution_id}"
            )
            return None

    # 方法2: 進捗JSONファイルの存在チェック（より確実）
    try:
        workspace = get_workspace_path()
        logs_dir = workspace / "logs"
        if logs_dir.exists():
            progress_files = list(logs_dir.glob(f"{execution_id}.*.progress.json"))
            if progress_files:
                # 進捗ファイルが存在 = Orchestrator実行中の可能性が高い
                logger.debug(f"Progress files exist, execution may be running: execution_id={execution_id}")
                # ファイルの中身をチェックしてstatusを確認
                for progress_file in progress_files:
                    try:
                        with open(progress_file) as f:
                            data = json.load(f)
                            if data.get("status") in ["running", "pending"]:
                                logger.debug(
                                    f"Execution is running (from progress file), "
                                    f"skipping DuckDB access: execution_id={execution_id}"
                                )
                                return None
                    except Exception:
                        # ファイル読み込みエラーは無視
                        continue
    except Exception:
        # 進捗ファイルチェックエラーは無視して続行
        pass

    # 完了後のみDuckDBから読み取る
    try:
        workspace = get_workspace_path()
        db_path = workspace / "mixseek.db"

        if not db_path.exists():
            return None

        # DuckDB接続を1回だけ試みる（Orchestrator実行中は失敗する）
        try:
            conn = duckdb.connect(str(db_path), read_only=True)
        except Exception as e:
            # 接続失敗時はNoneを返す（Orchestrator実行中の可能性）
            logger.debug(f"Failed to connect to DuckDB (likely Orchestrator is running): {e}")
            return None

        try:
            result = conn.execute(
                """
                SELECT
                    execution_id,
                    user_prompt,
                    status,
                    best_team_id,
                    best_score,
                    total_execution_time_seconds,
                    created_at,
                    completed_at
                FROM execution_summary
                WHERE execution_id = ?
                """,
                [execution_id],
            ).fetchone()

            if result:
                status = ExecutionStatus(result[2])

                # 失敗チーム情報を進捗ファイルから取得
                failed_teams_info: list[FailedTeamInfo] = []
                if status in (ExecutionStatus.PARTIAL_FAILURE, ExecutionStatus.FAILED):
                    failed_teams_info = _get_failed_teams_from_progress_files(execution_id, workspace)

                return Execution(
                    execution_id=result[0],
                    prompt=result[1],  # user_prompt → prompt
                    status=status,
                    best_team_id=result[3],
                    best_score=result[4],
                    duration_seconds=result[5],  # total_execution_time_seconds → duration_seconds
                    created_at=result[6],
                    completed_at=result[7],
                    failed_teams_info=failed_teams_info,
                )
            return None
        finally:
            conn.close()

    except Exception as e:
        logger.warning(f"Failed to fetch execution result from DuckDB: {e}")
        return None


def get_team_ids_for_execution(execution_id: str) -> list[str]:
    """実行に含まれるチームIDのリストを取得.

    Args:
        execution_id: 実行ID

    Returns:
        list[str]: チームIDのリスト（team_idでソート済み）

    Note:
        - leader_boardテーブルからユニークなteam_idを取得
        - チームが存在しない場合は空リストを返す
        - DuckDB接続エラー時は最大5回リトライ
    """
    # 実行中の場合はDuckDBにアクセスしない（接続競合を回避）
    # 方法1: グローバル辞書チェック
    if execution_id in _execution_states:
        state = _execution_states[execution_id]
        if state.status == ExecutionStatus.RUNNING:
            logger.debug(
                f"Execution is still running (from state dict), skipping DuckDB access: execution_id={execution_id}"
            )
            return []

    # 方法2: 進捗JSONファイルの存在チェック（より確実）
    try:
        workspace = get_workspace_path()
        logs_dir = workspace / "logs"
        if logs_dir.exists():
            progress_files = list(logs_dir.glob(f"{execution_id}.*.progress.json"))
            if progress_files:
                # 進捗ファイルが存在 = Orchestrator実行中の可能性が高い
                for progress_file in progress_files:
                    try:
                        with open(progress_file) as f:
                            data = json.load(f)
                            if data.get("status") in ["running", "pending"]:
                                logger.debug(
                                    f"Execution is running (from progress file), "
                                    f"skipping DuckDB access: execution_id={execution_id}"
                                )
                                return []
                    except Exception:
                        continue
    except Exception:
        pass

    try:
        workspace = get_workspace_path()
        db_path = workspace / "mixseek.db"

        if not db_path.exists():
            return []

        # DuckDB接続を1回だけ試みる（Orchestrator実行中は失敗する）
        try:
            conn = duckdb.connect(str(db_path), read_only=True)
        except Exception as e:
            # 接続失敗時は空リストを返す（Orchestrator実行中の可能性）
            logger.debug(f"Failed to connect to DuckDB (likely Orchestrator is running): {e}")
            return []

        try:
            results = conn.execute(
                """
                SELECT DISTINCT team_id
                FROM leader_board
                WHERE execution_id = ?
                ORDER BY team_id
                """,
                [execution_id],
            ).fetchall()

            return [row[0] for row in results]
        finally:
            conn.close()

    except Exception as e:
        logger.warning(f"Failed to fetch team IDs for execution {execution_id}: {e}")
        return []


def get_recent_logs(lines: int = 100, level: str = "INFO") -> list[str]:
    """ログファイルの末尾N行を取得（指定レベル以上）.

    Args:
        lines: 取得する行数（デフォルト100）
        level: 最小ログレベル（デフォルトINFO）

    Returns:
        list[str]: ログ行のリスト（古い順）

    Note:
        - ログファイル: $MIXSEEK_WORKSPACE/logs/mixseek.log
        - ログ形式: %(asctime)s - %(name)s - %(levelname)s - %(message)s
        - ファイル不在時は空リストを返す
        - FR-026: 実行ログセクション要件
        - dequeを使用してファイル全体をメモリに読み込まずに末尾を効率的に取得
    """
    from collections import deque

    workspace = get_workspace_path()
    log_file = workspace / "logs" / "mixseek.log"

    if not log_file.exists():
        return []

    try:
        with open(log_file, encoding="utf-8") as f:
            # dequeを使い、ファイル全体をメモリに読み込まずに末尾の行を取得
            # フィルタリング後に十分な行数を確保するため、多めに読み込む
            log_buffer = deque(f, maxlen=lines * 5)
    except Exception as e:
        logger.warning(f"Failed to read log file: {e}")
        return []

    # レベルフィルタリング
    level_map = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
    min_level = level_map.get(level.upper(), 1)

    filtered_logs: list[str] = []
    # バッファの末尾から逆順に処理して、最新のログから収集
    for line in reversed(log_buffer):
        if len(filtered_logs) >= lines:
            break

        for lvl, val in level_map.items():
            if f"- {lvl} -" in line and val >= min_level:
                filtered_logs.append(line.rstrip())
                break

    # 時系列順（古い→新しい）に戻して返す
    return list(reversed(filtered_logs))
