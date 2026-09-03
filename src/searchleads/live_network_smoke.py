"""Bounded live-network certification for the currently supported external sources.

The default factories use the real transports of the existing BrasilAPI and
SERPRO adapters. Callers may inject deterministic transports for tests. A PASS
from this module only certifies the exact observed point lookup/page fetch; it
must not be generalized into market coverage or source availability claims.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from searchleads.company_enrichment.official_location import (
    OFFICIAL_URL,
    OfficialCompanyLocationSource,
)
from searchleads.persistence import SQLiteRepository
from searchleads.sources.brasilapi import BrasilAPISource

DEFAULT_CNPJ = "33683111000280"


@dataclass(frozen=True, slots=True)
class LiveSourceObservation:
    source: str
    locator: str
    evidence_id: str
    content_digest: str | None
    http_status: int
    persisted_raw_payload: bool
    candidate_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LiveNetworkCertificationResult:
    cnpj: str
    company_id: str
    brasilapi: LiveSourceObservation
    serpro_official_location: LiveSourceObservation

    @property
    def passed(self) -> bool:
        return (
            self.brasilapi.http_status == 200
            and self.serpro_official_location.http_status == 200
            and self.brasilapi.persisted_raw_payload
            and self.serpro_official_location.persisted_raw_payload
        )


RepositoryFactory = Callable[[], SQLiteRepository]
BrasilSourceFactory = Callable[[], BrasilAPISource]
OfficialSourceFactory = Callable[[], OfficialCompanyLocationSource]


def _observation(*, repository: SQLiteRepository, source: str, evidence, candidate_fields: tuple[str, ...]) -> LiveSourceObservation:
    persisted = repository.load_evidence(evidence.evidence_id)
    if persisted is None:
        raise AssertionError(f"Evidence was not persisted for {source}")
    if persisted.raw_payload != evidence.raw_payload:
        raise AssertionError(f"persisted raw payload mismatch for {source}")
    status = persisted.metadata.get("http_status")
    if status != 200:
        raise AssertionError(f"expected HTTP 200 for {source}, got {status!r}")
    return LiveSourceObservation(
        source=source,
        locator=persisted.locator,
        evidence_id=persisted.evidence_id,
        content_digest=persisted.content_digest,
        http_status=status,
        persisted_raw_payload=True,
        candidate_fields=tuple(sorted(candidate_fields)),
    )


def run_live_network_certification(
    *,
    cnpj: str = DEFAULT_CNPJ,
    repository_factory: RepositoryFactory = lambda: SQLiteRepository(":memory:"),
    brasil_source_factory: BrasilSourceFactory = BrasilAPISource,
    official_source_factory: OfficialSourceFactory = OfficialCompanyLocationSource,
) -> LiveNetworkCertificationResult:
    """Exercise the two documented live transports and verify Evidence persistence."""
    with repository_factory() as repository:
        brasil = brasil_source_factory().ingest(cnpj, repository)
        brasil_observation = _observation(
            repository=repository,
            source="brasilapi_cnpj_v1",
            evidence=brasil.evidence,
            candidate_fields=tuple(fact.field_name for fact in brasil.candidate_facts),
        )

        official = official_source_factory().ingest(
            brasil.company.company_id,
            cnpj,
            repository,
            url=OFFICIAL_URL,
        )
        official_observation = _observation(
            repository=repository,
            source="serpro_official_company_location",
            evidence=official.evidence,
            candidate_fields=tuple(fact.field_name for fact in official.candidate_facts),
        )

        result = LiveNetworkCertificationResult(
            cnpj=cnpj,
            company_id=brasil.company.company_id,
            brasilapi=brasil_observation,
            serpro_official_location=official_observation,
        )
        if not result.passed:
            raise AssertionError("live-network certification did not pass")
        return result


__all__ = [
    "DEFAULT_CNPJ",
    "LiveNetworkCertificationResult",
    "LiveSourceObservation",
    "run_live_network_certification",
]
