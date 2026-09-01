from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from searchleads.domain import (
    CandidateFact,
    CanonicalFact,
    Company,
    Conflict,
    ContactPoint,
    Evidence,
    Lead,
    PersonCompanyRelationship,
    PersonIdentity,
    ProfessionalRegistration,
    QualificationDecision,
    RelationshipContactLink,
    Source,
    Statement,
    StatementEvidenceLink,
    Provenance,
)
from searchleads.selective_review import ReviewItem

from .export import _ordered, _primitive

SCHEMA_VERSION = "lead_export_canonical_v1"


@dataclass(frozen=True, slots=True)
class CanonicalLeadExportBundle:
    company: Company
    lead: Lead | None = None
    identities: tuple[PersonIdentity, ...] = ()
    relationships: tuple[PersonCompanyRelationship, ...] = ()
    registrations: tuple[ProfessionalRegistration, ...] = ()
    contacts: tuple[ContactPoint, ...] = ()
    candidate_facts: tuple[CandidateFact, ...] = ()
    canonical_facts: tuple[CanonicalFact, ...] = ()
    conflicts: tuple[Conflict, ...] = ()
    statements: tuple[Statement, ...] = ()
    statement_evidence_links: tuple[StatementEvidenceLink, ...] = ()
    provenances: tuple[Provenance, ...] = ()
    sources: tuple[Source, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    qualification_decisions: tuple[QualificationDecision, ...] = ()
    review_items: tuple[ReviewItem, ...] = ()


def _record_index(records: Iterable[Any], id_attr: str, label: str) -> dict[str, Any]:
    indexed: dict[str, Any] = {}
    for record in records:
        record_id = getattr(record, id_attr)
        if record_id in indexed:
            raise ValueError(f"duplicate {label} id in export: {record_id}")
        indexed[record_id] = record
    return indexed


def _require_subset(values: Iterable[str], available: set[str], context: str) -> None:
    missing = sorted(set(values) - available)
    if missing:
        raise ValueError(f"{context} references records missing from export: {missing}")


def _validate(bundle: CanonicalLeadExportBundle) -> None:
    company_id = bundle.company.company_id
    identities = _record_index(bundle.identities, "person_id", "identity")
    relationships = _record_index(bundle.relationships, "relationship_id", "relationship")
    registrations = _record_index(bundle.registrations, "registration_id", "registration")
    contacts = _record_index(bundle.contacts, "contact_id", "contact")
    candidates = _record_index(bundle.candidate_facts, "fact_id", "candidate fact")
    canonicals = _record_index(bundle.canonical_facts, "fact_id", "canonical fact")
    conflicts = _record_index(bundle.conflicts, "conflict_id", "conflict")
    statements = _record_index(bundle.statements, "statement_id", "statement")
    statement_links = _record_index(bundle.statement_evidence_links, "link_id", "statement evidence link")
    provenances = _record_index(bundle.provenances, "provenance_id", "provenance")
    sources = _record_index(bundle.sources, "source_id", "source")
    evidence = _record_index(bundle.evidence, "evidence_id", "evidence")
    decisions = _record_index(bundle.qualification_decisions, "decision_id", "qualification decision")
    _record_index(bundle.review_items, "review_id", "review item")

    if bundle.lead is not None and bundle.lead.company_id != company_id:
        raise ValueError("lead belongs to another company")

    identity_ids = set(identities)
    relationship_ids = set(relationships)
    evidence_ids = set(evidence)
    source_ids = set(sources)
    provenance_ids = set(provenances)
    candidate_ids = set(candidates)
    decision_ids = set(decisions)
    subject_ids = {company_id, *identity_ids, *relationship_ids}

    for identity in identities.values():
        if not identity.person_id.strip():
            raise ValueError("identity id must not be blank")

    for relationship in relationships.values():
        if relationship.person_id not in identity_ids:
            raise ValueError(f"relationship references missing person identity: {relationship.relationship_id}")
        if relationship.company_id != company_id and relationship.company_id not in subject_ids:
            raise ValueError(f"relationship belongs to another company: {relationship.relationship_id}")
        _require_subset(relationship.evidence_ids, evidence_ids, f"relationship {relationship.relationship_id}")

    for registration in registrations.values():
        if registration.person_id not in identity_ids:
            raise ValueError(f"registration references missing person identity: {registration.registration_id}")
        _require_subset(registration.evidence_ids, evidence_ids, f"registration {registration.registration_id}")

    for contact in contacts.values():
        if contact.owner_id not in subject_ids:
            raise ValueError(f"contact belongs to another subject: {contact.contact_id}")
        _require_subset(contact.discovery_evidence_ids, evidence_ids, f"contact {contact.contact_id} discovery")
        _require_subset(contact.validation_evidence_ids, evidence_ids, f"contact {contact.contact_id} validation")

    for provenance in provenances.values():
        if provenance.subject_id not in subject_ids:
            raise ValueError(f"provenance belongs to another subject: {provenance.provenance_id}")
        _require_subset(provenance.evidence_ids, evidence_ids, f"provenance {provenance.provenance_id}")
        _require_subset(provenance.derived_from_fact_ids, candidate_ids, f"provenance {provenance.provenance_id} derivation")

    for fact in candidates.values():
        if fact.subject_id not in subject_ids:
            raise ValueError(f"candidate fact belongs to another subject: {fact.fact_id}")
        _require_subset(fact.evidence_ids, evidence_ids, f"candidate fact {fact.fact_id}")
        _require_subset((fact.provenance_id,), provenance_ids, f"candidate fact {fact.fact_id}")

    for fact in canonicals.values():
        if fact.subject_id not in subject_ids:
            raise ValueError(f"canonical fact belongs to another subject: {fact.fact_id}")
        _require_subset(fact.candidate_fact_ids, candidate_ids, f"canonical fact {fact.fact_id}")
        _require_subset((fact.provenance_id,), provenance_ids, f"canonical fact {fact.fact_id}")

    for conflict in conflicts.values():
        if conflict.subject_id not in subject_ids:
            raise ValueError(f"conflict belongs to another subject: {conflict.conflict_id}")
        _require_subset(conflict.candidate_fact_ids, candidate_ids, f"conflict {conflict.conflict_id}")

    for statement in statements.values():
        if statement.subject_id not in subject_ids:
            raise ValueError(f"statement belongs to another subject: {statement.statement_id}")
        _require_subset((statement.provenance_id,), provenance_ids, f"statement {statement.statement_id}")

    for link in statement_links.values():
        _require_subset((link.statement_id,), set(statements), f"statement evidence link {link.link_id}")
        _require_subset(link.evidence_ids, evidence_ids, f"statement evidence link {link.link_id}")

    for decision in decisions.values():
        if bundle.lead is not None and decision.lead_id != bundle.lead.lead_id:
            raise ValueError("qualification decision belongs to another lead")
        _require_subset(decision.evidence_ids, evidence_ids, f"qualification decision {decision.decision_id}")

    for item in bundle.review_items:
        _require_subset(item.evidence_ids, evidence_ids, f"review item {item.review_id}")

    for item in evidence.values():
        _require_subset((item.source_id,), source_ids, f"evidence {item.evidence_id}")


def to_canonical_export_dict(bundle: CanonicalLeadExportBundle) -> dict[str, Any]:
    _validate(bundle)
    return {
        "schema_version": SCHEMA_VERSION,
        "company": _primitive(bundle.company),
        "lead": _primitive(bundle.lead),
        "identities": _ordered(bundle.identities, "person_id"),
        "relationships": _ordered(bundle.relationships, "relationship_id"),
        "registrations": _ordered(bundle.registrations, "registration_id"),
        "contacts": _ordered(bundle.contacts, "contact_id"),
        "candidate_facts": _ordered(bundle.candidate_facts, "fact_id"),
        "canonical_facts": _ordered(bundle.canonical_facts, "fact_id"),
        "conflicts": _ordered(bundle.conflicts, "conflict_id"),
        "statements": _ordered(bundle.statements, "statement_id"),
        "statement_evidence_links": _ordered(bundle.statement_evidence_links, "link_id"),
        "provenances": _ordered(bundle.provenances, "provenance_id"),
        "sources": _ordered(bundle.sources, "source_id"),
        "evidence": _ordered(bundle.evidence, "evidence_id"),
        "qualification_decisions": _ordered(bundle.qualification_decisions, "decision_id"),
        "review_items": _ordered(bundle.review_items, "review_id"),
    }


def export_canonical_json(bundle: CanonicalLeadExportBundle) -> str:
    import json

    return json.dumps(
        to_canonical_export_dict(bundle),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


__all__ = [
    "CanonicalLeadExportBundle",
    "SCHEMA_VERSION",
    "export_canonical_json",
    "to_canonical_export_dict",
]
