"""
Async Job System — queue-based execution with persistent state management.

Flow: User → API → Queue → asyncio.to_thread(Worker) → Result Store → WebSocket

Provides:
- Async task submission with immediate task_id return
- Non-blocking execution via asyncio.to_thread (won't starve the event loop)
- Checkpointing after each pipeline step
- Task status polling and result retrieval
- Cancellation support
"""

import asyncio
import time
import uuid
import threading
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
    Async-aware task queue using asyncio.to_thread for CPU-bound workflows.

    - submit() schedules a task as an asyncio background coroutine
    - The actual workflow runs in a thread (via asyncio.to_thread) so it
      never blocks the FastAPI event loop
    - Supports concurrent tasks limited by max_workers semaphore
    """

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
        self._tasks: Dict[str, TaskState] = {}
        self._lock = threading.Lock()
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._max_workers = max_workers

    def _get_semaphore(self) -> asyncio.Semaphore:
        """Lazy-create semaphore (must happen inside an event loop)."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._max_workers)
        return self._semaphore

    def submit(
        self,
        func: Callable,
        query: str,
        domain: str = "general",
        **kwargs,
    ) -> str:
        """
        Submit a task for async execution.

        Schedules the work as an asyncio task running in a background thread.
        Returns task_id immediately.
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

        # Schedule as a fire-and-forget asyncio task
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self._run_async(task_id, func, query, domain, **kwargs))
            else:
                # Fallback: run in a thread if no event loop
                import concurrent.futures
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                executor.submit(self._run_sync, task_id, func, query, domain, **kwargs)
        except RuntimeError:
            import concurrent.futures
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            executor.submit(self._run_sync, task_id, func, query, domain, **kwargs)

        log.info("Task submitted", task_id=task_id, query=query[:80])
        return task_id

    async def _run_async(
        self,
        task_id: str,
        func: Callable,
        query: str,
        domain: str,
        **kwargs,
    ):
        """Run the workflow in a thread, gated by a semaphore for concurrency control."""
        sem = self._get_semaphore()
        async with sem:
            self._update_status(task_id, TaskStatus.RUNNING, current_step="starting")
            try:
                result = await asyncio.to_thread(
                    func, query=query, domain=domain, task_id=task_id, **kwargs,
                )
                self._on_complete_success(task_id, result)
            except Exception as e:
                self._on_complete_failure(task_id, e)

    def _run_sync(
        self,
        task_id: str,
        func: Callable,
        query: str,
        domain: str,
        **kwargs,
    ):
        """Fallback sync execution for environments without a running event loop."""
        self._update_status(task_id, TaskStatus.RUNNING, current_step="starting")
        try:
            result = func(query=query, domain=domain, task_id=task_id, **kwargs)
            self._on_complete_success(task_id, result)
        except Exception as e:
            self._on_complete_failure(task_id, e)

    def _on_complete_success(self, task_id: str, result: Any):
        """Handle successful task completion."""
        from research_and_analyst.job_queue.websocket_manager import broadcast_completed

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

    def _on_complete_failure(self, task_id: str, error: Exception):
        """Handle task failure."""
        from research_and_analyst.job_queue.websocket_manager import broadcast_error

        self._update_status(
            task_id,
            TaskStatus.FAILED,
            current_step="failed",
            error=str(error),
        )
        log.error("Task failed", task_id=task_id, error=str(error))
        broadcast_error(task_id, str(error))

    def checkpoint(self, task_id: str, step_name: str, data: Optional[Dict] = None):
        """Save a checkpoint after a pipeline step completes."""
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
