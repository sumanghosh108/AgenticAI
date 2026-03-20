"""
Cross-Verification Engine — validates claims against multiple independent sources.

Core rules:
  1. Every claim requires ≥2 independent sources to be considered verified.
  2. Sources with credibility < 0.5 are excluded from decision-making.
  3. Claims backed by only one source are flagged as "weakly supported".
  4. Claims with zero credible sources are flagged as "unverified".

Used after agent dispatch and before decision generation to filter
hallucinated or poorly-sourced content.
"""

import hashlib
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from research_and_analyst.business_intel.source_scorer import SourceReliabilityScorer
from research_and_analyst.decision_engine.schemas import SourceScore
from research_and_analyst.logger import GLOBAL_LOGGER as log


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────

class VerifiedClaim(BaseModel):
    """A single claim with its verification status."""
    claim: str
    status: str = Field(description="verified | weakly_supported | unverified")
    supporting_sources: List[str] = Field(default_factory=list)
    source_count: int = 0
    credible_source_count: int = 0
    avg_credibility: float = 0.0


class VerificationReport(BaseModel):
    """Aggregated cross-verification results."""
    total_claims: int = 0
    verified_claims: int = 0
    weakly_supported_claims: int = 0
    unverified_claims: int = 0
    verification_rate: float = 0.0
    claims: List[VerifiedClaim] = Field(default_factory=list)
    filtered_sources: List[str] = Field(
        default_factory=list,
        description="Sources excluded for credibility < 0.5",
    )
    credible_sources: List[SourceScore] = Field(
        default_factory=list,
        description="Sources that passed the credibility threshold",
    )


# ─────────────────────────────────────────────
# Cross Verifier
# ─────────────────────────────────────────────

