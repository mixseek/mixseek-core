"""Common field mapping utilities for Member Agent configuration.

このモジュールは、TOMLファイルのフィールド名を MemberAgentSettings の内部フィールド名に
統一的にマッピングするユーティリティを提供します。

以下の3つの経路すべてで同一のマッピングロジックを使用することで、
どの経路から作成しても同一の MemberAgentSettings が生成されることを保証します:

1. MemberAgentTomlSource._load_and_convert()
2. TeamTomlSource._resolve_member_reference()
3. TeamTomlSource._process_inline_member()
"""

from typing import Any


def normalize_member_agent_fields(agent_data: dict[str, Any]) -> dict[str, Any]:
    """Member Agent フィールド名を正規化して MemberAgentSettings 形式にマッピング。

    TOMLファイルの推奨キー名を内部フィールド名に変換:
    - name → agent_name
    - type → agent_type
    - description → tool_description (tool_description が未設定の場合のみ)

    system_instruction のフラット化:
    - [agent.system_instruction] text = "..." → system_instruction = "..."

    Args:
        agent_data: TOMLファイルの [agent] セクションまたはインライン member 設定

    Returns:
        MemberAgentSettings 形式にマッピングされた辞書
    """
    # system_instruction のフラット化
    system_instruction = None
    if "system_instruction" in agent_data:
        if isinstance(agent_data["system_instruction"], dict):
            system_instruction = agent_data["system_instruction"].get("text")
        else:
            system_instruction = agent_data["system_instruction"]

    # 基本設定をマッピング
    mapped_data = {
        # 名前とタイプのマッピング (推奨: name/type → 内部: agent_name/agent_type)
        # 後方互換性のため、レガシーキー (agent_name/agent_type) もサポート
        "agent_name": agent_data.get("name") or agent_data.get("agent_name"),
        "agent_type": agent_data.get("type") or agent_data.get("agent_type"),
        # Tool設定
        "tool_name": agent_data.get("tool_name"),
        "tool_description": agent_data.get("tool_description") or agent_data.get("description"),
        # モデル設定
        "model": agent_data.get("model"),
        "temperature": agent_data.get("temperature"),
        "max_tokens": agent_data.get("max_tokens"),
        # プロンプト設定
        "system_instruction": system_instruction,
        "system_prompt": agent_data.get("system_prompt"),
        # タイムアウトとリトライ設定
        "timeout_seconds": agent_data.get("timeout_seconds"),
        "max_retries": agent_data.get("max_retries"),
        # LLMパラメータ
        "stop_sequences": agent_data.get("stop_sequences"),
        "top_p": agent_data.get("top_p"),
        "seed": agent_data.get("seed"),
        # カスタムAgent設定 (Issue #146)
        "plugin": agent_data.get("plugin"),
        # 直接指定を優先、未指定時はmetadata内のネスト指定を参照（後方互換性）
        "tool_settings": agent_data["tool_settings"]
        if "tool_settings" in agent_data
        else (agent_data.get("metadata") or {}).get("tool_settings"),
    }

    # tool_description がNoneまたは空の場合、デフォルト値を生成
    if not mapped_data.get("tool_description"):
        agent_name = mapped_data.get("agent_name", "agent")
        mapped_data["tool_description"] = f"Delegate task to {agent_name}"

    # Noneの値を除去（ただし、tool_descriptionは必須なので削除しない）
    mapped_data = {k: v for k, v in mapped_data.items() if v is not None or k == "tool_description"}

    return mapped_data


def merge_member_agent_fields(base_config: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """ベース設定に上書き設定をマージ。

    TeamTomlSource の config 参照形式で、team.toml 側で tool_name や tool_description を
    上書き指定した場合に使用します。

    Args:
        base_config: ベース設定（外部TOMLファイルから読み込んだ設定）
        overrides: 上書き設定（team.toml の [[team.members]] に記載された設定）

    Returns:
        マージされた設定
    """
    merged = dict(base_config)

    # tool_name と tool_description は上書き可能
    # None でない値のみで上書き（None での上書きを防ぐ）
    if overrides.get("tool_name") is not None:
        merged["tool_name"] = overrides["tool_name"]
    if overrides.get("tool_description") is not None:
        merged["tool_description"] = overrides["tool_description"]

    return merged
