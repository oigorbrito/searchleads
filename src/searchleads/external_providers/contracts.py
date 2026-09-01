"""Provider-neutral external web-search contracts."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Protocol
from searchleads.domain import Evidence
from searchleads.persistence import SQLiteRepository

@dataclass(frozen=True, slots=True)
class WebSearchQuery:
    query_id: str
    query: str
    country_code: str = "BR"
    language_code: str = "pt"
    def __post_init__(self) -> None:
        if not self.query_id.strip() or not self.query.strip(): raise ValueError("query_id and query must be non-blank")
        if len(self.country_code.strip()) != 2: raise ValueError("country_code must be a two-letter code")
        if not self.language_code.strip(): raise ValueError("language_code must be non-blank")

@dataclass(frozen=True, slots=True)
class WebSearchHit:
    query_id: str
    title: str
    url: str
    snippet: str
    position: int | None
    evidence_id: str
    def __post_init__(self) -> None:
        for value,name in ((self.query_id,"query_id"),(self.title,"title"),(self.url,"url"),(self.evidence_id,"evidence_id")):
            if not value.strip(): raise ValueError(f"{name} must be non-blank")
        if self.position is not None and self.position < 1: raise ValueError("position must be >= 1 when supplied")

@dataclass(frozen=True, slots=True)
class WebSearchBatch:
    provider_id: str
    hits: tuple[WebSearchHit, ...]
    evidence: tuple[Evidence, ...]
    def __post_init__(self) -> None:
        if not self.provider_id.strip(): raise ValueError("provider_id must be non-blank")
        ids={item.evidence_id for item in self.evidence}
        missing=sorted({hit.evidence_id for hit in self.hits}-ids)
        if missing: raise ValueError("every search hit must reference evidence returned in the same batch: "+", ".join(missing))

class WebSearchProvider(Protocol):
    provider_id: str
    def search(self, repository: SQLiteRepository, queries: Iterable[WebSearchQuery], *, retrieved_at: datetime | None=None) -> WebSearchBatch: ...
