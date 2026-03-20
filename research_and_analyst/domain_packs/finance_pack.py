"""
Finance Domain Pack — configuration, prompts, and tools for financial analysis.
"""

from research_and_analyst.domain_packs.base_pack import BaseDomainPack, DomainPackConfig


class FinanceDomainPack(BaseDomainPack):
    """Domain pack for financial analysis and investment decisions."""

    def get_config(self) -> DomainPackConfig:
        return DomainPackConfig(
            domain="finance",
            display_name="Financial Analysis",
            tools=["web_search", "yfinance", "data_analyzer", "web_scraper"],
            metrics=[
                "Revenue", "Revenue Growth (%)", "Net Income", "EBITDA",
                "Profit Margin (%)", "P/E Ratio", "Market Cap",
                "CAC", "LTV", "Debt-to-Equity", "ROI",
                "Free Cash Flow", "Gross Margin (%)",
            ],
            scoring_dimensions=[
                "growth_potential",
                "market_competition",
                "financial_health",
                "risk_adjusted_return",
                "management_quality",
            ],
            agent_types=["research", "finance"],
            constraints=[
                "All financial claims must cite data sources",
                "Distinguish between trailing and forward metrics",
                "Include risk factors in every recommendation",
                "Note the date of all market data used",
            ],
        )

    def get_system_prompt(self) -> str:
        return """\
You are a senior financial analyst producing investment-grade analysis.
Focus on quantitative metrics, market positioning, and risk-reward assessment.
Always cite data sources and note the recency of information.
Distinguish between established facts and forward-looking projections."""

    def get_analysis_prompt(self, query: str, context: str) -> str:
        return f"""\
## Financial Analysis Request

**Query:** {query}

**Available Data & Research:**
{context}

## Required Output Structure
1. **Market Overview** — size, growth rate, key players
2. **Financial Metrics** — revenue, margins, growth rates, valuation multiples
3. **Competitive Analysis** — positioning, moat, market share
4. **Risk Assessment** — regulatory, market, operational, financial risks
5. **Investment Thesis** — bull case, bear case, base case
6. **Recommendation** — specific action with confidence level and time horizon

Use data tables where applicable. Cite all sources."""
