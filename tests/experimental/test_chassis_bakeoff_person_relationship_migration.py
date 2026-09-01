from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from searchleads.domain import CandidateFact, DecisionClass, Person
from searchleads.person_entity_resolution import person_record_from_observation
from searchleads.qualification import qualify_dental_person


@dataclass(frozen=True, slots=True)
class PersonIdentityCandidate:
    """Experimental identity shape with no organization context."""

    person_id: str
    candidate_fact_ids: tuple[str, ...] = ()
    canonical_fact_ids: tuple[str, ...] = ()
    contact_point_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.person_id.strip():
            raise ValueError("person_id must not be blank")


@dataclass(frozen=True, slots=True)
class PersonCompanyRelationshipCandidate:
    """Experimental SearchLeads relationship with mandatory raw-evidence references."""

    relationship_id: str
    person_id: str
    company_id: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if any(not value.strip() for value in (self.relationship_id, self.person_id, self.company_id)):
            raise ValueError("relationship identity must not be blank")
        if not self.evidence_ids or any(not value.strip() for value in self.evidence_ids):
            raise ValueError("relationship requires non-blank evidence_ids")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("relationship evidence_ids must not contain duplicates")


def split_v1_person(person: Person) -> tuple[PersonIdentityCandidate, PersonCompanyRelationshipCandidate]:
    identity = PersonIdentityCandidate(
        person_id=person.person_id,
        candidate_fact_ids=person.candidate_fact_ids,
        canonical_fact_ids=person.canonical_fact_ids,
        contact_point_ids=person.contact_point_ids,
    )
    relationship = PersonCompanyRelationshipCandidate(
        relationship_id=f"person-company:{person.person_id}:{person.company_id}",
        person_id=person.person_id,
        company_id=person.company_id,
        evidence_ids=person.relationship_evidence_ids,
    )
    return identity, relationship


def v1_compat_person(
    identity: PersonIdentityCandidate,
    relationship: PersonCompanyRelationshipCandidate,
) -> Person:
    if identity.person_id != relationship.person_id:
        raise ValueError("relationship does not belong to identity")
    return Person(
        person_id=identity.person_id,
        company_id=relationship.company_id,
        relationship_evidence_ids=relationship.evidence_ids,
        candidate_fact_ids=identity.candidate_fact_ids,
        canonical_fact_ids=identity.canonical_fact_ids,
        contact_point_ids=identity.contact_point_ids,
    )


def _fact(
    fact_id: str,
    subject_id: str,
    field_name: str,
    value: str,
    evidence_id: str,
) -> CandidateFact:
    return CandidateFact(
        fact_id=fact_id,
        subject_id=subject_id,
        field_name=field_name,
        raw_value=value,
        normalized_value=None,
        evidence_ids=(evidence_id,),
        provenance_id=f"provenance:{fact_id}",
        confidence=None,
        decision_class=DecisionClass.EVIDENCE_BACKED,
        observed_at=datetime(2026, 8, 30, tzinfo=timezone.utc),
    )


def test_v1_person_splits_into_identity_and_relationship_losslessly() -> None:
    original = Person(
        person_id="person:ana-silva",
        company_id="company:clinic-a",
        relationship_evidence_ids=("evidence:relationship:a",),
        candidate_fact_ids=("fact:name", "fact:role"),
        canonical_fact_ids=("canonical:name",),
        contact_point_ids=("contact:email",),
    )

    identity, relationship = split_v1_person(original)
    reconstructed = v1_compat_person(identity, relationship)

    assert reconstructed == original
    assert identity.person_id == original.person_id
    assert not hasattr(identity, "company_id")
    assert relationship.company_id == original.company_id
    assert relationship.evidence_ids == original.relationship_evidence_ids

    print("PERSON_RELATIONSHIP_MIGRATION_ROUNDTRIP_V1")
    print("v1_to_identity_relationship_to_v1_lossless=YES")
    print("company_context_removed_from_identity=YES")
    print("relationship_evidence_preserved=YES")


def test_one_identity_can_supply_two_legacy_company_contexts_without_identity_mutation() -> None:
    identity = PersonIdentityCandidate(person_id="person:ana-silva")
    relationship_a = PersonCompanyRelationshipCandidate(
        "person-company:ana:a",
        identity.person_id,
        "company:a",
        ("evidence:relationship:a",),
    )
    relationship_b = PersonCompanyRelationshipCandidate(
        "person-company:ana:b",
        identity.person_id,
        "company:b",
        ("evidence:relationship:b",),
    )

    compat_a = v1_compat_person(identity, relationship_a)
    compat_b = v1_compat_person(identity, relationship_b)

    assert compat_a.person_id == compat_b.person_id == identity.person_id
    assert compat_a.company_id != compat_b.company_id
    assert relationship_a.relationship_id != relationship_b.relationship_id

    print("PERSON_RELATIONSHIP_MULTI_COMPANY_COMPAT_V1")
    print("identity_records=1")
    print("relationship_records=2")
    print("legacy_company_contexts=2")


