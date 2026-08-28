from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from searchleads.sources.sec import (
    SEC_COMPANY_TICKERS_EXCHANGE_URL,
    SourceContractError,
    ingest_company_tickers_exchange,
    parse_company_tickers_exchange,
)

FIXTURE = Path(__file__).parent / "fixtures" / "sec_company_tickers_exchange_sample.json"


def _fixture_bytes() -> bytes:
    return FIXTURE.read_bytes()


def test_parse_sec_company_tickers_exchange_normalizes_cik() -> None:
    records = parse_company_tickers_exchange(_fixture_bytes())

    assert len(records) == 3
    assert records[0].cik == "0001045810"
    assert records[0].name == "NVIDIA CORP"
    assert records[0].ticker == "NVDA"
    assert records[0].exchange == "Nasdaq"


def test_ingestion_preserves_raw_evidence_and_fact_level_provenance() -> None:
    raw = _fixture_bytes()
    batch = ingest_company_tickers_exchange(raw, retrieved_at="2026-08-28T00:00:00Z")

    assert batch.source.locator == SEC_COMPANY_TICKERS_EXCHANGE_URL
    assert batch.evidence.raw_content == raw
    assert batch.evidence.sha256 == sha256(raw).hexdigest()
    assert len(batch.companies) == 3
    assert len(batch.candidate_facts) == 12
    assert all(fact.evidence_id == batch.evidence.id for fact in batch.candidate_facts)
    assert batch.companies[0].id == "company:sec:cik:0001045810"


def test_company_discovery_does_not_create_leads() -> None:
    batch = ingest_company_tickers_exchange(_fixture_bytes())

    assert not hasattr(batch, "leads")


def test_limit_is_deterministic_and_bounded() -> None:
    batch = ingest_company_tickers_exchange(_fixture_bytes(), limit=2)

    assert [company.id for company in batch.companies] == [
        "company:sec:cik:0001045810",
        "company:sec:cik:0000320193",
    ]
    assert len(batch.candidate_facts) == 8


def test_schema_drift_is_rejected() -> None:
    drifted = b'{"fields":["cik","name","symbol","exchange"],"data":[]}'

    with pytest.raises(SourceContractError, match="schema drift"):
        parse_company_tickers_exchange(drifted)


def test_malformed_rows_are_rejected() -> None:
    malformed = b'{"fields":["cik","name","ticker","exchange"],"data":[[1,"ACME"]]}'

    with pytest.raises(SourceContractError, match="exactly 4"):
        parse_company_tickers_exchange(malformed)


def test_negative_limit_is_rejected() -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        parse_company_tickers_exchange(_fixture_bytes(), limit=-1)
