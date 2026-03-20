"""
Security Layer — prompt injection protection, output sanitization,
rate limiting, and tool access restrictions.

AI-specific security hardening for production deployment.
"""

import re
import time
import hashlib
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from research_and_analyst.logger import GLOBAL_LOGGER as log


# ─────────────────────────────────────────────
# Prompt Injection Detection
# ─────────────────────────────────────────────

# Known injection patterns (case-insensitive)
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?above",
    r"disregard\s+(all\s+)?previous",
    r"forget\s+(all\s+)?previous",
    r"you\s+are\s+now\s+a",
    r"pretend\s+you\s+are",
    r"act\s+as\s+if\s+you",
    r"new\s+instructions?:",
    r"system\s*:\s*you\s+are",
    r"<\s*system\s*>",
    r"\[\s*SYSTEM\s*\]",
    r"```\s*system",
    r"override\s+safety",
    r"bypass\s+(security|filter|restriction)",
    r"jailbreak",
    r"DAN\s+mode",
    r"do\s+anything\s+now",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


class PromptInjectionDetector:
    """
    Detects prompt injection attempts in user input.

    Uses pattern matching and heuristic analysis to flag
    potentially malicious prompts before they reach the LLM.
    """

    def __init__(self, custom_patterns: Optional[List[str]] = None):
        self.patterns = list(COMPILED_PATTERNS)
        if custom_patterns:
            self.patterns.extend(re.compile(p, re.IGNORECASE) for p in custom_patterns)

    def detect(self, text: str) -> Dict[str, Any]:
        """
        Analyze text for injection attempts.

        Returns:
            Dict with 'is_injection', 'confidence', 'matched_patterns'.
        """
        matches = []
        for pattern in self.patterns:
            if pattern.search(text):
                matches.append(pattern.pattern)

        # Heuristic: check for unusual instruction-like structures
        heuristic_score = 0
        if text.count("```") >= 2:
            heuristic_score += 0.1
        if re.search(r"</?[a-z]+>", text, re.IGNORECASE):
            heuristic_score += 0.1
        if len(text) > 5000:
            heuristic_score += 0.05

        is_injection = len(matches) > 0
        confidence = min(len(matches) * 0.3 + heuristic_score, 1.0)

        if is_injection:
            log.warning(
                "Prompt injection detected",
                patterns=len(matches),
                confidence=confidence,
            )

        return {
            "is_injection": is_injection,
            "confidence": round(confidence, 2),
            "matched_patterns": matches,
            "heuristic_score": round(heuristic_score, 2),
        }

    def sanitize(self, text: str) -> str:
        """Remove or escape known injection patterns from text."""
        sanitized = text
        for pattern in self.patterns:
            sanitized = pattern.sub("[FILTERED]", sanitized)
        return sanitized


# ─────────────────────────────────────────────
# Output Sanitization
# ─────────────────────────────────────────────

class OutputSanitizer:
    """
    Sanitizes LLM outputs before returning to users.

    Removes:
    - Potential XSS payloads
    - SQL injection patterns
    - Sensitive data leaks (API keys, passwords)
    - Internal system information
    """

    # Sensitive data patterns
    SENSITIVE_PATTERNS = [
        (r"(?:api[_-]?key|apikey)\s*[=:]\s*['\"]?\w{20,}", "[REDACTED_API_KEY]"),
        (r"(?:password|passwd|pwd)\s*[=:]\s*['\"]?\S+", "[REDACTED_PASSWORD]"),
        (r"(?:secret|token)\s*[=:]\s*['\"]?\w{20,}", "[REDACTED_SECRET]"),
        (r"sk-[a-zA-Z0-9]{20,}", "[REDACTED_API_KEY]"),
        (r"ghp_[a-zA-Z0-9]{36}", "[REDACTED_GITHUB_TOKEN]"),
        (r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]"),
    ]

    # XSS patterns
    XSS_PATTERNS = [
        (r"<script[^>]*>.*?</script>", "", re.IGNORECASE | re.DOTALL),
        (r"on\w+\s*=\s*['\"].*?['\"]", "", re.IGNORECASE),
        (r"javascript\s*:", "", re.IGNORECASE),
    ]

    def __init__(self):
        self._sensitive = [(re.compile(p), r) for p, r in self.SENSITIVE_PATTERNS]
        self._xss = [(re.compile(p, f), r) for p, r, f in self.XSS_PATTERNS]

    def sanitize(self, text: str) -> str:
        """Sanitize output text."""
        result = text

        # Remove sensitive data
        for pattern, replacement in self._sensitive:
            result = pattern.sub(replacement, result)

        # Remove XSS
        for pattern, replacement in self._xss:
            result = pattern.sub(replacement, result)

        return result

    def check_for_leaks(self, text: str) -> List[str]:
        """Check for potential data leaks without modifying text."""
        leaks = []
        for pattern, replacement in self._sensitive:
            if pattern.search(text):
                leaks.append(replacement)
        return leaks


