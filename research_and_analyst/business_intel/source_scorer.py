"""
Source Reliability Scorer — assesses credibility of information sources.

Evaluates sources based on domain authority, citation frequency,
and content quality indicators.
"""

import re
from typing import Dict, List, Optional
from urllib.parse import urlparse

from research_and_analyst.decision_engine.schemas import SourceScore
from research_and_analyst.logger import GLOBAL_LOGGER as log


# Domain authority tiers (extensible)
HIGH_AUTHORITY_DOMAINS = {
    "reuters.com", "bloomberg.com", "wsj.com", "ft.com",
    "nature.com", "science.org", "thelancet.com", "nejm.org",
    "gov", "edu", "who.int", "nih.gov", "fda.gov", "sec.gov",
    "arxiv.org", "scholar.google.com", "pubmed.ncbi.nlm.nih.gov",
    "statista.com", "worldbank.org", "imf.org",
}

MEDIUM_AUTHORITY_DOMAINS = {
    "techcrunch.com", "wired.com", "arstechnica.com",
    "forbes.com", "cnbc.com", "bbc.com", "nytimes.com",
    "theguardian.com", "economist.com", "hbr.org",
    "wikipedia.org", "investopedia.com",
}

LOW_AUTHORITY_PATTERNS = [
    r"blog\.", r"medium\.com", r"substack\.com",
    r"reddit\.com", r"quora\.com", r"twitter\.com", r"x\.com",
]


class SourceReliabilityScorer:
    """Scores information sources for credibility and authority."""

    def __init__(self, custom_high: Optional[set] = None, custom_low: Optional[List[str]] = None):
        self.high_domains = HIGH_AUTHORITY_DOMAINS | (custom_high or set())
        self.medium_domains = MEDIUM_AUTHORITY_DOMAINS
        self.low_patterns = LOW_AUTHORITY_PATTERNS + (custom_low or [])

    def score_source(self, source: str, citation_count: int = 0) -> SourceScore:
        """
        Score a single source URL or identifier.

        Args:
            source: URL or source name.
            citation_count: How many times this source was cited in the analysis.

        Returns:
            SourceScore with credibility and authority tier.
        """
        domain = self._extract_domain(source)
        authority = self._classify_authority(domain)
        base_score = self._authority_to_score(authority)

        # Boost for citation frequency (max +0.15)
        citation_boost = min(citation_count * 0.05, 0.15)

        # TLD bonuses
        tld = domain.split(".")[-1] if domain else ""
        tld_bonus = 0.1 if tld in ("gov", "edu", "org") else 0.0

        credibility = min(base_score + citation_boost + tld_bonus, 1.0)

        reasoning = (
            f"Domain '{domain}' classified as {authority} authority. "
            f"Base score: {base_score:.2f}, citation boost: +{citation_boost:.2f}, "
            f"TLD bonus: +{tld_bonus:.2f}."
        )

        return SourceScore(
            source=source,
            credibility=round(credibility, 2),
            domain_authority=authority,
            citation_frequency=citation_count,
            reasoning=reasoning,
        )

    def score_sources(self, sources: List[str], citation_counts: Optional[Dict[str, int]] = None) -> List[SourceScore]:
        """Score multiple sources."""
        counts = citation_counts or {}
        scored = []
        for src in sources:
            count = counts.get(src, 1)
            scored.append(self.score_source(src, count))
        return scored

    def filter_reliable(self, sources: List[SourceScore], min_credibility: float = 0.5) -> List[SourceScore]:
        """Filter sources above a credibility threshold."""
        return [s for s in sources if s.credibility >= min_credibility]

    def _extract_domain(self, source: str) -> str:
        """Extract domain from URL or return source as-is."""
        try:
            if "://" in source:
                parsed = urlparse(source)
                return parsed.netloc.lower().lstrip("www.")
            return source.lower()
        except Exception:
            return source.lower()

    def _classify_authority(self, domain: str) -> str:
        """Classify domain into authority tier."""
        # Check high authority
        for high in self.high_domains:
            if domain.endswith(high) or domain == high:
                return "high"

        # Check medium authority
        for med in self.medium_domains:
            if domain.endswith(med) or domain == med:
                return "medium"

        # Check low authority patterns
        for pattern in self.low_patterns:
            if re.search(pattern, domain):
                return "low"

        return "unknown"

    def _authority_to_score(self, authority: str) -> float:
        """Convert authority tier to base credibility score."""
        return {
            "high": 0.85,
            "medium": 0.65,
            "low": 0.35,
            "unknown": 0.50,
        }.get(authority, 0.50)
