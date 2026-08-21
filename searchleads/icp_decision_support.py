"""ICP decision-support without defining an ICP.

Measures whether each handoff ICP dimension has evidence usable by the current
qualification path. It never supplies target values, weights, thresholds, or a
default policy.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

class ICPDimension(str, Enum):
    TARGET_MARKET="TARGET_MARKET"; INDUSTRY="INDUSTRY"; GEOGRAPHY="GEOGRAPHY"; COMPANY_SIZE="COMPANY_SIZE"; BUSINESS_SIGNAL="BUSINESS_SIGNAL"; EXCLUSION_CRITERIA="EXCLUSION_CRITERIA"; TARGET_ROLE="TARGET_ROLE"; REQUIRED_CONTACTABILITY="REQUIRED_CONTACTABILITY"
class ReadinessLevel(str, Enum): READY="READY"; PARTIAL="PARTIAL"; BLOCKED="BLOCKED"
@dataclass(frozen=True, slots=True)
class ICPReadinessSnapshot:
    canonical_predicates:frozenset[str]=frozenset(); candidate_predicates:frozenset[str]=frozenset(); unresolved_predicates:frozenset[str]=frozenset(); professional_role_count:int=0; validated_contact_kinds:frozenset[str]=frozenset(); qualification_operators:frozenset[str]=frozenset({"EQ","IN","EXISTS","CONTAINS"}); qualification_signal_predicates:frozenset[str]=frozenset(); deliverability_verified:bool=False
    def __post_init__(self):
        if self.professional_role_count<0: raise ValueError("professional_role_count cannot be negative")
@dataclass(frozen=True, slots=True)
class DimensionAssessment:
    dimension:ICPDimension; readiness:ReadinessLevel; observed_support:tuple[str,...]; blockers:tuple[str,...]; business_definition_required:bool=True
@dataclass(frozen=True, slots=True)
class ICPDecisionSupportReport:
    assessments:tuple[DimensionAssessment,...]
    @property
    def ready(self): return sum(a.readiness is ReadinessLevel.READY for a in self.assessments)
    @property
    def partial(self): return sum(a.readiness is ReadinessLevel.PARTIAL for a in self.assessments)
    @property
    def blocked(self): return sum(a.readiness is ReadinessLevel.BLOCKED for a in self.assessments)
    @property
    def total(self): return len(self.assessments)
def _has_any(values:frozenset[str], candidates:Iterable[str])->tuple[str,...]: return tuple(sorted(set(values).intersection(candidates)))
def assess_icp_readiness(snapshot:ICPReadinessSnapshot)->ICPDecisionSupportReport:
    canonical=snapshot.canonical_predicates; candidates=snapshot.candidate_predicates; unresolved=snapshot.unresolved_predicates; signals=snapshot.qualification_signal_predicates; items=[]
    market=_has_any(canonical,("target_market","market_segment")); items.append(DimensionAssessment(ICPDimension.TARGET_MARKET,ReadinessLevel.READY if market else ReadinessLevel.BLOCKED,market,() if market else ("no canonical target-market/segment evidence; B2B remains a hypothesis, not an ICP",)))
    ic=_has_any(canonical,("industry","primary_cnae_code","primary_cnae_description")); ia=_has_any(candidates,("industry","primary_cnae_code","primary_cnae_description")); items.append(DimensionAssessment(ICPDimension.INDUSTRY,ReadinessLevel.READY if ic else ReadinessLevel.PARTIAL if ia else ReadinessLevel.BLOCKED,ic or ia,() if ic else ("industry evidence exists but is not canonical/qualification-ready",) if ia else ("no industry/CNAE evidence available",)))
    gc=_has_any(canonical,("country","state","city")); ga=_has_any(candidates,("country","state","city")); gx=_has_any(unresolved,("country","state","city")); gl=ReadinessLevel.READY if gc and not gx and not(set(ga)-set(gc)) else ReadinessLevel.PARTIAL if gc or ga else ReadinessLevel.BLOCKED; gb=[]
    if gx: gb.append("geography has unresolved conflicting fields")
    if set(ga)-set(gc): gb.append("some geography evidence is not canonical")
    if not(gc or ga): gb.append("no geography evidence available")
    items.append(DimensionAssessment(ICPDimension.GEOGRAPHY,gl,tuple(sorted(set(gc+ga))),tuple(gb)))

    # Registry `porte` is useful size evidence but is not equivalent to employee
    # count, revenue, or a business-defined size band. Keep it PARTIAL even when
    # canonical until the business explicitly accepts registry class semantics.
    full_size_canonical=_has_any(canonical,("company_size","employee_count","revenue","size_band")); full_size_candidate=_has_any(candidates,("company_size","employee_count","revenue","size_band")); registry_size_canonical=_has_any(canonical,("registry_size_class","registry_size_code")); registry_size_candidate=_has_any(candidates,("registry_size_class","registry_size_code"))
    if full_size_canonical:
        size_level=ReadinessLevel.READY; size_support=full_size_canonical; size_blockers=()
    elif registry_size_canonical:
        size_level=ReadinessLevel.PARTIAL; size_support=registry_size_canonical; size_blockers=("registry size classification is canonical, but it is not employee count/revenue and its commercial meaning must be chosen explicitly",)
    elif full_size_candidate or registry_size_candidate:
        size_level=ReadinessLevel.PARTIAL; size_support=full_size_candidate or registry_size_candidate; size_blockers=("size evidence exists but is not fully qualification-ready or its business semantics are not defined",)
    else:
        size_level=ReadinessLevel.BLOCKED; size_support=(); size_blockers=("no company-size evidence/source is implemented",)
    items.append(DimensionAssessment(ICPDimension.COMPANY_SIZE,size_level,size_support,size_blockers))

    bf=("registration_status","website","domain","social_activity","technology","hiring_signal","growth_signal"); bc=_has_any(canonical,bf); ba=_has_any(candidates,bf); items.append(DimensionAssessment(ICPDimension.BUSINESS_SIGNAL,ReadinessLevel.READY if bc else ReadinessLevel.PARTIAL if ba else ReadinessLevel.BLOCKED,bc or ba,() if bc else ("business-signal evidence exists but is not canonical/qualification-ready",) if ba else ("no business-signal evidence is currently qualification-ready",)))
    neg=bool(snapshot.qualification_operators.intersection({"NE","NOT_IN","NOT_EXISTS","NOT_CONTAINS"})); items.append(DimensionAssessment(ICPDimension.EXCLUSION_CRITERIA,ReadinessLevel.READY if neg else ReadinessLevel.PARTIAL,tuple(sorted(snapshot.qualification_operators)),() if neg else ("qualification engine has no first-class negative/exclusion operator",)))
    role_signal="professional_role_title" in signals
    if snapshot.professional_role_count>0:
        rl=ReadinessLevel.READY if role_signal else ReadinessLevel.PARTIAL; rb=() if role_signal else ("role evidence exists, but qualification currently evaluates CanonicalFact only",); rs=(f"professional_roles={snapshot.professional_role_count}",)+(('professional_role_title signal',) if role_signal else ())
    else: rl=ReadinessLevel.BLOCKED; rb=("no evidence-backed professional roles available",); rs=()
    items.append(DimensionAssessment(ICPDimension.TARGET_ROLE,rl,rs,rb))
    contact_signal=bool(signals.intersection({"validated_contact_kind","validated_contact_present"}))
    if snapshot.validated_contact_kinds:
        cb=[]
        if not contact_signal: cb.append("validated ContactPoint evidence is not directly consumable by qualification")
        if not snapshot.deliverability_verified: cb.append("current contact validation proves official publication/corroboration, not deliverability or reachability")
        cl=ReadinessLevel.READY if contact_signal and snapshot.deliverability_verified else ReadinessLevel.PARTIAL; cs=tuple(sorted(snapshot.validated_contact_kinds))+(("qualification contact signal",) if contact_signal else ())
    else: cl=ReadinessLevel.BLOCKED; cs=(); cb=["no validated contact evidence available"]
    items.append(DimensionAssessment(ICPDimension.REQUIRED_CONTACTABILITY,cl,cs,tuple(cb)))
    return ICPDecisionSupportReport(tuple(items))
def acceptance_fixture_snapshot()->ICPReadinessSnapshot:
    return ICPReadinessSnapshot(canonical_predicates=frozenset({"business_registry_id","state"}),candidate_predicates=frozenset({"business_registry_id","legal_name","trade_name","registration_status","primary_cnae_code","primary_cnae_description","city","state","address","postal_code","activity_start_date"}),unresolved_predicates=frozenset({"city"}),professional_role_count=1,validated_contact_kinds=frozenset({"EMAIL","PHONE"}),qualification_operators=frozenset({"EQ","IN","EXISTS","CONTAINS"}),deliverability_verified=False)
def qualification_bridge_snapshot()->ICPReadinessSnapshot:
    base=acceptance_fixture_snapshot(); return ICPReadinessSnapshot(canonical_predicates=base.canonical_predicates,candidate_predicates=base.candidate_predicates,unresolved_predicates=base.unresolved_predicates,professional_role_count=base.professional_role_count,validated_contact_kinds=base.validated_contact_kinds,qualification_operators=frozenset({"EQ","NE","IN","NOT_IN","EXISTS","NOT_EXISTS","CONTAINS","NOT_CONTAINS"}),qualification_signal_predicates=frozenset({"professional_role_title","validated_contact_kind","validated_contact_present"}),deliverability_verified=False)
def qualification_field_canonicalization_snapshot()->ICPReadinessSnapshot:
    base=qualification_bridge_snapshot(); return ICPReadinessSnapshot(canonical_predicates=base.canonical_predicates.union({"primary_cnae_code","primary_cnae_description","registration_status"}),candidate_predicates=base.candidate_predicates,unresolved_predicates=base.unresolved_predicates,professional_role_count=base.professional_role_count,validated_contact_kinds=base.validated_contact_kinds,qualification_operators=base.qualification_operators,qualification_signal_predicates=base.qualification_signal_predicates,deliverability_verified=False)
def registry_size_signal_snapshot()->ICPReadinessSnapshot:
    base=qualification_field_canonicalization_snapshot(); return ICPReadinessSnapshot(canonical_predicates=base.canonical_predicates.union({"registry_size_class"}),candidate_predicates=base.candidate_predicates.union({"registry_size_class"}),unresolved_predicates=base.unresolved_predicates,professional_role_count=base.professional_role_count,validated_contact_kinds=base.validated_contact_kinds,qualification_operators=base.qualification_operators,qualification_signal_predicates=base.qualification_signal_predicates,deliverability_verified=False)
