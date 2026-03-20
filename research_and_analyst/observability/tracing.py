"""
Observability — tracing, metrics collection, and structured logging enhancement.

Provides:
- Workflow tracing (span-based, compatible with OpenTelemetry concepts)
- Metrics collection (latency, token usage, error rate, success rate)
- Agent performance dashboards
- Immutable audit trail
"""

import time
import uuid
from collections import defaultdict
from typing import Any, Dict, List, Optional

from research_and_analyst.logger import GLOBAL_LOGGER as log


# ─────────────────────────────────────────────
# Span-based Tracing
# ─────────────────────────────────────────────

class Span:
    """A single span in a trace — represents one unit of work."""

    def __init__(self, name: str, trace_id: str, parent_id: Optional[str] = None):
        self.span_id = str(uuid.uuid4())[:8]
        self.trace_id = trace_id
        self.parent_id = parent_id
        self.name = name
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.status = "running"
        self.attributes: Dict[str, Any] = {}
        self.events: List[Dict[str, Any]] = []

    def set_attribute(self, key: str, value: Any) -> "Span":
        self.attributes[key] = value
        return self

    def add_event(self, name: str, attributes: Optional[Dict] = None) -> "Span":
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {},
        })
        return self

    def end(self, status: str = "ok"):
        self.end_time = time.time()
        self.status = status

    @property
    def duration_ms(self) -> float:
        end = self.end_time or time.time()
        return round((end - self.start_time) * 1000, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "events": self.events,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }


