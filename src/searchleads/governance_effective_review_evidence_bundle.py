from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .governance_effective_review_audit import (
    EffectiveReviewAuditEntry,
    EffectiveReviewAuditRepository,
    effective_review_audit_entry_to_mapping,
)


EFFECTIVE_REVIEW_EVIDENCE_BUNDLE_SCHEMA_VERSION = "effective-review-evidence-bundle/v1"


class EffectiveReviewEvidenceBundleError(RuntimeError):
    """Raised when an effective-review evidence bundle cannot be built or verified."""


@dataclass(frozen=True, slots=True)
class EffectiveReviewEvidenceBundle:
    schema_version: str
    audit_entry_id: str
    audit_id: str
    bundle_sha256: str
    status: dict[str, Any]
    audit_entry: dict[str, Any]
    chain_headers: tuple[dict[str, Any], ...]
    evidence_sha256: str
    send_authorized: bool = False
    evidence_is_campaign_authorization: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != EFFECTIVE_REVIEW_EVIDENCE_BUNDLE_SCHEMA_VERSION:
            raise ValueError("unsupported effective-review evidence bundle schema version")
        if not self.audit_entry_id.strip() or not self.audit_id.strip():
            raise ValueError("audit_entry_id and audit_id must not be blank")
        if len(self.bundle_sha256) != 64 or len(self.evidence_sha256) != 64:
            raise ValueError("bundle_sha256 and evidence_sha256 must be SHA-256 hex digests")
        if self.send_authorized or self.evidence_is_campaign_authorization:
            raise ValueError("effective-review evidence bundle cannot authorize send or campaign")


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _require_false_flags(payload: dict[str, Any], fields: tuple[str, ...], *, label: str) -> None:
    for field in fields:
        if payload.get(field) is not False:
            raise EffectiveReviewEvidenceBundleError(f"{label} invariant {field} must be false")


def _entry_hash_payload(header: dict[str, Any]) -> dict[str, Any]:
    return {
        "audit_entry_id": header.get("audit_entry_id"),
        "sequence": header.get("sequence"),
        "audit_id": header.get("audit_id"),
        "bundle_sha256": header.get("bundle_sha256"),
        "status_sha256": header.get("status_sha256"),
        "previous_entry_hash": header.get("previous_entry_hash"),
    }


def _header(entry: EffectiveReviewAuditEntry) -> dict[str, Any]:
    return {
        "audit_entry_id": entry.audit_entry_id,
        "sequence": entry.sequence,
        "audit_id": entry.audit_id,
        "bundle_sha256": entry.bundle_sha256,
        "status_sha256": entry.status_sha256,
        "previous_entry_hash": entry.previous_entry_hash,
        "entry_hash": entry.entry_hash,
    }


