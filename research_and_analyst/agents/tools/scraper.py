"""
Web Scraper Tool — extracts text content from web pages.
Uses BeautifulSoup with requests, with fallback error handling.
"""

from typing import Optional

import requests
from pydantic import BaseModel, Field
from research_and_analyst.logger import GLOBAL_LOGGER as log


class ScrapedContent(BaseModel):
    url: str
    title: str = ""
    text: str = ""
    word_count: int = 0
    success: bool = True
    error: str = ""


class WebScraperTool:
    """Extracts readable text content from web pages."""

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (compatible; AgenticAI-Research/1.0)"
    }
    TIMEOUT = 15

    def scrape(self, url: str, max_chars: int = 10000) -> ScrapedContent:
        """Scrape a URL and return extracted text."""
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=self.TIMEOUT)
            resp.raise_for_status()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "lxml")

            # Remove script and style elements
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()

            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            text = soup.get_text(separator="\n", strip=True)

            # Collapse whitespace
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            clean_text = "\n".join(lines)[:max_chars]

            log.info("Page scraped successfully", url=url, chars=len(clean_text))
            return ScrapedContent(
                url=url,
                title=title,
                text=clean_text,
                word_count=len(clean_text.split()),
            )

        except Exception as e:
            log.error("Scrape failed", url=url, error=str(e))
            return ScrapedContent(url=url, success=False, error=str(e))

    def scrape_multiple(self, urls: list[str], max_chars: int = 5000) -> list[ScrapedContent]:
        """Scrape multiple URLs."""
        results = []
        for url in urls:
            results.append(self.scrape(url, max_chars))
        return results
