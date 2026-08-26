"""Operational live-network smoke for the currently documented SearchLeads sources.

This module composes existing adapters without changing their extraction or
persistence semantics. It is intentionally narrow: one known SERPRO CNPJ via
BrasilAPI and the one fixed official SERPRO transparency location page.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from searchleads.company_enrichment.official_location import (
    OFFICIAL_URL,
    OfficialCompanyLocationSource,
)
from searchleads.persistence import SQLiteRepository
from searchleads.sources.brasilapi import BASE_URL, BrasilAPISource

DEFAULT_CNPJ = "33.683.111/0002-80"


@dataclass(frozen=True, slots=True)
class LiveSourceSmoke:
    source: str
    locator: str
    evidence_id: str
    content_digest: str | None
    http_status: int
    raw_replay_ok: bool
    candidate_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LiveNetworkSmokeResult:
    cnpj: str
    company_id: str
    brasilapi: LiveSourceSmoke
    official_location: LiveSourceSmoke
    status: str = "PASS"


RepositoryFactory = Callable[[], SQLiteRepository]
BrasilSourceFactory = Callable[[], BrasilAPISource]
OfficialSourceFactory = Callable[[], OfficialCompanyLocationSource]


def _evidence_smoke(
    repository: SQLiteRepository,
    *,
    source: str,
    locator: str,
    evidence,
    candidate_fields: tuple[str, ...],
) -> LiveSourceSmoke:
    raw = repository.raw_evidence_bytes(evidence.evidence_id)
    expected = None if evidence.raw_payload is None else evidence.raw_payload.encode("utf-8")
    raw_replay_ok = raw is not None and raw == expected
    if not raw_replay_ok:
        raise AssertionError(f"raw Evidence replay failed for {source}")
    status = evidence.metadata.get("http_status")
    if status != 200:
        raise AssertionError(f"expected live HTTP 200 for {source}, got {status!r}")
    return LiveSourceSmoke(
        source=source,
        locator=locator,
        evidence_id=evidence.evidence_id,
        content_digest=evidence.content_digest,
        http_status=status,
        raw_replay_ok=True,
        candidate_fields=tuple(sorted(candidate_fields)),
    )


def run_live_network_smoke(
    *,
    cnpj: str = DEFAULT_CNPJ,
    repository_factory: RepositoryFactory = lambda: SQLiteRepository(":memory:"),
    brasil_source_factory: BrasilSourceFactory = BrasilAPISource,
    official_source_factory: OfficialSourceFactory = OfficialCompanyLocationSource,
) -> LiveNetworkSmokeResult:
    """Run the documented live source path using real transports by default."""

    with repository_factory() as repository:
        brasil = brasil_source_factory().ingest(cnpj, repository)
        brasil_smoke = _evidence_smoke(
            repository,
            source="brasilapi_cnpj_v1",
            locator=f"{BASE_URL}/{cnpj.replace('.', '').replace('-', '').replace('/', '')}",
            evidence=brasil.evidence,
            candidate_fields=tuple(fact.field_name for fact in brasil.candidate_facts),
        )

        official = official_source_factory().ingest(
            brasil.company.company_id,
            cnpj,
            repository,
            url=OFFICIAL_URL,
        )
        official_smoke = _evidence_smoke(
            repository,
            source="serpro_official_company_location",
            locator=OFFICIAL_URL,
            evidence=official.evidence,
            candidate_fields=tuple(fact.field_name for fact in official.candidate_facts),
        )

        return LiveNetworkSmokeResult(
            cnpj=cnpj,
            company_id=brasil.company.company_id,
            brasilapi=brasil_smoke,
            official_location=official_smoke,
        )


__all__ = [
    "DEFAULT_CNPJ",
    "LiveNetworkSmokeResult",
    "LiveSourceSmoke",
    "run_live_network_smoke",
]
