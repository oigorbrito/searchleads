from __future__ import annotations

import hashlib
import json

from searchleads.governance_effective_review_audit import EffectiveReviewAuditRepository
from searchleads.governance_effective_review_evidence_bundle import (
    EFFECTIVE_REVIEW_EVIDENCE_BUNDLE_SCHEMA_VERSION,
    EffectiveReviewEvidenceBundleError,
    build_effective_review_evidence_bundle,
    effective_review_evidence_bundle_to_mapping,
    verify_effective_review_evidence_bundle,
)
from searchleads.governance_effective_review_status import (
    EffectiveEvidenceReviewSource,
    EffectiveEvidenceReviewState,
    EffectiveEvidenceReviewStatus,
)
from searchleads.governance_evidence_review import EvidenceReviewDecision


def _status(*, audit_id: str, bundle_sha256: str, decision: str | None = None) -> EffectiveEvidenceReviewStatus:
    effective = EvidenceReviewDecision(decision) if decision is not None else None
    return EffectiveEvidenceReviewStatus(
        audit_id=audit_id,
        bundle_sha256=bundle_sha256,
        state=(
            EffectiveEvidenceReviewState.EFFECTIVE_REVIEW_DECISION
            if effective is not None
            else EffectiveEvidenceReviewState.NO_REVIEW
        ),
        effective_decision=effective,
        decision_source=(
            EffectiveEvidenceReviewSource.CONSOLIDATED_REVIEWS
            if effective is not None
            else EffectiveEvidenceReviewSource.NONE
        ),
        review_ids=("review-1",) if effective is not None else (),
        applicable_resolution_ids=(),
        stale_resolution_ids=(),
        conflict=False,
    )


def _redigest(payload: dict) -> None:
    unsigned = dict(payload)
    unsigned.pop("evidence_sha256", None)
    canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload["evidence_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def test_builds_deterministic_offline_verifiable_bundle_for_historical_entry(tmp_path) -> None:
    db = tmp_path / "audit.sqlite"
    digest = "a" * 64
    with EffectiveReviewAuditRepository(db) as audit:
        audit.append_status(audit_entry_id="effective-audit-1", status=_status(audit_id="audit-1", bundle_sha256=digest))
        audit.append_status(
            audit_entry_id="effective-audit-2",
            status=_status(audit_id="audit-1", bundle_sha256=digest, decision="APPROVED"),
        )
        first = effective_review_evidence_bundle_to_mapping(
            build_effective_review_evidence_bundle(audit_repository=audit, audit_entry_id="effective-audit-2")
        )
        second = effective_review_evidence_bundle_to_mapping(
            build_effective_review_evidence_bundle(audit_repository=audit, audit_entry_id="effective-audit-2")
        )
    assert first == second
    assert first["schema_version"] == EFFECTIVE_REVIEW_EVIDENCE_BUNDLE_SCHEMA_VERSION
    assert first["audit_entry_id"] == "effective-audit-2"
    assert len(first["chain_headers"]) == 2
    assert first["status"]["effective_decision"] == "APPROVED"
    assert first["send_authorized"] is False
    assert first["evidence_is_campaign_authorization"] is False
    verify_effective_review_evidence_bundle(first)


def test_bundle_for_first_entry_contains_only_historical_chain_prefix(tmp_path) -> None:
    db = tmp_path / "audit.sqlite"
    digest = "b" * 64
    with EffectiveReviewAuditRepository(db) as audit:
        audit.append_status(audit_entry_id="entry-1", status=_status(audit_id="audit-2", bundle_sha256=digest))
        audit.append_status(audit_entry_id="entry-2", status=_status(audit_id="audit-2", bundle_sha256=digest, decision="REJECTED"))
        bundle = effective_review_evidence_bundle_to_mapping(
            build_effective_review_evidence_bundle(audit_repository=audit, audit_entry_id="entry-1")
        )
    assert [header["audit_entry_id"] for header in bundle["chain_headers"]] == ["entry-1"]
    verify_effective_review_evidence_bundle(bundle)


def test_tampering_status_chain_or_authority_claim_fails_closed(tmp_path) -> None:
    db = tmp_path / "audit.sqlite"
    digest = "c" * 64
    with EffectiveReviewAuditRepository(db) as audit:
        audit.append_status(audit_entry_id="entry-1", status=_status(audit_id="audit-3", bundle_sha256=digest, decision="MORE_REVIEW_REQUIRED"))
        bundle = effective_review_evidence_bundle_to_mapping(
            build_effective_review_evidence_bundle(audit_repository=audit, audit_entry_id="entry-1")
        )

    tampered_status = dict(bundle)
    tampered_status["status"] = dict(bundle["status"])
    tampered_status["status"]["effective_decision"] = "APPROVED"
    try:
        verify_effective_review_evidence_bundle(tampered_status)
    except EffectiveReviewEvidenceBundleError as exc:
        assert "digest mismatch" in str(exc)
    else:
        raise AssertionError("tampered status must fail")

    tampered_chain = dict(bundle)
    tampered_chain["chain_headers"] = [dict(bundle["chain_headers"][0])]
    tampered_chain["chain_headers"][0]["previous_entry_hash"] = "0" * 64
    try:
        verify_effective_review_evidence_bundle(tampered_chain)
    except EffectiveReviewEvidenceBundleError as exc:
        assert "digest mismatch" in str(exc)
    else:
        raise AssertionError("tampered chain must fail")

    authority = dict(bundle)
    authority["send_authorized"] = True
    try:
        verify_effective_review_evidence_bundle(authority)
    except EffectiveReviewEvidenceBundleError as exc:
        assert "must be false" in str(exc)
    else:
        raise AssertionError("authority claim must fail")


def test_recomputed_digest_cannot_override_negative_scope_invariants(tmp_path) -> None:
    db = tmp_path / "audit.sqlite"
    with EffectiveReviewAuditRepository(db) as audit:
        audit.append_status(audit_entry_id="entry-1", status=_status(audit_id="audit-4", bundle_sha256="d" * 64))
        bundle = effective_review_evidence_bundle_to_mapping(
            build_effective_review_evidence_bundle(audit_repository=audit, audit_entry_id="entry-1")
        )

    bundle["changes_preflight"] = True
    _redigest(bundle)
    try:
        verify_effective_review_evidence_bundle(bundle)
    except EffectiveReviewEvidenceBundleError as exc:
        assert "changes_preflight must be false" in str(exc)
    else:
        raise AssertionError("negative-scope rewrite must fail even with recomputed digest")


def test_unknown_audit_entry_is_rejected(tmp_path) -> None:
    with EffectiveReviewAuditRepository(tmp_path / "audit.sqlite") as audit:
        try:
            build_effective_review_evidence_bundle(audit_repository=audit, audit_entry_id="missing")
        except KeyError as exc:
            assert exc.args == ("missing",)
        else:
            raise AssertionError("missing entry must fail")