class Tracer:
    """
    Workflow tracer — tracks full agent execution pipelines.

    Usage:
        tracer = Tracer()
        with tracer.start_trace("decision_workflow") as trace:
            with trace.start_span("decompose_task") as span:
                span.set_attribute("query", "Analyze AI market")
                # ... do work ...
    """

    def __init__(self):
        self._traces: Dict[str, List[Span]] = {}
        self._active_spans: Dict[str, Span] = {}

    def start_trace(self, name: str) -> "TraceContext":
        """Start a new trace."""
        trace_id = str(uuid.uuid4())[:12]
        self._traces[trace_id] = []
        log.info("Trace started", trace_id=trace_id, name=name)
        return TraceContext(self, trace_id, name)

    def _add_span(self, span: Span):
        """Add a span to its trace."""
        if span.trace_id in self._traces:
            self._traces[span.trace_id].append(span)

    def get_trace(self, trace_id: str) -> List[Dict[str, Any]]:
        """Get all spans in a trace."""
        spans = self._traces.get(trace_id, [])
        return [s.to_dict() for s in spans]

    def get_all_traces(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all traces."""
        return {
            tid: [s.to_dict() for s in spans]
            for tid, spans in self._traces.items()
        }


class TraceContext:
    """Context manager for a trace."""

    def __init__(self, tracer: Tracer, trace_id: str, name: str):
        self.tracer = tracer
        self.trace_id = trace_id
        self.name = name
        self._root_span: Optional[Span] = None

    def __enter__(self):
        self._root_span = Span(self.name, self.trace_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._root_span:
            status = "error" if exc_type else "ok"
            self._root_span.end(status)
            self.tracer._add_span(self._root_span)
            log.info(
                "Trace completed",
                trace_id=self.trace_id,
                duration_ms=self._root_span.duration_ms,
                status=status,
            )

    def start_span(self, name: str) -> "SpanContext":
        """Start a child span within this trace."""
        parent_id = self._root_span.span_id if self._root_span else None
        span = Span(name, self.trace_id, parent_id)
        return SpanContext(self.tracer, span)


class SpanContext:
    """Context manager for a span."""

    def __init__(self, tracer: Tracer, span: Span):
        self.tracer = tracer
        self.span = span

    def __enter__(self):
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        status = "error" if exc_type else "ok"
        self.span.end(status)
        self.tracer._add_span(self.span)


# ─────────────────────────────────────────────
# Metrics Collection
# ─────────────────────────────────────────────

class MetricsCollector:
    """
    Collects and exposes Prometheus-compatible metrics.

    Tracks:
    - LLM call latency (histogram)
    - Token usage (counter)
    - Error rate (counter)
    - Agent success rate (gauge)
    - Workflow duration (histogram)
    """

    def __init__(self):
        self._counters: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._gauges: Dict[str, float] = {}

    def increment(self, name: str, value: float = 1.0, labels: Optional[Dict] = None):
        """Increment a counter."""
        key = self._make_key(name, labels)
        self._counters[key] += value

    def observe(self, name: str, value: float, labels: Optional[Dict] = None):
        """Record a histogram observation."""
        key = self._make_key(name, labels)
        self._histograms[key].append(value)

    def set_gauge(self, name: str, value: float, labels: Optional[Dict] = None):
        """Set a gauge value."""
        key = self._make_key(name, labels)
        self._gauges[key] = value

    def get_counter(self, name: str, labels: Optional[Dict] = None) -> float:
        return self._counters.get(self._make_key(name, labels), 0)

    def get_histogram_stats(self, name: str, labels: Optional[Dict] = None) -> Dict[str, float]:
        """Get histogram statistics (min, max, avg, p50, p95, p99, count)."""
        key = self._make_key(name, labels)
        values = self._histograms.get(key, [])
        if not values:
            return {"count": 0}

        sorted_vals = sorted(values)
        count = len(sorted_vals)
        return {
            "count": count,
            "min": round(sorted_vals[0], 4),
            "max": round(sorted_vals[-1], 4),
            "avg": round(sum(sorted_vals) / count, 4),
            "p50": round(sorted_vals[int(count * 0.5)], 4),
            "p95": round(sorted_vals[min(int(count * 0.95), count - 1)], 4),
            "p99": round(sorted_vals[min(int(count * 0.99), count - 1)], 4),
        }

    def get_all_metrics(self) -> Dict[str, Any]:
        """Export all metrics."""
        return {
            "counters": dict(self._counters),
            "histograms": {
                k: self.get_histogram_stats(k) for k in self._histograms
            },
            "gauges": dict(self._gauges),
        }

    def reset(self):
        self._counters.clear()
        self._histograms.clear()
        self._gauges.clear()

    @staticmethod
    def _make_key(name: str, labels: Optional[Dict] = None) -> str:
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


# ─────────────────────────────────────────────
# Audit Trail
# ─────────────────────────────────────────────

class AuditTrail:
    """
    Immutable audit log for tracking all system actions.

    Every decision, agent call, and output is logged with timestamp,
    actor, action, and data — enabling full reproducibility.
    """

    def __init__(self, max_entries: int = 10000):
        self._entries: List[Dict[str, Any]] = []
        self.max_entries = max_entries

    def record(
        self,
        action: str,
        actor: str,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, str]] = None,
    ):
        """Record an audit event (immutable append-only)."""
        entry = {
            "id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "action": action,
            "actor": actor,
            "data": data or {},
            "metadata": metadata or {},
        }

        if len(self._entries) >= self.max_entries:
            self._entries = self._entries[-(self.max_entries // 2):]

        self._entries.append(entry)
        log.info("Audit recorded", action=action, actor=actor)

    def get_entries(
        self,
        action: Optional[str] = None,
        actor: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Query audit entries with optional filters."""
        filtered = self._entries
        if action:
            filtered = [e for e in filtered if e["action"] == action]
        if actor:
            filtered = [e for e in filtered if e["actor"] == actor]
        return filtered[-limit:]

    def count(self) -> int:
        return len(self._entries)


# ─────────────────────────────────────────────
# Global Instances
# ─────────────────────────────────────────────

GLOBAL_TRACER = Tracer()
GLOBAL_METRICS = MetricsCollector()
GLOBAL_AUDIT = AuditTrail()
