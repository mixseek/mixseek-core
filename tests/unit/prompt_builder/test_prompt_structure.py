"""デフォルトプロンプトテンプレートの構造契約テスト。

Frontmatter（実行メタ情報）と XML タグ（外部由来テキストの境界）が
期待どおりに構成されていることを検証する。

Issue: #153
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

import pytest

from mixseek.config.schema import PromptBuilderSettings
from mixseek.prompt_builder.builder import UserPromptBuilder
from mixseek.prompt_builder.models import EvaluatorPromptContext, RoundPromptContext
from mixseek.round_controller.models import RoundState

pytestmark = pytest.mark.unit

# Frontmatter は必ずプロンプト先頭に置かれる（前方に空行やテキストがあってはならない）
_FRONTMATTER_PATTERN = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)

# 外部由来テキストを埋め込むコンテキストブロックのタグ一覧
TEAM_CONTEXT_TAGS = ("user_task", "leader_board", "submission_history")
EVALUATOR_CONTEXT_TAGS = ("user_task", "submission")
JUDGMENT_CONTEXT_TAGS = ("user_task", "submission_history", "leader_board")

# 旧フォーマットの Markdown 見出し（廃止済みであることを確認するために使う）
LEGACY_HEADINGS = (
    "# ユーザから指定されたタスク",
    "# 現在のラウンド",
    "# 現在のリーダーボード",
    "# 過去の提出履歴",
    "# 提出内容",
    "# 提出履歴",
    "# リーダーボード",
)


def parse_frontmatter(prompt: str) -> dict[str, str]:
    """プロンプト冒頭の Frontmatter を ``key: value`` の dict として取り出す。

    Args:
        prompt: 整形済みプロンプト文字列

    Returns:
        Frontmatter のキーと値の dict

    Raises:
        AssertionError: 冒頭に Frontmatter ブロックが存在しない場合
    """
    match = _FRONTMATTER_PATTERN.match(prompt)
    if match is None:
        raise AssertionError("プロンプト冒頭に Frontmatter ブロックがありません")

    parsed: dict[str, str] = {}
    for line in match.group("body").splitlines():
        key, separator, value = line.partition(":")
        assert separator, f"Frontmatter に 'key: value' 形式でない行があります: {line!r}"
        parsed[key.strip()] = value.strip()
    return parsed


def extract_tag(prompt: str, tag: str) -> str:
    """XML タグで囲まれたブロックの中身を取り出す。

    Args:
        prompt: 整形済みプロンプト文字列
        tag: 取り出したいタグ名（例: ``user_task``）

    Returns:
        タグに囲まれた本文（前後の改行は含まない）

    Raises:
        AssertionError: 対象タグのブロックが存在しない場合
    """
    pattern = re.compile(rf"<{tag}>\n(?P<body>.*?)\n</{tag}>", re.DOTALL)
    match = pattern.search(prompt)
    if match is None:
        raise AssertionError(f"<{tag}> ブロックが見つかりません")
    return match.group("body")


def assert_tag_balanced(prompt: str, tag: str) -> None:
    """区切りとしての開始タグ・終了タグが 1 度ずつだけ出現することを検証する。

    テンプレートの「入力の読み方」では説明のためにタグ名を本文中で参照するため、
    行単独で出現するもの（＝実際のブロック区切り）のみを数える。

    Args:
        prompt: 整形済みプロンプト文字列
        tag: 検証対象のタグ名
    """
    open_count = len(re.findall(rf"^<{tag}>$", prompt, re.MULTILINE))
    close_count = len(re.findall(rf"^</{tag}>$", prompt, re.MULTILINE))
    assert open_count == 1, f"<{tag}> の開始タグが 1 個ではありません（{open_count} 個）"
    assert close_count == 1, f"</{tag}> の終了タグが 1 個ではありません（{close_count} 個）"


def make_round_state(round_number: int, submission_content: str, score: float = 75.5) -> RoundState:
    """テスト用の RoundState を生成する。

    Args:
        round_number: ラウンド番号
        submission_content: 提出内容
        score: 評価スコア

    Returns:
        RoundState インスタンス
    """
    now = datetime.now(UTC)
    return RoundState(
        round_number=round_number,
        submission_content=submission_content,
        evaluation_score=score,
        score_details={},
        round_started_at=now,
        round_ended_at=now,
    )


def make_round_context(
    *,
    user_prompt: str = "データ分析タスク",
    round_number: int = 1,
    round_history: list[RoundState] | None = None,
) -> RoundPromptContext:
    """テスト用の RoundPromptContext を生成する（store は常に None）。

    Args:
        user_prompt: ユーザから指定されたタスク
        round_number: 現在のラウンド番号
        round_history: 過去のラウンド履歴

    Returns:
        RoundPromptContext インスタンス
    """
    return RoundPromptContext(
        user_prompt=user_prompt,
        round_number=round_number,
        round_history=round_history if round_history is not None else [],
        team_id="team1",
        team_name="Alpha",
        execution_id="exec1",
        store=None,
    )


def build_builder() -> UserPromptBuilder:
    """デフォルト設定の UserPromptBuilder を生成する。

    Returns:
        UserPromptBuilder インスタンス
    """
    return UserPromptBuilder(settings=PromptBuilderSettings(), store=None)


# Markdown 見出し・区切り線・コードフェンスを含む、構造を壊しやすいユーザ指示
MARKDOWN_HEAVY_USER_PROMPT = """---
title: 偽の Frontmatter
---

