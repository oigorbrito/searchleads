"""Deterministic company-field normalization for COMPANY_NORMALIZATION_V1.

Normalization is a projection over a source-derived CandidateFact. The persisted
raw candidate remains immutable; callers may recompute this projection from the
stored raw fact when rules evolve.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import re
import unicodedata
from typing import Any, Callable, Iterable
from urllib.parse import urlsplit, urlunsplit

from .domain import CandidateFact
from .persistence import SQLiteLeadStore


class NormalizationStatus(str, Enum):
    NORMALIZED = "NORMALIZED"
    UNCHANGED = "UNCHANGED"
    UNSUPPORTED = "UNSUPPORTED"
    INVALID = "INVALID"


class NormalizationError(ValueError):
    """Raised internally when a recognized field cannot be normalized safely."""


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    source_fact: CandidateFact
    normalized_fact: CandidateFact | None
    status: NormalizationStatus
    reason: str | None = None


Normalizer = Callable[[Any], tuple[Any, str]]


def _text(value: Any) -> str:
    if not isinstance(value, str):
        value = str(value)
    return " ".join(unicodedata.normalize("NFKC", value).split())


def _normalize_company_name(value: Any) -> tuple[str, str]:
    normalized = _text(value)
    if not normalized:
        raise NormalizationError("company name is blank")
    return normalized, "company_name_nfkc_whitespace_v1"


def _normalize_text(value: Any) -> tuple[str, str]:
    normalized = _text(value)
    if not normalized:
        raise NormalizationError("text value is blank")
    return normalized, "text_nfkc_whitespace_v1"


def _normalize_domain(value: Any) -> tuple[str, str]:
    raw = _text(value)
    if not raw:
        raise NormalizationError("domain is blank")

    candidate = raw
    if "://" not in candidate:
        candidate = "//" + candidate
    parsed = urlsplit(candidate)
    host = parsed.hostname
    if not host:
        raise NormalizationError("domain does not contain a valid host")
    try:
        normalized = host.rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise NormalizationError("domain cannot be converted to IDNA") from exc
    if not normalized or " " in normalized:
        raise NormalizationError("domain is invalid")
    return normalized, "domain_lower_idna_v1"


def _normalize_url(value: Any) -> tuple[str, str]:
    raw = _text(value)
    parsed = urlsplit(raw)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise NormalizationError("URL must contain an explicit http/https scheme and host")

    scheme = parsed.scheme.lower()
    host = parsed.hostname.rstrip(".").encode("idna").decode("ascii").lower()
    port = parsed.port
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None
    netloc = host if port is None else f"{host}:{port}"
    if parsed.username or parsed.password:
        raise NormalizationError("credential-bearing URLs are not normalized")

    normalized = urlunsplit((scheme, netloc, parsed.path or "", parsed.query, ""))
    return normalized, "url_scheme_host_fragment_v1"


def _normalize_phone(value: Any) -> tuple[str, str]:
    raw = _text(value)
    if not raw:
        raise NormalizationError("phone is blank")
    leading_plus = raw.lstrip().startswith("+")
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 7:
        raise NormalizationError("phone has too few digits")
    normalized = ("+" if leading_plus else "") + digits
    return normalized, "phone_punctuation_only_v1"


def _normalize_state(value: Any) -> tuple[str, str]:
    normalized = _text(value)
    if not normalized:
        raise NormalizationError("state is blank")
    if len(normalized) == 2 and normalized.isalpha():
        normalized = normalized.upper()
        return normalized, "state_two_letter_upper_v1"
    return normalized, "text_nfkc_whitespace_v1"


def _normalize_cnae(value: Any) -> tuple[str, str]:
    digits = re.sub(r"\D", "", str(value))
    if len(digits) != 7:
        raise NormalizationError("CNAE code must contain exactly 7 digits")
    return digits, "cnae_digits7_v1"


_NORMALIZERS: dict[str, Normalizer] = {
    "company_name": _normalize_company_name,
    "legal_name": _normalize_company_name,
    "trade_name": _normalize_company_name,
    "domain": _normalize_domain,
    "website": _normalize_url,
    "website_url": _normalize_url,
    "url": _normalize_url,
    "phone": _normalize_phone,
    "company_phone": _normalize_phone,
    "address": _normalize_text,
    "street_address": _normalize_text,
    "city": _normalize_text,
    "location": _normalize_text,
    "state": _normalize_state,
    "country": _normalize_text,
    "industry": _normalize_text,
    "industry_label": _normalize_text,
    "primary_cnae_description": _normalize_text,
    "primary_cnae_code": _normalize_cnae,
    "cnae_code": _normalize_cnae,
    "linkedin_url": _normalize_url,
    "instagram_url": _normalize_url,
    "social_profile_url": _normalize_url,
}


def normalize_candidate_fact(fact: CandidateFact) -> NormalizationResult:
    """Return a non-destructive normalized projection for one candidate fact."""

    normalizer = _NORMALIZERS.get(fact.predicate)
    if normalizer is None:
        return NormalizationResult(
            source_fact=fact,
            normalized_fact=None,
            status=NormalizationStatus.UNSUPPORTED,
            reason=f"no V1 normalizer for predicate {fact.predicate!r}",
        )

    try:
        normalized_value, rule = normalizer(fact.raw_value)
    except (NormalizationError, ValueError) as exc:
        return NormalizationResult(
            source_fact=fact,
            normalized_fact=None,
            status=NormalizationStatus.INVALID,
            reason=str(exc),
        )

    projected = replace(
        fact,
        normalized_value=normalized_value,
        normalization_rule=rule,
    )
    status = (
        NormalizationStatus.UNCHANGED
        if normalized_value == fact.raw_value
        else NormalizationStatus.NORMALIZED
    )
    return NormalizationResult(
        source_fact=fact,
        normalized_fact=projected,
        status=status,
    )


def normalize_candidate_facts(
    facts: Iterable[CandidateFact],
) -> tuple[NormalizationResult, ...]:
    return tuple(normalize_candidate_fact(fact) for fact in facts)


def normalize_persisted_candidate(
    store: SQLiteLeadStore,
    candidate_fact_id: str,
) -> NormalizationResult | None:
    """Recompute normalization from the immutable persisted raw candidate."""

    fact = store.get_candidate_fact(candidate_fact_id)
    if fact is None:
        return None
    return normalize_candidate_fact(fact)
