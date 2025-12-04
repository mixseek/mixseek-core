"""Tests for OrchestratorSettings round configuration"""

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from pydantic import ValidationError

from mixseek.config.schema import OrchestratorSettings


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Create a temporary workspace directory for testing"""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


@pytest.fixture
def clean_env() -> Generator[None]:
    """Clean environment variables before each test"""
    env_vars_to_clean = [
        "MIXSEEK_MAX_ROUNDS",
        "MIXSEEK_MIN_ROUNDS",
        "MIXSEEK_SUBMISSION_TIMEOUT_SECONDS",
        "MIXSEEK_JUDGMENT_TIMEOUT_SECONDS",
    ]
    original_env = {}
    for var in env_vars_to_clean:
        original_env[var] = os.environ.pop(var, None)

    yield

    # Restore original environment
    for var, value in original_env.items():
        if value is not None:
            os.environ[var] = value


class TestRoundConfigurationDefaults:
    """Test default values for round configuration fields"""

    def test_default_round_configuration(self, temp_workspace: Path) -> None:
        """Test that default round configuration values are correct"""
        settings = OrchestratorSettings(workspace_path=temp_workspace)

        assert settings.max_rounds == 5
        assert settings.min_rounds == 2
        assert settings.submission_timeout_seconds == 300
        assert settings.judgment_timeout_seconds == 60

    def test_custom_round_configuration(self, temp_workspace: Path) -> None:
        """Test custom round configuration values"""
        settings = OrchestratorSettings(
            workspace_path=temp_workspace,
            max_rounds=10,
            min_rounds=3,
            submission_timeout_seconds=600,
            judgment_timeout_seconds=120,
        )

        assert settings.max_rounds == 10
        assert settings.min_rounds == 3
        assert settings.submission_timeout_seconds == 600
        assert settings.judgment_timeout_seconds == 120


class TestMaxRoundsConstraints:
    """Test max_rounds field constraints"""

    def test_max_rounds_valid_range(self, temp_workspace: Path) -> None:
        """Test that max_rounds accepts values in valid range [1, 10]"""
        for value in [1, 5, 10]:
            # Adjust min_rounds to be valid with each max_rounds value
            min_val = min(value, 2)  # Ensure min_rounds <= max_rounds
            settings = OrchestratorSettings(workspace_path=temp_workspace, max_rounds=value, min_rounds=min_val)
            assert settings.max_rounds == value

    def test_max_rounds_zero(self, temp_workspace: Path) -> None:
        """Test that max_rounds=0 raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            OrchestratorSettings(workspace_path=temp_workspace, max_rounds=0)

        assert "greater than or equal to 1" in str(exc_info.value).lower()

    def test_max_rounds_negative(self, temp_workspace: Path) -> None:
        """Test that negative max_rounds raises ValidationError"""
        with pytest.raises(ValidationError):
            OrchestratorSettings(workspace_path=temp_workspace, max_rounds=-1)

    def test_max_rounds_exceeds_upper_bound(self, temp_workspace: Path) -> None:
        """Test that max_rounds > 10 raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            OrchestratorSettings(workspace_path=temp_workspace, max_rounds=11)

        assert "less than or equal to 10" in str(exc_info.value).lower()


class TestMinRoundsConstraints:
    """Test min_rounds field constraints"""

    def test_min_rounds_valid_minimum(self, temp_workspace: Path) -> None:
        """Test that min_rounds accepts values >= 1"""
        for value in [1, 2, 5]:
            settings = OrchestratorSettings(workspace_path=temp_workspace, min_rounds=value)
            assert settings.min_rounds == value

    def test_min_rounds_zero(self, temp_workspace: Path) -> None:
        """Test that min_rounds=0 raises ValidationError"""
        with pytest.raises(ValidationError):
            OrchestratorSettings(workspace_path=temp_workspace, min_rounds=0)

    def test_min_rounds_negative(self, temp_workspace: Path) -> None:
        """Test that negative min_rounds raises ValidationError"""
        with pytest.raises(ValidationError):
            OrchestratorSettings(workspace_path=temp_workspace, min_rounds=-1)


class TestTimeoutConstraints:
    """Test timeout field constraints"""

    def test_submission_timeout_positive(self, temp_workspace: Path) -> None:
        """Test that submission_timeout_seconds accepts positive values"""
        for value in [1, 60, 300, 600]:
            settings = OrchestratorSettings(
                workspace_path=temp_workspace,
                submission_timeout_seconds=value,
            )
            assert settings.submission_timeout_seconds == value

    def test_submission_timeout_zero(self, temp_workspace: Path) -> None:
        """Test that submission_timeout_seconds=0 raises ValidationError"""
        with pytest.raises(ValidationError):
            OrchestratorSettings(workspace_path=temp_workspace, submission_timeout_seconds=0)

    def test_submission_timeout_negative(self, temp_workspace: Path) -> None:
        """Test that negative submission_timeout_seconds raises ValidationError"""
        with pytest.raises(ValidationError):
            OrchestratorSettings(workspace_path=temp_workspace, submission_timeout_seconds=-100)

    def test_judgment_timeout_positive(self, temp_workspace: Path) -> None:
        """Test that judgment_timeout_seconds accepts positive values"""
        for value in [1, 30, 60, 120]:
            settings = OrchestratorSettings(
                workspace_path=temp_workspace,
                judgment_timeout_seconds=value,
            )
            assert settings.judgment_timeout_seconds == value

    def test_judgment_timeout_zero(self, temp_workspace: Path) -> None:
        """Test that judgment_timeout_seconds=0 raises ValidationError"""
        with pytest.raises(ValidationError):
            OrchestratorSettings(workspace_path=temp_workspace, judgment_timeout_seconds=0)

    def test_judgment_timeout_negative(self, temp_workspace: Path) -> None:
        """Test that negative judgment_timeout_seconds raises ValidationError"""
        with pytest.raises(ValidationError):
            OrchestratorSettings(workspace_path=temp_workspace, judgment_timeout_seconds=-50)


class TestCrossFieldValidation:
    """Test cross-field validation (min_rounds <= max_rounds)"""

    def test_valid_round_combinations(self, temp_workspace: Path) -> None:
        """Test valid combinations of min_rounds and max_rounds"""
        valid_combinations = [
            (1, 10),
            (2, 5),
            (5, 5),  # boundary: equal values
            (3, 8),
        ]

        for min_val, max_val in valid_combinations:
            settings = OrchestratorSettings(
                workspace_path=temp_workspace,
                min_rounds=min_val,
                max_rounds=max_val,
            )
            assert settings.min_rounds == min_val
            assert settings.max_rounds == max_val

    def test_min_rounds_exceeds_max_rounds(self, temp_workspace: Path) -> None:
        """Test that min_rounds > max_rounds raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            OrchestratorSettings(
                workspace_path=temp_workspace,
                min_rounds=5,
                max_rounds=3,
            )

        error_str = str(exc_info.value).lower()
        assert "min_rounds" in error_str and "max_rounds" in error_str

    def test_error_message_includes_values(self, temp_workspace: Path) -> None:
        """Test that validation error message includes the actual values"""
        with pytest.raises(ValidationError) as exc_info:
            OrchestratorSettings(
                workspace_path=temp_workspace,
                min_rounds=10,
                max_rounds=5,
            )

        error_str = str(exc_info.value)
        # Check for specific values in error message
        assert "10" in error_str and "5" in error_str


