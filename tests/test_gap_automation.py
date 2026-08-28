from __future__ import annotations

from pathlib import Path

from searchleads.gap_automation import GapAutomationState, run_nvidia_gap_cycle
from searchleads.repeatable_discovery import EvidenceCache
from searchleads.sources.sec import ingest_company_tickers_exchange

TICKERS_FIXTURE = Path(__file__).parent / "fixtures" / "sec_company_tickers_exchange_sample.json"
SUBMISSIONS_FIXTURE = Path(__file__).parent / "fixtures" / "sec_nvidia_submissions_sample.json"


def _nvidia_discovery_facts():  # type: ignore[no-untyped-def]
    batch = ingest_company_tickers_exchange(TICKERS_FIXTURE.read_bytes())
    return tuple(
        fact
        for fact in batch.candidate_facts
        if fact.subject_id == "company:sec:cik:0001045810"
    )


def test_nvidia_known_source_closes_supported_gaps(tmp_path: Path) -> None:
    acquisitions = 0

    def acquire() -> bytes:
        nonlocal acquisitions
        acquisitions += 1
        return SUBMISSIONS_FIXTURE.read_bytes()

    result = run_nvidia_gap_cycle(
        existing_candidate_facts=_nvidia_discovery_facts(),
        required_fields=("ein", "sic", "business_address", "phone"),
        cache=EvidenceCache(tmp_path / "cache"),
        state=GapAutomationState(),
        acquire=acquire,
    )

    assert result.gaps_before == ("ein", "sic", "business_address", "phone")
    assert result.gaps_after == ()
    assert result.network_acquisitions == 1
    assert result.used_cache is False
    assert acquisitions == 1


def test_second_execution_replays_cache_without_network(tmp_path: Path) -> None:
    acquisitions = 0
    cache = EvidenceCache(tmp_path / "cache")

    def acquire() -> bytes:
        nonlocal acquisitions
        acquisitions += 1
        return SUBMISSIONS_FIXTURE.read_bytes()

    first = run_nvidia_gap_cycle(
        existing_candidate_facts=_nvidia_discovery_facts(),
        required_fields=("ein", "sic", "business_address", "phone"),
        cache=cache,
        state=GapAutomationState(),
        acquire=acquire,
    )
    second = run_nvidia_gap_cycle(
        existing_candidate_facts=_nvidia_discovery_facts(),
        required_fields=("ein", "sic", "business_address", "phone"),
        cache=cache,
        state=first.state,
        acquire=acquire,
    )

    assert acquisitions == 1
    assert second.network_acquisitions == 0
    assert second.used_cache is True
    assert second.gaps_after == ()
    assert second.canonical_facts == first.canonical_facts


def test_unknown_gap_does_not_trigger_generic_crawler(tmp_path: Path) -> None:
    acquisitions = 0

    def acquire() -> bytes:
        nonlocal acquisitions
        acquisitions += 1
        return SUBMISSIONS_FIXTURE.read_bytes()

    result = run_nvidia_gap_cycle(
        existing_candidate_facts=_nvidia_discovery_facts(),
        required_fields=("employee_count",),
        cache=EvidenceCache(tmp_path / "cache"),
        state=GapAutomationState(),
        acquire=acquire,
    )

    assert result.gaps_before == ("employee_count",)
    assert result.gaps_after == ("employee_count",)
    assert result.unsupported_gaps == ("employee_count",)
    assert result.network_acquisitions == 0
    assert acquisitions == 0


def test_canonical_provenance_survives_gap_cycle(tmp_path: Path) -> None:
    result = run_nvidia_gap_cycle(
        existing_candidate_facts=_nvidia_discovery_facts(),
        required_fields=("ein",),
        cache=EvidenceCache(tmp_path / "cache"),
        state=GapAutomationState(),
        acquire=SUBMISSIONS_FIXTURE.read_bytes,
    )
    candidate_ids = {fact.id for fact in result.candidate_facts}

    assert all(
        set(fact.supporting_candidate_fact_ids).issubset(candidate_ids)
        for fact in result.canonical_facts
    )
