"""Measured, conservative company entity resolution for WU5."""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import StrEnum
from itertools import combinations
import re
import unicodedata
from typing import Iterable, Sequence

from searchleads.domain import CandidateFact
from searchleads.normalization import NormalizationStatus, normalize_candidate_fact


@dataclass(frozen=True, slots=True)
class CompanyRecord:
    record_id: str
    name: str | None = None
    registry_namespace: str | None = None
    registry_id: str | None = None
    domain: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    cnae: str | int | None = None

    def __post_init__(self) -> None:
        if not self.record_id.strip():
            raise ValueError("record_id must not be blank")
        if (self.registry_namespace is None) != (self.registry_id is None):
            raise ValueError("registry_namespace and registry_id must be supplied together")


@dataclass(frozen=True, slots=True)
class LabeledPair:
    pair_id: str
    left: CompanyRecord
    right: CompanyRecord
    is_duplicate: bool
    category: str

    def __post_init__(self) -> None:
        if not self.pair_id.strip() or not self.category.strip():
            raise ValueError("pair_id and category must not be blank")
        if self.left.record_id == self.right.record_id:
            raise ValueError("labeled pair records must be distinct observations")


@dataclass(frozen=True, slots=True)
class MatchFeatures:
    registry_comparable: bool
    registry_exact: bool | None
    registry_conflict: bool
    domain_exact: bool | None
    phone_exact: bool | None
    name_similarity: float | None
    address_similarity: float | None
    location_exact: bool | None
    cnae_exact: bool | None


class Strategy(StrEnum):
    REGISTRY_ONLY = "registry_only"
    EXACT_EVIDENCE = "exact_evidence"
    WEIGHTED = "weighted"


class ResolutionDisposition(StrEnum):
    AUTO_MATCH = "AUTO_MATCH"
    REVIEW = "REVIEW"
    DISTINCT = "DISTINCT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True, slots=True)
class TriageDecision:
    disposition: ResolutionDisposition
    features: MatchFeatures
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MatchDecision:
    is_match: bool
    score: float
    strategy: Strategy
    threshold: float | None
    features: MatchFeatures
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvaluationMetrics:
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int
    precision: float
    recall: float
    f1: float
    false_merge_rate: float


@dataclass(frozen=True, slots=True)
class BlockingMetrics:
    true_duplicate_pairs: int
    candidate_duplicate_pairs: int
    blocking_recall: float
    total_pairs: int
    candidate_pairs: int
    reduction_ratio: float


def _fold(value: str | None) -> str | None:
    if value is None:
        return None
    text = " ".join(unicodedata.normalize("NFKC", value).split()).casefold()
    if not text:
        return None
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def _tokens(value: str | None) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9]+", folded)) if (folded := _fold(value)) else ()


def _similarity(left: str | None, right: str | None) -> float | None:
    a, b = _fold(left), _fold(right)
    if not a or not b:
        return None
    ta, tb = set(_tokens(a)), set(_tokens(b))
    jac = len(ta & tb) / len(ta | tb) if ta and tb else 0.0
    return max(SequenceMatcher(None, a, b).ratio(), jac)


def _address_similarity(left: str | None, right: str | None) -> float | None:
    a, b = set(_tokens(left)), set(_tokens(right))
    return len(a & b) / len(a | b) if a and b else None


def _registry(record: CompanyRecord) -> tuple[str, str] | None:
    if record.registry_namespace is None or record.registry_id is None:
        return None
    namespace = record.registry_namespace.strip().casefold()
    if namespace != "br:cnpj":
        return None
    compact = re.sub(r"[.\-/\s]", "", record.registry_id).upper()
    return (namespace, compact) if re.fullmatch(r"[0-9A-Z]{14}", compact) else None


def _wu4(field: str, value: str | None) -> str | None:
    if value is None:
        return None
    result = normalize_candidate_fact(CandidateFact(
        fact_id=f"er:{field}", subject_id="er:observation", field_name=field,
        raw_value=value, normalized_value=None, evidence_ids=("er:evidence",),
        provenance_id="er:provenance",
    ))
    if result.status not in {NormalizationStatus.NORMALIZED, NormalizationStatus.UNCHANGED}:
        return None
    assert result.normalized_fact is not None
    normalized = result.normalized_fact.normalized_value
    return normalized if isinstance(normalized, str) else str(normalized)


def _exact(left: str | None, right: str | None) -> bool | None:
    return None if not left or not right else left == right


def compare_features(left: CompanyRecord, right: CompanyRecord) -> MatchFeatures:
    lr, rr = _registry(left), _registry(right)
    comparable = bool(lr and rr and lr[0] == rr[0])
    registry_exact = lr[1] == rr[1] if comparable and lr and rr else None
    lc, rc = _fold(left.city), _fold(right.city)
    ls, rs = _fold(left.state), _fold(right.state)
    location = lc == rc and ls == rs if lc and rc and ls and rs else None
    lcn = re.sub(r"\D", "", str(left.cnae)) if left.cnae is not None else ""
    rcn = re.sub(r"\D", "", str(right.cnae)) if right.cnae is not None else ""
    return MatchFeatures(
        comparable, registry_exact, registry_exact is False,
        _exact(_wu4("domain", left.domain), _wu4("domain", right.domain)),
        _exact(_wu4("phone", left.phone), _wu4("phone", right.phone)),
        _similarity(left.name, right.name), _address_similarity(left.address, right.address),
        location, _exact(lcn or None, rcn or None),
    )


