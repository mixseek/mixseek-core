"""BitbankAPIAgent implementation (TASK-016).

Custom Member Agent for bitbank Public API integration.
"""

from typing import Any

from pydantic_ai import Agent, RunContext

from examples.custom_agents.bitbank.models import BitbankAPIConfig
from examples.custom_agents.bitbank.tools import (
    calculate_financial_metrics,
    get_candlestick_data,
    get_ticker_data,
)
from mixseek.agents.member.base import BaseMemberAgent
from mixseek.models.member_agent import AgentType, MemberAgentConfig, MemberAgentResult, ResultStatus


class BitbankAPIAgent(BaseMemberAgent):
    """Custom Member Agent for bitbank Public API integration."""

    def __init__(self, config: MemberAgentConfig) -> None:
        """Initialize the bitbank API agent.

        Args:
            config: Member Agent configuration.
        """
        super().__init__(config)

        # Build BitbankAPIConfig from MemberAgentConfig.metadata
        # The [agent.tool_settings.bitbank_api] section from TOML is stored in metadata
        bitbank_settings = config.metadata.get("tool_settings", {}).get("bitbank_api", {})
        if not bitbank_settings:
            raise ValueError(
                "Missing [agent.tool_settings.bitbank_api] configuration in TOML. "
                "Please ensure the TOML file contains bitbank API settings."
            )

        self.bitbank_config = BitbankAPIConfig.model_validate(bitbank_settings)

        # Initialize Pydantic AI Agent
        self.agent: Agent[BitbankAPIConfig, str] = Agent(
            model=self.config.model,
            deps_type=BitbankAPIConfig,
            system_prompt=(
                "You are a cryptocurrency market data analyst specializing in bitbank exchange. "
                "You have access to real-time ticker data, historical candlestick data, "
                "and financial metrics analysis tools. Provide clear, concise analysis in Markdown format.\n\n"
                "IMPORTANT: When using candlestick tools, candle_type parameter MUST be one of:\n"
                "- 4hour (for 4時間/4時間足)\n"
                "- 8hour (for 8時間/8時間足)\n"
                "- 12hour (for 12時間/12時間足)\n"
                "- 1day (for 1日/日足/日次)\n"
                "- 1week (for 1週間/週足)\n"
                "- 1month (for 1ヶ月/月足)\n"
                "Do NOT use abbreviations like '12h' or '1d'. Use the exact format specified above."
            ),
        )

        # Register tools
        @self.agent.tool
        async def fetch_ticker(ctx: RunContext[BitbankAPIConfig], pair: str) -> str:
            """Fetch current ticker data for a currency pair."""
            ticker = await get_ticker_data(pair, ctx.deps)
            return (
                f"# {pair.upper()} Ticker Data\n\n"
                f"- **Buy**: {ticker.buy_float:,.0f} JPY\n"
                f"- **Sell**: {ticker.sell_float:,.0f} JPY\n"
                f"- **Last**: {ticker.last_float:,.0f} JPY\n"
                f"- **High (24h)**: {float(ticker.high):,.0f} JPY\n"
                f"- **Low (24h)**: {float(ticker.low):,.0f} JPY\n"
                f"- **Volume (24h)**: {ticker.vol_float:,.4f}\n"
            )

        @self.agent.tool
        async def fetch_candlestick(ctx: RunContext[BitbankAPIConfig], pair: str, candle_type: str, year: int) -> str:
            """Fetch candlestick data for a currency pair.

            Args:
                pair: Currency pair (btc_jpy, xrp_jpy, eth_jpy)
                candle_type: Interval type - MUST be one of: 4hour, 8hour, 12hour, 1day, 1week, 1month
                    - For "4時間" or "4時間足" use "4hour"
                    - For "8時間" or "8時間足" use "8hour"
                    - For "12時間" or "12時間足" use "12hour"
                    - For "1日" or "日足" or "日次" use "1day"
                    - For "1週間" or "週足" use "1week"
                    - For "1ヶ月" or "月足" use "1month"
                year: Year (e.g., 2024)
            """
            candlestick = await get_candlestick_data(pair, candle_type, year, ctx.deps)
            return (
                f"# {pair.upper()} Candlestick Data\n\n"
                f"- **Interval**: {candle_type}\n"
                f"- **Data Points**: {candlestick.count}\n"
                f"- **Year**: {year}\n"
            )

        @self.agent.tool
        async def analyze_financial_metrics(
            ctx: RunContext[BitbankAPIConfig], pair: str, candle_type: str, year: int
        ) -> str:
            """Analyze financial metrics from candlestick data.

            Args:
                pair: Currency pair (btc_jpy, xrp_jpy, eth_jpy)
                candle_type: Interval type - MUST be one of: 4hour, 8hour, 12hour, 1day, 1week, 1month
                    - For "4時間" or "4時間足" use "4hour"
                    - For "8時間" or "8時間足" use "8hour"
                    - For "12時間" or "12時間足" use "12hour"
                    - For "1日" or "日足" or "日次" use "1day"
                    - For "1週間" or "週足" use "1week"
                    - For "1ヶ月" or "月足" use "1month"
                year: Year (e.g., 2024)
            """
            # Get candlestick data (await directly instead of asyncio.run)
            candlestick = await get_candlestick_data(pair, candle_type, year, ctx.deps)

            # Calculate financial metrics
            metrics = calculate_financial_metrics(candlestick, ctx.deps)

            return (
                f"# {pair.upper()} Financial Metrics Analysis\n\n"
                f"## Returns\n"
                f"- **Annualized Return**: {metrics.annualized_return:.2%}\n"
                f"- **Total Return**: {metrics.total_return:.2%}\n\n"
                f"## Risk Metrics\n"
                f"- **Annualized Volatility**: {metrics.annualized_volatility:.2%}\n"
                f"- **Maximum Drawdown**: {metrics.max_drawdown:.2%}\n\n"
                f"## Risk-Adjusted Returns\n"
                f"- **Sharpe Ratio**: {metrics.sharpe_ratio:.3f}\n"
                f"- **Sortino Ratio**: {metrics.sortino_ratio:.3f}\n\n"
                f"## Distribution\n"
                f"- **Skewness**: {metrics.return_skewness:.3f}\n"
                f"- **Kurtosis**: {metrics.return_kurtosis:.3f}\n\n"
                f"## Price Statistics\n"
                f"- **Start Price**: {metrics.start_price:,.0f} JPY\n"
                f"- **End Price**: {metrics.end_price:,.0f} JPY\n"
                f"- **Mean Price**: {metrics.mean_price:,.0f} JPY\n"
                f"- **Trading Days**: {metrics.trading_days}\n"
                f"- **Total Volume**: {metrics.total_volume:,.4f}\n"
            )

    async def execute(self, task: str, context: dict[str, Any] | None = None, **kwargs: Any) -> MemberAgentResult:
        """Execute the agent task.

        Args:
            task: Task description from Leader Agent.
            context: Optional execution context.
            **kwargs: Additional execution parameters.

        Returns:
            MemberAgentResult with analysis results.
        """
        try:
            # Run Pydantic AI Agent
            result = await self.agent.run(task, deps=self.bitbank_config)

            return MemberAgentResult(
                status=ResultStatus.SUCCESS,
                content=result.output,
                agent_name=self.config.name,
                agent_type=str(AgentType.CUSTOM),
            )

        except Exception as e:
            return MemberAgentResult(
                status=ResultStatus.ERROR,
                content=f"Error executing task: {str(e)}",
                agent_name=self.config.name,
                agent_type=str(AgentType.CUSTOM),
                error_message=str(e),
            )
