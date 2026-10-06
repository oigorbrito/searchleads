"""Bounded Apify Google Search provider for the clean SearchLeads Evidence model."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
import hashlib, json, re
from typing import Any, Callable, Iterable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen
from searchleads.domain import Evidence, Source, utc_now
from searchleads.persistence import EvidenceEnvelopeConsistencyError, EvidenceEnvelopeIntegrityError, SQLiteRepository
from .contracts import WebSearchBatch, WebSearchHit, WebSearchQuery

APIFY_API_BASE_URL="https://api.apify.com/v2"
DEFAULT_GOOGLE_SEARCH_ACTOR="apify~google-search-scraper"
APIFY_GOOGLE_SEARCH_PROVIDER_ID="apify-google-search-v1"
_AGENT="searchleads.external_providers.apify_google_search.v1"
_ACTOR_ID=re.compile(r"^[A-Za-z0-9_.-]+[~/][A-Za-z0-9_.-]+$")

class ApifyAPIError(RuntimeError): pass
class ApifyTransportError(ApifyAPIError): pass
class ApifyPayloadError(ApifyAPIError): pass
JsonPostTransport=Callable[[str, Mapping[str,str], bytes, float], Any]

def _canonical_json_text(value:Any)->str:
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def _canonical_json_bytes(value:Any)->bytes: return _canonical_json_text(value).encode()
def _digest_text(value:str)->str: return hashlib.sha256(value.encode()).hexdigest()
def _normalized_actor_id(actor_id:str)->str:
    value=actor_id.strip()
    if not _ACTOR_ID.fullmatch(value): raise ValueError("actor_id must be in owner/name or owner~name form")
    owner,name=re.split(r"[~/]",value,maxsplit=1); return f"{owner}~{name}"
def _interface_language(language_code:str,country_code:str)->str:
    language=language_code.strip(); country=country_code.strip().lower()
    return "pt-BR" if language.lower()=="pt" and country=="br" else language

def _http_post_json(url:str,headers:Mapping[str,str],body:bytes,timeout:float)->Any:
    try:
        parsed = urlsplit(url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            raise ValueError("url must be an absolute http/https URL")
    except ValueError as exc:
        raise ApifyTransportError(f"Apify request failed: {exc}") from exc
    request=Request(url,data=body,headers=dict(headers),method="POST")
    try:
        with urlopen(request,timeout=timeout) as response:
            charset=response.headers.get_content_charset() or "utf-8"
            return json.loads(response.read().decode(charset))
    except (HTTPError,URLError,TimeoutError,OSError,UnicodeDecodeError,json.JSONDecodeError) as exc:
        raise ApifyTransportError(f"Apify request failed: {exc}") from exc

class ApifyActorClient:
    def __init__(self,transport:JsonPostTransport|None=None,*,base_url:str=APIFY_API_BASE_URL)->None:
        self._transport=transport or _http_post_json; self._base_url=base_url.rstrip("/")
    def run_sync_get_dataset_items(self,actor_id:str,run_input:Mapping[str,Any],*,token:str,timeout_seconds:float=120.0,max_items:int=200)->tuple[Mapping[str,Any],...]:
        actor=_normalized_actor_id(actor_id)
        if not token.strip(): raise ValueError("Apify token must be non-blank")
        if timeout_seconds<=0: raise ValueError("timeout_seconds must be > 0")
        if max_items<1: raise ValueError("max_items must be >= 1")
        if not isinstance(run_input,Mapping): raise TypeError("run_input must be a mapping")
        url=f"{self._base_url}/actors/{quote(actor,safe='~')}/run-sync-get-dataset-items?clean=true&format=json"
        payload=self._transport(url,{"Accept":"application/json","Content-Type":"application/json","Authorization":f"Bearer {token.strip()}","User-Agent":"searchleads/clean-apify-v1"},_canonical_json_bytes(dict(run_input)),timeout_seconds)
        if isinstance(payload,bytes):
            try: payload=json.loads(payload.decode())
            except (UnicodeDecodeError,json.JSONDecodeError) as exc: raise ApifyPayloadError("Apify response bytes are not valid JSON") from exc
        elif isinstance(payload,str):
            try: payload=json.loads(payload)
            except json.JSONDecodeError as exc: raise ApifyPayloadError("Apify response text is not valid JSON") from exc
        if not isinstance(payload,list): raise ApifyPayloadError("Apify synchronous dataset response must be a JSON array")
        if len(payload)>max_items: raise ApifyPayloadError(f"Apify returned {len(payload)} items, exceeding bounded max_items={max_items}")
        if any(not isinstance(item,Mapping) for item in payload): raise ApifyPayloadError("every Apify dataset item must be a JSON object")
        return tuple(dict(item) for item in payload)

@dataclass(frozen=True,slots=True)
class ApifyGoogleSearchConfig:
    actor_id:str=DEFAULT_GOOGLE_SEARCH_ACTOR
    max_pages_per_query:int=1
    max_queries:int=20
    max_dataset_items:int=200
    timeout_seconds:float=120.0
    def __post_init__(self)->None:
        _normalized_actor_id(self.actor_id)
        for value,name in ((self.max_pages_per_query,"max_pages_per_query"),(self.max_queries,"max_queries"),(self.max_dataset_items,"max_dataset_items")):
            if value<1: raise ValueError(f"{name} must be >= 1")
        if self.timeout_seconds<=0: raise ValueError("timeout_seconds must be > 0")

class ApifyGoogleSearchProvider:
    provider_id=APIFY_GOOGLE_SEARCH_PROVIDER_ID
    def __init__(self,token:str,*,client:ApifyActorClient|None=None,config:ApifyGoogleSearchConfig=ApifyGoogleSearchConfig())->None:
        if not token.strip(): raise ValueError("Apify token must be non-blank")
        self._token=token.strip(); self._client=client or ApifyActorClient(); self.config=config
    @staticmethod
    def _query_key(value:str)->str: return " ".join(value.split()).casefold()
    def search(self,repository:SQLiteRepository,queries:Iterable[WebSearchQuery],*,retrieved_at:datetime|None=None)->WebSearchBatch:
        query_items=tuple(queries)
        if not query_items: return WebSearchBatch(self.provider_id,(),())
        if len(query_items)>self.config.max_queries: raise ValueError(f"query count {len(query_items)} exceeds max_queries={self.config.max_queries}")
        if len({q.query_id for q in query_items})!=len(query_items): raise ValueError("query IDs must be unique within a provider batch")
        countries={q.country_code.strip().lower() for q in query_items}; languages={q.language_code.strip() for q in query_items}
        if len(countries)!=1 or len(languages)!=1: raise ValueError("one Apify Actor batch must use one country and one language")
        country=next(iter(countries)); language=next(iter(languages))
        run_input={"queries":"\n".join(q.query for q in query_items),"countryCode":country,"languageCode":_interface_language(language,country),"maxPagesPerQuery":self.config.max_pages_per_query,"includeUnfilteredResults":False,"mobileResults":False,"saveHtml":False,"saveHtmlToKeyValueStore":False}
        raw_items=self._client.run_sync_get_dataset_items(self.config.actor_id,run_input,token=self._token,timeout_seconds=self.config.timeout_seconds,max_items=self.config.max_dataset_items)
        captured=retrieved_at or utc_now()
        if captured.tzinfo is None or captured.utcoffset() is None: raise ValueError("retrieved_at must be timezone-aware")
        actor=_normalized_actor_id(self.config.actor_id)
        source=Source(f"source:apify:actor:{actor}","external-api",f"{APIFY_API_BASE_URL}/actors/{actor}","Apify Google Search Results Scraper")
        repository.save(source)
        query_by_text={self._query_key(q.query):q for q in query_items}
        persisted=[]; hits=[]
        for raw_item in raw_items:
            wrapped={"provider":"apify","actor_id":actor,"agent":_AGENT,"item":dict(raw_item)}
            raw_text=_canonical_json_text(wrapped); payload_digest=_digest_text(raw_text); evidence_id=f"evidence:apify:google-search:{payload_digest}"
            sq=raw_item.get("searchQuery"); locator=source.locator
            if isinstance(sq,Mapping) and str(sq.get("url","")).strip(): locator=str(sq["url"])
            try:
                existing=repository.load_evidence(evidence_id)
            except (EvidenceEnvelopeConsistencyError, EvidenceEnvelopeIntegrityError) as exc:
                raise ApifyPayloadError("content-addressed evidence ID collision") from exc
            if existing is not None:
                if existing.source_id!=source.source_id or existing.raw_payload!=raw_text or existing.locator!=locator: raise ApifyPayloadError("content-addressed evidence ID collision")
                evidence=existing
            else:
                evidence=Evidence(evidence_id,source.source_id,locator,captured,raw_text,f"sha256:{payload_digest}",{"provider":"apify","actor_id":actor,"transport":"external-api"})
                repository.save(evidence)
            persisted.append(evidence)
            term=""
            if isinstance(sq,Mapping): term=str(sq.get("term","")).strip()
            if not term: term=str(raw_item.get("query","")).strip()
            source_query=query_by_text.get(self._query_key(term))
            if source_query is None: continue
            organic=raw_item.get("organicResults",[])
            if not isinstance(organic,list): raise ApifyPayloadError("organicResults must be an array when present")
            for result in organic:
                if not isinstance(result,Mapping): raise ApifyPayloadError("organic result must be an object")
                title=str(result.get("title","")).strip(); url=str(result.get("url","")).strip()
                if not title or not url: continue
                snippet=str(result.get("description","")).strip(); raw_position=result.get("position")
                position=raw_position if isinstance(raw_position,int) and raw_position>=1 else None
                hits.append(WebSearchHit(source_query.query_id,title,url,snippet,position,evidence.evidence_id))
        unique={e.evidence_id:e for e in persisted}
        return WebSearchBatch(self.provider_id,tuple(hits),tuple(unique.values()))
