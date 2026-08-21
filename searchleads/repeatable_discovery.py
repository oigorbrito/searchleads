"""Source-specific reusable web extraction for REPEATABLE_WEB_DISCOVERY_V1.

The implementation is intentionally not a generic crawler. It captures one
known-source recipe: the repeated office blocks on the official Serpro address
page. The same deterministic recipe can be replayed on later snapshots.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import re

from .company_enrichment import extract_official_location_facts
from .domain import Evidence, Source, SourceType
from .persistence import SQLiteLeadStore

RECIPE_ID = "serpro_office_directory_v1"
_CNPJ_RE = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")

@dataclass(frozen=True, slots=True)
class DiscoveredCompanySeed:
    cnpj: str
    city: str | None
    state: str | None
    discovery_evidence_id: str | None = None
    recipe_id: str = RECIPE_ID

@dataclass(frozen=True, slots=True)
class RepeatableDiscoveryResult:
    source: Source
    evidence: Evidence
    seeds: tuple[DiscoveredCompanySeed, ...]
    recipe_id: str = RECIPE_ID

def _digits(value:str)->str: return re.sub(r"\D","",value)

def discover_serpro_office_seeds(html:str)->tuple[DiscoveredCompanySeed,...]:
    cnpjs=[]; seen=set()
    for match in _CNPJ_RE.finditer(html):
        cnpj=_digits(match.group(0))
        if cnpj in seen: continue
        seen.add(cnpj); cnpjs.append(cnpj)
    seeds=[]
    for cnpj in cnpjs:
        try: facts=extract_official_location_facts(html,cnpj)
        except ValueError: continue
        seeds.append(DiscoveredCompanySeed(cnpj,facts.get("city"),facts.get("state")))
    return tuple(seeds)

class SerproOfficeDirectorySource:
    def ingest(self,store:SQLiteLeadStore,url:str,html:str,*,retrieved_at:datetime|None=None)->RepeatableDiscoveryResult:
        at=retrieved_at or datetime.now(timezone.utc)
        if at.tzinfo is None or at.utcoffset() is None: raise ValueError("retrieved_at must be timezone-aware")
        digest=hashlib.sha256(html.encode("utf-8")).hexdigest()
        source=Source("source:repeatable-discovery:"+hashlib.sha256(url.encode()).hexdigest()[:20],SourceType.OFFICIAL_SOURCE,url,"Serpro office directory")
        evidence=Evidence("evidence:repeatable-discovery:"+digest[:24],source.source_id,at,{"content_type":"text/html","body":html,"recipe_id":RECIPE_ID},locator=url,content_hash="sha256:"+digest)
        seeds=tuple(DiscoveredCompanySeed(s.cnpj,s.city,s.state,evidence.evidence_id,s.recipe_id) for s in discover_serpro_office_seeds(html))
        store.save_source(source); store.save_evidence(evidence)
        return RepeatableDiscoveryResult(source,evidence,seeds)
