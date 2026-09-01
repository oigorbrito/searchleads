"""Bounded discovery-coverage measurement for the known SERPRO recipe."""
from __future__ import annotations
from dataclasses import dataclass
import re
from typing import Iterable, Mapping, Any
from .serpro_offices import DIRECTORY_URL, RECIPE_ID, DiscoveredCompanySeed, discover_serpro_office_seeds

_CNPJ_KEY = re.compile(r"^[0-9A-Z]{14}$")

@dataclass(frozen=True, slots=True)
class DiscoveryCoverageReference:
    scope_id: str
    source_url: str
    recipe_id: str
    scope_definition: str
    reference_method: str
    reference_cnpjs: tuple[str, ...]
    checked_on: str | None = None
    source_updated_on: str | None = None

    def __post_init__(self) -> None:
        for name, value in (("scope_id", self.scope_id), ("scope_definition", self.scope_definition), ("reference_method", self.reference_method)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be blank")
        if self.source_url != DIRECTORY_URL:
            raise ValueError("coverage reference must use the known SERPRO directory URL")
        if self.recipe_id != RECIPE_ID:
            raise ValueError("coverage reference recipe_id mismatch")
        if not self.reference_cnpjs:
            raise ValueError("coverage reference must contain at least one CNPJ")
        if len(set(self.reference_cnpjs)) != len(self.reference_cnpjs):
            raise ValueError("coverage reference CNPJs must be unique")
        if tuple(sorted(self.reference_cnpjs)) != self.reference_cnpjs:
            raise ValueError("coverage reference CNPJs must be sorted")
        if any(_CNPJ_KEY.fullmatch(cnpj) is None for cnpj in self.reference_cnpjs):
            raise ValueError("coverage reference CNPJ must match the 14-character routing contract")

@dataclass(frozen=True, slots=True)
class DiscoveryCoverageResult:
    scope_id: str
    reference_count: int
    discovered_unique_count: int
    duplicate_observation_count: int
    true_positive: int
    false_positive: int
    false_negative: int
    precision: float | None
    recall: float
    discovered_cnpjs: tuple[str, ...]
    missed_cnpjs: tuple[str, ...]
    unexpected_cnpjs: tuple[str, ...]

    @property
    def source_page_coverage(self) -> float:
        return self.recall


def reference_from_mapping(data: Mapping[str, Any]) -> DiscoveryCoverageReference:
    cnpjs = data.get("reference_cnpjs")
    if not isinstance(cnpjs, list) or not all(isinstance(v, str) for v in cnpjs):
        raise ValueError("reference_cnpjs must be a list of strings")
    return DiscoveryCoverageReference(
        scope_id=data.get("scope_id", ""),
        source_url=data.get("source_url", ""),
        recipe_id=data.get("recipe_id", ""),
        scope_definition=data.get("scope_definition", ""),
        reference_method=data.get("reference_method", ""),
        reference_cnpjs=tuple(sorted(cnpjs)),
        checked_on=data.get("checked_on"),
        source_updated_on=data.get("source_updated_on"),
    )


def measure_discovery_coverage(
    reference: DiscoveryCoverageReference,
    discovered: Iterable[DiscoveredCompanySeed],
) -> DiscoveryCoverageResult:
    observations = tuple(discovered)
    if any(seed.recipe_id != reference.recipe_id for seed in observations):
        raise ValueError("discovered seed recipe does not match coverage reference")
    observed_ids = tuple(seed.cnpj for seed in observations)
    unique = tuple(sorted(set(observed_ids)))
    reference_set = set(reference.reference_cnpjs)
    discovered_set = set(unique)
    matched = reference_set & discovered_set
    unexpected = tuple(sorted(discovered_set - reference_set))
    missed = tuple(sorted(reference_set - discovered_set))
    precision = None if not discovered_set else len(matched) / len(discovered_set)
    recall = len(matched) / len(reference_set)
    return DiscoveryCoverageResult(
        scope_id=reference.scope_id,
        reference_count=len(reference_set),
        discovered_unique_count=len(discovered_set),
        duplicate_observation_count=len(observed_ids)-len(discovered_set),
        true_positive=len(matched),
        false_positive=len(unexpected),
        false_negative=len(missed),
        precision=precision,
        recall=recall,
        discovered_cnpjs=unique,
        missed_cnpjs=missed,
        unexpected_cnpjs=unexpected,
    )


def measure_serpro_snapshot_coverage(
    reference: DiscoveryCoverageReference,
    html: str,
) -> DiscoveryCoverageResult:
    return measure_discovery_coverage(reference, discover_serpro_office_seeds(html))
