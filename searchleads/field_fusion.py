"""Conservative field fusion and truth-discovery diagnostics for Work Unit 6.

The module turns a homogeneous set of CandidateFact records for one
subject/predicate into either a CanonicalFact (when all usable candidates agree)
or an explicit open Conflict (when they disagree).  It deliberately does not
encode a source-authority ranking or silently choose a majority value.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Iterable

from .domain import CandidateFact, CanonicalFact, Conflict, EntityRef, Provenance
from .persistence import SQLiteLeadStore


AGENT = "searchleads.field_fusion.v1"


class FusionStatus(str, Enum):
    CANONICAL = "CANONICAL"
    CONFLICT = "CONFLICT"
    EMPTY = "EMPTY"


class FusionPolicy(str, Enum):
    UNANIMOUS = "UNANIMOUS"
    NAIVE_MAJORITY_DIAGNOSTIC = "NAIVE_MAJORITY_DIAGNOSTIC"


@dataclass(frozen=True, slots=True)
class ValueSupport:
    value: Any
    candidate_fact_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    support_count: int
    support_ratio: float


@dataclass(frozen=True, slots=True)
class FusionOutcome:
    status: FusionStatus
    subject: EntityRef | None
    predicate: str | None
    supports: tuple[ValueSupport, ...]
    canonical_fact: CanonicalFact | None = None
    conflict: Conflict | None = None
    diagnostic_majority_value: Any | None = None
    diagnostic_majority_ratio: float | None = None


def _json_default(value: Any) -> str:
    return repr(value)


def _stable_value_key(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=_json_default)


def _candidate_value(fact: CandidateFact) -> Any:
    return fact.normalized_value if fact.normalized_value is not None else fact.raw_value


def _homogeneous(facts: tuple[CandidateFact, ...]) -> tuple[EntityRef, str]:
    subject = facts[0].subject
    predicate = facts[0].predicate
    for fact in facts[1:]:
        if fact.subject != subject or fact.predicate != predicate:
            raise ValueError("fusion requires one subject and one predicate")
    return subject, predicate


def _supports(facts: tuple[CandidateFact, ...]) -> tuple[ValueSupport, ...]:
    grouped: dict[str, dict[str, Any]] = {}
    total = len(facts)
    for fact in facts:
        value = _candidate_value(fact)
        key = _stable_value_key(value)
        bucket = grouped.setdefault(
            key,
            {"value": value, "candidates": [], "evidence": []},
        )
        bucket["candidates"].append(fact.candidate_fact_id)
        bucket["evidence"].extend(fact.provenance.evidence_ids)

    supports: list[ValueSupport] = []
    for key in sorted(grouped):
        bucket = grouped[key]
        candidate_ids = tuple(sorted(set(bucket["candidates"])))
        evidence_ids = tuple(sorted(set(bucket["evidence"])))
        count = len(bucket["candidates"])
        supports.append(
            ValueSupport(
                value=bucket["value"],
                candidate_fact_ids=candidate_ids,
                evidence_ids=evidence_ids,
                support_count=count,
                support_ratio=count / total,
            )
        )
    return tuple(sorted(supports, key=lambda item: (-item.support_count, _stable_value_key(item.value))))


def _id(prefix: str, subject: EntityRef, predicate: str, candidate_ids: tuple[str, ...], value: Any | None = None) -> str:
    material = {
        "subject_type": subject.entity_type.value,
        "subject_id": subject.entity_id,
        "predicate": predicate,
        "candidate_fact_ids": sorted(candidate_ids),
        "value": value,
    }
    digest = hashlib.sha256(_stable_value_key(material).encode("utf-8")).hexdigest()[:24]
    return f"{prefix}:{digest}"


def _fusion_provenance(facts: tuple[CandidateFact, ...]) -> Provenance:
    evidence_ids = tuple(sorted({eid for fact in facts for eid in fact.provenance.evidence_ids}))
    generated_at = max(fact.provenance.generated_at for fact in facts)
    return Provenance(
        evidence_ids=evidence_ids,
        activity="fuse_company_field_unanimous_v1",
        generated_at=generated_at,
        agent=AGENT,
    )


def fuse_candidate_facts(facts: Iterable[CandidateFact]) -> FusionOutcome:
    """Fuse candidates conservatively.

    - zero candidates -> EMPTY
    - one or more candidates whose effective values all agree -> CANONICAL
    - two or more distinct effective values -> open CONFLICT

    Effective value means normalized_value when available, otherwise raw_value.
    A majority value is exposed only as a diagnostic; it is not selected.
    """

    items = tuple(facts)
    if not items:
        return FusionOutcome(FusionStatus.EMPTY, None, None, ())

    subject, predicate = _homogeneous(items)
    supports = _supports(items)
    all_candidate_ids = tuple(sorted(fact.candidate_fact_id for fact in items))
    majority = supports[0]

    if len(supports) == 1:
        canonical = CanonicalFact(
            canonical_fact_id=_id("canonical:fusion:v1", subject, predicate, all_candidate_ids, majority.value),
            subject=subject,
            predicate=predicate,
            value=majority.value,
            candidate_fact_ids=all_candidate_ids,
            provenance=_fusion_provenance(items),
            confidence=None,
        )
        return FusionOutcome(
            status=FusionStatus.CANONICAL,
            subject=subject,
            predicate=predicate,
            supports=supports,
            canonical_fact=canonical,
            diagnostic_majority_value=majority.value,
            diagnostic_majority_ratio=1.0,
        )

    conflict = Conflict(
        conflict_id=_id("conflict:fusion:v1", subject, predicate, all_candidate_ids),
        subject=subject,
        predicate=predicate,
        candidate_fact_ids=all_candidate_ids,
    )
    return FusionOutcome(
        status=FusionStatus.CONFLICT,
        subject=subject,
        predicate=predicate,
        supports=supports,
        conflict=conflict,
        diagnostic_majority_value=majority.value,
        diagnostic_majority_ratio=majority.support_ratio,
    )


def persist_fusion_outcome(store: SQLiteLeadStore, outcome: FusionOutcome) -> None:
    """Persist the derived canonical fact or conflict without rewriting candidates."""

    if outcome.canonical_fact is not None:
        store.save_canonical_fact(outcome.canonical_fact)
    if outcome.conflict is not None:
        store.save_conflict(outcome.conflict)


def fuse_persisted_candidates(store: SQLiteLeadStore, candidate_fact_ids: Iterable[str]) -> FusionOutcome:
    facts: list[CandidateFact] = []
    for candidate_fact_id in candidate_fact_ids:
        fact = store.get_candidate_fact(candidate_fact_id)
        if fact is None:
            raise ValueError(f"missing candidate fact: {candidate_fact_id}")
        facts.append(fact)
    return fuse_candidate_facts(facts)


def naive_majority_value(facts: Iterable[CandidateFact]) -> tuple[Any | None, float]:
    """Diagnostic-only naive majority used for benchmark comparison.

    It intentionally counts candidate observations rather than source authority.
    This is *not* used by fuse_candidate_facts for canonicalization.
    """

    items = tuple(facts)
    if not items:
        return None, 0.0
    _homogeneous(items)
    supports = _supports(items)
    top = supports[0]
    return top.value, top.support_ratio
