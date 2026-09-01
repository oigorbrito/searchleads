"""Bridge provider-neutral web search into the clean Dental discovery recipe."""
from dataclasses import dataclass
from datetime import datetime
import hashlib
from typing import Iterable
from searchleads.dental_discovery import DentalDiscoveryCandidate,DentalDiscoveryQuery,PublicSearchObservation,build_dental_discovery_queries,discover_dental_candidates
from searchleads.persistence import SQLiteRepository
from .contracts import WebSearchBatch,WebSearchProvider,WebSearchQuery
@dataclass(frozen=True,slots=True)
class DentalExternalDiscoveryResult:
    queries:tuple[DentalDiscoveryQuery,...]; provider_batch:WebSearchBatch; observations:tuple[PublicSearchObservation,...]; candidates:tuple[DentalDiscoveryCandidate,...]
def discover_dental_candidates_with_provider(repository:SQLiteRepository,provider:WebSearchProvider,*,states:Iterable[str]=(),professional_groups:Iterable[str]=(),max_queries:int=20,retrieved_at:datetime|None=None)->DentalExternalDiscoveryResult:
    queries=build_dental_discovery_queries(states=states,professional_groups=professional_groups,max_queries=max_queries)
    web_queries=tuple(WebSearchQuery(q.query_id,q.query,"BR","pt") for q in queries)
    batch=provider.search(repository,web_queries,retrieved_at=retrieved_at)
    observations=[]
    for hit in batch.hits:
        digest=hashlib.sha256(f"{batch.provider_id}|{hit.query_id}|{hit.url}|{hit.evidence_id}".encode()).hexdigest()[:20]
        observations.append(PublicSearchObservation(f"external-search-observation:{digest}",hit.url,hit.title,hit.snippet,hit.evidence_id,hit.query_id))
    obs=tuple(observations)
    return DentalExternalDiscoveryResult(queries,batch,obs,discover_dental_candidates(obs))
