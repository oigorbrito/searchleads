"""Unified scientific metrics with explicit unavailable states."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from enum import StrEnum
import json,re
from typing import Iterable,Mapping,Sequence
from searchleads.domain import CandidateFact,CanonicalFact,Conflict,ContactKind,ContactPoint,ContactStatus,Provenance,QualificationStatus

class MetricAvailability(StrEnum): AVAILABLE='AVAILABLE'; UNAVAILABLE='UNAVAILABLE'
@dataclass(frozen=True,slots=True)
class MetricValue:
    availability:MetricAvailability; value:float|None; numerator:float|None=None; denominator:float|None=None; reason:str|None=None
    def __post_init__(self):
        if self.availability is MetricAvailability.AVAILABLE and self.value is None: raise ValueError('available metric requires value')
        if self.availability is MetricAvailability.UNAVAILABLE and not self.reason: raise ValueError('unavailable metric requires reason')
    @classmethod
    def rate(cls,numerator:float,denominator:float,*,zero_reason:str):
        if denominator<=0:return cls(MetricAvailability.UNAVAILABLE,None,numerator,denominator,zero_reason)
        return cls(MetricAvailability.AVAILABLE,numerator/denominator,numerator,denominator,None)
    @classmethod
    def unavailable(cls,reason:str):
        if not reason.strip(): raise ValueError('unavailable reason must be non-blank')
        return cls(MetricAvailability.UNAVAILABLE,None,None,None,reason)

@dataclass(frozen=True,slots=True)
class DiscoveryMetrics:
    discovered_observations:int; unique_entities:int; duplicate_discovery_rate:MetricValue; bounded_coverage:MetricValue; discovery_precision:MetricValue

def compute_discovery_metrics(discovered_entity_ids:Sequence[str],*,universe_entity_ids:Iterable[str]|None=None,true_relevant_entity_ids:Iterable[str]|None=None)->DiscoveryMetrics:
    observed=tuple(discovered_entity_ids); unique=set(observed); duplicate=len(observed)-len(unique)
    duplicate_rate=MetricValue.rate(duplicate,len(observed),zero_reason='no discovery observations')
    coverage=MetricValue.unavailable('bounded discovery universe / denominator is not supplied') if universe_entity_ids is None else MetricValue.rate(len(unique & set(universe_entity_ids)),len(set(universe_entity_ids)),zero_reason='bounded discovery universe is empty')
    precision=MetricValue.unavailable('discovery relevance ground truth is not supplied') if true_relevant_entity_ids is None else MetricValue.rate(len(unique & set(true_relevant_entity_ids)),len(unique),zero_reason='no discovered entities')
    return DiscoveryMetrics(len(observed),len(unique),duplicate_rate,coverage,precision)

@dataclass(frozen=True,slots=True)
class EntityResolutionMetrics:
    true_positive:int; false_positive:int; true_negative:int; false_negative:int; precision:MetricValue; recall:MetricValue; f1:MetricValue; false_merge_rate:MetricValue; false_split_rate:MetricValue

def compute_entity_resolution_metrics(tp:int,fp:int,tn:int,fn:int)->EntityResolutionMetrics:
    if min(tp,fp,tn,fn)<0: raise ValueError('confusion-matrix counts must be non-negative')
    precision=MetricValue.rate(tp,tp+fp,zero_reason='no predicted matches'); recall=MetricValue.rate(tp,tp+fn,zero_reason='no labeled duplicate pairs')
    if precision.value is None or recall.value is None or precision.value+recall.value==0:f1=MetricValue.unavailable('precision/recall are unavailable or both zero')
    else:
        value=2*precision.value*recall.value/(precision.value+recall.value); f1=MetricValue(MetricAvailability.AVAILABLE,value)
    return EntityResolutionMetrics(tp,fp,tn,fn,precision,recall,f1,MetricValue.rate(fp,fp+tn,zero_reason='no labeled distinct pairs'),MetricValue.rate(fn,tp+fn,zero_reason='no labeled duplicate pairs'))

@dataclass(frozen=True,slots=True)
class EnrichmentMetrics:
    field_coverage:MetricValue; field_accuracy:MetricValue; provenance_coverage:MetricValue; conflict_rate:MetricValue

def compute_enrichment_metrics(subject_ids:Sequence[str],required_fields:Sequence[str],*,canonical_facts:Iterable[CanonicalFact]=(),candidate_facts:Iterable[CandidateFact]=(),provenances:Iterable[Provenance]=(),conflicts:Iterable[Conflict]=(),field_accuracy_labels:Mapping[tuple[str,str],bool]|None=None)->EnrichmentMetrics:
    subjects=tuple(dict.fromkeys(subject_ids)); fields=tuple(dict.fromkeys(required_fields)); canonical=tuple(canonical_facts); candidates=tuple(candidate_facts); prov=tuple(provenances); conflict_items=tuple(conflicts)
    present={(f.subject_id,f.field_name) for f in canonical}; slots=len(subjects)*len(fields); covered=sum((s,f) in present for s in subjects for f in fields)
    coverage=MetricValue.rate(covered,slots,zero_reason='no subject/field slots defined')
    if field_accuracy_labels is None: accuracy=MetricValue.unavailable('field-accuracy ground truth is not supplied')
    else:
        labels=[bool(v) for k,v in field_accuracy_labels.items() if k in present]; accuracy=MetricValue.rate(sum(labels),len(labels),zero_reason='no labeled present fields')
    evidence_prov={p.provenance_id for p in prov if p.evidence_ids}; evidence_backed=sum(bool(f.evidence_ids) for f in candidates)+sum(f.provenance_id in evidence_prov for f in canonical); total=len(candidates)+len(canonical)
    provenance_coverage=MetricValue.rate(evidence_backed,total,zero_reason='no facts to measure')
    conflict_keys={(c.subject_id,c.field_name) for c in conflict_items}; evaluated=present|conflict_keys; conflict_rate=MetricValue.rate(len(conflict_keys),len(evaluated),zero_reason='no canonical/conflicting fields evaluated')
    return EnrichmentMetrics(coverage,accuracy,provenance_coverage,conflict_rate)

def _logical_contact_value(contact:ContactPoint)->str:
    value=contact.value.strip()
    if contact.kind is ContactKind.EMAIL:return value.casefold()
    if contact.kind in {ContactKind.PHONE,ContactKind.WHATSAPP}:return re.sub(r'\D','',value)
    return value.rstrip('/').casefold()
def _effective_contact_time(contact:ContactPoint): return contact.validated_at or contact.discovered_at
def _latest_logical_contacts(contacts:Iterable[ContactPoint])->tuple[ContactPoint,...]:
    latest={}; rank={ContactStatus.DISCOVERED:0,ContactStatus.UNKNOWN:1,ContactStatus.STALE:2,ContactStatus.INVALID:3,ContactStatus.VALIDATED:4}
    for c in contacts:
        key=(c.owner_id,c.kind.value,_logical_contact_value(c)); current=latest.get(key)
        if current is None or _effective_contact_time(c)>_effective_contact_time(current): latest[key]=c
        elif _effective_contact_time(c)==_effective_contact_time(current) and rank[c.status]>rank[current.status]: latest[key]=c
    return tuple(latest.values())
@dataclass(frozen=True,slots=True)
class ContactMetrics:
    logical_contacts:int; contact_discovery_rate:MetricValue; validation_rate:MetricValue; invalid_rate:MetricValue; stale_rate:MetricValue

def compute_contact_metrics(contacts:Iterable[ContactPoint],*,owner_ids:Sequence[str])->ContactMetrics:
    logical=_latest_logical_contacts(contacts); owners=set(owner_ids); owners_with={c.owner_id for c in logical if c.owner_id in owners}
    return ContactMetrics(len(logical),MetricValue.rate(len(owners_with),len(owners),zero_reason='no owners supplied'),MetricValue.rate(sum(c.status is ContactStatus.VALIDATED for c in logical),len(logical),zero_reason='no contacts discovered'),MetricValue.rate(sum(c.status is ContactStatus.INVALID for c in logical),len(logical),zero_reason='no contacts discovered'),MetricValue.rate(sum(c.status is ContactStatus.STALE for c in logical),len(logical),zero_reason='no contacts discovered'))

@dataclass(frozen=True,slots=True)
class QualificationMetrics:
    precision:MetricValue; recall:MetricValue; human_disagreement_rate:MetricValue

def compute_qualification_metrics(predictions:Mapping[str,QualificationStatus],*,ground_truth:Mapping[str,bool]|None=None,human_decisions:Mapping[str,QualificationStatus]|None=None)->QualificationMetrics:
    if ground_truth is None:
        precision=MetricValue.unavailable('qualification ground truth is not supplied'); recall=MetricValue.unavailable('qualification ground truth is not supplied')
    else:
        common=set(predictions)&set(ground_truth); tp=sum(predictions[k] is QualificationStatus.QUALIFIED and ground_truth[k] for k in common); fp=sum(predictions[k] is QualificationStatus.QUALIFIED and not ground_truth[k] for k in common); fn=sum(predictions[k] is not QualificationStatus.QUALIFIED and ground_truth[k] for k in common)
        precision=MetricValue.rate(tp,tp+fp,zero_reason='no predicted qualified leads'); recall=MetricValue.rate(tp,tp+fn,zero_reason='no positive qualification labels')
    if human_decisions is None: disagreement=MetricValue.unavailable('human review decisions are not supplied')
    else:
        common=set(predictions)&set(human_decisions); disagreement=MetricValue.rate(sum(predictions[k] is not human_decisions[k] for k in common),len(common),zero_reason='no overlapping human decisions')
    return QualificationMetrics(precision,recall,disagreement)

@dataclass(frozen=True,slots=True)
class OperationalMetrics:
    cost_per_discovered:MetricValue; cost_per_enriched:MetricValue; cost_per_qualified:MetricValue; cost_per_validated_contact:MetricValue; time_per_lead_seconds:MetricValue

def _per_unit(total:float|None,count:int,missing_reason:str,zero_reason:str)->MetricValue:
    return MetricValue.unavailable(missing_reason) if total is None else MetricValue.rate(total,count,zero_reason=zero_reason)
def compute_operational_metrics(*,total_cost:float|None=None,elapsed_seconds:float|None=None,discovered:int=0,enriched:int=0,qualified:int=0,validated_contacts:int=0,processed_leads:int=0)->OperationalMetrics:
    if min(discovered,enriched,qualified,validated_contacts,processed_leads)<0: raise ValueError('operation counts cannot be negative')
    if total_cost is not None and total_cost<0: raise ValueError('total_cost cannot be negative')
    if elapsed_seconds is not None and elapsed_seconds<0: raise ValueError('elapsed_seconds cannot be negative')
    return OperationalMetrics(_per_unit(total_cost,discovered,'cost telemetry is not supplied','no discovered units'),_per_unit(total_cost,enriched,'cost telemetry is not supplied','no enriched units'),_per_unit(total_cost,qualified,'cost telemetry is not supplied','no qualified units'),_per_unit(total_cost,validated_contacts,'cost telemetry is not supplied','no validated contacts'),_per_unit(elapsed_seconds,processed_leads,'elapsed-time telemetry is not supplied','no processed leads'))

@dataclass(frozen=True,slots=True)
class MeasurementReport:
    schema_version:str; scope:str; discovery:DiscoveryMetrics; entity_resolution:EntityResolutionMetrics; enrichment:EnrichmentMetrics; contacts:ContactMetrics; qualification:QualificationMetrics; operation:OperationalMetrics
    def __post_init__(self):
        if self.schema_version!='searchleads_measurement_v1': raise ValueError('measurement schema_version is fixed')
        if not self.scope.strip(): raise ValueError('measurement scope must be non-blank')
    def to_dict(self): return asdict(self)
    def to_json(self): return json.dumps(self.to_dict(),ensure_ascii=False,sort_keys=True,separators=(',',':'))

def build_measurement_report(*,scope:str,discovery:DiscoveryMetrics,entity_resolution:EntityResolutionMetrics,enrichment:EnrichmentMetrics,contacts:ContactMetrics,qualification:QualificationMetrics,operation:OperationalMetrics)->MeasurementReport:
    return MeasurementReport('searchleads_measurement_v1',scope,discovery,entity_resolution,enrichment,contacts,qualification,operation)
