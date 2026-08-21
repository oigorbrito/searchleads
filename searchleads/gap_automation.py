"""Bounded gap detection and known-capability automation planning for Work Unit 14.

This module plans work; it does not run a generic scheduler. Requirements are
explicit inputs, and only already-implemented sources/capabilities may be
selected automatically.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
from typing import Iterable

from .domain import CanonicalFact, ContactPoint, ContactStatus, ProfessionalRole
from .qualification import QualificationResult

class GapKind(str, Enum):
    COMPANY_FIELD = "COMPANY_FIELD"
    VALIDATED_CONTACT = "VALIDATED_CONTACT"
    PERSON_ROLE = "PERSON_ROLE"
    QUALIFICATION = "QUALIFICATION"

class ActionKind(str, Enum):
    BRASILAPI_LOOKUP = "BRASILAPI_LOOKUP"
    OFFICIAL_LOCATION_ENRICHMENT = "OFFICIAL_LOCATION_ENRICHMENT"
    OFFICIAL_CONTACT_DISCOVERY = "OFFICIAL_CONTACT_DISCOVERY"
    OFFICIAL_PEOPLE_DISCOVERY = "OFFICIAL_PEOPLE_DISCOVERY"
    QUALIFICATION_EVALUATION = "QUALIFICATION_EVALUATION"

class ActionDisposition(str, Enum):
    READY = "READY"
    BLOCKED = "BLOCKED"

@dataclass(frozen=True, slots=True)
class GapRequirements:
    company_predicates: tuple[str, ...] = ()
    require_validated_contact: bool = False
    require_person_role: bool = False
    require_qualification: bool = False

@dataclass(frozen=True, slots=True)
class Gap:
    kind: GapKind
    key: str
    reason: str

@dataclass(frozen=True, slots=True)
class AutomationAction:
    action_id: str
    gap: Gap
    disposition: ActionDisposition
    action_kind: ActionKind | None
    reason: str
    retry_max_attempts: int
    cache_key: str
    min_interval_seconds: int

@dataclass(frozen=True, slots=True)
class AutomationPlan:
    company_id: str
    gaps: tuple[Gap, ...]
    actions: tuple[AutomationAction, ...]

_REGISTRY_FIELDS = {"business_registry_id", "legal_name", "trade_name", "registration_status", "primary_cnae_code", "primary_cnae_description", "city", "state"}
_LOCATION_FIELDS = {"street_address", "postal_code", "activity_start_date"}

def detect_gaps(company_id: str, requirements: GapRequirements, *, canonical_facts: Iterable[CanonicalFact] = (), contacts: Iterable[ContactPoint] = (), roles: Iterable[ProfessionalRole] = (), qualification: QualificationResult | None = None) -> tuple[Gap, ...]:
    present = {fact.predicate for fact in canonical_facts if fact.subject.entity_id == company_id}
    gaps: list[Gap] = []
    for predicate in requirements.company_predicates:
        if predicate not in present: gaps.append(Gap(GapKind.COMPANY_FIELD, predicate, f"missing canonical company field: {predicate}"))
    if requirements.require_validated_contact:
        ok = any(c.owner.entity_id == company_id and c.status is ContactStatus.VALIDATED for c in contacts)
        if not ok: gaps.append(Gap(GapKind.VALIDATED_CONTACT, "validated_contact", "no validated company contact is present"))
    if requirements.require_person_role:
        ok = any(role.company_id == company_id for role in roles)
        if not ok: gaps.append(Gap(GapKind.PERSON_ROLE, "person_role", "no evidence-backed person/company role is present"))
    if requirements.require_qualification and qualification is None:
        gaps.append(Gap(GapKind.QUALIFICATION, "qualification", "qualification has not been evaluated"))
    return tuple(gaps)

def _action_id(company_id: str, gap: Gap, action_kind: ActionKind | None) -> str:
    material = f"{company_id}|{gap.kind.value}|{gap.key}|{action_kind.value if action_kind else 'BLOCKED'}"
    return "automation:" + hashlib.sha256(material.encode()).hexdigest()[:24]

def _action_for_gap(company_id: str, gap: Gap, *, qualification_policy_id: str | None) -> AutomationAction:
    action_kind: ActionKind | None
    if gap.kind is GapKind.COMPANY_FIELD and gap.key in _REGISTRY_FIELDS:
        action_kind = ActionKind.BRASILAPI_LOOKUP; reason = "known structured registry source covers this field"
    elif gap.kind is GapKind.COMPANY_FIELD and gap.key in _LOCATION_FIELDS:
        action_kind = ActionKind.OFFICIAL_LOCATION_ENRICHMENT; reason = "known official location source covers this field"
    elif gap.kind is GapKind.VALIDATED_CONTACT:
        action_kind = ActionKind.OFFICIAL_CONTACT_DISCOVERY; reason = "known official contact-page capability can discover/corroborate contacts"
    elif gap.kind is GapKind.PERSON_ROLE:
        action_kind = ActionKind.OFFICIAL_PEOPLE_DISCOVERY; reason = "known official people-page capability covers person/role links"
    elif gap.kind is GapKind.QUALIFICATION and qualification_policy_id:
        action_kind = ActionKind.QUALIFICATION_EVALUATION; reason = "explicit qualification policy is available"
    else:
        action_kind = None; reason = "no implemented known source/capability can safely fill this gap" if gap.kind is not GapKind.QUALIFICATION else "qualification is blocked until an explicit policy/ICP is supplied"
    disposition = ActionDisposition.READY if action_kind else ActionDisposition.BLOCKED
    retry = 3 if action_kind in {ActionKind.BRASILAPI_LOOKUP, ActionKind.OFFICIAL_LOCATION_ENRICHMENT, ActionKind.OFFICIAL_CONTACT_DISCOVERY, ActionKind.OFFICIAL_PEOPLE_DISCOVERY} else 1
    interval = 60 if action_kind else 0
    cache_material = f"{company_id}|{gap.kind.value}|{gap.key}|{action_kind.value if action_kind else 'blocked'}"
    return AutomationAction(_action_id(company_id, gap, action_kind), gap, disposition, action_kind, reason, retry, "gap:" + hashlib.sha256(cache_material.encode()).hexdigest()[:24], interval)

def plan_gap_actions(company_id: str, requirements: GapRequirements, *, canonical_facts: Iterable[CanonicalFact] = (), contacts: Iterable[ContactPoint] = (), roles: Iterable[ProfessionalRole] = (), qualification: QualificationResult | None = None, qualification_policy_id: str | None = None) -> AutomationPlan:
    gaps = detect_gaps(company_id, requirements, canonical_facts=canonical_facts, contacts=contacts, roles=roles, qualification=qualification)
    return AutomationPlan(company_id, gaps, tuple(_action_for_gap(company_id, gap, qualification_policy_id=qualification_policy_id) for gap in gaps))
