"""Evidence-backed, policy-required lead qualification for Work Unit 10.

No default ICP is defined. Callers must supply an explicit QualificationPolicy.
The engine evaluates only CanonicalFact records and separates contradiction,
missing evidence, and qualification.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import hashlib
from typing import Any, Iterable
from .domain import CanonicalFact, Lead, LeadStatus

class CriterionOperator(str, Enum):
    EQ="EQ"; IN="IN"; EXISTS="EXISTS"; CONTAINS="CONTAINS"

@dataclass(frozen=True, slots=True)
class QualificationCriterion:
    criterion_id:str; predicate:str; operator:CriterionOperator; expected:Any=None; required:bool=True
    def __post_init__(self):
        if not self.criterion_id.strip() or not self.predicate.strip(): raise ValueError("criterion_id and predicate must be non-blank")
        if self.operator is CriterionOperator.IN and (not isinstance(self.expected,(tuple,list,set,frozenset)) or not self.expected): raise ValueError("IN criterion requires a non-empty collection")
        if self.operator is CriterionOperator.EXISTS and self.expected is not None: raise ValueError("EXISTS criterion does not accept expected")

@dataclass(frozen=True, slots=True)
class QualificationPolicy:
    policy_id:str; criteria:tuple[QualificationCriterion,...]; minimum_optional_matches:int=0
    def __post_init__(self):
        if not self.policy_id.strip(): raise ValueError("policy_id must be non-blank")
        if not self.criteria: raise ValueError("qualification policy must define at least one criterion")
        if len({c.criterion_id for c in self.criteria}) != len(self.criteria): raise ValueError("criterion IDs must be unique")
        optional=sum(not c.required for c in self.criteria)
        if not 0 <= self.minimum_optional_matches <= optional: raise ValueError("minimum_optional_matches exceeds optional criteria")

@dataclass(frozen=True, slots=True)
class CriterionEvaluation:
    criterion_id:str; predicate:str; matched:bool|None; canonical_fact_id:str|None; actual_value:Any=None; reason:str=""

@dataclass(frozen=True, slots=True)
class QualificationResult:
    company_id:str; policy_id:str|None; status:LeadStatus; evaluations:tuple[CriterionEvaluation,...]; reasons:tuple[str,...]; qualification_fact_ids:tuple[str,...]

def _match(value,criterion):
    if criterion.operator is CriterionOperator.EQ: return value == criterion.expected
    if criterion.operator is CriterionOperator.IN: return value in criterion.expected
    if criterion.operator is CriterionOperator.EXISTS: return value is not None
    if criterion.operator is CriterionOperator.CONTAINS:
        if isinstance(value,str): return str(criterion.expected).casefold() in value.casefold()
        try: return criterion.expected in value
        except TypeError: return False
    raise ValueError(f"unsupported operator: {criterion.operator}")

def qualify_company(company_id:str,facts:Iterable[CanonicalFact],policy:QualificationPolicy|None)->QualificationResult:
    if policy is None: return QualificationResult(company_id,None,LeadStatus.UNKNOWN,(),("ICP/policy is not defined",),())
    by={}
    for fact in facts:
        if fact.subject.entity_id==company_id: by.setdefault(fact.predicate,[]).append(fact)
    evaluations=[]; used=[]; required_failed=False; required_missing=False; optional_matches=0
    for criterion in policy.criteria:
        candidates=by.get(criterion.predicate,[])
        if len(candidates)!=1:
            reason="missing canonical fact" if not candidates else "multiple canonical facts; conflict must be resolved first"
            evaluations.append(CriterionEvaluation(criterion.criterion_id,criterion.predicate,None,None,None,reason))
            if criterion.required: required_missing=True
            continue
        fact=candidates[0]; matched=_match(fact.value,criterion)
        evaluations.append(CriterionEvaluation(criterion.criterion_id,criterion.predicate,matched,fact.canonical_fact_id,fact.value,"matched" if matched else "criterion not met")); used.append(fact.canonical_fact_id)
        if criterion.required and not matched: required_failed=True
        if not criterion.required and matched: optional_matches+=1
    if required_failed: status=LeadStatus.NOT_QUALIFIED; reasons=("one or more required criteria are contradicted by canonical facts",)
    elif required_missing: status=LeadStatus.UNKNOWN; reasons=("required qualification evidence is missing or unresolved",)
    elif optional_matches < policy.minimum_optional_matches: status=LeadStatus.NOT_QUALIFIED; reasons=(f"optional-match requirement not met: {optional_matches}/{policy.minimum_optional_matches}",)
    else: status=LeadStatus.QUALIFIED; reasons=(f"all required criteria met under explicit policy {policy.policy_id}",)
    return QualificationResult(company_id,policy.policy_id,status,tuple(evaluations),reasons,tuple(sorted(set(used))))

def lead_from_qualification(result:QualificationResult)->Lead:
    material=f"{result.company_id}|{result.policy_id}|{result.status.value}|{'|'.join(result.qualification_fact_ids)}"
    return Lead("lead:qualification:"+hashlib.sha256(material.encode()).hexdigest()[:24],result.company_id,result.status,result.reasons,result.qualification_fact_ids,{"qualification_policy_id":result.policy_id})
