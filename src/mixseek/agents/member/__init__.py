"""Member Agent module bundle.

This subpackage groups all Member Agent implementations and shared utilities:
    - base: Abstract base class and common logic (BaseMemberAgent)
    - factory: Factory for creating Member Agents (MemberAgentFactory)
    - plain: General reasoning agent implementation (PlainMemberAgent)
    - web_search: Research-focused agent implementation (WebSearchMemberAgent)
    - code_execution: Computational agent implementation (CodeExecutionMemberAgent)

References:
    - Spec: specs/009-member/spec.md
    - Plan: specs/009-member/plan.md
"""

from mixseek.agents.member.base import BaseMemberAgent
from mixseek.agents.member.code_execution import CodeExecutionMemberAgent
from mixseek.agents.member.factory import MemberAgentFactory
from mixseek.agents.member.plain import PlainMemberAgent
from mixseek.agents.member.web_fetch import WebFetchMemberAgent
from mixseek.agents.member.web_search import WebSearchMemberAgent

__all__ = [
    "BaseMemberAgent",
    "MemberAgentFactory",
    "PlainMemberAgent",
    "WebSearchMemberAgent",
    "WebFetchMemberAgent",
    "CodeExecutionMemberAgent",
]
