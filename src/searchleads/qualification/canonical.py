from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Iterable

from searchleads.domain import (
    CandidateFact,
    CanonicalFact,
    Conflict,
    ContactPoint,
    Lead,
    Person,
    PersonCompanyRelationship,
    PersonIdentity,
    ProfessionalRegistration,
    QualificationStatus,
    RelationshipContactLink,
)

from ..domain.migration import project_legacy_person
from .dental import (
    APPROVED_DENTAL_ICP_POLICY_V1,
    DentalICPPolicyContractV1,
    DentalOfferTrack,
    DentalQualificationDecision,
    materialize_lead,
    qualify_dental_person,
)


def _rebase_fact_subjects(
    facts: Iterable[CandidateFact | CanonicalFact],
    *,
    identity: PersonIdentity,
    relationship: PersonCompanyRelationship,
) -> tuple[CandidateFact | CanonicalFact, ...]:
    rebased: list[CandidateFact | CanonicalFact] = []
    for fact in facts:
        if fact.subject_id == relationship.relationship_id:
            rebased.append(replace(fact, subject_id=identity.person_id))
            continue
        rebased.append(fact)
    return tuple(rebased)


def _relationship_contacts(
    contacts: Iterable[ContactPoint],
    links: Iterable[RelationshipContactLink],
    *,
    relationship: PersonCompanyRelationship,
    identity: PersonIdentity,
) -> tuple[ContactPoint, ...]:
    by_id = {contact.contact_id: contact for contact in contacts}
    selected: list[ContactPoint] = []
    for link in links:
        if link.relationship_id != relationship.relationship_id:
            continue
        contact = by_id.get(link.contact_id)
        if contact is None:
            continue
        selected.append(replace(contact, owner_id=identity.person_id))
    return tuple(selected)


def qualify_dental_relationship(
    identity: PersonIdentity,
    relationship: PersonCompanyRelationship,
    *,
    relationship_candidate_facts: Iterable[CandidateFact] = (),
    company_candidate_facts: Iterable[CandidateFact] = (),
    canonical_facts: Iterable[CanonicalFact] = (),
    conflicts: Iterable[Conflict] = (),
    contacts: Iterable[ContactPoint] = (),
    relationship_contact_links: Iterable[RelationshipContactLink] = (),
    registrations: Iterable[ProfessionalRegistration] = (),
    offer_track: DentalOfferTrack = DentalOfferTrack.CEOF_SPECIALIZATION,
    require_validated_contact: bool = False,
    policy: DentalICPPolicyContractV1 = APPROVED_DENTAL_ICP_POLICY_V1,
) -> DentalQualificationDecision:
    """Qualify a person through a company-scoped relationship.

    The canonical adapter keeps relationship-scoped facts and contacts explicit
    while reusing the proven dental policy engine as the decision kernel.
    """

    if identity.person_id != relationship.person_id:
        raise ValueError("identity and relationship must describe the same person")

    rebased_relationship_facts = _rebase_fact_subjects(
        relationship_candidate_facts,
        identity=identity,
        relationship=relationship,
    )
    rebased_canonical_facts = _rebase_fact_subjects(
        canonical_facts,
        identity=identity,
        relationship=relationship,
    )
    relationship_contacts = _relationship_contacts(
        contacts,
        relationship_contact_links,
        relationship=relationship,
        identity=identity,
    )

    relationship_evidence_ids = tuple(
        dict.fromkeys(
            (
                *relationship.evidence_ids,
                *(
                    evidence_id
                    for registration in registrations
                    if registration.person_id == identity.person_id
                    for evidence_id in registration.evidence_ids
                ),
            )
        )
    )
    legacy_person = project_legacy_person(
        replace(identity),  # identity is immutable, but replace keeps the adapter explicit.
        replace(relationship, evidence_ids=relationship_evidence_ids),
        candidate_fact_ids=tuple(
            fact.fact_id for fact in rebased_relationship_facts if isinstance(fact, CandidateFact)
        ),
        canonical_fact_ids=tuple(
            fact.fact_id for fact in rebased_canonical_facts if isinstance(fact, CanonicalFact)
        ),
        contact_point_ids=tuple(contact.contact_id for contact in relationship_contacts),
    )

    return qualify_dental_person(
        legacy_person,
        candidate_facts=tuple(
            fact for fact in (*rebased_relationship_facts, *company_candidate_facts) if isinstance(fact, CandidateFact)
        ),
        canonical_facts=tuple(item for item in rebased_canonical_facts if isinstance(item, CanonicalFact)),
        conflicts=tuple(conflicts),
        contacts=relationship_contacts,
        offer_track=offer_track,
        require_validated_contact=require_validated_contact,
        policy=policy,
    )


def materialize_relationship_lead(
    decision: DentalQualificationDecision,
    *,
    created_at: datetime,
    lead_id: str | None = None,
) -> Lead:
    return materialize_lead(decision, created_at=created_at, lead_id=lead_id)


__all__ = [
    "materialize_relationship_lead",
    "qualify_dental_relationship",
]
