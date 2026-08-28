from datetime import datetime, timezone

import pytest

from searchleads.domain import CandidateFact, CanonicalFact, Conflict, Evidence, Provenance

NOW = datetime(2026, 8, 28, 21, 20, tzinfo=timezone.utc)


def test_candidate_fact_rejects_duplicate_evidence_ids():
    with pytest.raises(ValueError, match="evidence_ids must not contain duplicates"):
        CandidateFact(
            "fact-1",
            "company-1",
            "name",
            "ACME",
            "acme",
            ("ev-1", "ev-1"),
            "prov-1",
            observed_at=NOW,
        )


def test_canonical_fact_rejects_duplicate_candidate_fact_ids():
    with pytest.raises(ValueError, match="candidate_fact_ids must not contain duplicates"):
        CanonicalFact(
            "canonical-1",
            "company-1",
            "name",
            "ACME",
            ("fact-1", "fact-1"),
            "prov-1",
            "unanimous",
        )


def test_conflict_rejects_blank_or_duplicate_candidate_fact_ids():
    with pytest.raises(ValueError, match="must not contain blanks"):
        Conflict("conflict-blank", "company-1", "name", ("fact-1", ""))
    with pytest.raises(ValueError, match="at least two distinct"):
        Conflict("conflict-duplicate", "company-1", "name", ("fact-1", "fact-1"))


def test_provenance_rejects_duplicate_evidence_and_derived_fact_ids():
    with pytest.raises(ValueError, match="evidence_ids must not contain duplicates"):
        Provenance(
            "prov-evidence",
            "company-1",
            "name",
            ("ev-1", "ev-1"),
            "extract",
            NOW,
        )
    with pytest.raises(ValueError, match="derived_from_fact_ids must not contain duplicates"):
        Provenance(
            "prov-derived",
            "company-1",
            "name",
            ("ev-1",),
            "fusion",
            NOW,
            derived_from_fact_ids=("fact-1", "fact-1"),
        )


def test_valid_reference_sets_remain_supported():
    evidence = Evidence("ev-1", "src-1", "https://example.test", NOW, "raw")
    provenance = Provenance(
        "prov-1",
        "company-1",
        "name",
        (evidence.evidence_id,),
        "extract",
        NOW,
        derived_from_fact_ids=("fact-parent",),
    )
    candidate = CandidateFact(
        "fact-1",
        "company-1",
        "name",
        "ACME",
        "acme",
        (evidence.evidence_id,),
        provenance.provenance_id,
        observed_at=NOW,
    )
    canonical = CanonicalFact(
        "canonical-1",
        "company-1",
        "name",
        "ACME",
        (candidate.fact_id,),
        provenance.provenance_id,
        "unanimous",
    )
    assert canonical.candidate_fact_ids == (candidate.fact_id,)
