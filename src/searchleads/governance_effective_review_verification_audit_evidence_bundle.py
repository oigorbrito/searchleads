from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .governance_effective_review_verification_audit import (
    EffectiveReviewVerificationAuditEntry,
    EffectiveReviewVerificationAuditRepository,
    verification_audit_entry_to_mapping,
)


VERIFICATION_AUDIT_EVIDENCE_SCHEMA_VERSION = "effective-review-verification-audit-evidence-bundle/v1"


class EffectiveReviewVerificationAuditEvidenceError(RuntimeError):
    pass


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _entry_hash_payload(header: dict[str, Any]) -> dict[str, Any]:
    return {
        "audit_entry_id": header.get("audit_entry_id"),
        "sequence": header.get("sequence"),
        "receipt_id": header.get("receipt_id"),
        "evidence_sha256": header.get("evidence_sha256"),
        "receipt_sha256": header.get("receipt_sha256"),
        "previous_entry_hash": header.get("previous_entry_hash"),
    }


def _header(entry: EffectiveReviewVerificationAuditEntry) -> dict[str, Any]:
    return {
        "audit_entry_id": entry.audit_entry_id,
        "sequence": entry.sequence,
        "receipt_id": entry.receipt_id,
        "evidence_sha256": entry.evidence_sha256,
        "receipt_sha256": entry.receipt_sha256,
        "previous_entry_hash": entry.previous_entry_hash,
        "entry_hash": entry.entry_hash,
    }


