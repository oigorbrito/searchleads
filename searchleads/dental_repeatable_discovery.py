"""Bounded repeatable public-web discovery recipe for the dental MVP.

This is deliberately not a generic crawler. It generates deterministic search
queries from the explicit dental ICP and converts externally retrieved public
search observations into conservative candidates for CFO verification.

Discovery never creates learning intent and never treats a claimed CRO/title as
officially verified. Exact CRO or exact normalized URL may deduplicate discovery
observations; names are never used as an automatic identity key.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import re
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit

from .dental_facial_surgery_icp import (
    BrazilRegion,
    DentalFacialSurgeryICPV1,
    DentalTitleGroup,
    DEFAULT_DENTAL_FACIAL_SURGERY_ICP_V1,
    brazil_region_for_state,
    classify_dental_title,
)

RECIPE_ID = "dental_public_web_discovery_v1"

_BRAZIL_STATES = (
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
)

_QUERY_TEMPLATES = (
    (DentalTitleGroup.GENERAL_DENTIST, '"cirurgião-dentista" CRO'),
    (DentalTitleGroup.BUCOMAXILLOFACIAL, 'bucomaxilofacial CRO'),
    (DentalTitleGroup.HOF, '"harmonização orofacial" CRO dentista'),
    (DentalTitleGroup.OTHER_DENTAL_SPECIALTY, 'dentista CRO "cirurgia facial"'),
)

_FACIAL_TERMS = (
    "blefaroplastia",
    "lip lift",
    "liplift",
    "lifting facial",
    "frontoplastia",
    "cirurgia facial",
    "harmonização orofacial",
    "harmonizacao orofacial",
)


class CFOVerificationStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    NOT_VERIFIED = "NOT_VERIFIED"


@dataclass(frozen=True, slots=True)
class DentalDiscoveryQuery:
    query_id: str
    query: str
    title_group: DentalTitleGroup
    state: str | None
    region: BrazilRegion | None
    recipe_id: str = RECIPE_ID


@dataclass(frozen=True, slots=True)
class PublicSearchObservation:
    observation_id: str
    url: str
    title: str
    snippet: str
    evidence_id: str
    query_id: str | None = None

    def __post_init__(self) -> None:
        for value, name in (
            (self.observation_id, "observation_id"),
            (self.url, "url"),
            (self.title, "title"),
            (self.evidence_id, "evidence_id"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-blank")


@dataclass(frozen=True, slots=True)
class DentalDiscoveryCandidate:
    candidate_id: str
    display_name_hint: str
    source_url: str
    evidence_ids: tuple[str, ...]
    cro_state: str | None
    cro_number: str | None
    observed_title_group: DentalTitleGroup | None
    facial_relevance_terms: tuple[str, ...]
    cfo_verification_status: CFOVerificationStatus = CFOVerificationStatus.PENDING
    recipe_id: str = RECIPE_ID

    @property
    def exact_cro_key(self) -> str | None:
        if self.cro_state and self.cro_number:
            return f"CRO:{self.cro_state}:{self.cro_number}"
        return None


_CRO_PATTERNS = (
    re.compile(r"\bCRO[\s-]*([A-Z]{2})[\s:#-]*(\d{3,7})\b", re.I),
    re.compile(r"\bCRO[\s:#-]*(\d{3,7})\s*/\s*([A-Z]{2})\b", re.I),
    re.compile(r"\b([A-Z]{2})-CD-(\d{3,7})\b", re.I),
    re.compile(r"\b(\d{3,7})\s+CRO\s*([A-Z]{2})\b", re.I),
)


def _normalized_url(url: str) -> str:
    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))


def _extract_cro(text: str) -> tuple[str | None, str | None]:
    for index, pattern in enumerate(_CRO_PATTERNS):
        match = pattern.search(text)
        if not match:
            continue
        a, b = match.groups()
        if index in (0, 2):
            state, number = a, b
        else:
            number, state = a, b
        state = state.upper()
        if state in _BRAZIL_STATES:
            return state, number
    return None, None


def _selected_states(icp: DentalFacialSurgeryICPV1) -> tuple[str | None, ...]:
    if icp.selection.states:
        return tuple(icp.selection.states)
    if icp.selection.regions:
        return tuple(
            state for state in _BRAZIL_STATES
            if brazil_region_for_state(state) in set(icp.selection.regions)
        )
    return (None,)


def build_dental_discovery_queries(
    icp: DentalFacialSurgeryICPV1 = DEFAULT_DENTAL_FACIAL_SURGERY_ICP_V1,
    *,
    max_queries: int = 20,
) -> tuple[DentalDiscoveryQuery, ...]:
    """Build a deterministic bounded query plan from the active ICP selection."""
    if max_queries < 1:
        raise ValueError("max_queries must be >= 1")
    enabled = set(icp.selection.title_groups)
    templates = tuple(item for item in _QUERY_TEMPLATES if item[0] in enabled)
    if not templates:
        return ()

    out: list[DentalDiscoveryQuery] = []
    for state in _selected_states(icp):
        location = "Brasil" if state is None else state
        region = brazil_region_for_state(state) if state else None
        for title_group, template in templates:
            query = f"{template} {location}".strip()
            digest = hashlib.sha256(
                f"{RECIPE_ID}|{title_group.value}|{state or 'BR'}|{query}".encode("utf-8")
            ).hexdigest()[:16]
            out.append(DentalDiscoveryQuery(
                query_id=f"dental-query:{digest}",
                query=query,
                title_group=title_group,
                state=state,
                region=region,
            ))
            if len(out) >= max_queries:
                return tuple(out)
    return tuple(out)


def candidate_from_public_observation(
    observation: PublicSearchObservation,
) -> DentalDiscoveryCandidate | None:
    """Convert one public search observation into a CFO-pending candidate.

    A candidate requires at least one explicit dental/CRO/facial signal. The
    search snippet is discovery evidence only; it cannot verify registration or
    create a learning-intent signal.
    """
    text = f"{observation.title}\n{observation.snippet}"
    cro_state, cro_number = _extract_cro(text)
    title_group = classify_dental_title(text)
    folded = text.casefold()
    facial_terms = tuple(sorted({term for term in _FACIAL_TERMS if term in folded}))
    if cro_number is None and title_group is None and not facial_terms:
        return None

    normalized_url = _normalized_url(observation.url)
    key = f"{cro_state}:{cro_number}" if cro_state and cro_number else normalized_url
    digest = hashlib.sha256(f"{RECIPE_ID}|{key}".encode("utf-8")).hexdigest()[:20]
    return DentalDiscoveryCandidate(
        candidate_id=f"dental-candidate:{digest}",
        display_name_hint=observation.title.strip(),
        source_url=normalized_url,
        evidence_ids=(observation.evidence_id,),
        cro_state=cro_state,
        cro_number=cro_number,
        observed_title_group=title_group,
        facial_relevance_terms=facial_terms,
    )


def deduplicate_dental_candidates(
    candidates: Iterable[DentalDiscoveryCandidate],
) -> tuple[DentalDiscoveryCandidate, ...]:
    """Deduplicate only on exact CRO or exact normalized URL.

    Name similarity is intentionally excluded because NAME MATCH != ENTITY MATCH.
    Evidence IDs from exact duplicates are unioned for later verification.
    """
    merged: dict[str, DentalDiscoveryCandidate] = {}
    order: list[str] = []
    for candidate in candidates:
        key = candidate.exact_cro_key or f"URL:{_normalized_url(candidate.source_url)}"
        previous = merged.get(key)
        if previous is None:
            merged[key] = candidate
            order.append(key)
            continue
        merged[key] = DentalDiscoveryCandidate(
            candidate_id=previous.candidate_id,
            display_name_hint=previous.display_name_hint,
            source_url=previous.source_url,
            evidence_ids=tuple(sorted(set(previous.evidence_ids + candidate.evidence_ids))),
            cro_state=previous.cro_state,
            cro_number=previous.cro_number,
            observed_title_group=previous.observed_title_group or candidate.observed_title_group,
            facial_relevance_terms=tuple(sorted(set(previous.facial_relevance_terms + candidate.facial_relevance_terms))),
            cfo_verification_status=CFOVerificationStatus.PENDING,
        )
    return tuple(merged[key] for key in order)


def discover_dental_candidates(
    observations: Iterable[PublicSearchObservation],
) -> tuple[DentalDiscoveryCandidate, ...]:
    candidates = tuple(
        candidate
        for observation in observations
        if (candidate := candidate_from_public_observation(observation)) is not None
    )
    return deduplicate_dental_candidates(candidates)
