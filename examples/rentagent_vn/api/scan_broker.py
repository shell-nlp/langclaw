"""In-memory event broker for real-time scan progress streaming.

This module provides a pub/sub mechanism for broadcasting scan events
to multiple SSE subscribers with buffered replay for late-joining clients.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@dataclass
class ScanEvent:
    """A single event in the scan stream."""

    type: str  # started | progress | streaming_url | error | complete
    url: str | None
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.monotonic)


@dataclass
class _ScanState:
    """Internal state for a single scan's event stream."""

    events: list[ScanEvent] = field(default_factory=list)
    subscribers: list[asyncio.Queue[ScanEvent | None]] = field(default_factory=list)
    done: bool = False


class ScanEventBroker:
    """In-memory event broker with buffered pub/sub for scan events.

    Features:
    - Per-scan event buffer for replay
    - Multiple concurrent subscribers per scan
    - Late-joining clients receive full history
    - Auto-cleanup after TTL
    """

    def __init__(self, cleanup_ttl_seconds: float = 300.0) -> None:
        self._scans: dict[str, _ScanState] = {}
        self._cleanup_ttl = cleanup_ttl_seconds

    def publish(self, scan_id: str, event: ScanEvent) -> None:
        """Publish an event to all subscribers of a scan.

        This is synchronous (non-blocking) so it can be called from
        async callbacks without overhead.

        Args:
            scan_id: The scan identifier.
            event: The event to publish.
        """
        state = self._scans.setdefault(scan_id, _ScanState())
        state.events.append(event)

        for queue in state.subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(
                    "Subscriber queue full for scan {}, dropping event",
                    scan_id,
                )

        if event.type == "complete":
            state.done = True
            for queue in state.subscribers:
                try:
                    queue.put_nowait(None)  # Sentinel to signal completion
                except asyncio.QueueFull:
                    pass
            self._schedule_cleanup(scan_id)

    async def subscribe(self, scan_id: str) -> AsyncIterator[ScanEvent]:
        """Subscribe to events for a scan.

        Yields all buffered events first (replay), then waits for new ones.
        Iteration ends when the scan completes or an error occurs.

        Args:
            scan_id: The scan identifier.

        Yields:
            ScanEvent objects in chronological order.
        """
        state = self._scans.get(scan_id)
        if state is None:
            state = self._scans.setdefault(scan_id, _ScanState())

        queue: asyncio.Queue[ScanEvent | None] = asyncio.Queue(maxsize=1000)
        state.subscribers.append(queue)

        try:
            # Replay buffered events first
            for event in list(state.events):
                yield event

            # If already done, stop
            if state.done:
                return

            # Wait for new events
            while True:
                event = await queue.get()
                if event is None:
                    return  # Scan complete
                yield event

        finally:
            if queue in state.subscribers:
                state.subscribers.remove(queue)

    def _schedule_cleanup(self, scan_id: str) -> None:
        """Schedule cleanup of scan state after TTL."""

        async def _cleanup() -> None:
            await asyncio.sleep(self._cleanup_ttl)
            self.cleanup(scan_id)

        try:
            asyncio.create_task(_cleanup(), name=f"scan-cleanup-{scan_id}")
        except RuntimeError:
            # No running event loop (e.g., during testing)
            pass

    def cleanup(self, scan_id: str) -> None:
        """Remove state for a completed scan."""
        removed = self._scans.pop(scan_id, None)
        if removed:
            logger.debug("Cleaned up scan state for {}", scan_id)

    def get_state(self, scan_id: str) -> _ScanState | None:
        """Get current state for a scan (for debugging/testing)."""
        return self._scans.get(scan_id)


# Module-level singleton
scan_broker = ScanEventBroker()