def _unsigned_mapping(
    *,
    audit_entry_id: str,
    audit_id: str,
    bundle_sha256: str,
    status: dict[str, Any],
    audit_entry: dict[str, Any],
    chain_headers: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    return {
        "schema_version": EFFECTIVE_REVIEW_EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "audit_entry_id": audit_entry_id,
        "audit_id": audit_id,
        "bundle_sha256": bundle_sha256,
        "status": status,
        "audit_entry": audit_entry,
        "chain_headers": list(chain_headers),
        "send_authorized": False,
        "evidence_is_campaign_authorization": False,
        "evidence_is_observational_only": True,
        "changes_auth_campaign_001": False,
        "changes_preflight": False,
        "changes_pilot_release": False,
        "changes_legal_signoff": False,
        "changes_professional_verification": False,
        "changes_source_freshness": False,
    }


def build_effective_review_evidence_bundle(
    *,
    audit_repository: EffectiveReviewAuditRepository,
    audit_entry_id: str,
) -> EffectiveReviewEvidenceBundle:
    """Build deterministic offline-verifiable evidence for one historical effective-review audit entry."""
    if not audit_entry_id.strip():
        raise ValueError("audit_entry_id must not be blank")
    entries = audit_repository.list_entries()
    selected_index = next((index for index, entry in enumerate(entries) if entry.audit_entry_id == audit_entry_id), None)
    if selected_index is None:
        raise KeyError(audit_entry_id)
    selected = entries[selected_index]
    status = dict(selected.status)
    audit_entry = effective_review_audit_entry_to_mapping(selected)
    chain_headers = tuple(_header(entry) for entry in entries[: selected_index + 1])
    unsigned = _unsigned_mapping(
        audit_entry_id=selected.audit_entry_id,
        audit_id=selected.audit_id,
        bundle_sha256=selected.bundle_sha256,
        status=status,
        audit_entry=audit_entry,
        chain_headers=chain_headers,
    )
    evidence_sha256 = _sha256_text(_canonical_json(unsigned))
    bundle = EffectiveReviewEvidenceBundle(
        schema_version=EFFECTIVE_REVIEW_EVIDENCE_BUNDLE_SCHEMA_VERSION,
        audit_entry_id=selected.audit_entry_id,
        audit_id=selected.audit_id,
        bundle_sha256=selected.bundle_sha256,
        status=status,
        audit_entry=audit_entry,
        chain_headers=chain_headers,
        evidence_sha256=evidence_sha256,
    )
    verify_effective_review_evidence_bundle(effective_review_evidence_bundle_to_mapping(bundle))
    return bundle


def effective_review_evidence_bundle_to_mapping(bundle: EffectiveReviewEvidenceBundle) -> dict[str, Any]:
    payload = _unsigned_mapping(
        audit_entry_id=bundle.audit_entry_id,
        audit_id=bundle.audit_id,
        bundle_sha256=bundle.bundle_sha256,
        status=bundle.status,
        audit_entry=bundle.audit_entry,
        chain_headers=bundle.chain_headers,
    )
    payload["evidence_sha256"] = bundle.evidence_sha256
    return payload


def verify_effective_review_evidence_bundle(payload: dict[str, Any]) -> None:
    """Verify the bundle digest, historical status digest, authority invariants, binding, and audit-chain prefix offline."""
    if not isinstance(payload, dict):
        raise EffectiveReviewEvidenceBundleError("evidence bundle must be an object")
    if payload.get("schema_version") != EFFECTIVE_REVIEW_EVIDENCE_BUNDLE_SCHEMA_VERSION:
        raise EffectiveReviewEvidenceBundleError("unsupported effective-review evidence bundle schema version")
    _require_false_flags(
        payload,
        (
            "send_authorized",
            "evidence_is_campaign_authorization",
            "changes_auth_campaign_001",
            "changes_preflight",
            "changes_pilot_release",
            "changes_legal_signoff",
            "changes_professional_verification",
            "changes_source_freshness",
        ),
        label="evidence bundle",
    )
    if payload.get("evidence_is_observational_only") is not True:
        raise EffectiveReviewEvidenceBundleError("evidence bundle must be observational only")

    status = payload.get("status")
    audit_entry = payload.get("audit_entry")
    chain_headers = payload.get("chain_headers")
    if not isinstance(status, dict) or not isinstance(audit_entry, dict):
        raise EffectiveReviewEvidenceBundleError("status and audit_entry must be objects")
    if not isinstance(chain_headers, list) or not chain_headers:
        raise EffectiveReviewEvidenceBundleError("chain_headers must be a non-empty list")
    _require_false_flags(
        status,
        (
            "send_authorized",
            "review_is_campaign_authorization",
            "changes_auth_campaign_001",
            "changes_preflight",
            "changes_pilot_release",
            "changes_legal_signoff",
            "changes_professional_verification",
            "changes_source_freshness",
        ),
        label="historical status",
    )
    if status.get("status_is_observational_only") is not True:
        raise EffectiveReviewEvidenceBundleError("historical status must be observational only")
    _require_false_flags(
        audit_entry,
        ("send_authorized", "audit_is_campaign_authorization"),
        label="audit entry",
    )
    if audit_entry.get("audit_is_observational_only") is not True:
        raise EffectiveReviewEvidenceBundleError("audit entry must be observational only")

    supplied_digest = payload.get("evidence_sha256")
    unsigned = dict(payload)
    unsigned.pop("evidence_sha256", None)
    expected_digest = _sha256_text(_canonical_json(unsigned))
    if supplied_digest != expected_digest:
        raise EffectiveReviewEvidenceBundleError("evidence bundle digest mismatch")

    status_sha256 = _sha256_text(_canonical_json(status))
    if audit_entry.get("status_sha256") != status_sha256:
        raise EffectiveReviewEvidenceBundleError("status digest does not match audit entry")
    if audit_entry.get("status") != status:
        raise EffectiveReviewEvidenceBundleError("audit entry status does not match exported status")
    if status.get("audit_id") != payload.get("audit_id") or status.get("bundle_sha256") != payload.get("bundle_sha256"):
        raise EffectiveReviewEvidenceBundleError("exported status binding mismatch")

    previous: str | None = None
    for expected_sequence, header in enumerate(chain_headers, start=1):
        if not isinstance(header, dict):
            raise EffectiveReviewEvidenceBundleError("chain header must be an object")
        if header.get("sequence") != expected_sequence:
            raise EffectiveReviewEvidenceBundleError("audit chain sequence mismatch")
        if header.get("previous_entry_hash") != previous:
            raise EffectiveReviewEvidenceBundleError("audit chain predecessor mismatch")
        expected_hash = _sha256_text(_canonical_json(_entry_hash_payload(header)))
        if header.get("entry_hash") != expected_hash:
            raise EffectiveReviewEvidenceBundleError("audit chain entry hash mismatch")
        previous = expected_hash

    final_header = chain_headers[-1]
    for field in (
        "audit_entry_id",
        "sequence",
        "audit_id",
        "bundle_sha256",
        "status_sha256",
        "previous_entry_hash",
        "entry_hash",
    ):
        if final_header.get(field) != audit_entry.get(field):
            raise EffectiveReviewEvidenceBundleError(f"final chain header does not match audit entry: {field}")
    if final_header.get("audit_entry_id") != payload.get("audit_entry_id"):
        raise EffectiveReviewEvidenceBundleError("audit_entry_id does not match final chain header")
    if final_header.get("audit_id") != payload.get("audit_id") or final_header.get("bundle_sha256") != payload.get("bundle_sha256"):
        raise EffectiveReviewEvidenceBundleError("top-level evidence binding does not match final chain header")


__all__ = [
    "EFFECTIVE_REVIEW_EVIDENCE_BUNDLE_SCHEMA_VERSION",
    "EffectiveReviewEvidenceBundle",
    "EffectiveReviewEvidenceBundleError",
    "build_effective_review_evidence_bundle",
    "effective_review_evidence_bundle_to_mapping",
    "verify_effective_review_evidence_bundle",
]
