"""In-memory remediation session (single active run enforced in main)."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RemediationSession:
    id: str
    events: List[Dict[str, Any]] = field(default_factory=list)
    completed: bool = False
    success: Optional[bool] = None
    exit_code: Optional[int] = None
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @staticmethod
    def new() -> "RemediationSession":
        return RemediationSession(id=str(uuid.uuid4()))

    async def append_event(self, event: Dict[str, Any]) -> None:
        async with self._lock:
            self.events.append(event)

    async def snapshot_events(self, from_index: int) -> tuple[List[Dict[str, Any]], int]:
        async with self._lock:
            return list(self.events[from_index:]), len(self.events)

    def mark_done(self, success: bool, exit_code: int) -> None:
        self.completed = True
        self.success = success
        self.exit_code = exit_code
