"""
Finance Agent — specialized for financial analysis, market data, and investment decisions.

Uses: WebSearchTool, DataAnalyzerTool, yfinance for market data
"""

from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage

from research_and_analyst.agents.base_agent import AgentResult, BaseAgent
from research_and_analyst.agents.tools.web_search import WebSearchTool
from research_and_analyst.agents.tools.data_analyzer import DataAnalyzerTool
from research_and_analyst.logger import GLOBAL_LOGGER as log


FINANCE_SYSTEM_PROMPT = """\
You are a senior financial analyst. Analyze the provided market data, financial
metrics, and research to produce actionable investment intelligence.

## STRICT CONTEXT RULES (MANDATORY)
- You MUST base your analysis ONLY on the market data, computed metrics, and research findings provided below.
- Do NOT use prior knowledge or training data to fill gaps.
- Every metric and claim MUST reference the provided data or a source URL.
- If data is missing for a metric, state "Data not available" — do NOT estimate.
- Clearly label any projection or inference as "[INFERENCE]".

## Output Guidelines
- Use quantitative data to support your analysis.
- Calculate or reference key metrics: ROI, EBITDA, P/E ratio, revenue growth, CAC, LTV.
- Assess risk-reward profile clearly.
- Distinguish between short-term and long-term perspectives.
- Provide a clear recommendation with confidence level.
"""


class FinanceAgent(BaseAgent):
    """Agent specialized in financial analysis and market intelligence."""

    def __init__(self, llm=None):
        super().__init__(name="FinanceAgent", agent_type="finance", llm=llm)
        self.search_tool = WebSearchTool()
        self.analyzer = DataAnalyzerTool()

    def available_tools(self) -> List[str]:
        return ["web_search", "data_analyzer", "yfinance"]

    def _fetch_market_data(self, ticker: str) -> Dict[str, Any]:
        """Fetch market data using yfinance."""
        try:
            import yfinance as yf

            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="1mo")

            return {
                "ticker": ticker,
                "name": info.get("longName", ticker),
                "price": info.get("currentPrice", info.get("regularMarketPrice")),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "revenue": info.get("totalRevenue"),
                "revenue_growth": info.get("revenueGrowth"),
                "profit_margin": info.get("profitMargins"),
                "ebitda": info.get("ebitda"),
                "debt_to_equity": info.get("debtToEquity"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
                "1mo_history": hist.tail(5).to_dict() if not hist.empty else {},
            }
        except Exception as e:
            log.warning("yfinance fetch failed", ticker=ticker, error=str(e))
            return {"ticker": ticker, "error": str(e)}

    def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        """Perform financial analysis: market data + web research + LLM synthesis."""
        ctx = context or {}
        sources_used = []
        market_data = {}

        # Step 1: Fetch market data if ticker provided
        ticker = ctx.get("ticker")
        if ticker:
            market_data = self._fetch_market_data(ticker)
            log.info("Market data fetched", ticker=ticker)

        # Step 2: Financial web research
        search_queries = [
            f"{task} financial analysis",
            f"{task} market outlook 2025 2026",
            f"{task} investment risks opportunities",
        ]
        search_results = self.search_tool.multi_search(search_queries, max_results=5)
        research_context = "\n\n".join(
            f"**{r.title}** ({r.url})\n{r.snippet}" for r in search_results
        )
        sources_used = [r.url for r in search_results if r.url]

        # Step 3: Run numerical analysis if data available
        analysis_output = ""
        if market_data and "error" not in market_data:
            result = self.analyzer.analyze(
                """
import json
data = market_data
metrics = {}
if data.get('revenue') and data.get('market_cap'):
    metrics['price_to_sales'] = round(data['market_cap'] / data['revenue'], 2)
if data.get('pe_ratio'):
    metrics['pe_ratio'] = round(data['pe_ratio'], 2)
if data.get('revenue_growth'):
    metrics['revenue_growth_pct'] = round(data['revenue_growth'] * 100, 2)
if data.get('profit_margin'):
    metrics['profit_margin_pct'] = round(data['profit_margin'] * 100, 2)
result = metrics
print(json.dumps(metrics, indent=2))
""",
                {"market_data": market_data},
            )
            analysis_output = result.output

        # Step 4: Synthesize with LLM
        if not self.llm:
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                task_description=task,
                output=f"Market Data:\n{market_data}\n\nResearch:\n{research_context}",
                sources_used=sources_used,
                structured_data=market_data,
            )

        import json
        synthesis_prompt = (
            f"{FINANCE_SYSTEM_PROMPT}\n\n"
            f"Task: {task}\n\n"
            f"========== BEGIN PROVIDED CONTEXT (use ONLY this) ==========\n\n"
            f"Market Data:\n{json.dumps(market_data, indent=2, default=str)}\n\n"
            f"Computed Metrics:\n{analysis_output}\n\n"
            f"Research Findings:\n{research_context}\n\n"
            f"========== END PROVIDED CONTEXT ==========\n\n"
            f"Based ONLY on the data above, provide a comprehensive financial analysis with:\n"
            f"1. Key metrics summary\n"
            f"2. Growth assessment\n"
            f"3. Risk analysis\n"
            f"4. Investment recommendation with confidence level\n"
            f"Cite source URLs for every claim."
        )

        response = self.llm.invoke([HumanMessage(content=synthesis_prompt)])

        return AgentResult(
            agent_name=self.name,
            agent_type=self.agent_type,
            task_description=task,
            output=response.content,
            sources_used=sources_used,
            confidence=0.65,
            structured_data={"market_data": market_data, "analysis": analysis_output},
        )
