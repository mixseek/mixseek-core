"""Leader Agent ロギング

Agent Delegation実行、Member Agent選択、データベース保存のログを記録。

References:
    - Article 11: 既存ロギングパターンを参考（DRY準拠）
"""

import logging
from datetime import UTC, datetime

from pydantic_ai import RunUsage

logger = logging.getLogger("mixseek.leader_agent")


def log_agent_delegation_start(team_id: str, team_name: str, round_number: int, prompt: str) -> None:
    """Agent Delegation開始ログ

    Args:
        team_id: チームID
        team_name: チーム名
        round_number: ラウンド番号
        prompt: ユーザープロンプト
    """
    logger.info(
        "Agent Delegation started",
        extra={
            "event": "delegation_start",
            "team_id": team_id,
            "team_name": team_name,
            "round_number": round_number,
            "prompt_preview": prompt[:100] + "..." if len(prompt) > 100 else prompt,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def log_member_agent_selected(team_id: str, agent_name: str, tool_name: str) -> None:
    """Member Agent選択ログ

    Args:
        team_id: チームID
        agent_name: Member Agent名
        tool_name: Tool名
    """
    logger.info(
        f"Member Agent selected: {agent_name}",
        extra={
            "event": "agent_selected",
            "team_id": team_id,
            "agent_name": agent_name,
            "tool_name": tool_name,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def log_member_agent_completed(
    team_id: str, agent_name: str, status: str, execution_time_ms: float, usage: RunUsage
) -> None:
    """Member Agent実行完了ログ

    Args:
        team_id: チームID
        agent_name: Member Agent名
        status: 実行ステータス
        execution_time_ms: 実行時間（ミリ秒）
        usage: RunUsage
    """
    logger.info(
        f"Member Agent completed: {agent_name} ({status})",
        extra={
            "event": "agent_completed",
            "team_id": team_id,
            "agent_name": agent_name,
            "status": status,
            "execution_time_ms": execution_time_ms,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "requests": usage.requests,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def log_database_save(team_id: str, round_number: int, submission_count: int) -> None:
    """データベース保存ログ

    Args:
        team_id: チームID
        round_number: ラウンド番号
        submission_count: 保存されたSubmission数
    """
    logger.info(
        f"Database save: {team_id}:{round_number}",
        extra={
            "event": "database_save",
            "team_id": team_id,
            "round_number": round_number,
            "submission_count": submission_count,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def log_agent_delegation_complete(
    team_id: str, round_number: int, total_count: int, success_count: int, total_usage: RunUsage
) -> None:
    """Agent Delegation完了ログ

    Args:
        team_id: チームID
        round_number: ラウンド番号
        total_count: 総Agent数
        success_count: 成功Agent数
        total_usage: 合計RunUsage
    """
    logger.info(
        f"Agent Delegation completed: {success_count}/{total_count} agents succeeded",
        extra={
            "event": "delegation_complete",
            "team_id": team_id,
            "round_number": round_number,
            "total_count": total_count,
            "success_count": success_count,
            "total_input_tokens": total_usage.input_tokens,
            "total_output_tokens": total_usage.output_tokens,
            "total_requests": total_usage.requests,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )
