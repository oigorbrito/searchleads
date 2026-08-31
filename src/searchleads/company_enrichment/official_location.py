"""Narrow official-page company enrichment for MULTI_SOURCE_COMPANY_ENRICHMENT_V1.

This adapter is intentionally specific to the SERPRO transparency address page.
It persists the complete HTTP body as Evidence before extracting source-backed
company facts for one already-identified Company. It does not crawl, rank
sources, canonicalize facts, or infer truth from source authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
import hashlib
import re
from typing import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from searchleads.domain import CandidateFact, Company, DecisionClass, Evidence, Provenance, Source, utc_now
from searchleads.persistence import SQLiteRepository

OFFICIAL_URL = "https://www.transparencia.serpro.gov.br/acesso-a-informacao/institucional/enderecos"
SOURCE_TYPE = "official-company-location-page"
AGENT = "searchleads.company_enrichment.official_location.v1"
USER_AGENT = "searchleads-company-enrichment-v1 (+https://github.com/tihotm/searchleads)"
_IGNORED = {"script", "style", "noscript", "template"}
_CNPJ_KEY = re.compile(r"^[0-9A-Z]{14}$")
_CNPJ_LABEL = re.compile(
    r"\bCNPJ\s*:?\s*([0-9A-Z]{2}(?:\.[0-9A-Z]{3}){2}/[0-9A-Z]{4}-[0-9A-Z]{2}|[0-9A-Z]{14})\b",
    re.I,
)
_CEP = re.compile(r"\bCEP\s*:?\s*([0-9]{2}\.?[0-9]{3}-?[0-9]{3})\b", re.I)
_START = re.compile(r"\bIn[ií]cio\s+das\s+Atividades\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})\b", re.I)
_ADDRESS_HINT = re.compile(
    r"^(?:av\.?|avenida|rua|rodovia|estrada|travessa|alameda|pra[cç]a|sgan|quadra|setor)\b",
    re.I,
)


class CompanyEnrichmentError(RuntimeError):
    """Base error for the source-specific enrichment adapter."""


class CompanyEnrichmentAcquisitionError(CompanyEnrichmentError):
    """Raised when no usable HTTP observation can be acquired."""


class CompanyEnrichmentResponseError(CompanyEnrichmentError):
    """Raised for a non-success response after its raw body was persisted."""

    def __init__(self, status_code: int, evidence_id: str) -> None:
        self.status_code = status_code
        self.evidence_id = evidence_id
        super().__init__(f"official location page returned HTTP {status_code}; evidence={evidence_id}")


class CompanyEnrichmentExtractionError(CompanyEnrichmentError):
    """Raised when the persisted page cannot safely identify one requested block."""


@dataclass(frozen=True, slots=True)
class HTTPEnrichmentObservation:
    url: str
    status_code: int
    raw_html: str
    captured_at: datetime = field(default_factory=utc_now)
    headers: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _normalize_official_url(self.url)
        if not 100 <= self.status_code <= 599:
            raise ValueError("status_code must be a valid HTTP status")
        if not isinstance(self.raw_html, str):
            raise TypeError("raw_html must be text")
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class ExtractedLocationFacts:
    business_registry_id_raw: str
    business_registry_id_normalized: str
    street_address: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    activity_start_date: str | None = None

    def as_field_values(self) -> tuple[tuple[str, str, str | None], ...]:
        values: list[tuple[str, str, str | None]] = [
            ("business_registry_id", self.business_registry_id_raw, self.business_registry_id_normalized)
        ]
        for field_name, value in (
            ("street_address", self.street_address),
            ("city", self.city),
            ("state", self.state),
            ("postal_code", self.postal_code),
            ("activity_start_date", self.activity_start_date),
        ):
            if value is not None:
                values.append((field_name, value, None))
        return tuple(values)


@dataclass(frozen=True, slots=True)
class CompanyEnrichmentResult:
    company: Company
    source: Source
    evidence: Evidence
    extracted: ExtractedLocationFacts
    provenances: tuple[Provenance, ...]
    candidate_facts: tuple[CandidateFact, ...]
    evidence_was_new: bool


@dataclass(frozen=True, slots=True)
class _Block:
    heading: str | None
    texts: tuple[str, ...]


class _VisibleBlockParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[_Block] = []
        self._ignored_depth = 0
        self._heading_depth = 0
        self._heading_parts: list[str] = []
        self._heading: str | None = None
        self._texts: list[str] = []

    def _finish(self) -> None:
        if self._heading is not None or self._texts:
            self.blocks.append(_Block(self._heading, tuple(self._texts)))
        self._heading = None
        self._texts = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        if tag in _IGNORED:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        if tag in {"h2", "h3", "h4"}:
            self._finish()
            self._heading_depth = 1
            self._heading_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if tag in _IGNORED:
            if self._ignored_depth:
                self._ignored_depth -= 1
            return
        if self._ignored_depth:
            return
        if tag in {"h2", "h3", "h4"} and self._heading_depth:
            self._heading_depth = 0
            heading = " ".join(" ".join(self._heading_parts).split())
            self._heading = heading or None

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        text = " ".join(data.split())
        if not text:
            return
        if self._heading_depth:
            self._heading_parts.append(text)
        else:
            self._texts.append(text)

    def close(self) -> None:
        super().close()
        self._finish()


def _normalize_official_url(url: str) -> str:
    if not isinstance(url, str):
        raise TypeError("url must be text")
    try:
        parsed = urlsplit(url.strip())
        port = parsed.port
    except ValueError as exc:
        raise ValueError("url is invalid") from exc
    expected = urlsplit(OFFICIAL_URL)
    if parsed.scheme.casefold() != "https" or not parsed.hostname:
        raise ValueError("url must be the known HTTPS SERPRO transparency address page")
    if parsed.hostname.casefold() != expected.hostname or parsed.path.rstrip("/") != expected.path.rstrip("/"):
        raise ValueError("adapter can only run on the known SERPRO transparency address page")
    if port not in (None, 443) or parsed.username or parsed.password:
        raise ValueError("official URL must not contain credentials or a non-default port")
    return urlunsplit(("https", expected.hostname or "", expected.path, "", ""))


def _compact_cnpj(value: str) -> str:
    compact = re.sub(r"[.\-/\s]", "", value).upper()
    if _CNPJ_KEY.fullmatch(compact) is None:
        raise ValueError("CNPJ must match the 14-character WU3 routing-key contract")
    return compact


def _block_cnpjs(block: _Block) -> tuple[tuple[str, str], ...]:
    found: list[tuple[str, str]] = []
    for text in block.texts:
        for match in _CNPJ_LABEL.finditer(text):
            raw = match.group(1)
            found.append((raw, _compact_cnpj(raw)))
    return tuple(found)


def _parse_location(text: str) -> tuple[str, str] | None:
    if "/" not in text or text.casefold().startswith(("cnpj", "cep", "http")):
        return None
    left, right = text.rsplit("/", 1)
    city = left.rsplit(",", 1)[-1].strip()
    state = right.strip()
    if not city or not state or len(city) > 80 or len(state) > 40:
        return None
    allowed = lambda value: all(ch.isalpha() or ch in " .'-" for ch in value)
    if not allowed(city) or not allowed(state):
        return None
    if len(state) == 2:
        state = state.upper()
    return city, state


def _street_address(texts: tuple[str, ...], location_index: int) -> str | None:
    for text in reversed(texts[:location_index]):
        if _ADDRESS_HINT.match(text) and any(ch.isdigit() for ch in text):
            return text.strip(" ,;")
    return None


def _extract_block(block: _Block, expected_cnpj: str) -> ExtractedLocationFacts:
    matching = [(raw, compact) for raw, compact in _block_cnpjs(block) if compact == expected_cnpj]
    if len(matching) != 1:
        raise CompanyEnrichmentExtractionError("selected source block must contain the expected CNPJ exactly once")
    raw_cnpj, compact = matching[0]
    joined = "\n".join(block.texts)
    postal_match = _CEP.search(joined)
    start_match = _START.search(joined)
    city = state = address = None
    for index, text in enumerate(block.texts):
        parsed = _parse_location(text)
        if parsed is not None:
            city, state = parsed
            address = _street_address(block.texts, index)
            break
    return ExtractedLocationFacts(
        business_registry_id_raw=raw_cnpj,
        business_registry_id_normalized=compact,
        street_address=address,
        city=city,
        state=state,
        postal_code=postal_match.group(1) if postal_match else None,
        activity_start_date=start_match.group(1) if start_match else None,
    )


def extract_official_location_facts(html: str, expected_cnpj: str) -> ExtractedLocationFacts:
    """Extract one explicit CNPJ location block from a preserved source page."""
    if not isinstance(html, str):
        raise TypeError("html must be text")
    expected = _compact_cnpj(expected_cnpj)
    parser = _VisibleBlockParser()
    parser.feed(html)
    parser.close()
    matches = [block for block in parser.blocks if any(compact == expected for _, compact in _block_cnpjs(block))]
    if not matches:
        raise CompanyEnrichmentExtractionError("expected CNPJ was not found in a visible source block")
    if len(matches) != 1:
        raise CompanyEnrichmentExtractionError("expected CNPJ appears in multiple visible source blocks")
    return _extract_block(matches[0], expected)


def _decode_body(body: bytes, headers: object) -> str:
    charset = "utf-8"
    getter = getattr(headers, "get_content_charset", None)
    if callable(getter):
        charset = getter() or "utf-8"
    try:
        return body.decode(charset)
    except (LookupError, UnicodeDecodeError) as exc:
        raise CompanyEnrichmentAcquisitionError(f"official location page is not decodable text ({charset})") from exc


def _headers(headers: object) -> dict[str, str]:
    items = getattr(headers, "items", None)
    return {} if not callable(items) else dict(sorted((str(k).lower(), str(v)) for k, v in items()))


def http_get(url: str, *, timeout: float = 20.0) -> HTTPEnrichmentObservation:
    canonical = _normalize_official_url(url)
    request = Request(
        canonical,
        headers={"Accept": "text/html,application/xhtml+xml", "User-Agent": USER_AGENT},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return HTTPEnrichmentObservation(
                canonical, int(response.status), _decode_body(response.read(), response.headers),
                utc_now(), _headers(response.headers),
            )
    except HTTPError as exc:
        return HTTPEnrichmentObservation(
            canonical, exc.code, _decode_body(exc.read(), exc.headers), utc_now(), _headers(exc.headers)
        )
    except (URLError, TimeoutError, OSError) as exc:
        raise CompanyEnrichmentAcquisitionError(f"failed to acquire {canonical}: {exc}") from exc


Transport = Callable[[str], HTTPEnrichmentObservation]


class OfficialCompanyLocationSource:
    """Source-specific adapter for the SERPRO transparency address page."""

    def __init__(self, transport: Transport = http_get) -> None:
        self._transport = transport

    @staticmethod
    def source_record(url: str = OFFICIAL_URL) -> Source:
        canonical = _normalize_official_url(url)
        source_id = "source:official-company-location:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
        return Source(source_id, SOURCE_TYPE, canonical, "SERPRO transparency address page")

    def ingest(
        self,
        company_id: str,
        expected_cnpj: str,
        repository: SQLiteRepository,
        *,
        url: str = OFFICIAL_URL,
    ) -> CompanyEnrichmentResult:
        company = repository.load(Company, company_id)
        if company is None:
            raise ValueError(f"company must already be persisted: {company_id}")
        canonical = _normalize_official_url(url)
        expected = _compact_cnpj(expected_cnpj)
        observation = self._transport(canonical)
        try:
            observed_url = _normalize_official_url(observation.url)
        except (TypeError, ValueError) as exc:
            raise CompanyEnrichmentAcquisitionError("transport returned an observation for a different URL") from exc
        source = self.source_record(canonical)
        repository.save(source)
        evidence, was_new = self._persist_observation(source, observation, repository)
        if observation.status_code != 200:
            raise CompanyEnrichmentResponseError(observation.status_code, evidence.evidence_id)
        extracted = extract_official_location_facts(observation.raw_html, expected)
        provenances: list[Provenance] = []
        facts: list[CandidateFact] = []
        for field_name, raw_value, normalized_value in extracted.as_field_values():
            provenance = Provenance(
                provenance_id=f"prov:official-company-location:{evidence.evidence_id}:{field_name}",
                subject_id=company_id,
                field_name=field_name,
                evidence_ids=(evidence.evidence_id,),
                activity="direct-official-location-field-extraction-v1",
                generated_at=evidence.captured_at,
                agent=AGENT,
            )
            fact = CandidateFact(
                fact_id=f"fact:official-company-location:{evidence.evidence_id}:{field_name}",
                subject_id=company_id,
                field_name=field_name,
                raw_value=raw_value,
                normalized_value=normalized_value,
                evidence_ids=(evidence.evidence_id,),
                provenance_id=provenance.provenance_id,
                confidence=None,
                decision_class=DecisionClass.EVIDENCE_BACKED,
                observed_at=evidence.captured_at,
            )
            repository.save(provenance)
            repository.save(fact)
            provenances.append(provenance)
            facts.append(fact)
        return CompanyEnrichmentResult(company, source, evidence, extracted, tuple(provenances), tuple(facts), was_new)

    @staticmethod
    def _persist_observation(
        source: Source,
        observation: HTTPEnrichmentObservation,
        repository: SQLiteRepository,
    ) -> tuple[Evidence, bool]:
        canonical = _normalize_official_url(observation.url)
        body_digest = hashlib.sha256(observation.raw_html.encode("utf-8")).hexdigest()
        observation_digest = hashlib.sha256(
            f"{canonical}\0{observation.status_code}\0{observation.raw_html}".encode("utf-8")
        ).hexdigest()
        evidence_id = f"evidence:official-company-location:{observation_digest}"
        existing = repository.load(Evidence, evidence_id)
        if existing is not None:
            if (
                existing.source_id != source.source_id
                or existing.locator != canonical
                or existing.raw_payload != observation.raw_html
                or existing.metadata.get("http_status") != observation.status_code
            ):
                raise CompanyEnrichmentAcquisitionError("content-addressed official-location Evidence collision")
            return existing, False
        evidence = Evidence(
            evidence_id=evidence_id,
            source_id=source.source_id,
            locator=canonical,
            captured_at=observation.captured_at,
            raw_payload=observation.raw_html,
            content_digest=f"sha256:{body_digest}",
            metadata={
                "http_status": observation.status_code,
                "headers": dict(observation.headers),
                "transport": "http",
                "adapter": "official_company_location_v1",
            },
        )
        repository.save(evidence)
        return evidence, True


__all__ = [
    "AGENT",
    "OFFICIAL_URL",
    "SOURCE_TYPE",
    "USER_AGENT",
    "CompanyEnrichmentAcquisitionError",
    "CompanyEnrichmentError",
    "CompanyEnrichmentExtractionError",
    "CompanyEnrichmentResponseError",
    "CompanyEnrichmentResult",
    "ExtractedLocationFacts",
    "HTTPEnrichmentObservation",
    "OfficialCompanyLocationSource",
    "extract_official_location_facts",
    "http_get",
]
