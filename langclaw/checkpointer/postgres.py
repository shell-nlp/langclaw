"""
PostgreSQL checkpointer backend — for production / multi-process deployments.

Requires: langclaw[postgres]
    pip install langclaw[postgres]
    # or:
    uv add "langclaw[postgres]"
"""

from __future__ import annotations

from langclaw.checkpointer.base import BaseCheckpointerBackend


class PostgresCheckpointerBackend(BaseCheckpointerBackend):
    """
    Async PostgreSQL-backed LangGraph checkpoint saver.

    Args:
        dsn: PostgreSQL connection string.
             Example: ``postgresql://user:pass@localhost:5432/langclaw``
    """

    def __init__(self, dsn: str) -> None:
        if not dsn:
            raise ValueError(
                "PostgresCheckpointerBackend requires a non-empty DSN. "
                "Set checkpointer.postgres.dsn in your config or "
                "LANGCLAW__CHECKPOINTER__POSTGRES__DSN env var."
            )
        self._dsn = dsn
        self._ctx: object = None

    async def _open(self) -> object:
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        except ImportError as exc:
            raise ImportError(
                "PostgreSQL checkpointer requires 'langclaw[postgres]'. "
                "Install with: uv add 'langclaw[postgres]'"
            ) from exc

        self._ctx = AsyncPostgresSaver.from_conn_string(self._dsn)
        saver = await self._ctx.__aenter__()
        # Run migrations on first use
        await saver.setup()
        return saver

    async def _close(self) -> None:
        if self._ctx is not None:
            await self._ctx.__aexit__(None, None, None)
            self._ctx = None
