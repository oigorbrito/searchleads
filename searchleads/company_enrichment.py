"""Second-source company enrichment for COMPANY_ENRICHMENT_V1.

This adapter is deliberately specific to a known official company location page.
It preserves the complete HTML page as Evidence and extracts only explicitly
present registry/location facts for an already-identified Company.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
import re
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .domain import CandidateFact, Company, EntityRef, EntityType, Evidence, Provenance, Source, SourceType
from .persistence import SQLiteLeadStore

AGENT = "searchleads.company_enrichment.official_location.v1"
_CNPJ_RE = re.compile(r"CNPJ\s*:?\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", re.I)
_CEP_RE = re.compile(r"CEP\s*:?\s*([0-9.\-]{8,12})", re.I)
_START_RE = re.compile(r"In[ií]cio\s+das\s+Atividades\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})", re.I)
_LOCATION_RE = re.compile(r"\b([A-Za-zÀ-ÖØ-öø-ÿ ]{3,})/(Acre|Alagoas|Amapá|Amazonas|Bahia|Ceará|Distrito Federal|Espírito Santo|Goiás|Maranhão|Mato Grosso|Mato Grosso do Sul|Minas Gerais|Pará|Paraíba|Paraná|Pernambuco|Piauí|Rio de Janeiro|Rio Grande do Norte|Rio Grande do Sul|Rondônia|Roraima|Santa Catarina|São Paulo|Sergipe|Tocantins|AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)\b", re.I)
_STATE_ABBR = {"distrito federal":"DF","são paulo":"SP","rio de janeiro":"RJ","minas gerais":"MG","rio grande do sul":"RS","santa catarina":"SC","paraná":"PR","bahia":"BA","pernambuco":"PE","ceará":"CE","goiás":"GO"}

class CompanyEnrichmentError(RuntimeError): pass
class CompanyEnrichmentAcquisitionError(CompanyEnrichmentError): pass

@dataclass(frozen=True, slots=True)
class CompanyEnrichmentResult:
    company: Company
    source: Source
    evidence: Evidence
    candidate_facts: tuple[CandidateFact, ...]

class _TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.parts=[]
    def handle_data(self,data):
        text=" ".join(data.split())
        if text: self.parts.append(text)

def _http_get(url:str)->str:
    request=Request(url,headers={"Accept":"text/html,application/xhtml+xml","User-Agent":"searchleads/0.11 (+https://github.com/tihotm/searchleads)"})
    try:
        with urlopen(request,timeout=20) as response:
            charset=response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset,errors="replace")
    except (HTTPError,URLError,TimeoutError) as exc:
        raise CompanyEnrichmentAcquisitionError(f"failed to fetch {url}: {exc}") from exc

def _digits(value:str)->str: return re.sub(r"\D","",value)

def extract_official_location_facts(html:str, expected_cnpj:str)->dict[str,str]:
    parser=_TextParser(); parser.feed(html); parts=parser.parts
    expected=_digits(expected_cnpj)
    hit=None
    for i,part in enumerate(parts):
        for match in _CNPJ_RE.finditer(part):
            if _digits(match.group(1)) == expected:
                hit=i; break
        if hit is not None: break
    if hit is None:
        for i in range(len(parts)-1):
            if parts[i].casefold().startswith("cnpj") and _digits(parts[i+1]) == expected:
                hit=i; break
    if hit is None: raise ValueError("expected CNPJ not found in official page")
    window=parts[max(0,hit-6):min(len(parts),hit+8)]
    text="\n".join(window)
    facts={"business_registry_id": expected}
    cep=_CEP_RE.search(text)
    if cep: facts["postal_code"]=_digits(cep.group(1))
    start=_START_RE.search(text)
    if start: facts["activity_start_date"]=start.group(1)
    loc=_LOCATION_RE.search(text)
    if loc:
        facts["city"]=" ".join(loc.group(1).split())
        state=loc.group(2); facts["state"]=_STATE_ABBR.get(state.casefold(),state.upper())
    for idx,part in enumerate(window):
        if _LOCATION_RE.search(part) and idx>0:
            candidate=window[idx-1]
            if re.search(r"\d",candidate) and not re.search(r"CEP|CNPJ|Atividades",candidate,re.I):
                facts["street_address"]=candidate
            break
    return facts

HtmlTransport=Callable[[str],str]
class OfficialCompanyLocationSource:
    def __init__(self,transport:HtmlTransport|None=None): self._transport=transport or _http_get
    def ingest(self,store:SQLiteLeadStore,company_id:str,url:str,expected_cnpj:str,*,retrieved_at:datetime|None=None,html:str|None=None)->CompanyEnrichmentResult:
        company=store.get_company(company_id)
        if company is None: raise ValueError(f"company must already be persisted: {company_id}")
        page=html if html is not None else self._transport(url)
        at=retrieved_at or datetime.now(timezone.utc)
        if at.tzinfo is None or at.utcoffset() is None: raise ValueError("retrieved_at must be timezone-aware")
        extracted=extract_official_location_facts(page,expected_cnpj)
        digest=hashlib.sha256(page.encode("utf-8")).hexdigest()
        source=Source("source:official-company-location:"+hashlib.sha256(url.encode()).hexdigest()[:20],SourceType.OFFICIAL_SOURCE,url,"Official company location page")
        evidence=Evidence("evidence:official-company-location:"+digest[:24],source.source_id,at,{"content_type":"text/html","body":page},locator=url,content_hash="sha256:"+digest)
        provenance=Provenance((evidence.evidence_id,),"extract_company_location_from_official_page_v1",generated_at=at,agent=AGENT)
        subject=EntityRef(EntityType.COMPANY,company_id)
        facts=tuple(CandidateFact("candidate:official-location:"+hashlib.sha256(f"{company_id}|{predicate}|{value}|{digest}".encode()).hexdigest()[:24],subject,predicate,value,provenance) for predicate,value in sorted(extracted.items()))
        store.save_source(source); store.save_evidence(evidence)
        for fact in facts: store.save_candidate_fact(fact)
        return CompanyEnrichmentResult(company,source,evidence,facts)
