"""Configuration view and display service for CLI commands.

This module provides classes and functions to display configuration settings
in human-readable formats (table, JSON, etc.) for the CLI commands.

Article 9 Compliance:
- Configuration values are explicitly sourced from ConfigurationManager
- No implicit defaults or assumptions
- Proper error handling and propagation
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic_core import PydanticUndefined
from pydantic_settings import BaseSettings

from mixseek.config.manager import ConfigurationManager
from mixseek.config.schema import (
    EvaluatorSettings,
    JudgmentSettings,
    LeaderAgentSettings,
    MemberAgentSettings,
    OrchestratorSettings,
    PromptBuilderSettings,
    TeamSettings,
    UISettings,
)


@dataclass
class SettingInfo:
    """Information about a single configuration setting.

    Attributes:
        key: Unique identifier combining class name and field name.
            (e.g., 'OrchestratorSettings.timeout_per_team_seconds')
        raw_key: Raw field name without class prefix.
            (e.g., 'timeout_per_team_seconds')
        class_name: Settings class name.
            (e.g., 'OrchestratorSettings', 'LeaderAgentSettings')
        current_value: Current value of the setting
        default_value: Default value from settings class
        source: Source of current value (e.g., 'TOML', 'environment_variables', 'default')
        source_type: Source type code (e.g., 'toml', 'env', 'init', 'default')
        value_type: Python type of the value (e.g., 'int', 'str', 'float')
        description: Field description from the settings class
        timestamp: When the value was loaded (None if from default)
        is_overridden: True if current_value != default_value
    """

    key: str
    raw_key: str
    class_name: str
    current_value: Any
    default_value: Any
    source: str
    source_type: str
    value_type: str
    description: str = ""
    timestamp: datetime | None = None
    is_overridden: bool = False


class ConfigViewService:
    """Service for viewing and formatting configuration settings.

    Provides methods to:
    - Get all settings with sources and defaults
    - Get specific settings by key
    - Filter to overridden settings only
    - Format output in various formats (table, JSON, etc.)
    """

    # Map of settings classes for loading all settings
    # These settings are displayed by `mixseek config show` command
    SETTINGS_CLASSES: list[type[BaseSettings]] = [
        OrchestratorSettings,  # Orchestration settings
        UISettings,  # Streamlit UI settings
        LeaderAgentSettings,  # Leader Agent settings
        MemberAgentSettings,  # Member Agent settings
        EvaluatorSettings,  # Evaluator settings
        JudgmentSettings,  # Judgment (round continuation decision) settings
        PromptBuilderSettings,  # UserPromptBuilder settings
        TeamSettings,  # Team settings (Leader + Members)
    ]

    def __init__(self, manager: ConfigurationManager, config_data: dict[str, Any] | None = None) -> None:
        """Initialize the service with a ConfigurationManager instance.

        Args:
            manager: Configured ConfigurationManager instance
            config_data: Optional config data from RecursiveConfigLoader (for evaluator/judgment/prompt_builder)
        """
        self.manager = manager
        self.config_data = config_data

    def get_all_settings(self) -> dict[str, SettingInfo]:
        """Get all configuration settings with their details.

        Returns:
            Dictionary mapping unique keys (ClassName.field_name) to SettingInfo objects.
            Ensures no collisions between fields with the same name in different classes.
        """
        all_settings: dict[str, SettingInfo] = {}

        for settings_class in self.SETTINGS_CLASSES:
            class_name = settings_class.__name__
            try:
                # Load settings for this class
                # For EvaluatorSettings/JudgmentSettings/PromptBuilderSettings,
                # use config_data if available (to respect orchestrator_settings paths)
                standalone_classes = ["EvaluatorSettings", "JudgmentSettings", "PromptBuilderSettings"]
                if self.config_data and class_name in standalone_classes:
                    setting_key = class_name.replace("Settings", "").lower()
                    if setting_key in self.config_data:
                        settings = self.config_data[setting_key]["settings"]
                    else:
                        settings = None
                else:
                    settings = self.manager.load_settings(settings_class)
            except Exception:
                # If loading fails (e.g., missing required field), still try to get field info
                # This allows viewing defaults even when some settings can't be loaded
                settings = None

            # Get field information from the Pydantic model
            for field_name, field_info in settings_class.model_fields.items():
                if settings is not None:
                    # Get trace information if available
                    trace = self.manager.get_trace_info(settings, field_name)

                    # Get current and default values
                    current_value = getattr(settings, field_name)
                    default_value = self._get_default_value(field_info)

                    # Determine if overridden
                    is_overridden = current_value != default_value
                else:
                    # Can't load settings, so show defaults only
                    trace = None
                    current_value = None
                    default_value = self._get_default_value(field_info)
                    is_overridden = False

                # Get type string
                value_type = self._get_type_string(field_info.annotation)

                # Create unique key combining class name and field name
                unique_key = f"{class_name}.{field_name}"

                # Create SettingInfo
                setting_info = SettingInfo(
                    key=unique_key,
                    raw_key=field_name,
                    class_name=class_name,
                    current_value=current_value,
                    default_value=default_value,
                    source=trace.source_name if trace else "default",
                    source_type=trace.source_type if trace else "default",
                    value_type=value_type,
                    description=field_info.description or "",
                    timestamp=trace.timestamp if trace else None,
                    is_overridden=is_overridden,
                )

                all_settings[unique_key] = setting_info

        return all_settings

    def get_setting(self, key: str) -> SettingInfo | None:
        """Get a specific setting by key (case-insensitive).

        Supports matching by:
        - Unique key: 'LeaderAgentSettings.model'
        - Raw field name: 'timeout_per_team_seconds' (returns first match if multiple classes have it)
        - Case-insensitive variants

        Args:
            key: Setting key to retrieve

        Returns:
            SettingInfo for the key, or None if not found
        """
        all_settings = self.get_all_settings()

        # Try exact match first (full unique key or raw field name)
        if key in all_settings:
            return all_settings[key]

        # Try case-insensitive exact match
        key_lower = key.lower()
        for setting_key, setting_info in all_settings.items():
            if setting_key.lower() == key_lower:
                return setting_info

        # Try matching just the raw field name (case-insensitive)
        # This handles the case where user types 'model' and wants the first match
        for setting_key, setting_info in all_settings.items():
            if setting_info.raw_key.lower() == key_lower:
                return setting_info

        return None

    def get_overridden_settings(self) -> dict[str, SettingInfo]:
        """Get only settings that are overridden from defaults.

        Returns:
            Dictionary of overridden settings
        """
        all_settings = self.get_all_settings()
        return {k: v for k, v in all_settings.items() if v.is_overridden}

    def format_table(self, settings: dict[str, SettingInfo] | None = None) -> str:
        """Format settings as a human-readable table.

        Args:
            settings: Settings to format (defaults to all settings)

        Returns:
            Table formatted as string
        """
        if settings is None:
            settings = self.get_all_settings()

        if not settings:
            return "No settings found."

        # Build table rows
        rows = []
        rows.append(
            [
                "Key",
                "Value",
                "Default",
                "Source",
                "Type",
                "Overridden",
            ]
        )

        for key in sorted(settings.keys()):
            info = settings[key]
            rows.append(
                [
                    key,
                    self._mask_value(info.raw_key, info.current_value),
                    self._mask_value(info.raw_key, info.default_value),
                    info.source,
                    info.value_type,
                    "Yes" if info.is_overridden else "No",
                ]
            )

        # Calculate column widths
        col_widths = [max(len(str(row[i])) for row in rows) for i in range(len(rows[0]))]

        # Format rows
        lines = []
        for i, row in enumerate(rows):
            formatted_row = " | ".join(str(cell).ljust(col_widths[j]) for j, cell in enumerate(row))
            lines.append(formatted_row)
            if i == 0:
                # Add separator after header
                lines.append("-" * len(formatted_row))

        return "\n".join(lines)

    def format_single(self, setting: SettingInfo) -> str:
        """Format a single setting with full details.

        Args:
            setting: SettingInfo to format

        Returns:
            Formatted string with setting details
        """
        lines = [
            f"Class: {setting.class_name}",
            f"Key: {setting.raw_key}",
            f"Current Value: {self._mask_value(setting.raw_key, setting.current_value)}",
            f"Default Value: {self._mask_value(setting.raw_key, setting.default_value)}",
            f"Source: {setting.source} ({setting.source_type})",
            f"Type: {setting.value_type}",
            f"Overridden: {'Yes' if setting.is_overridden else 'No'}",
        ]

        if setting.timestamp:
            lines.append(f"Timestamp: {setting.timestamp.isoformat()}")

        if setting.description:
            lines.append(f"Description: {setting.description}")

        return "\n".join(lines)

    def format_single_json(self, setting: SettingInfo) -> str:
        """Format a single setting as JSON.

        Args:
            setting: SettingInfo to format

        Returns:
            JSON formatted string with setting details
        """
        result = {
            "class": setting.class_name,
            "key": setting.raw_key,
            "current_value": self._mask_value(setting.raw_key, setting.current_value),
            "default_value": self._mask_value(setting.raw_key, setting.default_value),
            "source": setting.source,
            "source_type": setting.source_type,
            "type": setting.value_type,
            "overridden": setting.is_overridden,
        }

        if setting.timestamp:
            result["timestamp"] = setting.timestamp.isoformat()

        if setting.description:
            result["description"] = setting.description

        return json.dumps(result, indent=2, ensure_ascii=False)

    def format_schema_table(self, settings: dict[str, SettingInfo] | None = None) -> str:
        """Format settings schema information as a human-readable table.

        This method displays only schema information (available settings, defaults, types, descriptions)
        without actual values, sources, or override status. Used by `config list` command.

        Args:
            settings: Settings to format (defaults to all settings)

        Returns:
            Table formatted as string with Key, Default, Type, Description columns
        """
        if settings is None:
            settings = self.get_all_settings()

        if not settings:
            return "No settings found."

        # Build table rows
        rows = []
        rows.append(
            [
                "Key",
                "Default",
                "Type",
                "Description",
            ]
        )

        for key in sorted(settings.keys()):
            info = settings[key]
            rows.append(
                [
                    key,
                    self._mask_value(info.raw_key, info.default_value),
                    info.value_type,
                    info.description or "(no description)",
                ]
            )

        # Calculate column widths
        col_widths = [max(len(str(row[i])) for row in rows) for i in range(len(rows[0]))]

        # Format rows
        lines = []
        for i, row in enumerate(rows):
            formatted_row = " | ".join(str(cell).ljust(col_widths[j]) for j, cell in enumerate(row))
            lines.append(formatted_row)
            if i == 0:
                # Add separator after header
                lines.append("-" * len(formatted_row))

        return "\n".join(lines)

    def format_schema_json(self, settings: dict[str, SettingInfo] | None = None) -> str:
        """Format settings schema information as JSON.

        This method displays only schema information (available settings, defaults, types, descriptions)
        without actual values, sources, or override status. Used by `config list --output-format json`.

        Args:
            settings: Settings to format (defaults to all settings)

        Returns:
            JSON formatted as string with array of setting objects
        """
        if settings is None:
            settings = self.get_all_settings()

        if not settings:
            return json.dumps([])

        # Build array of setting objects
        settings_list = []
        for key in sorted(settings.keys()):
            info = settings[key]
            settings_list.append(
                {
                    "key": key,
                    "class_name": info.class_name,
                    "raw_key": info.raw_key,
                    "default": self._mask_value(info.raw_key, info.default_value),
                    "type": info.value_type,
                    "description": info.description or "",
                }
            )

        return json.dumps(settings_list, indent=2, ensure_ascii=False)

    def format_list(self) -> str:
        """Format all available settings as a list with descriptions.

        Returns:
            List formatted as string
        """
        all_settings = self.get_all_settings()

        if not all_settings:
            return "No settings found."

        lines = ["Available Configuration Settings:\n"]

        # Group by type (required vs optional)
        required = {}
        optional = {}

        for key, info in sorted(all_settings.items()):
            # Simple heuristic: if default is None, it might be required
            if info.default_value is None and "workspace" in key.lower():
                required[key] = info
            else:
                optional[key] = info

        if required:
            lines.append("[Required]")
            for key, info in sorted(required.items()):
                lines.append(f"  {key} ({info.value_type})")
                if info.description:
                    lines.append(f"    Description: {info.description}")
                lines.append(f"    Default: {info.default_value} (must be set)")
                lines.append("")

        if optional:
            lines.append("\n[Optional]")
            for key, info in sorted(optional.items()):
                lines.append(f"  {key} ({info.value_type})")
                if info.description:
                    lines.append(f"    Description: {info.description}")
                lines.append(f"    Default: {info.default_value}")
                lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _get_default_value(field_info: Any) -> Any:
        """Get default value from field info, considering default_factory.

        Args:
            field_info: Pydantic FieldInfo

        Returns:
            Default value or None if no default is defined
        """
        # Check if field has a regular default value
        if field_info.default is not PydanticUndefined:
            return field_info.default

        # Check if field has a default_factory
        if field_info.default_factory is not None:
            return field_info.default_factory()

        # No default defined
        return None

    def format_hierarchical(self, config_data: dict[str, Any]) -> str:
        """Format hierarchical configuration data (orchestrator → team → member).

        This method displays configuration in a hierarchical indented format:
        - orchestrator level: no indent
        - team level: 2-space indent
        - member level: 4-space indent

        Args:
            config_data: Dictionary returned by RecursiveConfigLoader.load_orchestrator_with_references()
                        Expected structure:
                        {
                            "orchestrator": OrchestratorSettings instance,
                            "teams": List of team data with members,
                            "source_file": Path to orchestrator TOML
                        }

        Returns:
            Formatted hierarchical string

        Phase 13 T105: FR-041
        """
        lines = []

        # Orchestrator level (no indent)
        orchestrator = config_data.get("orchestrator")
        source_file = config_data.get("source_file")

        if orchestrator:
            lines.append(f"[orchestrator] ({source_file})")
            lines.append(self._format_settings_fields(orchestrator, indent=0))
        else:
            lines.append("[orchestrator] (no data)")

        # Teams level (2-space indent)
        teams = config_data.get("teams", [])
        if teams:
            lines.append("")
            for team_idx, team_data in enumerate(teams, start=1):
                team_settings = team_data.get("team_settings")
                team_source = team_data.get("source_file")
                members = team_data.get("members", [])

                lines.append(f"  [team {team_idx}] ({team_source})")
                if team_settings:
                    lines.append(self._format_settings_fields(team_settings, indent=2))
                else:
                    lines.append("    (no team data)")

                # Members level (4-space indent)
                if members:
                    lines.append("")
                    for member_idx, member_data in enumerate(members, start=1):
                        member_settings = member_data.get("member_settings")
                        member_source = member_data.get("source_file")

                        source_str = f" ({member_source})" if member_source else ""
                        lines.append(f"    [member {member_idx}]{source_str}")
                        if member_settings:
                            lines.append(self._format_settings_fields(member_settings, indent=4))
                        else:
                            lines.append("      (no member data)")
                        lines.append("")

        # Standalone settings (same level as orchestrator/teams)
        # Display evaluator, judgment, and prompt_builder if present
        for setting_name in ["evaluator", "judgment", "prompt_builder"]:
            setting_data = config_data.get(setting_name)
            if setting_data:
                settings_obj = setting_data.get("settings")
                source_file = setting_data.get("source_file")
                lines.append("")
                source_str = f" ({'None' if source_file is None else source_file})"
                lines.append(f"[{setting_name}]{source_str}")
                if settings_obj:
                    lines.append(self._format_settings_fields(settings_obj, indent=0))
                else:
                    lines.append("  (no data)")

        return "\n".join(lines)

    def format_hierarchical_json(self, config_data: dict[str, Any]) -> str:
        """Format hierarchical configuration data as JSON.

        This method converts hierarchical configuration (orchestrator → team → member)
        into a JSON structure for programmatic consumption.

        Args:
            config_data: Dictionary returned by RecursiveConfigLoader.load_orchestrator_with_references()
                        Expected structure:
                        {
                            "orchestrator": OrchestratorSettings instance,
                            "teams": List of team data with members,
                            "source_file": Path to orchestrator TOML
                        }

        Returns:
            JSON formatted string

        Example output:
            {
              "orchestrator": {
                "source_file": "/path/to/orchestrator.toml",
                "settings": {...}
              },
              "teams": [
                {
                  "source_file": "/path/to/team.toml",
                  "settings": {...},
                  "members": [...]
                }
              ]
            }
        """
        result: dict[str, Any] = {}

        # Orchestrator level
        orchestrator = config_data.get("orchestrator")
        source_file = config_data.get("source_file")

        if orchestrator:
            result["orchestrator"] = {
                "source_file": str(source_file) if source_file else None,
                "settings": self._settings_to_dict(orchestrator),
            }
        else:
            result["orchestrator"] = {"source_file": None, "settings": {}}

        # Teams level
        teams = config_data.get("teams", [])
        teams_list = []
        for team_data in teams:
            team_settings = team_data.get("team_settings")
            team_source = team_data.get("source_file")
            members = team_data.get("members", [])

            team_dict: dict[str, Any] = {
                "source_file": str(team_source) if team_source else None,
                "settings": self._settings_to_dict(team_settings) if team_settings else {},
            }

            # Members level
            if members:
                members_list = []
                for member_data in members:
                    member_settings = member_data.get("member_settings")
                    member_source = member_data.get("source_file")

                    member_dict = {
                        "source_file": str(member_source) if member_source else None,
                        "settings": self._settings_to_dict(member_settings) if member_settings else {},
                    }
                    members_list.append(member_dict)

                team_dict["members"] = members_list

            teams_list.append(team_dict)

        # Always include teams key, even if empty
        result["teams"] = teams_list

        # Standalone settings (same level as orchestrator/teams)
        # Add evaluator, judgment, and prompt_builder if present
        for setting_name in ["evaluator", "judgment", "prompt_builder"]:
            setting_data = config_data.get(setting_name)
            if setting_data:
                settings_obj = setting_data.get("settings")
                source_file = setting_data.get("source_file")
                result[setting_name] = {
                    "source_file": str(source_file) if source_file else None,
                    "settings": self._settings_to_dict(settings_obj) if settings_obj else {},
                }

        return json.dumps(result, indent=2, ensure_ascii=False)

    @classmethod
    def _settings_to_dict(cls, settings: BaseSettings | dict[str, Any]) -> dict[str, Any]:
        """Convert Pydantic BaseSettings or dict to a JSON-serializable dictionary.

        Recursively processes nested BaseSettings instances and lists containing BaseSettings.

        Args:
            settings: Pydantic BaseSettings instance or dictionary

        Returns:
            Dictionary with field name -> value mappings (sensitive values masked)
        """
        result: dict[str, Any] = {}

        # Handle both BaseSettings and dict
        if isinstance(settings, dict):
            items: list[tuple[str, Any]] = list(settings.items())
        else:
            # Get all fields from the Pydantic model
            items = [
                (field_name, getattr(settings, field_name, None))
                for field_name in settings.__class__.model_fields.keys()
            ]

        for field_name, value in items:
            # Convert value to JSON-serializable format
            if cls._is_sensitive_field(field_name):
                from mixseek.config.constants import MASKED_VALUE

                result[field_name] = MASKED_VALUE
            elif isinstance(value, (str, int, float, bool)) or value is None:
                result[field_name] = value
            elif isinstance(value, BaseSettings):
                # Recursively convert nested BaseSettings
                result[field_name] = cls._settings_to_dict(value)
            elif isinstance(value, list):
                # Process list items, converting BaseSettings instances
                result[field_name] = [
                    cls._settings_to_dict(item) if isinstance(item, BaseSettings) else item for item in value
                ]
            elif isinstance(value, dict):
                # Process dict values, converting BaseSettings instances
                result[field_name] = {
                    k: cls._settings_to_dict(v) if isinstance(v, BaseSettings) else v for k, v in value.items()
                }
            else:
                # Convert other types to string
                result[field_name] = str(value)

        return result

    @staticmethod
    def _format_settings_fields(settings: BaseSettings | dict[str, Any], indent: int = 0) -> str:
        """Format Pydantic BaseSettings or dict fields as key-value pairs with indentation.

        Args:
            settings: Pydantic BaseSettings instance or dictionary
            indent: Number of spaces for base indentation (2 for team, 4 for member)

        Returns:
            Formatted string with field values
        """
        lines = []
        indent_str = " " * (indent + 2)  # Add 2 more spaces for field indentation

        # Handle both BaseSettings and dict
        if isinstance(settings, dict):
            items: list[tuple[str, Any]] = list(settings.items())
        else:
            # Get all fields from the Pydantic model
            items = [
                (field_name, getattr(settings, field_name, None))
                for field_name in settings.__class__.model_fields.keys()
            ]

        for field_name, value in items:
            # Format the value
            if isinstance(value, (list, dict)):
                # For complex types, use repr for compact display
                value_str = repr(value)
                if len(value_str) > 80:
                    value_str = value_str[:77] + "..."
            else:
                value_str = ConfigViewService._mask_value(field_name, value)

            lines.append(f"{indent_str}{field_name}: {value_str}")

        return "\n".join(lines)

    @staticmethod
    def _get_type_string(annotation: Any) -> str:
        """Get string representation of a type annotation.

        Args:
            annotation: Python type annotation

        Returns:
            String representation of the type
        """
        # Handle common cases
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

        # Handle generic types and unions
        type_str = str(annotation)
        # Clean up common patterns
        type_str = type_str.replace("typing.", "")
        type_str = type_str.replace("<class '", "")
        type_str = type_str.replace("'>", "")

        return type_str

    @staticmethod
    def _is_sensitive_field(field_name: str) -> bool:
        """Check if a field name contains sensitive information patterns.

        Article 9 Compliance: Uses explicit pattern list and exception list (no implicit assumptions).

        Performance: Uses pre-computed frozenset for O(1) membership testing.

        Args:
            field_name: The field name to check

        Returns:
            True if the field name matches any sensitive pattern (case-insensitive),
            unless it's in the exception list
        """
        from mixseek.config.constants import (
            _NON_SENSITIVE_FIELD_EXCEPTIONS_LOWER,
            SENSITIVE_FIELD_PATTERNS,
        )

        field_lower = field_name.lower()

        # Check exception list first (O(1) frozenset lookup)
        if field_lower in _NON_SENSITIVE_FIELD_EXCEPTIONS_LOWER:
            return False

        # Check sensitive patterns
        return any(pattern in field_lower for pattern in SENSITIVE_FIELD_PATTERNS)

    @staticmethod
    def _mask_value(field_name: str, value: Any) -> str:
        """Mask sensitive field values for security.

        Article 9 Compliance: Explicit security policy for sensitive data.

        Args:
            field_name: The field name to check
            value: The value to potentially mask

        Returns:
            Masked value ("[REDACTED]") if field is sensitive, otherwise string representation of value
        """
        from mixseek.config.constants import MASKED_VALUE

        if ConfigViewService._is_sensitive_field(field_name):
            return MASKED_VALUE
        return str(value)
