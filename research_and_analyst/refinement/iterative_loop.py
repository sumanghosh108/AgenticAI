"""
Iterative Refinement Loop — Generate → Evaluate → Improve → Repeat.

Implements the core refinement pattern with:
- Configurable stopping criteria (score threshold, max iterations, token budget)
- Version tracking for each iteration
- Integration with the multi-critic system
"""

from typing import Any, Callable, Dict, List, Optional

from langchain_core.messages import HumanMessage

from research_and_analyst.decision_engine.schemas import (
    AggregatedCritique,
    CritiqueResult,
    RefinementVersion,
)
from research_and_analyst.logger import GLOBAL_LOGGER as log


REFINEMENT_PROMPT = """\
You are an expert editor. Improve the following content based on the critique feedback.

## Original Content
{content}

## Critique Feedback
Overall Score: {score}/10
Issues Found:
{issues}

Suggestions:
{suggestions}

## Instructions
1. Address each issue identified by the critique.
2. Implement the suggestions where appropriate.
3. Maintain the original structure and intent.
4. Improve clarity, accuracy, and completeness.
5. Do NOT add disclaimers about the revision process.

Return the improved content only.
"""


class RefinementConfig:
    """Configuration for the refinement loop."""

    def __init__(
        self,
        max_iterations: int = 3,
        score_threshold: float = 7.5,
        max_token_budget: int = 50000,
        min_improvement: float = 0.5,
    ):
        self.max_iterations = max_iterations
        self.score_threshold = score_threshold
        self.max_token_budget = max_token_budget
        self.min_improvement = min_improvement


class IterativeRefinementLoop:
    """
    Generate → Evaluate → Improve → Repeat

    Coordinates between content generation and the critic system
    to iteratively improve output quality.
    """

    def __init__(
        self,
        llm=None,
        critics: Optional[List[Any]] = None,
        config: Optional[RefinementConfig] = None,
    ):
        self.llm = llm
        self.critics = critics or []
        self.config = config or RefinementConfig()
        self.versions: List[RefinementVersion] = []
        self.total_tokens = 0

    def run(
        self,
        initial_content: str,
        critique_fn: Optional[Callable[[str], AggregatedCritique]] = None,
    ) -> Dict[str, Any]:
        """
        Run the refinement loop.

        Args:
            initial_content: The initial generated content.
            critique_fn: Optional custom critique function. If not provided,
                         uses self.critics to evaluate.

        Returns:
            Dict with 'final_content', 'versions', 'iterations', 'final_score'.
        """
        current_content = initial_content
        evaluate = critique_fn or self._default_critique

        for iteration in range(1, self.config.max_iterations + 1):
            log.info("Refinement iteration", iteration=iteration)

            # Step 1: Evaluate current content
            critique = evaluate(current_content)

            # Track version
            est_tokens = len(current_content.split()) * 2  # rough estimate
            self.total_tokens += est_tokens
            version = RefinementVersion(
                iteration=iteration,
                content=current_content,
                critique=critique,
                token_usage=est_tokens,
            )
            self.versions.append(version)

            # Step 2: Check stopping criteria
            if self._should_stop(critique, iteration):
                log.info(
                    "Refinement complete",
                    iteration=iteration,
                    score=critique.overall_score,
                    reason=self._stop_reason(critique, iteration),
                )
                break

            # Step 3: Improve content based on critique
            current_content = self._improve(current_content, critique)

        return {
            "final_content": current_content,
            "versions": self.versions,
            "iterations": len(self.versions),
            "final_score": self.versions[-1].critique.overall_score if self.versions else 0,
            "total_tokens": self.total_tokens,
        }

    def _should_stop(self, critique: AggregatedCritique, iteration: int) -> bool:
        """Check all stopping criteria."""
        # Score threshold met
        if critique.overall_score >= self.config.score_threshold:
            return True

        # Max iterations reached
        if iteration >= self.config.max_iterations:
            return True

        # Token budget exhausted
        if self.total_tokens >= self.config.max_token_budget:
            return True

        # Insufficient improvement (after at least 2 iterations)
        if len(self.versions) >= 2:
            prev_score = self.versions[-2].critique.overall_score if self.versions[-2].critique else 0
            improvement = critique.overall_score - prev_score
            if improvement < self.config.min_improvement:
                return True

        return False

    def _stop_reason(self, critique: AggregatedCritique, iteration: int) -> str:
        """Return why the loop stopped."""
        if critique.overall_score >= self.config.score_threshold:
            return "score_threshold_met"
        if iteration >= self.config.max_iterations:
            return "max_iterations_reached"
        if self.total_tokens >= self.config.max_token_budget:
            return "token_budget_exhausted"
        return "insufficient_improvement"

    def _improve(self, content: str, critique: AggregatedCritique) -> str:
        """Use LLM to improve content based on critique."""
        if not self.llm:
            log.warning("No LLM available for refinement, returning original")
            return content

        issues_str = "\n".join(f"- {issue}" for c in critique.critiques for issue in c.issues)
        suggestions_str = "\n".join(f"- {s}" for c in critique.critiques for s in c.suggestions)

        prompt = REFINEMENT_PROMPT.format(
            content=content,
            score=critique.overall_score,
            issues=issues_str or "None identified",
            suggestions=suggestions_str or "None provided",
        )

        response = self.llm.invoke([HumanMessage(content=prompt)])
        improved = response.content.strip()

        log.info("Content improved", original_len=len(content), improved_len=len(improved))
        return improved

    def _default_critique(self, content: str) -> AggregatedCritique:
        """Default critique using self.critics list."""
        if not self.critics:
            return AggregatedCritique(
                overall_score=5.0,
                critiques=[
                    CritiqueResult(
                        critic_type="default",
                        score=5.0,
                        issues=["No critics configured"],
                        suggestions=["Add critic agents for quality evaluation"],
                    )
                ],
                pass_threshold=False,
                revision_needed=True,
            )

        results = []
        for critic in self.critics:
            result = critic.critique(content)
            results.append(result)

        avg_score = sum(r.score for r in results) / len(results)

        return AggregatedCritique(
            overall_score=round(avg_score, 2),
            critiques=results,
            pass_threshold=avg_score >= self.config.score_threshold,
            revision_needed=avg_score < self.config.score_threshold,
        )
