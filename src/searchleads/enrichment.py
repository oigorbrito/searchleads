from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from urllib.request import Request, urlopen

from .domain import CandidateFact, CanonicalFact, Evidence, Source

SEC_SUBMISSIONS_URL_TEMPLATE = "https://data.sec.gov/submissions/CIK{cik}.json"


class EnrichmentContractError(ValueError):
    """Raised when enrichment evidence does not satisfy the known source contract."""


@dataclass(frozen=True, slots=True)
class FactConflict:
    subject_type: str
    subject_id: str
    field_name: str
    candidate_fact_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FusionResult:
    canonical_facts: tuple[CanonicalFact, ...]
    conflicts: tuple[FactConflict, ...]


@dataclass(frozen=True, slots=True)
class SecSubmissionBatch:
    source: Source
    evidence: Evidence
    candidate_facts: tuple[CandidateFact, ...]


def acquire_sec_submission(
    cik: str, *, user_agent: str, timeout: float = 30.0
) -> bytes:
    normalized_cik = _normalize_cik(cik)
    if not isinstance(user_agent, str) or not user_agent.strip():
        raise ValueError("user_agent must be non-empty text")
    if timeout <= 0:
        raise ValueError("timeout must be positive")

    url = SEC_SUBMISSIONS_URL_TEMPLATE.format(cik=normalized_cik)
    request = Request(
        url,
        headers={"User-Agent": user_agent.strip(), "Accept": "application/json"},
    )
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - known HTTPS source
        return response.read()


def ingest_sec_submission(
    raw_content: bytes,
    *,
    company_id: str,
    expected_cik: str,
    retrieved_at: str | None = None,
) -> SecSubmissionBatch:
    cik = _normalize_cik(expected_cik)
    try:
        payload = json.loads(raw_content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EnrichmentContractError("SEC submissions payload is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise EnrichmentContractError("SEC submissions payload root must be an object")

    payload_cik = _normalize_cik(payload.get("cik"))
    if payload_cik != cik:
        raise EnrichmentContractError(
            f"SEC submissions CIK mismatch: expected {cik}, got {payload_cik}"
        )

    digest = hashlib.sha256(raw_content).hexdigest()
    url = SEC_SUBMISSIONS_URL_TEMPLATE.format(cik=cik)
    source = Source(
        id=f"source:sec:submissions:{cik}",
        name=f"SEC EDGAR submissions {cik}",
        kind="OFFICIAL_REGULATOR_ENTITY_DATA",
        locator=url,
    )
    evidence = Evidence(
        id=f"evidence:sha256:{digest}",
        source_id=source.id,
        raw_content=raw_content,
        sha256=digest,
        retrieved_at=retrieved_at,
    )

    fields = _extract_submission_fields(payload, cik=cik)
    candidate_facts = tuple(
        CandidateFact(
            id=f"candidate:{company_id}:{field_name}:{digest[:16]}",
            subject_type="Company",
            subject_id=company_id,
            field_name=field_name,
            value=value,
            evidence_id=evidence.id,
        )
        for field_name, value in fields
    )
    return SecSubmissionBatch(
        source=source,
        evidence=evidence,
        candidate_facts=candidate_facts,
    )


def fuse_candidate_facts(candidate_facts: tuple[CandidateFact, ...]) -> FusionResult:
    grouped: dict[tuple[str, str, str], list[CandidateFact]] = {}
    for fact in candidate_facts:
        key = (fact.subject_type, fact.subject_id, fact.field_name)
        grouped.setdefault(key, []).append(fact)

    canonical: list[CanonicalFact] = []
    conflicts: list[FactConflict] = []
    for (subject_type, subject_id, field_name), facts in sorted(grouped.items()):
        values = {_stable_json(fact.value) for fact in facts}
        supporting_ids = tuple(sorted(fact.id for fact in facts))
        if len(values) != 1:
            conflicts.append(
                FactConflict(
                    subject_type=subject_type,
                    subject_id=subject_id,
                    field_name=field_name,
                    candidate_fact_ids=supporting_ids,
                )
            )
            continue

        value = facts[0].value
        digest = hashlib.sha256(
            _stable_json(
                {
                    "subject_type": subject_type,
                    "subject_id": subject_id,
                    "field_name": field_name,
                    "value": value,
                }
            ).encode("utf-8")
        ).hexdigest()
        canonical.append(
            CanonicalFact(
                id=f"canonical:sha256:{digest}",
                subject_type=subject_type,
                subject_id=subject_id,
                field_name=field_name,
                value=value,
                supporting_candidate_fact_ids=supporting_ids,
            )
        )

    return FusionResult(tuple(canonical), tuple(conflicts))


def _extract_submission_fields(payload: dict[str, object], *, cik: str) -> tuple[tuple[str, object], ...]:
    tickers = payload.get("tickers")
    exchanges = payload.get("exchanges")
    addresses = payload.get("addresses")
    if not isinstance(tickers, list) or not tickers or not isinstance(tickers[0], str):
        raise EnrichmentContractError("SEC submissions tickers must contain a primary ticker")
    if not isinstance(exchanges, list) or not exchanges or not isinstance(exchanges[0], str):
        raise EnrichmentContractError("SEC submissions exchanges must contain a primary exchange")
    if not isinstance(addresses, dict):
        raise EnrichmentContractError("SEC submissions addresses must be an object")

    business = addresses.get("business")
    mailing = addresses.get("mailing")
    if not isinstance(business, dict) or not isinstance(mailing, dict):
        raise EnrichmentContractError("SEC submissions requires business and mailing addresses")

    return (
        ("cik", cik),
        ("legal_name", _required_text(payload, "name")),
        ("entity_type", _required_text(payload, "entityType")),
        ("sic", _required_text(payload, "sic")),
        ("sic_description", _required_text(payload, "sicDescription")),
        ("ein", _required_text(payload, "ein")),
        ("ticker", tickers[0]),
        ("exchange", exchanges[0]),
        ("fiscal_year_end", _required_text(payload, "fiscalYearEnd")),
        ("state_of_incorporation", _required_text(payload, "stateOfIncorporation")),
        ("business_address", business),
        ("mailing_address", mailing),
        ("phone", _required_text(payload, "phone")),
        ("former_names", _former_names(payload.get("formerNames"))),
    )


def _required_text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EnrichmentContractError(f"SEC submissions field {key!r} must be non-empty text")
    return value.strip()


def _former_names(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise EnrichmentContractError("SEC submissions formerNames must be a list")
    for item in value:
        if not isinstance(item, dict):
            raise EnrichmentContractError("SEC submissions formerNames items must be objects")
    return value


def _normalize_cik(value: object) -> str:
    if isinstance(value, int) and value >= 0:
        return f"{value:010d}"
    if isinstance(value, str) and value.isdigit():
        return value.zfill(10)
    raise EnrichmentContractError("CIK must be a non-negative integer or digit string")


def _stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
