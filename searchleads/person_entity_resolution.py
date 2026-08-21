"""Conservative person entity resolution for evidence-backed professional identities.

Same-name people are never assumed to be the same person. Strong identity-bearing
signals (profile URL / professional email) are separated from contextual signals
(company / role / location), and no opaque weights are used.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit
from typing import Iterable


@dataclass(frozen=True, slots=True)
class PersonRecord:
    record_id: str
    name: str | None = None
    company_id: str | None = None
    role: str | None = None
    location: str | None = None
    profile_url: str | None = None
    professional_email: str | None = None


@dataclass(frozen=True, slots=True)
class PersonMatchFeatures:
    name_exact: bool | None
    company_exact: bool | None
    role_exact: bool | None
    location_exact: bool | None
    profile_url_exact: bool | None
    professional_email_exact: bool | None


class PersonResolutionDisposition(str, Enum):
    AUTO_MATCH = "AUTO_MATCH"
    REVIEW = "REVIEW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True, slots=True)
class PersonResolutionDecision:
    disposition: PersonResolutionDisposition
    features: PersonMatchFeatures
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LabeledPersonPair:
    pair_id: str
    left: PersonRecord
    right: PersonRecord
    is_same_person: bool
    category: str


@dataclass(frozen=True, slots=True)
class PersonResolutionMetrics:
    auto_true: int
    auto_false: int
    review_true: int
    review_false: int
    unresolved_true: int
    unresolved_false: int

    @property
    def auto_precision(self) -> float:
        total = self.auto_true + self.auto_false
        return self.auto_true / total if total else 0.0

    @property
    def duplicate_coverage_with_review(self) -> float:
        total = self.auto_true + self.review_true + self.unresolved_true
        return (self.auto_true + self.review_true) / total if total else 0.0


def _fold(value: str | None) -> str | None:
    if value is None:
        return None
    text = " ".join(unicodedata.normalize("NFKC", value).split()).casefold()
    if not text:
        return None
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(ch)
    )


def _email(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip().casefold()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", text):
        return None
    return text


def _profile(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    try:
        parts = urlsplit(text)
    except ValueError:
        return None
    if parts.scheme.casefold() not in {"http", "https"} or not parts.hostname:
        return None
    host = parts.hostname.casefold()
    port = parts.port
    netloc = host if port is None else f"{host}:{port}"
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.casefold(), netloc, path, parts.query, ""))


def _exact(left: str | None, right: str | None, normalizer=_fold) -> bool | None:
    a = normalizer(left)
    b = normalizer(right)
    return None if a is None or b is None else a == b


def compare_person_features(left: PersonRecord, right: PersonRecord) -> PersonMatchFeatures:
    return PersonMatchFeatures(
        name_exact=_exact(left.name, right.name),
        company_exact=_exact(left.company_id, right.company_id),
        role_exact=_exact(left.role, right.role),
        location_exact=_exact(left.location, right.location),
        profile_url_exact=_exact(left.profile_url, right.profile_url, _profile),
        professional_email_exact=_exact(left.professional_email, right.professional_email, _email),
    )


def resolve_person_pair(left: PersonRecord, right: PersonRecord) -> PersonResolutionDecision:
    features = compare_person_features(left, right)

    # Strong identifier evidence may auto-match only when the published human
    # name also agrees. This avoids treating shared/functional accounts as IDs.
    if features.name_exact is True and features.profile_url_exact is True:
        return PersonResolutionDecision(
            PersonResolutionDisposition.AUTO_MATCH,
            features,
            ("name_exact", "profile_url_exact"),
        )
    if features.name_exact is True and features.professional_email_exact is True:
        return PersonResolutionDecision(
            PersonResolutionDisposition.AUTO_MATCH,
            features,
            ("name_exact", "professional_email_exact"),
        )

    # Context can justify review, never irreversible auto-merge in V1.
    contextual = tuple(
        label
        for label, flag in (
            ("company_exact", features.company_exact),
            ("role_exact", features.role_exact),
            ("location_exact", features.location_exact),
        )
        if flag is True
    )
    if features.name_exact is True and len(contextual) >= 2:
        return PersonResolutionDecision(
            PersonResolutionDisposition.REVIEW,
            features,
            ("name_exact",) + contextual,
        )

    # Same name + one company/role context signal remains ambiguous but
    # reviewable. Same name + location alone is deliberately insufficient.
    if features.name_exact is True and (
        features.company_exact is True or features.role_exact is True
    ):
        reasons = ["name_exact"]
        if features.company_exact is True:
            reasons.append("company_exact")
        if features.role_exact is True:
            reasons.append("role_exact")
        return PersonResolutionDecision(
            PersonResolutionDisposition.REVIEW,
            features,
            tuple(reasons),
        )

    return PersonResolutionDecision(
        PersonResolutionDisposition.INSUFFICIENT_EVIDENCE,
        features,
        ("no_v1_person_identity_rule",),
    )


def evaluate_person_resolution(pairs: Iterable[LabeledPersonPair]) -> PersonResolutionMetrics:
    auto_true = auto_false = review_true = review_false = unresolved_true = unresolved_false = 0
    for pair in pairs:
        disposition = resolve_person_pair(pair.left, pair.right).disposition
        if disposition is PersonResolutionDisposition.AUTO_MATCH:
            if pair.is_same_person:
                auto_true += 1
            else:
                auto_false += 1
        elif disposition is PersonResolutionDisposition.REVIEW:
            if pair.is_same_person:
                review_true += 1
            else:
                review_false += 1
        else:
            if pair.is_same_person:
                unresolved_true += 1
            else:
                unresolved_false += 1
    return PersonResolutionMetrics(
        auto_true,
        auto_false,
        review_true,
        review_false,
        unresolved_true,
        unresolved_false,
    )
