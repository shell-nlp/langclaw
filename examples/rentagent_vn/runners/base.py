"""Base class for background TinyFish runners with task management."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from examples.rentagent_vn.tinyfish.client import TinyFishClient
from examples.rentagent_vn.tinyfish.types import TinyFishSSEEvent
from langclaw import Langclaw

ProgressCallback = Callable[
    [Langclaw, str, str, str, str, str, dict[str, Any]],
    Awaitable[None],
]
"""(app, id_primary, id_secondary, id_tertiary, event_type/step, purpose/detail, channel_context)"""

StreamingUrlCallback = Callable[
    [Langclaw, str, str, str, str, dict[str, Any]],
    Awaitable[None],
]
"""(app, id_primary, id_secondary, id_tertiary, streaming_url, channel_context)"""

ErrorCallback = Callable[
    [Langclaw, str, str, str, str, dict[str, Any]],
    Awaitable[None],
]
"""(app, id_primary, id_secondary, id_tertiary, error_message, channel_context)"""


class BaseTinyFishRunner:
    """Base class for background runners that stream TinyFish events.

    Provides:
    - Asyncio task lifecycle management (_tasks dict, job_id generation)
    - Common callback storage (progress, streaming_url, error)
    - Helper to dispatch TinyFish SSE events to callbacks

    Subclasses implement their own start() and _run() with domain-specific
    logic and their own result callback type.

    Args:
        app: The Langclaw application instance.
        tinyfish_client: TinyFish SSE streaming client.
        progress_callback: Called on PROGRESS events.
        streaming_url_callback: Called on STREAMING_URL events.
        error_callback: Called on ERROR events.
    """

    def __init__(
        self,
        app: Langclaw,
        tinyfish_client: TinyFishClient,
        *,
        progress_callback: ProgressCallback | None = None,
        streaming_url_callback: StreamingUrlCallback | None = None,
        error_callback: ErrorCallback | None = None,
    ) -> None:
        self._app = app
        self._tinyfish_client = tinyfish_client
        self._progress_callback = progress_callback
        self._streaming_url_callback = streaming_url_callback
        self._error_callback = error_callback
        self._tasks: dict[str, asyncio.Task[None]] = {}

    def _generate_job_id(self) -> str:
        """Generate a 12-character hex job identifier."""
        return uuid4().hex[:12]

    async def _dispatch_event(
        self,
        event: TinyFishSSEEvent,
        *,
        id_primary: str,
        id_secondary: str,
        id_tertiary: str,
        channel_context: dict[str, Any],
    ) -> None:
        """Dispatch a TinyFish SSE event to the appropriate callback.

        Handles PROGRESS and STREAMING_URL events. COMPLETE and ERROR
        are left to subclasses because their handling differs (scrape
        aggregates multi-URL results; research raises on error).

        Args:
            event: The TinyFish SSE event.
            id_primary: Primary identifier (job_id or research_id).
            id_secondary: Secondary identifier (run_id or listing_id).
            id_tertiary: Tertiary identifier (url or campaign_id).
            channel_context: Channel context dict for callbacks.
        """
        if event.type == "PROGRESS" and self._progress_callback:
            await self._progress_callback(
                self._app,
                id_primary,
                id_secondary,
                id_tertiary,
                event.purpose or "processing",
                event.purpose or "",
                channel_context,
            )
        elif event.type == "STREAMING_URL" and event.streaming_url:
            if self._streaming_url_callback:
                await self._streaming_url_callback(
                    self._app,
                    id_primary,
                    id_secondary,
                    id_tertiary,
                    event.streaming_url,
                    channel_context,
                )
