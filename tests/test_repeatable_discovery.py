from __future__ import annotations

from pathlib import Path

import pytest

from searchleads.repeatable_discovery import (
    EvidenceCache,
    KnownSourcePlan,
    ReplayIntegrityError,
    record_acquisition,
    replay_acquisition,
    sec_company_tickers_schema_fingerprint,
)
from searchleads.sources.sec import SEC_COMPANY_TICKERS_EXCHANGE_URL

FIXTURE = Path(__file__).parent / "fixtures" / "sec_company_tickers_exchange_sample.json"


def _plan(raw: bytes) -> KnownSourcePlan:
    return KnownSourcePlan(
        id="sec-company-tickers-exchange-v1",
        url=SEC_COMPANY_TICKERS_EXCHANGE_URL,
        parser_id="parse_company_tickers_exchange:v1",
        expected_schema_fingerprint=sec_company_tickers_schema_fingerprint(raw),
    )


def test_content_addressed_cache_roundtrip_is_deterministic(tmp_path: Path) -> None:
    raw = FIXTURE.read_bytes()
    cache = EvidenceCache(tmp_path / "cache")

    first = cache.put(raw)
    second = cache.put(raw)

    assert first == second
    assert cache.get(first) == raw
    assert len(tuple((tmp_path / "cache").iterdir())) == 1


def test_record_and_replay_known_source_without_network(tmp_path: Path) -> None:
    raw = FIXTURE.read_bytes()
    cache = EvidenceCache(tmp_path / "cache")
    plan = _plan(raw)

    record = record_acquisition(
        plan,
        raw,
        cache=cache,
        schema_fingerprint=sec_company_tickers_schema_fingerprint,
    )
    replayed = replay_acquisition(
        plan,
        record,
        cache=cache,
        schema_fingerprint=sec_company_tickers_schema_fingerprint,
    )

    assert replayed == raw


def test_replay_rejects_plan_drift(tmp_path: Path) -> None:
    raw = FIXTURE.read_bytes()
    cache = EvidenceCache(tmp_path / "cache")
    plan = _plan(raw)
    record = record_acquisition(
        plan,
        raw,
        cache=cache,
        schema_fingerprint=sec_company_tickers_schema_fingerprint,
    )
    changed_plan = KnownSourcePlan(
        id=plan.id,
        url=plan.url,
        parser_id="parse_company_tickers_exchange:v2",
        expected_schema_fingerprint=plan.expected_schema_fingerprint,
    )

    with pytest.raises(ReplayIntegrityError, match="Plan fingerprint changed"):
        replay_acquisition(
            changed_plan,
            record,
            cache=cache,
            schema_fingerprint=sec_company_tickers_schema_fingerprint,
        )


def test_acquisition_rejects_schema_drift_before_cache_write(tmp_path: Path) -> None:
    raw = FIXTURE.read_bytes()
    drifted = raw.replace(b'"ticker"', b'"symbol"')
    cache = EvidenceCache(tmp_path / "cache")
    plan = _plan(raw)

    with pytest.raises(ReplayIntegrityError, match="schema drifted"):
        record_acquisition(
            plan,
            drifted,
            cache=cache,
            schema_fingerprint=sec_company_tickers_schema_fingerprint,
        )

    assert tuple((tmp_path / "cache").iterdir()) == ()


def test_cache_detects_post_write_mutation(tmp_path: Path) -> None:
    raw = FIXTURE.read_bytes()
    cache = EvidenceCache(tmp_path / "cache")
    digest = cache.put(raw)
    (tmp_path / "cache" / digest).write_bytes(b"mutated")

    with pytest.raises(ReplayIntegrityError, match="content address"):
        cache.get(digest)
