"""
Document Converter — converts Markdown reports to PDF and DOCX formats.

Generates download-ready documents from the report content stored in Supabase.
File names include username for unique identification.
"""

import io
import re
import time
from typing import Optional, Tuple

from research_and_analyst.logger import GLOBAL_LOGGER as log


def _sanitize_filename(text: str) -> str:
    """Create a safe filename from text."""
    safe = re.sub(r'[^\w\s-]', '', text.lower().strip())
    safe = re.sub(r'[\s]+', '_', safe)
    return safe[:60]


def generate_file_name(username: str, topic: str, file_type: str) -> str:
    """
    Generate a unique file name that identifies the user.

    Format: {username}_{topic_slug}_{timestamp}.{ext}
    """
    topic_slug = _sanitize_filename(topic)
    ts = int(time.time())
    return f"{username}_{topic_slug}_{ts}.{file_type}"


def markdown_to_pdf(markdown_content: str, title: str = "Analysis Report") -> bytes:
    """
    Convert Markdown content to a PDF byte stream.

    Uses fpdf2 for PDF generation with formatted sections.
    Uses landscape orientation for wide tables and wraps all text safely.
    """
    from fpdf import FPDF

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Usable width (A4 portrait = 210mm, default margins 10mm each side)
    usable_w = pdf.w - pdf.l_margin - pdf.r_margin

    def _safe(text: str) -> str:
        return text.encode("latin-1", errors="replace").decode("latin-1")

    # Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.multi_cell(usable_w, 12, _safe(title), align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 8, f"Generated: {time.strftime('%Y-%m-%d %H:%M UTC')}",
             new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(6)

    # Collect table rows so we can render proper tables
    table_rows: list[list[str]] = []

    def _flush_table():
        nonlocal table_rows
        if not table_rows:
            return
        num_cols = max(len(r) for r in table_rows)
        if num_cols == 0:
            table_rows = []
            return
        col_w = usable_w / num_cols
        pdf.set_font("Helvetica", "", 8)
        for row_idx, row in enumerate(table_rows):
            x_start = pdf.l_margin
            y_start = pdf.get_y()
            max_h = 0
            # Calculate max cell height first
            cell_heights = []
            for col_idx in range(num_cols):
                cell_text = _safe(row[col_idx]) if col_idx < len(row) else ""
                # Estimate lines needed
                n_lines = max(1, int(pdf.get_string_width(cell_text) / (col_w - 2)) + 1)
                cell_h = n_lines * 4.5
                cell_heights.append(cell_h)
            max_h = max(cell_heights) if cell_heights else 5

            # Check if we need a new page
            if pdf.get_y() + max_h > pdf.h - pdf.b_margin:
                pdf.add_page()
                y_start = pdf.get_y()

            for col_idx in range(num_cols):
                cell_text = _safe(row[col_idx]) if col_idx < len(row) else ""
                pdf.set_xy(x_start + col_idx * col_w, y_start)
                if row_idx == 0:
                    pdf.set_font("Helvetica", "B", 8)
                else:
                    pdf.set_font("Helvetica", "", 8)
                pdf.multi_cell(col_w, 4.5, cell_text, border=1)

            pdf.set_y(y_start + max_h)
        pdf.ln(2)
        table_rows = []

    lines = markdown_content.split("\n")

    for line in lines:
        stripped = line.strip()

        # If we were in a table and this line is not a table row, flush
        if table_rows and not stripped.startswith("|"):
            _flush_table()

        if stripped.startswith("# "):
            continue
        elif stripped.startswith("## "):
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 14)
            pdf.multi_cell(usable_w, 10, _safe(stripped[3:].strip()))
            pdf.set_font("Helvetica", "", 10)
        elif stripped.startswith("### "):
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(usable_w, 8, _safe(stripped[4:].strip()))
            pdf.set_font("Helvetica", "", 10)
        elif stripped.startswith("|---") or stripped.startswith("| ---"):
            continue  # Table separator
        elif stripped.startswith("|"):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            table_rows.append(cells)
        elif stripped.startswith("- "):
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(usable_w, 6, _safe("  \u2022 " + stripped[2:]))
        elif stripped.startswith("*") and stripped.endswith("*") and len(stripped) > 2:
            pdf.set_font("Helvetica", "I", 9)
            pdf.multi_cell(usable_w, 5, _safe(stripped.strip("*")))
            pdf.set_font("Helvetica", "", 10)
        elif stripped == "":
            pdf.ln(2)
        else:
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(usable_w, 6, _safe(stripped))

    # Flush any remaining table
    _flush_table()

    return pdf.output()


def markdown_to_docx(markdown_content: str, title: str = "Analysis Report") -> bytes:
    """
    Convert Markdown content to a DOCX byte stream.

    Uses python-docx for Word document generation.
    """
    from docx import Document
    from docx.shared import Pt, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()

    # Title
    title_para = doc.add_heading(title, level=0)
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Date
    date_para = doc.add_paragraph(f"Generated: {time.strftime('%Y-%m-%d %H:%M UTC')}")
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_para.runs[0].font.size = Pt(9)

    doc.add_paragraph("")  # Spacer

    # Parse markdown
    lines = markdown_content.split("\n")
    in_table = False
    table_rows = []

    for line in lines:
        stripped = line.strip()

        # Flush table if we exit table context
        if in_table and not stripped.startswith("|"):
            if table_rows:
                _add_table_to_docx(doc, table_rows)
                table_rows = []
            in_table = False

        if stripped.startswith("# "):
            continue  # Skip H1 (already title)
        elif stripped.startswith("## "):
            doc.add_heading(stripped[3:].strip(), level=1)
        elif stripped.startswith("### "):
            doc.add_heading(stripped[4:].strip(), level=2)
        elif stripped.startswith("| ") and "---" not in stripped:
            in_table = True
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            table_rows.append(cells)
        elif stripped.startswith("|---"):
            continue
        elif stripped.startswith("- "):
            doc.add_paragraph(stripped[2:], style="List Bullet")
        elif stripped.startswith("**") and stripped.endswith("**"):
            p = doc.add_paragraph()
            run = p.add_run(stripped.strip("*"))
            run.bold = True
        elif stripped.startswith("*") and stripped.endswith("*"):
            p = doc.add_paragraph()
            run = p.add_run(stripped.strip("*"))
            run.italic = True
            run.font.size = Pt(9)
        elif stripped == "":
            continue
        else:
            doc.add_paragraph(stripped)

    # Flush any remaining table
    if table_rows:
        _add_table_to_docx(doc, table_rows)

    # Return as bytes
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


def _add_table_to_docx(doc, rows):
    """Add a table to the DOCX document."""
    if not rows:
        return

    from docx.shared import Pt

    num_cols = len(rows[0])
    table = doc.add_table(rows=len(rows), cols=num_cols, style="Light Grid Accent 1")

    for i, row_data in enumerate(rows):
        for j, cell_text in enumerate(row_data):
            if j < num_cols:
                cell = table.rows[i].cells[j]
                cell.text = cell_text
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(9)
                # Bold header row
                if i == 0:
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.bold = True
