from __future__ import annotations

from .semantic import SQLiteRepository as _SemanticSQLiteRepository
from .sqlite import SCHEMA_VERSION, Evidence, PersistenceError


class EvidenceEnvelopeConsistencyError(PersistenceError):
    """Raised when an Evidence envelope disagrees with its immutable storage columns."""


class SQLiteRepository(_SemanticSQLiteRepository):
    """Semantic repository with ledger repair and Evidence envelope consistency checks."""

    def _repair_current_schema(self) -> None:
        super()._repair_current_schema()
        self._connection.execute(
            "INSERT OR IGNORE INTO schema_migrations(version) VALUES (?)",
            (SCHEMA_VERSION,),
        )

    def load_evidence(self, evidence_id: str) -> Evidence | None:
        evidence = super().load_evidence(evidence_id)
        if evidence is None:
            return None

        row = self._connection.execute(
            """SELECT source_id, captured_at FROM evidence_records
               WHERE evidence_id = ?""",
            (evidence_id,),
        ).fetchone()
        if row is None:  # pragma: no cover - impossible without concurrent deletion
            raise EvidenceEnvelopeConsistencyError(
                f"Evidence {evidence_id!r} disappeared during consistency validation"
            )

        mismatches: list[str] = []
        if evidence.evidence_id != evidence_id:
            mismatches.append("evidence_id")
        if evidence.source_id != row["source_id"]:
            mismatches.append("source_id")
        if evidence.captured_at.isoformat() != row["captured_at"]:
            mismatches.append("captured_at")

        if mismatches:
            raise EvidenceEnvelopeConsistencyError(
                f"Evidence {evidence_id!r} envelope disagrees with storage columns: "
                + ", ".join(mismatches)
            )
        return evidence
