"""
Research Agent — conducts web research, scrapes sources, and synthesizes findings.

Uses: WebSearchTool, WebScraperTool
"""

from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage

from research_and_analyst.agents.base_agent import AgentResult, BaseAgent
from research_and_analyst.agents.tools.web_search import WebSearchTool
from research_and_analyst.agents.tools.scraper import WebScraperTool
from research_and_analyst.logger import GLOBAL_LOGGER as log


RESEARCH_SYSTEM_PROMPT = """\
You are a thorough research analyst. Given a research task and web search results,
synthesize the information into a clear, factual analysis.

Guidelines:
- Ground your analysis in the provided search results and scraped content.
- Cite sources by URL when making specific claims.
- Distinguish between verified facts and inferences.
- Flag any gaps in the available information.
- Structure your output with clear sections.
"""

SEARCH_GENERATION_PROMPT = """\
Generate {n} diverse search queries to research the following task:

Task: {task}

Context (if any): {context}

Return each query on a separate line, numbered 1-{n}.
"""


class ResearchAgent(BaseAgent):
    """Agent that performs web research and synthesizes findings."""

    def __init__(self, llm=None):
        super().__init__(name="ResearchAgent", agent_type="research", llm=llm)
        self.search_tool = WebSearchTool()
        self.scraper_tool = WebScraperTool()

    def available_tools(self) -> List[str]:
        return ["web_search", "web_scraper"]

    def _generate_queries(self, task: str, context: str = "", n: int = 3) -> List[str]:
        """Use LLM to generate search queries for the task."""
        if not self.llm:
            return [task]

        prompt = SEARCH_GENERATION_PROMPT.format(task=task, context=context, n=n)
        response = self.llm.invoke([HumanMessage(content=prompt)])
        lines = response.content.strip().split("\n")
        queries = []
        for line in lines:
            # Strip numbering like "1. " or "1) "
            cleaned = line.strip().lstrip("0123456789.)- ").strip()
            if cleaned:
                queries.append(cleaned)
        return queries[:n] if queries else [task]

    def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        """Research a topic: generate queries → search → scrape top results → synthesize."""
        ctx_str = context.get("additional_context", "") if context else ""
        sources_used = []

        # Step 1: Generate search queries
        queries = self._generate_queries(task, ctx_str)
        log.info("Research queries generated", queries=queries)

        # Step 2: Multi-search
        search_results = self.search_tool.multi_search(queries, max_results=3)
        search_context = "\n\n".join(
            f"**{r.title}** ({r.url})\n{r.snippet}" for r in search_results
        )
        sources_used = [r.url for r in search_results if r.url]

        # Step 3: Scrape top 3 unique URLs for deeper content
        top_urls = list(dict.fromkeys(r.url for r in search_results if r.url))[:3]
        scraped = self.scraper_tool.scrape_multiple(top_urls, max_chars=3000)
        scraped_context = "\n\n".join(
            f"--- Content from {s.url} ---\n{s.text[:2000]}" for s in scraped if s.success
        )

        # Step 4: Synthesize with LLM
        if not self.llm:
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                task_description=task,
                output=f"Search Results:\n{search_context}\n\nScraped Content:\n{scraped_context}",
                sources_used=sources_used,
            )

        synthesis_prompt = (
            f"{RESEARCH_SYSTEM_PROMPT}\n\n"
            f"Research Task: {task}\n\n"
            f"Search Results:\n{search_context}\n\n"
            f"Detailed Content:\n{scraped_context}\n\n"
            f"Provide a comprehensive research synthesis."
        )

        response = self.llm.invoke([HumanMessage(content=synthesis_prompt)])

        return AgentResult(
            agent_name=self.name,
            agent_type=self.agent_type,
            task_description=task,
            output=response.content,
            sources_used=sources_used,
            confidence=0.7,
            structured_data={"queries": queries, "result_count": len(search_results)},
        )
