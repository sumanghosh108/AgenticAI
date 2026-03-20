"""
Retry Handler — exponential backoff with jitter for resilient API calls.

Provides decorators and utilities for:
- Configurable retry with exponential backoff
- Circuit breaker pattern to prevent cascading failures
- Fallback model chains
- Idempotent request caching
"""

import hashlib
import json
import time
import random
import functools
from typing import Any, Callable, Dict, List, Optional, Type

from research_and_analyst.logger import GLOBAL_LOGGER as log


# ─────────────────────────────────────────────
# Retry with Exponential Backoff
# ─────────────────────────────────────────────

class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[List[Type[Exception]]] = None,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [Exception]


def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Optional[List[Type[Exception]]] = None,
):
    """
    Decorator: retry a function with exponential backoff.

    Usage:
        @retry(max_retries=3, base_delay=1.0)
        def call_llm(prompt):
            return llm.invoke(prompt)
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions,
    )

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        log.info(
                            "Retry succeeded",
                            function=func.__name__,
                            attempt=attempt + 1,
                        )
                    return result
                except tuple(config.retryable_exceptions) as e:
                    last_exception = e
                    if attempt < config.max_retries:
                        delay = min(
                            config.base_delay * (config.exponential_base ** attempt),
                            config.max_delay,
                        )
                        if config.jitter:
                            delay *= (0.5 + random.random())

                        log.warning(
                            "Retrying after failure",
                            function=func.__name__,
                            attempt=attempt + 1,
                            delay=round(delay, 2),
                            error=str(e),
                        )
                        time.sleep(delay)
                    else:
                        log.error(
                            "All retries exhausted",
                            function=func.__name__,
                            max_retries=config.max_retries,
                            error=str(e),
                        )

            raise last_exception

        return wrapper
    return decorator


# ─────────────────────────────────────────────
# Circuit Breaker
# ─────────────────────────────────────────────

class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open (service unavailable)."""
    pass


class CircuitBreaker:
    """
    Circuit breaker pattern — stops calling a failing service temporarily.

    States:
    - CLOSED: Normal operation, calls pass through
    - OPEN: Service is failing, calls are blocked
    - HALF_OPEN: Testing if service has recovered

    Usage:
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30)

        @breaker
        def call_external_api():
            ...
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 2,
        name: str = "default",
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.name = name

        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0

    @property
    def state(self) -> str:
        if self._state == self.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = self.HALF_OPEN
                log.info("Circuit breaker half-open", breaker=self.name)
        return self._state

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker."""
        current_state = self.state

        if current_state == self.OPEN:
            log.warning("Circuit breaker OPEN, call blocked", breaker=self.name)
            raise CircuitBreakerOpen(
                f"Circuit breaker '{self.name}' is OPEN. "
                f"Service unavailable, retry after {self.recovery_timeout}s."
            )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Record successful call."""
        if self._state == self.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._state = self.CLOSED
                self._failure_count = 0
                self._success_count = 0
                log.info("Circuit breaker CLOSED (recovered)", breaker=self.name)
        else:
            self._failure_count = 0

    def _on_failure(self):
        """Record failed call."""
        self._failure_count += 1
        self._success_count = 0
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            self._state = self.OPEN
            log.error(
                "Circuit breaker OPEN (threshold reached)",
                breaker=self.name,
                failures=self._failure_count,
            )

    def reset(self):
        """Manually reset the circuit breaker."""
        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0


# ─────────────────────────────────────────────
# Fallback Model Chain
# ─────────────────────────────────────────────

class FallbackChain:
    """
    Try models in order, falling back to the next on failure.

    Usage:
        chain = FallbackChain([gpt4_llm, groq_llm, local_llm])
        result = chain.invoke(messages)
    """

    def __init__(self, models: list, names: Optional[List[str]] = None):
        self.models = models
        self.names = names or [f"model_{i}" for i in range(len(models))]

    def invoke(self, *args, **kwargs) -> Any:
        """Try each model in order until one succeeds."""
        last_error = None

        for model, name in zip(self.models, self.names):
            try:
                result = model.invoke(*args, **kwargs)
                log.info("Fallback chain succeeded", model=name)
                return result
            except Exception as e:
                last_error = e
                log.warning("Fallback model failed, trying next", model=name, error=str(e))

        log.error("All fallback models failed")
        raise last_error


# ─────────────────────────────────────────────
# Idempotency Cache
# ─────────────────────────────────────────────

class IdempotencyCache:
    """
    Ensures same request → same result via input hashing and caching.

    Usage:
        cache = IdempotencyCache(ttl=3600)
        result = cache.get_or_execute(request_data, callable)
    """

    def __init__(self, ttl: int = 3600, max_entries: int = 1000):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl
        self.max_entries = max_entries

    def _hash_input(self, data: Any) -> str:
        """Create deterministic hash of input data."""
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def get_or_execute(self, request_data: Any, func: Callable, *args, **kwargs) -> Any:
        """Return cached result or execute and cache."""
        key = self._hash_input(request_data)

        # Check cache
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["timestamp"] < self.ttl:
                log.info("Idempotency cache hit", key=key[:12])
                return entry["result"]
            else:
                del self._cache[key]

        # Evict oldest if full
        if len(self._cache) >= self.max_entries:
            oldest_key = min(self._cache, key=lambda k: self._cache[k]["timestamp"])
            del self._cache[oldest_key]

        # Execute and cache
        result = func(*args, **kwargs)
        self._cache[key] = {"result": result, "timestamp": time.time()}
        log.info("Idempotency cache stored", key=key[:12])
        return result

    def invalidate(self, request_data: Any) -> None:
        """Remove a specific entry from cache."""
        key = self._hash_input(request_data)
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear entire cache."""
        self._cache.clear()

    def size(self) -> int:
        return len(self._cache)
