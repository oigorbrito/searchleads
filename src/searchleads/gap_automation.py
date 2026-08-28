from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Callable

from .domain import CandidateFact, CanonicalFact
from .enrichment import (
    SEC_SUBMISSIONS_URL_TEMPLATE,
    fuse_candidate_facts,
    ingest_sec_submission,
)
from .repeatable_discovery import (
    AcquisitionRecord,
    EvidenceCache,
    KnownSourcePlan,
    ReplayIntegrityError,
    record_acquisition,
    replay_acquisition,
)

NVIDIA_CIK = "0001045810"
NVIDIA_COMPANY_ID = "company:sec:cik:0001045810"
SEC_SUBMISSION_CAPABILITY_FIELDS = frozenset(
    {
        "cik",
        "legal_name",
        "entity_type",
        "sic",
        "sic_description",
        "ein",
        "ticker",
        "exchange",
        "fiscal_year_end",
        "state_of_incorporation",
        "business_address",
        "mailing_address",
        "phone",
        "former_names",
    }
)
_SCHEMA_DESCRIPTOR = (
    "cik",
    "entityType",
    "sic",
    "sicDescription",
    "name",
    "tickers",
    "exchanges",
    "ein",
    "fiscalYearEnd",
    "stateOfIncorporation",
    "addresses.business",
    "addresses.mailing",
    "phone",
    "formerNames",
)
SEC_SUBMISSION_SCHEMA_FINGERPRINT_V1 = hashlib.sha256(
    json.dumps(_SCHEMA_DESCRIPTOR, separators=(",", ":")).encode("utf-8")
).hexdigest()


@dataclass(frozen=True, slots=True)
class GapAutomationState:
    submission_record: AcquisitionRecord | None = None


@dataclass(frozen=True, slots=True)
class GapAutomationResult:
    gaps_before: tuple[str, ...]
    gaps_after: tuple[str, ...]
    canonical_facts: tuple[CanonicalFact, ...]
    candidate_facts: tuple[CandidateFact, ...]
    state: GapAutomationState
    network_acquisitions: int
    used_cache: bool
    unsupported_gaps: tuple[str, ...]


def detect_gaps(
    canonical_facts: tuple[CanonicalFact, ...], required_fields: tuple[str, ...]
) -> tuple[str, ...]:
    present = {fact.field_name for fact in canonical_facts}
    return tuple(field for field in required_fields if field not in present)


def run_nvidia_gap_cycle(
    *,
    existing_candidate_facts: tuple[CandidateFact, ...],
    required_fields: tuple[str, ...],
    cache: EvidenceCache,
    state: GapAutomationState,
    acquire: Callable[[], bytes],
) -> GapAutomationResult:
    before_fusion = fuse_candidate_facts(existing_candidate_facts)
    gaps_before = detect_gaps(before_fusion.canonical_facts, required_fields)
    unsupported = tuple(
        field for field in gaps_before if field not in SEC_SUBMISSION_CAPABILITY_FIELDS
    )
    actionable = tuple(
        field for field in gaps_before if field in SEC_SUBMISSION_CAPABILITY_FIELDS
    )

    if not actionable:
        return GapAutomationResult(
            gaps_before=gaps_before,
            gaps_after=gaps_before,
            canonical_facts=before_fusion.canonical_facts,
            candidate_facts=existing_candidate_facts,
            state=state,
            network_acquisitions=0,
            used_cache=False,
            unsupported_gaps=unsupported,
        )

    plan = KnownSourcePlan(
        id="sec-nvidia-submission-v1",
        url=SEC_SUBMISSIONS_URL_TEMPLATE.format(cik=NVIDIA_CIK),
        parser_id="ingest_sec_submission:v1",
        expected_schema_fingerprint=SEC_SUBMISSION_SCHEMA_FINGERPRINT_V1,
    )

    if state.submission_record is None:
        raw = acquire()
        record = record_acquisition(
            plan,
            raw,
            cache=cache,
            schema_fingerprint=sec_submission_schema_fingerprint,
        )
        network_acquisitions = 1
        used_cache = False
    else:
        record = state.submission_record
        raw = replay_acquisition(
            plan,
            record,
            cache=cache,
            schema_fingerprint=sec_submission_schema_fingerprint,
        )
        network_acquisitions = 0
        used_cache = True

    enrichment = ingest_sec_submission(
        raw,
        company_id=NVIDIA_COMPANY_ID,
        expected_cik=NVIDIA_CIK,
    )
    combined = _merge_candidate_facts(existing_candidate_facts, enrichment.candidate_facts)
    fusion = fuse_candidate_facts(combined)
    _validate_canonical_provenance(combined, fusion.canonical_facts)
    gaps_after = detect_gaps(fusion.canonical_facts, required_fields)

    return GapAutomationResult(
        gaps_before=gaps_before,
        gaps_after=gaps_after,
        canonical_facts=fusion.canonical_facts,
        candidate_facts=combined,
        state=GapAutomationState(record),
        network_acquisitions=network_acquisitions,
        used_cache=used_cache,
        unsupported_gaps=unsupported,
    )


def sec_submission_schema_fingerprint(raw_content: bytes) -> str:
    try:
        payload = json.loads(raw_content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReplayIntegrityError("SEC submission is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ReplayIntegrityError("SEC submission root must be an object")

    required_root = {
        "cik",
        "entityType",
        "sic",
        "sicDescription",
        "name",
        "tickers",
        "exchanges",
        "ein",
        "fiscalYearEnd",
        "stateOfIncorporation",
        "addresses",
        "phone",
        "formerNames",
    }
    if not required_root.issubset(payload):
        raise ReplayIntegrityError("SEC submission schema drifted: required fields missing")
    addresses = payload.get("addresses")
    if not isinstance(addresses, dict) or not {"business", "mailing"}.issubset(addresses):
        raise ReplayIntegrityError("SEC submission schema drifted: address fields missing")
    return SEC_SUBMISSION_SCHEMA_FINGERPRINT_V1


def _merge_candidate_facts(
    existing: tuple[CandidateFact, ...], new: tuple[CandidateFact, ...]
) -> tuple[CandidateFact, ...]:
    by_id = {fact.id: fact for fact in existing}
    for fact in new:
        by_id.setdefault(fact.id, fact)
    return tuple(by_id[key] for key in sorted(by_id))


def _validate_canonical_provenance(
    candidates: tuple[CandidateFact, ...], canonical: tuple[CanonicalFact, ...]
) -> None:
    candidate_ids = {fact.id for fact in candidates}
    for fact in canonical:
        if not set(fact.supporting_candidate_fact_ids).issubset(candidate_ids):
            raise ReplayIntegrityError("CanonicalFact references missing CandidateFact provenance")