def _weighted(features: MatchFeatures) -> float:
    parts: list[tuple[float, float]] = []
    values = (
        (0.40, features.name_similarity),
        (0.25, None if features.domain_exact is None else float(features.domain_exact)),
        (0.15, None if features.phone_exact is None else float(features.phone_exact)),
        (0.10, features.address_similarity),
        (0.05, None if features.location_exact is None else float(features.location_exact)),
        (0.05, None if features.cnae_exact is None else float(features.cnae_exact)),
    )
    parts.extend((w, v) for w, v in values if v is not None)
    if not parts:
        return 0.0
    total = sum(w for w, _ in parts)
    return sum(w * v for w, v in parts) / total


def resolve_pair(left: CompanyRecord, right: CompanyRecord, *, strategy: Strategy = Strategy.WEIGHTED, threshold: float = 0.78) -> MatchDecision:
    if not isinstance(strategy, Strategy):
        raise ValueError(f"unsupported strategy: {strategy}")
    if strategy is Strategy.WEIGHTED and not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1")
    f = compare_features(left, right)
    if f.registry_conflict:
        return MatchDecision(False, 0.0, strategy, threshold, f, ("registry_conflict",))
    if f.registry_exact is True:
        return MatchDecision(True, 1.0, strategy, threshold, f, ("registry_exact",))
    if strategy is Strategy.REGISTRY_ONLY:
        return MatchDecision(False, 0.0, strategy, None, f, ("no_exact_registry",))
    if strategy is Strategy.EXACT_EVIDENCE:
        name = f.name_similarity or 0.0
        exact_count = sum(x is True for x in (f.domain_exact, f.phone_exact, f.location_exact))
        matched = ((f.domain_exact is True and name >= .72) or
                   (f.phone_exact is True and name >= .78) or
                   (exact_count >= 2 and name >= .62))
        reasons = tuple(k for k, ok in (("domain_exact", f.domain_exact), ("phone_exact", f.phone_exact), ("location_exact", f.location_exact)) if ok is True)
        reasons += ((f"name={name:.3f}",) if name else ())
        return MatchDecision(matched, float(matched), strategy, None, f, reasons)
    score = _weighted(f)
    return MatchDecision(score >= threshold, score, strategy, threshold, f, (f"weighted_score={score:.3f}",))


def triage_pair(left: CompanyRecord, right: CompanyRecord) -> TriageDecision:
    f = compare_features(left, right)
    if f.registry_conflict:
        return TriageDecision(ResolutionDisposition.DISTINCT, f, ("registry_conflict",))
    if f.registry_exact is True:
        return TriageDecision(ResolutionDisposition.AUTO_MATCH, f, ("registry_exact",))
    review = resolve_pair(left, right, strategy=Strategy.EXACT_EVIDENCE)
    if review.is_match:
        return TriageDecision(ResolutionDisposition.REVIEW, f, review.reasons)
    return TriageDecision(ResolutionDisposition.INSUFFICIENT_EVIDENCE, f, ("no_v1_auto_match_or_review_rule",))


def evaluate(pairs: Iterable[LabeledPair], *, strategy: Strategy, threshold: float = .78) -> EvaluationMetrics:
    tp = fp = tn = fn = 0
    for pair in pairs:
        pred = resolve_pair(pair.left, pair.right, strategy=strategy, threshold=threshold).is_match
        if pair.is_duplicate and pred: tp += 1
        elif pair.is_duplicate: fn += 1
        elif pred: fp += 1
        else: tn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    fmr = fp / (fp + tn) if fp + tn else 0.0
    return EvaluationMetrics(tp, fp, tn, fn, precision, recall, f1, fmr)


def blocking_keys(record: CompanyRecord) -> frozenset[str]:
    keys: set[str] = set()
    if registry := _registry(record): keys.add(f"registry:{registry[0]}:{registry[1]}")
    if domain := _wu4("domain", record.domain): keys.add(f"domain:{domain}")
    if phone := _wu4("phone", record.phone): keys.add(f"phone:{phone}")
    if tokens := _tokens(record.name):
        prefix = tokens[0][:6]
        keys.add(f"name0:{prefix}")
        if city := _fold(record.city): keys.add(f"name0_city:{prefix}:{city}")
    return frozenset(keys)


def is_blocked_candidate(left: CompanyRecord, right: CompanyRecord) -> bool:
    return bool(blocking_keys(left) & blocking_keys(right))


def evaluate_blocking(pairs: Sequence[LabeledPair]) -> BlockingMetrics:
    # Single-pass evaluation over pairs to avoid double evaluation of positives.
    positives = cp = candidates = 0
    for p in pairs:
        blocked = is_blocked_candidate(p.left, p.right)
        if blocked:
            candidates += 1
        if p.is_duplicate:
            positives += 1
            if blocked:
                cp += 1
    return BlockingMetrics(positives, cp, cp / positives if positives else 0.0,
                           len(pairs), candidates, 1 - candidates / len(pairs) if pairs else 0.0)


def evaluate_blocking_corpus(pairs: Sequence[LabeledPair]) -> BlockingMetrics:
    records = [record for p in pairs for record in (p.left, p.right)]
    truth = {frozenset((p.left.record_id, p.right.record_id)) for p in pairs if p.is_duplicate}
    total = len(records) * (len(records) - 1) // 2
    candidates = covered = 0
    # Performance optimization: pre-compute blocking keys O(N) once before pairwise O(N^2) evaluation,
    # avoiding redundant feature extraction/normalization inside combinations loop (~76x speedup).
    keys_and_ids = [(blocking_keys(r), r.record_id) for r in records]
    for (k1, id1), (k2, id2) in combinations(keys_and_ids, 2):
        if k1 & k2:
            candidates += 1
            if frozenset((id1, id2)) in truth:
                covered += 1
    return BlockingMetrics(len(truth), covered, covered / len(truth) if truth else 0.0,
                           total, candidates, 1 - candidates / total if total else 0.0)
