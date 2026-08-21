"""Business-defined ICP V1 for dental facial-surgery education leads.

This vertical policy is intentionally separate from the generic qualification engine.
It converts evidence-backed person/company-context signals into transparent FIT and
INTENT classifications for the user-defined Brazil-wide dental education ICP.

Absence of learning-intent evidence is UNKNOWN, never evidence of no interest.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import re
import unicodedata
from typing import Any, Iterable

from .domain import CanonicalFact, ContactPoint, ContactStatus, EntityType, LeadStatus, ProfessionalRole


class BrazilRegion(str, Enum):
    NORTH = "NORTH"
    NORTHEAST = "NORTHEAST"
    CENTRAL_WEST = "CENTRAL_WEST"
    SOUTHEAST = "SOUTHEAST"
    SOUTH = "SOUTH"


_STATE_TO_REGION = {
    "AC": BrazilRegion.NORTH, "AP": BrazilRegion.NORTH, "AM": BrazilRegion.NORTH,
    "PA": BrazilRegion.NORTH, "RO": BrazilRegion.NORTH, "RR": BrazilRegion.NORTH,
    "TO": BrazilRegion.NORTH,
    "AL": BrazilRegion.NORTHEAST, "BA": BrazilRegion.NORTHEAST,
    "CE": BrazilRegion.NORTHEAST, "MA": BrazilRegion.NORTHEAST,
    "PB": BrazilRegion.NORTHEAST, "PE": BrazilRegion.NORTHEAST,
    "PI": BrazilRegion.NORTHEAST, "RN": BrazilRegion.NORTHEAST,
    "SE": BrazilRegion.NORTHEAST,
    "DF": BrazilRegion.CENTRAL_WEST, "GO": BrazilRegion.CENTRAL_WEST,
    "MT": BrazilRegion.CENTRAL_WEST, "MS": BrazilRegion.CENTRAL_WEST,
    "ES": BrazilRegion.SOUTHEAST, "MG": BrazilRegion.SOUTHEAST,
    "RJ": BrazilRegion.SOUTHEAST, "SP": BrazilRegion.SOUTHEAST,
    "PR": BrazilRegion.SOUTH, "RS": BrazilRegion.SOUTH, "SC": BrazilRegion.SOUTH,
}


class DentalTitleGroup(str, Enum):
    GENERAL_DENTIST = "GENERAL_DENTIST"
    BUCOMAXILLOFACIAL = "BUCOMAXILLOFACIAL"
    HOF = "HOF"
    OTHER_DENTAL_SPECIALTY = "OTHER_DENTAL_SPECIALTY"


class OfferFormat(str, Enum):
    IN_PERSON = "IN_PERSON"
    IMMERSION = "IMMERSION"
    MENTORING = "MENTORING"
    LONG_FORM_TRAINING = "LONG_FORM_TRAINING"
    ONLINE_OR_HYBRID = "ONLINE_OR_HYBRID"


class FitLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class IntentLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class LeadPriority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    REVIEW = "REVIEW"
    EXCLUDE = "EXCLUDE"


class DentalSignalKind(str, Enum):
    PROFESSIONAL_TITLE = "PROFESSIONAL_TITLE"
    SPECIALTY = "SPECIALTY"
    PRACTICE_FOCUS = "PRACTICE_FOCUS"
    PROCEDURE = "PROCEDURE"
    STATE = "STATE"
    CITY = "CITY"
    COUNTRY = "COUNTRY"
    LEARNING_INTENT = "LEARNING_INTENT"
    VALIDATED_CONTACT = "VALIDATED_CONTACT"
    DISCOVERED_CONTACT = "DISCOVERED_CONTACT"


class DentalIntentSignal(str, Enum):
    PROCEDURE_LEARNING = "PROCEDURE_LEARNING"
    COURSE_INTEREST = "COURSE_INTEREST"
    TRAINING_PARTICIPATION = "TRAINING_PARTICIPATION"
    CONTINUING_EDUCATION = "CONTINUING_EDUCATION"
    EDUCATION_CONTENT_ENGAGEMENT = "EDUCATION_CONTENT_ENGAGEMENT"
    EXPLICIT_NO_INTEREST = "EXPLICIT_NO_INTEREST"


@dataclass(frozen=True, slots=True)
class DentalICPSignal:
    signal_id: str
    person_id: str
    kind: DentalSignalKind
    value: Any
    evidence_ids: tuple[str, ...]
    company_id: str | None = None

    def __post_init__(self) -> None:
        if not self.signal_id.strip() or not self.person_id.strip():
            raise ValueError("signal_id and person_id must be non-blank")
        if self.company_id is not None and not self.company_id.strip():
            raise ValueError("company_id must be non-blank when supplied")
        if not self.evidence_ids or any(not item.strip() for item in self.evidence_ids):
            raise ValueError("every ICP signal must carry at least one evidence ID")


@dataclass(frozen=True, slots=True)
class DentalICPSelection:
    regions: tuple[BrazilRegion, ...] = ()
    states: tuple[str, ...] = ()
    title_groups: tuple[DentalTitleGroup, ...] = (
        DentalTitleGroup.GENERAL_DENTIST,
        DentalTitleGroup.BUCOMAXILLOFACIAL,
        DentalTitleGroup.HOF,
        DentalTitleGroup.OTHER_DENTAL_SPECIALTY,
    )
    title_terms: tuple[str, ...] = ()
    require_validated_contact: bool = False

    def __post_init__(self) -> None:
        states = tuple(state.strip().upper() for state in self.states)
        if len(set(states)) != len(states):
            raise ValueError("states must not contain duplicates")
        unknown = tuple(state for state in states if state not in _STATE_TO_REGION)
        if unknown:
            raise ValueError(f"unknown Brazilian state abbreviations: {unknown}")
        if len(set(self.regions)) != len(self.regions):
            raise ValueError("regions must not contain duplicates")
        if not self.title_groups:
            raise ValueError("at least one title group must be enabled")
        if len(set(self.title_groups)) != len(self.title_groups):
            raise ValueError("title_groups must not contain duplicates")
        normalized_terms = tuple(term.strip() for term in self.title_terms)
        if any(not term for term in normalized_terms):
            raise ValueError("title_terms must be non-blank")
        object.__setattr__(self, "states", states)
        object.__setattr__(self, "title_terms", normalized_terms)


@dataclass(frozen=True, slots=True)
class DentalFacialSurgeryICPV1:
    policy_id: str = "dental-facial-surgery-education-br-v1"
    country: str = "BR"
    core_procedures: tuple[str, ...] = (
        "blefaroplastia",
        "lip lift",
        "lifting facial",
        "frontoplastia",
    )
    offer_formats: tuple[OfferFormat, ...] = (
        OfferFormat.IN_PERSON,
        OfferFormat.IMMERSION,
        OfferFormat.MENTORING,
        OfferFormat.LONG_FORM_TRAINING,
        OfferFormat.ONLINE_OR_HYBRID,
    )
    selection: DentalICPSelection = DentalICPSelection()
    decision_basis: str = "BUSINESS_REQUIREMENT_USER_DEFINED_2026_08_21"

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise ValueError("policy_id must be non-blank")
        if self.country != "BR":
            raise ValueError("ICP V1 is explicitly scoped to Brazil")
        if not self.core_procedures or not self.offer_formats:
            raise ValueError("core procedures and offer formats must be explicit")


DEFAULT_DENTAL_FACIAL_SURGERY_ICP_V1 = DentalFacialSurgeryICPV1()


@dataclass(frozen=True, slots=True)
class DentalPersonQualificationResult:
    person_id: str
    company_id: str | None
    policy_id: str
    status: LeadStatus
    fit: FitLevel
    intent: IntentLevel
    priority: LeadPriority
    title_groups: tuple[DentalTitleGroup, ...]
    state: str | None
    region: BrazilRegion | None
    has_professional_contact: bool
    has_validated_contact: bool
    reasons: tuple[str, ...]
    signal_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    text = "".join(
        ch for ch in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(ch)
    )
    return " ".join(text.split())


def brazil_region_for_state(state: str | None) -> BrazilRegion | None:
    if state is None:
        return None
    return _STATE_TO_REGION.get(state.strip().upper())


_BUCOMAX_PATTERNS = (
    "bucomax", "buco maxilo", "buco-maxilo", "bucomaxilofacial",
    "cirurgia e traumatologia bucomaxilofacial",
)
_HOF_PATTERNS = ("harmonizacao orofacial", "harmonizacao facial")
_OTHER_DENTAL_PATTERNS = (
    "odontolog", "ortodont", "endodont", "periodont", "implantodont",
    "odontopediatr", "estomatolog", "protesista", "prostodont",
)


def classify_dental_title(value: Any) -> DentalTitleGroup | None:
    text = _fold(value)
    if any(pattern in text for pattern in _BUCOMAX_PATTERNS):
        return DentalTitleGroup.BUCOMAXILLOFACIAL
    if any(pattern in text for pattern in _HOF_PATTERNS) or re.search(r"(?<![a-z])hof(?![a-z])", text):
        return DentalTitleGroup.HOF
    if "dentista" in text or "cirurgiao-dentista" in text or "cirurgiao dentista" in text:
        return DentalTitleGroup.GENERAL_DENTIST
    if any(pattern in text for pattern in _OTHER_DENTAL_PATTERNS):
        return DentalTitleGroup.OTHER_DENTAL_SPECIALTY
    return None


_FACIAL_RELEVANCE_TERMS = (
    "blefaroplastia", "lip lift", "liplift", "lifting facial", "frontoplastia",
    "cirurgia facial", "estetica facial", "harmonizacao orofacial",
)


def _is_facially_relevant(value: Any) -> bool:
    text = _fold(value)
    return any(term in text for term in _FACIAL_RELEVANCE_TERMS)


def select_dental_icp(
    base: DentalFacialSurgeryICPV1 = DEFAULT_DENTAL_FACIAL_SURGERY_ICP_V1,
    *,
    regions: Iterable[BrazilRegion] | None = None,
    states: Iterable[str] | None = None,
    title_groups: Iterable[DentalTitleGroup] | None = None,
    title_terms: Iterable[str] | None = None,
    require_validated_contact: bool | None = None,
) -> DentalFacialSurgeryICPV1:
    current = base.selection
    selection = DentalICPSelection(
        regions=current.regions if regions is None else tuple(regions),
        states=current.states if states is None else tuple(states),
        title_groups=current.title_groups if title_groups is None else tuple(title_groups),
        title_terms=current.title_terms if title_terms is None else tuple(title_terms),
        require_validated_contact=(
            current.require_validated_contact
            if require_validated_contact is None
            else require_validated_contact
        ),
    )
    return replace(base, selection=selection)


def signals_from_existing_evidence(
    person_id: str,
    *,
    company_id: str | None = None,
    roles: Iterable[ProfessionalRole] = (),
    contacts: Iterable[ContactPoint] = (),
    canonical_facts: Iterable[CanonicalFact] = (),
) -> tuple[DentalICPSignal, ...]:
    """Bridge existing evidence-backed records into vertical ICP signals.

    The bridge does not infer a specialty or intent. It only projects fields that
    already exist in ProfessionalRole, ContactPoint or CanonicalFact records.
    """
    out: list[DentalICPSignal] = []

    for role in roles:
        if role.person_id != person_id:
            continue
        if company_id is not None and role.company_id != company_id:
            continue
        out.append(DentalICPSignal(
            signal_id=f"icp-role:{role.role_id}",
            person_id=person_id,
            company_id=role.company_id,
            kind=DentalSignalKind.PROFESSIONAL_TITLE,
            value=role.title,
            evidence_ids=tuple(role.provenance.evidence_ids),
        ))

    predicate_map = {
        "professional_title": DentalSignalKind.PROFESSIONAL_TITLE,
        "specialty": DentalSignalKind.SPECIALTY,
        "practice_focus": DentalSignalKind.PRACTICE_FOCUS,
        "procedure": DentalSignalKind.PROCEDURE,
        "education_intent": DentalSignalKind.LEARNING_INTENT,
        "state": DentalSignalKind.STATE,
        "city": DentalSignalKind.CITY,
        "country": DentalSignalKind.COUNTRY,
    }
    for fact in canonical_facts:
        is_person = fact.subject.entity_type is EntityType.PERSON and fact.subject.entity_id == person_id
        is_company_context = (
            company_id is not None
            and fact.subject.entity_type is EntityType.COMPANY
            and fact.subject.entity_id == company_id
            and fact.predicate in {"state", "city", "country"}
        )
        if not (is_person or is_company_context):
            continue
        kind = predicate_map.get(fact.predicate)
        if kind is None:
            continue
        out.append(DentalICPSignal(
            signal_id=f"icp-fact:{fact.canonical_fact_id}",
            person_id=person_id,
            company_id=company_id,
            kind=kind,
            value=fact.value,
            evidence_ids=tuple(fact.provenance.evidence_ids),
        ))

    for contact in contacts:
        person_owned = (
            contact.owner.entity_type is EntityType.PERSON
            and contact.owner.entity_id == person_id
        )
        company_owned = (
            company_id is not None
            and contact.owner.entity_type is EntityType.COMPANY
            and contact.owner.entity_id == company_id
        )
        if not (person_owned or company_owned):
            continue
        kind = (
            DentalSignalKind.VALIDATED_CONTACT
            if contact.status is ContactStatus.VALIDATED
            else DentalSignalKind.DISCOVERED_CONTACT
        )
        out.append(DentalICPSignal(
            signal_id=f"icp-contact:{contact.contact_id}",
            person_id=person_id,
            company_id=company_id,
            kind=kind,
            value=contact.kind.value,
            evidence_ids=tuple(contact.provenance.evidence_ids),
        ))

    return tuple(out)


def _intent_level(signals: tuple[DentalICPSignal, ...]) -> tuple[IntentLevel, tuple[str, ...]]:
    values = {
        str(signal.value.value if isinstance(signal.value, DentalIntentSignal) else signal.value)
        for signal in signals
        if signal.kind is DentalSignalKind.LEARNING_INTENT
    }
    if DentalIntentSignal.EXPLICIT_NO_INTEREST.value in values:
        return IntentLevel.LOW, ("explicit evidence of no current learning interest",)
    if values & {
        DentalIntentSignal.PROCEDURE_LEARNING.value,
        DentalIntentSignal.COURSE_INTEREST.value,
    }:
        return IntentLevel.HIGH, ("explicit evidence of procedure/course learning interest",)
    if values & {
        DentalIntentSignal.TRAINING_PARTICIPATION.value,
        DentalIntentSignal.CONTINUING_EDUCATION.value,
        DentalIntentSignal.EDUCATION_CONTENT_ENGAGEMENT.value,
    }:
        return IntentLevel.MEDIUM, ("evidence of continuing education/training activity",)
    return IntentLevel.UNKNOWN, ("no evidence-backed learning-intent signal is available",)


def _priority(fit: FitLevel, intent: IntentLevel) -> LeadPriority:
    if fit is FitLevel.LOW:
        return LeadPriority.EXCLUDE
    if fit is FitLevel.UNKNOWN:
        return LeadPriority.REVIEW
    if fit is FitLevel.HIGH and intent is IntentLevel.HIGH:
        return LeadPriority.P1
    if (fit is FitLevel.HIGH and intent in {IntentLevel.MEDIUM, IntentLevel.UNKNOWN}) or (
        fit is FitLevel.MEDIUM and intent is IntentLevel.HIGH
    ):
        return LeadPriority.P2
    if fit in {FitLevel.HIGH, FitLevel.MEDIUM}:
        return LeadPriority.P3
    return LeadPriority.REVIEW


def qualify_dental_person(
    person_id: str,
    signals: Iterable[DentalICPSignal],
    *,
    company_id: str | None = None,
    icp: DentalFacialSurgeryICPV1 = DEFAULT_DENTAL_FACIAL_SURGERY_ICP_V1,
) -> DentalPersonQualificationResult:
    items = tuple(signal for signal in signals if signal.person_id == person_id)
    reasons: list[str] = []

    title_signals = tuple(
        signal for signal in items
        if signal.kind in {DentalSignalKind.PROFESSIONAL_TITLE, DentalSignalKind.SPECIALTY}
    )
    groups = tuple(dict.fromkeys(
        group
        for signal in title_signals
        for group in (classify_dental_title(signal.value),)
        if group is not None
    ))

    state_values = tuple(
        str(signal.value).strip().upper()
        for signal in items if signal.kind is DentalSignalKind.STATE
    )
    state = next((value for value in state_values if value in _STATE_TO_REGION), None)
    region = brazil_region_for_state(state)

    selection = icp.selection
    geographic_unknown = False
    geographic_excluded = False
    if selection.states:
        if state is None:
            geographic_unknown = True
            reasons.append("state filter is active but state evidence is missing")
        elif state not in selection.states:
            geographic_excluded = True
            reasons.append(f"state {state} is outside selected states")
    if selection.regions:
        if region is None:
            geographic_unknown = True
            reasons.append("region filter is active but Brazilian state evidence is missing")
        elif region not in selection.regions:
            geographic_excluded = True
            reasons.append(f"region {region.value} is outside selected regions")

    title_unknown = not groups
    title_excluded = bool(groups) and not any(group in selection.title_groups for group in groups)
    if title_unknown:
        reasons.append("dental profession/title evidence is missing or unrecognized")
    elif title_excluded:
        reasons.append("recognized dental title is outside selected title groups")

    if selection.title_terms:
        observed = tuple(_fold(signal.value) for signal in title_signals)
        required = tuple(_fold(term) for term in selection.title_terms)
        if not observed:
            title_unknown = True
            reasons.append("title-term filter is active but title evidence is missing")
        elif not any(term in value for term in required for value in observed):
            title_excluded = True
            reasons.append("professional title does not match selected title terms")

    relevant = any(
        _is_facially_relevant(signal.value)
        for signal in items
        if signal.kind in {
            DentalSignalKind.SPECIALTY,
            DentalSignalKind.PRACTICE_FOCUS,
            DentalSignalKind.PROCEDURE,
        }
    )
    specific_title = any(
        group in {DentalTitleGroup.BUCOMAXILLOFACIAL, DentalTitleGroup.HOF}
        for group in groups
    )

    has_validated_contact = any(
        signal.kind is DentalSignalKind.VALIDATED_CONTACT for signal in items
    )
    has_professional_contact = has_validated_contact or any(
        signal.kind is DentalSignalKind.DISCOVERED_CONTACT for signal in items
    )
    contact_blocked = selection.require_validated_contact and not has_validated_contact
    if contact_blocked:
        reasons.append("validated professional contact is required by the active selection")

    if geographic_excluded or title_excluded or contact_blocked:
        fit = FitLevel.LOW
        status = LeadStatus.NOT_QUALIFIED
    elif geographic_unknown or title_unknown:
        fit = FitLevel.UNKNOWN
        status = LeadStatus.UNKNOWN
    elif specific_title or relevant:
        fit = FitLevel.HIGH
        status = LeadStatus.QUALIFIED
        if specific_title:
            reasons.append("target dental specialty/title is evidence-backed")
        if relevant:
            reasons.append("facial surgery/aesthetics relevance is evidence-backed")
    else:
        fit = FitLevel.MEDIUM
        status = LeadStatus.QUALIFIED
        reasons.append("evidence-backed dentist profile is eligible; facial relevance not yet observed")

    intent, intent_reasons = _intent_level(items)
    reasons.extend(intent_reasons)
    priority = _priority(fit, intent)

    used_ids = tuple(sorted({signal.signal_id for signal in items}))
    evidence_ids = tuple(sorted({
        evidence_id for signal in items for evidence_id in signal.evidence_ids
    }))

    return DentalPersonQualificationResult(
        person_id=person_id,
        company_id=company_id,
        policy_id=icp.policy_id,
        status=status,
        fit=fit,
        intent=intent,
        priority=priority,
        title_groups=groups,
        state=state,
        region=region,
        has_professional_contact=has_professional_contact,
        has_validated_contact=has_validated_contact,
        reasons=tuple(dict.fromkeys(reasons)),
        signal_ids=used_ids,
        evidence_ids=evidence_ids,
    )
