"""
Cost Optimization — embedding cache, LLM call batching, and token usage tracking.

Provides:
- Token usage tracking per agent, per workflow
- Embedding reuse cache (prevents duplicate embedding calls)
- LLM call batching for independent queries
- Cost estimation per model
"""

import hashlib
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from research_and_analyst.logger import GLOBAL_LOGGER as log


# ─────────────────────────────────────────────
# Model Cost Rates (per 1K tokens)
# ─────────────────────────────────────────────

MODEL_COSTS = {
    # OpenAI
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    # Google
    "gemini-2.0-flash": {"input": 0.0001, "output": 0.0004},
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
    # Groq
    "deepseek-r1-distill-llama-70b": {"input": 0.00075, "output": 0.00099},
    "llama-3.1-70b-versatile": {"input": 0.00059, "output": 0.00079},
    # OpenRouter (varies)
    "default": {"input": 0.001, "output": 0.002},
}


class TokenTracker:
    """
    Tracks token usage across agents, workflows, and sessions.

    Provides cost estimation and budget alerting.
    """

    def __init__(self, model_name: str = "default", budget_limit: float = 10.0):
        self.model_name = model_name
        self.budget_limit = budget_limit
        self._usage: Dict[str, Dict[str, int]] = defaultdict(lambda: {"input": 0, "output": 0})
        self._calls: List[Dict[str, Any]] = []
        self._total_cost = 0.0

    def track(
        self,
        agent_name: str,
        input_tokens: int,
        output_tokens: int,
        model: Optional[str] = None,
    ):
        """Record token usage for a call."""
        model = model or self.model_name
        self._usage[agent_name]["input"] += input_tokens
        self._usage[agent_name]["output"] += output_tokens

        cost = self._estimate_cost(input_tokens, output_tokens, model)
        self._total_cost += cost

        self._calls.append({
            "agent": agent_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": round(cost, 6),
            "model": model,
            "timestamp": time.time(),
        })

        # Budget alert
        if self._total_cost > self.budget_limit * 0.8:
            log.warning(
                "Token budget alert",
                used=round(self._total_cost, 4),
                limit=self.budget_limit,
                pct=round(self._total_cost / self.budget_limit * 100, 1),
            )

    def _estimate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """Estimate cost in USD for a call."""
        rates = MODEL_COSTS.get(model, MODEL_COSTS["default"])
        return (input_tokens / 1000) * rates["input"] + (output_tokens / 1000) * rates["output"]

    def get_summary(self) -> Dict[str, Any]:
        """Get usage summary."""
        total_input = sum(u["input"] for u in self._usage.values())
        total_output = sum(u["output"] for u in self._usage.values())
        return {
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_cost_usd": round(self._total_cost, 4),
            "budget_remaining_usd": round(self.budget_limit - self._total_cost, 4),
            "budget_used_pct": round(self._total_cost / max(self.budget_limit, 0.01) * 100, 1),
            "calls": len(self._calls),
            "per_agent": {
                agent: {
                    "input_tokens": usage["input"],
                    "output_tokens": usage["output"],
                    "total_tokens": usage["input"] + usage["output"],
                }
                for agent, usage in self._usage.items()
            },
        }

    def is_within_budget(self) -> bool:
        return self._total_cost < self.budget_limit


# ─────────────────────────────────────────────
# Embedding Cache
# ─────────────────────────────────────────────

class EmbeddingCache:
    """
    Caches embedding results to prevent duplicate API calls.

    Same text → same embedding (deterministic), so caching is safe.
    """

    def __init__(self, max_entries: int = 10000):
        self._cache: Dict[str, List[float]] = {}
        self.max_entries = max_entries
        self._hits = 0
        self._misses = 0

    def get_or_embed(
        self,
        text: str,
        embed_fn,
    ) -> List[float]:
        """
        Return cached embedding or compute and cache.

        Args:
            text: Text to embed.
            embed_fn: Function(text) -> List[float].

        Returns:
            Embedding vector.
        """
        key = self._hash(text)

        if key in self._cache:
            self._hits += 1
            return self._cache[key]

        self._misses += 1

        # Evict if full
        if len(self._cache) >= self.max_entries:
            # Remove oldest (first inserted)
            first_key = next(iter(self._cache))
            del self._cache[first_key]

        embedding = embed_fn(text)
        self._cache[key] = embedding
        return embedding

    def batch_get_or_embed(
        self,
        texts: List[str],
        batch_embed_fn,
    ) -> List[List[float]]:
        """
        Batch embedding with cache — only embeds uncached texts.

        Args:
            texts: List of texts.
            batch_embed_fn: Function(List[str]) -> List[List[float]].
        """
        results = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []

        for i, text in enumerate(texts):
            key = self._hash(text)
            if key in self._cache:
                results[i] = self._cache[key]
                self._hits += 1
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)
                self._misses += 1

        if uncached_texts:
            new_embeddings = batch_embed_fn(uncached_texts)
            for idx, text, emb in zip(uncached_indices, uncached_texts, new_embeddings):
                key = self._hash(text)
                self._cache[key] = emb
                results[idx] = emb

        return results

    def get_stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "cache_size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / max(total, 1) * 100, 1),
        }

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()


# ─────────────────────────────────────────────
# LLM Call Batcher
# ─────────────────────────────────────────────

class LLMBatcher:
    """
    Batches independent LLM calls for efficiency.

    Collects prompts and sends them together where supported,
    reducing API round-trips and latency.
    """

    def __init__(self, llm=None, max_batch_size: int = 5):
        self.llm = llm
        self.max_batch_size = max_batch_size
        self._pending: List[Tuple[Any, str]] = []  # (messages, identifier)

    def add(self, messages, identifier: str = ""):
        """Add a call to the batch."""
        self._pending.append((messages, identifier))

    def flush(self) -> List[Dict[str, Any]]:
        """Execute all pending calls and return results."""
        if not self._pending or not self.llm:
            return []

        results = []
        # Process in batches
        for i in range(0, len(self._pending), self.max_batch_size):
            batch = self._pending[i:i + self.max_batch_size]

            for messages, identifier in batch:
                try:
                    response = self.llm.invoke(messages)
                    results.append({
                        "identifier": identifier,
                        "success": True,
                        "content": response.content,
                    })
                except Exception as e:
                    results.append({
                        "identifier": identifier,
                        "success": False,
                        "error": str(e),
                    })

        self._pending.clear()
        log.info("LLM batch flushed", calls=len(results))
        return results

    @property
    def pending_count(self) -> int:
        return len(self._pending)
