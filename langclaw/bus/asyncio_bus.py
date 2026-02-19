"""
AsyncioMessageBus — default in-process bus backed by asyncio.Queue.

Suitable for single-process / development deployments.
For multi-process production use RabbitMQMessageBus or KafkaMessageBus.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from langclaw.bus.base import BaseMessageBus, InboundMessage


class AsyncioMessageBus(BaseMessageBus):
    """
    In-process message bus using :class:`asyncio.Queue`.

    Thread-safe within a single event loop. Not suitable for multi-process
    or distributed deployments — use RabbitMQ/Kafka for those.
    """

    def __init__(self, maxsize: int = 0) -> None:
        """
        Args:
            maxsize: Maximum queue depth. 0 = unbounded.
                     Set a limit in production to apply back-pressure.
        """
        self._maxsize = maxsize
        self._queue: asyncio.Queue[InboundMessage] | None = None

    async def start(self) -> None:
        self._queue = asyncio.Queue(maxsize=self._maxsize)

    async def stop(self) -> None:
        # Drain remaining items to unblock any waiting consumers
        if self._queue is not None:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                    self._queue.task_done()
                except asyncio.QueueEmpty:
                    break

    async def publish(self, msg: InboundMessage) -> None:
        if self._queue is None:
            raise RuntimeError("Bus not started — use 'async with bus:' first.")
        await self._queue.put(msg)

    async def subscribe(self) -> AsyncIterator[InboundMessage]:  # type: ignore[override]
        if self._queue is None:
            raise RuntimeError("Bus not started — use 'async with bus:' first.")
        while True:
            msg = await self._queue.get()
            try:
                yield msg
            finally:
                self._queue.task_done()
