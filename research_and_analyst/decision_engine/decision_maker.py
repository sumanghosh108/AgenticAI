"""
Decision Engine — produces structured decisions with scoring rubrics.

Takes agent outputs, applies a scoring rubric with configurable dimensions,
and produces a Decision with confidence, reasons, risks, and alternatives.
"""

import json
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage

from research_and_analyst.decision_engine.schemas import Decision, ScoringDimension
from research_and_analyst.logger import GLOBAL_LOGGER as log


DECISION_PROMPT = """\
You are a decision engine that produces structured, actionable decisions.

## Input
Query: {query}
Domain: {domain}

## Agent Research Outputs
{agent_outputs}

## Constraints
{constraints}

## Scoring Rubric
Evaluate on these dimensions (score each 0.0 to 1.0):
{scoring_dimensions}

## Instructions
Based on the research outputs and scoring rubric, produce a structured decision.

Return VALID JSON matching this schema exactly:
{{
  "decision": "<recommended action — be specific>",
  "confidence": <0.0 to 1.0>,
  "reasons": ["<reason 1>", "<reason 2>", ...],
  "risks": ["<risk 1>", "<risk 2>", ...],
  "scoring": [
    {{"name": "<dimension>", "score": <0.0-1.0>, "reasoning": "<why>"}},
    ...
  ],
  "alternatives": ["<alternative action 1>", ...]
}}

Rules:
- Decision must be actionable (e.g., "Invest", "Hold", "Reject", "Proceed with caution").
- Confidence is the weighted average of scoring dimensions.
- Include at least 3 reasons and 2 risks.
- Consider at least 2 alternatives.
- Be specific and data-driven in your reasoning.

Return ONLY the JSON.
"""

# Default scoring dimensions by domain
DEFAULT_RUBRICS = {
    "finance": [
        "growth_potential",
        "market_competition",
        "financial_health",
        "risk_adjusted_return",
        "management_quality",
    ],
    "healthcare": [
        "clinical_evidence",
        "regulatory_pathway",
        "market_need",
        "competitive_landscape",
        "safety_profile",
    ],
    "general": [
        "feasibility",
        "impact_potential",
        "risk_level",
        "data_quality",
        "strategic_alignment",
    ],
}


class DecisionMaker:
    """Produces structured decisions from agent outputs using a scoring rubric."""

    def __init__(self, llm=None):
        self.llm = llm

    def decide(
        self,
        query: str,
        agent_outputs: List[Dict[str, Any]],
        domain: str = "general",
        constraints: Optional[List[str]] = None,
        custom_rubric: Optional[List[str]] = None,
    ) -> Decision:
        """
        Generate a structured decision.

        Args:
            query: Original user query.
            agent_outputs: List of agent result dicts.
            domain: Domain context.
            constraints: Decision constraints.
            custom_rubric: Custom scoring dimensions (overrides domain default).

        Returns:
            Decision with confidence, reasons, risks, scoring.
        """
        rubric = custom_rubric or DEFAULT_RUBRICS.get(domain, DEFAULT_RUBRICS["general"])
        constraints_list = constraints or ["Use available data only"]

        # Format agent outputs for the prompt
        outputs_str = ""
        for i, out in enumerate(agent_outputs, 1):
            agent_name = out.get("agent_name", f"Agent {i}")
            output = out.get("output", "")
            outputs_str += f"\n### {agent_name}\n{output[:3000]}\n"

        rubric_str = "\n".join(f"- {dim}" for dim in rubric)
        constraints_str = "\n".join(f"- {c}" for c in constraints_list)

        if not self.llm:
            return self._fallback_decision(query, agent_outputs, rubric)

        prompt = DECISION_PROMPT.format(
            query=query,
            domain=domain,
            agent_outputs=outputs_str,
            constraints=constraints_str,
            scoring_dimensions=rubric_str,
        )

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            raw = response.content.strip()

            # Strip markdown code fences
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()

            data = json.loads(raw)

            scoring = [
                ScoringDimension(**s) for s in data.get("scoring", [])
            ]

            decision = Decision(
                decision=data.get("decision", "Insufficient data"),
                confidence=float(data.get("confidence", 0.5)),
                reasons=data.get("reasons", []),
                risks=data.get("risks", []),
                scoring=scoring,
                alternatives=data.get("alternatives", []),
            )

            log.info(
                "Decision generated",
                decision=decision.decision,
                confidence=decision.confidence,
            )
            return decision

        except (json.JSONDecodeError, Exception) as e:
            log.warning("Decision parsing failed, using fallback", error=str(e))
            return self._fallback_decision(query, agent_outputs, rubric)

    def _fallback_decision(
        self, query: str, agent_outputs: List[Dict[str, Any]], rubric: List[str]
    ) -> Decision:
        """Produce a conservative decision when LLM fails."""
        return Decision(
            decision="Requires further analysis",
            confidence=0.3,
            reasons=[
                "Automated analysis completed with limited data",
                f"Based on {len(agent_outputs)} agent report(s)",
            ],
            risks=["Decision engine could not produce high-confidence result"],
            scoring=[
                ScoringDimension(name=dim, score=0.5, reasoning="Default — LLM scoring unavailable")
                for dim in rubric
            ],
            alternatives=["Manual review recommended", "Gather additional data"],
        )
