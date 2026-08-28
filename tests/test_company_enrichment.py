from __future__ import annotations

from pathlib import Path

from searchleads.enrichment import fuse_candidate_facts, ingest_sec_submission
from searchleads.sources.sec import ingest_company_tickers_exchange

TICKERS_FIXTURE = Path(__file__).parent / "fixtures" / "sec_company_tickers_exchange_sample.json"
SUBMISSIONS_FIXTURE = Path(__file__).parent / "fixtures" / "sec_nvidia_submissions_sample.json"


def test_nvidia_sec_submission_produces_14_candidate_facts() -> None:
    batch = ingest_sec_submission(
        SUBMISSIONS_FIXTURE.read_bytes(),
        company_id="company:sec:cik:0001045810",
        expected_cik="1045810",
        retrieved_at="2026-08-28T00:00:00Z",
    )

    assert len(batch.candidate_facts) == 14
    assert batch.evidence.raw_content == SUBMISSIONS_FIXTURE.read_bytes()
    assert all(fact.evidence_id == batch.evidence.id for fact in batch.candidate_facts)


def test_two_sec_sources_fuse_to_14_canonical_facts_without_conflict() -> None:
    discovery = ingest_company_tickers_exchange(TICKERS_FIXTURE.read_bytes())
    nvidia_discovery_facts = tuple(
        fact
        for fact in discovery.candidate_facts
        if fact.subject_id == "company:sec:cik:0001045810"
    )
    enrichment = ingest_sec_submission(
        SUBMISSIONS_FIXTURE.read_bytes(),
        company_id="company:sec:cik:0001045810",
        expected_cik="0001045810",
    )

    fusion = fuse_candidate_facts(nvidia_discovery_facts + enrichment.candidate_facts)

    assert len(nvidia_discovery_facts) == 4
    assert len(enrichment.candidate_facts) == 14
    assert len(fusion.canonical_facts) == 14
    assert fusion.conflicts == ()


def test_overlapping_canonical_facts_keep_multiple_supporting_candidates() -> None:
    discovery = ingest_company_tickers_exchange(TICKERS_FIXTURE.read_bytes())
    nvidia_discovery_facts = tuple(
        fact
        for fact in discovery.candidate_facts
        if fact.subject_id == "company:sec:cik:0001045810"
    )
    enrichment = ingest_sec_submission(
        SUBMISSIONS_FIXTURE.read_bytes(),
        company_id="company:sec:cik:0001045810",
        expected_cik="0001045810",
    )

    fusion = fuse_candidate_facts(nvidia_discovery_facts + enrichment.candidate_facts)
    by_field = {fact.field_name: fact for fact in fusion.canonical_facts}

    for field_name in ("cik", "legal_name", "ticker", "exchange"):
        assert len(by_field[field_name].supporting_candidate_fact_ids) == 2


def test_conflicting_values_do_not_become_canonical_fact() -> None:
    discovery = ingest_company_tickers_exchange(TICKERS_FIXTURE.read_bytes())
    nvidia_facts = tuple(
        fact
        for fact in discovery.candidate_facts
        if fact.subject_id == "company:sec:cik:0001045810"
    )
    conflicting = ingest_sec_submission(
        SUBMISSIONS_FIXTURE.read_bytes().replace(b'"NVIDIA CORP"', b'"NVIDIA CORPORATION"'),
        company_id="company:sec:cik:0001045810",
        expected_cik="0001045810",
    )

    fusion = fuse_candidate_facts(nvidia_facts + conflicting.candidate_facts)

    assert any(conflict.field_name == "legal_name" for conflict in fusion.conflicts)
    assert all(fact.field_name != "legal_name" for fact in fusion.canonical_facts)
