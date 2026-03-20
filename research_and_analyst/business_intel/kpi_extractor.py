"""
KPI Extractor — extracts key performance indicators from text and structured data.

Uses LLM to identify and extract KPIs from research outputs, financial data,
and documents. Supports domain-specific KPI definitions.
"""

import json
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage

from research_and_analyst.decision_engine.schemas import KPI, KPIReport
from research_and_analyst.logger import GLOBAL_LOGGER as log


KPI_EXTRACTION_PROMPT = """\
You are a KPI extraction specialist. Extract key performance indicators from the following content.

Content:
{content}

Entity: {entity}
Domain: {domain}

Target KPIs to look for:
{target_kpis}

Return VALID JSON matching this schema:
{{
  "entity": "{entity}",
  "kpis": [
    {{
      "name": "<KPI name>",
      "value": "<extracted value with units>",
      "period": "<time period if mentioned>",
      "source": "<where in the content this was found>",
      "confidence": <0.0 to 1.0>
    }},
    ...
  ],
  "summary": "<brief narrative summary of the KPI picture>"
}}

Rules:
- Only extract KPIs that are explicitly stated or can be directly calculated.
- Include units (%, $, etc.) in the value.
- Set confidence low (< 0.5) for inferred values.
- If a target KPI is not found, omit it from results.

Return ONLY the JSON.
"""

# Domain-specific KPI definitions
DOMAIN_KPIS = {
    "finance": [
        "Revenue", "Revenue Growth (%)", "Net Income", "EBITDA",
        "Profit Margin (%)", "P/E Ratio", "Market Cap",
        "Customer Acquisition Cost (CAC)", "Lifetime Value (LTV)",
        "Debt-to-Equity Ratio", "Return on Investment (ROI)",
        "Free Cash Flow", "Gross Margin (%)",
    ],
    "healthcare": [
        "Clinical Trial Phase", "Patient Enrollment",
        "Efficacy Rate (%)", "Safety Events", "FDA Status",
        "Market Size", "Revenue", "R&D Spend",
        "Patent Expiration", "Pipeline Count",
    ],
    "general": [
        "Revenue", "Growth Rate (%)", "Market Size",
        "Market Share (%)", "User Count", "Retention Rate (%)",
        "Customer Satisfaction", "Employee Count",
    ],
}


class KPIExtractor:
    """Extracts KPIs from text content using LLM analysis."""

    def __init__(self, llm=None):
        self.llm = llm

    def extract(
        self,
        content: str,
        entity: str,
        domain: str = "general",
        target_kpis: Optional[List[str]] = None,
    ) -> KPIReport:
        """
        Extract KPIs from content.

        Args:
            content: Text to extract KPIs from.
            entity: Company or entity name.
            domain: Domain context for KPI selection.
            target_kpis: Specific KPIs to look for (overrides domain defaults).

        Returns:
            KPIReport with extracted KPIs.
        """
        kpi_targets = target_kpis or DOMAIN_KPIS.get(domain, DOMAIN_KPIS["general"])

        if not self.llm:
            return KPIReport(entity=entity, kpis=[], summary="LLM required for KPI extraction.")

        kpis_str = "\n".join(f"- {k}" for k in kpi_targets)
        prompt = KPI_EXTRACTION_PROMPT.format(
            content=content[:5000],
            entity=entity,
            domain=domain,
            target_kpis=kpis_str,
        )

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            raw = response.content.strip()

            # Strip code fences
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()

            data = json.loads(raw)

            kpis = [KPI(**k) for k in data.get("kpis", [])]
            report = KPIReport(
                entity=data.get("entity", entity),
                kpis=kpis,
                summary=data.get("summary", ""),
            )

            log.info("KPIs extracted", entity=entity, count=len(kpis))
            return report

        except (json.JSONDecodeError, Exception) as e:
            log.warning("KPI extraction failed", entity=entity, error=str(e))
            return KPIReport(entity=entity, kpis=[], summary=f"Extraction failed: {e}")

    def get_domain_kpis(self, domain: str) -> List[str]:
        """Return the default KPI list for a domain."""
        return DOMAIN_KPIS.get(domain, DOMAIN_KPIS["general"])
