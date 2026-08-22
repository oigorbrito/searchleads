#!/usr/bin/env python3
"""Evaluate a manually CFO-reviewed dental batch without scraping the CFO portal.

Input rows keep public discovery claims separate from official verification fields.
The default campaign legal status is PENDING_REVIEW, so the script cannot emit
READY unless an explicit CONFIRMED_FOR_OUTREACH value is supplied.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from searchleads.dental_facial_surgery_icp import DentalICPSignal, DentalSignalKind
from searchleads.dental_outreach import (
    CFOProfessionalVerification,
    CFORegistrationState,
    CampaignLegalStatus,
    evaluate_dental_outreach_readiness,
)
from searchleads.dental_regulatory import DentalOfferTrack, qualify_dental_person_for_offer


def _truthy(value: str | None) -> bool:
    return (value or "").strip().casefold() in {"1", "true", "yes", "y", "sim", "s"}


def _split_semicolon(value: str | None) -> tuple[str, ...]:
    return tuple(part.strip() for part in (value or "").split(";") if part.strip())


def _enum_or_default(enum_type, value: str | None, default):
    text = (value or "").strip()
    return enum_type(text) if text else default


def evaluate_row(row: dict[str, str]) -> dict[str, str]:
    person_id = row["person_id"].strip()
    if not person_id:
        raise ValueError("person_id is required")

    signals: list[DentalICPSignal] = []
    public_evidence_id = (row.get("public_evidence_url") or "").strip() or f"public-discovery:{person_id}"

    title = (row.get("professional_title") or "").strip()
    if title:
        signals.append(DentalICPSignal(
            f"batch-title:{person_id}", person_id, DentalSignalKind.PROFESSIONAL_TITLE,
            title, (public_evidence_id,), row.get("company_id") or None,
        ))

    claimed_state = (row.get("claimed_cro_state") or "").strip().upper()
    if claimed_state:
        signals.append(DentalICPSignal(
            f"batch-state:{person_id}", person_id, DentalSignalKind.STATE,
            claimed_state, (public_evidence_id,), row.get("company_id") or None,
        ))

    if _truthy(row.get("has_public_professional_contact")):
        signals.append(DentalICPSignal(
            f"batch-contact:{person_id}", person_id, DentalSignalKind.DISCOVERED_CONTACT,
            "PUBLIC_PROFESSIONAL_CHANNEL", (public_evidence_id,), row.get("company_id") or None,
        ))

    offer_track = _enum_or_default(
        DentalOfferTrack,
        row.get("offer_track"),
        DentalOfferTrack.CEOF_SPECIALIZATION,
    )
    qualification = qualify_dental_person_for_offer(
        person_id,
        signals,
        company_id=row.get("company_id") or None,
        offer_track=offer_track,
    )

    registration_state = _enum_or_default(
        CFORegistrationState,
        row.get("cfo_registration_state"),
        CFORegistrationState.PENDING,
    )
    verified_state = (row.get("verified_cro_state") or "").strip().upper() or None
    verified_number = (row.get("verified_cro_number") or "").strip() or None
    cfo_source_url = (row.get("cfo_source_url") or "").strip()
    evidence_id = cfo_source_url or f"cfo-review-pending:{person_id}"

    verification = CFOProfessionalVerification(
        person_id=person_id,
        registration_state=registration_state,
        cro_state=verified_state,
        cro_number=verified_number,
        specialty_names=_split_semicolon(row.get("verified_specialties")),
        evidence_id=evidence_id,
    )
    legal_status = _enum_or_default(
        CampaignLegalStatus,
        row.get("campaign_legal_status"),
        CampaignLegalStatus.PENDING_REVIEW,
    )
    decision = evaluate_dental_outreach_readiness(
        qualification,
        verification,
        campaign_legal_status=legal_status,
    )

    out = dict(row)
    out.update({
        "fit": qualification.base.fit.value,
        "intent": qualification.base.intent.value,
        "qualification_status": qualification.status.value,
        "regulatory_eligibility": qualification.regulatory_eligibility.value,
        "outreach_readiness": decision.readiness.value,
        "priority": decision.priority,
        "decision_reason": " | ".join(decision.reasons),
    })
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    with args.input.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = [evaluate_row(dict(row)) for row in reader]

    ready = sum(row["outreach_readiness"] == "READY" for row in rows)
    review = sum(row["outreach_readiness"] == "REVIEW" for row in rows)
    exclude = sum(row["outreach_readiness"] == "EXCLUDE" for row in rows)
    print(f"ROWS={len(rows)} READY={ready} REVIEW={review} EXCLUDE={exclude}")

    if args.output:
        fieldnames = list(rows[0]) if rows else []
        with args.output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    main()
