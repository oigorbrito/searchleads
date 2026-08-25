"""Bounded gap detection and known-capability planning for GAP_DETECTION_AND_AUTOMATION_V1.

The module only plans work. It never launches background execution, invents a
source, crawls the web, or upgrades a prerequisite acquisition into a verified
fact. Requirements and action inputs are explicit caller data.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import re
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit

from searchleads.domain import (
    CandidateFact,
    CanonicalFact,
    ContactPoint,
    ContactStatus,
    Lead,
    Person,
    QualificationStatus,
)


ROLE_FIELD = "professional_role_title"
BRASILAPI_FIELDS = frozenset({
    "business_registry_id",
    "legal_name",
    "trade_name",
    "registration_status",
    "primary_cnae_code",
    "primary_cnae_description",
    "city",
    "state",
})
_CNPJ_FORMATTING = re.compile(r"[.\-/\s]")
_CNPJ_KEY = re.compile(r"^[0-9A-Z]{14}$")


class GapKind(StrEnum):
    COMPANY_FIELD = "COMPANY_FIELD"
    VALIDATED_COMPANY_CONTACT = "VALIDATED_COMPANY_CONTACT"
    PERSON_ROLE = "PERSON_ROLE"
    QUALIFICATION = "QUALIFICATION"


class ActionKind(StrEnum):
    BRASILAPI_POINT_LOOKUP = "BRASILAPI_POINT_LOOKUP"
    COMPANY_CONTACT_PAGE_INGEST = "COMPANY_CONTACT_PAGE_INGEST"
    PERSON_ROLE_PAGE_INGEST = "PERSON_ROLE_PAGE_INGEST"
    CONTACT_PUBLICATION_VALIDATION = "CONTACT_PUBLICATION_VALIDATION"


class ActionDisposition(StrEnum):
    READY = "READY"
    BLOCKED = "BLOCKED"


class ActionEffect(StrEnum):
    PREREQUISITE = "PREREQUISITE"
    DIRECT = "DIRECT"
    NONE = "NONE"


@dataclass(frozen=True, slots=True)
class GapRequirements:
    company_fields: tuple[str, ...] = ()
    require_validated_company_contact: bool = False
    require_person_role: bool = False
    require_qualification: bool = False

    def __post_init__(self) -> None:
        if any(not item.strip() for item in self.company_fields):
            raise ValueError("company_fields must not contain blanks")


@dataclass(frozen=True, slots=True)
class AutomationInputs:
    known_cnpj: str | None = None
    company_contact_page_urls: tuple[str, ...] = ()
    people_page_url: str | None = None
    validation_contact_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.known_cnpj is not None:
            _normalize_cnpj(self.known_cnpj)
        if any(not value.strip() for value in self.company_contact_page_urls):
            raise ValueError("company_contact_page_urls must not contain blanks")
        for value in self.company_contact_page_urls:
            _normalize_http_url(value)
        if self.people_page_url is not None:
            _normalize_http_url(self.people_page_url)
        if any(not value.strip() for value in self.validation_contact_ids):
            raise ValueError("validation_contact_ids must not contain blanks")


@dataclass(frozen=True, slots=True)
class Gap:
    gap_id: str
    kind: GapKind
    key: str
    reason: str

    def __post_init__(self) -> None:
        if not self.gap_id.strip() or not self.key.strip() or not self.reason.strip():
            raise ValueError("gap requires non-blank id, key, and reason")


@dataclass(frozen=True, slots=True)
class AutomationAction:
    action_id: str
    gap_id: str
    disposition: ActionDisposition
    action_kind: ActionKind | None
    effect: ActionEffect
    reason: str
    locator: str | None = None
    input_ids: tuple[str, ...] = ()
    retry_max_attempts: int = 0
    cache_key: str | None = None
    min_interval_seconds: int = 0

    def __post_init__(self) -> None:
        if not self.action_id.strip() or not self.gap_id.strip() or not self.reason.strip():
            raise ValueError("automation action requires non-blank identity and reason")
        if any(not value.strip() for value in self.input_ids):
            raise ValueError("input_ids must not contain blanks")
        if tuple(sorted(set(self.input_ids))) != self.input_ids:
            raise ValueError("input_ids must be sorted and unique")
        if self.disposition is ActionDisposition.READY:
            if self.action_kind is None or self.effect is ActionEffect.NONE:
                raise ValueError("READY action requires kind and non-NONE effect")
            if self.retry_max_attempts < 1 or self.cache_key is None:
                raise ValueError("READY action requires finite attempts and cache key")
            if self.min_interval_seconds < 0:
                raise ValueError("min_interval_seconds must be non-negative")
        else:
            if self.action_kind is not None or self.effect is not ActionEffect.NONE:
                raise ValueError("BLOCKED action cannot expose executable kind/effect")
            if self.retry_max_attempts != 0 or self.cache_key is not None or self.min_interval_seconds != 0:
                raise ValueError("BLOCKED action cannot carry retry/cache/rate-limit execution metadata")


@dataclass(frozen=True, slots=True)
class AutomationPlan:
    company_id: str
    requirements: GapRequirements
    gaps: tuple[Gap, ...]
    actions: tuple[AutomationAction, ...]

    def __post_init__(self) -> None:
        if not self.company_id.strip():
            raise ValueError("company_id must not be blank")
        gap_ids = {gap.gap_id for gap in self.gaps}
        if len(gap_ids) != len(self.gaps):
            raise ValueError("plan gap IDs must be unique")
        if any(action.gap_id not in gap_ids for action in self.actions):
            raise ValueError("every action must reference one plan gap")

    @property
    def ready_actions(self) -> tuple[AutomationAction, ...]:
        return tuple(action for action in self.actions if action.disposition is ActionDisposition.READY)

    @property
    def blocked_actions(self) -> tuple[AutomationAction, ...]:
        return tuple(action for action in self.actions if action.disposition is ActionDisposition.BLOCKED)


def _digest(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()


def _normalize_cnpj(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("known_cnpj must be text")
    compact = _CNPJ_FORMATTING.sub("", value).upper()
    if _CNPJ_KEY.fullmatch(compact) is None:
        raise ValueError("known_cnpj must contain exactly 14 characters from 0-9 or A-Z")
    return compact


def _normalize_http_url(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("automation URLs must be text")
    try:
        parsed = urlsplit(value.strip())
        port = parsed.port
    except ValueError as exc:
        raise ValueError("automation URL must be a valid absolute HTTP(S) URL") from exc
    scheme = parsed.scheme.casefold()
    if scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("automation URL must be a valid absolute HTTP(S) URL without credentials")
    default = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    host = parsed.hostname.casefold()
    netloc = host if port is None or default else f"{host}:{port}"
    path = parsed.path or "/"
    return urlunsplit((scheme, netloc, path, parsed.query, ""))


def _gap(company_id: str, kind: GapKind, key: str, reason: str) -> Gap:
    normalized_key = " ".join(key.split())
    material = _digest(company_id, kind.value, normalized_key)
    return Gap(f"gap:v1:{material}", kind, normalized_key, " ".join(reason.split()))


def detect_gaps(
    company_id: str,
    requirements: GapRequirements,
    *,
    canonical_facts: Iterable[CanonicalFact] = (),
    contacts: Iterable[ContactPoint] = (),
    people: Iterable[Person] = (),
    candidate_facts: Iterable[CandidateFact] = (),
    lead: Lead | None = None,
) -> tuple[Gap, ...]:
    """Detect only gaps explicitly requested by the caller."""
    if not company_id.strip():
        raise ValueError("company_id must not be blank")

    facts = tuple(canonical_facts)
    present_fields = {
        fact.field_name
        for fact in facts
        if fact.subject_id == company_id
    }
    requested_fields = tuple(sorted(set(field.strip() for field in requirements.company_fields)))
    gaps: list[Gap] = []
    for field_name in requested_fields:
        if field_name not in present_fields:
            gaps.append(_gap(
                company_id, GapKind.COMPANY_FIELD, field_name,
                f"missing required canonical company field: {field_name}",
            ))

    contact_records = tuple(contacts)
    if requirements.require_validated_company_contact:
        validated = any(
            contact.owner_id == company_id and contact.status is ContactStatus.VALIDATED
            for contact in contact_records
        )
        if not validated:
            gaps.append(_gap(
                company_id, GapKind.VALIDATED_COMPANY_CONTACT, "validated_company_contact",
                "no validated company-owned contact is present",
            ))

    people_records = tuple(person for person in people if person.company_id == company_id)
    if requirements.require_person_role:
        person_ids = {person.person_id for person in people_records}
        has_role = any(
            fact.subject_id in person_ids and fact.field_name == ROLE_FIELD
            for fact in candidate_facts
        )
        if not has_role:
            gaps.append(_gap(
                company_id, GapKind.PERSON_ROLE, "person_role",
                "no evidence-backed person role fact is present for this company",
            ))

    if requirements.require_qualification:
        qualified = lead is not None and lead.company_id == company_id and lead.qualification_status is not QualificationStatus.UNKNOWN
        if not qualified:
            gaps.append(_gap(
                company_id, GapKind.QUALIFICATION, "qualification",
                "qualification remains absent or UNKNOWN",
            ))

    return tuple(sorted(gaps, key=lambda item: (item.kind.value, item.key, item.gap_id)))


def _ready_action(
    company_id: str,
    gap: Gap,
    kind: ActionKind,
    effect: ActionEffect,
    reason: str,
    *,
    locator: str | None = None,
    input_ids: tuple[str, ...] = (),
    network: bool,
) -> AutomationAction:
    normalized_locator = _normalize_http_url(locator) if locator is not None else None
    ids = tuple(sorted(set(input_ids)))
    material = _digest(company_id, gap.gap_id, kind.value, normalized_locator or "", *ids)
    return AutomationAction(
        action_id=f"automation:v1:{material}",
        gap_id=gap.gap_id,
        disposition=ActionDisposition.READY,
        action_kind=kind,
        effect=effect,
        reason=" ".join(reason.split()),
        locator=normalized_locator,
        input_ids=ids,
        retry_max_attempts=3 if network else 1,
        cache_key=f"automation-cache:v1:{material}",
        min_interval_seconds=60 if network else 0,
    )


def _blocked_action(company_id: str, gap: Gap, reason: str) -> AutomationAction:
    material = _digest(company_id, gap.gap_id, "BLOCKED")
    return AutomationAction(
        action_id=f"automation:v1:{material}",
        gap_id=gap.gap_id,
        disposition=ActionDisposition.BLOCKED,
        action_kind=None,
        effect=ActionEffect.NONE,
        reason=" ".join(reason.split()),
    )


def _actions_for_gap(company_id: str, gap: Gap, inputs: AutomationInputs) -> tuple[AutomationAction, ...]:
    if gap.kind is GapKind.COMPANY_FIELD:
        if gap.key not in BRASILAPI_FIELDS:
            return (_blocked_action(
                company_id, gap,
                "no implemented clean-stack source is registered for this required company field",
            ),)
        if inputs.known_cnpj is None:
            return (_blocked_action(
                company_id, gap,
                "BrasilAPI point lookup requires an explicit known CNPJ routing key",
            ),)
        cnpj = _normalize_cnpj(inputs.known_cnpj)
        locator = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
        return (_ready_action(
            company_id, gap, ActionKind.BRASILAPI_POINT_LOOKUP, ActionEffect.PREREQUISITE,
            "existing WU3 point lookup can acquire source evidence/candidate facts for this field; canonicalization remains separate",
            locator=locator, input_ids=(cnpj,), network=True,
        ),)

    if gap.kind is GapKind.VALIDATED_COMPANY_CONTACT:
        validation_ids = tuple(sorted(set(inputs.validation_contact_ids)))
        if len(validation_ids) >= 2:
            return (_ready_action(
                company_id, gap, ActionKind.CONTACT_PUBLICATION_VALIDATION, ActionEffect.DIRECT,
                "existing WU9 publication-corroboration method can evaluate the explicitly supplied contact observations",
                input_ids=validation_ids, network=False,
            ),)
        urls = tuple(sorted({_normalize_http_url(url) for url in inputs.company_contact_page_urls}))
        if urls:
            return tuple(_ready_action(
                company_id, gap, ActionKind.COMPANY_CONTACT_PAGE_INGEST, ActionEffect.PREREQUISITE,
                "existing WU7 page ingestion can create discovery evidence/contact observations; validation still requires independent corroboration",
                locator=url, network=True,
            ) for url in urls)
        return (_blocked_action(
            company_id, gap,
            "validated-contact gap needs either at least two explicit contact observation IDs or explicit company contact-page URLs",
        ),)

    if gap.kind is GapKind.PERSON_ROLE:
        if inputs.people_page_url is None:
            return (_blocked_action(
                company_id, gap,
                "person/role discovery requires an explicit people/leadership page URL",
            ),)
        return (_ready_action(
            company_id, gap, ActionKind.PERSON_ROLE_PAGE_INGEST, ActionEffect.PREREQUISITE,
            "existing WU8 people-page ingestion can create evidence-backed Person and role candidate facts",
            locator=inputs.people_page_url, network=True,
        ),)

    if gap.kind is GapKind.QUALIFICATION:
        return (_blocked_action(
            company_id, gap,
            "no qualification engine/ICP capability exists in the clean stack; planning cannot invent one",
        ),)

    raise ValueError(f"unsupported gap kind: {gap.kind}")


def plan_gap_actions(
    company_id: str,
    requirements: GapRequirements,
    *,
    inputs: AutomationInputs = AutomationInputs(),
    canonical_facts: Iterable[CanonicalFact] = (),
    contacts: Iterable[ContactPoint] = (),
    people: Iterable[Person] = (),
    candidate_facts: Iterable[CandidateFact] = (),
    lead: Lead | None = None,
) -> AutomationPlan:
    gaps = detect_gaps(
        company_id, requirements,
        canonical_facts=canonical_facts,
        contacts=contacts,
        people=people,
        candidate_facts=candidate_facts,
        lead=lead,
    )
    actions = tuple(
        action
        for gap in gaps
        for action in _actions_for_gap(company_id, gap, inputs)
    )
    actions = tuple(sorted(actions, key=lambda item: (
        item.gap_id,
        item.disposition.value,
        item.action_kind.value if item.action_kind else "",
        item.locator or "",
        item.action_id,
    )))
    return AutomationPlan(company_id, requirements, gaps, actions)
