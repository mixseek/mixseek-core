"""Template generation module for TOML configuration files (Phase 10).

This module provides functionality to generate TOML templates for different
configuration components (orchestrator, team, etc.).

Article 9 Compliance:
- Configuration values are explicitly sourced from Pydantic schema
- No implicit defaults or assumptions
- Proper error handling and propagation
"""

from typing import Any

from pydantic_settings import BaseSettings as PydanticBaseSettings

from .schema import (
    EvaluatorSettings,
    JudgmentSettings,
    LeaderAgentSettings,
    MemberAgentSettings,
    OrchestratorSettings,
)


class TemplateGenerator:
    """Generate TOML configuration templates from Pydantic schemas.

    Provides methods to:
    - Generate template from Pydantic settings class
    - Distinguish required vs optional fields
    - Format with appropriate comments and defaults
    """

    # Component to settings class mapping
    COMPONENT_MAP: dict[str, type[PydanticBaseSettings] | None] = {
        "orchestrator": OrchestratorSettings,
        "team": None,  # Special case: combines leader and member
        "leader": LeaderAgentSettings,
        "member": MemberAgentSettings,
        "evaluator": EvaluatorSettings,
        "judgment": JudgmentSettings,
        "config": None,  # Special case: all settings
    }

    def __init__(self) -> None:
        """Initialize template generator."""
        pass

    def generate_template(self, component: str) -> str:
        """Generate TOML template for specified component.

        Args:
            component: Component name ('orchestrator', 'team', 'config', etc.)

        Returns:
            TOML template as string

        Raises:
            ValueError: If component not recognized
        """
        component_lower = component.lower()

        if component_lower == "config":
            # Generate full template with all settings
            return self._generate_full_template()
        elif component_lower == "team":
            # Generate team template with [leader] and [member] sections
            return self._generate_team_template()
        elif component_lower in self.COMPONENT_MAP:
            settings_class = self.COMPONENT_MAP[component_lower]
            if settings_class is None:
                raise ValueError(
                    f"Component '{component}' is not yet implemented. "
                    f"Valid components: {', '.join(self.COMPONENT_MAP.keys())}"
                )
            return self._generate_component_template(settings_class, component_lower)
        else:
            raise ValueError(
                f"Unknown component: '{component}'. Valid components: {', '.join(self.COMPONENT_MAP.keys())}"
            )

    def _generate_full_template(self) -> str:
        """Generate full template with all settings classes."""
        sections = []

        # Generate sections for each settings class
        for component in ["orchestrator", "leader", "member", "evaluator", "judgment", "round_controller"]:
            settings_class = self.COMPONENT_MAP.get(component)
            if settings_class:
                section = self._generate_component_template(settings_class, component)
                sections.append(f"# {component.upper()} SETTINGS\n{section}")

        return "\n\n".join(sections)

    def _generate_team_template(self) -> str:
        """Generate team template with [leader] and [member] sections."""
        leader_section = self._generate_section_template(LeaderAgentSettings, "leader")
        member_section = self._generate_section_template(MemberAgentSettings, "member")

        return f"# Leader Agent Configuration\n{leader_section}\n\n# Member Agent Configuration\n{member_section}"

    def _generate_template_base(
        self,
        settings_class: type[PydanticBaseSettings],
        header_lines: list[str],
        add_blank_lines: bool = False,
    ) -> str:
        """テンプレート生成の共通処理（Template Method）。

        Article 10（DRY原則）準拠：ループ処理の重複を排除。
        Article 11（Refactoring Policy）準拠：既存クラスを直接改善（V2クラス作成なし）。

        Args:
            settings_class: 設定クラス
            header_lines: ヘッダー行のリスト
            add_blank_lines: フィールド間に空行を追加するか

        Returns:
            生成されたテンプレート文字列
        """
        lines = header_lines.copy()

        # 共通のフィールド処理
        for field_name, field_info in settings_class.model_fields.items():
            # Skip 'environment' field (base class)
            if field_name == "environment":
                continue

            # Add field template
            field_template = self._generate_field_template(field_name, field_info)
            lines.append(field_template)

            # Add blank line if requested
            if add_blank_lines:
                lines.append("")

        return "\n".join(lines)

    def _generate_component_template(self, settings_class: type[PydanticBaseSettings], component_name: str) -> str:
        """Generate template for a single settings class."""
        header = [
            f"# {component_name.replace('_', ' ').title()} Configuration",
            "",
        ]
        return self._generate_template_base(settings_class, header, add_blank_lines=True)

    def _generate_section_template(self, settings_class: type[PydanticBaseSettings], section_name: str) -> str:
        """Generate a TOML section for nested settings."""
        header = [f"[{section_name}]"]
        return self._generate_template_base(settings_class, header, add_blank_lines=False)

    def _generate_field_template(self, field_name: str, field_info: Any) -> str:
        """Generate template for a single field with comments."""
        lines = []

        # Add type comment
        type_str = self._get_type_string(field_info.annotation)
        lines.append(f"# Type: {type_str}")

        # Add description if available
        if field_info.description:
            lines.append(f"# Description: {field_info.description}")

        # Add default value info
        if field_info.default is not None:
            default_val = field_info.default
            if isinstance(default_val, str):
                lines.append(f"# Default: {default_val}")
            else:
                lines.append(f"# Default: {default_val}")

        # Add constraints if applicable
        if hasattr(field_info, "ge") and field_info.ge is not None:
            lines.append(f"# Minimum: {field_info.ge}")
        if hasattr(field_info, "le") and field_info.le is not None:
            lines.append(f"# Maximum: {field_info.le}")

        # Add field line
        field_line = self._format_field_line(field_name, field_info)
        lines.append(field_line)

        return "\n".join(lines)

    def _format_field_line(self, field_name: str, field_info: Any) -> str:
        """Format the actual field assignment line."""
        is_required = field_info.is_required()

        if is_required:
            # Required fields: empty string value
            return f'{field_name} = ""'
        else:
            # Optional fields: commented with default value
            default_val = field_info.default
            if isinstance(default_val, str):
                # Escape quotes in string values
                escaped_val = default_val.replace('"', '\\"')
                return f'# {field_name} = "{escaped_val}"'
            elif isinstance(default_val, bool):
                return f"# {field_name} = {str(default_val).lower()}"
            else:
                return f"# {field_name} = {default_val}"

    @staticmethod
    def _get_type_string(annotation: Any) -> str:
        """Get string representation of a type annotation."""
        if annotation is None:
            return "None"
        if annotation is int:
            return "int"
        if annotation is str:
            return "str"
        if annotation is float:
            return "float"
        if annotation is bool:
            return "bool"

        # For complex types, get string representation
        type_str = str(annotation)
        # Clean up common patterns
        type_str = type_str.replace("typing.", "")
        type_str = type_str.replace("<class '", "")
        type_str = type_str.replace("'>", "")
        type_str = type_str.replace("pathlib.", "")

        return type_str
