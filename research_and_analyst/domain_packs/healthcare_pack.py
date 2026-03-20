"""
Healthcare Domain Pack — configuration, prompts, and tools for healthcare/biotech analysis.
"""

from research_and_analyst.domain_packs.base_pack import BaseDomainPack, DomainPackConfig


class HealthcareDomainPack(BaseDomainPack):
    """Domain pack for healthcare, pharma, and biotech analysis."""

    def get_config(self) -> DomainPackConfig:
        return DomainPackConfig(
            domain="healthcare",
            display_name="Healthcare & Biotech Analysis",
            tools=["web_search", "document_parser", "data_analyzer", "web_scraper"],
            metrics=[
                "Clinical Trial Phase", "Patient Enrollment",
                "Efficacy Rate (%)", "Safety Events", "FDA Status",
                "Market Size", "Revenue", "R&D Spend",
                "Patent Expiration", "Pipeline Count",
                "Approval Timeline", "Addressable Patient Population",
            ],
            scoring_dimensions=[
                "clinical_evidence",
                "regulatory_pathway",
                "market_need",
                "competitive_landscape",
                "safety_profile",
            ],
            agent_types=["research", "healthcare"],
            constraints=[
                "Prioritize peer-reviewed and clinical trial data",
                "Clearly distinguish FDA-approved vs experimental",
                "Include safety and adverse event information",
                "Note regulatory jurisdiction (FDA, EMA, etc.)",
                "Never provide medical advice",
            ],
        )

    def get_system_prompt(self) -> str:
        return """\
You are a healthcare and biotech research analyst producing evidence-based analysis.
Prioritize clinical data, regulatory status, and safety profiles.
Distinguish between approved treatments and experimental candidates.
Always note the phase of clinical trials and regulatory jurisdiction."""

    def get_analysis_prompt(self, query: str, context: str) -> str:
        return f"""\
## Healthcare Analysis Request

**Query:** {query}

**Available Data & Research:**
{context}

## Required Output Structure
1. **Clinical Landscape** — current treatments, unmet needs, standard of care
2. **Pipeline Analysis** — clinical trial phases, endpoints, enrollment status
3. **Regulatory Status** — FDA/EMA pathway, approval timeline, designations
4. **Safety Profile** — known adverse events, black box warnings, contraindications
5. **Market Opportunity** — addressable population, pricing, reimbursement
6. **Competitive Dynamics** — competing therapies, differentiation, market share
7. **Risk Assessment** — clinical, regulatory, commercial, IP risks
8. **Recommendation** — specific action with evidence level and confidence

Cite clinical trial identifiers (NCT numbers) where available."""
