"""`tests.unit.workflow` 共通 fixture。"""

import pytest

from mixseek.agents.leader.dependencies import TeamDependencies


@pytest.fixture
def team_deps() -> TeamDependencies:
    """workflow executable / engine テスト共通の `TeamDependencies`。"""
    return TeamDependencies(
        execution_id="exec-123",
        team_id="team-a",
        team_name="Team A",
        round_number=1,
    )
