"""Conservative, measured Person entity-resolution decision layer."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re
import unicodedata
from typing import Iterable, Sequence
from urllib.parse import urlsplit

from searchleads.domain import CandidateFact, ContactKind, ContactPoint, Person

NAME_FIELD = "person_name"
ROLE_FIELD = "professional_role_title"


class PersonResolutionDisposition(StrEnum):
    REVIEW = "REVIEW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True, slots=True)
class EvidenceSignal:
    value: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("signal value must not be blank")
        if not self.evidence_ids or any(not item.strip() for item in self.evidence_ids):
            raise ValueError("signal requires non-blank evidence_ids")


@dataclass(frozen=True, slots=True)
class PersonRecord:
    record_id: str
    company_id: str
    relationship_evidence_ids: tuple[str, ...]
    names: tuple[EvidenceSignal, ...] = ()
    roles: tuple[EvidenceSignal, ...] = ()
    emails: tuple[EvidenceSignal, ...] = ()
    phones: tuple[EvidenceSignal, ...] = ()
    professional_profiles: tuple[EvidenceSignal, ...] = ()

    def __post_init__(self) -> None:
        if not self.record_id.strip() or not self.company_id.strip():
            raise ValueError("record_id and company_id must not be blank")
        if not self.relationship_evidence_ids or any(not x.strip() for x in self.relationship_evidence_ids):
            raise ValueError("Person ER record requires relationship evidence")

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        ids = set(self.relationship_evidence_ids)
        for group in (self.names, self.roles, self.emails, self.phones, self.professional_profiles):
            for signal in group:
                ids.update(signal.evidence_ids)
        return tuple(sorted(ids))


@dataclass(frozen=True, slots=True)
class PersonMatchFeatures:
    same_company: bool
    name_exact: bool | None
    role_exact: bool | None
    email_overlap: bool | None
    phone_overlap: bool | None
    professional_profile_overlap: bool | None
    relationship_evidence_overlap: bool


@dataclass(frozen=True, slots=True)
class PersonTriageDecision:
    disposition: PersonResolutionDisposition
    features: PersonMatchFeatures
    reasons: tuple[str, ...]
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LabeledPersonPair:
    pair_id: str
    left: PersonRecord
    right: PersonRecord
    is_same_person: bool
    category: str

    def __post_init__(self) -> None:
        if not self.pair_id.strip() or not self.category.strip():
            raise ValueError("pair_id and category must not be blank")
        if self.left.record_id == self.right.record_id:
            raise ValueError("labeled pair records must be distinct observations")


@dataclass(frozen=True, slots=True)
class ExperimentalAutoMatchMetrics:
    pairs: int
    same_person_pairs: int
    distinct_person_pairs: int
    candidate_matches: int
    true_positive: int
    false_positive: int
    precision: float | None
    recall: float
    false_merge_rate: float


@dataclass(frozen=True, slots=True)
class PersonResolutionMetrics:
    pairs: int
    same_person_pairs: int
    distinct_person_pairs: int
    reviews: int
    insufficient: int
    review_rate: float
    insufficient_rate: float
    positive_review_recall: float


def _fold(value: str) -> str:
    text = " ".join(unicodedata.normalize("NFKC", value).split()).casefold()
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def _email(value: str) -> str | None:
    value = value.strip().casefold()
    if value.count("@") != 1 or any(ch.isspace() for ch in value):
        return None
    local, domain = value.split("@", 1)
    return value if local and "." in domain and not domain.startswith(".") and not domain.endswith(".") else None


def _phone(value: str) -> str | None:
    digits = re.sub(r"\D", "", value)
    return digits if 8 <= len(digits) <= 15 else None


def _profile(value: str) -> str | None:
    try:
        parsed = urlsplit(value.strip())
        port = parsed.port
    except (ValueError, AttributeError):
        return None
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname or port not in (None, 80, 443):
        return None
    host = parsed.hostname.casefold()
    if host not in {"linkedin.com", "www.linkedin.com"}:
        return None
    parts = tuple(part for part in parsed.path.split("/") if part)
    if len(parts) != 2 or parts[0].casefold() != "in" or not parts[1].strip():
        return None
    return f"linkedin.com/in/{parts[1].casefold()}"


def _values(signals: Sequence[EvidenceSignal], normalize) -> frozenset[str]:
    result = set()
    for signal in signals:
        normalized = normalize(signal.value)
        if normalized:
            result.add(normalized)
    return frozenset(result)


def _overlap(left: frozenset[str], right: frozenset[str]) -> bool | None:
    if not left or not right:
        return None
    return bool(left & right)


def person_record_from_observation(
    person: Person,
    *,
    candidate_facts: Iterable[CandidateFact] = (),
    contacts: Iterable[ContactPoint] = (),
) -> PersonRecord:
    names: list[EvidenceSignal] = []
    roles: list[EvidenceSignal] = []
    emails: list[EvidenceSignal] = []
    phones: list[EvidenceSignal] = []
    profiles: list[EvidenceSignal] = []
    for fact in candidate_facts:
        if fact.subject_id != person.person_id:
            continue
        value = fact.normalized_value if isinstance(fact.normalized_value, str) and fact.normalized_value.strip() else fact.raw_value
        if not isinstance(value, str) or not value.strip():
            continue
        signal = EvidenceSignal(value, tuple(sorted(set(fact.evidence_ids))))
        if fact.field_name == NAME_FIELD:
            names.append(signal)
        elif fact.field_name == ROLE_FIELD:
            roles.append(signal)
    for contact in contacts:
        if contact.owner_id != person.person_id:
            continue
        evidence_ids = tuple(sorted(set(contact.discovery_evidence_ids + contact.validation_evidence_ids)))
        signal = EvidenceSignal(contact.value, evidence_ids)
        if contact.kind is ContactKind.EMAIL:
            emails.append(signal)
        elif contact.kind is ContactKind.PHONE:
            phones.append(signal)
        elif contact.kind is ContactKind.PROFESSIONAL_PROFILE:
            profiles.append(signal)
    key = lambda s: (s.value.casefold(), s.evidence_ids)
    return PersonRecord(
        person.person_id,
        person.company_id,
        tuple(sorted(set(person.relationship_evidence_ids))),
        tuple(sorted(names, key=key)),
        tuple(sorted(roles, key=key)),
        tuple(sorted(emails, key=key)),
        tuple(sorted(phones, key=key)),
        tuple(sorted(profiles, key=key)),
    )


def compare_person_features(left: PersonRecord, right: PersonRecord) -> PersonMatchFeatures:
    left_names, right_names = _values(left.names, _fold), _values(right.names, _fold)
    left_roles, right_roles = _values(left.roles, _fold), _values(right.roles, _fold)
    return PersonMatchFeatures(
        same_company=left.company_id == right.company_id,
        name_exact=_overlap(left_names, right_names),
        role_exact=_overlap(left_roles, right_roles),
        email_overlap=_overlap(_values(left.emails, _email), _values(right.emails, _email)),
        phone_overlap=_overlap(_values(left.phones, _phone), _values(right.phones, _phone)),
        professional_profile_overlap=_overlap(
            _values(left.professional_profiles, _profile), _values(right.professional_profiles, _profile)
        ),
        relationship_evidence_overlap=bool(set(left.relationship_evidence_ids) & set(right.relationship_evidence_ids)),
    )


def is_experimental_profile_name_auto_candidate(left: PersonRecord, right: PersonRecord) -> bool:
    """Diagnostic only; this rule has no operational AUTO_MATCH authority in V1."""
    f = compare_person_features(left, right)
    return f.same_company and f.name_exact is True and f.professional_profile_overlap is True


def triage_person_pair(left: PersonRecord, right: PersonRecord) -> PersonTriageDecision:
    if left.record_id == right.record_id:
        raise ValueError("Person ER requires distinct observation IDs")
    f = compare_person_features(left, right)
    evidence = tuple(sorted(set(left.evidence_ids) | set(right.evidence_ids)))
    reasons: list[str] = []
    if f.same_company and f.name_exact is True and f.professional_profile_overlap is True:
        reasons.extend(("same_company", "normalized_name_exact", "professional_profile_exact", "auto_match_not_authorized"))
    elif f.professional_profile_overlap is True:
        reasons.append("professional_profile_exact")
    if f.name_exact is True and f.email_overlap is True:
        reasons.extend(("normalized_name_exact", "email_exact"))
    if f.name_exact is True and f.phone_overlap is True:
        reasons.extend(("normalized_name_exact", "phone_exact"))
    if f.name_exact is True and f.role_exact is True:
        reasons.extend(("normalized_name_exact", "role_exact"))
    if f.email_overlap is True and f.phone_overlap is True:
        reasons.extend(("email_exact", "phone_exact"))
    if reasons:
        return PersonTriageDecision(PersonResolutionDisposition.REVIEW, f, tuple(dict.fromkeys(reasons)), evidence)
    return PersonTriageDecision(
        PersonResolutionDisposition.INSUFFICIENT_EVIDENCE,
        f,
        ("no_v1_review_rule",),
        evidence,
    )


def evaluate_experimental_auto_match(pairs: Iterable[LabeledPersonPair]) -> ExperimentalAutoMatchMetrics:
    items = tuple(pairs)
    same = sum(pair.is_same_person for pair in items)
    distinct = len(items) - same
    tp = fp = 0
    for pair in items:
        if is_experimental_profile_name_auto_candidate(pair.left, pair.right):
            if pair.is_same_person:
                tp += 1
            else:
                fp += 1
    matches = tp + fp
    precision = tp / matches if matches else None
    recall = tp / same if same else 0.0
    false_merge = fp / distinct if distinct else 0.0
    return ExperimentalAutoMatchMetrics(len(items), same, distinct, matches, tp, fp, precision, recall, false_merge)


def evaluate_person_resolution(pairs: Iterable[LabeledPersonPair]) -> PersonResolutionMetrics:
    items = tuple(pairs)
    same = sum(pair.is_same_person for pair in items)
    distinct = len(items) - same
    reviews = positive_review = 0
    for pair in items:
        if triage_person_pair(pair.left, pair.right).disposition is PersonResolutionDisposition.REVIEW:
            reviews += 1
            positive_review += int(pair.is_same_person)
    insufficient = len(items) - reviews
    review_rate = reviews / len(items) if items else 0.0
    insufficient_rate = insufficient / len(items) if items else 0.0
    positive_recall = positive_review / same if same else 0.0
    return PersonResolutionMetrics(len(items), same, distinct, reviews, insufficient, review_rate, insufficient_rate, positive_recall)


__all__ = [
    "NAME_FIELD", "ROLE_FIELD", "EvidenceSignal", "PersonRecord", "PersonMatchFeatures",
    "PersonResolutionDisposition", "PersonTriageDecision", "LabeledPersonPair",
    "ExperimentalAutoMatchMetrics", "PersonResolutionMetrics", "person_record_from_observation",
    "compare_person_features", "is_experimental_profile_name_auto_candidate", "triage_person_pair",
    "evaluate_experimental_auto_match", "evaluate_person_resolution",
]
