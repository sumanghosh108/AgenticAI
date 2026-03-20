"""
Enterprise Report Formatter — generates polished PDF and Markdown reports.

Produces executive-grade output with:
- Executive summary
- Key insights
- Risks
- Recommendations
- KPIs
- Source credibility assessment
"""

import os
import time
from typing import Optional

from research_and_analyst.decision_engine.schemas import EnterpriseReport
from research_and_analyst.logger import GLOBAL_LOGGER as log


class ReportFormatter:
    """Formats EnterpriseReport into PDF and Markdown outputs."""

    def __init__(self, output_dir: str = "generated_report"):
        self.output_dir = output_dir

    def to_markdown(self, report: EnterpriseReport, title: str = "Analysis Report") -> str:
        """Convert EnterpriseReport to formatted Markdown."""
        sections = []

        # Title
        sections.append(f"# {title}")
        sections.append(f"*Generated: {time.strftime('%Y-%m-%d %H:%M UTC')}*\n")

        # Executive Summary
        sections.append("## Executive Summary")
        sections.append(report.executive_summary + "\n")

        # Decision (if present)
        if report.decision:
            d = report.decision
            sections.append("## Decision")
            sections.append(f"**Recommendation:** {d.decision}")
            sections.append(f"**Confidence:** {d.confidence:.0%}\n")
            sections.append("### Reasons")
            for r in d.reasons:
                sections.append(f"- {r}")
            sections.append("")
            if d.risks:
                sections.append("### Risks")
                for r in d.risks:
                    sections.append(f"- {r}")
                sections.append("")
            if d.scoring:
                sections.append("### Scoring Breakdown")
                sections.append("| Dimension | Score | Reasoning |")
                sections.append("|-----------|-------|-----------|")
                for s in d.scoring:
                    sections.append(f"| {s.name} | {s.score:.2f} | {s.reasoning} |")
                sections.append("")

        # Key Insights
        sections.append("## Key Insights")
        for insight in report.key_insights:
            sections.append(f"- {insight}")
        sections.append("")

        # Risks
        sections.append("## Risks")
        for risk in report.risks:
            sections.append(f"- {risk}")
        sections.append("")

        # Recommendations
        sections.append("## Recommendations")
        for rec in report.recommendations:
            sections.append(f"- {rec}")
        sections.append("")

        # KPIs (if present)
        if report.kpis and report.kpis.kpis:
            sections.append(f"## Key Performance Indicators — {report.kpis.entity}")
            sections.append("| KPI | Value | Period | Confidence |")
            sections.append("|-----|-------|--------|------------|")
            for kpi in report.kpis.kpis:
                sections.append(
                    f"| {kpi.name} | {kpi.value} | {kpi.period} | {kpi.confidence:.0%} |"
                )
            sections.append(f"\n*{report.kpis.summary}*\n")

        # Source Credibility
        if report.sources:
            sections.append("## Source Credibility Assessment")
            sections.append("| Source | Credibility | Authority |")
            sections.append("|--------|------------|-----------|")
            for src in report.sources:
                sections.append(
                    f"| {src.source[:60]} | {src.credibility:.0%} | {src.domain_authority} |"
                )
            sections.append("")

        return "\n".join(sections)

    def to_pdf(self, report: EnterpriseReport, title: str = "Analysis Report", filename: str = "report.pdf") -> str:
        """Generate a PDF report using fpdf2."""
        try:
            from fpdf import FPDF
        except ImportError:
            log.error("fpdf2 not installed, cannot generate PDF")
            return ""

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Title
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, f"Generated: {time.strftime('%Y-%m-%d %H:%M UTC')}", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(8)

        # Executive Summary
        self._pdf_section(pdf, "Executive Summary", report.executive_summary)

        # Decision
        if report.decision:
            d = report.decision
            decision_text = (
                f"Recommendation: {d.decision}\n"
                f"Confidence: {d.confidence:.0%}\n\n"
                f"Reasons:\n" + "\n".join(f"  - {r}" for r in d.reasons)
            )
            if d.risks:
                decision_text += "\n\nRisks:\n" + "\n".join(f"  - {r}" for r in d.risks)
            self._pdf_section(pdf, "Decision", decision_text)

        # Key Insights
        insights_text = "\n".join(f"- {i}" for i in report.key_insights)
        self._pdf_section(pdf, "Key Insights", insights_text)

        # Risks
        risks_text = "\n".join(f"- {r}" for r in report.risks)
        self._pdf_section(pdf, "Risks", risks_text)

        # Recommendations
        recs_text = "\n".join(f"- {r}" for r in report.recommendations)
        self._pdf_section(pdf, "Recommendations", recs_text)

        # KPIs
        if report.kpis and report.kpis.kpis:
            kpi_text = f"Entity: {report.kpis.entity}\n\n"
            for kpi in report.kpis.kpis:
                kpi_text += f"- {kpi.name}: {kpi.value} ({kpi.period}) [Confidence: {kpi.confidence:.0%}]\n"
            kpi_text += f"\n{report.kpis.summary}"
            self._pdf_section(pdf, "Key Performance Indicators", kpi_text)

        # Save
        save_dir = os.path.join(self.output_dir, f"decision_{int(time.time())}")
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)
        pdf.output(filepath)

        log.info("PDF report generated", path=filepath)
        return filepath

    def save_markdown(self, markdown: str, filename: str = "report.md") -> str:
        """Save markdown report to file."""
        save_dir = os.path.join(self.output_dir, f"decision_{int(time.time())}")
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown)

        log.info("Markdown report saved", path=filepath)
        return filepath

    def _pdf_section(self, pdf, heading: str, body: str) -> None:
        """Add a section to the PDF."""
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, heading, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        # Handle encoding issues
        safe_body = body.encode("latin-1", errors="replace").decode("latin-1")
        pdf.multi_cell(0, 6, safe_body)
        pdf.ln(4)
