from __future__ import annotations

from datetime import datetime, timezone

import pytest

from searchleads.domain import (
    CandidateFact,
    CanonicalFact,
    Company,
    Conflict,
    ConflictStatus,
    ContactKind,
    ContactPoint,
    ContactStatus,
    DecisionClass,
    Evidence,
    Lead,
    LeadStage,
    Person,
    Provenance,
    QualificationStatus,
    Source,
)

NOW = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)


def test_source_represents_stable_origin() -> None:
    source = Source("src-1", "website", "https://acme.example", "ACME")
    assert source.source_type == "website"


@pytest.mark.parametrize("field,value", [("source_id", ""), ("source_type", ""), ("locator", "")])
def test_source_rejects_blank_required_fields(field: str, value: str) -> None:
    kwargs = dict(source_id="src-1", source_type="website", locator="https://acme.example")
    kwargs[field] = value
    with pytest.raises(ValueError):
        Source(**kwargs)


def test_evidence_captures_source_locator_and_time() -> None:
    evidence = Evidence("ev-1", "src-1", "https://acme.example/contact", NOW, "email: hi@acme.example")
    assert evidence.source_id == "src-1"
    assert evidence.captured_at == NOW


def test_evidence_requires_timezone_aware_capture_time() -> None:
    with pytest.raises(ValueError):
        Evidence("ev-1", "src-1", "x", datetime(2026, 8, 24, 12, 0))


def test_provenance_is_per_fact_and_requires_evidence() -> None:
    provenance = Provenance("prov-1", "company-1", "domain", ("ev-1",), "extract")
    assert provenance.field_name == "domain"
    with pytest.raises(ValueError):
        Provenance("prov-2", "company-1", "domain", (), "extract")


def test_candidate_fact_preserves_raw_and_normalized_values() -> None:
    fact = CandidateFact(
        "fact-1", "company-1", "name", " ACME LTDA. ", "acme ltda", ("ev-1",), "prov-1"
    )
    assert fact.raw_value != fact.normalized_value


def test_candidate_fact_without_evidence_is_rejected() -> None:
    with pytest.raises(ValueError):
        CandidateFact("fact-1", "company-1", "name", "ACME", "acme", (), "prov-1")


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_candidate_fact_rejects_confidence_outside_unit_interval(confidence: float) -> None:
    with pytest.raises(ValueError):
        CandidateFact("fact-1", "company-1", "name", "ACME", "acme", ("ev-1",), "prov-1", confidence)


def test_candidate_fact_accepts_documented_decision_classification() -> None:
    fact = CandidateFact(
        "fact-1",
        "company-1",
        "domain",
        "acme.example",
        "acme.example",
        ("ev-1",),
        "prov-1",
        decision_class=DecisionClass.LOCALLY_VERIFIED,
    )
    assert fact.decision_class is DecisionClass.LOCALLY_VERIFIED


def test_canonical_fact_requires_candidates_and_resolution_method() -> None:
    with pytest.raises(ValueError):
        CanonicalFact("canon-1", "company-1", "name", "ACME", (), "prov-c", "manual")
    with pytest.raises(ValueError):
        CanonicalFact("canon-1", "company-1", "name", "ACME", ("fact-1",), "prov-c", "")


def test_canonical_fact_can_link_multiple_candidates() -> None:
    fact = CanonicalFact(
        "canon-1", "company-1", "name", "ACME", ("fact-1", "fact-2"), "prov-c", "source agreement"
    )
    assert len(fact.candidate_fact_ids) == 2


def test_conflict_requires_two_distinct_candidates() -> None:
    with pytest.raises(ValueError):
        Conflict("conf-1", "company-1", "phone", ("fact-1",))
    with pytest.raises(ValueError):
        Conflict("conf-1", "company-1", "phone", ("fact-1", "fact-1"))


def test_open_conflict_is_representable_without_forced_resolution() -> None:
    conflict = Conflict("conf-1", "company-1", "phone", ("fact-1", "fact-2"))
    assert conflict.status is ConflictStatus.OPEN
    assert conflict.selected_fact_id is None


def test_resolved_conflict_requires_selected_candidate() -> None:
    with pytest.raises(ValueError):
        Conflict("conf-1", "company-1", "phone", ("fact-1", "fact-2"), ConflictStatus.RESOLVED)


def test_resolved_conflict_selection_must_be_member() -> None:
    with pytest.raises(ValueError):
        Conflict(
            "conf-1",
            "company-1",
            "phone",
            ("fact-1", "fact-2"),
            ConflictStatus.RESOLVED,
            "fact-3",
        )


def test_company_is_not_a_lead() -> None:
    company = Company("company-1")
    lead = Lead("lead-1", company.company_id)
    assert company.company_id == lead.company_id
    assert company != lead
    assert lead.stage is LeadStage.CANDIDATE