class CrossVerifier:
    """
    Multi-source cross-verification engine.

    Validates claims by checking how many independent, credible sources
    support each one. Filters low-quality sources before verification.
    """

    MIN_SOURCES_PER_CLAIM = 2
    MIN_CREDIBILITY = 0.5

    def __init__(
        self,
        source_scorer: Optional[SourceReliabilityScorer] = None,
        min_sources: int = 2,
        min_credibility: float = 0.5,
    ):
        self.scorer = source_scorer or SourceReliabilityScorer()
        self.MIN_SOURCES_PER_CLAIM = min_sources
        self.MIN_CREDIBILITY = min_credibility

    def verify(
        self,
        agent_outputs: List[Dict[str, Any]],
        llm=None,
    ) -> VerificationReport:
        """
        Cross-verify claims across all agent outputs.

        Steps:
          1. Score all sources and filter out those < min_credibility
          2. Extract claims from each agent output
          3. For each claim, find how many independent credible sources support it
          4. Classify as verified / weakly_supported / unverified

        Args:
            agent_outputs: List of agent result dicts (from AgentResult.model_dump()).
            llm: Optional LLM for claim extraction (falls back to heuristic).

        Returns:
            VerificationReport with per-claim verification status.
        """
        # Step 1: Collect and score all sources
        all_sources = []
        source_to_outputs: Dict[str, List[int]] = {}  # url → list of output indices

        for idx, out in enumerate(agent_outputs):
            for src in out.get("sources_used", []):
                if src not in source_to_outputs:
                    source_to_outputs[src] = []
                    all_sources.append(src)
                source_to_outputs[src].append(idx)

        scored_sources = self.scorer.score_sources(all_sources)

        # Partition into credible and filtered
        credible = [s for s in scored_sources if s.credibility >= self.MIN_CREDIBILITY]
        filtered = [s for s in scored_sources if s.credibility < self.MIN_CREDIBILITY]
        credible_urls = {s.source for s in credible}
        filtered_urls = [s.source for s in filtered]

        log.info(
            "Source filtering complete",
            total=len(scored_sources),
            credible=len(credible),
            filtered_out=len(filtered),
        )

        # Step 2: Extract claims from each agent output
        claims_by_output = self._extract_claims_from_outputs(agent_outputs, llm)

        # Step 3: Cross-verify each claim
        verified_claims: List[VerifiedClaim] = []
        seen_claims = set()

        for output_idx, claims in enumerate(claims_by_output):
            output_sources = set(agent_outputs[output_idx].get("sources_used", []))
            output_credible_sources = output_sources & credible_urls

            for claim_text in claims:
                # Deduplicate similar claims
                claim_key = self._normalize_claim(claim_text)
                if claim_key in seen_claims:
                    continue
                seen_claims.add(claim_key)

                # Find which other outputs corroborate this claim
                supporting = self._find_corroborating_sources(
                    claim_text, output_idx, agent_outputs, credible_urls
                )

                # Include current output's credible sources
                all_supporting = list(output_credible_sources | supporting)
                credible_count = len(all_supporting)

                # Compute average credibility of supporting sources
                avg_cred = 0.0
                if all_supporting:
                    scores = [
                        s.credibility for s in credible
                        if s.source in all_supporting
                    ]
                    avg_cred = sum(scores) / len(scores) if scores else 0.0

                # Classify
                if credible_count >= self.MIN_SOURCES_PER_CLAIM:
                    status = "verified"
                elif credible_count == 1:
                    status = "weakly_supported"
                else:
                    status = "unverified"

                verified_claims.append(VerifiedClaim(
                    claim=claim_text,
                    status=status,
                    supporting_sources=all_supporting,
                    source_count=credible_count,
                    credible_source_count=credible_count,
                    avg_credibility=round(avg_cred, 3),
                ))

        # Aggregate
        n_verified = sum(1 for c in verified_claims if c.status == "verified")
        n_weak = sum(1 for c in verified_claims if c.status == "weakly_supported")
        n_unverified = sum(1 for c in verified_claims if c.status == "unverified")
        total = len(verified_claims)

        report = VerificationReport(
            total_claims=total,
            verified_claims=n_verified,
            weakly_supported_claims=n_weak,
            unverified_claims=n_unverified,
            verification_rate=round(n_verified / max(total, 1), 3),
            claims=verified_claims,
            filtered_sources=filtered_urls,
            credible_sources=credible,
        )

        log.info(
            "Cross-verification complete",
            total_claims=total,
            verified=n_verified,
            weak=n_weak,
            unverified=n_unverified,
            rate=report.verification_rate,
        )

        return report

    def get_verified_content(
        self,
        agent_outputs: List[Dict[str, Any]],
        report: VerificationReport,
    ) -> str:
        """
        Build a filtered content string using only verified/weakly-supported claims.
        Unverified claims are excluded from the decision-making context.
        """
        verified_texts = []
        for claim in report.claims:
            if claim.status == "verified":
                verified_texts.append(f"[VERIFIED – {claim.credible_source_count} sources] {claim.claim}")
            elif claim.status == "weakly_supported":
                verified_texts.append(f"[SINGLE SOURCE] {claim.claim}")
            # Unverified claims are excluded

        return "\n".join(verified_texts) if verified_texts else ""

    # ─────────────────────────────────────────
    # Internals
    # ─────────────────────────────────────────

    def _extract_claims_from_outputs(
        self,
        agent_outputs: List[Dict[str, Any]],
        llm=None,
    ) -> List[List[str]]:
        """Extract claims from each agent output. Uses LLM if available, else heuristic."""
        all_claims = []

        for out in agent_outputs:
            text = out.get("output", "")
            if not text:
                all_claims.append([])
                continue

            if llm:
                claims = self._extract_claims_llm(text, llm)
            else:
                claims = self._extract_claims_heuristic(text)

            all_claims.append(claims)

        return all_claims

    def _extract_claims_llm(self, text: str, llm) -> List[str]:
        """Use LLM to extract factual claims from text."""
        from langchain_core.messages import HumanMessage

        prompt = (
            "Extract all specific factual claims from the following text. "
            "Return each claim on its own line, numbered. "
            "Only include concrete, verifiable statements — not opinions or qualifiers.\n\n"
            f"Text:\n{text[:4000]}\n\n"
            "Claims:"
        )

        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            lines = response.content.strip().split("\n")
            claims = []
            for line in lines:
                cleaned = line.strip().lstrip("0123456789.)- ").strip()
                if cleaned and len(cleaned) > 15:
                    claims.append(cleaned)
            return claims[:30]  # Cap at 30 claims per output
        except Exception as e:
            log.warning("LLM claim extraction failed, using heuristic", error=str(e))
            return self._extract_claims_heuristic(text)

    def _extract_claims_heuristic(self, text: str) -> List[str]:
        """Heuristic claim extraction: sentences containing numbers, dates, or strong assertions."""
        sentences = re.split(r'(?<=[.!?])\s+', text[:5000])
        claims = []

        # Patterns that indicate factual claims
        claim_patterns = [
            r'\d+%',                    # Percentages
            r'\$[\d,.]+[BMK]?',         # Dollar amounts
            r'\d{4}',                   # Years
            r'according to',            # Attribution
            r'reported that',
            r'study (found|shows|indicates)',
            r'data (shows|suggests|indicates)',
            r'grew|declined|increased|decreased',
            r'market (size|share|cap)',
            r'revenue|profit|loss|growth',
            r'million|billion|trillion',
        ]

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:
                continue
            for pattern in claim_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    claims.append(sentence)
                    break

        return claims[:30]

    def _find_corroborating_sources(
        self,
        claim: str,
        origin_idx: int,
        agent_outputs: List[Dict[str, Any]],
        credible_urls: set,
    ) -> set:
        """
        Find credible sources from OTHER agent outputs that corroborate a claim.

        Uses keyword overlap to detect if another agent's output covers
        similar content (a lightweight semantic similarity check).
        """
        claim_keywords = self._extract_keywords(claim)
        if len(claim_keywords) < 2:
            return set()

        corroborating = set()

        for idx, out in enumerate(agent_outputs):
            if idx == origin_idx:
                continue

            other_text = out.get("output", "").lower()
            other_sources = set(out.get("sources_used", [])) & credible_urls

            if not other_sources:
                continue

            # Check keyword overlap (at least 40% of claim keywords appear)
            matches = sum(1 for kw in claim_keywords if kw in other_text)
            overlap = matches / len(claim_keywords)

            if overlap >= 0.4:
                corroborating |= other_sources

        return corroborating

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract significant keywords from text (skip stop words)."""
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above",
            "below", "between", "and", "but", "or", "not", "no", "it",
            "its", "this", "that", "these", "those", "he", "she", "they",
            "we", "you", "i", "me", "my", "your", "their", "our", "than",
            "more", "most", "very", "also", "just", "about",
        }
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        return [w for w in words if w not in stop_words]

    def _normalize_claim(self, claim: str) -> str:
        """Normalize a claim for deduplication."""
        normalized = re.sub(r'\s+', ' ', claim.lower().strip())
        return hashlib.md5(normalized.encode()).hexdigest()[:16]


def _get_domain(url: str) -> str:
    """Extract root domain from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower().lstrip("www.")
    except Exception:
        return url