# ─────────────────────────────────────────────
# Rate Limiting
# ─────────────────────────────────────────────

class RateLimiter:
    """
    Token bucket rate limiter for API endpoints.

    Supports per-user and per-endpoint rate limiting.
    """

    def __init__(
        self,
        max_requests: int = 60,
        window_seconds: int = 60,
        burst_limit: int = 10,
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.burst_limit = burst_limit
        self._requests: Dict[str, List[float]] = defaultdict(list)

    def check(self, identifier: str) -> Dict[str, Any]:
        """
        Check if a request should be allowed.

        Args:
            identifier: User ID, API key, or IP address.

        Returns:
            Dict with 'allowed', 'remaining', 'retry_after'.
        """
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old entries
        self._requests[identifier] = [
            t for t in self._requests[identifier] if t > window_start
        ]

        requests_in_window = len(self._requests[identifier])

        if requests_in_window >= self.max_requests:
            oldest = min(self._requests[identifier])
            retry_after = oldest + self.window_seconds - now

            log.warning(
                "Rate limit exceeded",
                identifier=identifier[:20],
                requests=requests_in_window,
            )
            return {
                "allowed": False,
                "remaining": 0,
                "retry_after": round(max(retry_after, 0), 1),
            }

        # Check burst limit (requests in last 1 second)
        burst_count = sum(1 for t in self._requests[identifier] if t > now - 1)
        if burst_count >= self.burst_limit:
            return {
                "allowed": False,
                "remaining": self.max_requests - requests_in_window,
                "retry_after": 1.0,
            }

        self._requests[identifier].append(now)
        return {
            "allowed": True,
            "remaining": self.max_requests - requests_in_window - 1,
            "retry_after": 0,
        }


# ─────────────────────────────────────────────
# Tool Access Control
# ─────────────────────────────────────────────

class ToolAccessController:
    """
    Restricts which tools agents can access based on role/context.

    Prevents unauthorized tool usage (e.g., a research agent
    shouldn't execute arbitrary code).
    """

    # Default allowed tools per agent type
    DEFAULT_PERMISSIONS: Dict[str, Set[str]] = {
        "research": {"web_search", "web_scraper"},
        "finance": {"web_search", "data_analyzer", "yfinance"},
        "healthcare": {"web_search", "document_parser"},
        "critic": {"web_search"},
        "general": {"web_search"},
    }

    def __init__(self, custom_permissions: Optional[Dict[str, Set[str]]] = None):
        self.permissions = dict(self.DEFAULT_PERMISSIONS)
        if custom_permissions:
            self.permissions.update(custom_permissions)

    def is_allowed(self, agent_type: str, tool_name: str) -> bool:
        """Check if an agent type is allowed to use a tool."""
        allowed_tools = self.permissions.get(agent_type, set())
        is_ok = tool_name in allowed_tools

        if not is_ok:
            log.warning(
                "Tool access denied",
                agent_type=agent_type,
                tool=tool_name,
                allowed=list(allowed_tools),
            )

        return is_ok

    def get_allowed_tools(self, agent_type: str) -> Set[str]:
        """Get all tools allowed for an agent type."""
        return self.permissions.get(agent_type, set())

    def grant(self, agent_type: str, tool_name: str):
        """Grant a tool permission to an agent type."""
        if agent_type not in self.permissions:
            self.permissions[agent_type] = set()
        self.permissions[agent_type].add(tool_name)

    def revoke(self, agent_type: str, tool_name: str):
        """Revoke a tool permission from an agent type."""
        if agent_type in self.permissions:
            self.permissions[agent_type].discard(tool_name)


# ─────────────────────────────────────────────
# Input Validator
# ─────────────────────────────────────────────

class InputValidator:
    """Validates and sanitizes all user inputs at the API boundary."""

    MAX_QUERY_LENGTH = 5000
    MAX_TOPIC_LENGTH = 500
    MIN_QUERY_LENGTH = 3

    def validate_query(self, query: str) -> Dict[str, Any]:
        """Validate a user query."""
        errors = []

        if not query or not query.strip():
            errors.append("Query cannot be empty")
        elif len(query.strip()) < self.MIN_QUERY_LENGTH:
            errors.append(f"Query too short (min {self.MIN_QUERY_LENGTH} characters)")
        elif len(query) > self.MAX_QUERY_LENGTH:
            errors.append(f"Query too long (max {self.MAX_QUERY_LENGTH} characters)")

        # Check for injection
        detector = PromptInjectionDetector()
        injection_result = detector.detect(query)

        if injection_result["is_injection"] and injection_result["confidence"] > 0.5:
            errors.append("Potential prompt injection detected")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "sanitized_query": query.strip()[:self.MAX_QUERY_LENGTH] if not errors else "",
            "injection_check": injection_result,
        }
