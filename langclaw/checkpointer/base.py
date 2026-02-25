"""
BaseCheckpointerBackend — abstract seam for LangGraph checkpoint persistence.

Swap dev → prod = one config field change (``checkpointer.backend``).
The GatewayManager never imports a concrete saver directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from langgraph.checkpoint.base import BaseCheckpointSaver


class BaseCheckpointerBackend(ABC):
    """
    Lifecycle-managed factory for a LangGraph ``BaseCheckpointSaver``.

    Usage (within an async context manager)::

        async with SqliteCheckpointerBackend() as backend:
            checkpointer = await backend.get()
            agent = create_claw_agent(config, checkpointer=checkpointer)
            ...
    """

    _saver: BaseCheckpointSaver | None = None

    @abstractmethod
    async def _open(self) -> BaseCheckpointSaver:
        """Open the underlying storage and return a ready saver."""
        ...

    @abstractmethod
    async def _close(self) -> None:
        """Release resources held by the saver."""
        ...

    async def __aenter__(self) -> BaseCheckpointerBackend:
        self._saver = await self._open()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._close()
        self._saver = None

    def get(self) -> BaseCheckpointSaver:
        """Return the active saver (must be called inside the context manager)."""
        if self._saver is None:
            raise RuntimeError("Checkpointer not initialised — use 'async with backend:' first.")
        return self._saver
