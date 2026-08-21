"""First real-source adapter: BrasilAPI CNPJ API.

This module belongs to LEADS_FIRST_REAL_SOURCE_V1. It deliberately implements
one narrow acquisition path only: lookup of a known CNPJ in BrasilAPI,
preservation of the complete JSON response as Evidence, creation of a Company
shell, and extraction of a small set of CandidateFact records.

It does not normalize values, resolve entities, discover contacts, create
canonical facts, or qualify leads.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .domain import CandidateFact, Company, EntityRef, EntityType, Evidence, Provenance, Source, SourceType
from .persistence import SQLiteLeadStore


BASE_URL = "https://brasilapi.com.br/api/cnpj/v1"
AGENT = "searchleads.brasilapi.v1"
_CNPJ_DIGITS = re.compile(r"^\d{14}$")


class BrasilAPIError(RuntimeError):
    """Base error for the BrasilAPI source adapter."""


class BrasilAPIAcquisitionError(BrasilAPIError):
    """Raised when HTTP acquisition fails."""


class BrasilAPIPayloadError(BrasilAPIError):
    """Raised when a response cannot safely represent the requested company."""


JsonTransport = Callable[[str], Mapping[str, Any]]


def _clean_cnpj(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if not _CNPJ_DIGITS.fullmatch(digits):
        raise ValueError("cnpj must contain exactly 14 digits")
    return digits


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _content_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def _http_json_get(url: str) -> Mapping[str, Any]:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "searchleads/0.3 (+https://github.com/tihotm/searchleads)",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            payload = json.loads(response.read().decode(charset))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise BrasilAPIAcquisitionError(f"failed to fetch {url}: {exc}") from exc

    if not isinstance(payload, dict):
        raise BrasilAPIPayloadError("BrasilAPI response must be a JSON object")
    return payload


@dataclass(frozen=True, slots=True)
class BrasilAPIIngestionResult:
    company: Company
    source: Source
    evidence: Evidence
    candidate_facts: tuple[CandidateFact, ...]


class BrasilAPISource:
    """Specialized source adapter for one-company CNPJ lookup."""

    def __init__(self, transport: JsonTransport | None = None) -> None:
        self._transport = transport or _http_json_get

    def fetch(self, cnpj: str) -> Mapping[str, Any]:
        cleaned = _clean_cnpj(cnpj)
        payload = self._transport(f"{BASE_URL}/{cleaned}")
        if not isinstance(payload, Mapping):
            raise BrasilAPIPayloadError("BrasilAPI response must be a mapping")
        returned_cnpj = str(payload.get("cnpj", ""))
        if returned_cnpj != cleaned:
            raise BrasilAPIPayloadError(
                f"response CNPJ {returned_cnpj!r} does not match requested CNPJ {cleaned!r}"
            )
        if not str(payload.get("razao_social", "")).strip():
            raise BrasilAPIPayloadError("response is missing a non-blank razao_social")
        return payload

    def ingest(
        self,
        store: SQLiteLeadStore,
        cnpj: str,
        *,
        retrieved_at: datetime | None = None,
    ) -> BrasilAPIIngestionResult:
        cleaned = _clean_cnpj(cnpj)
        payload = self.fetch(cleaned)
        fetched_at = retrieved_at or datetime.now(timezone.utc)
        if fetched_at.tzinfo is None or fetched_at.utcoffset() is None:
            raise ValueError("retrieved_at must be timezone-aware")

        digest = _content_hash(payload)
        locator = f"{BASE_URL}/{cleaned}"
        source = Source(
            source_id=f"source:brasilapi:cnpj:{cleaned}",
            source_type=SourceType.DATASET,
            locator=locator,
            label="BrasilAPI CNPJ API",
        )
        evidence = Evidence(
            evidence_id=f"evidence:brasilapi:{cleaned}:{digest[:20]}",
            source_id=source.source_id,
            retrieved_at=fetched_at,
            payload=dict(payload),
            locator=locator,
            content_hash=f"sha256:{digest}",
        )
        company_id = f"company:cnpj:{cleaned}"
        company = store.get_company(company_id) or Company(
            company_id=company_id,
            created_at=fetched_at,
        )
        provenance = Provenance(
            evidence_ids=(evidence.evidence_id,),
            activity="extract_company_candidate_from_brasilapi_v1",
            generated_at=fetched_at,
            agent=AGENT,
        )
        subject = EntityRef(EntityType.COMPANY, company.company_id)
        facts = tuple(
            self._candidate_facts(
                payload=payload,
                subject=subject,
                provenance=provenance,
                cnpj=cleaned,
                digest=digest,
            )
        )

        store.save_source(source)
        store.save_evidence(evidence)
        store.save_company(company)
        for fact in facts:
            store.save_candidate_fact(fact)

        return BrasilAPIIngestionResult(
            company=company,
            source=source,
            evidence=evidence,
            candidate_facts=facts,
        )

    @staticmethod
    def _candidate_facts(
        *,
        payload: Mapping[str, Any],
        subject: EntityRef,
        provenance: Provenance,
        cnpj: str,
        digest: str,
    ) -> list[CandidateFact]:
        # Direct source-field extraction only. `porte` is exposed as an
        # explicit registry size classification; it is not interpreted as
        # employee count, revenue, or a generic commercial size band.
        fields = (
            ("cnpj", "business_registry_id"),
            ("razao_social", "legal_name"),
            ("nome_fantasia", "trade_name"),
            ("descricao_situacao_cadastral", "registration_status"),
            ("cnae_fiscal", "primary_cnae_code"),
            ("cnae_fiscal_descricao", "primary_cnae_description"),
            ("porte", "registry_size_class"),
            ("codigo_porte", "registry_size_code"),
            ("municipio", "city"),
            ("uf", "state"),
        )
        result: list[CandidateFact] = []
        for source_field, predicate in fields:
            if source_field not in payload:
                continue
            raw_value = payload[source_field]
            if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
                continue
            result.append(
                CandidateFact(
                    candidate_fact_id=(
                        f"candidate:brasilapi:{cnpj}:{predicate}:{digest[:16]}"
                    ),
                    subject=subject,
                    predicate=predicate,
                    raw_value=raw_value,
                    provenance=provenance,
                )
            )
        return result
