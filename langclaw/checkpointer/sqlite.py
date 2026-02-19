"""
SQLite checkpointer backend — default for dev / single-process deployments.

Requires: langgraph-checkpoint-sqlite (included in core dependencies).
"""

from __future__ import annotations

from pathlib import Path

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from langclaw.checkpointer.base import BaseCheckpointerBackend


class SqliteCheckpointerBackend(BaseCheckpointerBackend):
    """
    Async SQLite-backed LangGraph checkpoint saver.

    Args:
        db_path: Path to the SQLite database file.
                 Tilde expansion is applied automatically.
                 Default: ``~/.langclaw/state.db``.
    """

    def __init__(self, db_path: str = "~/.langclaw/state.db") -> None:
        self._db_path = Path(db_path).expanduser()
        self._ctx: object = None  # AsyncSqliteSaver async context manager

    async def _open(self) -> BaseCheckpointSaver:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ctx = AsyncSqliteSaver.from_conn_string(str(self._db_path))
        saver = await self._ctx.__aenter__()
        return saver

    async def _close(self) -> None:
        if self._ctx is not None:
            await self._ctx.__aexit__(None, None, None)
            self._ctx = None
