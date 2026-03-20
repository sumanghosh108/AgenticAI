"""
API Routes — REST endpoints for the report generation pipeline.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from research_and_analyst.api.services.report_service import ReportService
from research_and_analyst.database.db_config import (
    hash_password, verify_password,
    get_user_by_username, get_user_by_email, create_user,
    save_user_report, get_user_reports,
)
from research_and_analyst.auth.google_oauth import (
    is_google_oauth_configured, exchange_code_for_user,
    get_google_auth_url,
)
from research_and_analyst.logger import GLOBAL_LOGGER as log


api_router = APIRouter()

# ─────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────


class SignupRequest(BaseModel):
    username: str = Field(..., min_length=3, description="Username")
    email: str = Field(..., description="Email address")
    password: str = Field(..., min_length=4, description="Password")
    age: int = Field(None, description="Age")
    gender: str = Field(None, description="Gender")


class LoginRequest(BaseModel):
    username: str
    password: str


class ReportRequest(BaseModel):
    topic: str = Field(..., description="Research topic")
    max_analysts: int = Field(3, description="Number of analyst personas")


class FeedbackRequest(BaseModel):
    thread_id: str
    feedback: str


class SaveReportRequest(BaseModel):
    user_name: str = Field(..., description="Username of the report owner")
    research_topic: str = Field(..., description="Research topic")
    research_domain: str = Field("", description="Research domain")
    document: str = Field("", description="Report document content")


# ─────────────────────────────────────────────
# Auth Routes (Supabase-backed)
# ─────────────────────────────────────────────


@api_router.post("/signup")
async def signup(req: SignupRequest):
    try:
        # Check if email already exists
        if get_user_by_email(req.email):
            return {
                "success": False,
                "email_exists": True,
                "message": "This email is already registered. Please login instead.",
            }

        # Check if username is taken
        if get_user_by_username(req.username):
            return {
                "success": False,
                "username_taken": True,
                "message": "Username is already taken. Please choose a different username.",
            }

        create_user(
            username=req.username,
            email=req.email,
            password_hash=hash_password(req.password),
            age=req.age,
            gender=req.gender,
        )
        log.info("New user registered", username=req.username, email=req.email)
        return {"success": True, "message": "Signup successful"}
    except Exception as e:
        log.error("Signup failed", error=str(e))
        return {"success": False, "message": f"Signup failed: {str(e)}"}


@api_router.post("/login")
async def login(req: LoginRequest):
    try:
        user = get_user_by_username(req.username)
        if user and verify_password(req.password, user["password"]):
            log.info("User logged in", username=req.username)
            return {"success": True, "message": "Login successful", "username": req.username}
        return {"success": False, "message": "Invalid username or password"}
    except Exception as e:
        log.error("Login failed", error=str(e))
        return {"success": False, "message": f"Login failed: {str(e)}"}

# ─────────────────────────────────────────────
# Google OAuth (Supabase-backed)
# ─────────────────────────────────────────────


class GoogleAuthRequest(BaseModel):
    code: str = Field(..., description="Authorization code from Google OAuth redirect")


@api_router.get("/google_auth_url")
async def get_google_auth_url_endpoint():
    if not is_google_oauth_configured():
        return {"success": False, "message": "Google OAuth is not configured on the server."}
    return {"success": True, "url": get_google_auth_url()}


@api_router.post("/google_auth")
async def google_auth(req: GoogleAuthRequest):
    """Exchange Google OAuth code for user info, auto-create or login."""
    if not is_google_oauth_configured():
        return {"success": False, "message": "Google OAuth is not configured on the server."}

    try:
        google_user = exchange_code_for_user(req.code)
        email = google_user.get("email")
        name = google_user.get("name", "")

        if not email:
            return {"success": False, "message": "Could not retrieve email from Google."}

        # Check if user exists by email
        user = get_user_by_email(email)

        if user:
            log.info("Google login", username=user["username"], email=email)
            return {"success": True, "message": "Login successful", "username": user["username"]}

        # New user → auto-create
        base_username = name.replace(" ", "_").lower() if name else email.split("@")[0]
        username = base_username
        counter = 1
        while get_user_by_username(username):
            username = f"{base_username}_{counter}"
            counter += 1

        create_user(
            username=username,
            email=email,
            password_hash=hash_password(f"google_oauth_{google_user.get('google_id', '')}"),
        )
        log.info("Google signup", username=username, email=email)
        return {"success": True, "message": "Account created via Google", "username": username}

    except Exception as e:
        log.error("Google auth failed", error=str(e))
        return {"success": False, "message": f"Google authentication failed: {str(e)}"}


# ─────────────────────────────────────────────
# User Report Storage (Supabase)
# ─────────────────────────────────────────────


@api_router.post("/save_report")
async def save_report(req: SaveReportRequest):
    """Save a generated report to the user_report table."""
    try:
        result = save_user_report(
            user_name=req.user_name,
            research_topic=req.research_topic,
            research_domain=req.research_domain,
            document=req.document,
        )
        log.info("Report saved", user=req.user_name, topic=req.research_topic)
        return {"success": True, "message": "Report saved", "report": result}
    except Exception as e:
        log.error("Save report failed", error=str(e))
        return {"success": False, "message": f"Failed to save report: {str(e)}"}


@api_router.get("/user_reports/{username}")
async def fetch_user_reports(username: str):
    """Fetch all reports for a given user."""
    try:
        reports = get_user_reports(username)
        return {"success": True, "reports": reports}
    except Exception as e:
        log.error("Fetch reports failed", error=str(e))
        return {"success": False, "message": f"Failed to fetch reports: {str(e)}"}


# ─────────────────────────────────────────────
# Report Routes (legacy generation)
# ─────────────────────────────────────────────

_service = None


def _get_service() -> ReportService:
    global _service
    if _service is None:
        _service = ReportService()
    return _service


@api_router.post("/generate_report")
async def generate_report(req: ReportRequest):
    try:
        service = _get_service()
        result = service.start_report_generation(req.topic, req.max_analysts)
        return {"success": True, **result}
    except Exception as e:
        log.error("Report generation failed", error=str(e))
        return {"success": False, "message": str(e)}


@api_router.post("/submit_feedback")
async def submit_feedback(req: FeedbackRequest):
    try:
        service = _get_service()
        result = service.submit_feedback(req.thread_id, req.feedback)
        return {"success": True, **result}
    except Exception as e:
        log.error("Feedback submission failed", error=str(e))
        return {"success": False, "message": str(e)}


@api_router.get("/report_status/{thread_id}")
async def report_status(thread_id: str):
    try:
        service = _get_service()
        result = service.get_report_status(thread_id)
        return {"success": True, **result}
    except Exception as e:
        log.error("Status check failed", error=str(e))
        return {"success": False, "message": str(e)}


@api_router.get("/download/{file_name}")
async def download_report(file_name: str):
    service = _get_service()
    return service.download_file(file_name)


# ─────────────────────────────────────────────
# Decision Workflow Routes
# ─────────────────────────────────────────────


class DecisionRequest(BaseModel):
    query: str = Field(..., description="Analysis query (e.g. 'Analyze AI startup market')")
    domain: str = Field("general", description="Domain: finance, healthcare, general")
    max_iterations: int = Field(3, ge=1, le=5, description="Max refinement iterations")


class FeedbackSubmission(BaseModel):
    task_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: str = ""


# ─── Singletons ──────────────────────────────

_decision_service = None
_task_queue = None
_rate_limiter = None
_input_validator = None
_feedback_store = None


def _get_decision_service():
    global _decision_service
    if _decision_service is None:
        from research_and_analyst.workflows.decision_workflow import DecisionWorkflowBuilder
        _decision_service = DecisionWorkflowBuilder()
        _decision_service.build()
    return _decision_service


def _get_task_queue():
    global _task_queue
    if _task_queue is None:
        from research_and_analyst.job_queue.task_queue import TaskQueue
        _task_queue = TaskQueue(max_workers=3)
    return _task_queue


def _get_rate_limiter():
    global _rate_limiter
    if _rate_limiter is None:
        from research_and_analyst.security.protection import RateLimiter
        _rate_limiter = RateLimiter(max_requests=30, window_seconds=60, burst_limit=5)
    return _rate_limiter


def _get_input_validator():
    global _input_validator
    if _input_validator is None:
        from research_and_analyst.security.protection import InputValidator
        _input_validator = InputValidator()
    return _input_validator


def _get_feedback_store():
    global _feedback_store
    if _feedback_store is None:
        from research_and_analyst.evaluation.quality_tests import FeedbackStore
        _feedback_store = FeedbackStore()
    return _feedback_store


# ─── Synchronous Analysis (blocking) ────────


@api_router.post("/decision/analyze")
async def run_decision_analysis(req: DecisionRequest):
    """Run the full multi-step decision workflow (synchronous)."""
    # Rate limiting
    rate_check = _get_rate_limiter().check(req.query[:50])
    if not rate_check["allowed"]:
        return {
            "success": False,
            "message": f"Rate limit exceeded. Retry after {rate_check['retry_after']}s",
            "retry_after": rate_check["retry_after"],
        }

    # Input validation + prompt injection check
    validation = _get_input_validator().validate_query(req.query)
    if not validation["valid"]:
        return {"success": False, "message": "Invalid input", "errors": validation["errors"]}

    try:
        service = _get_decision_service()
        result = service.run(
            query=validation["sanitized_query"],
            domain=req.domain,
            max_iterations=req.max_iterations,
        )
        return {"success": True, **result}
    except Exception as e:
        log.error("Decision analysis failed", error=str(e))
        return {"success": False, "message": str(e)}


# ─── Async Analysis (queue-based) ───────────


@api_router.post("/decision/analyze/async")
async def run_decision_async(req: DecisionRequest):
    """Submit analysis for async execution. Returns task_id for polling."""
    # Rate limiting
    rate_check = _get_rate_limiter().check(req.query[:50])
    if not rate_check["allowed"]:
        return {
            "success": False,
            "message": f"Rate limit exceeded. Retry after {rate_check['retry_after']}s",
        }

    # Input validation
    validation = _get_input_validator().validate_query(req.query)
    if not validation["valid"]:
        return {"success": False, "message": "Invalid input", "errors": validation["errors"]}

    try:
        service = _get_decision_service()
        queue = _get_task_queue()

        task_id = queue.submit(
            func=service.run,
            query=validation["sanitized_query"],
            domain=req.domain,
            max_iterations=req.max_iterations,
        )

        return {
            "success": True,
            "task_id": task_id,
            "message": "Analysis submitted. Poll /decision/status/{task_id} for progress.",
        }
    except Exception as e:
        log.error("Async submission failed", error=str(e))
        return {"success": False, "message": str(e)}


@api_router.get("/decision/status/{task_id}")
async def get_task_status(task_id: str):
    """Poll task progress and status."""
    queue = _get_task_queue()
    status = queue.get_status(task_id)
    if not status:
        return {"success": False, "message": "Task not found"}
    return {"success": True, **status}


@api_router.get("/decision/result/{task_id}")
async def get_task_result(task_id: str):
    """Get completed task result."""
    queue = _get_task_queue()
    result = queue.get_result(task_id)
    if not result:
        return {"success": False, "message": "Task not found"}
    return {"success": True, **result}


@api_router.post("/decision/cancel/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a queued or running task."""
    queue = _get_task_queue()
    cancelled = queue.cancel(task_id)
    return {"success": cancelled, "message": "Cancelled" if cancelled else "Cannot cancel"}


