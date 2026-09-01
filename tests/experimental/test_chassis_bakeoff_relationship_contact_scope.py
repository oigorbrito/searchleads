from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from searchleads.domain import (
    CandidateFact,
    ContactKind,
    ContactPoint,
    ContactStatus,
    DecisionClass,
    Person,
    QualificationStatus,
)
from searchleads.qualification import qualify_dental_person


@dataclass(frozen=True, slots=True)
class RelationshipContactLink:
    relationship_id: str
    contact_id: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.relationship_id.strip() or not self.contact_id.strip():
            raise ValueError("relationship/contact identity must not be blank")
        if not self.evidence_ids:
            raise ValueError("relationship contact link requires evidence")


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


def _validated_person_contact(person_id: str) -> ContactPoint:
    return ContactPoint(
        contact_id="contact:ana:company-a-email",
        owner_id=person_id,
        kind=ContactKind.EMAIL,
        value="ana@company-a.example",
        discovery_evidence_ids=("evidence:contact-discovery:a",),
        status=ContactStatus.VALIDATED,
        discovered_at=datetime(2026, 8, 29, tzinfo=timezone.utc),
        validation_evidence_ids=("evidence:contact-validation:a",),
        validated_at=datetime(2026, 8, 30, tzinfo=timezone.utc),
    )


def _facts(person_id: str) -> tuple[CandidateFact, ...]:
    return (
        _fact("title", person_id, "professional_role_title", "Cirurgiã-Dentista"),
        _fact("country-a", "company:a", "country", "BR"),
        _fact("country-b", "company:b", "country", "BR"),
    )


def _contacts_for_relationship(
    contacts: tuple[ContactPoint, ...],
    links: tuple[RelationshipContactLink, ...],
    relationship_id: str,
) -> tuple[ContactPoint, ...]:
    allowed = {link.contact_id for link in links if link.relationship_id == relationship_id}
    return tuple(contact for contact in contacts if contact.contact_id in allowed)


def test_current_person_owned_contact_leaks_across_two_relationship_contexts_negative_control() -> None:
    person_id = "person:ana"
    person_a = Person(person_id, "company:a", ("evidence:relationship:a",))
    person_b = Person(person_id, "company:b", ("evidence:relationship:b",))
    contact = _validated_person_contact(person_id)
    facts = _facts(person_id)

    decision_a = qualify_dental_person(
        person_a,
        candidate_facts=facts,
        contacts=(contact,),
        require_validated_contact=True,
    )
    decision_b = qualify_dental_person(
        person_b,
        candidate_facts=facts,
        contacts=(contact,),
        require_validated_contact=True,
    )

    assert decision_a.qualification_status is QualificationStatus.QUALIFIED
    assert decision_b.qualification_status is QualificationStatus.QUALIFIED
    assert contact.contact_id in decision_a.contact_ids
    assert contact.contact_id in decision_b.contact_ids

    print("PERSON_CONTACT_RELATIONSHIP_LEAK_NEGATIVE_CONTROL_V1")
    print("contact_validated_for_company_a=YES")
    print("same_person_contact_seen_in_company_b_context=YES")
    print("current_owner_model_prevents_cross_relationship_leak=NO")


def test_relationship_contact_link_prevents_cross_company_contact_gate_leakage() -> None:
    person_id = "person:ana"
    person_a = Person(person_id, "company:a", ("evidence:relationship:a",))
    person_b = Person(person_id, "company:b", ("evidence:relationship:b",))
    contact = _validated_person_contact(person_id)
    facts = _facts(person_id)
    link_a = RelationshipContactLink(
        "relationship:ana:a",
        contact.contact_id,
        ("evidence:contact-association:a",),
    )

    contacts_a = _contacts_for_relationship((contact,), (link_a,), "relationship:ana:a")
    contacts_b = _contacts_for_relationship((contact,), (link_a,), "relationship:ana:b")

    decision_a = qualify_dental_person(
        person_a,
        candidate_facts=facts,
        contacts=contacts_a,
        require_validated_contact=True,
    )
    decision_b = qualify_dental_person(
        person_b,
        candidate_facts=facts,
        contacts=contacts_b,
        require_validated_contact=True,
    )

    assert decision_a.qualification_status is QualificationStatus.QUALIFIED
    assert decision_b.qualification_status is QualificationStatus.NOT_QUALIFIED
    assert decision_a.contact_ids == (contact.contact_id,)
    assert decision_b.contact_ids == ()
    assert any("validated professional contact" in reason for reason in decision_b.reasons)

    print("RELATIONSHIP_SCOPED_CONTACT_GATE_V1")
    print("company_a_relationship_contact_gate=PASS")
    print("company_b_relationship_contact_gate=BLOCKED")
    print("cross_relationship_contact_leak=0")


def test_relationship_contact_association_is_evidence_backed() -> None:
    try:
        RelationshipContactLink("relationship:ana:a", "contact:a", ())
    except ValueError as exc:
        assert "requires evidence" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("relationship contact link without evidence must be rejected")