def test_company_can_hold_fact_person_and_contact_references() -> None:
    company = Company("company-1", ("f1",), ("c1",), ("p1",), ("cp1",))
    assert company.canonical_fact_ids == ("c1",)


def test_person_requires_company_relationship_evidence() -> None:
    with pytest.raises(ValueError):
        Person("person-1", "company-1", ())


def test_person_with_relationship_evidence_is_representable() -> None:
    person = Person("person-1", "company-1", ("ev-rel",))
    assert person.company_id == "company-1"


def test_contact_defaults_to_discovered_not_validated() -> None:
    contact = ContactPoint("contact-1", "company-1", ContactKind.EMAIL, "hello@acme.example", ("ev-1",))
    assert contact.status is ContactStatus.DISCOVERED
    assert contact.validation_evidence_ids == ()


def test_contact_requires_discovery_evidence() -> None:
    with pytest.raises(ValueError):
        ContactPoint("contact-1", "company-1", ContactKind.EMAIL, "hello@acme.example", ())


@pytest.mark.parametrize("status", [ContactStatus.VALIDATED, ContactStatus.INVALID, ContactStatus.STALE])
def test_assessed_contact_requires_validation_evidence(status: ContactStatus) -> None:
    with pytest.raises(ValueError):
        ContactPoint(
            "contact-1",
            "company-1",
            ContactKind.EMAIL,
            "hello@acme.example",
            ("ev-1",),
            status=status,
            validated_at=NOW,
        )


@pytest.mark.parametrize("status", [ContactStatus.VALIDATED, ContactStatus.INVALID, ContactStatus.STALE])
def test_assessed_contact_requires_validation_time(status: ContactStatus) -> None:
    with pytest.raises(ValueError):
        ContactPoint(
            "contact-1",
            "company-1",
            ContactKind.EMAIL,
            "hello@acme.example",
            ("ev-1",),
            status=status,
            validation_evidence_ids=("ev-validation",),
        )


def test_validated_contact_is_representable_with_validation_evidence() -> None:
    contact = ContactPoint(
        "contact-1",
        "company-1",
        ContactKind.EMAIL,
        "hello@acme.example",
        ("ev-1",),
        status=ContactStatus.VALIDATED,
        validation_evidence_ids=("ev-validation",),
        validated_at=NOW,
    )
    assert contact.status is ContactStatus.VALIDATED


def test_lead_defaults_to_unknown_qualification_without_icp() -> None:
    lead = Lead("lead-1", "company-1")
    assert lead.qualification_status is QualificationStatus.UNKNOWN
    assert lead.qualification_reasons == ()


def test_qualified_lead_stage_requires_qualified_status() -> None:
    with pytest.raises(ValueError):
        Lead("lead-1", "company-1", stage=LeadStage.QUALIFIED)


def test_disqualified_lead_stage_requires_not_qualified_status() -> None:
    with pytest.raises(ValueError):
        Lead("lead-1", "company-1", stage=LeadStage.DISQUALIFIED)


def test_consistent_qualified_lead_is_representable() -> None:
    lead = Lead(
        "lead-1",
        "company-1",
        stage=LeadStage.QUALIFIED,
        qualification_status=QualificationStatus.QUALIFIED,
        qualification_reasons=("future ICP rule",),
    )
    assert lead.stage is LeadStage.QUALIFIED


def test_end_to_end_minimal_fact_provenance_chain_is_representable() -> None:
    source = Source("src-1", "website", "https://acme.example")
    evidence = Evidence("ev-1", source.source_id, "https://acme.example/about", NOW, "ACME Tecnologia")
    provenance = Provenance("prov-1", "company-1", "name", (evidence.evidence_id,), "structured-extraction")
    candidate = CandidateFact(
        "fact-1",
        "company-1",
        "name",
        "ACME Tecnologia",
        "acme tecnologia",
        (evidence.evidence_id,),
        provenance.provenance_id,
    )
    canonical = CanonicalFact(
        "canon-1",
        "company-1",
        "name",
        "ACME Tecnologia",
        (candidate.fact_id,),
        provenance.provenance_id,
        "single-source provisional selection",
        DecisionClass.ENGINEERING_CHOICE,
    )
    company = Company("company-1", (candidate.fact_id,), (canonical.fact_id,))
    assert company.canonical_fact_ids == ("canon-1",)


def test_multisource_conflict_chain_is_representable() -> None:
    conflict = Conflict("conf-1", "company-1", "industry", ("fact-source-a", "fact-source-b"))
    assert conflict.status is ConflictStatus.OPEN


def test_company_rejects_blank_id() -> None:
    with pytest.raises(ValueError):
        Company(" ")


