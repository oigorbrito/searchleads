from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .governance_audit import (
    GovernanceAuditEntry,
    GovernanceAuditIntegrityError,
    GovernanceAuditRepository,
    governance_audit_entry_to_mapping,
)


EVIDENCE_BUNDLE_SCHEMA_VERSION = "governance-evidence-bundle/v1"


class GovernanceEvidenceBundleError(RuntimeError):
    """Raised when a governance evidence bundle cannot be built or verified."""


@dataclass(frozen=True, slots=True)
class GovernanceEvidenceBundle:
    schema_version: str
    audit_id: str
    snapshot: dict[str, Any]
    audit_entry: dict[str, Any]
    chain_headers: tuple[dict[str, Any], ...]
    provenance: tuple[dict[str, Any], ...]
    bundle_sha256: str
    send_authorized: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != EVIDENCE_BUNDLE_SCHEMA_VERSION:
            raise ValueError("unsupported evidence bundle schema version")
        if not self.audit_id.strip():
            raise ValueError("audit_id must not be blank")
        if len(self.bundle_sha256) != 64:
            raise ValueError("bundle_sha256 must be a SHA-256 hex digest")
        if self.send_authorized:
            raise ValueError("governance evidence bundle cannot authorize send")


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _entry_hash(*, audit_id: str, snapshot_sha256: str, previous_entry_hash: str | None) -> str:
    return _sha256_text(
        _canonical_json(
            {
                "audit_id": audit_id,
                "snapshot_sha256": snapshot_sha256,
                "previous_entry_hash": previous_entry_hash,
            }
        )
    )


def _header(entry: GovernanceAuditEntry) -> dict[str, Any]:
    return {
        "sequence": entry.sequence,
        "audit_id": entry.audit_id,
        "snapshot_sha256": entry.snapshot_sha256,
        "previous_entry_hash": entry.previous_entry_hash,
        "entry_hash": entry.entry_hash,
    }


