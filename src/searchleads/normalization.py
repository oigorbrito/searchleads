"""Deterministic company-field normalization for COMPANY_NORMALIZATION_V1.

Normalization is a non-destructive projection over immutable source-derived
``CandidateFact`` records. It standardizes representation only; it does not
perform entity resolution, source fusion, canonicalization, geocoding, or
qualification.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
import ipaddress
import re
import unicodedata
from typing import Any, Callable, Iterable
from urllib.parse import SplitResult, urlsplit, urlunsplit

from .domain import CandidateFact
from .persistence import SQLiteRepository


class NormalizationStatus(StrEnum):
    NORMALIZED = "NORMALIZED"
    UNCHANGED = "UNCHANGED"
    UNSUPPORTED = "UNSUPPORTED"
    INVALID = "INVALID"


class NormalizationError(ValueError):
    """Raised internally when a recognized value cannot be normalized safely."""


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    """Auditable result of applying one explicit normalization rule."""

    source_fact: CandidateFact
    normalized_fact: CandidateFact | None
    status: NormalizationStatus
    normalization_rule: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        successful = self.status in {NormalizationStatus.NORMALIZED, NormalizationStatus.UNCHANGED}
        if successful:
            if self.normalized_fact is None or not self.normalization_rule:
                raise ValueError("successful normalization requires normalized_fact and normalization_rule")
        elif self.normalized_fact is not None or self.normalization_rule is not None:
            raise ValueError("unsuccessful normalization must not expose a projected fact or rule")


Normalizer = Callable[[Any], tuple[Any, str]]
_HOST_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise NormalizationError(f"{label} must be text")
    return value


def _nfkc_whitespace(value: Any, label: str) -> str:
    text = _require_text(value, label)
    return " ".join(unicodedata.normalize("NFKC", text).split())


def _normalize_company_name(value: Any) -> tuple[str, str]:
    normalized = _nfkc_whitespace(value, "company name")
    if not normalized:
        raise NormalizationError("company name is blank")
    return normalized, "company_name_nfkc_whitespace_v1"


def _normalize_text(value: Any) -> tuple[str, str]:
    normalized = _nfkc_whitespace(value, "text value")
    if not normalized:
        raise NormalizationError("text value is blank")
    return normalized, "text_nfkc_whitespace_v1"


def _normalize_host(host: str) -> str:
    host = host.rstrip(".")
    if not host:
        raise NormalizationError("host is blank")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        if re.fullmatch(r"[0-9.]+", host):
            raise NormalizationError("host looks like an invalid IP literal")
        try:
            normalized = host.encode("idna").decode("ascii").lower()
        except UnicodeError as exc:
            raise NormalizationError("host cannot be converted to IDNA") from exc
        labels = normalized.split(".")
        if len(normalized) > 253 or any(_HOST_LABEL.fullmatch(label) is None for label in labels):
            raise NormalizationError("host is invalid")
        return normalized
    return ip.compressed.lower()


def _normalize_domain(value: Any) -> tuple[str, str]:
    raw = _nfkc_whitespace(value, "domain")
    if not raw:
        raise NormalizationError("domain is blank")
    candidate = raw if "://" in raw else f"//{raw}"
    try:
        parsed = urlsplit(candidate)
        host = parsed.hostname
    except ValueError as exc:
        raise NormalizationError("domain is invalid") from exc
    if not host:
        raise NormalizationError("domain does not contain a valid host")
    return _normalize_host(host), "domain_lower_idna_v1"


def _normalized_netloc(parsed: SplitResult) -> str:
    if parsed.username is not None or parsed.password is not None:
        raise NormalizationError("credential-bearing URLs are not normalized")
    if not parsed.hostname:
        raise NormalizationError("URL host is missing")
    host = _normalize_host(parsed.hostname)
    try:
        port = parsed.port
    except ValueError as exc:
        raise NormalizationError("URL port is invalid") from exc
    scheme = parsed.scheme.lower()
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None
    display_host = f"[{host}]" if ":" in host else host
    return display_host if port is None else f"{display_host}:{port}"


def _normalize_url(value: Any) -> tuple[str, str]:
    raw = _nfkc_whitespace(value, "URL")
    if not raw:
        raise NormalizationError("URL is blank")
    try:
        parsed = urlsplit(raw)
    except ValueError as exc:
        raise NormalizationError("URL is invalid") from exc
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise NormalizationError("URL must contain an explicit http/https scheme")
    netloc = _normalized_netloc(parsed)
    normalized = urlunsplit((scheme, netloc, parsed.path, parsed.query, ""))
    return normalized, "url_scheme_host_fragment_v1"


def _normalize_phone(value: Any) -> tuple[str, str]:
    raw = _nfkc_whitespace(value, "phone")
    if not raw:
        raise NormalizationError("phone is blank")
    leading_plus = raw.startswith("+")
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 7:
        raise NormalizationError("phone has too few digits")
    normalized = ("+" if leading_plus else "") + digits
    return normalized, "phone_punctuation_only_v1"


def _normalize_state(value: Any) -> tuple[str, str]:
    normalized = _nfkc_whitespace(value, "state")
    if not normalized:
        raise NormalizationError("state is blank")
    if len(normalized) == 2 and normalized.isalpha():
        return normalized.upper(), "state_two_letter_upper_v1"
    return normalized, "text_nfkc_whitespace_v1"


def _normalize_cnae(value: Any) -> tuple[str, str]:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise NormalizationError("CNAE code must be text or integer")
    text = str(value)
    digits = re.sub(r"\D", "", text)
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
    "registration_status": _normalize_text,
    "primary_cnae_description": _normalize_text,
    "primary_cnae_code": _normalize_cnae,
    "cnae_code": _normalize_cnae,
    "linkedin_url": _normalize_url,
    "instagram_url": _normalize_url,
    "social_profile_url": _normalize_url,
}


def normalize_candidate_fact(fact: CandidateFact) -> NormalizationResult:
    """Return a non-destructive normalized projection for one candidate fact."""

    normalizer = _NORMALIZERS.get(fact.field_name)
    if normalizer is None:
        return NormalizationResult(
            source_fact=fact,
            normalized_fact=None,
            status=NormalizationStatus.UNSUPPORTED,
            reason=f"no V1 normalizer for field {fact.field_name!r}",
        )

    try:
        normalized_value, rule = normalizer(fact.raw_value)
    except NormalizationError as exc:
        return NormalizationResult(
            source_fact=fact,
            normalized_fact=None,
            status=NormalizationStatus.INVALID,
            reason=str(exc),
        )

    projected = replace(fact, normalized_value=normalized_value)
    status = (
        NormalizationStatus.UNCHANGED
        if normalized_value == fact.raw_value
        else NormalizationStatus.NORMALIZED
    )
    return NormalizationResult(
        source_fact=fact,
        normalized_fact=projected,
        status=status,
        normalization_rule=rule,
    )


def normalize_candidate_facts(facts: Iterable[CandidateFact]) -> tuple[NormalizationResult, ...]:
    """Normalize candidates in caller-supplied order without deduplication or fusion."""

    return tuple(normalize_candidate_fact(fact) for fact in facts)


def normalize_persisted_candidate(
    repository: SQLiteRepository,
    candidate_fact_id: str,
) -> NormalizationResult | None:
    """Reload an immutable raw candidate and recompute its V1 projection."""

    fact = repository.load(CandidateFact, candidate_fact_id)
    if fact is None:
        return None
    return normalize_candidate_fact(fact)


__all__ = [
    "NormalizationError",
    "NormalizationResult",
    "NormalizationStatus",
    "normalize_candidate_fact",
    "normalize_candidate_facts",
    "normalize_persisted_candidate",
]
