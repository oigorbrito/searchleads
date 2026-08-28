from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import hashlib
import re
import unicodedata
from typing import Iterable

from searchleads.domain import (
    CandidateFact, CanonicalFact, Conflict, ConflictStatus, ContactPoint, ContactStatus,
    Lead, LeadStage, Person, QualificationStatus,
)
from searchleads.qualification_policy import APPROVED_DENTAL_ICP_POLICY_V1, DentalICPPolicyContractV1


class DentalFit(StrEnum): HIGH='HIGH'; MEDIUM='MEDIUM'; LOW='LOW'; UNKNOWN='UNKNOWN'
class DentalIntent(StrEnum): HIGH='HIGH'; MEDIUM='MEDIUM'; LOW='LOW'; UNKNOWN='UNKNOWN'
class DentalPriority(StrEnum): P1='P1'; P2='P2'; P3='P3'; REVIEW='REVIEW'; EXCLUDE='EXCLUDE'
class DentalOfferTrack(StrEnum):
    CEOF_SPECIALIZATION='CEOF_SPECIALIZATION'
    COMPLEMENTARY_EXCLUSIVE_CEOF='COMPLEMENTARY_EXCLUSIVE_CEOF'

_BR_STATES=frozenset({'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'})
_TITLE_FIELDS=frozenset({'professional_role_title','professional_title','specialty'})
_RELEVANCE_FIELDS=frozenset({'professional_role_title','professional_title','specialty','practice_focus','procedure'})
_GEO_FIELDS=frozenset({'country','state'})
_INTENT_FIELD='education_intent'
_REQUIRED_CONFLICT_FIELDS=_TITLE_FIELDS|_GEO_FIELDS


def _fold(value: object) -> str:
    text=unicodedata.normalize('NFKC',str(value)).casefold()
    text=''.join(ch for ch in unicodedata.normalize('NFKD',text) if not unicodedata.combining(ch))
    return ' '.join(text.split())


def _effective_candidate_value(fact: CandidateFact) -> object:
    value=fact.normalized_value
    if isinstance(value,str) and not value.strip(): value=None
    return fact.raw_value if value is None else value


def _unique(values: Iterable[object]) -> tuple[object,...]:
    out=[]; seen=set()
    for value in values:
        key=_fold(value)
        if key not in seen:
            seen.add(key); out.append(value)
    return tuple(out)


def _classify_title(value: object) -> str|None:
    text=_fold(value)
    if 'cirurgia estetica orofacial' in text or re.search(r'(?<![a-z])ceof(?![a-z])',text): return 'CEOF'
    if any(x in text for x in ('bucomax','buco maxilo','buco-maxilo','cirurgia e traumatologia bucomaxilofacial')): return 'BUCOMAXILLOFACIAL'
    if any(x in text for x in ('harmonizacao orofacial','harmonizacao facial')) or re.search(r'(?<![a-z])hof(?![a-z])',text): return 'HOF_OR_FACIAL_ACTIVITY'
    if any(x in text for x in ('dentista','cirurgiao-dentista','cirurgiao dentista','odontolog')): return 'GENERAL_DENTIST'
    if any(x in text for x in ('ortodont','endodont','periodont','implantodont','odontopediatr','estomatolog','protesista','prostodont')): return 'DENTAL_SPECIALIST'
    return None


def _facially_relevant(value: object) -> bool:
    text=_fold(value)
    return any(term in text for term in ('blefaroplastia','lip lift','liplift','lifting facial','frontoplastia','cirurgia facial','estetica facial','harmonizacao orofacial','harmonizacao facial','cirurgia estetica orofacial'))


def _priority(fit:DentalFit,intent:DentalIntent)->DentalPriority:
    if fit is DentalFit.LOW: return DentalPriority.EXCLUDE
    if fit is DentalFit.UNKNOWN: return DentalPriority.REVIEW
    if fit is DentalFit.HIGH and intent is DentalIntent.HIGH: return DentalPriority.P1
    if (fit is DentalFit.HIGH and intent in {DentalIntent.MEDIUM,DentalIntent.UNKNOWN}) or (fit is DentalFit.MEDIUM and intent is DentalIntent.HIGH): return DentalPriority.P2
    if fit in {DentalFit.HIGH,DentalFit.MEDIUM}: return DentalPriority.P3
    raise AssertionError('unreachable fit value')  # pragma: no cover