# 見出し1

## 見出し2

# 過去の提出履歴
これはユーザが書いたタスク本文であり、システムのセクションではない。

```python
print("---")
```
"""

# LLM 生成物を模した、Markdown 見出しを含む提出内容
MARKDOWN_HEAVY_SUBMISSION = """# AUD/NZD 金融政策レポート

## 市場動向

本文。

## ラウンド 99
紛らわしい見出し。
"""


class TestTeamPromptFrontmatter:
    """team_user_prompt の Frontmatter に関するテスト。"""

    async def test_prompt_starts_with_frontmatter(self) -> None:
        """プロンプトが Frontmatter ブロックで始まる。"""
        prompt = await build_builder().build_team_prompt(make_round_context())

        assert prompt.startswith("---\n")

    async def test_frontmatter_contains_datetime_and_round_number(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Frontmatter に current_datetime と round_number が含まれる。"""
        monkeypatch.delenv("TZ", raising=False)

        prompt = await build_builder().build_team_prompt(make_round_context(round_number=3))
        frontmatter = parse_frontmatter(prompt)

        assert set(frontmatter) == {"current_datetime", "round_number"}
        assert frontmatter["round_number"] == "3"
        assert frontmatter["current_datetime"].startswith(str(datetime.now(UTC).year))

    async def test_frontmatter_survives_markdown_heavy_user_prompt(self) -> None:
        """ユーザ指示が `---` で始まっても Frontmatter は壊れない。"""
        prompt = await build_builder().build_team_prompt(
            make_round_context(user_prompt=MARKDOWN_HEAVY_USER_PROMPT, round_number=2)
        )
        frontmatter = parse_frontmatter(prompt)

        assert frontmatter["round_number"] == "2"
        assert "title" not in frontmatter


class TestTeamPromptContextTags:
    """team_user_prompt の XML コンテキストブロックに関するテスト。"""

    async def test_context_blocks_are_xml_tagged(self) -> None:
        """3 つのコンテキストブロックが XML タグで 1 度ずつ囲まれている。"""
        prompt = await build_builder().build_team_prompt(make_round_context())

        for tag in TEAM_CONTEXT_TAGS:
            assert_tag_balanced(prompt, tag)

    async def test_legacy_markdown_headings_are_removed(self) -> None:
        """旧フォーマットのセクション見出しがテンプレートから消えている。"""
        prompt = await build_builder().build_team_prompt(make_round_context())
        # ユーザ指示・履歴由来の混入と区別するため、外部由来テキストを含まない状態で検証する
        template_only = prompt.replace(extract_tag(prompt, "user_task"), "")

        for heading in LEGACY_HEADINGS:
            assert heading not in template_only

    async def test_user_task_block_contains_user_prompt_verbatim(self) -> None:
        """<user_task> ブロックにユーザ指示がそのまま入る。"""
        prompt = await build_builder().build_team_prompt(make_round_context(user_prompt=MARKDOWN_HEAVY_USER_PROMPT))

        assert extract_tag(prompt, "user_task").strip() == MARKDOWN_HEAVY_USER_PROMPT.strip()

    async def test_markdown_heavy_user_prompt_stays_inside_user_task(self) -> None:
        """Markdown を含むユーザ指示が後続ブロックを侵食しない。"""
        prompt = await build_builder().build_team_prompt(make_round_context(user_prompt=MARKDOWN_HEAVY_USER_PROMPT))

        # ユーザ指示に含まれる紛らわしい見出しは <user_task> の内側だけに存在する
        assert prompt.count("# 過去の提出履歴") == 1
        assert "# 過去の提出履歴" in extract_tag(prompt, "user_task")
        # 後続のブロックは欠落していない
        assert_tag_balanced(prompt, "leader_board")
        assert_tag_balanced(prompt, "submission_history")

    async def test_submission_history_block_wraps_history(self) -> None:
        """<submission_history> ブロックに履歴が入る。"""
        history = [make_round_state(1, "First submission")]
        prompt = await build_builder().build_team_prompt(make_round_context(round_number=2, round_history=history))
        history_block = extract_tag(prompt, "submission_history")

        assert "## ラウンド 1" in history_block
        assert "First submission" in history_block

    async def test_generated_markdown_stays_inside_submission_tag(self) -> None:
        """LLM 生成物の見出しが <submission> に封じ込められ、ラウンド境界を壊さない。"""
        history = [
            make_round_state(1, MARKDOWN_HEAVY_SUBMISSION),
            make_round_state(2, "Second submission"),
        ]
        prompt = await build_builder().build_team_prompt(make_round_context(round_number=3, round_history=history))
        history_block = extract_tag(prompt, "submission_history")

        # ラウンド区切りは生成物の見出しに埋もれず、ラウンド数と一致する
        assert history_block.count("<submission>") == 2
        assert history_block.count("</submission>") == 2
        assert history_block.count("## ラウンド 1") == 1
        assert history_block.count("## ラウンド 2") == 1
        # 生成物内の紛らわしい見出しは <submission> の内側にある
        first_submission = history_block.split("<submission>")[1].split("</submission>")[0]
        assert "# AUD/NZD 金融政策レポート" in first_submission
        assert "## ラウンド 99" in first_submission

    async def test_empty_history_is_wrapped(self) -> None:
        """履歴が空でも <submission_history> ブロックは存在する。"""
        prompt = await build_builder().build_team_prompt(make_round_context())

        assert extract_tag(prompt, "submission_history") == "まだ過去のSubmissionはありません。"


