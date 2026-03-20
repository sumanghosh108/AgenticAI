"""
Evaluation & Quality Control — automated testing for AI output quality.

Provides:
- Output scoring (accuracy, completeness, relevance)
- Automated AI quality tests
- Human-in-the-loop feedback integration
- Regression testing for prompt changes
"""

import json
import time
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field
from research_and_analyst.logger import GLOBAL_LOGGER as log


# ─────────────────────────────────────────────
# Quality Dimensions
# ─────────────────────────────────────────────

class QualityScore(BaseModel):
    """Scores for a single quality evaluation."""
    accuracy: float = Field(ge=0, le=10, description="Factual accuracy")
    completeness: float = Field(ge=0, le=10, description="Coverage of required topics")
    relevance: float = Field(ge=0, le=10, description="Relevance to the original query")
    coherence: float = Field(ge=0, le=10, description="Logical flow and clarity")
    actionability: float = Field(ge=0, le=10, description="How actionable are the recommendations")
    source_quality: float = Field(ge=0, le=10, description="Quality and credibility of sources")

    @property
    def overall(self) -> float:
        scores = [
            self.accuracy, self.completeness, self.relevance,
            self.coherence, self.actionability, self.source_quality,
        ]
        return round(sum(scores) / len(scores), 2)

    @property
    def passes(self) -> bool:
        return self.overall >= 7.0 and min(
            self.accuracy, self.completeness, self.relevance
        ) >= 5.0


class EvaluationResult(BaseModel):
    """Result of a quality evaluation."""
    test_name: str
    passed: bool
    score: QualityScore
    details: str = ""
    timestamp: float = Field(default_factory=time.time)


# ─────────────────────────────────────────────
# Output Scorer
# ─────────────────────────────────────────────

class OutputScorer:
    """
    Scores AI outputs on multiple quality dimensions.

    Can use LLM-as-judge or rule-based scoring.
    """

    def __init__(self, llm=None):
        self.llm = llm

    def score(self, query: str, output: str, sources: Optional[List[str]] = None) -> QualityScore:
        """Score an output against a query."""
        if self.llm:
            return self._llm_score(query, output, sources)
        return self._heuristic_score(query, output, sources)

    def _heuristic_score(self, query: str, output: str, sources: Optional[List[str]]) -> QualityScore:
        """Rule-based scoring when no LLM is available."""
        word_count = len(output.split())
        has_structure = any(marker in output for marker in ["##", "**", "- ", "1."])
        query_terms = set(query.lower().split())
        output_lower = output.lower()
        term_coverage = sum(1 for t in query_terms if t in output_lower) / max(len(query_terms), 1)
        source_count = len(sources) if sources else 0

        return QualityScore(
            accuracy=6.0 + (1.0 if source_count > 2 else 0),
            completeness=min(word_count / 100, 9.0),
            relevance=round(term_coverage * 10, 1),
            coherence=7.0 if has_structure else 5.0,
            actionability=6.0 if any(w in output_lower for w in ["recommend", "suggest", "should", "action"]) else 4.0,
            source_quality=min(source_count * 2.0, 9.0),
        )

    def _llm_score(self, query: str, output: str, sources: Optional[List[str]]) -> QualityScore:
        """LLM-as-judge scoring."""
        from langchain_core.messages import HumanMessage

        prompt = f"""Score the following AI output on these dimensions (0-10 each):
- accuracy: factual correctness
- completeness: coverage of required topics
- relevance: relevance to the query
- coherence: logical flow and clarity
- actionability: how actionable are recommendations
- source_quality: quality of cited sources

Query: {query}
Output: {output[:3000]}
Sources: {sources if sources else 'None cited'}

Return ONLY valid JSON: {{"accuracy": N, "completeness": N, "relevance": N, "coherence": N, "actionability": N, "source_quality": N}}"""

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(raw)
            return QualityScore(**data)
        except Exception as e:
            log.warning("LLM scoring failed, using heuristic", error=str(e))
            return self._heuristic_score(query, output, sources)


# ─────────────────────────────────────────────
# AI Quality Test Suite
# ─────────────────────────────────────────────

