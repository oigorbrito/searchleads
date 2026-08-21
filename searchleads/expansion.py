"""Controlled seed-list expansion for LEADS_EXPANSION_V1."""
from __future__ import annotations
from dataclasses import dataclass
import re
from typing import Iterable
from .brasilapi import BrasilAPIError, BrasilAPIIngestionResult, BrasilAPISource
from .persistence import SQLiteLeadStore

@dataclass(frozen=True, slots=True)
class ExpansionItemResult:
    cnpj:str
    ingested:bool
    already_present:bool=False
    company_id:str|None=None
    evidence_id:str|None=None
    error:str|None=None

@dataclass(frozen=True, slots=True)
class ExpansionRunResult:
    requested:int
    unique_seeds:int
    duplicate_seeds_skipped:int
    ingested:int
    already_present:int
    failed:int
    items:tuple[ExpansionItemResult,...]
    company_ids:tuple[str,...]

def _clean(value:str)->str:
    digits=re.sub(r"\D","",value)
    if len(digits)!=14: raise ValueError("CNPJ seed must contain exactly 14 digits")
    return digits

def expand_cnpj_seeds(store:SQLiteLeadStore,source:BrasilAPISource,seeds:Iterable[str])->ExpansionRunResult:
    raw=tuple(seeds); unique=[]; seen=set(); duplicate=0; items=[]
    for seed in raw:
        try: cnpj=_clean(seed)
        except ValueError as exc:
            items.append(ExpansionItemResult(str(seed),False,error=str(exc))); continue
        if cnpj in seen:
            duplicate+=1; continue
        seen.add(cnpj); unique.append(cnpj)
    company_ids=[]; failed=sum(item.error is not None for item in items); existing=0
    for cnpj in unique:
        company_id=f"company:cnpj:{cnpj}"
        if store.get_company(company_id) is not None:
            items.append(ExpansionItemResult(cnpj,False,True,company_id,None,None)); company_ids.append(company_id); existing+=1; continue
        try:
            result:BrasilAPIIngestionResult=source.ingest(store,cnpj)
            items.append(ExpansionItemResult(cnpj,True,False,result.company.company_id,result.evidence.evidence_id,None)); company_ids.append(result.company.company_id)
        except (BrasilAPIError,ValueError) as exc:
            items.append(ExpansionItemResult(cnpj,False,False,error=str(exc))); failed+=1
    ingested=sum(item.ingested for item in items)
    return ExpansionRunResult(len(raw),len(unique),duplicate,ingested,existing,failed,tuple(items),tuple(dict.fromkeys(company_ids)))
