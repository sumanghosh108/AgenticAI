"""
Healthcare Agent — specialized for healthcare, biotech, and clinical research analysis.

Uses: WebSearchTool, DocumentParserTool
"""

from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage

from research_and_analyst.agents.base_agent import AgentResult, BaseAgent
from research_and_analyst.agents.tools.web_search import WebSearchTool
from research_and_analyst.agents.tools.document_parser import DocumentParserTool
from research_and_analyst.logger import GLOBAL_LOGGER as log


HEALTHCARE_SYSTEM_PROMPT = """\
You are a healthcare and biotech research analyst. Analyze the provided clinical data,
medical research, and market information to produce evidence-based insights.

## STRICT CONTEXT RULES (MANDATORY)
- You MUST base your analysis ONLY on the web research and documents provided below.
- Do NOT use prior knowledge or training data to fill gaps.
- Every claim about clinical data, regulatory status, or efficacy MUST cite a source URL.
- If data is unavailable from sources, state "No data available from sources" — do NOT infer.
- Clearly label any inference as "[INFERENCE]".

## Output Guidelines
- Prioritize peer-reviewed sources and clinical trial data.
- Clearly distinguish between FDA-approved treatments and experimental ones.
- Note regulatory status and approval timelines.
- Flag potential safety concerns and side effects.
- Use standard medical terminology with plain-language explanations.
- Never provide medical advice — focus on market and research analysis.
"""


class HealthcareAgent(BaseAgent):
    """Agent specialized in healthcare, pharma, and biotech analysis."""

    def __init__(self, llm=None):
        super().__init__(name="HealthcareAgent", agent_type="healthcare", llm=llm)
        self.search_tool = WebSearchTool()
        self.doc_parser = DocumentParserTool()

    def available_tools(self) -> List[str]:
        return ["web_search", "document_parser"]

    def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        """Research healthcare topic: search specialized sources → parse docs → synthesize."""
        ctx = context or {}
        sources_used = []

        # Step 1: Specialized healthcare search
        search_queries = [
            f"{task} clinical research",
            f"{task} FDA approval regulatory",
            f"{task} market analysis healthcare",
        ]
        search_results = self.search_tool.multi_search(search_queries, max_results=5)
        research_context = "\n\n".join(
            f"**{r.title}** ({r.url})\n{r.snippet}" for r in search_results
        )
        sources_used = [r.url for r in search_results if r.url]

        # Step 2: Parse any provided documents
        doc_context = ""
        doc_paths = ctx.get("documents", [])
        for path in doc_paths:
            parsed = self.doc_parser.parse(path)
            if parsed.success:
                doc_context += f"\n--- Document: {parsed.filename} ---\n{parsed.text[:3000]}\n"
                sources_used.append(parsed.filename)

        # Step 3: Synthesize with LLM
        if not self.llm:
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                task_description=task,
                output=f"Research:\n{research_context}\n\nDocuments:\n{doc_context}",
                sources_used=sources_used,
            )

        synthesis_prompt = (
            f"{HEALTHCARE_SYSTEM_PROMPT}\n\n"
            f"Research Task: {task}\n\n"
            f"========== BEGIN PROVIDED CONTEXT (use ONLY this) ==========\n\n"
            f"Web Research:\n{research_context}\n\n"
            f"Document Analysis:\n{doc_context}\n\n"
            f"========== END PROVIDED CONTEXT ==========\n\n"
            f"Based ONLY on the context above, provide a comprehensive healthcare analysis with:\n"
            f"1. Current research landscape\n"
            f"2. Regulatory status\n"
            f"3. Market opportunity\n"
            f"4. Risk factors\n"
            f"5. Key recommendations\n"
            f"Cite source URLs for every claim."
        )

        response = self.llm.invoke([HumanMessage(content=synthesis_prompt)])

        return AgentResult(
            agent_name=self.name,
            agent_type=self.agent_type,
            task_description=task,
            output=response.content,
            sources_used=sources_used,
            confidence=0.6,
        )
