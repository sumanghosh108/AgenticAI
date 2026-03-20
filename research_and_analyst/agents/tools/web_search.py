"""
Web Search Tool — wraps Tavily and DuckDuckGo for multi-source search.
"""

import os
from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from research_and_analyst.logger import GLOBAL_LOGGER as log


class SearchResult(BaseModel):
    title: str = ""
    url: str = ""
    snippet: str = ""
    source: str = ""


class WebSearchTool:
    """Unified web search across Tavily and DuckDuckGo."""

    def __init__(self):
        self.tavily_key = os.getenv("TAVILY_API_KEY")
        self._tavily_client = None
        self._ddg = None

    def _get_tavily(self):
        if self._tavily_client is None and self.tavily_key:
            try:
                from langchain_tavily import TavilySearch
                self._tavily_client = TavilySearch(max_results=5)
            except Exception as e:
                log.warning("Tavily client init failed, falling back to DuckDuckGo", error=str(e))
        return self._tavily_client

    def search_tavily(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Search using Tavily API."""
        try:
            client = self._get_tavily()
            if not client:
                return []

            results = client.invoke({"query": query})
            parsed = []
            if isinstance(results, list):
                for r in results[:max_results]:
                    parsed.append(SearchResult(
                        title=r.get("title", ""),
                        url=r.get("url", ""),
                        snippet=r.get("content", ""),
                        source="tavily",
                    ))
            log.info("Tavily search completed", query=query, results=len(parsed))
            return parsed
        except Exception as e:
            log.error("Tavily search failed", query=query, error=str(e))
            return []

    def search_ddg(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Search using DuckDuckGo."""
        try:
            from ddgs import DDGS
            ddgs = DDGS()
            raw = list(ddgs.text(query, max_results=max_results))
            parsed = []
            for r in raw:
                parsed.append(SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", ""),
                    source="duckduckgo",
                ))
            log.info("DuckDuckGo search completed", query=query, results=len(parsed))
            return parsed
        except Exception as e:
            log.error("DuckDuckGo search failed", query=query, error=str(e))
            return []

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Search with fallback: Tavily first, then DuckDuckGo."""
        results = self.search_tavily(query, max_results)
        if not results:
            results = self.search_ddg(query, max_results)
        return results

    def multi_search(self, queries: List[str], max_results: int = 3) -> List[SearchResult]:
        """Run multiple queries and deduplicate results by URL."""
        all_results = []
        seen_urls = set()
        for q in queries:
            for r in self.search(q, max_results):
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    all_results.append(r)
        return all_results
