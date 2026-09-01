"""Conservative company-field fusion for COMPANY_FIELD_FUSION_AND_TRUTH_DISCOVERY_V1."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import hashlib
import json
from typing import Any, Iterable

from searchleads.domain import CandidateFact, CanonicalFact, Conflict, DecisionClass, Provenance
from searchleads.persistence import SQLiteRepository

AGENT = "searchleads.field_fusion.company.v1"
RESOLUTION_METHOD = "unanimous-effective-value-v1"
ACTIVITY = "company-field-unanimous-fusion-v1"


class FusionStatus(StrEnum):
    CANONICAL = "CANONICAL"
    CONFLICT = "CONFLICT"
    EMPTY = "EMPTY"


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
    subject_id: str | None
    field_name: str | None
    supports: tuple[ValueSupport, ...]
    provenance: Provenance | None = None
    canonical_fact: CanonicalFact | None = None
    conflict: Conflict | None = None
    diagnostic_majority_value: Any | None = None
    diagnostic_majority_ratio: float | None = None

    def __post_init__(self) -> None:
        if self.status is FusionStatus.EMPTY:
            if any((self.subject_id, self.field_name, self.supports, self.provenance, self.canonical_fact, self.conflict)):
                raise ValueError("EMPTY fusion outcome cannot contain derived records")
            return
        if not self.subject_id or not self.field_name or not self.supports:
            raise ValueError("non-empty fusion outcome requires subject, field and supports")
        if self.status is FusionStatus.CANONICAL:
            if self.provenance is None or self.canonical_fact is None or self.conflict is not None:
                raise ValueError("CANONICAL outcome requires provenance and canonical fact only")
        elif self.status is FusionStatus.CONFLICT:
            if self.conflict is None or self.provenance is not None or self.canonical_fact is not None:
                raise ValueError("CONFLICT outcome requires conflict only")


def _stable_value_key(value: Any) -> str:
    def encode(item: Any) -> Any:
        if item is None or isinstance(item, (str, int, float, bool)):
            return [type(item).__name__, item]
        if isinstance(item, bytes):
            return ["bytes", item.hex()]
        if isinstance(item, datetime):
            return ["datetime", item.isoformat()]
        if isinstance(item, tuple):
            return ["tuple", [encode(x) for x in item]]
        if isinstance(item, list):
            return ["list", [encode(x) for x in item]]
        if isinstance(item, dict):
            pairs = sorted(((encode(k), encode(v)) for k, v in item.items()), key=lambda p: json.dumps(p[0], sort_keys=True))
            return ["dict", pairs]
        raise TypeError(f"unsupported fusion value type: {type(item).__name__}")
    return json.dumps(encode(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _effective_value(fact: CandidateFact) -> Any:
    return fact.normalized_value if fact.normalized_value is not None else fact.raw_value


def _validate_facts(facts: tuple[CandidateFact, ...]) -> tuple[str, str]:
    subject_id, field_name = facts[0].subject_id, facts[0].field_name
    seen: set[str] = set()
    for fact in facts:
        if fact.subject_id != subject_id or fact.field_name != field_name:
            raise ValueError("fusion requires one subject_id and one field_name")
        if fact.fact_id in seen:
            raise ValueError(f"duplicate candidate fact id: {fact.fact_id}")
        seen.add(fact.fact_id)
    return subject_id, field_name


def _supports(facts: tuple[CandidateFact, ...]) -> tuple[ValueSupport, ...]:
    grouped: dict[str, dict[str, Any]] = {}
    for fact in facts:
        value = _effective_value(fact)
        key = _stable_value_key(value)
        bucket = grouped.setdefault(key, {"value": value, "facts": [], "evidence": set()})
        bucket["facts"].append(fact.fact_id)
        bucket["evidence"].update(fact.evidence_ids)
    total = len(facts)
    result = [
        ValueSupport(
            bucket["value"], tuple(sorted(bucket["facts"])), tuple(sorted(bucket["evidence"])),
            len(bucket["facts"]), len(bucket["facts"]) / total,
        )
        for _, bucket in sorted(grouped.items())
    ]
    return tuple(sorted(result, key=lambda item: (-item.support_count, _stable_value_key(item.value))))


def _derived_id(prefix: str, subject_id: str, field_name: str, candidate_ids: tuple[str, ...], value: Any | None = None) -> str:
    material = {"subject_id": subject_id, "field_name": field_name, "candidate_fact_ids": sorted(candidate_ids), "value": value}
    digest = hashlib.sha256(_stable_value_key(material).encode("utf-8")).hexdigest()[:24]
    return f"{prefix}:{digest}"


def _fusion_provenance(facts: tuple[CandidateFact, ...], subject_id: str, field_name: str, candidate_ids: tuple[str, ...], value: Any) -> Provenance:
    evidence_ids = tuple(sorted({eid for fact in facts for eid in fact.evidence_ids}))
    generated_at = max(fact.observed_at for fact in facts)
    return Provenance(
        provenance_id=_derived_id("prov:fusion:v1", subject_id, field_name, candidate_ids, value),
        subject_id=subject_id,
        field_name=field_name,
        evidence_ids=evidence_ids,
        activity=ACTIVITY,
        generated_at=generated_at,
        agent=AGENT,
        derived_from_fact_ids=candidate_ids,
    )


def fuse_candidate_facts(facts: Iterable[CandidateFact]) -> FusionOutcome:
    items = tuple(facts)
    if not items:
        return FusionOutcome(FusionStatus.EMPTY, None, None, ())
    subject_id, field_name = _validate_facts(items)
    supports = _supports(items)
    candidate_ids = tuple(sorted(f.fact_id for f in items))
    majority = supports[0]
    if len(supports) == 1:
        provenance = _fusion_provenance(items, subject_id, field_name, candidate_ids, majority.value)
        canonical = CanonicalFact(
            fact_id=_derived_id("canonical:fusion:v1", subject_id, field_name, candidate_ids, majority.value),
            subject_id=subject_id,
            field_name=field_name,
            value=majority.value,
            candidate_fact_ids=candidate_ids,
            provenance_id=provenance.provenance_id,
            resolution_method=RESOLUTION_METHOD,
            decision_class=DecisionClass.ENGINEERING_CHOICE,
        )
        return FusionOutcome(
            FusionStatus.CANONICAL, subject_id, field_name, supports,
            provenance=provenance, canonical_fact=canonical,
            diagnostic_majority_value=majority.value, diagnostic_majority_ratio=1.0,
        )
    conflict = Conflict(
        conflict_id=_derived_id("conflict:fusion:v1", subject_id, field_name, candidate_ids),
        subject_id=subject_id,
        field_name=field_name,
        candidate_fact_ids=candidate_ids,
        rationale="candidate effective values disagree; V1 does not choose majority truth",
    )
    return FusionOutcome(
        FusionStatus.CONFLICT, subject_id, field_name, supports, conflict=conflict,
        diagnostic_majority_value=majority.value, diagnostic_majority_ratio=majority.support_ratio,
    )


def persist_fusion_outcome(repository: SQLiteRepository, outcome: FusionOutcome) -> tuple[bool, ...]:
    if outcome.status is FusionStatus.EMPTY:
        return ()
    if outcome.status is FusionStatus.CANONICAL:
        assert outcome.provenance is not None and outcome.canonical_fact is not None
        return (repository.save(outcome.provenance), repository.save(outcome.canonical_fact))
    assert outcome.conflict is not None
    return (repository.save(outcome.conflict),)


def fuse_persisted_candidates(repository: SQLiteRepository, candidate_fact_ids: Iterable[str]) -> FusionOutcome:
    facts: list[CandidateFact] = []
    for fact_id in candidate_fact_ids:
        fact = repository.load(CandidateFact, fact_id)
        if fact is None:
            raise ValueError(f"missing candidate fact: {fact_id}")
        facts.append(fact)
    return fuse_candidate_facts(facts)


def naive_majority_value(facts: Iterable[CandidateFact]) -> tuple[Any | None, float]:
    items = tuple(facts)
    if not items:
        return None, 0.0
    _validate_facts(items)
    top = _supports(items)[0]
    return top.value, top.support_ratio
