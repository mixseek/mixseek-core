"""TeamDependencies - Agent Delegation依存関係

Agent Delegationで各Member Agentに共有される依存関係オブジェクト。
RunContext[TeamDependencies]として使用されます。

References:
    - Data Model: specs/008-leader/data-model.md (Section 4)
    - Research: specs/008-leader/research.md (Section 1)
"""

from dataclasses import dataclass, field

from mixseek.agents.leader.models import MemberSubmission


@dataclass
class TeamDependencies:
    """Leader Agent実行時の依存関係

    Agent Delegationで各Member Agentに共有される依存関係オブジェクト。

    Attributes:
        execution_id: 実行セッション全体の一意識別子
        team_id: チームID
        team_name: チーム名
        round_number: ラウンド番号
        submissions: Member Agent応答を記録するリスト（mutable、初期空リスト）
    """

    execution_id: str
    team_id: str
    team_name: str
    round_number: int
    submissions: list[MemberSubmission] = field(default_factory=list)
