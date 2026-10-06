"""Narrow real-source adapter for BrasilAPI CNPJ v1.

This module implements exactly one acquisition path: a point lookup for a known
CNPJ. The HTTP response body is persisted as Evidence before JSON payload
validation or fact extraction. Source values become CandidateFact records only;
this unit does not normalize, canonicalize, resolve entities, discover contacts,
or qualify leads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
import re
from typing import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from searchleads.domain import CandidateFact, Company, DecisionClass, Evidence, Provenance, Source, utc_now
from searchleads.persistence import SQLiteRepository

BASE_URL = "https://brasilapi.com.br/api/cnpj/v1"
SOURCE_ID = "source:brasilapi:cnpj-v1"
USER_AGENT = "searchleads-real-source-v1 (+https://github.com/tihotm/searchleads)"
_AGENT = "searchleads.sources.brasilapi.v1"
_CNPJ_KEY = re.compile(r"^[0-9A-Z]{14}$")
_CNPJ_FORMATTING = re.compile(r"[.\-/\s]")


class BrasilAPIError(RuntimeError):
    """Base error for the BrasilAPI adapter."""


class BrasilAPIAcquisitionError(BrasilAPIError):
    """Raised when no HTTP response can be acquired."""


class BrasilAPIResponseError(BrasilAPIError):
    """Raised for a non-success HTTP response after its body is persisted."""

    def __init__(self, status_code: int, evidence_id: str) -> None:
        self.status_code = status_code
        self.evidence_id = evidence_id
        super().__init__(f"BrasilAPI returned HTTP {status_code}; evidence={evidence_id}")


class BrasilAPIPayloadError(BrasilAPIError):
    """Raised when a successful response cannot safely represent the request."""

    def __init__(self, message: str, evidence_id: str) -> None:
        self.evidence_id = evidence_id
        super().__init__(f"{message}; evidence={evidence_id}")


@dataclass(frozen=True, slots=True)
class HTTPObservation:
    """Textual HTTP response captured by the transport boundary."""

    url: str
    status_code: int
    raw_payload: str
    captured_at: datetime = field(default_factory=utc_now)
    headers: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.url.strip():
            raise ValueError("url must not be blank")
        if self.status_code < 100 or self.status_code > 599:
            raise ValueError("status_code must be a valid HTTP status")
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class BrasilAPIIngestionResult:
    """Records produced by one successful point lookup."""

    source: Source
    company: Company
    evidence: Evidence
    provenances: tuple[Provenance, ...]
    candidate_facts: tuple[CandidateFact, ...]
    evidence_was_new: bool
    company_was_new: bool


Transport = Callable[[str], HTTPObservation]


def normalize_cnpj_key(value: str) -> str:
    """Normalize only transport formatting for the current 14-char CNPJ key.

    BrasilAPI's current contract allows digits and letters A-Z, with or without
    punctuation. This function is an adapter routing key, not a business-field
    normalization rule.
    """

    if not isinstance(value, str):
        raise TypeError("cnpj must be a string")
    compact = _CNPJ_FORMATTING.sub("", value).upper()
    if not _CNPJ_KEY.fullmatch(compact):
        raise ValueError("cnpj must contain exactly 14 characters from 0-9 or A-Z")
    return compact


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _build_request(url: str) -> Request:
    return Request(
        url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        method="GET",
    )


def _response_text(body: bytes, headers: object) -> str:
    charset = "utf-8"
    get_content_charset = getattr(headers, "get_content_charset", None)
    if callable(get_content_charset):
        charset = get_content_charset() or "utf-8"
    try:
        return body.decode(charset)
    except (LookupError, UnicodeDecodeError) as exc:
        raise BrasilAPIAcquisitionError(f"BrasilAPI response is not decodable text ({charset})") from exc


def _headers_dict(headers: object) -> dict[str, str]:
    items = getattr(headers, "items", None)
    if not callable(items):
        return {}
    return dict(sorted((str(key).lower(), str(value)) for key, value in items()))


def _require_http_url(url: str) -> None:
    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        raise ValueError("url must be an absolute http/https URL") from exc
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("url must be an absolute http/https URL")


def http_get(url: str, *, timeout: float = 20.0) -> HTTPObservation:
    """Acquire one BrasilAPI response with an explicit identifying User-Agent."""

    _require_http_url(url)
    request = _build_request(url)
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
            return HTTPObservation(
                url=url,
                status_code=int(response.status),
                raw_payload=_response_text(body, response.headers),
                captured_at=utc_now(),
                headers=_headers_dict(response.headers),
            )
    except HTTPError as exc:
        body = exc.read()
        return HTTPObservation(
            url=url,
            status_code=exc.code,
            raw_payload=_response_text(body, exc.headers),
            captured_at=utc_now(),
            headers=_headers_dict(exc.headers),
        )
    except (URLError, TimeoutError, OSError) as exc:
        raise BrasilAPIAcquisitionError(f"failed to acquire {url}: {exc}") from exc


_FIELD_MAP: tuple[tuple[str, str], ...] = (
    ("business_registry_id", "cnpj"),
    ("legal_name", "razao_social"),
    ("trade_name", "nome_fantasia"),
    ("registration_status", "descricao_situacao_cadastral"),
    ("primary_cnae_code", "cnae_fiscal"),
    ("primary_cnae_description", "cnae_fiscal_descricao"),
    ("city", "municipio"),
    ("state", "uf"),
)


class BrasilAPISource:
    """Point-lookup adapter for the public BrasilAPI CNPJ v1 endpoint."""

    def __init__(self, transport: Transport = http_get) -> None:
        self._transport = transport

    @staticmethod
    def source_record() -> Source:
        return Source(SOURCE_ID, "public-api", BASE_URL, "BrasilAPI CNPJ v1")

    @staticmethod
    def url_for(cnpj: str) -> str:
        return f"{BASE_URL}/{normalize_cnpj_key(cnpj)}"

    def ingest(self, cnpj: str, repository: SQLiteRepository) -> BrasilAPIIngestionResult:
        requested_key = normalize_cnpj_key(cnpj)
        url = f"{BASE_URL}/{requested_key}"
        observation = self._transport(url)
        if observation.url != url:
            raise BrasilAPIAcquisitionError("transport returned an observation for a different URL")

        source = self.source_record()
        repository.save(source)

        evidence, evidence_was_new = self._persist_observation(source, observation, repository)

        if observation.status_code != 200:
            raise BrasilAPIResponseError(observation.status_code, evidence.evidence_id)

        payload = self._parse_payload(observation.raw_payload, evidence.evidence_id)
        returned_cnpj = payload.get("cnpj")
        if not isinstance(returned_cnpj, str):
            raise BrasilAPIPayloadError("response cnpj must be a string", evidence.evidence_id)
        try:
            returned_key = normalize_cnpj_key(returned_cnpj)
        except (TypeError, ValueError) as exc:
            raise BrasilAPIPayloadError("response cnpj is invalid", evidence.evidence_id) from exc
        if returned_key != requested_key:
            raise BrasilAPIPayloadError("response cnpj does not match requested cnpj", evidence.evidence_id)

        legal_name = payload.get("razao_social")
        if not isinstance(legal_name, str) or not legal_name.strip():
            raise BrasilAPIPayloadError("response requires non-blank razao_social", evidence.evidence_id)

        company_id = f"company:brasilapi-cnpj:{requested_key}"
        existing_company = repository.load(Company, company_id)
        if existing_company is None:
            company = Company(company_id)
            repository.save(company)
            company_was_new = True
        else:
            company = existing_company
            company_was_new = False

        provenances: list[Provenance] = []
        facts: list[CandidateFact] = []
        for field_name, source_field in _FIELD_MAP:
            raw_value = payload.get(source_field)
            if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
                continue
            provenance = Provenance(
                provenance_id=f"prov:brasilapi:{evidence.evidence_id}:{field_name}",
                subject_id=company.company_id,
                field_name=field_name,
                evidence_ids=(evidence.evidence_id,),
                activity="direct-source-field-extraction",
                generated_at=evidence.captured_at,
                agent=_AGENT,
            )
            fact = CandidateFact(
                fact_id=f"fact:brasilapi:{evidence.evidence_id}:{field_name}",
                subject_id=company.company_id,
                field_name=field_name,
                raw_value=raw_value,
                normalized_value=None,
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

        return BrasilAPIIngestionResult(
            source=source,
            company=company,
            evidence=evidence,
            provenances=tuple(provenances),
            candidate_facts=tuple(facts),
            evidence_was_new=evidence_was_new,
            company_was_new=company_was_new,
        )

    @staticmethod
    def _parse_payload(raw_payload: str, evidence_id: str) -> dict[str, object]:
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise BrasilAPIPayloadError("response body is not valid JSON", evidence_id) from exc
        if not isinstance(payload, dict):
            raise BrasilAPIPayloadError("response body must be a JSON object", evidence_id)
        return payload

    @staticmethod
    def _persist_observation(
        source: Source,
        observation: HTTPObservation,
        repository: SQLiteRepository,
    ) -> tuple[Evidence, bool]:
        payload_digest = _digest_text(observation.raw_payload)
        observation_digest = _digest_text(f"{observation.url}\0{observation.raw_payload}")
        evidence_id = f"evidence:brasilapi:{observation_digest}"
        existing = repository.load_evidence(evidence_id)
        if existing is not None:
            if (
                existing.source_id != source.source_id
                or existing.locator != observation.url
                or existing.raw_payload != observation.raw_payload
            ):
                raise BrasilAPIAcquisitionError("content-addressed evidence ID collision")
            return existing, False

        evidence = Evidence(
            evidence_id=evidence_id,
            source_id=source.source_id,
            locator=observation.url,
            captured_at=observation.captured_at,
            raw_payload=observation.raw_payload,
            content_digest=f"sha256:{payload_digest}",
            metadata={
                "http_status": observation.status_code,
                "headers": dict(observation.headers),
                "transport": "http",
            },
        )
        repository.save(evidence)
        return evidence, True