class TestEvaluatorPromptStructure:
    """evaluator_user_prompt の構造に関するテスト。"""

    def test_frontmatter_contains_datetime_only(self) -> None:
        """Frontmatter は current_datetime のみを持つ。"""
        context = EvaluatorPromptContext(user_query="Pythonとは？", submission="プログラミング言語です。")

        prompt = build_builder().build_evaluator_prompt(context)

        assert set(parse_frontmatter(prompt)) == {"current_datetime"}

    def test_context_blocks_are_xml_tagged(self) -> None:
        """<user_task> と <submission> が 1 度ずつ出現する。"""
        context = EvaluatorPromptContext(user_query="Pythonとは？", submission="プログラミング言語です。")

        prompt = build_builder().build_evaluator_prompt(context)

        for tag in EVALUATOR_CONTEXT_TAGS:
            assert_tag_balanced(prompt, tag)

    def test_submission_is_isolated_from_instructions(self) -> None:
        """Markdown を含む提出内容が <submission> の内側に留まる。"""
        context = EvaluatorPromptContext(
            user_query=MARKDOWN_HEAVY_USER_PROMPT,
            submission=MARKDOWN_HEAVY_SUBMISSION,
        )

        prompt = build_builder().build_evaluator_prompt(context)

        assert extract_tag(prompt, "user_task").strip() == MARKDOWN_HEAVY_USER_PROMPT.strip()
        assert extract_tag(prompt, "submission").strip() == MARKDOWN_HEAVY_SUBMISSION.strip()


class TestJudgmentPromptStructure:
    """judgment_user_prompt の構造に関するテスト。"""

    async def test_frontmatter_contains_datetime_and_round_number(self) -> None:
        """Frontmatter に current_datetime と round_number が含まれる。"""
        history = [make_round_state(1, "First submission")]

        prompt = await build_builder().build_judgment_prompt(make_round_context(round_number=2, round_history=history))

        assert set(parse_frontmatter(prompt)) == {"current_datetime", "round_number"}
        assert parse_frontmatter(prompt)["round_number"] == "2"

    async def test_context_blocks_are_xml_tagged(self) -> None:
        """3 つのコンテキストブロックが XML タグで 1 度ずつ囲まれている。"""
        history = [make_round_state(1, "First submission")]

        prompt = await build_builder().build_judgment_prompt(make_round_context(round_number=2, round_history=history))

        for tag in JUDGMENT_CONTEXT_TAGS:
            assert_tag_balanced(prompt, tag)

    async def test_generated_markdown_stays_inside_submission_tag(self) -> None:
        """LLM 生成物の見出しが <submission> に封じ込められる。"""
        history = [make_round_state(1, MARKDOWN_HEAVY_SUBMISSION)]

        prompt = await build_builder().build_judgment_prompt(make_round_context(round_number=2, round_history=history))
        history_block = extract_tag(prompt, "submission_history")

        assert history_block.count("<submission>") == 1
        assert "# AUD/NZD 金融政策レポート" in history_block.split("<submission>")[1]