def test_dental_qualification_is_behavior_preserving_through_relationship_adapter() -> None:
    original = Person(
        person_id="person:ana-silva",
        company_id="company:clinic-a",
        relationship_evidence_ids=("evidence:relationship:a",),
    )
    identity, relationship = split_v1_person(original)
    adapted = v1_compat_person(identity, relationship)
    facts = (
        _fact(
            "fact:title",
            original.person_id,
            "professional_role_title",
            "Cirurgiã-Dentista",
            "evidence:title",
        ),
        _fact(
            "fact:country",
            original.company_id,
            "country",
            "BR",
            "evidence:country",
        ),
    )

    before = qualify_dental_person(original, candidate_facts=facts)
    after = qualify_dental_person(adapted, candidate_facts=facts)

    assert after == before
    assert after.person_id == identity.person_id
    assert after.company_id == relationship.company_id
    assert set(after.evidence_ids) == {
        "evidence:relationship:a",
        "evidence:title",
        "evidence:country",
    }

    print("PERSON_RELATIONSHIP_QUALIFICATION_COMPAT_V1")
    print("decision_semantics_preserved=YES")
    print("decision_id_preserved=YES")
    print("evidence_set_preserved=YES")


def test_same_identity_can_be_qualified_independently_per_relationship_context() -> None:
    identity = PersonIdentityCandidate(person_id="person:ana-silva")
    relationship_a = PersonCompanyRelationshipCandidate(
        "person-company:ana:a",
        identity.person_id,
        "company:a",
        ("evidence:relationship:a",),
    )
    relationship_b = PersonCompanyRelationshipCandidate(
        "person-company:ana:b",
        identity.person_id,
        "company:b",
        ("evidence:relationship:b",),
    )
    facts = (
        _fact("fact:title", identity.person_id, "professional_role_title", "Cirurgiã-Dentista", "evidence:title"),
        _fact("fact:country:a", "company:a", "country", "BR", "evidence:country:a"),
        _fact("fact:country:b", "company:b", "country", "BR", "evidence:country:b"),
    )

    decision_a = qualify_dental_person(v1_compat_person(identity, relationship_a), candidate_facts=facts)
    decision_b = qualify_dental_person(v1_compat_person(identity, relationship_b), candidate_facts=facts)

    assert decision_a.person_id == decision_b.person_id == identity.person_id
    assert decision_a.company_id == "company:a"
    assert decision_b.company_id == "company:b"
    assert decision_a.decision_id != decision_b.decision_id
    assert "evidence:relationship:a" in decision_a.evidence_ids
    assert "evidence:relationship:b" in decision_b.evidence_ids

    print("PERSON_RELATIONSHIP_CONTEXTUAL_QUALIFICATION_V1")
    print("same_person_identity=YES")
    print("company_specific_decisions=2")
    print("decision_ids_distinct_by_relationship_context=YES")


def test_person_er_can_remain_behavior_compatible_during_migration() -> None:
    original = Person(
        person_id="person:ana-silva",
        company_id="company:clinic-a",
        relationship_evidence_ids=("evidence:relationship:a",),
    )
    identity, relationship = split_v1_person(original)
    adapted = v1_compat_person(identity, relationship)
    facts = (
        _fact("fact:name", original.person_id, "person_name", "Ana Silva", "evidence:name"),
        _fact("fact:role", original.person_id, "professional_role_title", "CFO", "evidence:role"),
    )

    before = person_record_from_observation(original, candidate_facts=facts)
    after = person_record_from_observation(adapted, candidate_facts=facts)

    assert after == before
    assert after.record_id == identity.person_id
    assert after.company_id == relationship.company_id
    assert after.relationship_evidence_ids == relationship.evidence_ids

    print("PERSON_RELATIONSHIP_PERSON_ER_COMPAT_V1")
    print("person_er_record_semantics_preserved=YES")
    print("company_context_can_be_supplied_by_relationship=YES")


def test_migration_candidate_rejects_cross_identity_relationship_adapter() -> None:
    identity = PersonIdentityCandidate(person_id="person:a")
    relationship = PersonCompanyRelationshipCandidate(
        "person-company:b:clinic",
        "person:b",
        "company:clinic",
        ("evidence:relationship",),
    )

    try:
        v1_compat_person(identity, relationship)
    except ValueError as exc:
        assert "does not belong to identity" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("cross-identity relationship must be rejected")
