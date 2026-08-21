"""ICP decision-support without defining an ICP.

This module measures whether each handoff ICP dimension has evidence that is
usable by the current qualification path. It never supplies target values,
weights, thresholds, or a default policy.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class ICPDimension(str, Enum):
    TARGET_MARKET = "TARGET_MARKET"
    INDUSTRY = "INDUSTRY"
    GEOGRAPHY = "GEOGRAPHY"
    COMPANY_SIZE = "COMPANY_SIZE"
    BUSINESS_SIGNAL = "BUSINESS_SIGNAL"
    EXCLUSION_CRITERIA = "EXCLUSION_CRITERIA"
    TARGET_ROLE = "TARGET_ROLE"
    REQUIRED_CONTACTABILITY = "REQUIRED_CONTACTABILITY"


class ReadinessLevel(str, Enum):
    READY = "READY"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class ICPReadinessSnapshot:
    canonical_predicates: frozenset[str] = frozenset()
    candidate_predicates: frozenset[str] = frozenset()
    unresolved_predicates: frozenset[str] = frozenset()
    professional_role_count: int = 0
    validated_contact_kinds: frozenset[str] = frozenset()
    qualification_operators: frozenset[str] = frozenset({"EQ", "IN", "EXISTS", "CONTAINS"})
    deliverability_verified: bool = False

    def __post_init__(self) -> None:
        if self.professional_role_count < 0:
            raise ValueError("professional_role_count cannot be negative")


@dataclass(frozen=True, slots=True)
class DimensionAssessment:
    dimension: ICPDimension
    readiness: ReadinessLevel
    observed_support: tuple[str, ...]
    blockers: tuple[str, ...]
    business_definition_required: bool = True


@dataclass(frozen=True, slots=True)
class ICPDecisionSupportReport:
    assessments: tuple[DimensionAssessment, ...]

    @property
    def ready(self) -> int:
        return sum(a.readiness is ReadinessLevel.READY for a in self.assessments)

    @property
    def partial(self) -> int:
        return sum(a.readiness is ReadinessLevel.PARTIAL for a in self.assessments)

    @property
    def blocked(self) -> int:
        return sum(a.readiness is ReadinessLevel.BLOCKED for a in self.assessments)

    @property
    def total(self) -> int:
        return len(self.assessments)


def _has_any(values: frozenset[str], candidates: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(set(values).intersection(candidates)))


def assess_icp_readiness(snapshot: ICPReadinessSnapshot) -> ICPDecisionSupportReport:
    canonical = snapshot.canonical_predicates
    candidates = snapshot.candidate_predicates
    unresolved = snapshot.unresolved_predicates
    items: list[DimensionAssessment] = []

    market_support = _has_any(canonical, ("target_market", "market_segment"))
    items.append(DimensionAssessment(
        ICPDimension.TARGET_MARKET,
        ReadinessLevel.READY if market_support else ReadinessLevel.BLOCKED,
        market_support,
        () if market_support else ("no canonical target-market/segment evidence; B2B remains a hypothesis, not an ICP",),
    ))

    industry_canonical = _has_any(canonical, ("industry", "primary_cnae_code", "primary_cnae_description"))
    industry_candidate = _has_any(candidates, ("industry", "primary_cnae_code", "primary_cnae_description"))
    if industry_canonical:
        industry_level = ReadinessLevel.READY
        industry_blockers = ()
        industry_support = industry_canonical
    elif industry_candidate:
        industry_level = ReadinessLevel.PARTIAL
        industry_blockers = ("industry evidence exists but is not canonical/qualification-ready",)
        industry_support = industry_candidate
    else:
        industry_level = ReadinessLevel.BLOCKED
        industry_blockers = ("no industry/CNAE evidence available",)
        industry_support = ()
    items.append(DimensionAssessment(ICPDimension.INDUSTRY, industry_level, industry_support, industry_blockers))

    geo_canonical = _has_any(canonical, ("country", "state", "city"))
    geo_candidate = _has_any(candidates, ("country", "state", "city"))
    geo_conflicts = _has_any(unresolved, ("country", "state", "city"))
    if geo_canonical and not geo_conflicts:
        geo_level = ReadinessLevel.READY
        geo_blockers = ()
    elif geo_canonical or geo_candidate:
        geo_level = ReadinessLevel.PARTIAL
        geo_blockers = tuple(filter(None, (
            "geography has unresolved conflicting fields" if geo_conflicts else "",
            "some geography evidence is not canonical" if set(geo_candidate) - set(geo_canonical) else "",
        )))
    else:
        geo_level = ReadinessLevel.BLOCKED
        geo_blockers = ("no geography evidence available",)
    items.append(DimensionAssessment(ICPDimension.GEOGRAPHY, geo_level, tuple(sorted(set(geo_canonical + geo_candidate))), geo_blockers))

    size_canonical = _has_any(canonical, ("company_size", "employee_count", "revenue", "size_band"))
    size_candidate = _has_any(candidates, ("company_size", "employee_count", "revenue", "size_band"))
    if size_canonical:
        size_level, size_support, size_blockers = ReadinessLevel.READY, size_canonical, ()
    elif size_candidate:
        size_level, size_support, size_blockers = ReadinessLevel.PARTIAL, size_candidate, ("size evidence is not canonical/qualification-ready",)
    else:
        size_level, size_support, size_blockers = ReadinessLevel.BLOCKED, (), ("no company-size evidence/source is implemented",)
    items.append(DimensionAssessment(ICPDimension.COMPANY_SIZE, size_level, size_support, size_blockers))

    business_fields = ("registration_status", "website", "domain", "social_activity", "technology", "hiring_signal", "growth_signal")
    signal_canonical = _has_any(canonical, business_fields)
    signal_candidate = _has_any(candidates, business_fields)
    if signal_canonical:
        signal_level, signal_support, signal_blockers = ReadinessLevel.READY, signal_canonical, ()
    elif signal_candidate:
        signal_level, signal_support, signal_blockers = ReadinessLevel.PARTIAL, signal_candidate, ("business-signal evidence exists but is not canonical/qualification-ready",)
    else:
        signal_level, signal_support, signal_blockers = ReadinessLevel.BLOCKED, (), ("no business-signal evidence is currently qualification-ready",)
    items.append(DimensionAssessment(ICPDimension.BUSINESS_SIGNAL, signal_level, signal_support, signal_blockers))

    has_negative_operator = bool(snapshot.qualification_operators.intersection({"NE", "NOT_IN", "NOT_EXISTS", "NOT_CONTAINS"}))
    items.append(DimensionAssessment(
        ICPDimension.EXCLUSION_CRITERIA,
        ReadinessLevel.READY if has_negative_operator else ReadinessLevel.PARTIAL,
        tuple(sorted(snapshot.qualification_operators)),
        () if has_negative_operator else ("qualification engine has no first-class negative/exclusion operator",),
    ))

    if snapshot.professional_role_count > 0:
        role_level = ReadinessLevel.PARTIAL
        role_support = (f"professional_roles={snapshot.professional_role_count}",)
        role_blockers = ("role evidence exists, but qualification currently evaluates CanonicalFact only",)
    else:
        role_level = ReadinessLevel.BLOCKED
        role_support = ()
        role_blockers = ("no evidence-backed professional roles available",)
    items.append(DimensionAssessment(ICPDimension.TARGET_ROLE, role_level, role_support, role_blockers))

    if snapshot.validated_contact_kinds:
        contact_level = ReadinessLevel.PARTIAL
        contact_support = tuple(sorted(snapshot.validated_contact_kinds))
        blockers = ["validated ContactPoint evidence is not directly consumable by the CanonicalFact-only qualification engine"]
        if not snapshot.deliverability_verified:
            blockers.append("current contact validation proves official publication/corroboration, not deliverability or reachability")
        contact_blockers = tuple(blockers)
    else:
        contact_level = ReadinessLevel.BLOCKED
        contact_support = ()
        contact_blockers = ("no validated contact evidence available",)
    items.append(DimensionAssessment(ICPDimension.REQUIRED_CONTACTABILITY, contact_level, contact_support, contact_blockers))

    return ICPDecisionSupportReport(tuple(items))


def acceptance_fixture_snapshot() -> ICPReadinessSnapshot:
    """Snapshot of the accepted deterministic full-run, not a population estimate."""
    return ICPReadinessSnapshot(
        canonical_predicates=frozenset({"business_registry_id", "state"}),
        candidate_predicates=frozenset({
            "business_registry_id", "legal_name", "trade_name", "registration_status",
            "primary_cnae_code", "primary_cnae_description", "city", "state",
            "address", "postal_code", "activity_start_date",
        }),
        unresolved_predicates=frozenset({"city"}),
        professional_role_count=1,
        validated_contact_kinds=frozenset({"EMAIL", "PHONE"}),
        qualification_operators=frozenset({"EQ", "IN", "EXISTS", "CONTAINS"}),
        deliverability_verified=False,
    )
