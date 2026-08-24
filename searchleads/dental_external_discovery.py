"""Bridge provider-neutral web-search APIs into the existing dental MVP recipe."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib

from .dental_facial_surgery_icp import (
    DentalFacialSurgeryICPV1,
    DEFAULT_DENTAL_FACIAL_SURGERY_ICP_V1,
)
from .dental_repeatable_discovery import (
    DentalDiscoveryCandidate,
    DentalDiscoveryQuery,
    PublicSearchObservation,
    build_dental_discovery_queries,
    discover_dental_candidates,
)
from .external_api import WebSearchBatch, WebSearchProvider, WebSearchQuery
from .persistence import SQLiteLeadStore


@dataclass(frozen=True, slots=True)
class DentalExternalDiscoveryResult:
    queries: tuple[DentalDiscoveryQuery, ...]
    provider_batch: WebSearchBatch
    observations: tuple[PublicSearchObservation, ...]
    candidates: tuple[DentalDiscoveryCandidate, ...]


def discover_dental_candidates_with_provider(
    store: SQLiteLeadStore,
    provider: WebSearchProvider,
    *,
    icp: DentalFacialSurgeryICPV1 = DEFAULT_DENTAL_FACIAL_SURGERY_ICP_V1,
    max_queries: int = 20,
    retrieved_at: datetime | None = None,
) -> DentalExternalDiscoveryResult:
    """Run deterministic dental queries through an external API provider.

    The provider is responsible for persisting its raw response as Evidence.
    This bridge only projects search hits into the existing conservative dental
    discovery logic. It does not infer learning intent and does not mark public
    CRO/title claims as officially verified.
    """
    queries = build_dental_discovery_queries(icp, max_queries=max_queries)
    web_queries = tuple(
        WebSearchQuery(
            query_id=query.query_id,
            query=query.query,
            country_code="BR",
            language_code="pt",
        )
        for query in queries
    )
    batch = provider.search(store, web_queries, retrieved_at=retrieved_at)

    observations: list[PublicSearchObservation] = []
    for hit in batch.hits:
        digest = hashlib.sha256(
            f"{batch.provider_id}|{hit.query_id}|{hit.url}|{hit.evidence_id}".encode("utf-8")
        ).hexdigest()[:20]
        observations.append(PublicSearchObservation(
            observation_id=f"external-search-observation:{digest}",
            url=hit.url,
            title=hit.title,
            snippet=hit.snippet,
            evidence_id=hit.evidence_id,
            query_id=hit.query_id,
        ))

    observation_tuple = tuple(observations)
    return DentalExternalDiscoveryResult(
        queries=queries,
        provider_batch=batch,
        observations=observation_tuple,
        candidates=discover_dental_candidates(observation_tuple),
    )
