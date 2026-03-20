"""
FastAPI Application Entry Point — AgenticAI Decision & Research Platform

Run with: uvicorn main:app --reload --port 8000
"""

import time

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from research_and_analyst.database.db_config import create_tables
from research_and_analyst.logger import GLOBAL_LOGGER as log

# ─────────────────────────────────────────────
# App Initialisation
# ─────────────────────────────────────────────

app = FastAPI(
    title="AgenticAI — Decision & Research Platform",
    description=(
        "Multi-step decision system with autonomous research, "
        "iterative refinement, and enterprise report generation. "
        "Powered by LangGraph."
    ),
    version="2.0.0",
)

# CORS — allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Request Logging & Metrics Middleware
# ─────────────────────────────────────────────

@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    """Track latency, log requests, and collect metrics."""
    start = time.time()
    response = await call_next(request)
    latency = time.time() - start

    # Structured request log
    log.info(
        "HTTP request",
        method=request.method,
        path=str(request.url.path),
        status=response.status_code,
        latency=round(latency, 4),
    )

    # Collect metrics
    try:
        from research_and_analyst.observability.tracing import GLOBAL_METRICS
        GLOBAL_METRICS.increment("http_requests_total", labels={"method": request.method, "path": request.url.path})
        GLOBAL_METRICS.observe("http_request_latency_seconds", latency, labels={"path": request.url.path})
        if response.status_code >= 400:
            GLOBAL_METRICS.increment("http_errors_total", labels={"status": str(response.status_code)})
    except Exception:
        pass  # Metrics collection should never break requests

    response.headers["X-Process-Time"] = str(round(latency, 4))
    return response


# ─────────────────────────────────────────────
# Startup Event
# ─────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Create database tables and initialize services on startup."""
    log.info("Starting AgenticAI API server v2.0.0")
    create_tables()
    log.info("Database tables verified")

    # Log available services
    log.info("Services: Research Reports, Decision Analysis, Async Jobs, WebSocket Progress")


# ─────────────────────────────────────────────
# API Routes
# ─────────────────────────────────────────────

from research_and_analyst.api.routes import api_router  # noqa: E402

app.include_router(api_router, prefix="/api")


# ─────────────────────────────────────────────
# WebSocket — Real-time Task Progress
# ─────────────────────────────────────────────

@app.websocket("/ws/task/{task_id}")
async def websocket_task_progress(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint for real-time task progress.

    Clients connect with: ws://host:8000/ws/task/{task_id}
    Receives JSON messages: {type, task_id, step, progress_pct, status}
    """
    from research_and_analyst.job_queue.websocket_manager import ws_manager

    await ws_manager.connect(websocket, task_id)
    try:
        while True:
            # Keep connection alive; client can send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type": "pong"}')
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, task_id)


# ─────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check with system status."""
    try:
        from research_and_analyst.observability.tracing import GLOBAL_METRICS
        metrics = GLOBAL_METRICS.get_all_metrics()
        request_count = sum(
            v for k, v in metrics.get("counters", {}).items()
            if "http_requests_total" in k
        )
    except Exception:
        request_count = 0

    return {
        "status": "healthy",
        "service": "AgenticAI",
        "version": "2.0.0",
        "total_requests_served": request_count,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
