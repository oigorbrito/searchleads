from __future__ import annotations

from .semantic import SQLiteRepository as _SemanticSQLiteRepository
from .sqlite import SCHEMA_VERSION


class SQLiteRepository(_SemanticSQLiteRepository):
    """Semantic repository with an idempotent current-version migration ledger."""

    def _repair_current_schema(self) -> None:
        super()._repair_current_schema()
        self._connection.execute(
            "INSERT OR IGNORE INTO schema_migrations(version) VALUES (?)",
            (SCHEMA_VERSION,),
        )
