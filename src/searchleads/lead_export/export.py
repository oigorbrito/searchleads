"""Deterministic, integrity-checked export boundary for LEADS_EXPORT_V1."""
from __future__ import annotations

import csv
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from enum import Enum
import io
import json
import math
from collections.abc import Mapping
from typing import Any, Iterable

from searchleads.domain import (
    CandidateFact, CanonicalFact, Company, Conflict, ContactPoint, Evidence,
    Lead, Person, Provenance, Source,
)
from searchleads.selective_review import ReviewItem

SCHEMA_VERSION = "leads_export_v1"


@dataclass(frozen=True, slots=True)
class LeadExportBundle:
    company: Company
    lead: Lead | None = None
    people: tuple[Person, ...] = ()
    contacts: tuple[ContactPoint, ...] = ()
    candidate_facts: tuple[CandidateFact, ...] = ()
    canonical_facts: tuple[CanonicalFact, ...] = ()
    conflicts: tuple[Conflict, ...] = ()
    provenances: tuple[Provenance, ...] = ()
    sources: tuple[Source, ...] = ()
    evidence: tuple[Evidence, ...] = ()
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


def _validate(bundle: LeadExportBundle) -> None:
    company_id = bundle.company.company_id
    people = _record_index(bundle.people, "person_id", "person")
    contacts = _record_index(bundle.contacts, "contact_id", "contact")
    candidates = _record_index(bundle.candidate_facts, "fact_id", "candidate fact")
    canonicals = _record_index(bundle.canonical_facts, "fact_id", "canonical fact")
    conflicts = _record_index(bundle.conflicts, "conflict_id", "conflict")
    provenances = _record_index(bundle.provenances, "provenance_id", "provenance")
    sources = _record_index(bundle.sources, "source_id", "source")
    evidence = _record_index(bundle.evidence, "evidence_id", "evidence")
    _record_index(bundle.review_items, "review_id", "review item")

    if bundle.lead is not None and bundle.lead.company_id != company_id:
        raise ValueError("lead belongs to another company")

    person_ids = set(people)
    subject_ids = {company_id, *person_ids}
    evidence_ids = set(evidence)
    provenance_ids = set(provenances)
    candidate_ids = set(candidates)

    for person in people.values():
        if person.company_id != company_id:
            raise ValueError(f"person belongs to another company: {person.person_id}")
        _require_subset(person.relationship_evidence_ids, evidence_ids, f"person {person.person_id}")

    for contact in contacts.values():
        if contact.owner_id not in subject_ids:
            raise ValueError(f"contact owner is outside export company/people set: {contact.contact_id}")
        _require_subset(contact.discovery_evidence_ids, evidence_ids, f"contact {contact.contact_id} discovery")
        _require_subset(contact.validation_evidence_ids, evidence_ids, f"contact {contact.contact_id} validation")

    for provenance in provenances.values():
        if provenance.subject_id not in subject_ids:
            raise ValueError(f"provenance belongs to another entity: {provenance.provenance_id}")
        _require_subset(provenance.evidence_ids, evidence_ids, f"provenance {provenance.provenance_id}")
        _require_subset(provenance.derived_from_fact_ids, candidate_ids, f"provenance {provenance.provenance_id} derivation")

    for fact in candidates.values():
        if fact.subject_id not in subject_ids:
            raise ValueError(f"candidate fact belongs to another entity: {fact.fact_id}")
        _require_subset(fact.evidence_ids, evidence_ids, f"candidate fact {fact.fact_id}")
        _require_subset((fact.provenance_id,), provenance_ids, f"candidate fact {fact.fact_id}")
        provenance = provenances[fact.provenance_id]
        if provenance.subject_id != fact.subject_id or provenance.field_name != fact.field_name:
            raise ValueError(f"candidate fact provenance subject/field mismatch: {fact.fact_id}")
        if not set(fact.evidence_ids).issubset(provenance.evidence_ids):
            raise ValueError(f"candidate fact evidence is not represented by provenance: {fact.fact_id}")

    for fact in canonicals.values():
        if fact.subject_id not in subject_ids:
            raise ValueError(f"canonical fact belongs to another entity: {fact.fact_id}")
        _require_subset(fact.candidate_fact_ids, candidate_ids, f"canonical fact {fact.fact_id}")
        _require_subset((fact.provenance_id,), provenance_ids, f"canonical fact {fact.fact_id}")
        provenance = provenances[fact.provenance_id]
        if provenance.subject_id != fact.subject_id or provenance.field_name != fact.field_name:
            raise ValueError(f"canonical fact provenance subject/field mismatch: {fact.fact_id}")
        for candidate_id in fact.candidate_fact_ids:
            candidate = candidates[candidate_id]
            if candidate.subject_id != fact.subject_id or candidate.field_name != fact.field_name:
                raise ValueError(f"canonical fact references candidate from another subject/field: {fact.fact_id}")

    for conflict in conflicts.values():
        if conflict.subject_id not in subject_ids:
            raise ValueError(f"conflict belongs to another entity: {conflict.conflict_id}")
        _require_subset(conflict.candidate_fact_ids, candidate_ids, f"conflict {conflict.conflict_id}")
        for candidate_id in conflict.candidate_fact_ids:
            candidate = candidates[candidate_id]
            if candidate.subject_id != conflict.subject_id or candidate.field_name != conflict.field_name:
                raise ValueError(f"conflict references candidate from another subject/field: {conflict.conflict_id}")

    source_ids = set(sources)
    for item in evidence.values():
        _require_subset((item.source_id,), source_ids, f"evidence {item.evidence_id}")

    for item in bundle.review_items:
        _require_subset(item.evidence_ids, evidence_ids, f"review item {item.review_id}")


