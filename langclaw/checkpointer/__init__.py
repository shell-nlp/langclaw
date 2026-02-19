from langclaw.checkpointer.base import BaseCheckpointerBackend
from langclaw.checkpointer.postgres import PostgresCheckpointerBackend
from langclaw.checkpointer.sqlite import SqliteCheckpointerBackend


def make_checkpointer_backend(
    backend: str,
    *,
    db_path: str = "~/.langclaw/state.db",
    dsn: str = "",
) -> BaseCheckpointerBackend:
    """
    Factory that returns the correct ``BaseCheckpointerBackend`` from a config string.

    Args:
        backend: One of ``"sqlite"`` or ``"postgres"``.
        db_path: Path for SQLite backend.
        dsn:     Connection string for Postgres backend.
    """
    if backend == "sqlite":
        return SqliteCheckpointerBackend(db_path=db_path)
    if backend == "postgres":
        return PostgresCheckpointerBackend(dsn=dsn)
    raise ValueError(f"Unknown checkpointer backend: {backend!r}. Choose 'sqlite' or 'postgres'.")


__all__ = [
    "BaseCheckpointerBackend",
    "SqliteCheckpointerBackend",
    "PostgresCheckpointerBackend",
    "make_checkpointer_backend",
]