class QualityTestSuite:
    """
    Automated test suite for AI output quality.

    Usage:
        suite = QualityTestSuite(scorer)
        suite.add_test("market_analysis", query="...", min_score=7.0)
        results = suite.run(generate_fn)
    """

    def __init__(self, scorer: Optional[OutputScorer] = None):
        self.scorer = scorer or OutputScorer()
        self.tests: List[Dict[str, Any]] = []
        self.results: List[EvaluationResult] = []

    def add_test(
        self,
        name: str,
        query: str,
        expected_keywords: Optional[List[str]] = None,
        min_score: float = 7.0,
        domain: str = "general",
    ):
        """Add a test case."""
        self.tests.append({
            "name": name,
            "query": query,
            "expected_keywords": expected_keywords or [],
            "min_score": min_score,
            "domain": domain,
        })

    def run(self, generate_fn: Callable[[str, str], str]) -> List[EvaluationResult]:
        """
        Run all tests against a generation function.

        Args:
            generate_fn: Function(query, domain) -> output_text

        Returns:
            List of EvaluationResult.
        """
        self.results = []

        for test in self.tests:
            log.info("Running quality test", test=test["name"])

            try:
                output = generate_fn(test["query"], test["domain"])
                score = self.scorer.score(test["query"], output)

                # Check keyword coverage
                keyword_hits = 0
                if test["expected_keywords"]:
                    output_lower = output.lower()
                    keyword_hits = sum(
                        1 for kw in test["expected_keywords"]
                        if kw.lower() in output_lower
                    )

                passed = score.overall >= test["min_score"]
                details = (
                    f"Overall: {score.overall}/10 (min: {test['min_score']}), "
                    f"Keywords: {keyword_hits}/{len(test['expected_keywords'])}"
                )

                result = EvaluationResult(
                    test_name=test["name"],
                    passed=passed,
                    score=score,
                    details=details,
                )

            except Exception as e:
                result = EvaluationResult(
                    test_name=test["name"],
                    passed=False,
                    score=QualityScore(
                        accuracy=0, completeness=0, relevance=0,
                        coherence=0, actionability=0, source_quality=0,
                    ),
                    details=f"Test failed with error: {e}",
                )

            self.results.append(result)
            log.info(
                "Quality test completed",
                test=test["name"],
                passed=result.passed,
                score=result.score.overall,
            )

        return self.results

    def summary(self) -> Dict[str, Any]:
        """Get test summary."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        return {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / max(total, 1) * 100, 1),
            "results": [
                {"name": r.test_name, "passed": r.passed, "score": r.score.overall}
                for r in self.results
            ],
        }


# ─────────────────────────────────────────────
# Human Feedback Store
# ─────────────────────────────────────────────

class FeedbackStore:
    """Stores and retrieves human feedback on AI outputs."""

    def __init__(self):
        self._feedback: List[Dict[str, Any]] = []

    def submit(
        self,
        task_id: str,
        rating: int,
        comment: str = "",
        user_id: str = "",
    ) -> str:
        """Submit feedback for a task output."""
        import uuid
        feedback_id = str(uuid.uuid4())[:8]
        self._feedback.append({
            "feedback_id": feedback_id,
            "task_id": task_id,
            "rating": max(1, min(rating, 5)),
            "comment": comment,
            "user_id": user_id,
            "timestamp": time.time(),
        })
        log.info("Feedback submitted", task_id=task_id, rating=rating)
        return feedback_id

    def get_feedback(self, task_id: str) -> List[Dict[str, Any]]:
        """Get all feedback for a task."""
        return [f for f in self._feedback if f["task_id"] == task_id]

    def average_rating(self) -> float:
        """Get average rating across all feedback."""
        if not self._feedback:
            return 0.0
        return round(sum(f["rating"] for f in self._feedback) / len(self._feedback), 2)

    def get_stats(self) -> Dict[str, Any]:
        """Get feedback statistics."""
        ratings = [f["rating"] for f in self._feedback]
        return {
            "total_feedback": len(ratings),
            "average_rating": self.average_rating(),
            "distribution": {r: ratings.count(r) for r in range(1, 6)},
        }
