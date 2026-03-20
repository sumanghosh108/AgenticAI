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

## STRICT CONTEXT RULES (MANDATORY)
- You MUST ONLY use information from the provided search results and scraped content below.
- Do NOT use prior knowledge, training data, or make assumptions beyond what the sources say.
- Every factual claim MUST cite a source URL from the provided results.
- If the sources do not cover a topic, explicitly state "No data available from sources" — do NOT fill gaps with your own knowledge.
- If sources conflict, present BOTH viewpoints with their respective URLs.
- Clearly label any inference or analysis that goes beyond what sources directly state as "[INFERENCE]".

## Output Guidelines
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
        """Research a topic: generate queries → hybrid search → scrape top results → synthesize."""
        ctx_str = context.get("additional_context", "") if context else ""
        sources_used = []

        # Step 1: Generate search queries
        queries = self._generate_queries(task, ctx_str)
        log.info("Research queries generated", queries=queries)

        # Step 2: Hybrid multi-search (Tavily + DuckDuckGo combined)
        search_results = self.search_tool.multi_search(queries, max_results=5)
        search_context = "\n\n".join(
            f"**{r.title}** ({r.url}) [source: {r.source}]\n{r.snippet}"
            for r in search_results
        )
        sources_used = [r.url for r in search_results if r.url]

        # Step 3: Scrape top 5 unique URLs for deeper content
        top_urls = list(dict.fromkeys(r.url for r in search_results if r.url))[:5]
        scraped = self.scraper_tool.scrape_multiple(top_urls, max_chars=3000)
        scraped_context = "\n\n".join(
            f"--- Content from {s.url} ---\n{s.text[:2000]}" for s in scraped if s.success
        )

        # Step 4: Synthesize with LLM (strict context constraining)
        if not self.llm:
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                task_description=task,
                output=f"Search Results:\n{search_context}\n\nScraped Content:\n{scraped_context}",
                sources_used=sources_used,
            )

        # Context-constrained prompt with clear boundaries
        synthesis_prompt = (
            f"{RESEARCH_SYSTEM_PROMPT}\n\n"
            f"Research Task: {task}\n\n"
            f"========== BEGIN PROVIDED CONTEXT (use ONLY this) ==========\n\n"
            f"Search Results:\n{search_context}\n\n"
            f"Detailed Content:\n{scraped_context}\n\n"
            f"========== END PROVIDED CONTEXT ==========\n\n"
            f"Based ONLY on the context above, provide a comprehensive research synthesis. "
            f"Cite source URLs for every factual claim. "
            f"If the context does not cover an aspect, say 'No data available from sources'."
        )

        response = self.llm.invoke([HumanMessage(content=synthesis_prompt)])

        return AgentResult(
            agent_name=self.name,
            agent_type=self.agent_type,
            task_description=task,
            output=response.content,
            sources_used=sources_used,
            confidence=0.7,
            structured_data={
                "queries": queries,
                "result_count": len(search_results),
                "sources_by_engine": {
                    "tavily": sum(1 for r in search_results if "tavily" in r.source),
                    "duckduckgo": sum(1 for r in search_results if "duckduckgo" in r.source),
                    "both": sum(1 for r in search_results if "+" in r.source),
                },
            },
        )
