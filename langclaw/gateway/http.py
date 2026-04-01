"""
HttpChannel — Gateway channel exposing a FastAPI HTTP server.

Requires: langclaw[http]  →  uv add "langclaw[http]"

Protocol (JSON over HTTP):
  Inbound  (client → gateway)  POST /message:
    {"user_id": "...", "context_id": "...", "content": "...", "attachments": [...]}

  Outbound (gateway → client):
    {"type": "ai"|"tool_progress"|"tool_result", "content": "...", ...}

Each request is identified by ``(user_id, context_id)`` pair.
Outbound messages are matched to pending HTTP responses via correlation_id.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
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


def _make_json_response(status_code: int, content: dict[str, Any]) -> Response:
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=status_code, content=content)


def _make_json_response_ok(content: dict[str, Any]) -> Response:
    from fastapi.responses import JSONResponse

    return JSONResponse(content=content)


class _PendingResponse:
    """Holds a response future for one HTTP request, awaited by the POST handler."""

    __slots__ = ("event", "response")

    def __init__(self) -> None:
        self.event: asyncio.Event = asyncio.Event()
        self.response: dict[str, Any] = {}


class HttpChannel(BaseChannel):
    """
    HTTP server channel backed by FastAPI + uvicorn.

    Listens on ``http://<host>:<port>`` and accepts JSON-framed messages.
    Matches outbound messages to pending requests via correlation_id.

    Args:
        config: HTTP-specific section of LangclawConfig.channels.http.
    """

    name = "http"

    def __init__(self, config: HttpChannelConfig) -> None:
        self._config = config
        self._bus: BaseMessageBus | None = None
        self._server_task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()
        self._pending: dict[str, _PendingResponse] = {}
        self._pending_lock = asyncio.Lock()

    def is_enabled(self) -> bool:
        return self._config.enabled

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

        @app.post("/message")
        async def handle_message(data: dict[str, Any]) -> Response:
            return await self._handle_message(data)

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
        async with self._pending_lock:
            self._pending.clear()
        logger.info("HttpChannel stopped.")

    # ------------------------------------------------------------------
    # Message handler
    # ------------------------------------------------------------------

    async def _handle_message(self, data: dict[str, Any]) -> Response:
        """Process an inbound HTTP POST /message request."""
        user_id = data.get("user_id", "http-anon")
        context_id = data.get("context_id", "default")
        content = data.get("content", "")

        if not self._is_allowed(user_id):
            return _make_json_response(
                403,
                {"type": "error", "content": "Not authorised."},
            )

        if not content and not data.get("attachments"):
            return _make_json_response(
                400,
                {"type": "error", "content": "Empty message."},
            )

        stripped = content.strip()
        if stripped.startswith("/") and self._command_router is not None:
            parts = stripped.split()
            cmd = parts[0].lstrip("/").lower()
            args = parts[1:] if len(parts) > 1 else []
            ctx = CommandContext(
                channel=self.name,
                user_id=user_id,
                context_id=context_id,
                chat_id=f"{user_id}:{context_id}",
                args=args,
                display_name=user_id,
            )
            response = await self._command_router.dispatch(cmd, ctx)
            return _make_json_response_ok({"type": "command", "content": response})

        if self._bus is None:
            return _make_json_response(
                503,
                {"type": "error", "content": "Bus not available."},
            )

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
        msg_id = str(uuid.uuid4())

        pending = _PendingResponse()
        async with self._pending_lock:
            self._pending[msg_id] = pending

        inbound_metadata = {
            "platform": "http",
            "correlation_id": msg_id,
            **client_metadata,
        }

        try:
            await self._bus.publish(
                InboundMessage(
                    channel=self.name,
                    user_id=user_id,
                    context_id=context_id,
                    chat_id=f"{user_id}:{context_id}",
                    content=content,
                    origin="channel",
                    attachments=attachments,
                    metadata=inbound_metadata,
                )
            )

            await asyncio.wait_for(pending.event.wait(), timeout=300)
            response_data = pending.response

        except TimeoutError:
            async with self._pending_lock:
                self._pending.pop(msg_id, None)
            return _make_json_response(
                504,
                {"type": "error", "content": "Request timed out."},
            )
        except Exception as exc:
            async with self._pending_lock:
                self._pending.pop(msg_id, None)
            logger.exception("Error processing HTTP message: %s", exc)
            return _make_json_response(
                500,
                {"type": "error", "content": "Internal error."},
            )
        finally:
            async with self._pending_lock:
                self._pending.pop(msg_id, None)

        response_type = response_data.get("type", "ai")
        response_content = response_data.get("content", "")

        return _make_json_response_ok({"type": response_type, "content": response_content})

    # ------------------------------------------------------------------
    # Outbound hooks
    # ------------------------------------------------------------------

    async def send_tool_progress(self, msg: OutboundMessage) -> None:
        correlation_id = msg.metadata.get("correlation_id") if msg.metadata else None
        if not correlation_id:
            return
        async with self._pending_lock:
            pending = self._pending.get(correlation_id)
        if pending is None:
            return
        if not msg.content:
            return
        pending.response = {
            "type": "tool_progress",
            "content": msg.content,
        }
        pending.event.set()
        pending.event.clear()
        await asyncio.sleep(0)
        async with self._pending_lock:
            pending.response = {}
            pending.event.clear()

    async def send_tool_result(self, msg: OutboundMessage) -> None:
        correlation_id = msg.metadata.get("correlation_id") if msg.metadata else None
        if not correlation_id:
            return
        async with self._pending_lock:
            pending = self._pending.get(correlation_id)
        if pending is None:
            return
        pending.response = {
            "type": "tool_result",
            "content": msg.content,
        }
        pending.event.set()
        pending.event.clear()
        await asyncio.sleep(0)
        async with self._pending_lock:
            pending.response = {}
            pending.event.clear()

    async def send_ai_message(self, msg: OutboundMessage) -> None:
        if not msg.content:
            return
        logger.warning("Sending AI message to unknown correlation_id: %s", msg)
        correlation_id = msg.metadata.get("correlation_id") if msg.metadata else None
        if not correlation_id:
            return
        async with self._pending_lock:
            pending = self._pending.get(correlation_id)
        if pending is None:
            return
        pending.response = {
            "type": "ai",
            "content": msg.content,
        }
        pending.event.set()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_allowed(self, user_id: str) -> bool:
        return is_allowed(self._config.allow_from, user_id)
