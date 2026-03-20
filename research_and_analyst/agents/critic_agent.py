"""
Critic Agent — evaluates outputs for quality, accuracy, and bias.

Implements the Self-Critique Mechanism with Chain-of-Verification (CoVe).
Can operate as fact-checker, bias detector, or logic validator.
"""

from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage

from research_and_analyst.agents.base_agent import AgentResult, BaseAgent
from research_and_analyst.decision_engine.schemas import CritiqueResult
from research_and_analyst.logger import GLOBAL_LOGGER as log


FACT_CHECK_PROMPT = """\
You are a rigorous fact-checker. Analyze the following content and identify:

1. **Verified Claims**: Statements that are supported by the provided sources.
2. **Unverified Claims**: Statements that cannot be confirmed from the sources.
3. **Potential Hallucinations**: Statements that appear fabricated or not grounded in evidence.
4. **Missing Information**: Important aspects that should be covered but aren't.

Content to evaluate:
{content}

Sources used:
{sources}

Return your analysis as ONLY valid structured JSON with these fields:
- score (0-10): overall factual accuracy
- issues: list of specific problems found
- suggestions: list of improvements
- verified_claims: list of confirmed facts
- unverified_claims: list of unconfirmed statements

Do not include any conversational text or formatting outside the JSON block.

BIAS_DETECTION_PROMPT = """\
You are a bias detection specialist. Analyze the following content for:

1. **Confirmation Bias**: Does it only present supporting evidence?
2. **Selection Bias**: Are sources cherry-picked?
3. **Framing Bias**: Is the language loaded or one-sided?
4. **Recency Bias**: Does it overweight recent events?
5. **Authority Bias**: Does it uncritically accept expert opinions?

Content to evaluate:
{content}

Score from 0 (heavily biased) to 10 (well-balanced).

Return ONLY valid JSON with: score, issues, suggestions. Do not include conversational text.
"""

LOGIC_VALIDATION_PROMPT = """\
You are a logic validation expert. Analyze the following content for:

1. **Logical Fallacies**: Identify any flawed reasoning patterns.
2. **Causal Claims**: Are cause-effect claims properly supported?
3. **Consistency**: Are there internal contradictions?
4. **Evidence Quality**: Do conclusions follow from the evidence?
5. **Assumption Gaps**: What unstated assumptions are being made?

Content to evaluate:
{content}

Score from 0 (seriously flawed) to 10 (logically sound).

Return ONLY valid JSON with: score, issues, suggestions. Do not include conversational text.
"""


class CriticAgent(BaseAgent):
    """
    Multi-mode critic agent that evaluates content quality.

    Modes:
        - fact_checker: Verifies factual claims against sources
        - bias_detector: Identifies various forms of bias
        - logic_validator: Checks logical consistency and reasoning
    """

    CRITIC_PROMPTS = {
        "fact_checker": FACT_CHECK_PROMPT,
        "bias_detector": BIAS_DETECTION_PROMPT,
        "logic_validator": LOGIC_VALIDATION_PROMPT,
    }

    def __init__(self, critic_type: str = "fact_checker", llm=None):
        if critic_type not in self.CRITIC_PROMPTS:
            raise ValueError(f"Unknown critic type: {critic_type}. Use: {list(self.CRITIC_PROMPTS.keys())}")
        self.critic_type = critic_type
        super().__init__(name=f"CriticAgent-{critic_type}", agent_type="critic", llm=llm)

    def available_tools(self) -> List[str]:
        return ["web_search"]  # For fact verification

    def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        """
        Evaluate content quality.

        Args:
            task: The content to evaluate.
            context: Optional dict with 'sources' (list of source URLs/names).
        """
        ctx = context or {}
        sources = ctx.get("sources", [])
        sources_str = "\n".join(f"- {s}" for s in sources) if sources else "No sources provided."

        if not self.llm:
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                task_description=f"Critique ({self.critic_type})",
                success=False,
                error="LLM required for critique.",
            )

        prompt_template = self.CRITIC_PROMPTS[self.critic_type]
        prompt = prompt_template.format(content=task, sources=sources_str)

        response = self.llm.invoke([HumanMessage(content=prompt)])
        raw_output = response.content

        # Parse the critique result from LLM output
        critique = self._parse_critique(raw_output)

        return AgentResult(
            agent_name=self.name,
            agent_type=self.agent_type,
            task_description=f"Critique ({self.critic_type})",
            output=raw_output,
            structured_data=critique.model_dump(),
            confidence=critique.score / 10.0,
        )

    def _parse_critique(self, raw_output: str) -> CritiqueResult:
        """Parse LLM output into a CritiqueResult, with fallback for non-JSON output."""
        import json
        import re

        try:
            # First, try to extract from markdown JSON block
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_output, re.DOTALL | re.IGNORECASE)
            if match:
                json_str = match.group(1)
            else:
                # Fallback: largest curly brace block
                json_start = raw_output.find("{")
                json_end = raw_output.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = raw_output[json_start:json_end]
                else:
                    json_str = ""
            
            if json_str:
                data = json.loads(json_str)
                return CritiqueResult(
                    critic_type=self.critic_type,
                    score=float(data.get("score", 5.0)),
                    issues=data.get("issues", []),
                    suggestions=data.get("suggestions", []),
                    verified_claims=data.get("verified_claims", []),
                    unverified_claims=data.get("unverified_claims", []),
                )
        except (json.JSONDecodeError, ValueError) as e:
            log.warning(f"Failed to decode critique JSON: {e}")
            pass

        # Fallback: return a basic critique
        log.warning("Could not parse critique JSON, using fallback", critic=self.critic_type)
        return CritiqueResult(
            critic_type=self.critic_type,
            score=5.0,
            issues=["Could not parse structured critique output"],
            suggestions=["Re-run critique with structured output format"],
        )

    def critique(self, content: str, sources: List[str] = None) -> CritiqueResult:
        """Convenience method: critique content and return CritiqueResult directly."""
        result = self.run(content, context={"sources": sources or []})
        if result.success and result.structured_data:
            return CritiqueResult(**result.structured_data)
        return CritiqueResult(
            critic_type=self.critic_type,
            score=0.0,
            issues=[result.error or "Critique failed"],
        )
