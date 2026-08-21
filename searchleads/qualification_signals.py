"""Typed evidence signals for future ICP qualification without inventing an ICP."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Any
from .domain import CanonicalFact, ContactPoint, ContactStatus, EntityType, LeadStatus, ProfessionalRole
from .qualification import CriterionOperator, QualificationPolicy, QualificationCriterion, criterion_matches

class QualificationInputType(str, Enum):
    CANONICAL_FACT='CANONICAL_FACT'; PROFESSIONAL_ROLE='PROFESSIONAL_ROLE'; VALIDATED_CONTACT='VALIDATED_CONTACT'

@dataclass(frozen=True, slots=True)
class QualificationInput:
    input_id:str; company_id:str; predicate:str; value:Any; evidence_ids:tuple[str,...]; input_type:QualificationInputType

@dataclass(frozen=True, slots=True)
class SignalCriterionEvaluation:
    criterion_id:str; predicate:str; matched:bool|None; input_ids:tuple[str,...]; actual_values:tuple[Any,...]; reason:str

@dataclass(frozen=True, slots=True)
class SignalQualificationResult:
    company_id:str; policy_id:str|None; status:LeadStatus; evaluations:tuple[SignalCriterionEvaluation,...]; reasons:tuple[str,...]; qualification_input_ids:tuple[str,...]

def inputs_from_evidence(company_id:str, canonical_facts:Iterable[CanonicalFact]=(), roles:Iterable[ProfessionalRole]=(), contacts:Iterable[ContactPoint]=())->tuple[QualificationInput,...]:
    out=[]
    for fact in canonical_facts:
        if fact.subject.entity_id==company_id:
            out.append(QualificationInput(fact.canonical_fact_id,company_id,fact.predicate,fact.value,tuple(fact.provenance.evidence_ids),QualificationInputType.CANONICAL_FACT))
    for role in roles:
        if role.company_id==company_id:
            out.append(QualificationInput(role.role_id,company_id,'professional_role_title',role.title,tuple(role.provenance.evidence_ids),QualificationInputType.PROFESSIONAL_ROLE))
    for contact in contacts:
        if contact.owner.entity_type is EntityType.COMPANY and contact.owner.entity_id==company_id and contact.status is ContactStatus.VALIDATED:
            out.append(QualificationInput(contact.contact_id,company_id,'validated_contact_kind',contact.kind.value,tuple(contact.provenance.evidence_ids),QualificationInputType.VALIDATED_CONTACT))
            out.append(QualificationInput(contact.contact_id+':presence',company_id,'validated_contact_present',True,tuple(contact.provenance.evidence_ids),QualificationInputType.VALIDATED_CONTACT))
    return tuple(out)

def _match_many(values:tuple[Any,...], criterion:QualificationCriterion)->bool:
    op=criterion.operator
    if op is CriterionOperator.EXISTS: return bool(values)
    if op is CriterionOperator.NOT_EXISTS: return not values
    if op in (CriterionOperator.NE,CriterionOperator.NOT_IN,CriterionOperator.NOT_CONTAINS):
        return bool(values) and all(criterion_matches(v,criterion) for v in values)
    return any(criterion_matches(v,criterion) for v in values)

def qualify_company_inputs(company_id:str, inputs:Iterable[QualificationInput], policy:QualificationPolicy|None)->SignalQualificationResult:
    if policy is None: return SignalQualificationResult(company_id,None,LeadStatus.UNKNOWN,(),('ICP/policy is not defined',),())
    by={}
    for item in inputs:
        if item.company_id==company_id: by.setdefault(item.predicate,[]).append(item)
    evaluations=[]; used=[]; required_failed=False; required_missing=False; optional_matches=0
    for criterion in policy.criteria:
        candidates=tuple(by.get(criterion.predicate,()))
        if not candidates and criterion.operator is not CriterionOperator.NOT_EXISTS:
            evaluations.append(SignalCriterionEvaluation(criterion.criterion_id,criterion.predicate,None,(),(),'missing qualification input'))
            if criterion.required: required_missing=True
            continue
        values=tuple(c.value for c in candidates); matched=_match_many(values,criterion)
        ids=tuple(c.input_id for c in candidates); used.extend(ids)
        evaluations.append(SignalCriterionEvaluation(criterion.criterion_id,criterion.predicate,matched,ids,values,'matched' if matched else 'criterion not met'))
        if criterion.required and not matched: required_failed=True
        if not criterion.required and matched: optional_matches+=1
    if required_failed: status=LeadStatus.NOT_QUALIFIED; reasons=('one or more required criteria are contradicted by evidence-backed qualification inputs',)
    elif required_missing: status=LeadStatus.UNKNOWN; reasons=('required qualification evidence is missing',)
    elif optional_matches < policy.minimum_optional_matches: status=LeadStatus.NOT_QUALIFIED; reasons=(f'optional-match requirement not met: {optional_matches}/{policy.minimum_optional_matches}',)
    else: status=LeadStatus.QUALIFIED; reasons=(f'all required criteria met under explicit policy {policy.policy_id}',)
    return SignalQualificationResult(company_id,policy.policy_id,status,tuple(evaluations),reasons,tuple(sorted(set(used))))