@pytest.mark.parametrize(
    "person_id,company_id,evidence",
    [("", "company-1", ("ev",)), ("person-1", "", ("ev",)), ("person-1", "company-1", ("",))],
)
def test_person_rejects_blank_identity_or_relationship_refs(person_id: str, company_id: str, evidence: tuple[str, ...]) -> None:
    with pytest.raises(ValueError):
        Person(person_id, company_id, evidence)


@pytest.mark.parametrize(
    "contact_id,owner_id,value,evidence,discovered_at",
    [
        ("", "company-1", "a@b.com", ("ev",), NOW),
        ("contact-1", "", "a@b.com", ("ev",), NOW),
        ("contact-1", "company-1", "", ("ev",), NOW),
        ("contact-1", "company-1", "a@b.com", ("",), NOW),
        ("contact-1", "company-1", "a@b.com", ("ev",), datetime(2026, 8, 24, 12, 0)),
    ],
)
def test_contact_rejects_invalid_identity_evidence_or_time(
    contact_id: str,
    owner_id: str,
    value: str,
    evidence: tuple[str, ...],
    discovered_at: datetime,
) -> None:
    with pytest.raises(ValueError):
        ContactPoint(contact_id, owner_id, ContactKind.EMAIL, value, evidence, discovered_at=discovered_at)


def test_contact_rejects_naive_validation_time() -> None:
    with pytest.raises(ValueError):
        ContactPoint(
            "contact-1",
            "company-1",
            ContactKind.EMAIL,
            "a@b.com",
            ("ev",),
            status=ContactStatus.VALIDATED,
            validation_evidence_ids=("ev-v",),
            validated_at=datetime(2026, 8, 24, 12, 0),
        )


@pytest.mark.parametrize(
    "lead_id,company_id,created_at",
    [
        ("", "company-1", NOW),
        ("lead-1", "", NOW),
        ("lead-1", "company-1", datetime(2026, 8, 24, 12, 0)),
    ],
)
def test_lead_rejects_blank_ids_or_naive_time(lead_id: str, company_id: str, created_at: datetime) -> None:
    with pytest.raises(ValueError):
        Lead(lead_id, company_id, created_at=created_at)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"fact_id": ""},
        {"subject_id": ""},
        {"field_name": ""},
        {"evidence_ids": ("",)},
        {"provenance_id": ""},
        {"observed_at": datetime(2026, 8, 24, 12, 0)},
    ],
)
def test_candidate_fact_rejects_invalid_identity_provenance_or_time(kwargs: dict[str, object]) -> None:
    values = dict(
        fact_id="fact-1",
        subject_id="company-1",
        field_name="name",
        raw_value="ACME",
        normalized_value="acme",
        evidence_ids=("ev-1",),
        provenance_id="prov-1",
        observed_at=NOW,
    )
    values.update(kwargs)
    with pytest.raises(ValueError):
        CandidateFact(**values)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"fact_id": ""},
        {"subject_id": ""},
        {"field_name": ""},
        {"candidate_fact_ids": ("",)},
        {"provenance_id": ""},
    ],
)
def test_canonical_fact_rejects_invalid_identity_or_references(kwargs: dict[str, object]) -> None:
    values = dict(
        fact_id="canon-1",
        subject_id="company-1",
        field_name="name",
        value="ACME",
        candidate_fact_ids=("fact-1",),
        provenance_id="prov-1",
        resolution_method="manual",
    )
    values.update(kwargs)
    with pytest.raises(ValueError):
        CanonicalFact(**values)


@pytest.mark.parametrize("kwargs", [{"conflict_id": ""}, {"subject_id": ""}, {"field_name": ""}])
def test_conflict_rejects_blank_identity_fields(kwargs: dict[str, object]) -> None:
    values = dict(
        conflict_id="conf-1",
        subject_id="company-1",
        field_name="name",
        candidate_fact_ids=("fact-1", "fact-2"),
    )
    values.update(kwargs)
    with pytest.raises(ValueError):
        Conflict(**values)


@pytest.mark.parametrize(
    "evidence_id,source_id,locator",
    [("", "src", "x"), ("ev", "", "x"), ("ev", "src", "")],
)
def test_evidence_rejects_blank_identity_fields(evidence_id: str, source_id: str, locator: str) -> None:
    with pytest.raises(ValueError):
        Evidence(evidence_id, source_id, locator, NOW)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"provenance_id": ""},
        {"subject_id": ""},
        {"field_name": ""},
        {"evidence_ids": ("",)},
        {"activity": ""},
        {"generated_at": datetime(2026, 8, 24, 12, 0)},
    ],
)
def test_provenance_rejects_invalid_identity_evidence_activity_or_time(kwargs: dict[str, object]) -> None:
    values = dict(
        provenance_id="prov-1",
        subject_id="company-1",
        field_name="name",
        evidence_ids=("ev-1",),
        activity="extract",
        generated_at=NOW,
    )
    values.update(kwargs)
    with pytest.raises(ValueError):
        Provenance(**values)
