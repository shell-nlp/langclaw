"""
HttpChannel — Gateway channel exposing a FastAPI HTTP server with SSE streaming.

Requires: langclaw[http]  →  uv add "langclaw[http]"

Protocol (SSE over HTTP):
  POST /stream:
    {"user_id": "...", "context_id": "...", "content": "...", "attachments": [...]}

  Outbound SSE:
    event: tool_progress\ndata: {"content": "...", "metadata": {...}}\n\n
    event: tool_result\ndata: {"content": "...", "metadata": {...}}\n\n
    event: ai\ndata: {"content": "..."}\n\n

Each SSE stream is identified by ``(user_id, context_id)`` pair.
The POST /stream publishes to the bus and returns an SSE stream for responses.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from langclaw.bus.base import (
    Attachment,
    AttachmentType,
    BaseMessageBus,
    InboundMessage,
    OutboundMessage,
)
from langclaw.config.schema import HttpChannelConfig
from langclaw.gateway.base import BaseChannel
from langclaw.gateway.commands import CommandContext
from langclaw.gateway.utils import is_allowed

if TYPE_CHECKING:
    from starlette.responses import Response

logger = logging.getLogger(__name__)


class _PendingStream:
    """Holds an async iterator for one SSE stream session."""

    __slots__ = ("queue", "user_id", "context_id")

    def __init__(self, user_id: str, context_id: str) -> None:
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.user_id = user_id
        self.context_id = context_id


class HttpChannel(BaseChannel):
    """
    HTTP server channel backed by FastAPI + uvicorn with SSE streaming.

    Single endpoint:
      - ``POST /stream`` — receives JSON with message data, returns SSE stream

    Args:
        config: HTTP-specific section of LangclawConfig.channels.http.
    """

    name = "http"

    def __init__(self, config: HttpChannelConfig) -> None:
        self._config = config
        self._bus: BaseMessageBus | None = None
        self._server_task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()
        self._streams: dict[str, _PendingStream] = {}
        self._streams_lock = asyncio.Lock()

    def is_enabled(self) -> bool:
        return self._config.enabled

    def _stream_key(self, user_id: str, context_id: str) -> str:
        return f"{user_id}:{context_id}"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self, bus: BaseMessageBus) -> None:
        try:
            import fastapi  # noqa: F401
            import uvicorn  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "HttpChannel requires 'fastapi' and 'uvicorn'. "
                "Install with: uv add 'langclaw[http]'"
            ) from exc

        self._bus = bus

        app = self._build_app()
        config = uvicorn.Config(
            app,
            host=self._config.host,
            port=self._config.port,
            log_level="warning",
        )
        server = uvicorn.Server(config)

        self._shutdown_event = asyncio.Event()
        self._server_task = asyncio.create_task(server.serve())

        logger.info(
            "HttpChannel listening on http://%s:%s",
            self._config.host,
            self._config.port,
        )

        try:
            await asyncio.Future()
        finally:
            self._shutdown_event.set()
            if self._server_task:
                self._server_task.cancel()
                try:
                    await self._server_task
                except asyncio.CancelledError:
                    pass

    def _build_app(self) -> Any:
        from fastapi import FastAPI

        app = FastAPI(title="langclaw-http")

        @app.post("/stream")
        async def stream_events(data: dict[str, Any]) -> Response:
            return await self._handle_stream(data)

        @app.get("/health")
        async def health() -> dict[str, str]:
            return {"status": "ok"}

        return app

    async def stop(self) -> None:
        self._shutdown_event.set()
        if self._server_task:
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                pass
            self._server_task = None
        async with self._streams_lock:
            self._streams.clear()
        logger.info("HttpChannel stopped.")

    # ------------------------------------------------------------------
    # Stream handler
    # ------------------------------------------------------------------

    async def _handle_stream(self, data: dict[str, Any]) -> Response:
        """Handle POST /stream request and return SSE response."""
        user_id = data.get("user_id", "http-anon")
        context_id = data.get("context_id", "default")
        content = data.get("content", "")

        if not self._is_allowed(user_id):
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=403,
                content={"type": "error", "content": "Not authorised."},
            )

        if not content and not data.get("attachments"):
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=400,
                content={"type": "error", "content": "Empty message."},
            )

        stream_key = self._stream_key(user_id, context_id)
        pending = _PendingStream(user_id, context_id)

        async with self._streams_lock:
            self._streams[stream_key] = pending

        stripped = content.strip()
        if stripped.startswith("/") and self._command_router is not None:
            parts = stripped.split()
            cmd = parts[0].lstrip("/").lower()
            args = parts[1:] if len(parts) > 1 else []
            ctx = CommandContext(
                channel=self.name,
                user_id=user_id,
                context_id=context_id,
                chat_id=stream_key,
                args=args,
                display_name=user_id,
            )
            response = await self._command_router.dispatch(cmd, ctx)
            await pending.queue.put({"type": "command", "content": response})

        elif self._bus is not None:
            raw_attachments = data.get("attachments") or []
            attachments = [
                Attachment(
                    type=AttachmentType(a.get("type", "file")),
                    mime_type=a.get("mime_type", ""),
                    filename=a.get("filename", ""),
                    url=a.get("url", ""),
                    data=a.get("data", ""),
                    size=a.get("size", 0),
                )
                for a in raw_attachments
                if isinstance(a, dict)
            ]

            client_metadata = data.get("metadata") or {}

            await self._bus.publish(
                InboundMessage(
                    channel=self.name,
                    user_id=user_id,
                    context_id=context_id,
                    chat_id=stream_key,
                    content=content,
                    origin="channel",
                    attachments=attachments,
                    metadata={
                        "platform": "http",
                        "stream_key": stream_key,
                        **client_metadata,
                    },
                )
            )

        try:
            return await self._stream_response(pending, stream_key)
        finally:
            pass

    async def _stream_response(self, pending: _PendingStream, stream_key: str) -> Response:
        """Create an async SSE streaming response."""
        from starlette.responses import StreamingResponse

        async def event_generator() -> AsyncIterator[str]:
            try:
                while True:
                    try:
                        event = await asyncio.wait_for(pending.queue.get(), timeout=6)
                    except TimeoutError:
                        break

                    # event_type = event.get("type", "ai")
                    event_data = event.get("content", "")
                    event_metadata = event.get("metadata", {})

                    if event_metadata:
                        payload = f'{{"content": {event_data!r}, "metadata": {event_metadata}}}'
                    else:
                        payload = f'{{"content": {event_data!r}}}'

                    yield f"data: {payload}\n\n"
            except asyncio.CancelledError:
                pass

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # ------------------------------------------------------------------
    # Outbound hooks
    # ------------------------------------------------------------------

    async def send_tool_progress(self, msg: OutboundMessage) -> None:
        await self._push_to_stream(msg)

    async def send_tool_result(self, msg: OutboundMessage) -> None:
        await self._push_to_stream(msg)

    async def send_ai_message(self, msg: OutboundMessage) -> None:
        if not msg.content:
            return
        await self._push_to_stream(msg)

    async def _push_to_stream(self, msg: OutboundMessage) -> None:
        """Push an outbound message to the appropriate SSE stream."""
        stream_key = msg.metadata.get("stream_key") if msg.metadata else None
        if not stream_key:
            stream_key = self._stream_key(msg.user_id, msg.context_id)
        async with self._streams_lock:
            pending = self._streams.get(stream_key)
        if pending is None:
            return

        event = {
            "type": msg.type,
            "content": msg.content,
            "metadata": msg.metadata,
        }

        await pending.queue.put(event)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_allowed(self, user_id: str) -> bool:
        return is_allowed(self._config.allow_from, user_id)
