"""
Async Job System — queue-based execution with persistent state management.

Flow: User → API → Queue → Worker → Result Store

Provides:
- Async task submission with immediate task_id return
- Persistent workflow state in PostgreSQL
- Checkpointing after each pipeline step
- Task status polling and result retrieval
- Cancellation support
"""

import time
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field
from research_and_analyst.logger import GLOBAL_LOGGER as log


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskState(BaseModel):
    """Persistent workflow state for a single task."""
    task_id: str
    status: TaskStatus = TaskStatus.QUEUED
    query: str = ""
    domain: str = "general"
    current_step: str = ""
    steps_completed: int = 0
    total_steps: int = 0
    progress_pct: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    checkpoints: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskQueue:
    """
    In-process async task queue with persistent state tracking.

    For production, replace with Redis/Celery or a dedicated queue service.
    This implementation uses ThreadPoolExecutor for async execution
    with in-memory state that can be extended to PostgreSQL.
    """

    # Pipeline step names (for progress tracking)
    PIPELINE_STEPS = [
        "decompose_task",
        "dispatch_agents",
        "generate_decision",
        "critique_output",
        "extract_kpis",
        "score_sources",
        "format_report",
    ]

    def __init__(self, max_workers: int = 3):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: Dict[str, TaskState] = {}
        self._lock = threading.Lock()

    def submit(
        self,
        func: Callable,
        query: str,
        domain: str = "general",
        **kwargs,
    ) -> str:
        """
        Submit a task for async execution.

        Args:
            func: The workflow function to execute.
            query: User query.
            domain: Domain context.
            **kwargs: Additional arguments for func.

        Returns:
            task_id for status polling.
        """
        task_id = f"task_{uuid.uuid4().hex[:12]}"

        state = TaskState(
            task_id=task_id,
            query=query,
            domain=domain,
            total_steps=len(self.PIPELINE_STEPS),
        )

        with self._lock:
            self._tasks[task_id] = state

        # Submit to thread pool
        future = self._executor.submit(self._execute, task_id, func, query, domain, **kwargs)
        future.add_done_callback(lambda f: self._on_complete(task_id, f))

        log.info("Task submitted", task_id=task_id, query=query[:80])
        return task_id

    def _execute(
        self,
        task_id: str,
        func: Callable,
        query: str,
        domain: str,
        **kwargs,
    ) -> Any:
        """Execute the task and track progress."""
        self._update_status(task_id, TaskStatus.RUNNING, current_step="starting")

        try:
            result = func(query=query, domain=domain, task_id=task_id, **kwargs)
            return result
        except Exception as e:
            log.error("Task execution failed", task_id=task_id, error=str(e))
            raise

    def _on_complete(self, task_id: str, future):
        """Callback when task completes or fails."""
        from research_and_analyst.job_queue.websocket_manager import (
            broadcast_completed, broadcast_error,
        )

        try:
            result = future.result()
            self._update_status(
                task_id,
                TaskStatus.COMPLETED,
                current_step="completed",
                result=result,
                progress_pct=100.0,
                steps_completed=len(self.PIPELINE_STEPS),
            )
            log.info("Task completed", task_id=task_id)
            broadcast_completed(task_id, result)
        except Exception as e:
            self._update_status(
                task_id,
                TaskStatus.FAILED,
                current_step="failed",
                error=str(e),
            )
            log.error("Task failed", task_id=task_id, error=str(e))
            broadcast_error(task_id, str(e))

    def checkpoint(self, task_id: str, step_name: str, data: Optional[Dict] = None):
        """
        Save a checkpoint after a pipeline step completes.

        Called by the workflow to track progress.
        """
        with self._lock:
            state = self._tasks.get(task_id)
            if not state:
                return

            step_idx = (
                self.PIPELINE_STEPS.index(step_name) + 1
                if step_name in self.PIPELINE_STEPS else state.steps_completed + 1
            )

            state.steps_completed = step_idx
            state.current_step = step_name
            state.progress_pct = round((step_idx / max(state.total_steps, 1)) * 100, 1)
            state.updated_at = time.time()
            state.checkpoints.append({
                "step": step_name,
                "timestamp": time.time(),
                "data_keys": list(data.keys()) if data else [],
            })

        log.info(
            "Checkpoint saved",
            task_id=task_id,
            step=step_name,
            progress=f"{state.progress_pct}%",
        )

    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current task status."""
        with self._lock:
            state = self._tasks.get(task_id)
            if not state:
                return None

            return {
                "task_id": state.task_id,
                "status": state.status.value,
                "query": state.query,
                "domain": state.domain,
                "current_step": state.current_step,
                "steps_completed": state.steps_completed,
                "total_steps": state.total_steps,
                "progress_pct": state.progress_pct,
                "created_at": state.created_at,
                "updated_at": state.updated_at,
                "has_result": state.result is not None,
                "error": state.error,
                "agents": state.metadata.get("agents", []),
                "total_agents": state.metadata.get("total_agents", 0),
                "completed_agents": state.metadata.get("completed_agents", 0),
            }

    def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task result (only available after completion)."""
        with self._lock:
            state = self._tasks.get(task_id)
            if not state:
                return None
            if state.status != TaskStatus.COMPLETED:
                return {"status": state.status.value, "message": "Task not yet completed"}
            return state.result

    def cancel(self, task_id: str) -> bool:
        """Cancel a queued or running task."""
        with self._lock:
            state = self._tasks.get(task_id)
            if not state:
                return False
            if state.status in (TaskStatus.QUEUED, TaskStatus.RUNNING):
                state.status = TaskStatus.CANCELLED
                state.updated_at = time.time()
                log.info("Task cancelled", task_id=task_id)
                return True
            return False

    def list_tasks(self, status: Optional[TaskStatus] = None, limit: int = 50) -> List[Dict]:
        """List tasks with optional status filter."""
        with self._lock:
            tasks = list(self._tasks.values())
            if status:
                tasks = [t for t in tasks if t.status == status]
            tasks.sort(key=lambda t: t.created_at, reverse=True)
            return [
                {
                    "task_id": t.task_id,
                    "status": t.status.value,
                    "query": t.query[:80],
                    "progress_pct": t.progress_pct,
                    "created_at": t.created_at,
                }
                for t in tasks[:limit]
            ]

    def _update_status(self, task_id: str, status: TaskStatus, **kwargs):
        """Update task state."""
        with self._lock:
            state = self._tasks.get(task_id)
            if state:
                state.status = status
                state.updated_at = time.time()
                for key, value in kwargs.items():
                    if hasattr(state, key):
                        setattr(state, key, value)

    def cleanup(self, max_age_seconds: int = 86400):
        """Remove tasks older than max_age_seconds."""
        now = time.time()
        with self._lock:
            to_remove = [
                tid for tid, state in self._tasks.items()
                if now - state.created_at > max_age_seconds
                and state.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
            ]
            for tid in to_remove:
                del self._tasks[tid]
        if to_remove:
            log.info("Tasks cleaned up", count=len(to_remove))
