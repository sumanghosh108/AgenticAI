"""
Document Parser Tool — extracts text from PDFs, CSVs, and other structured files.
"""

import io
import os
from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from research_and_analyst.logger import GLOBAL_LOGGER as log


class ParsedDocument(BaseModel):
    filename: str
    file_type: str
    text: str = ""
    pages: int = 0
    metadata: Dict[str, str] = Field(default_factory=dict)
    success: bool = True
    error: str = ""


class DocumentParserTool:
    """Parses PDFs, CSVs, and text files into structured text."""

    def parse_pdf(self, file_path: str) -> ParsedDocument:
        """Extract text from a PDF using PyMuPDF (fitz)."""
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(file_path)
            pages_text = []
            for page in doc:
                pages_text.append(page.get_text())
            doc.close()

            full_text = "\n\n".join(pages_text)
            log.info("PDF parsed", file=file_path, pages=len(pages_text))
            return ParsedDocument(
                filename=os.path.basename(file_path),
                file_type="pdf",
                text=full_text,
                pages=len(pages_text),
            )
        except ImportError:
            # Fallback to fpdf2's reader or basic extraction
            return self._parse_pdf_fallback(file_path)
        except Exception as e:
            log.error("PDF parse failed", file=file_path, error=str(e))
            return ParsedDocument(
                filename=os.path.basename(file_path),
                file_type="pdf",
                success=False,
                error=str(e),
            )

    def _parse_pdf_fallback(self, file_path: str) -> ParsedDocument:
        """Fallback PDF parser using pdfplumber."""
        try:
            import pdfplumber

            pages_text = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages_text.append(text)

            full_text = "\n\n".join(pages_text)
            return ParsedDocument(
                filename=os.path.basename(file_path),
                file_type="pdf",
                text=full_text,
                pages=len(pages_text),
            )
        except Exception as e:
            log.error("PDF fallback parse failed", file=file_path, error=str(e))
            return ParsedDocument(
                filename=os.path.basename(file_path),
                file_type="pdf",
                success=False,
                error=f"No PDF parser available: {e}",
            )

    def parse_csv(self, file_path: str) -> ParsedDocument:
        """Parse CSV into a text summary using pandas."""
        try:
            import pandas as pd

            df = pd.read_csv(file_path)
            summary = (
                f"Columns: {list(df.columns)}\n"
                f"Rows: {len(df)}\n\n"
                f"First 10 rows:\n{df.head(10).to_string()}\n\n"
                f"Statistics:\n{df.describe().to_string()}"
            )
            log.info("CSV parsed", file=file_path, rows=len(df))
            return ParsedDocument(
                filename=os.path.basename(file_path),
                file_type="csv",
                text=summary,
                metadata={"rows": str(len(df)), "columns": str(len(df.columns))},
            )
        except Exception as e:
            log.error("CSV parse failed", file=file_path, error=str(e))
            return ParsedDocument(
                filename=os.path.basename(file_path),
                file_type="csv",
                success=False,
                error=str(e),
            )

    def parse_text(self, file_path: str) -> ParsedDocument:
        """Parse plain text or markdown files."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            return ParsedDocument(
                filename=os.path.basename(file_path),
                file_type="text",
                text=text,
            )
        except Exception as e:
            return ParsedDocument(
                filename=os.path.basename(file_path),
                file_type="text",
                success=False,
                error=str(e),
            )

    def parse(self, file_path: str) -> ParsedDocument:
        """Auto-detect file type and parse accordingly."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return self.parse_pdf(file_path)
        elif ext == ".csv":
            return self.parse_csv(file_path)
        elif ext in (".txt", ".md", ".json", ".yaml", ".yml"):
            return self.parse_text(file_path)
        else:
            return ParsedDocument(
                filename=os.path.basename(file_path),
                file_type=ext,
                success=False,
                error=f"Unsupported file type: {ext}",
            )
