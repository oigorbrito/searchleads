from __future__ import annotations

from searchleads.domain import CandidateFact, CanonicalFact, Conflict, Provenance

from .sqlite import PersistenceError, SQLiteRepository as _SQLiteRepository


class SemanticReferenceError(PersistenceError):
    """Raised when an existing reference is incompatible with the referring record."""


class SQLiteRepository(_SQLiteRepository):
    """Public repository with semantic checks across persisted fact references."""

    @staticmethod
    def _assert_same_fact_scope(
        *,
        context: str,
        expected_subject_id: str,
        expected_field_name: str,
        referenced: CandidateFact | Provenance,
    ) -> None:
        if referenced.subject_id != expected_subject_id or referenced.field_name != expected_field_name:
            raise SemanticReferenceError(
                f"{context} requires references with matching subject_id and field_name; "
                f"got {referenced.subject_id!r}/{referenced.field_name!r}, expected "
                f"{expected_subject_id!r}/{expected_field_name!r}"
            )

    def _load_candidate(self, candidate_id: str, context: str) -> CandidateFact:
        candidate = self.load(CandidateFact, candidate_id)
        if candidate is None:  # base reference checks run first
            raise SemanticReferenceError(f"{context} candidate reference disappeared: {candidate_id!r}")
        return candidate

    def _load_provenance(self, provenance_id: str, context: str) -> Provenance:
        provenance = self.load(Provenance, provenance_id)
        if provenance is None:  # base reference checks run first
            raise SemanticReferenceError(f"{context} provenance reference disappeared: {provenance_id!r}")
        return provenance

    def _assert_references(self, record: object) -> None:
        super()._assert_references(record)  # type: ignore[arg-type]

        if isinstance(record, Provenance):
            context = f"Provenance {record.provenance_id!r}"
            for candidate_id in record.derived_from_fact_ids:
                candidate = self._load_candidate(candidate_id, context)
                self._assert_same_fact_scope(
                    context=context,
                    expected_subject_id=record.subject_id,
                    expected_field_name=record.field_name,
                    referenced=candidate,
                )
            return

        if isinstance(record, CandidateFact):
            context = f"CandidateFact {record.fact_id!r}"
            provenance = self._load_provenance(record.provenance_id, context)
            self._assert_same_fact_scope(
                context=context,
                expected_subject_id=record.subject_id,
                expected_field_name=record.field_name,
                referenced=provenance,
            )
            return

        if isinstance(record, CanonicalFact):
            context = f"CanonicalFact {record.fact_id!r}"
            for candidate_id in record.candidate_fact_ids:
                candidate = self._load_candidate(candidate_id, context)
                self._assert_same_fact_scope(
                    context=context,
                    expected_subject_id=record.subject_id,
                    expected_field_name=record.field_name,
                    referenced=candidate,
                )
            provenance = self._load_provenance(record.provenance_id, context)
            self._assert_same_fact_scope(
                context=context,
                expected_subject_id=record.subject_id,
                expected_field_name=record.field_name,
                referenced=provenance,
            )
            return

        if isinstance(record, Conflict):
            context = f"Conflict {record.conflict_id!r}"
            for candidate_id in record.candidate_fact_ids:
                candidate = self._load_candidate(candidate_id, context)
                self._assert_same_fact_scope(
                    context=context,
                    expected_subject_id=record.subject_id,
                    expected_field_name=record.field_name,
                    referenced=candidate,
                )
