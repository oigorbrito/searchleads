from __future__ import annotations

from collections.abc import Iterable

from .entities import Company, Person, PersonCompanyRelationship, PersonIdentity

__all__ = [
    "project_company_person_ids",
    "project_legacy_person",
    "relationship_id_for",
    "split_legacy_person",
]


def relationship_id_for(person_id: str, company_id: str) -> str:
    return f"person-company:{person_id}:{company_id}"


def split_legacy_person(person: Person) -> tuple[PersonIdentity, PersonCompanyRelationship]:
    """Project the legacy Person snapshot into canonical identity and relationship records."""

    identity = PersonIdentity(person.person_id)
    relationship = PersonCompanyRelationship(
        relationship_id_for(person.person_id, person.company_id),
        person.person_id,
        person.company_id,
        person.relationship_evidence_ids,
    )
    return identity, relationship


def project_legacy_person(
    identity: PersonIdentity,
    relationship: PersonCompanyRelationship,
    *,
    candidate_fact_ids: tuple[str, ...] = (),
    canonical_fact_ids: tuple[str, ...] = (),
    contact_point_ids: tuple[str, ...] = (),
) -> Person:
    """Temporary adapter from canonical relationship records back to the legacy Person snapshot."""

    if identity.person_id != relationship.person_id:
        raise ValueError("identity and relationship must describe the same person")
    return Person(
        identity.person_id,
        relationship.company_id,
        relationship.evidence_ids,
        candidate_fact_ids,
        canonical_fact_ids,
        contact_point_ids,
    )


def project_company_person_ids(
    company: Company,
    relationships: Iterable[PersonCompanyRelationship],
) -> tuple[str, ...]:
    """Compute a legacy-compatible person_id snapshot from first-class relationships."""

    return tuple(
        sorted(
            {
                relationship.person_id
                for relationship in relationships
                if relationship.company_id == company.company_id
            }
        )
    )