@api_router.get("/decision/tasks")
async def list_tasks():
    """List all tasks."""
    queue = _get_task_queue()
    return {"success": True, "tasks": queue.list_tasks()}


# ─── Feedback ────────────────────────────────


@api_router.post("/decision/feedback")
async def submit_quality_feedback(req: FeedbackSubmission):
    """Submit human feedback on a task output."""
    store = _get_feedback_store()
    feedback_id = store.submit(
        task_id=req.task_id,
        rating=req.rating,
        comment=req.comment,
    )
    return {"success": True, "feedback_id": feedback_id}


@api_router.get("/decision/feedback/stats")
async def get_feedback_stats():
    """Get aggregate feedback statistics."""
    store = _get_feedback_store()
    return {"success": True, **store.get_stats()}


# ─── Domain Packs ────────────────────────────


@api_router.get("/decision/domains")
async def list_domains():
    """List available domain packs."""
    from research_and_analyst.domain_packs.finance_pack import FinanceDomainPack
    from research_and_analyst.domain_packs.healthcare_pack import HealthcareDomainPack

    packs = {
        "finance": FinanceDomainPack().get_config().model_dump(),
        "healthcare": HealthcareDomainPack().get_config().model_dump(),
        "general": {
            "domain": "general",
            "display_name": "General Analysis",
            "tools": ["web_search", "web_scraper", "data_analyzer"],
            "metrics": ["feasibility", "impact", "risk"],
            "scoring_dimensions": ["feasibility", "impact_potential", "risk_level", "data_quality", "strategic_alignment"],
        },
    }
    return {"success": True, "domains": packs}


# ─── Observability & Metrics ─────────────────


@api_router.get("/decision/metrics")
async def get_system_metrics():
    """Get system observability metrics."""
    from research_and_analyst.observability.tracing import GLOBAL_METRICS, GLOBAL_AUDIT

    metrics = GLOBAL_METRICS.get_all_metrics()
    audit_count = GLOBAL_AUDIT.count()

    # Add task queue stats
    queue = _get_task_queue()
    tasks = queue.list_tasks(limit=100)
    task_stats = {
        "total_tasks": len(tasks),
        "by_status": {},
    }
    for t in tasks:
        status = t["status"]
        task_stats["by_status"][status] = task_stats["by_status"].get(status, 0) + 1

    return {
        "success": True,
        "metrics": metrics,
        "audit_entries": audit_count,
        "task_stats": task_stats,
        "feedback_stats": _get_feedback_store().get_stats(),
    }


@api_router.get("/decision/prompts")
async def list_prompt_versions():
    """List available prompt versions for A/B testing."""
    from research_and_analyst.reliability.prompt_manager import PromptManager
    pm = PromptManager()
    versions = pm.list_versions()
    result = {}
    for v in versions:
        result[v] = pm.list_prompts(v)
    return {"success": True, "versions": result}
