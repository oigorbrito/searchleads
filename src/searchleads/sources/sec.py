from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from urllib.request import Request, urlopen

from searchleads.domain import CandidateFact, Company, Evidence, Source

SEC_COMPANY_TICKERS_EXCHANGE_URL = (
    "https://www.sec.gov/files/company_tickers_exchange.json"
)
SEC_SOURCE_ID = "source:sec:company-tickers-exchange"


class SourceContractError(ValueError):
    """Raised when a known source no longer matches its expected contract."""


@dataclass(frozen=True, slots=True)
class SecCompanyRecord:
    cik: str
    name: str
    ticker: str
    exchange: str | None

    @property
    def company_id(self) -> str:
        return f"company:sec:cik:{self.cik}"


@dataclass(frozen=True, slots=True)
class SecCompanyBatch:
    source: Source
    evidence: Evidence
    companies: tuple[Company, ...]
    candidate_facts: tuple[CandidateFact, ...]


def acquire_company_tickers_exchange(*, user_agent: str, timeout: float = 30.0) -> bytes:
    """Fetch the SEC ticker/CIK/company/exchange association file.

    The SEC requests that automated clients identify themselves. The caller must
    therefore provide a non-empty User-Agent rather than relying on an implicit
    library default.
    """

    if not isinstance(user_agent, str) or not user_agent.strip():
        raise ValueError("user_agent must be non-empty text")
    if timeout <= 0:
        raise ValueError("timeout must be positive")

    request = Request(
        SEC_COMPANY_TICKERS_EXCHANGE_URL,
        headers={
            "User-Agent": user_agent.strip(),
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - known HTTPS source
        return response.read()


def parse_company_tickers_exchange(
    raw_content: bytes, *, limit: int | None = None
) -> tuple[SecCompanyRecord, ...]:
    if not isinstance(raw_content, bytes):
        raise SourceContractError("SEC payload must be bytes")
    if limit is not None and limit < 0:
        raise ValueError("limit cannot be negative")

    try:
        payload = json.loads(raw_content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceContractError("SEC payload is not valid JSON") from exc

    if not isinstance(payload, dict):
        raise SourceContractError("SEC payload root must be an object")

    fields = payload.get("fields")
    data = payload.get("data")
    expected_fields = ["cik", "name", "ticker", "exchange"]
    if fields != expected_fields:
        raise SourceContractError(
            f"SEC schema drift: expected fields {expected_fields!r}, got {fields!r}"
        )
    if not isinstance(data, list):
        raise SourceContractError("SEC data must be a list")

    selected = data if limit is None else data[:limit]
    records: list[SecCompanyRecord] = []
    for index, row in enumerate(selected):
        if not isinstance(row, list) or len(row) != 4:
            raise SourceContractError(f"SEC row {index} must contain exactly 4 values")
        cik, name, ticker, exchange = row
        records.append(
            SecCompanyRecord(
                cik=_normalize_cik(cik, index=index),
                name=_require_text(name, f"row {index} name"),
                ticker=_require_text(ticker, f"row {index} ticker"),
                exchange=_optional_text(exchange, f"row {index} exchange"),
            )
        )
    return tuple(records)


def ingest_company_tickers_exchange(
    raw_content: bytes,
    *,
    retrieved_at: str | None = None,
    limit: int | None = 25,
) -> SecCompanyBatch:
    records = parse_company_tickers_exchange(raw_content, limit=limit)
    digest = hashlib.sha256(raw_content).hexdigest()
    evidence_id = f"evidence:sha256:{digest}"
    source = Source(
        id=SEC_SOURCE_ID,
        name="SEC EDGAR company tickers exchange",
        kind="OFFICIAL_REGULATOR_DATASET",
        locator=SEC_COMPANY_TICKERS_EXCHANGE_URL,
    )
    evidence = Evidence(
        id=evidence_id,
        source_id=source.id,
        raw_content=raw_content,
        sha256=digest,
        retrieved_at=retrieved_at,
    )

    companies: list[Company] = []
    facts: list[CandidateFact] = []
    for record in records:
        companies.append(Company(id=record.company_id, legal_name=record.name))
        fact_values: tuple[tuple[str, object], ...] = (
            ("cik", record.cik),
            ("legal_name", record.name),
            ("ticker", record.ticker),
            ("exchange", record.exchange),
        )
        for field_name, value in fact_values:
            facts.append(
                CandidateFact(
                    id=f"candidate:{record.company_id}:{field_name}:{digest[:16]}",
                    subject_type="Company",
                    subject_id=record.company_id,
                    field_name=field_name,
                    value=value,
                    evidence_id=evidence.id,
                )
            )

    return SecCompanyBatch(
        source=source,
        evidence=evidence,
        companies=tuple(companies),
        candidate_facts=tuple(facts),
    )


def _normalize_cik(value: object, *, index: int) -> str:
    if isinstance(value, int) and value >= 0:
        return f"{value:010d}"
    if isinstance(value, str) and value.isdigit():
        return value.zfill(10)
    raise SourceContractError(f"row {index} cik must be a non-negative integer or digits")


def _require_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SourceContractError(f"{field_name} must be non-empty text")
    return value.strip()


def _optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _require_text(value, field_name)
