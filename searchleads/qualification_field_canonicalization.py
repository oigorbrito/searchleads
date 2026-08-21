"""Apply existing conservative field-fusion rules to qualification-relevant fields.

This module does not choose qualification criteria or source authority. It only
runs the already-measured `fuse_candidate_facts` rule over an explicit list of
predicates. Agreement may yield CanonicalFact; disagreement remains Conflict.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Callable

from .domain import CandidateFact, CanonicalFact, Conflict
from .field_fusion import FusionOutcome, FusionStatus, fuse_candidate_facts, persist_fusion_outcome
from .persistence import SQLiteLeadStore


@dataclass(frozen=True, slots=True)
class QualificationFieldCanonicalizationResult:
    requested_predicates: tuple[str, ...]
    canonical_facts: tuple[CanonicalFact, ...]
    conflicts: tuple[Conflict, ...]
    missing_predicates: tuple[str, ...]


def canonicalize_selected_company_fields(
    facts: Iterable[CandidateFact],
    predicates: Iterable[str],
    *,
    fuse_fn: Callable[[Iterable[CandidateFact]], FusionOutcome] = fuse_candidate_facts,
) -> QualificationFieldCanonicalizationResult:
    items = tuple(facts)
    requested = tuple(dict.fromkeys(p.strip() for p in predicates if p and p.strip()))
    if not requested:
        raise ValueError("at least one qualification predicate must be requested")

    canonical: list[CanonicalFact] = []
    conflicts: list[Conflict] = []
    missing: list[str] = []

    for predicate in requested:
        selected = tuple(f for f in items if f.predicate == predicate)
        if not selected:
            missing.append(predicate)
            continue
        outcome = fuse_fn(selected)
        if outcome.status is FusionStatus.CANONICAL and outcome.canonical_fact is not None:
            canonical.append(outcome.canonical_fact)
        elif outcome.status is FusionStatus.CONFLICT and outcome.conflict is not None:
            conflicts.append(outcome.conflict)
        elif outcome.status is FusionStatus.EMPTY:
            missing.append(predicate)
        else:
            raise ValueError(f"unexpected fusion outcome for {predicate}: {outcome.status}")

    return QualificationFieldCanonicalizationResult(
        requested_predicates=requested,
        canonical_facts=tuple(canonical),
        conflicts=tuple(conflicts),
        missing_predicates=tuple(missing),
    )


def persist_qualification_field_canonicalization(
    store: SQLiteLeadStore,
    result: QualificationFieldCanonicalizationResult,
) -> None:
    """Persist derived canonical/conflict outcomes without rewriting candidates."""
    for canonical in result.canonical_facts:
        store.save_canonical_fact(canonical)
    for conflict in result.conflicts:
        store.save_conflict(conflict)
