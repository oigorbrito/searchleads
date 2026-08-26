"""Bounded public-web discovery recipe for the approved Dental ICP.

This module is transport-neutral. It builds deterministic search queries from
explicit approved-policy filters and converts already-captured public search
observations into conservative CFO-pending candidates. It is not a crawler and
never treats public CRO/title text as official registration verification.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import re
import unicodedata
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit

from searchleads.qualification_policy import (
    APPROVED_DENTAL_ICP_POLICY_V1,
    DentalICPPolicyContractV1,
)

RECIPE_ID = "dental_public_web_discovery_v1"

BRAZIL_STATES = (
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
)

_QUERY_TEMPLATES = {
    "GENERAL_DENTIST": '"cirurgião-dentista" CRO',
    "DENTAL_SPECIALIST": 'dentista CRO "cirurgia facial"',
    "BUCOMAXILLOFACIAL": "bucomaxilofacial CRO",
    "HOF_OR_FACIAL_ACTIVITY": '"harmonização orofacial" CRO dentista',
}

_FACIAL_TERMS = (
    "blefaroplastia", "lip lift", "liplift", "lifting facial", "frontoplastia",
    "cirurgia facial", "estetica facial", "harmonizacao orofacial",
)

_BUCOMAX_PATTERNS = (
    "bucomax", "buco maxilo", "buco-maxilo", "bucomaxilofacial",
    "cirurgia e traumatologia bucomaxilofacial",
)
_HOF_PATTERNS = ("harmonizacao orofacial", "harmonizacao facial")
_OTHER_DENTAL_PATTERNS = (
    "odontolog", "ortodont", "endodont", "periodont", "implantodont",
    "odontopediatr", "estomatolog", "protesista", "prostodont",
)

_CRO_PATTERNS = (
    re.compile(r"\bCRO[\s-]*([A-Z]{2})[\s:#-]*(\d{3,7})\b", re.I),
    re.compile(r"\bCRO[\s:#-]*(\d{3,7})\s*/\s*([A-Z]{2})\b", re.I),
    re.compile(r"\b([A-Z]{2})-CD-(\d{3,7})\b", re.I),
    re.compile(r"\b(\d{3,7})\s+CRO\s*([A-Z]{2})\b", re.I),
)


class CFOVerificationStatus(StrEnum):
    PENDING = "PENDING"


@dataclass(frozen=True, slots=True)
class DentalDiscoveryQuery:
    query_id: str
    query: str
    professional_group: str
    state: str | None
    recipe_id: str = RECIPE_ID

    def __post_init__(self) -> None:
        if not self.query_id.strip() or not self.query.strip():
            raise ValueError("query identity/text must be non-blank")
        if self.professional_group not in APPROVED_DENTAL_ICP_POLICY_V1.eligible_professional_groups:
            raise ValueError("professional_group is not part of the approved Dental policy")
        if self.state is not None and self.state not in BRAZIL_STATES:
            raise ValueError("state must be a Brazilian UF code")
        if self.recipe_id != RECIPE_ID:
            raise ValueError("recipe_id is fixed for Dental discovery V1")


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
            (self.observation_id, "observation_id"), (self.url, "url"),
            (self.title, "title"), (self.evidence_id, "evidence_id"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-blank")
        _normalized_url(self.url)
        if self.query_id is not None and not self.query_id.strip():
            raise ValueError("query_id must be non-blank when supplied")


@dataclass(frozen=True, slots=True)
class DentalDiscoveryCandidate:
    candidate_id: str
    display_name_hint: str
    source_url: str
    evidence_ids: tuple[str, ...]
    cro_state: str | None
    cro_number: str | None
    observed_professional_group: str | None
    facial_relevance_terms: tuple[str, ...]
    cfo_verification_status: CFOVerificationStatus = CFOVerificationStatus.PENDING
    recipe_id: str = RECIPE_ID

    def __post_init__(self) -> None:
        if not self.candidate_id.strip() or not self.display_name_hint.strip():
            raise ValueError("candidate identity/display hint must be non-blank")
        _normalized_url(self.source_url)
        if not self.evidence_ids or any(not item.strip() for item in self.evidence_ids):
            raise ValueError("candidate requires evidence IDs")
        if tuple(sorted(set(self.evidence_ids))) != self.evidence_ids:
            raise ValueError("candidate evidence IDs must be sorted and unique")
        if (self.cro_state is None) != (self.cro_number is None):
            raise ValueError("CRO state and number must be supplied together")
        if self.cro_state is not None and self.cro_state not in BRAZIL_STATES:
            raise ValueError("candidate CRO state must be a Brazilian UF code")
        if self.observed_professional_group is not None and self.observed_professional_group not in APPROVED_DENTAL_ICP_POLICY_V1.eligible_professional_groups:
            raise ValueError("candidate professional group is outside the approved policy")
        if self.cfo_verification_status is not CFOVerificationStatus.PENDING:
            raise ValueError("public-web discovery cannot promote CFO verification")
        if self.recipe_id != RECIPE_ID:
            raise ValueError("recipe_id is fixed for Dental discovery V1")

    @property
    def exact_cro_key(self) -> str | None:
        if self.cro_state is None:
            return None
        return f"CRO:{self.cro_state}:{self.cro_number}"


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold()
    text = "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))
    return " ".join(text.split())


def _normalized_url(url: str) -> str:
    try:
        parts = urlsplit(url.strip())
        port = parts.port
    except ValueError as exc:
        raise ValueError("public observation URL must be a valid absolute HTTP(S) URL") from exc
    scheme = parts.scheme.casefold()
    if scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
        raise ValueError("public observation URL must be an absolute HTTP(S) URL without credentials")
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    host = parts.hostname.casefold()
    netloc = host if port is None or default_port else f"{host}:{port}"
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((scheme, netloc, path, "", ""))


def _extract_cro(text: str) -> tuple[str | None, str | None]:
    for index, pattern in enumerate(_CRO_PATTERNS):
        match = pattern.search(text)
        if match is None:
            continue
        a, b = match.groups()
        state, number = (a, b) if index in (0, 2) else (b, a)
        state = state.upper()
        if state in BRAZIL_STATES:
            return state, number
    return None, None


def _classify_professional_group(text: str) -> str | None:
    folded = _fold(text)
    if any(pattern in folded for pattern in _BUCOMAX_PATTERNS):
        return "BUCOMAXILLOFACIAL"
    if any(pattern in folded for pattern in _HOF_PATTERNS) or re.search(r"(?<![a-z])hof(?![a-z])", folded):
        return "HOF_OR_FACIAL_ACTIVITY"
    if "dentista" in folded or "cirurgiao-dentista" in folded or "cirurgiao dentista" in folded:
        return "GENERAL_DENTIST"
    if any(pattern in folded for pattern in _OTHER_DENTAL_PATTERNS):
        return "DENTAL_SPECIALIST"
    return None


def build_dental_discovery_queries(
    policy: DentalICPPolicyContractV1 = APPROVED_DENTAL_ICP_POLICY_V1,
    *,
    states: Iterable[str] = (),
    professional_groups: Iterable[str] = (),
    max_queries: int = 20,
) -> tuple[DentalDiscoveryQuery, ...]:
    """Build a deterministic bounded query plan from explicit approved filters."""
    if policy != APPROVED_DENTAL_ICP_POLICY_V1:
        raise ValueError("Dental public discovery requires the exact approved V1 policy")
    if max_queries < 1:
        raise ValueError("max_queries must be >= 1")

    selected_states = tuple(sorted({state.strip().upper() for state in states}))
    if any(state not in BRAZIL_STATES for state in selected_states):
        raise ValueError("states must contain only Brazilian UF codes")
    state_scope: tuple[str | None, ...] = selected_states or (None,)

    requested_groups = tuple(professional_groups)
    if requested_groups:
        if any(group not in policy.eligible_professional_groups for group in requested_groups):
            raise ValueError("professional_groups must be approved Dental policy groups")
        selected_group_set = set(requested_groups)
        groups = tuple(group for group in policy.eligible_professional_groups if group in selected_group_set)
    else:
        groups = policy.eligible_professional_groups

    out: list[DentalDiscoveryQuery] = []
    for state in state_scope:
        location = state or "Brasil"
        for group in groups:
            template = _QUERY_TEMPLATES[group]
            query = f"{template} {location}"
            digest = hashlib.sha256(f"{RECIPE_ID}|{group}|{state or 'BR'}|{query}".encode()).hexdigest()[:16]
            out.append(DentalDiscoveryQuery(f"dental-query:{digest}", query, group, state))
            if len(out) >= max_queries:
                return tuple(out)
    return tuple(out)


def candidate_from_public_observation(observation: PublicSearchObservation) -> DentalDiscoveryCandidate | None:
    text = f"{observation.title}\n{observation.snippet}"
    cro_state, cro_number = _extract_cro(text)
    group = _classify_professional_group(text)
    folded = _fold(text)
    facial_terms = tuple(sorted({term for term in _FACIAL_TERMS if term in folded}))
    if cro_number is None and group is None and not facial_terms:
        return None

    normalized_url = _normalized_url(observation.url)
    key = f"{cro_state}:{cro_number}" if cro_state and cro_number else normalized_url
    digest = hashlib.sha256(f"{RECIPE_ID}|{key}".encode()).hexdigest()[:20]
    return DentalDiscoveryCandidate(
        candidate_id=f"dental-candidate:{digest}",
        display_name_hint=observation.title.strip(),
        source_url=normalized_url,
        evidence_ids=(observation.evidence_id,),
        cro_state=cro_state,
        cro_number=cro_number,
        observed_professional_group=group,
        facial_relevance_terms=facial_terms,
    )


def deduplicate_dental_candidates(candidates: Iterable[DentalDiscoveryCandidate]) -> tuple[DentalDiscoveryCandidate, ...]:
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
            observed_professional_group=previous.observed_professional_group or candidate.observed_professional_group,
            facial_relevance_terms=tuple(sorted(set(previous.facial_relevance_terms + candidate.facial_relevance_terms))),
        )
    return tuple(merged[key] for key in order)


def discover_dental_candidates(observations: Iterable[PublicSearchObservation]) -> tuple[DentalDiscoveryCandidate, ...]:
    candidates = tuple(
        candidate for observation in observations
        if (candidate := candidate_from_public_observation(observation)) is not None
    )
    return deduplicate_dental_candidates(candidates)
