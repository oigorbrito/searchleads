"""Measured company entity resolution for COMPANY_ENTITY_RESOLUTION_V1.

This module deliberately separates candidate generation (blocking), pairwise
feature comparison, decision policy, and evaluation.  It does not mutate or
merge persisted Company records automatically.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import Enum
from itertools import combinations
import re
import unicodedata
from typing import Iterable, Sequence

from .normalization import _normalize_domain, _normalize_phone


@dataclass(frozen=True, slots=True)
class CompanyRecord:
    record_id: str
    name: str | None = None
    registry_id: str | None = None
    domain: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    cnae: str | int | None = None


@dataclass(frozen=True, slots=True)
class LabeledPair:
    pair_id: str
    left: CompanyRecord
    right: CompanyRecord
    is_duplicate: bool
    category: str


@dataclass(frozen=True, slots=True)
class MatchFeatures:
    registry_exact: bool | None
    registry_conflict: bool
    domain_exact: bool | None
    phone_exact: bool | None
    name_similarity: float | None
    address_similarity: float | None
    location_exact: bool | None
    cnae_exact: bool | None


class Strategy(str, Enum):
    REGISTRY_ONLY = "registry_only"
    EXACT_EVIDENCE = "exact_evidence"
    WEIGHTED = "weighted"


class ResolutionDisposition(str, Enum):
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


def _fold_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = " ".join(unicodedata.normalize("NFKC", str(value)).split()).casefold()
    if not text:
        return None
    text = "".join(
        ch for ch in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(ch)
    )
    return text


def _tokens(value: str | None) -> tuple[str, ...]:
    folded = _fold_text(value)
    if not folded:
        return ()
    return tuple(re.findall(r"[a-z0-9]+", folded))


def _name_similarity(left: str | None, right: str | None) -> float | None:
    a = _fold_text(left)
    b = _fold_text(right)
    if not a or not b:
        return None
    seq = SequenceMatcher(None, a, b).ratio()
    ta, tb = set(_tokens(a)), set(_tokens(b))
    jaccard = len(ta & tb) / len(ta | tb) if ta and tb else 0.0
    return max(seq, jaccard)


def _address_similarity(left: str | None, right: str | None) -> float | None:
    ta, tb = set(_tokens(left)), set(_tokens(right))
    if not ta or not tb:
        return None
    return len(ta & tb) / len(ta | tb)


def _clean_registry(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\W", "", str(value)).casefold()
    return cleaned or None


def _safe_domain(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return _normalize_domain(value)[0]
    except ValueError:
        return None


def _safe_phone(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return _normalize_phone(value)[0]
    except ValueError:
        return None


def compare_features(left: CompanyRecord, right: CompanyRecord) -> MatchFeatures:
    lreg, rreg = _clean_registry(left.registry_id), _clean_registry(right.registry_id)
    registry_exact = None if not lreg or not rreg else lreg == rreg
    registry_conflict = registry_exact is False

    ldom, rdom = _safe_domain(left.domain), _safe_domain(right.domain)
    domain_exact = None if not ldom or not rdom else ldom == rdom

    lphone, rphone = _safe_phone(left.phone), _safe_phone(right.phone)
    phone_exact = None if not lphone or not rphone else lphone == rphone

    lcity, rcity = _fold_text(left.city), _fold_text(right.city)
    lstate, rstate = _fold_text(left.state), _fold_text(right.state)
    location_exact = None
    if lcity and rcity and lstate and rstate:
        location_exact = lcity == rcity and lstate == rstate

    lcnae = re.sub(r"\D", "", str(left.cnae)) if left.cnae is not None else ""
    rcnae = re.sub(r"\D", "", str(right.cnae)) if right.cnae is not None else ""
    cnae_exact = None if not lcnae or not rcnae else lcnae == rcnae

    return MatchFeatures(
        registry_exact=registry_exact,
        registry_conflict=registry_conflict,
        domain_exact=domain_exact,
        phone_exact=phone_exact,
        name_similarity=_name_similarity(left.name, right.name),
        address_similarity=_address_similarity(left.address, right.address),
        location_exact=location_exact,
        cnae_exact=cnae_exact,
    )


def _weighted_score(features: MatchFeatures) -> float:
    weighted: list[tuple[float, float]] = []
    if features.name_similarity is not None:
        weighted.append((0.40, features.name_similarity))
    if features.domain_exact is not None:
        weighted.append((0.25, 1.0 if features.domain_exact else 0.0))
    if features.phone_exact is not None:
        weighted.append((0.15, 1.0 if features.phone_exact else 0.0))
    if features.address_similarity is not None:
        weighted.append((0.10, features.address_similarity))
    if features.location_exact is not None:
        weighted.append((0.05, 1.0 if features.location_exact else 0.0))
    if features.cnae_exact is not None:
        weighted.append((0.05, 1.0 if features.cnae_exact else 0.0))
    if not weighted:
        return 0.0
    total_weight = sum(weight for weight, _ in weighted)
    return sum(weight * value for weight, value in weighted) / total_weight


def resolve_pair(
    left: CompanyRecord,
    right: CompanyRecord,
    *,
    strategy: Strategy = Strategy.WEIGHTED,
    threshold: float = 0.78,
) -> MatchDecision:
    features = compare_features(left, right)
    reasons: list[str] = []

    if features.registry_conflict:
        return MatchDecision(False, 0.0, strategy, threshold, features, ("registry_conflict",))
    if features.registry_exact is True:
        return MatchDecision(True, 1.0, strategy, threshold, features, ("registry_exact",))

    if strategy is Strategy.REGISTRY_ONLY:
        return MatchDecision(False, 0.0, strategy, None, features, ("no_exact_registry",))

    if strategy is Strategy.EXACT_EVIDENCE:
        name = features.name_similarity or 0.0
        exact_signals = sum(
            signal is True
            for signal in (features.domain_exact, features.phone_exact, features.location_exact)
        )
        matched = (
            (features.domain_exact is True and name >= 0.72)
            or (features.phone_exact is True and name >= 0.78)
            or (exact_signals >= 2 and name >= 0.62)
        )
        if features.domain_exact is True:
            reasons.append("domain_exact")
        if features.phone_exact is True:
            reasons.append("phone_exact")
        if features.location_exact is True:
            reasons.append("location_exact")
        if name:
            reasons.append(f"name={name:.3f}")
        return MatchDecision(matched, 1.0 if matched else 0.0, strategy, None, features, tuple(reasons))

    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1")
    score = _weighted_score(features)
    matched = score >= threshold
    reasons.append(f"weighted_score={score:.3f}")
    return MatchDecision(matched, score, strategy, threshold, features, tuple(reasons))


def triage_pair(left: CompanyRecord, right: CompanyRecord) -> TriageDecision:
    features = compare_features(left, right)
    if features.registry_conflict:
        return TriageDecision(ResolutionDisposition.DISTINCT, features, ("registry_conflict",))
    if features.registry_exact is True:
        return TriageDecision(ResolutionDisposition.AUTO_MATCH, features, ("registry_exact",))

    review = resolve_pair(left, right, strategy=Strategy.EXACT_EVIDENCE)
    if review.is_match:
        return TriageDecision(ResolutionDisposition.REVIEW, features, review.reasons)
    return TriageDecision(
        ResolutionDisposition.INSUFFICIENT_EVIDENCE,
        features,
        ("no_v1_auto_match_or_review_rule",),
    )


def evaluate(
    pairs: Iterable[LabeledPair],
    *,
    strategy: Strategy,
    threshold: float = 0.78,
) -> EvaluationMetrics:
    tp = fp = tn = fn = 0
    for pair in pairs:
        pred = resolve_pair(pair.left, pair.right, strategy=strategy, threshold=threshold).is_match
        if pair.is_duplicate and pred:
            tp += 1
        elif pair.is_duplicate:
            fn += 1
        elif pred:
            fp += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    false_merge_rate = fp / (fp + tn) if fp + tn else 0.0
    return EvaluationMetrics(tp, fp, tn, fn, precision, recall, f1, false_merge_rate)


def blocking_keys(record: CompanyRecord) -> frozenset[str]:
    keys: set[str] = set()
    registry = _clean_registry(record.registry_id)
    if registry:
        keys.add(f"registry:{registry}")
    domain = _safe_domain(record.domain)
    if domain:
        keys.add(f"domain:{domain}")
    phone = _safe_phone(record.phone)
    if phone:
        keys.add(f"phone:{phone}")
    tokens = _tokens(record.name)
    if tokens:
        keys.add(f"name0:{tokens[0][:6]}")
        if record.city:
            keys.add(f"name0_city:{tokens[0][:6]}:{_fold_text(record.city)}")
    return frozenset(keys)


def is_blocked_candidate(left: CompanyRecord, right: CompanyRecord) -> bool:
    return bool(blocking_keys(left) & blocking_keys(right))


def evaluate_blocking(pairs: Sequence[LabeledPair]) -> BlockingMetrics:
    positives = [pair for pair in pairs if pair.is_duplicate]
    candidate_positive = sum(is_blocked_candidate(pair.left, pair.right) for pair in positives)
    candidate_pairs = sum(is_blocked_candidate(pair.left, pair.right) for pair in pairs)
    recall = candidate_positive / len(positives) if positives else 0.0
    reduction = 1.0 - (candidate_pairs / len(pairs)) if pairs else 0.0
    return BlockingMetrics(
        true_duplicate_pairs=len(positives),
        candidate_duplicate_pairs=candidate_positive,
        blocking_recall=recall,
        total_pairs=len(pairs),
        candidate_pairs=candidate_pairs,
        reduction_ratio=reduction,
    )


def evaluate_blocking_corpus(pairs: Sequence[LabeledPair]) -> BlockingMetrics:
    records: list[CompanyRecord] = []
    true_pairs: set[frozenset[str]] = set()
    for pair in pairs:
        records.extend((pair.left, pair.right))
        if pair.is_duplicate:
            true_pairs.add(frozenset((pair.left.record_id, pair.right.record_id)))

    total_pairs = len(records) * (len(records) - 1) // 2
    candidate_pairs = 0
    covered_true_pairs = 0
    for left, right in combinations(records, 2):
        if not is_blocked_candidate(left, right):
            continue
        candidate_pairs += 1
        if frozenset((left.record_id, right.record_id)) in true_pairs:
            covered_true_pairs += 1

    recall = covered_true_pairs / len(true_pairs) if true_pairs else 0.0
    reduction = 1.0 - candidate_pairs / total_pairs if total_pairs else 0.0
    return BlockingMetrics(
        true_duplicate_pairs=len(true_pairs),
        candidate_duplicate_pairs=covered_true_pairs,
        blocking_recall=recall,
        total_pairs=total_pairs,
        candidate_pairs=candidate_pairs,
        reduction_ratio=reduction,
    )