def _primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise TypeError("non-finite floats are not exportable")
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise TypeError("naive datetimes are not exportable")
        return value.isoformat()
    if isinstance(value, bytes):
        return {"encoding": "hex", "value": value.hex()}
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _primitive(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key in sorted(value):
            if not isinstance(key, str):
                raise TypeError("mapping keys must be strings for export")
            result[key] = _primitive(value[key])
        return result
    if isinstance(value, (tuple, list)):
        return [_primitive(item) for item in value]
    if isinstance(value, (set, frozenset)):
        items = [_primitive(item) for item in value]
        return sorted(items, key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    raise TypeError(f"unsupported export value type: {type(value).__name__}")


def _ordered(records: Iterable[Any], id_attr: str) -> list[Any]:
    return [_primitive(record) for record in sorted(records, key=lambda item: getattr(item, id_attr))]


def to_export_dict(bundle: LeadExportBundle) -> dict[str, Any]:
    _validate(bundle)
    return {
        "schema_version": SCHEMA_VERSION,
        "company": _primitive(bundle.company),
        "lead": _primitive(bundle.lead),
        "people": _ordered(bundle.people, "person_id"),
        "contacts": _ordered(bundle.contacts, "contact_id"),
        "candidate_facts": _ordered(bundle.candidate_facts, "fact_id"),
        "canonical_facts": _ordered(bundle.canonical_facts, "fact_id"),
        "conflicts": _ordered(bundle.conflicts, "conflict_id"),
        "provenances": _ordered(bundle.provenances, "provenance_id"),
        "sources": _ordered(bundle.sources, "source_id"),
        "evidence": _ordered(bundle.evidence, "evidence_id"),
        "review_items": _ordered(bundle.review_items, "review_id"),
    }


def export_json(bundle: LeadExportBundle) -> str:
    return json.dumps(
        to_export_dict(bundle), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    )


def _cell(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def export_csv(bundle: LeadExportBundle) -> str:
    data = to_export_dict(bundle)
    lead = bundle.lead
    row = {
        "schema_version": SCHEMA_VERSION,
        "company_id": bundle.company.company_id,
        "lead_id": lead.lead_id if lead else "",
        "lead_stage": lead.stage.value if lead else "",
        "qualification_status": lead.qualification_status.value if lead else "",
        "company": _cell(data["company"]),
        "people": _cell(data["people"]),
        "contacts": _cell(data["contacts"]),
        "facts": _cell({
            "candidate": data["candidate_facts"],
            "canonical": data["canonical_facts"],
            "conflicts": data["conflicts"],
        }),
        "provenances": _cell(data["provenances"]),
        "sources": _cell(data["sources"]),
        "evidence": _cell(data["evidence"]),
        "review_items": _cell(data["review_items"]),
    }
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=tuple(row), lineterminator="\n")
    writer.writeheader()
    writer.writerow(row)
    return output.getvalue()
