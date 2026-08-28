from datetime import datetime, timezone

import pytest

from searchleads.domain import (
    CandidateFact,
    CanonicalFact,
    Conflict,
    Evidence,
    Provenance,
    Source,
)
from searchleads.persistence import SQLiteRepository, SemanticReferenceError

NOW = datetime(2026, 8, 28, 23, 10, tzinfo=timezone.utc)


def seed(repo: SQLiteRepository) -> None:
    repo.save(Source("src", "registry", "https://example.test"))
    repo.save(Evidence("ev", "src", "https://example.test/a", NOW, "raw"))


def provenance(pid: str, subject: str, field: str, *, derived: tuple[str, ...] = ()) -> Provenance:
    return Provenance(pid, subject, field, ("ev",), "test", NOW, derived_from_fact_ids=derived)


def candidate(fid: str, subject: str, field: str, pid: str) -> CandidateFact:
    return CandidateFact(fid, subject, field, "raw", "normalized", ("ev",), pid, observed_at=NOW)


def test_candidate_fact_rejects_provenance_from_different_subject_or_field() -> None:
    with SQLiteRepository() as repo:
        seed(repo)
        repo.save(provenance("prov-subject", "company-other", "name"))
        with pytest.raises(SemanticReferenceError, match="matching subject_id and field_name"):
            repo.save(candidate("fact-subject", "company", "name", "prov-subject"))

        repo.save(provenance("prov-field", "company", "domain"))
        with pytest.raises(SemanticReferenceError, match="matching subject_id and field_name"):
            repo.save(candidate("fact-field", "company", "name", "prov-field"))


def test_derived_provenance_rejects_candidate_from_different_scope() -> None:
    with SQLiteRepository() as repo:
        seed(repo)
        repo.save(provenance("prov-parent", "company", "domain"))
        repo.save(candidate("parent", "company", "domain", "prov-parent"))

        with pytest.raises(SemanticReferenceError, match="matching subject_id and field_name"):
            repo.save(provenance("prov-fusion", "company", "name", derived=("parent",)))


def test_canonical_fact_rejects_candidate_or_provenance_from_different_scope() -> None:
    with SQLiteRepository() as repo:
        seed(repo)
        repo.save(provenance("prov-domain", "company", "domain"))
        repo.save(candidate("domain-fact", "company", "domain", "prov-domain"))
        repo.save(provenance("prov-name", "company", "name"))

        with pytest.raises(SemanticReferenceError, match="matching subject_id and field_name"):
            repo.save(
                CanonicalFact(
                    "canonical-wrong-candidate",
                    "company",
                    "name",
                    "Acme",
                    ("domain-fact",),
                    "prov-name",
                    "unanimous",
                )
            )

        repo.save(candidate("name-fact", "company", "name", "prov-name"))
        with pytest.raises(SemanticReferenceError, match="matching subject_id and field_name"):
            repo.save(
                CanonicalFact(
                    "canonical-wrong-provenance",
                    "company",
                    "name",
                    "Acme",
                    ("name-fact",),
                    "prov-domain",
                    "unanimous",
                )
            )


def test_conflict_rejects_candidates_from_different_scope() -> None:
    with SQLiteRepository() as repo:
        seed(repo)
        repo.save(provenance("prov-name", "company", "name"))
        repo.save(provenance("prov-domain", "company", "domain"))
        repo.save(candidate("name-fact", "company", "name", "prov-name"))
        repo.save(candidate("domain-fact", "company", "domain", "prov-domain"))

        with pytest.raises(SemanticReferenceError, match="matching subject_id and field_name"):
            repo.save(Conflict("conflict", "company", "name", ("name-fact", "domain-fact")))


def test_valid_fact_lineage_persists_and_roundtrips() -> None:
    with SQLiteRepository() as repo:
        seed(repo)
        repo.save(provenance("prov-a", "company", "name"))
        repo.save(provenance("prov-b", "company", "name"))
        first = candidate("fact-a", "company", "name", "prov-a")
        second = candidate("fact-b", "company", "name", "prov-b")
        repo.save(first)
        repo.save(second)
        fusion = provenance("prov-fusion", "company", "name", derived=("fact-a", "fact-b"))
        repo.save(fusion)
        canonical = CanonicalFact(
            "canonical",
            "company",
            "name",
            "Acme",
            ("fact-a", "fact-b"),
            "prov-fusion",
            "unanimous",
        )
        repo.save(canonical)

        assert repo.load(CandidateFact, "fact-a") == first
        assert repo.load(Provenance, "prov-fusion") == fusion
        assert repo.load(CanonicalFact, "canonical") == canonical
