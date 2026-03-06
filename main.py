"""
FastAPI Application Entry Point — Autonomous Research Report Generator

Run with: uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from research_and_analyst.database.db_config import create_tables
from research_and_analyst.logger import GLOBAL_LOGGER as log

# ─────────────────────────────────────────────
# App Initialisation
# ─────────────────────────────────────────────

app = FastAPI(
    title="AgenticAI — Research Report Generator",
    description="Autonomous research report generation powered by LangGraph",
    version="0.1.0",
)

# CORS — allow Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Startup Event
# ─────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Create database tables on startup."""
    log.info("Starting AgenticAI API server")
    create_tables()
    log.info("Database tables verified")


# ─────────────────────────────────────────────
# API Routes
# ─────────────────────────────────────────────

from research_and_analyst.api.routes import api_router  # noqa: E402

app.include_router(api_router, prefix="/api")


# ─────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "AgenticAI"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