def _extract_provenance(snapshot: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    provenance: list[dict[str, Any]] = []
    gates = snapshot.get("gates", [])
    if not isinstance(gates, list):
        raise GovernanceEvidenceBundleError("snapshot gates must be a list")
    for gate in gates:
        if not isinstance(gate, dict):
            raise GovernanceEvidenceBundleError("snapshot gate must be an object")
        decision_id = gate.get("decision_id")
        if isinstance(decision_id, str) and decision_id:
            provenance.append(
                {
                    "gate_id": gate.get("gate_id"),
                    "status": gate.get("status"),
                    "owner": gate.get("owner"),
                    "decision_id": decision_id,
                    "authority_reference": gate.get("authority_reference"),
                    "evidence_refs": list(gate.get("evidence_refs", [])),
                }
            )
    return tuple(provenance)


def _bundle_unsigned_mapping(
    *,
    audit_id: str,
    snapshot: dict[str, Any],
    audit_entry: dict[str, Any],
    chain_headers: tuple[dict[str, Any], ...],
    provenance: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    return {
        "schema_version": EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "audit_id": audit_id,
        "snapshot": snapshot,
        "audit_entry": audit_entry,
        "chain_headers": list(chain_headers),
        "provenance": list(provenance),
        "send_authorized": False,
        "authority_semantics": {
            "ready_state_is_send_authorization": False,
            "bundle_is_authorization": False,
            "bundle_is_observational_evidence_only": True,
        },
    }


def build_governance_evidence_bundle(
    *,
    audit_repository: GovernanceAuditRepository,
    audit_id: str,
) -> GovernanceEvidenceBundle:
    """Build a deterministic offline-verifiable bundle for one audited snapshot."""
    if not audit_id.strip():
        raise ValueError("audit_id must not be blank")

    entries = audit_repository.list_entries()
    selected_index = next((i for i, entry in enumerate(entries) if entry.audit_id == audit_id), None)
    if selected_index is None:
        raise KeyError(audit_id)
    selected = entries[selected_index]
    snapshot = audit_repository.load_snapshot_mapping(audit_id)
    audit_entry = governance_audit_entry_to_mapping(selected)
    chain_headers = tuple(_header(entry) for entry in entries[: selected_index + 1])
    provenance = _extract_provenance(snapshot)

    unsigned = _bundle_unsigned_mapping(
        audit_id=audit_id,
        snapshot=snapshot,
        audit_entry=audit_entry,
        chain_headers=chain_headers,
        provenance=provenance,
    )
    bundle_sha256 = _sha256_text(_canonical_json(unsigned))
    bundle = GovernanceEvidenceBundle(
        schema_version=EVIDENCE_BUNDLE_SCHEMA_VERSION,
        audit_id=audit_id,
        snapshot=snapshot,
        audit_entry=audit_entry,
        chain_headers=chain_headers,
        provenance=provenance,
        bundle_sha256=bundle_sha256,
        send_authorized=False,
    )
    verify_governance_evidence_bundle(governance_evidence_bundle_to_mapping(bundle))
    return bundle


def governance_evidence_bundle_to_mapping(bundle: GovernanceEvidenceBundle) -> dict[str, Any]:
    payload = _bundle_unsigned_mapping(
        audit_id=bundle.audit_id,
        snapshot=bundle.snapshot,
        audit_entry=bundle.audit_entry,
        chain_headers=bundle.chain_headers,
        provenance=bundle.provenance,
    )
    payload["bundle_sha256"] = bundle.bundle_sha256
    return payload


def verify_governance_evidence_bundle(payload: dict[str, Any]) -> None:
    """Verify bundle digest, snapshot digest, audit entry hash and full header chain."""
    if not isinstance(payload, dict):
        raise GovernanceEvidenceBundleError("bundle must be an object")
    if payload.get("schema_version") != EVIDENCE_BUNDLE_SCHEMA_VERSION:
        raise GovernanceEvidenceBundleError("unsupported evidence bundle schema version")
    if payload.get("send_authorized") is not False:
        raise GovernanceEvidenceBundleError("bundle must not authorize send")

    snapshot = payload.get("snapshot")
    audit_entry = payload.get("audit_entry")
    chain_headers = payload.get("chain_headers")
    provenance = payload.get("provenance")
    if not isinstance(snapshot, dict) or not isinstance(audit_entry, dict):
        raise GovernanceEvidenceBundleError("bundle snapshot and audit_entry must be objects")
    if not isinstance(chain_headers, list) or not chain_headers:
        raise GovernanceEvidenceBundleError("bundle chain_headers must be a non-empty list")
    if not isinstance(provenance, list):
        raise GovernanceEvidenceBundleError("bundle provenance must be a list")
    if snapshot.get("send_authorized") is not False or audit_entry.get("send_authorized") is not False:
        raise GovernanceEvidenceBundleError("nested evidence must not authorize send")

    supplied_bundle_digest = payload.get("bundle_sha256")
    unsigned = dict(payload)
    unsigned.pop("bundle_sha256", None)
    expected_bundle_digest = _sha256_text(_canonical_json(unsigned))
    if supplied_bundle_digest != expected_bundle_digest:
        raise GovernanceEvidenceBundleError("bundle digest mismatch")

    snapshot_digest = _sha256_text(_canonical_json(snapshot))
    if snapshot_digest != audit_entry.get("snapshot_sha256"):
        raise GovernanceEvidenceBundleError("snapshot digest does not match audit entry")

    expected_previous: str | None = None
    for expected_sequence, header in enumerate(chain_headers, start=1):
        if not isinstance(header, dict):
            raise GovernanceEvidenceBundleError("chain header must be an object")
        if header.get("sequence") != expected_sequence:
            raise GovernanceEvidenceBundleError("audit chain sequence mismatch")
        if header.get("previous_entry_hash") != expected_previous:
            raise GovernanceEvidenceBundleError("audit chain predecessor mismatch")
        expected_hash = _entry_hash(
            audit_id=str(header.get("audit_id", "")),
            snapshot_sha256=str(header.get("snapshot_sha256", "")),
            previous_entry_hash=expected_previous,
        )
        if header.get("entry_hash") != expected_hash:
            raise GovernanceEvidenceBundleError("audit chain entry hash mismatch")
        expected_previous = expected_hash

    final_header = chain_headers[-1]
    for field in ("audit_id", "snapshot_sha256", "previous_entry_hash", "entry_hash"):
        if final_header.get(field) != audit_entry.get(field):
            raise GovernanceEvidenceBundleError(f"final chain header does not match audit entry: {field}")
    if final_header.get("audit_id") != payload.get("audit_id"):
        raise GovernanceEvidenceBundleError("bundle audit_id does not match final chain header")

    expected_decision_ids = [
        item.get("decision_id")
        for item in provenance
        if isinstance(item, dict) and isinstance(item.get("decision_id"), str)
    ]
    if expected_decision_ids != audit_entry.get("decision_ids"):
        raise GovernanceEvidenceBundleError("provenance decision IDs do not match audit entry")


__all__ = [
    "EVIDENCE_BUNDLE_SCHEMA_VERSION",
    "GovernanceEvidenceBundle",
    "GovernanceEvidenceBundleError",
    "build_governance_evidence_bundle",
    "governance_evidence_bundle_to_mapping",
    "verify_governance_evidence_bundle",
]