class TestEnvironmentVariablePrecedence:
    """Test environment variable precedence (ENV > TOML > Default)"""

    def test_env_var_overrides_default(self, temp_workspace: Path, clean_env: None) -> None:
        """Test that environment variable overrides default value"""
        os.environ["MIXSEEK_MAX_ROUNDS"] = "8"

        settings = OrchestratorSettings(workspace_path=temp_workspace)
        assert settings.max_rounds == 8

    def test_all_round_fields_env_override(self, temp_workspace: Path, clean_env: None) -> None:
        """Test environment variable override for all round fields"""
        os.environ["MIXSEEK_MAX_ROUNDS"] = "9"
        os.environ["MIXSEEK_MIN_ROUNDS"] = "3"
        os.environ["MIXSEEK_SUBMISSION_TIMEOUT_SECONDS"] = "450"
        os.environ["MIXSEEK_JUDGMENT_TIMEOUT_SECONDS"] = "90"

        settings = OrchestratorSettings(workspace_path=temp_workspace)
        assert settings.max_rounds == 9
        assert settings.min_rounds == 3
        assert settings.submission_timeout_seconds == 450
        assert settings.judgment_timeout_seconds == 90

    def test_invalid_env_var_type(self, temp_workspace: Path, clean_env: None) -> None:
        """Test that invalid environment variable type raises ValidationError"""
        os.environ["MIXSEEK_MAX_ROUNDS"] = "not_a_number"

        with pytest.raises(ValidationError):
            OrchestratorSettings(workspace_path=temp_workspace)
