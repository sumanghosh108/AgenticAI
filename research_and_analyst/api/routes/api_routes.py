"""
API Routes — REST endpoints for the report generation pipeline.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from research_and_analyst.api.services.report_service import ReportService
from research_and_analyst.database.db_config import (
    SessionLocal, User, hash_password, verify_password,
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


# ─────────────────────────────────────────────
# Auth Routes
# ─────────────────────────────────────────────


@api_router.post("/signup")
async def signup(req: SignupRequest):
    db = SessionLocal()
    try:
        # Check if email already exists → redirect to login
        email_user = db.query(User).filter(User.email == req.email).first()
        if email_user:
            return {
                "success": False,
                "email_exists": True,
                "message": "This email is already registered. Please login instead.",
            }

        # Check if username is taken
        username_user = db.query(User).filter(User.username == req.username).first()
        if username_user:
            return {
                "success": False,
                "username_taken": True,
                "message": "Username is already taken. Please choose a different username.",
            }

        new_user = User(
            username=req.username,
            email=req.email,
            password=hash_password(req.password),
            age=req.age,
            gender=req.gender,
        )
        db.add(new_user)
        db.commit()
        log.info("New user registered", username=req.username, email=req.email)
        return {"success": True, "message": "Signup successful"}
    except Exception as e:
        db.rollback()
        log.error("Signup failed", error=str(e))
        return {"success": False, "message": f"Signup failed: {str(e)}"}
    finally:
        db.close()


@api_router.post("/login")
async def login(req: LoginRequest):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == req.username).first()
        if user and verify_password(req.password, user.password):
            log.info("User logged in", username=req.username)
            return {"success": True, "message": "Login successful", "username": req.username}
        return {"success": False, "message": "Invalid username or password"}
    except Exception as e:
        log.error("Login failed", error=str(e))
        return {"success": False, "message": f"Login failed: {str(e)}"}
    finally:
        db.close()


# ─────────────────────────────────────────────
# Report Routes
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
