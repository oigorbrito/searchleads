from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from itertools import combinations


class ResolutionDecision(str, Enum):
    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"
    UNRESOLVED = "UNRESOLVED"
    POSSIBLY_DIFFERENT = "POSSIBLY_DIFFERENT"


@dataclass(frozen=True, slots=True)
class CompanyIdentity:
    company_id: str
    external_ids: dict[str, str] = field(default_factory=dict)
    normalized_name: str | None = None
    domain: str | None = None
    city: str | None = None

    def __post_init__(self) -> None:
        if not self.company_id.strip():
            raise ValueError("company_id must be non-empty")
        for namespace, value in self.external_ids.items():
            if not namespace.strip() or not value.strip():
                raise ValueError("external id namespace and value must be non-empty")


@dataclass(frozen=True, slots=True)
class ResolutionResult:
    decision: ResolutionDecision
    reasons: tuple[str, ...]


def blocking_keys(identity: CompanyIdentity) -> tuple[str, ...]:
    """Return deterministic candidate-generation keys, not match decisions."""

    keys: list[str] = []
    for namespace, value in sorted(identity.external_ids.items()):
        keys.append(f"external:{namespace.casefold()}:{value.casefold()}")
    if identity.domain:
        keys.append(f"domain:{identity.domain.casefold()}")
    if identity.normalized_name:
        keys.append(f"name:{identity.normalized_name}")
    return tuple(keys)


def candidate_pairs(identities: tuple[CompanyIdentity, ...]) -> tuple[tuple[int, int], ...]:
    """Generate candidate index pairs without evaluating entity identity."""

    buckets: dict[str, list[int]] = defaultdict(list)
    for index, identity in enumerate(identities):
        for key in blocking_keys(identity):
            buckets[key].append(index)

    pairs: set[tuple[int, int]] = set()
    for indexes in buckets.values():
        if len(indexes) < 2:
            continue
        pairs.update(combinations(indexes, 2))
    return tuple(sorted(pairs))


def resolve_company_pair(left: CompanyIdentity, right: CompanyIdentity) -> ResolutionResult:
    """Apply explicit V1 company matching rules with categorical outcomes."""

    if left.company_id == right.company_id:
        return ResolutionResult(ResolutionDecision.MATCH, ("same_company_id",))

    shared_namespaces = sorted(set(left.external_ids) & set(right.external_ids))
    exact_external = [
        namespace
        for namespace in shared_namespaces
        if left.external_ids[namespace] == right.external_ids[namespace]
    ]
    conflicting_external = [
        namespace
        for namespace in shared_namespaces
        if left.external_ids[namespace] != right.external_ids[namespace]
    ]

    if conflicting_external:
        return ResolutionResult(
            ResolutionDecision.NO_MATCH,
            tuple(f"conflicting_external_id:{namespace}" for namespace in conflicting_external),
        )

    if exact_external:
        return ResolutionResult(
            ResolutionDecision.MATCH,
            tuple(f"exact_external_id:{namespace}" for namespace in exact_external),
        )

    same_domain = _same_nonempty(left.domain, right.domain)
    same_name = _same_nonempty(left.normalized_name, right.normalized_name)
    city_conflict = (
        left.city is not None
        and right.city is not None
        and left.city.casefold() != right.city.casefold()
    )

    if same_name and city_conflict:
        return ResolutionResult(
            ResolutionDecision.POSSIBLY_DIFFERENT,
            ("exact_normalized_name", "conflicting_city"),
        )

    if same_domain and same_name:
        return ResolutionResult(
            ResolutionDecision.MATCH,
            ("exact_domain", "exact_normalized_name"),
        )

    if same_domain:
        return ResolutionResult(ResolutionDecision.UNRESOLVED, ("exact_domain_only",))

    if same_name:
        return ResolutionResult(
            ResolutionDecision.UNRESOLVED,
            ("exact_normalized_name_only",),
        )

    return ResolutionResult(ResolutionDecision.UNRESOLVED, ("insufficient_evidence",))


def all_pairs_count(item_count: int) -> int:
    if item_count < 0:
        raise ValueError("item_count cannot be negative")
    return item_count * (item_count - 1) // 2


def reduction_ratio(*, all_pairs: int, candidates: int) -> float:
    if all_pairs < 0 or candidates < 0:
        raise ValueError("pair counts cannot be negative")
    if candidates > all_pairs:
        raise ValueError("candidates cannot exceed all pairs")
    if all_pairs == 0:
        return 0.0
    return 1.0 - (candidates / all_pairs)


def _same_nonempty(left: str | None, right: str | None) -> bool:
    return left is not None and right is not None and left.casefold() == right.casefold()