def _unsigned_mapping(*, audit_entry_id: str, receipt_id: str, evidence_sha256: str, receipt: dict[str, Any], audit_entry: dict[str, Any], chain_headers: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    return {
        "schema_version": VERIFICATION_AUDIT_EVIDENCE_SCHEMA_VERSION,
        "audit_entry_id": audit_entry_id,
        "receipt_id": receipt_id,
        "evidence_sha256": evidence_sha256,
        "receipt": receipt,
        "audit_entry": audit_entry,
        "chain_headers": list(chain_headers),
        "send_authorized": False,
        "evidence_is_campaign_authorization": False,
        "evidence_is_human_approval": False,
        "evidence_is_observational_only": True,
        "changes_auth_campaign_001": False,
        "changes_preflight": False,
        "changes_pilot_release": False,
        "changes_legal_signoff": False,
        "changes_professional_verification": False,
        "changes_source_freshness": False,
    }


@dataclass(frozen=True, slots=True)
class EffectiveReviewVerificationAuditEvidenceBundle:
    audit_entry_id: str
    receipt_id: str
    evidence_sha256: str
    receipt: dict[str, Any]
    audit_entry: dict[str, Any]
    chain_headers: tuple[dict[str, Any], ...]
    export_sha256: str


def build_effective_review_verification_audit_evidence_bundle(*, audit_repository: EffectiveReviewVerificationAuditRepository, audit_entry_id: str) -> EffectiveReviewVerificationAuditEvidenceBundle:
    if not audit_entry_id.strip():
        raise ValueError("audit_entry_id must not be blank")
    entries = audit_repository.list_entries()
    selected_index = next((index for index, entry in enumerate(entries) if entry.audit_entry_id == audit_entry_id), None)
    if selected_index is None:
        raise KeyError(audit_entry_id)
    selected = entries[selected_index]
    receipt = dict(selected.receipt)
    audit_entry = verification_audit_entry_to_mapping(selected)
    chain_headers = tuple(_header(entry) for entry in entries[: selected_index + 1])
    unsigned = _unsigned_mapping(
        audit_entry_id=selected.audit_entry_id,
        receipt_id=selected.receipt_id,
        evidence_sha256=selected.evidence_sha256,
        receipt=receipt,
        audit_entry=audit_entry,
        chain_headers=chain_headers,
    )
    export_sha256 = _sha256(_canonical_json(unsigned))
    bundle = EffectiveReviewVerificationAuditEvidenceBundle(
        audit_entry_id=selected.audit_entry_id,
        receipt_id=selected.receipt_id,
        evidence_sha256=selected.evidence_sha256,
        receipt=receipt,
        audit_entry=audit_entry,
        chain_headers=chain_headers,
        export_sha256=export_sha256,
    )
    verify_effective_review_verification_audit_evidence_bundle(verification_audit_evidence_bundle_to_mapping(bundle))
    return bundle


def verification_audit_evidence_bundle_to_mapping(bundle: EffectiveReviewVerificationAuditEvidenceBundle) -> dict[str, Any]:
    payload = _unsigned_mapping(
        audit_entry_id=bundle.audit_entry_id,
        receipt_id=bundle.receipt_id,
        evidence_sha256=bundle.evidence_sha256,
        receipt=bundle.receipt,
        audit_entry=bundle.audit_entry,
        chain_headers=bundle.chain_headers,
    )
    payload["export_sha256"] = bundle.export_sha256
    return payload


def verify_effective_review_verification_audit_evidence_bundle(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise EffectiveReviewVerificationAuditEvidenceError("verification audit evidence bundle must be an object")
    if payload.get("schema_version") != VERIFICATION_AUDIT_EVIDENCE_SCHEMA_VERSION:
        raise EffectiveReviewVerificationAuditEvidenceError("unsupported verification audit evidence schema version")

    required_false = (
        "send_authorized",
        "evidence_is_campaign_authorization",
        "evidence_is_human_approval",
        "changes_auth_campaign_001",
        "changes_preflight",
        "changes_pilot_release",
        "changes_legal_signoff",
        "changes_professional_verification",
        "changes_source_freshness",
    )
    if any(payload.get(field) is not False for field in required_false):
        raise EffectiveReviewVerificationAuditEvidenceError("verification audit evidence violates negative-scope invariants")
    if payload.get("evidence_is_observational_only") is not True:
        raise EffectiveReviewVerificationAuditEvidenceError("verification audit evidence must remain observational only")

    receipt = payload.get("receipt")
    audit_entry = payload.get("audit_entry")
    chain_headers = payload.get("chain_headers")
    if not isinstance(receipt, dict) or not isinstance(audit_entry, dict):
        raise EffectiveReviewVerificationAuditEvidenceError("receipt and audit_entry must be objects")
    if not isinstance(chain_headers, list) or not chain_headers:
        raise EffectiveReviewVerificationAuditEvidenceError("chain_headers must be a non-empty list")
    if receipt.get("send_authorized") is not False or receipt.get("verification_is_campaign_authorization") is not False or receipt.get("verification_is_human_approval") is not False or receipt.get("receipt_is_observational_only") is not True:
        raise EffectiveReviewVerificationAuditEvidenceError("exported receipt violates non-authorization invariants")
    if audit_entry.get("send_authorized") is not False or audit_entry.get("audit_is_campaign_authorization") is not False or audit_entry.get("audit_is_human_approval") is not False or audit_entry.get("audit_is_observational_only") is not True:
        raise EffectiveReviewVerificationAuditEvidenceError("exported audit entry violates non-authorization invariants")

    supplied_digest = payload.get("export_sha256")
    unsigned = dict(payload)
    unsigned.pop("export_sha256", None)
    if supplied_digest != _sha256(_canonical_json(unsigned)):
        raise EffectiveReviewVerificationAuditEvidenceError("verification audit evidence digest mismatch")

    receipt_sha256 = _sha256(_canonical_json(receipt))
    if audit_entry.get("receipt_sha256") != receipt_sha256 or audit_entry.get("receipt") != receipt:
        raise EffectiveReviewVerificationAuditEvidenceError("receipt does not match exported audit entry")
    if receipt.get("receipt_id") != payload.get("receipt_id") or receipt.get("evidence_sha256") != payload.get("evidence_sha256"):
        raise EffectiveReviewVerificationAuditEvidenceError("top-level receipt binding mismatch")

    previous: str | None = None
    for expected_sequence, header in enumerate(chain_headers, start=1):
        if not isinstance(header, dict):
            raise EffectiveReviewVerificationAuditEvidenceError("chain header must be an object")
        if header.get("sequence") != expected_sequence:
            raise EffectiveReviewVerificationAuditEvidenceError("verification audit chain sequence mismatch")
        if header.get("previous_entry_hash") != previous:
            raise EffectiveReviewVerificationAuditEvidenceError("verification audit chain predecessor mismatch")
        expected_hash = _sha256(_canonical_json(_entry_hash_payload(header)))
        if header.get("entry_hash") != expected_hash:
            raise EffectiveReviewVerificationAuditEvidenceError("verification audit chain entry hash mismatch")
        previous = expected_hash

    final_header = chain_headers[-1]
    for field in ("audit_entry_id", "sequence", "receipt_id", "evidence_sha256", "receipt_sha256", "previous_entry_hash", "entry_hash"):
        if final_header.get(field) != audit_entry.get(field):
            raise EffectiveReviewVerificationAuditEvidenceError(f"final chain header does not match audit entry: {field}")
    if final_header.get("audit_entry_id") != payload.get("audit_entry_id") or final_header.get("receipt_id") != payload.get("receipt_id") or final_header.get("evidence_sha256") != payload.get("evidence_sha256"):
        raise EffectiveReviewVerificationAuditEvidenceError("top-level evidence binding does not match final chain header")


__all__ = [
    "VERIFICATION_AUDIT_EVIDENCE_SCHEMA_VERSION",
    "EffectiveReviewVerificationAuditEvidenceBundle",
    "EffectiveReviewVerificationAuditEvidenceError",
    "build_effective_review_verification_audit_evidence_bundle",
    "verification_audit_evidence_bundle_to_mapping",
    "verify_effective_review_verification_audit_evidence_bundle",
]
