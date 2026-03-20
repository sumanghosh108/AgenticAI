"""
WebSocket Manager — real-time task progress broadcasting.

Provides:
- WebSocket connection management
- Real-time progress updates to connected clients
- Task status change notifications
- Heartbeat / keepalive
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect
from research_and_analyst.logger import GLOBAL_LOGGER as log


def _fire_async(coro):
    """Run an async coroutine from a sync thread context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(coro)
        else:
            loop.run_until_complete(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(coro)


def broadcast_progress(task_id: str, step: str, progress_pct: float,
                       status: str = "running", details: Optional[Dict] = None):
    """Thread-safe helper to broadcast progress from sync code."""
    _fire_async(ws_manager.send_progress(task_id, step, progress_pct, status, details))


def broadcast_completed(task_id: str, result: Optional[Dict] = None):
    """Thread-safe helper to broadcast completion from sync code."""
    _fire_async(ws_manager.send_completed(task_id, result))


def broadcast_error(task_id: str, error: str):
    """Thread-safe helper to broadcast errors from sync code."""
    _fire_async(ws_manager.send_error(task_id, error))


class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts task progress.

    Usage:
        manager = ConnectionManager()

        @app.websocket("/ws/task/{task_id}")
        async def ws_endpoint(websocket: WebSocket, task_id: str):
            await manager.connect(websocket, task_id)
            try:
                while True:
                    data = await websocket.receive_text()
            except WebSocketDisconnect:
                manager.disconnect(websocket, task_id)
    """

    def __init__(self):
        # task_id → set of connected websockets
        self._connections: Dict[str, Set[WebSocket]] = {}
        # All active connections
        self._all_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, task_id: str):
        """Accept and register a WebSocket connection."""
        await websocket.accept()

        if task_id not in self._connections:
            self._connections[task_id] = set()

        self._connections[task_id].add(websocket)
        self._all_connections.add(websocket)

        log.info("WebSocket connected", task_id=task_id, total=len(self._all_connections))

        # Send initial status
        await self._send(websocket, {
            "type": "connected",
            "task_id": task_id,
            "timestamp": time.time(),
        })

    def disconnect(self, websocket: WebSocket, task_id: str):
        """Remove a WebSocket connection."""
        if task_id in self._connections:
            self._connections[task_id].discard(websocket)
            if not self._connections[task_id]:
                del self._connections[task_id]

        self._all_connections.discard(websocket)
        log.info("WebSocket disconnected", task_id=task_id)

    async def send_progress(
        self,
        task_id: str,
        step: str,
        progress_pct: float,
        status: str = "running",
        details: Optional[Dict] = None,
    ):
        """Broadcast progress update to all clients watching a task."""
        message = {
            "type": "progress",
            "task_id": task_id,
            "step": step,
            "progress_pct": progress_pct,
            "status": status,
            "details": details or {},
            "timestamp": time.time(),
        }
        await self._broadcast(task_id, message)

    async def send_completed(
        self,
        task_id: str,
        result: Optional[Dict] = None,
    ):
        """Broadcast task completion."""
        message = {
            "type": "completed",
            "task_id": task_id,
            "progress_pct": 100.0,
            "status": "completed",
            "result": result or {},
            "timestamp": time.time(),
        }
        await self._broadcast(task_id, message)

    async def send_error(self, task_id: str, error: str):
        """Broadcast task error."""
        message = {
            "type": "error",
            "task_id": task_id,
            "status": "failed",
            "error": error,
            "timestamp": time.time(),
        }
        await self._broadcast(task_id, message)

    async def _broadcast(self, task_id: str, message: Dict):
        """Send message to all connections watching a task."""
        connections = self._connections.get(task_id, set())
        disconnected = set()

        for ws in connections:
            try:
                await self._send(ws, message)
            except Exception:
                disconnected.add(ws)

        # Clean up disconnected
        for ws in disconnected:
            self.disconnect(ws, task_id)

    async def _send(self, websocket: WebSocket, data: Dict):
        """Send JSON data to a single WebSocket."""
        await websocket.send_text(json.dumps(data, default=str))

    @property
    def active_connections(self) -> int:
        return len(self._all_connections)

    @property
    def watched_tasks(self) -> List[str]:
        return list(self._connections.keys())


# Global instance
ws_manager = ConnectionManager()
