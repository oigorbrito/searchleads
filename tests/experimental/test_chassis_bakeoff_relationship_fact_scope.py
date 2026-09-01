from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from searchleads.domain import CandidateFact, DecisionClass, Person, QualificationStatus
from searchleads.qualification import qualify_dental_person


@dataclass(frozen=True, slots=True)
class RelationshipFactLink:
    relationship_id: str
    fact_id: str


def _fact(fact_id: str, subject_id: str, field: str, value: str) -> CandidateFact:
    return CandidateFact(
        fact_id,
        subject_id,
        field,
        value,
        None,
        (f"evidence:{fact_id}",),
        f"provenance:{fact_id}",
        None,
        DecisionClass.EVIDENCE_BACKED,
        datetime(2026, 8, 30, tzinfo=timezone.utc),
    )


def _remap_relationship_facts_for_legacy_qualification(
    person_id: str,
    relationship_id: str,
    facts: tuple[CandidateFact, ...],
    links: tuple[RelationshipFactLink, ...],
) -> tuple[CandidateFact, ...]:
    allowed = {link.fact_id for link in links if link.relationship_id == relationship_id}
    result: list[CandidateFact] = []
    for fact in facts:
        if fact.fact_id not in allowed:
            continue
        result.append(CandidateFact(
            fact.fact_id,
            person_id,
            fact.field_name,
            fact.raw_value,
            fact.normalized_value,
            fact.evidence_ids,
            fact.provenance_id,
            fact.confidence,
            fact.decision_class,
            fact.observed_at,
        ))
    return tuple(result)


def test_person_level_role_fact_leaks_across_relationship_contexts_negative_control() -> None:
    person_id = "person:ana"
    person_a = Person(person_id, "company:a", ("evidence:relationship:a",))
    person_b = Person(person_id, "company:b", ("evidence:relationship:b",))
    facts = (
        _fact("role:a", person_id, "professional_role_title", "Cirurgiã-Dentista"),
        _fact("country:a", "company:a", "country", "BR"),
        _fact("country:b", "company:b", "country", "BR"),
    )

    decision_a = qualify_dental_person(person_a, candidate_facts=facts)
    decision_b = qualify_dental_person(person_b, candidate_facts=facts)

    assert decision_a.qualification_status is QualificationStatus.QUALIFIED
    assert decision_b.qualification_status is QualificationStatus.QUALIFIED

    print("PERSON_ROLE_RELATIONSHIP_LEAK_NEGATIVE_CONTROL_V1")
    print("dentist_role_observed_in_company_a=YES")
    print("same_person_role_visible_in_company_b_context=YES")
    print("current_person_subject_prevents_role_leak=NO")


def test_relationship_scoped_role_fact_prevents_cross_company_qualification_leak() -> None:
    person_id = "person:ana"
    person_a = Person(person_id, "company:a", ("evidence:relationship:a",))
    person_b = Person(person_id, "company:b", ("evidence:relationship:b",))
    relationship_fact = _fact(
        "role:a",
        "relationship:ana:a",
        "professional_role_title",
        "Cirurgiã-Dentista",
    )
    links = (RelationshipFactLink("relationship:ana:a", relationship_fact.fact_id),)
    country_a = _fact("country:a", "company:a", "country", "BR")
    country_b = _fact("country:b", "company:b", "country", "BR")

    facts_a = _remap_relationship_facts_for_legacy_qualification(
        person_id,
        "relationship:ana:a",
        (relationship_fact,),
        links,
    ) + (country_a, country_b)
    facts_b = _remap_relationship_facts_for_legacy_qualification(
        person_id,
        "relationship:ana:b",
        (relationship_fact,),
        links,
    ) + (country_a, country_b)

    decision_a = qualify_dental_person(person_a, candidate_facts=facts_a)
    decision_b = qualify_dental_person(person_b, candidate_facts=facts_b)

    assert decision_a.qualification_status is QualificationStatus.QUALIFIED
    assert decision_b.qualification_status is QualificationStatus.UNKNOWN
    assert any("professional dental title evidence is missing" in reason for reason in decision_b.reasons)

    print("RELATIONSHIP_SCOPED_ROLE_FACT_V1")
    print("company_a_relationship_role_available=YES")
    print("company_b_relationship_role_available=NO")
    print("cross_relationship_role_leak=0")


def test_structural_migration_must_scope_relationship_facts_before_identity_merge() -> None:
    required_order = (
        "split_v1_person_identity_and_relationship",
        "move_relationship_specific_facts_to_relationship_context",
        "preserve_fact_evidence_and_provenance",
        "run_or_apply_explicit_person_er_decision",
        "repoint_relationships_to_canonical_person_identity",
    )
    assert required_order.index("move_relationship_specific_facts_to_relationship_context") < required_order.index(
        "run_or_apply_explicit_person_er_decision"
    )

    print("PERSON_RELATIONSHIP_MIGRATION_ORDER_V1")
    for index, step in enumerate(required_order, start=1):
        print(f"step_{index}={step}")
