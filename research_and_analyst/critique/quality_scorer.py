"""
Quality Scorer — aggregates multi-critic evaluations into a unified quality assessment.

Orchestrates fact-checker, bias detector, and logic validator critics
to produce an AggregatedCritique with weighted scoring.
"""

from typing import Any, Dict, List, Optional

from research_and_analyst.agents.critic_agent import CriticAgent
from research_and_analyst.decision_engine.schemas import AggregatedCritique, CritiqueResult
from research_and_analyst.logger import GLOBAL_LOGGER as log


# Default weights for each critic type
DEFAULT_WEIGHTS = {
    "fact_checker": 0.4,
    "bias_detector": 0.3,
    "logic_validator": 0.3,
}


class QualityScorer:
    """
    Multi-critic quality assessment system.

    Runs multiple specialized critics in sequence and produces
    a weighted aggregate score with pass/fail determination.
    """

    def __init__(
        self,
        llm=None,
        critic_types: Optional[List[str]] = None,
        weights: Optional[Dict[str, float]] = None,
        pass_threshold: float = 7.0,
    ):
        self.llm = llm
        self.pass_threshold = pass_threshold

        critic_names = critic_types or list(DEFAULT_WEIGHTS.keys())
        self.weights = weights or {ct: DEFAULT_WEIGHTS.get(ct, 0.33) for ct in critic_names}

        # Normalize weights
        total_weight = sum(self.weights.values())
        self.weights = {k: v / total_weight for k, v in self.weights.items()}

        # Initialize critics
        self.critics: Dict[str, CriticAgent] = {}
        for ct in critic_names:
            try:
                self.critics[ct] = CriticAgent(critic_type=ct, llm=llm)
            except ValueError as e:
                log.warning("Skipping invalid critic type", critic=ct, error=str(e))

    def evaluate(self, content: str, sources: Optional[List[str]] = None) -> AggregatedCritique:
        """
        Run all critics and aggregate results.

        Args:
            content: Text content to evaluate.
            sources: List of source URLs/names for fact-checking.

        Returns:
            AggregatedCritique with weighted score and individual results.
        """
        results: List[CritiqueResult] = []

        for critic_type, critic in self.critics.items():
            log.info("Running critic", critic=critic_type)
            result = critic.critique(content, sources=sources)
            results.append(result)
            log.info("Critic completed", critic=critic_type, score=result.score)

        # Compute weighted average
        if results:
            weighted_sum = sum(
                r.score * self.weights.get(r.critic_type, 0.33)
                for r in results
            )
            overall_score = round(weighted_sum, 2)
        else:
            overall_score = 0.0

        passes = overall_score >= self.pass_threshold

        aggregate = AggregatedCritique(
            overall_score=overall_score,
            critiques=results,
            pass_threshold=passes,
            revision_needed=not passes,
        )

        log.info(
            "Quality evaluation complete",
            overall_score=overall_score,
            passes=passes,
            critics_run=len(results),
        )
        return aggregate

    def quick_score(self, content: str) -> float:
        """Get just the numeric score without full critique details."""
        result = self.evaluate(content)
        return result.overall_score