@dataclass(frozen=True,slots=True)
class DentalQualificationDecision:
    decision_id:str; person_id:str; company_id:str; policy_id:str; offer_track:DentalOfferTrack
    qualification_status:QualificationStatus; fit:DentalFit; intent:DentalIntent; priority:DentalPriority
    title_groups:tuple[str,...]; reasons:tuple[str,...]; evidence_ids:tuple[str,...]
    candidate_fact_ids:tuple[str,...]; canonical_fact_ids:tuple[str,...]; conflict_ids:tuple[str,...]; contact_ids:tuple[str,...]
    def __post_init__(self)->None:
        if any(not x.strip() for x in (self.decision_id,self.person_id,self.company_id,self.policy_id)): raise ValueError('decision identity must be non-blank')
        if self.policy_id != APPROVED_DENTAL_ICP_POLICY_V1.policy_id: raise ValueError('qualification decision policy is not the approved dental ICP policy')
        if not isinstance(self.offer_track,DentalOfferTrack): raise ValueError('qualification decision offer_track must be a DentalOfferTrack')
        if not isinstance(self.qualification_status,QualificationStatus): raise ValueError('qualification decision status must be a QualificationStatus')
        if not isinstance(self.fit,DentalFit) or not isinstance(self.intent,DentalIntent) or not isinstance(self.priority,DentalPriority): raise ValueError('qualification decision fit, intent and priority must use dental enums')
        if self.qualification_status is QualificationStatus.UNKNOWN and self.fit is not DentalFit.UNKNOWN: raise ValueError('UNKNOWN qualification requires UNKNOWN fit')
        if self.qualification_status is QualificationStatus.NOT_QUALIFIED and self.fit is not DentalFit.LOW: raise ValueError('NOT_QUALIFIED qualification requires LOW fit')
        if self.qualification_status is QualificationStatus.QUALIFIED and self.fit not in {DentalFit.HIGH,DentalFit.MEDIUM}: raise ValueError('QUALIFIED qualification requires HIGH or MEDIUM fit')
        if self.priority is not _priority(self.fit,self.intent): raise ValueError('qualification priority is inconsistent with fit and intent')
        if not self.evidence_ids: raise ValueError('qualification decision requires evidence')
        for values in (self.evidence_ids,self.candidate_fact_ids,self.canonical_fact_ids,self.conflict_ids,self.contact_ids):
            if tuple(sorted(set(values)))!=values: raise ValueError('decision reference IDs must be sorted and unique')


def _fact_values(subject_ids:set[str], field:str, candidates:tuple[CandidateFact,...], canonicals:tuple[CanonicalFact,...])->tuple[object,...]:
    canonical_values=_unique(f.value for f in canonicals if f.subject_id in subject_ids and f.field_name==field)
    if canonical_values: return canonical_values
    return _unique(_effective_candidate_value(f) for f in candidates if f.subject_id in subject_ids and f.field_name==field)


