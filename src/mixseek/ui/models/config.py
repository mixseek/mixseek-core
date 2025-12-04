"""Pydantic models for configuration files."""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class ConfigFile(BaseModel):
    """TOML設定ファイルのメタデータ."""

    file_path: Path = Field(..., description="設定ファイルの絶対パス")
    file_name: str = Field(..., description="ファイル名（拡張子含む）")
    last_modified: datetime = Field(..., description="最終更新日時")
    content: str = Field(..., description="TOML文字列（生データ）")

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: Path) -> Path:
        """ファイルパスが存在し、.toml拡張子を持つことを検証."""
        if not v.exists():
            raise ValueError(f"File does not exist: {v}")
        if v.suffix != ".toml":
            raise ValueError(f"File must have .toml extension: {v}")
        return v

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, v: str) -> str:
        """ファイル名が空でないことを検証."""
        if not v.strip():
            raise ValueError("File name cannot be empty")
        return v

    @property
    def display_name(self) -> str:
        """UIで表示するファイル名（拡張子なし）."""
        return self.file_name.replace(".toml", "")

    class Config:
        frozen = False  # Streamlit session_stateで変更可能にする


class MemberAgent(BaseModel):
    """Member Agent定義."""

    agent_id: str = Field(..., description="Agent識別子（TOML内のキー）")
    provider: str = Field(..., description="プロバイダー名（例: anthropic, google-adk）")
    model: str = Field(..., description="モデル名（例: claude-sonnet-4-5）")
    system_prompt: str | None = Field(None, description="システムプロンプト")
    temperature: float | None = Field(None, ge=0.0, le=2.0, description="Temperature設定")
    max_tokens: int | None = Field(None, gt=0, description="最大トークン数")

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, v: str) -> str:
        """Agent IDが空でないことを検証."""
        if not v.strip():
            raise ValueError("Agent ID cannot be empty")
        return v

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """プロバイダー名が空でないことを検証."""
        if not v.strip():
            raise ValueError("Provider cannot be empty")
        return v


class LeaderAgent(BaseModel):
    """Leader Agent定義."""

    agent_id: str = Field(..., description="Agent識別子（TOML内のキー）")
    provider: str = Field(..., description="プロバイダー名（例: anthropic, google-adk）")
    model: str = Field(..., description="モデル名（例: claude-sonnet-4-5）")
    system_prompt: str | None = Field(None, description="システムプロンプト")
    temperature: float | None = Field(None, ge=0.0, le=2.0, description="Temperature設定")
    max_tokens: int | None = Field(None, gt=0, description="最大トークン数")

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, v: str) -> str:
        """Agent IDが空でないことを検証."""
        if not v.strip():
            raise ValueError("Agent ID cannot be empty")
        return v

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """プロバイダー名が空でないことを検証."""
        if not v.strip():
            raise ValueError("Provider cannot be empty")
        return v


class Orchestration(BaseModel):
    """オーケストレーション定義."""

    orchestration_id: str = Field(..., description="オーケストレーション識別子")
    leader_agent_id: str = Field(..., description="使用するLeader AgentのID")
    member_agent_ids: list[str] = Field(..., description="使用するMember AgentのIDリスト")
    description: str | None = Field(None, description="オーケストレーションの説明")

    @field_validator("orchestration_id")
    @classmethod
    def validate_orchestration_id(cls, v: str) -> str:
        """オーケストレーションIDが空でないことを検証."""
        if not v.strip():
            raise ValueError("Orchestration ID cannot be empty")
        return v

    @field_validator("leader_agent_id")
    @classmethod
    def validate_leader_agent_id(cls, v: str) -> str:
        """Leader Agent IDが空でないことを検証."""
        if not v.strip():
            raise ValueError("Leader Agent ID cannot be empty")
        return v

    @field_validator("member_agent_ids")
    @classmethod
    def validate_member_agent_ids(cls, v: list[str]) -> list[str]:
        """Member Agent IDリストが空でないことを検証."""
        if not v:
            raise ValueError("At least one member agent is required")
        if any(not agent_id.strip() for agent_id in v):
            raise ValueError("Member Agent ID cannot be empty")
        return v

    @property
    def display_name(self) -> str:
        """UIで表示する名前."""
        return self.orchestration_id


class OrchestrationOption(BaseModel):
    """オーケストレーション選択肢（UI用）."""

    config_file_name: str = Field(..., description="設定ファイル名")
    orchestration_id: str = Field(..., description="オーケストレーションID")
    display_label: str = Field(..., description="UIに表示するラベル")

    @classmethod
    def from_config_and_orch(cls, config_file_name: str, orchestration: Orchestration) -> "OrchestrationOption":
        """ConfigFileとOrchestrationから生成."""
        display_label = f"{config_file_name} - {orchestration.orchestration_id}"
        return cls(
            config_file_name=config_file_name,
            orchestration_id=orchestration.orchestration_id,
            display_label=display_label,
        )

    class Config:
        frozen = True  # イミュータブル
