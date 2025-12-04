"""Configuration Manager for unified settings management."""

import contextvars
import json
import logging
from datetime import UTC
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic_settings import BaseSettings
from pydantic_settings.sources import EnvSettingsSource

from .sources.tracing_source import SourceTrace

if TYPE_CHECKING:
    from .schema import (
        EvaluatorSettings,
        JudgmentSettings,
        MemberAgentSettings,
        OrchestratorSettings,
        PromptBuilderSettings,
        TeamSettings,
    )

# Generic type variable for settings classes (Phase 12: Generic return type)
SettingsT = TypeVar("SettingsT", bound=BaseSettings)

# T097: Context variable for config_file (thread-safe and async-safe)
# This replaces the class attribute to avoid race conditions in concurrent calls
_config_file_context: contextvars.ContextVar[Path | None] = contextvars.ContextVar("config_file", default=None)


class ConfigurationManager:
    """統一的な設定管理マネージャー。

    Pydantic Settingsの機能を統一的なインターフェースで提供し、
    優先順位に基づいた設定の読み込みとトレース情報の管理を行います。
    """

    def __init__(
        self,
        cli_args: dict[str, Any] | None = None,
        workspace: Path | None = None,
        environment: str = "dev",
        config_file: Path | None = None,
    ) -> None:
        """初期化。

        Args:
            cli_args: CLI引数（typerから変換）
            workspace: ワークスペースパス
            environment: 実行環境（dev/staging/prod）
            config_file: TOMLファイルパス（T097: 環境変数アクセスを呼び出し側に移譲）
        """
        self.cli_args = cli_args or {}
        self.workspace = workspace
        self.environment = environment
        self.config_file = config_file

    def load_settings(
        self,
        settings_class: type[SettingsT],
        **extra_kwargs: Any,
    ) -> SettingsT:
        """設定を読み込み。

        優先順位: CLI > 環境変数 > .env > TOML > デフォルト値
        None 値は優先順位チェーンから除外される（Article 9準拠）

        TOML ファイル読み込みは CustomTomlConfigSettingsSource により
        自動的に処理されます。

        Args:
            settings_class: 設定クラス（LeaderAgentSettings等）
            **extra_kwargs: 追加のキーワード引数

        Returns:
            設定インスタンス
        """
        # CLI引数から None 値をフィルタリング（Article 9: Data Accuracy Mandate）
        filtered_cli_args = {k: v for k, v in self.cli_args.items() if v is not None}

        # CLI引数と追加引数をマージ
        init_kwargs: dict[str, Any] = {**filtered_cli_args, **extra_kwargs}

        # 環境を設定
        if "environment" not in init_kwargs:
            init_kwargs["environment"] = self.environment

        # ワークスペースを設定
        if self.workspace and "workspace_path" not in init_kwargs:
            init_kwargs["workspace_path"] = self.workspace

        # T097: config_fileをコンテキスト変数に設定（settings_customise_sources()で使用）
        # Article 9準拠: ConfigurationManager呼び出し側が環境変数読み取りの責任を持つ
        # contextvars使用により、並行処理・ネストされた呼び出しでも安全
        token = _config_file_context.set(self.config_file)

        try:
            # Pydantic Settingsで読み込み
            # 優先順位: init (CLI) > env > .env > TOML > secrets > defaults
            settings = settings_class(**init_kwargs)
            return settings
        finally:
            # クリーンアップ: コンテキスト変数をリセット（元の値に復元）
            _config_file_context.reset(token)
            # Phase 2-4追加: trace_storage context varsもクリアして、テスト間の干渉を防ぐ
            from .schema import _trace_storage_context

            _trace_storage_context.set(None)

    def get_trace_info(
        self,
        settings_instance: BaseSettings,
        field_name: str,
    ) -> SourceTrace | None:
        """設定値のトレース情報を取得（Phase 2: インスタンス対応）。

        Args:
            settings_instance: 設定インスタンス
            field_name: フィールド名

        Returns:
            トレース情報（存在しない場合はNone）

        Note:
            インスタンスメソッドget_trace_info()を呼び出します。
        """
        if hasattr(settings_instance, "get_trace_info"):
            return settings_instance.get_trace_info(field_name)  # type: ignore
        return None

    def print_debug_info(
        self,
        settings: BaseSettings,
        verbose: bool = False,
    ) -> None:
        """デバッグ情報を出力。

        設定値、トレース情報（ソース名、タイムスタンプ）を表示します。

        Args:
            settings: 設定インスタンス
            verbose: 詳細情報を出力するか
        """
        from datetime import datetime

        print("=" * 60)
        print("Configuration Debug Information")
        print("=" * 60)
        print()

        # 設定値とトレース情報
        for field_name in settings.__class__.model_fields:
            value = getattr(settings, field_name)
            trace = self.get_trace_info(settings, field_name)

            # Mask sensitive fields (Article 9: Explicit security policy)
            from mixseek.config.views import ConfigViewService

            masked_value = ConfigViewService._mask_value(field_name, value)
            print(f"{field_name}: {masked_value}")
            if trace:
                print(f"  Source: {trace.source_name} ({trace.source_type})")
                print(f"  Timestamp: {trace.timestamp.isoformat()}")
            else:
                print("  Source: default")
                # Show current timestamp even for defaults in verbose mode
                if verbose:
                    current_time = datetime.now(UTC)
                    print(f"  Timestamp: {current_time.isoformat()}")

            if verbose and trace:
                masked_raw_value = ConfigViewService._mask_value(field_name, trace.value)
                print(f"  Raw value: {masked_raw_value}")
            print()

        print("=" * 60)

    def get_all_defaults(
        self,
        settings_class: type[BaseSettings],
    ) -> dict[str, Any]:
        """すべての設定項目のデフォルト値を取得。

        Args:
            settings_class: 設定クラス

        Returns:
            デフォルト値の辞書
        """
        from collections.abc import Callable
        from typing import cast

        from pydantic_core import PydanticUndefinedType

        defaults: dict[str, Any] = {}
        for field_name, field_info in settings_class.model_fields.items():
            # Skip fields with no default (required fields)
            if isinstance(field_info.default, PydanticUndefinedType):
                continue
            if field_info.default is not None:
                defaults[field_name] = field_info.default
            elif field_info.default_factory is not None:
                # Cast default_factory to Callable for type safety (Article 16)
                factory = cast(Callable[[], Any], field_info.default_factory)
                defaults[field_name] = factory()
        return defaults

    def _load_settings_with_tracing(
        self,
        settings_cls: type[SettingsT],
        toml_source_cls: type,
        toml_file: Path,
        toml_source_name: str,
        **extra_kwargs: Any,
    ) -> SettingsT:
        """設定ファイルをトレース付きで読み込む汎用メソッド（Template Method）。

        Article 10（DRY原則）準拠：4つのload_*_settingsメソッドの共通処理を統合。
        Article 11（Refactoring Policy）準拠：既存クラスを直接改善（V2クラス作成なし）。

        Args:
            settings_cls: 設定クラス（TeamSettings, MemberAgentSettings等）
            toml_source_cls: TOMLソースクラス（TeamTomlSource等）
            toml_file: TOMLファイルパス
            toml_source_name: トレース用のソース名（例: "team.toml"）
            **extra_kwargs: 追加のキーワード引数

        Returns:
            設定インスタンス（トレース情報付き）

        Raises:
            FileNotFoundError: TOMLファイルが見つからない場合
            ValueError: TOML構文エラーまたはバリデーションエラー
        """
        from .sources.tracing_source import TracingSourceWrapper

        # CLI引数から None 値をフィルタリング（Article 9: Data Accuracy Mandate）
        filtered_cli_args = {k: v for k, v in self.cli_args.items() if v is not None}

        # カスタムTOMLソースを作成（workspace対応）
        toml_source = toml_source_cls(
            settings_cls=settings_cls,
            toml_file=toml_file,
            workspace=self.workspace,
        )

        # トレースストレージを初期化
        trace_storage: dict[str, SourceTrace] = {}

        # context varsにトレースストレージを設定（model_post_init()で使用される）
        from .schema import _trace_storage_context

        _trace_storage_context.set(trace_storage)

        # TracingSourceWrapperでラップしてトレーサビリティを確保
        traced_source = TracingSourceWrapper(
            settings_cls,
            toml_source,
            source_name=toml_source_name,
            source_type="toml",
            trace_storage=trace_storage,
        )

        # TOMLソースから手動でデータを取得（トレース付き）
        toml_data = traced_source()

        # 環境変数ソースを作成（トレース付き）
        env_source = EnvSettingsSource(
            settings_cls,
            case_sensitive=settings_cls.model_config.get("case_sensitive", True),
            env_prefix=settings_cls.model_config.get("env_prefix", ""),
            env_nested_delimiter=settings_cls.model_config.get("env_nested_delimiter", "__"),
        )
        traced_env_source = TracingSourceWrapper(
            settings_cls,
            env_source,
            source_name="environment_variables",
            source_type="env",
            trace_storage=trace_storage,
        )

        # .envファイルソースを作成（トレース付き、マッピング適用）
        # Issue #251対応: MappedDotEnvSettingsSource を使用
        # Note: インラインインポートはschema.pyとの循環インポートを回避するため
        from .schema import MappedDotEnvSettingsSource

        env_file_config = settings_cls.model_config.get("env_file", ".env")
        env_file_str = str(env_file_config) if env_file_config is not None else None
        dotenv_source = MappedDotEnvSettingsSource(
            settings_cls,
            env_file=env_file_str,
            env_file_encoding=settings_cls.model_config.get("env_file_encoding", "utf-8"),
            case_sensitive=settings_cls.model_config.get("case_sensitive", True),
            env_prefix=settings_cls.model_config.get("env_prefix", ""),
            env_nested_delimiter=settings_cls.model_config.get("env_nested_delimiter", "__"),
        )
        traced_dotenv_source = TracingSourceWrapper(
            settings_cls,
            dotenv_source,
            source_name=".env",
            source_type="dotenv",
            trace_storage=trace_storage,
        )

        # CLI引数（filtered_cli_argsのみ）をトレーシングでラップ
        from .sources.cli_source import CLISource

        cli_source = CLISource(settings_cls, filtered_cli_args)
        traced_cli_source = TracingSourceWrapper(
            settings_cls,
            cli_source,
            source_name="CLI",
            source_type="cli",
            trace_storage=trace_storage,
        )

        # 各ソースからデータを取得
        cli_data = traced_cli_source()
        env_data = traced_env_source()
        dotenv_data = traced_dotenv_source()

        # データをマージ（優先順位: init (CLI) > ENV > .env > TOML）
        # init_kwargsには filtered_cli_args + extra_kwargs + environment が含まれる
        # トレースはfiltered_cli_argsのみに記録されている
        merged_data = {**toml_data, **dotenv_data, **env_data, **cli_data, **extra_kwargs}

        # environmentを追加（extra_kwargsに含まれていない場合）
        if "environment" not in merged_data:
            merged_data["environment"] = self.environment

        # Settingsインスタンスを構築
        # NOTE: model_validate()を使用してPydanticの設定ソースメカニズムをバイパス
        # これにより、settings_customise_sources()が呼ばれず、手動で作成したtrace_storageが保持される
        settings_instance = settings_cls.model_validate(merged_data)

        # トレース情報をインスタンスに添付（取り出し可能にする）
        # model_validate()を使用した場合、model_post_init()は呼ばれるが、
        # context varsに設定したtrace_storageが使用される
        if not hasattr(settings_instance, "__source_traces__"):
            object.__setattr__(settings_instance, "__source_traces__", trace_storage)

        return settings_instance

    def load_team_settings(
        self,
        toml_file: Path,
        **extra_kwargs: Any,
    ) -> "TeamSettings":
        """Team設定を参照解決付きで読み込み（T091実装、T078トレーシング対応）。

        既存のteam.toml形式（参照形式 config="agents/xxx.toml" を含む）と
        完全互換性を維持します。

        優先順位: CLI > 環境変数 > .env > TOML（参照解決済み） > デフォルト値

        Args:
            toml_file: Team設定TOMLファイルパス
            **extra_kwargs: 追加のキーワード引数

        Returns:
            TeamSettings instance（トレース情報付き）

        Raises:
            FileNotFoundError: TOMLファイルまたは参照先ファイルが見つからない場合
            ValueError: TOML構文エラーまたはバリデーションエラー

        Examples:
            >>> manager = ConfigurationManager(workspace=Path("/path/to/workspace"))
            >>> team_settings = manager.load_team_settings(Path("team.toml"))
            >>> print(team_settings.team_id)
            'team1'
            >>> # トレース情報を取得
            >>> trace_info = manager.get_source_trace(team_settings, "team_id")
            >>> print(trace_info.source_name)
            'team.toml'
        """
        from .schema import TeamSettings
        from .sources.team_toml_source import TeamTomlSource

        return self._load_settings_with_tracing(
            TeamSettings,
            TeamTomlSource,
            toml_file,
            str(toml_file.name),
            **extra_kwargs,
        )

    def load_member_settings(
        self,
        toml_file: Path,
        **extra_kwargs: Any,
    ) -> "MemberAgentSettings":
        """Member Agent設定を読み込み（T079実装）。

        個別のMember Agent TOMLファイル（例: examples/agents/plain_agent.toml）を
        読み込み、MemberAgentSettingsインスタンスを返します。

        優先順位: CLI > 環境変数 > .env > TOML > デフォルト値

        Args:
            toml_file: Member Agent設定TOMLファイルパス
            **extra_kwargs: 追加のキーワード引数

        Returns:
            MemberAgentSettings instance（トレース情報付き）

        Raises:
            FileNotFoundError: TOMLファイルが見つからない場合
            ValueError: TOML構文エラーまたはバリデーションエラー

        Examples:
            >>> manager = ConfigurationManager(workspace=Path.cwd())
            >>> member_settings = manager.load_member_settings(Path("examples/agents/plain_agent.toml"))
            >>> print(member_settings.agent_name)
            'plain-agent'
            >>> # トレース情報を取得
            >>> trace_info = getattr(member_settings, "__source_traces__", {})
            >>> if "agent_name" in trace_info:
            ...     print(trace_info["agent_name"].source_name)
            'plain_agent.toml'
        """
        from .schema import MemberAgentSettings
        from .sources.member_toml_source import MemberAgentTomlSource

        return self._load_settings_with_tracing(
            MemberAgentSettings,
            MemberAgentTomlSource,
            toml_file,
            str(toml_file.name),
            **extra_kwargs,
        )

    def load_evaluation_settings(
        self,
        toml_file: Path,
        **extra_kwargs: Any,
    ) -> "EvaluatorSettings":
        """Evaluator設定を読み込み（T080実装）。

        evaluator.toml形式（EvaluationConfig互換）を読み込み、
        EvaluatorSettingsインスタンスを返します。

        優先順位: CLI > 環境変数 > .env > TOML > デフォルト値

        Args:
            toml_file: Evaluator設定TOMLファイルパス
            **extra_kwargs: 追加のキーワード引数

        Returns:
            EvaluatorSettings instance（トレース情報付き）

        Raises:
            FileNotFoundError: TOMLファイルが見つからない場合
            ValueError: TOML構文エラーまたはバリデーションエラー

        Examples:
            >>> manager = ConfigurationManager(workspace=Path("/workspace"))
            >>> evaluator_settings = manager.load_evaluation_settings(
            ...     Path("configs/evaluator.toml")
            ... )
            >>> print(evaluator_settings.default_model)
            'anthropic:claude-sonnet-4-5-20250929'
            >>> # トレース情報を取得
            >>> trace_info = getattr(evaluator_settings, "__source_traces__", {})
            >>> if "default_model" in trace_info:
            ...     print(trace_info["default_model"].source_name)
            'evaluator.toml'
        """
        from .schema import EvaluatorSettings
        from .sources.evaluation_toml_source import EvaluationTomlSource

        return self._load_settings_with_tracing(
            EvaluatorSettings,
            EvaluationTomlSource,
            toml_file,
            str(toml_file.name),
            **extra_kwargs,
        )

    def get_evaluator_settings(
        self,
        evaluator_config: Path | str | None = None,
        **extra_kwargs: Any,
    ) -> "EvaluatorSettings":
        """Evaluator設定を取得（フォールバックロジック付き）。

        evaluator_config が指定されていればそれを使用し、
        未指定の場合は {workspace}/configs/evaluator.toml を試し、
        ファイルが存在しなければデフォルト値を返します（FR-049準拠）。

        Args:
            evaluator_config: Evaluator設定ファイルパス（オプション）
            **extra_kwargs: 追加のキーワード引数

        Returns:
            EvaluatorSettings instance

        Raises:
            FileNotFoundError: 明示的に指定されたファイルが存在しない場合（FR-048準拠）
            ValueError: TOML構文エラーまたはバリデーションエラー、または workspace が None の場合

        Examples:
            >>> manager = ConfigurationManager(workspace=Path("/workspace"))
            >>> # カスタムパスから読み込み
            >>> settings = manager.get_evaluator_settings("custom/evaluator.toml")
            >>> # デフォルトパス（存在しない場合はデフォルト値）
            >>> settings = manager.get_evaluator_settings()
        """
        from .schema import EvaluatorSettings

        # workspace が None の場合はエラー（Article 9: Data Accuracy Mandate）
        if self.workspace is None:
            raise ValueError(
                "ConfigurationManager.workspace is None. Cannot resolve relative paths or default config location."
            )

        if evaluator_config:
            # 明示的に指定されたパスから読み込み（存在しない場合はエラー）
            config_path = Path(evaluator_config)
            if not config_path.is_absolute():
                # 相対パスの場合は workspace 基準で解決（FR-045準拠）
                config_path = self.workspace / config_path

            if not config_path.exists():
                # FR-048準拠: 明示的に指定されたファイルが存在しない場合はエラー
                raise FileNotFoundError(
                    f"Evaluator config file not found: {config_path}\n"
                    f"Please check the path specified in evaluator_config."
                )

            return self.load_evaluation_settings(config_path, **extra_kwargs)

        # evaluator_config が未指定の場合、デフォルトパスを試す
        default_config = self.workspace / "configs" / "evaluator.toml"
        if default_config.exists():
            return self.load_evaluation_settings(default_config, **extra_kwargs)

        # FR-049準拠: ファイルが存在しない場合はデフォルト値で初期化
        default_settings = EvaluatorSettings()
        default_json = json.dumps(default_settings.model_dump(mode="json"), indent=2, ensure_ascii=False)
        logging.warning(
            f"Configuration file not found: {default_config}. Using default configuration:\n{default_json}"
        )
        return default_settings

    def load_judgment_settings(
        self,
        toml_file: Path,
        **extra_kwargs: Any,
    ) -> "JudgmentSettings":
        """Judgment設定を読み込み。

        judgment.toml形式を読み込み、JudgmentSettingsインスタンスを返します。

        優先順位: CLI > 環境変数 > .env > TOML > デフォルト値

        Args:
            toml_file: Judgment設定TOMLファイルパス
            **extra_kwargs: 追加のキーワード引数

        Returns:
            JudgmentSettings instance（トレース情報付き）

        Raises:
            FileNotFoundError: TOMLファイルが見つからない場合
            ValueError: TOML構文エラーまたはバリデーションエラー

        Examples:
            >>> manager = ConfigurationManager(workspace=Path("/workspace"))
            >>> judgment_settings = manager.load_judgment_settings(
            ...     Path("configs/judgment.toml")
            ... )
            >>> print(judgment_settings.model)
            'google-gla:gemini-2.5-flash'
            >>> # トレース情報を取得
            >>> trace_info = getattr(judgment_settings, "__source_traces__", {})
            >>> if "model" in trace_info:
            ...     print(trace_info["model"].source_name)
            'judgment.toml'
        """
        from .schema import JudgmentSettings
        from .sources.judgment_toml_source import JudgmentTomlSource

        return self._load_settings_with_tracing(
            JudgmentSettings,
            JudgmentTomlSource,
            toml_file,
            str(toml_file.name),
            **extra_kwargs,
        )

    def get_judgment_settings(
        self,
        judgment_config: Path | str | None = None,
        **extra_kwargs: Any,
    ) -> "JudgmentSettings":
        """Judgment設定を取得（フォールバックロジック付き）。

        judgment_config が指定されていればそれを使用し、
        未指定の場合は {workspace}/configs/judgment.toml を試し、
        ファイルが存在しなければデフォルト値を返します。

        Args:
            judgment_config: Judgment設定ファイルパス（オプション）
            **extra_kwargs: 追加のキーワード引数

        Returns:
            JudgmentSettings instance

        Raises:
            FileNotFoundError: 明示的に指定されたファイルが存在しない場合
            ValueError: TOML構文エラーまたはバリデーションエラー、または workspace が None の場合

        Examples:
            >>> manager = ConfigurationManager(workspace=Path("/workspace"))
            >>> # カスタムパスから読み込み
            >>> settings = manager.get_judgment_settings("custom/judgment.toml")
            >>> # デフォルトパス（存在しない場合はデフォルト値）
            >>> settings = manager.get_judgment_settings()
        """
        from .schema import JudgmentSettings

        # workspace が None の場合はエラー（Article 9: Data Accuracy Mandate）
        if self.workspace is None:
            raise ValueError(
                "ConfigurationManager.workspace is None. Cannot resolve relative paths or default config location."
            )

        if judgment_config:
            # 明示的に指定されたパスから読み込み（存在しない場合はエラー）
            config_path = Path(judgment_config)
            if not config_path.is_absolute():
                # 相対パスの場合は workspace 基準で解決
                config_path = self.workspace / config_path

            if not config_path.exists():
                # 明示的に指定されたファイルが存在しない場合はエラー
                raise FileNotFoundError(
                    f"Judgment config file not found: {config_path}\n"
                    f"Please check the path specified in judgment_config."
                )

            return self.load_judgment_settings(config_path, **extra_kwargs)

        # judgment_config が未指定の場合、デフォルトパスを試す
        default_config = self.workspace / "configs" / "judgment.toml"
        if default_config.exists():
            return self.load_judgment_settings(default_config, **extra_kwargs)

        # ファイルが存在しない場合はデフォルト値で初期化
        default_settings = JudgmentSettings()
        default_json = json.dumps(default_settings.model_dump(mode="json"), indent=2, ensure_ascii=False)
        logging.warning(
            f"Configuration file not found: {default_config}. Using default configuration:\n{default_json}"
        )
        return default_settings

    def load_orchestrator_settings(
        self,
        toml_file: Path,
        **extra_kwargs: Any,
    ) -> "OrchestratorSettings":
        """Orchestrator設定を読み込み（T086実装）。

        orchestrator.toml形式を読み込み、OrchestratorSettingsインスタンスを返します。

        優先順位: CLI > 環境変数 > .env > TOML > デフォルト値

        Args:
            toml_file: Orchestrator設定TOMLファイルパス
            **extra_kwargs: 追加のキーワード引数

        Returns:
            OrchestratorSettings instance（トレース情報付き）

        Raises:
            FileNotFoundError: TOMLファイルが見つからない場合
            ValueError: TOML構文エラーまたはバリデーションエラー

        Examples:
            >>> manager = ConfigurationManager(workspace=Path("/workspace"))
            >>> orchestrator_settings = manager.load_orchestrator_settings(
            ...     Path("configs/orchestrator.toml")
            ... )
            >>> print(orchestrator_settings.timeout_per_team_seconds)
            600
        """
        from .schema import OrchestratorSettings
        from .sources.orchestrator_toml_source import OrchestratorTomlSource

        # workspaceを設定（T093 fix: workspace_pathをinit_kwargsに含める）
        if "workspace_path" not in extra_kwargs and self.workspace is not None:
            extra_kwargs["workspace_path"] = self.workspace

        return self._load_settings_with_tracing(
            OrchestratorSettings,
            OrchestratorTomlSource,
            toml_file,
            str(toml_file.name),
            **extra_kwargs,
        )

    def load_prompt_builder_settings(
        self,
        toml_file: Path,
        **extra_kwargs: Any,
    ) -> "PromptBuilderSettings":
        """PromptBuilder設定を読み込み。

        prompt_builder.toml形式を読み込み、PromptBuilderSettingsインスタンスを返します。

        優先順位: CLI > 環境変数 > .env > TOML > デフォルト値

        Args:
            toml_file: PromptBuilder設定TOMLファイルパス
            **extra_kwargs: 追加のキーワード引数

        Returns:
            PromptBuilderSettings instance（トレース情報付き）

        Raises:
            FileNotFoundError: TOMLファイルが見つからない場合
            ValueError: TOML構文エラーまたはバリデーションエラー

        Examples:
            >>> manager = ConfigurationManager(workspace=Path("/workspace"))
            >>> prompt_builder_settings = manager.load_prompt_builder_settings(
            ...     Path("configs/prompt_builder.toml")
            ... )
            >>> print(prompt_builder_settings.team_user_prompt[:50])
            '---\n現在日時: {{ current_datetime }}\n---\n\n# 概要\nあなた...'
        """
        from .schema import PromptBuilderSettings
        from .sources.prompt_builder_toml_source import PromptBuilderTomlSource

        return self._load_settings_with_tracing(
            PromptBuilderSettings,
            PromptBuilderTomlSource,
            toml_file,
            str(toml_file.name),
            **extra_kwargs,
        )

    def get_prompt_builder_settings(
        self,
        prompt_builder_config: Path | str | None = None,
        **extra_kwargs: Any,
    ) -> "PromptBuilderSettings":
        """PromptBuilder設定を取得（フォールバックロジック付き）。

        prompt_builder_config が指定されていればそれを使用し、
        未指定の場合は {workspace}/configs/prompt_builder.toml を試し、
        ファイルが存在しなければデフォルト値を返します。

        Args:
            prompt_builder_config: PromptBuilder設定ファイルパス（オプション）
            **extra_kwargs: 追加のキーワード引数

        Returns:
            PromptBuilderSettings instance

        Raises:
            FileNotFoundError: 明示的に指定されたファイルが存在しない場合
            ValueError: TOML構文エラーまたはバリデーションエラー、または workspace が None の場合

        Examples:
            >>> manager = ConfigurationManager(workspace=Path("/workspace"))
            >>> # カスタムパスから読み込み
            >>> settings = manager.get_prompt_builder_settings("custom/prompt_builder.toml")
            >>> # デフォルトパス（存在しない場合はデフォルト値）
            >>> settings = manager.get_prompt_builder_settings()
        """
        from .schema import PromptBuilderSettings

        # workspace が None の場合はエラー（Article 9: Data Accuracy Mandate）
        if self.workspace is None:
            raise ValueError(
                "ConfigurationManager.workspace is None. Cannot resolve relative paths or default config location."
            )

        if prompt_builder_config:
            # 明示的に指定されたパスから読み込み（存在しない場合はエラー）
            config_path = Path(prompt_builder_config)
            if not config_path.is_absolute():
                # 相対パスの場合は workspace 基準で解決
                config_path = self.workspace / config_path

            if not config_path.exists():
                # 明示的に指定されたファイルが存在しない場合はエラー
                raise FileNotFoundError(
                    f"PromptBuilder config file not found: {config_path}\n"
                    f"Please check the path specified in prompt_builder_config."
                )

            return self.load_prompt_builder_settings(config_path, **extra_kwargs)

        # prompt_builder_config が未指定の場合、デフォルトパスを試す
        default_config = self.workspace / "configs" / "prompt_builder.toml"
        if default_config.exists():
            return self.load_prompt_builder_settings(default_config, **extra_kwargs)

        # ファイルが存在しない場合はデフォルト値で初期化
        default_settings = PromptBuilderSettings()
        default_json = json.dumps(default_settings.model_dump(mode="json"), indent=2, ensure_ascii=False)
        logging.warning(
            f"Configuration file not found: {default_config}. Using default configuration:\n{default_json}"
        )
        return default_settings