def qualify_dental_person(
    person:Person, *, candidate_facts:Iterable[CandidateFact]=(), canonical_facts:Iterable[CanonicalFact]=(),
    conflicts:Iterable[Conflict]=(), contacts:Iterable[ContactPoint]=(),
    offer_track:DentalOfferTrack=DentalOfferTrack.CEOF_SPECIALIZATION, require_validated_contact:bool=False,
    policy:DentalICPPolicyContractV1=APPROVED_DENTAL_ICP_POLICY_V1,
)->DentalQualificationDecision:
    if not isinstance(policy, DentalICPPolicyContractV1) or policy != APPROVED_DENTAL_ICP_POLICY_V1:
        raise ValueError('unsupported qualification policy contract')
    if not isinstance(offer_track, DentalOfferTrack) or offer_track.value not in {policy.default_offer_track,'COMPLEMENTARY_EXCLUSIVE_CEOF'}:
        raise ValueError('offer track is not allowed by policy')

    candidates=tuple(candidate_facts); canonicals=tuple(canonical_facts); conflicts=tuple(conflicts); contacts=tuple(contacts)
    subjects={person.person_id,person.company_id}
    cand_by_id={f.fact_id:f for f in candidates}
    relevant_candidates={f.fact_id for f in candidates if f.subject_id in subjects and f.field_name in (_RELEVANCE_FIELDS|_GEO_FIELDS|{_INTENT_FIELD})}
    relevant_canonicals={f.fact_id for f in canonicals if f.subject_id in subjects and f.field_name in (_RELEVANCE_FIELDS|_GEO_FIELDS|{_INTENT_FIELD})}
    open_conflicts=tuple(c for c in conflicts if c.subject_id in subjects and c.status is ConflictStatus.OPEN and c.field_name in (_RELEVANCE_FIELDS|_GEO_FIELDS|{_INTENT_FIELD}))
    evidence=set(person.relationship_evidence_ids)
    for fact_id in relevant_candidates: evidence.update(cand_by_id[fact_id].evidence_ids)
    for fact in (item for item in canonicals if item.fact_id in relevant_canonicals):
        for cid in fact.candidate_fact_ids:
            if cid in cand_by_id: evidence.update(cand_by_id[cid].evidence_ids)
    for conflict in open_conflicts:
        for cid in conflict.candidate_fact_ids:
            if cid in cand_by_id: evidence.update(cand_by_id[cid].evidence_ids)

    reasons=[]
    required_conflict_fields=sorted({c.field_name for c in open_conflicts if c.field_name in _REQUIRED_CONFLICT_FIELDS})
    intent_conflict=any(c.field_name==_INTENT_FIELD for c in open_conflicts)

    country_values=_fact_values(subjects,'country',candidates,canonicals)
    state_values=_fact_values(subjects,'state',candidates,canonicals)
    countries={_fold(v).upper() for v in country_values}
    states={str(v).strip().upper() for v in state_values}
    has_br_country=bool(countries & {'BR','BRAZIL','BRASIL'})
    has_non_br_country=bool(countries-{'BR','BRAZIL','BRASIL'})
    has_br_state=bool(states & _BR_STATES)
    geo_unknown=False; geo_excluded=False
    if has_br_country and has_non_br_country: geo_unknown=True; reasons.append('conflicting country evidence prevents geographic qualification')
    elif has_non_br_country and not has_br_state: geo_excluded=True; reasons.append('evidence-backed geography is outside Brazil')
    elif not has_br_country and not has_br_state: geo_unknown=True; reasons.append('Brazil geography evidence is missing')

    title_values=tuple(v for field in _TITLE_FIELDS for v in _fact_values({person.person_id},field,candidates,canonicals))
    title_groups=tuple(dict.fromkeys(group for value in title_values for group in (_classify_title(value),) if group))
    title_unknown=False; title_excluded=False
    if not title_values: title_unknown=True; reasons.append('professional dental title evidence is missing')
    elif not title_groups: title_excluded=True; reasons.append('observed professional title is outside the approved dentistry target')

    if required_conflict_fields:
        reasons.append('unresolved required conflict: '+', '.join(required_conflict_fields))

    relevant_values=tuple(v for field in _RELEVANCE_FIELDS for v in _fact_values({person.person_id},field,candidates,canonicals))
    facial=any(_facially_relevant(v) for v in relevant_values)
    specific=any(g in {'CEOF','BUCOMAXILLOFACIAL','HOF_OR_FACIAL_ACTIVITY'} for g in title_groups)

    intent_values={str(v).strip().upper() for v in _fact_values({person.person_id},_INTENT_FIELD,candidates,canonicals)}
    positive_high=bool(intent_values & {'PROCEDURE_LEARNING','COURSE_INTEREST'})
    positive_medium=bool(intent_values & {'TRAINING_PARTICIPATION','CONTINUING_EDUCATION','EDUCATION_CONTENT_ENGAGEMENT'})
    negative='EXPLICIT_NO_INTEREST' in intent_values
    if intent_conflict or (negative and (positive_high or positive_medium)):
        intent=DentalIntent.UNKNOWN; reasons.append('learning-intent evidence is conflicted')
    elif negative:
        intent=DentalIntent.LOW; reasons.append('explicit evidence of no current learning interest')
    elif positive_high:
        intent=DentalIntent.HIGH; reasons.append('explicit evidence of procedure/course learning interest')
    elif positive_medium:
        intent=DentalIntent.MEDIUM; reasons.append('evidence of continuing education/training activity')
    else:
        intent=DentalIntent.UNKNOWN; reasons.append('no evidence-backed learning-intent signal is available')

    owned_contacts=tuple(c for c in contacts if c.owner_id in {person.person_id,person.company_id})
    validated=tuple(c for c in owned_contacts if c.status is ContactStatus.VALIDATED)
    contact_blocked=require_validated_contact and not validated
    if contact_blocked: reasons.append('validated professional contact is required by the active campaign selection')

    if required_conflict_fields or geo_unknown or title_unknown:
        status=QualificationStatus.UNKNOWN; fit=DentalFit.UNKNOWN
    elif geo_excluded or title_excluded or contact_blocked:
        status=QualificationStatus.NOT_QUALIFIED; fit=DentalFit.LOW
    elif specific or facial:
        status=QualificationStatus.QUALIFIED; fit=DentalFit.HIGH
        if specific: reasons.append('target dental specialty/title is evidence-backed')
        if facial: reasons.append('facial surgery/aesthetics relevance is evidence-backed')
    else:
        status=QualificationStatus.QUALIFIED; fit=DentalFit.MEDIUM; reasons.append('evidence-backed dentist profile is eligible; facial relevance not yet observed')

    if status is not QualificationStatus.NOT_QUALIFIED and offer_track is DentalOfferTrack.COMPLEMENTARY_EXCLUSIVE_CEOF:
        has_ceof=any(group=='CEOF' for group in title_groups)
        if status is QualificationStatus.UNKNOWN:
            reasons.append('CEOF specialist eligibility cannot be resolved while required evidence is unknown')
        elif has_ceof:
            reasons.append('explicit CEOF title supports the complementary exclusive-procedure offer track')
        else:
            status=QualificationStatus.NOT_QUALIFIED; fit=DentalFit.LOW; reasons.append('complementary exclusive CEOF offer requires explicit CEOF-specialist evidence')

    priority=_priority(fit,intent)
    candidate_ids=tuple(sorted(relevant_candidates | {cid for c in open_conflicts for cid in c.candidate_fact_ids if cid in cand_by_id}))
    canonical_ids=tuple(sorted(relevant_canonicals))
    conflict_ids=tuple(sorted(c.conflict_id for c in open_conflicts))
    contact_ids=tuple(sorted(c.contact_id for c in owned_contacts))
    evidence_ids=tuple(sorted(evidence))
    reason_tuple=tuple(dict.fromkeys(reasons))
    material='\0'.join((person.person_id,person.company_id,policy.policy_id,offer_track.value,status.value,fit.value,intent.value,priority.value,*candidate_ids,*canonical_ids,*conflict_ids,*contact_ids,*evidence_ids))
    decision_id='qualification:v1:'+hashlib.sha256(material.encode()).hexdigest()
    return DentalQualificationDecision(decision_id,person.person_id,person.company_id,policy.policy_id,offer_track,status,fit,intent,priority,title_groups,reason_tuple,evidence_ids,candidate_ids,canonical_ids,conflict_ids,contact_ids)


def materialize_lead(decision:DentalQualificationDecision, *, created_at:datetime, lead_id:str|None=None)->Lead:
    if created_at.tzinfo is None: raise ValueError('created_at must be timezone-aware')
    if lead_id is None: lead_id='lead:v1:'+hashlib.sha256((decision.person_id+'\0'+decision.company_id+'\0'+decision.policy_id+'\0'+decision.offer_track.value).encode()).hexdigest()
    stage={QualificationStatus.QUALIFIED:LeadStage.QUALIFIED,QualificationStatus.NOT_QUALIFIED:LeadStage.DISQUALIFIED,QualificationStatus.UNKNOWN:LeadStage.REVIEW}[decision.qualification_status]
    audit=(f'policy_id={decision.policy_id}',f'person_id={decision.person_id}',f'offer_track={decision.offer_track.value}',f'fit={decision.fit.value}',f'intent={decision.intent.value}',f'priority={decision.priority.value}',*decision.reasons)
    return Lead(lead_id,decision.company_id,stage,decision.qualification_status,audit,created_at)
