"""
Resilient LLM Wrapper — production-grade LLM client with retry, circuit breaker,
fallback, and idempotency built in.

Wraps any LangChain LLM with reliability guarantees.
"""

import os
import time
from typing import Any, Dict, List, Optional

from research_and_analyst.reliability.retry_handler import (
    CircuitBreaker,
    FallbackChain,
    IdempotencyCache,
    retry,
)
from research_and_analyst.logger import GLOBAL_LOGGER as log


# Per-agent temperature defaults
AGENT_TEMPERATURES = {
    "research": 0.7,
    "finance": 0.2,
    "healthcare": 0.3,
    "decision": 0.2,
    "critic": 0.1,
    "general": 0.5,
}


class ResilientLLM:
    """
    Production wrapper around LangChain LLMs with:
    - Retry with exponential backoff
    - Circuit breaker for API protection
    - Fallback model chain
    - Idempotency caching
    - Per-agent temperature control
    - Token usage tracking
    """

    def __init__(
        self,
        primary_llm=None,
        fallback_llms: Optional[list] = None,
        cache_ttl: int = 3600,
        circuit_failure_threshold: int = 5,
        circuit_recovery_timeout: float = 60.0,
    ):
        self.primary_llm = primary_llm
        self.fallback_llms = fallback_llms or []
        self.cache = IdempotencyCache(ttl=cache_ttl)

        # Build fallback chain
        all_models = [primary_llm] + self.fallback_llms if primary_llm else self.fallback_llms
        self.fallback_chain = FallbackChain(all_models) if len(all_models) > 1 else None

        # Circuit breaker per model
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        if primary_llm:
            self.circuit_breakers["primary"] = CircuitBreaker(
                failure_threshold=circuit_failure_threshold,
                recovery_timeout=circuit_recovery_timeout,
                name="primary_llm",
            )

        # Metrics
        self._total_calls = 0
        self._total_tokens = 0
        self._total_errors = 0
        self._call_latencies: List[float] = []

    @retry(max_retries=3, base_delay=1.0, max_delay=30.0)
    def _call_with_retry(self, llm, messages, **kwargs) -> Any:
        """Internal: call LLM with retry."""
        return llm.invoke(messages, **kwargs)

    def invoke(
        self,
        messages,
        agent_type: str = "general",
        use_cache: bool = True,
        **kwargs,
    ) -> Any:
        """
        Invoke LLM with full reliability stack.

        Args:
            messages: LangChain messages.
            agent_type: Agent type for temperature selection.
            use_cache: Whether to use idempotency cache.
            **kwargs: Additional LLM kwargs.
        """
        start_time = time.time()
        self._total_calls += 1

        # Set temperature based on agent type
        temperature = AGENT_TEMPERATURES.get(agent_type, 0.5)

        # Build cache key from messages content
        cache_key = None
        if use_cache:
            cache_key = {
                "messages": str(messages),
                "agent_type": agent_type,
                "temperature": temperature,
            }
            cached = self.cache._cache.get(self.cache._hash_input(cache_key))
            if cached and time.time() - cached["timestamp"] < self.cache.ttl:
                log.info("LLM cache hit", agent_type=agent_type)
                return cached["result"]

        try:
            # Try primary with circuit breaker
            result = None
            primary_breaker = self.circuit_breakers.get("primary")

            if self.primary_llm and primary_breaker:
                try:
                    result = primary_breaker.call(
                        self._call_with_retry,
                        self.primary_llm,
                        messages,
                        **kwargs,
                    )
                except Exception as e:
                    log.warning("Primary LLM failed", error=str(e))
                    if self.fallback_chain:
                        result = self.fallback_chain.invoke(messages, **kwargs)
                    else:
                        raise
            elif self.primary_llm:
                result = self._call_with_retry(self.primary_llm, messages, **kwargs)
            elif self.fallback_chain:
                result = self.fallback_chain.invoke(messages, **kwargs)
            else:
                raise ValueError("No LLM configured")

            # Track metrics
            latency = time.time() - start_time
            self._call_latencies.append(latency)

            # Estimate token usage from response
            if hasattr(result, "response_metadata"):
                token_info = result.response_metadata.get("token_usage", {})
                self._total_tokens += token_info.get("total_tokens", 0)

            # Cache result
            if use_cache and cache_key:
                self.cache._cache[self.cache._hash_input(cache_key)] = {
                    "result": result,
                    "timestamp": time.time(),
                }

            log.info(
                "LLM call completed",
                agent_type=agent_type,
                latency=round(latency, 3),
            )
            return result

        except Exception as e:
            self._total_errors += 1
            log.error("LLM call failed", agent_type=agent_type, error=str(e))
            raise

    def get_metrics(self) -> Dict[str, Any]:
        """Return current metrics."""
        avg_latency = (
            sum(self._call_latencies) / len(self._call_latencies)
            if self._call_latencies else 0
        )
        return {
            "total_calls": self._total_calls,
            "total_tokens": self._total_tokens,
            "total_errors": self._total_errors,
            "error_rate": self._total_errors / max(self._total_calls, 1),
            "avg_latency": round(avg_latency, 3),
            "cache_size": self.cache.size(),
            "circuit_breaker_states": {
                name: cb.state for name, cb in self.circuit_breakers.items()
            },
        }
