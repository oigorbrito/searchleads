"""Independent structured lead export for LEADS_EXPORT_V1."""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from enum import Enum
import csv
import io
import json
from typing import Any

from .domain import CandidateFact, CanonicalFact, Company, Conflict, ContactPoint, EntityType, Evidence, Lead, Person, ProfessionalRole, Source
from .qualification import QualificationResult

@dataclass(frozen=True, slots=True)
class LeadExportBundle:
    company: Company
    lead: Lead | None = None
    people: tuple[Person,...] = ()
    roles: tuple[ProfessionalRole,...] = ()
    contacts: tuple[ContactPoint,...] = ()
    candidate_facts: tuple[CandidateFact,...] = ()
    canonical_facts: tuple[CanonicalFact,...] = ()
    conflicts: tuple[Conflict,...] = ()
    sources: tuple[Source,...] = ()
    evidence: tuple[Evidence,...] = ()
    qualification: QualificationResult | None = None

def _primitive(value:Any)->Any:
    if isinstance(value,Enum): return value.value
    if isinstance(value,datetime): return value.isoformat()
    if is_dataclass(value): return {k:_primitive(v) for k,v in asdict(value).items()}
    if isinstance(value,dict): return {str(k):_primitive(v) for k,v in value.items()}
    if isinstance(value,(tuple,list,set,frozenset)): return [_primitive(v) for v in value]
    if isinstance(value,bytes): return {"encoding":"hex","value":value.hex()}
    return value

def _validate(bundle:LeadExportBundle)->None:
    company_id=bundle.company.company_id
    people_ids={p.person_id for p in bundle.people}
    evidence_ids={e.evidence_id for e in bundle.evidence}
    source_ids={s.source_id for s in bundle.sources}
    if bundle.lead is not None and bundle.lead.company_id != company_id: raise ValueError("lead belongs to another company")
    if bundle.qualification is not None and bundle.qualification.company_id != company_id: raise ValueError("qualification belongs to another company")
    for role in bundle.roles:
        if role.company_id != company_id or role.person_id not in people_ids: raise ValueError("role is outside export company/people set")
    for contact in bundle.contacts:
        if contact.owner.entity_type is EntityType.COMPANY and contact.owner.entity_id != company_id: raise ValueError("contact belongs to another company")
        if contact.owner.entity_type is EntityType.PERSON and contact.owner.entity_id not in people_ids: raise ValueError("person contact owner is missing from export")
    for fact in bundle.candidate_facts + bundle.canonical_facts:
        if fact.subject.entity_type is not EntityType.COMPANY or fact.subject.entity_id != company_id: raise ValueError("fact belongs to another entity")
    for conflict in bundle.conflicts:
        if conflict.subject.entity_type is not EntityType.COMPANY or conflict.subject.entity_id != company_id: raise ValueError("conflict belongs to another entity")
    for ev in bundle.evidence:
        if ev.source_id not in source_ids: raise ValueError("evidence source is missing from export")
    provenance_sets=[x.provenance.evidence_ids for x in bundle.contacts + bundle.candidate_facts + bundle.canonical_facts + bundle.roles]
    for ids in provenance_sets:
        missing=set(ids)-evidence_ids
        if missing: raise ValueError(f"provenance evidence missing from export: {sorted(missing)}")

def to_export_dict(bundle:LeadExportBundle)->dict[str,Any]:
    _validate(bundle)
    return {
        "company":_primitive(bundle.company),
        "lead":_primitive(bundle.lead),
        "people":_primitive(bundle.people),
        "roles":_primitive(bundle.roles),
        "contacts":_primitive(bundle.contacts),
        "candidate_facts":_primitive(bundle.candidate_facts),
        "canonical_facts":_primitive(bundle.canonical_facts),
        "conflicts":_primitive(bundle.conflicts),
        "sources":_primitive(bundle.sources),
        "evidence":_primitive(bundle.evidence),
        "qualification":_primitive(bundle.qualification),
    }

def export_json(bundle:LeadExportBundle)->str:
    return json.dumps(to_export_dict(bundle),ensure_ascii=False,sort_keys=True,separators=(",",":"))

def export_csv(bundle:LeadExportBundle)->str:
    data=to_export_dict(bundle)
    row={
        "company_id":bundle.company.company_id,
        "lead_status":bundle.lead.status.value if bundle.lead else "",
        "company":json.dumps(data["company"],ensure_ascii=False,sort_keys=True),
        "people":json.dumps(data["people"],ensure_ascii=False,sort_keys=True),
        "roles":json.dumps(data["roles"],ensure_ascii=False,sort_keys=True),
        "contacts":json.dumps(data["contacts"],ensure_ascii=False,sort_keys=True),
        "facts":json.dumps({"candidate":data["candidate_facts"],"canonical":data["canonical_facts"],"conflicts":data["conflicts"]},ensure_ascii=False,sort_keys=True),
        "sources":json.dumps(data["sources"],ensure_ascii=False,sort_keys=True),
        "evidence":json.dumps(data["evidence"],ensure_ascii=False,sort_keys=True),
        "qualification":json.dumps(data["qualification"],ensure_ascii=False,sort_keys=True),
    }
    out=io.StringIO(); writer=csv.DictWriter(out,fieldnames=tuple(row)); writer.writeheader(); writer.writerow(row); return out.getvalue()
