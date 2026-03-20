"""
Web Search Tool — hybrid multi-source search with deduplication and ranking.

Retrieval strategy:
  1. Tavily (structured summarization — best for synthesis)
  2. DuckDuckGo (keyword breadth — catches sources Tavily misses)
  3. BOTH run in parallel for hybrid search, results merged and ranked

This gives significantly better coverage than single-engine fallback.
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
    relevance_score: float = Field(default=0.0, description="Ranking score (higher = more relevant)")


class WebSearchTool:
    """Hybrid web search combining Tavily (summarization) + DuckDuckGo (keyword breadth)."""

    def __init__(self):
        self.tavily_key = os.getenv("TAVILY_API_KEY")
        self._tavily_client = None

    def _get_tavily(self):
        if self._tavily_client is None and self.tavily_key:
            try:
                from langchain_tavily import TavilySearch
                self._tavily_client = TavilySearch(max_results=5)
            except Exception as e:
                log.warning("Tavily client init failed", error=str(e))
        return self._tavily_client

    def search_tavily(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Search using Tavily API (better summarization, structured content)."""
        try:
            client = self._get_tavily()
            if not client:
                return []

            results = client.invoke({"query": query})
            parsed = []
            if isinstance(results, list):
                for i, r in enumerate(results[:max_results]):
                    parsed.append(SearchResult(
                        title=r.get("title", ""),
                        url=r.get("url", ""),
                        snippet=r.get("content", ""),
                        source="tavily",
                        relevance_score=1.0 - (i * 0.1),  # Position-based score
                    ))
            log.info("Tavily search completed", query=query[:80], results=len(parsed))
            return parsed
        except Exception as e:
            log.error("Tavily search failed", query=query[:80], error=str(e))
            return []

    def search_ddg(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Search using DuckDuckGo (keyword breadth, catches diverse sources)."""
        try:
            from ddgs import DDGS
            ddgs = DDGS()
            raw = list(ddgs.text(query, max_results=max_results))
            parsed = []
            for i, r in enumerate(raw):
                parsed.append(SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", ""),
                    source="duckduckgo",
                    relevance_score=0.9 - (i * 0.1),  # Slightly lower base than Tavily
                ))
            log.info("DuckDuckGo search completed", query=query[:80], results=len(parsed))
            return parsed
        except Exception as e:
            log.error("DuckDuckGo search failed", query=query[:80], error=str(e))
            return []

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Single-engine search: Tavily first, DuckDuckGo fallback."""
        results = self.search_tavily(query, max_results)
        if not results:
            results = self.search_ddg(query, max_results)
        return results

    def hybrid_search(self, query: str, max_results: int = 8) -> List[SearchResult]:
        """
        Hybrid search: run BOTH Tavily and DuckDuckGo, merge and rank results.

        This gives much better source diversity and coverage than single-engine.
        Results are deduplicated by URL and ranked by combined relevance score.
        """
        # Run both engines
        tavily_results = self.search_tavily(query, max_results=max_results)
        ddg_results = self.search_ddg(query, max_results=max_results)

        # Merge with deduplication
        merged = self._merge_and_rank(tavily_results, ddg_results)

        log.info(
            "Hybrid search completed",
            query=query[:80],
            tavily=len(tavily_results),
            ddg=len(ddg_results),
            merged=len(merged),
        )

        return merged[:max_results]

    def multi_search(self, queries: List[str], max_results: int = 3) -> List[SearchResult]:
        """Run multiple queries with hybrid search and deduplicate across all."""
        all_results = []
        seen_urls = set()

        for q in queries:
            for r in self.hybrid_search(q, max_results=max_results):
                if r.url and r.url not in seen_urls:
                    seen_urls.add(r.url)
                    all_results.append(r)

        # Sort by relevance score
        all_results.sort(key=lambda r: r.relevance_score, reverse=True)
        return all_results

    def keyword_search(self, query: str, keywords: List[str], max_results: int = 5) -> List[SearchResult]:
        """
        Keyword-augmented search: generate focused queries from keywords
        and merge results with the main query results.
        """
        # Main query via hybrid
        main_results = self.hybrid_search(query, max_results=max_results)

        # Keyword-focused queries
        keyword_results = []
        for kw in keywords[:3]:  # Limit to avoid too many API calls
            kw_query = f"{query} {kw}"
            kw_results = self.hybrid_search(kw_query, max_results=3)
            keyword_results.extend(kw_results)

        # Merge all
        merged = self._merge_and_rank(main_results, keyword_results)

        log.info(
            "Keyword search completed",
            query=query[:80],
            keywords=keywords[:3],
            results=len(merged),
        )

        return merged[:max_results]

    def _merge_and_rank(
        self,
        results_a: List[SearchResult],
        results_b: List[SearchResult],
    ) -> List[SearchResult]:
        """
        Merge two result sets with deduplication and boosted scoring.

        Results appearing in BOTH engines get a relevance boost (cross-engine
        agreement is a strong signal).
        """
        by_url: Dict[str, SearchResult] = {}

        for r in results_a:
            if r.url:
                by_url[r.url] = r

        for r in results_b:
            if not r.url:
                continue
            if r.url in by_url:
                # Cross-engine agreement: boost score
                existing = by_url[r.url]
                existing.relevance_score = min(
                    existing.relevance_score + 0.2, 1.0
                )
                # Prefer Tavily snippet (better summarization) but keep longer
                if len(r.snippet) > len(existing.snippet):
                    existing.snippet = r.snippet
                existing.source = "tavily+duckduckgo"
            else:
                by_url[r.url] = r

        ranked = sorted(by_url.values(), key=lambda r: r.relevance_score, reverse=True)
        return ranked
