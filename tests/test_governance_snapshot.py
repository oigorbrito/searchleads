from datetime import datetime, timedelta, timezone

from searchleads.campaign_preflight import (
    CampaignAuthorizationRecord,
    ComplianceSignoffRecord,
    ProfessionalVerificationRecord,
    ReviewDecision,
    VerificationDecision,
)
from searchleads.governance_persistence import GovernanceDecisionRepository
from searchleads.governance_preflight import CampaignPreflightScope
from searchleads.governance_snapshot import (
    GateSnapshotStatus,
    build_governance_operational_snapshot,
    governance_operational_snapshot_to_mapping,
)


NOW = datetime(2026, 9, 12, 2, 45, tzinfo=timezone.utc)


def _scope(*, brasilapi_fresh: bool = True, professional_required: bool = True) -> CampaignPreflightScope:
    return CampaignPreflightScope(
        campaign_id="camp-1",
        policy_id="policy-1",
        policy_version="v1",
        jurisdiction="BR-RS",
        channel="email",
        brasilapi_fresh=brasilapi_fresh,
        professional_verification_required=professional_required,
        person_id="person-1" if professional_required else None,
        council="CRO-RS" if professional_required else None,
    )


def _seed_valid_chain(repo: GovernanceDecisionRepository) -> None:
    repo.save_compliance_signoff(
        ComplianceSignoffRecord(
            signoff_id="legal-1",
            reviewer_reference="legal-reviewer",
            policy_id="policy-1",
            policy_version="v1",
            jurisdiction="BR-RS",
            channel="email",
            campaign_id="camp-1",
            decision=ReviewDecision.APPROVED,
            decided_at=NOW - timedelta(hours=1),
            expires_at=NOW + timedelta(days=1),
            authority_evidence_refs=("legal-memo:1",),
        )
    )
    repo.save_professional_verification(
        ProfessionalVerificationRecord(
            verification_id="cro-1",
            person_id="person-1",
            council="CRO-RS",
            registration_number="12345",
            decision=VerificationDecision.VERIFIED_ACTIVE,
            verified_at=NOW - timedelta(hours=1),
            evidence_refs=("cro-query:sha256:abc",),
            reviewer_reference="professional-reviewer",
            expires_at=NOW + timedelta(days=1),
        )
    )
    repo.save_campaign_authorization(
        CampaignAuthorizationRecord(
            authorization_id="auth-1",
            campaign_id="camp-1",
            policy_id="policy-1",
            policy_version="v1",
            authorizer_reference="campaign-owner",
            authorized_at=NOW - timedelta(minutes=30),
            valid_until=NOW + timedelta(hours=4),
        )
    )


def test_snapshot_reports_complete_valid_chain_without_send_authority() -> None:
    with GovernanceDecisionRepository() as repo:
        _seed_valid_chain(repo)
        snapshot = build_governance_operational_snapshot(repository=repo, scope=_scope(), now=NOW)

    assert snapshot.blockers == ()
    assert snapshot.preflight_state == "READY_FOR_AUTHORIZED_EXECUTION"
    assert snapshot.pilot_release_state == "READY_FOR_AUTHORIZED_EXECUTION"
    assert all(gate.status is GateSnapshotStatus.SATISFIED for gate in snapshot.gates)
    payload = governance_operational_snapshot_to_mapping(snapshot)
    assert payload["send_authorized"] is False
    assert payload["gates"][1]["decision_id"] == "legal-1"
    assert payload["gates"][1]["authority_reference"] == "legal-reviewer"
    assert payload["gates"][1]["evidence_refs"] == ["legal-memo:1"]


def test_snapshot_explains_all_missing_required_gates() -> None:
    with GovernanceDecisionRepository() as repo:
        snapshot = build_governance_operational_snapshot(
            repository=repo,
            scope=_scope(brasilapi_fresh=False),
            now=NOW,
        )

    assert snapshot.blockers == (
        "EXT-BRASILAPI-001",
        "LEGAL-001",
        "EXT-CFO-001",
        "AUTH-CAMPAIGN-001",
    )
    reasons = {gate.gate_id: gate.reason for gate in snapshot.gates}
    assert "not fresh" in reasons["EXT-BRASILAPI-001"]
    assert "no scoped legal" in reasons["LEGAL-001"]
    assert "no person-specific" in reasons["EXT-CFO-001"]
    assert "no scoped campaign authorization" in reasons["AUTH-CAMPAIGN-001"]


def test_snapshot_preserves_latest_negative_professional_decision_provenance() -> None:
    with GovernanceDecisionRepository() as repo:
        _seed_valid_chain(repo)
        repo.save_professional_verification(
            ProfessionalVerificationRecord(
                verification_id="cro-2",
                person_id="person-1",
                council="CRO-RS",
                registration_number="12345",
                decision=VerificationDecision.CONFLICT,
                verified_at=NOW,
                evidence_refs=("cro-query:sha256:def",),
                reviewer_reference="professional-reviewer-2",
                expires_at=NOW + timedelta(days=1),
            )
        )
        snapshot = build_governance_operational_snapshot(repository=repo, scope=_scope(), now=NOW)

    gate = next(item for item in snapshot.gates if item.gate_id == "EXT-CFO-001")
    assert gate.status is GateSnapshotStatus.BLOCKED
    assert gate.decision_id == "cro-2"
    assert gate.authority_reference == "professional-reviewer-2"
    assert gate.evidence_refs == ("cro-query:sha256:def",)
    assert snapshot.blockers == ("EXT-CFO-001",)


def test_snapshot_marks_professional_gate_not_required_when_policy_does_not_require_it() -> None:
    with GovernanceDecisionRepository() as repo:
        repo.save_compliance_signoff(
            ComplianceSignoffRecord(
                signoff_id="legal-1",
                reviewer_reference="legal-reviewer",
                policy_id="policy-1",
                policy_version="v1",
                jurisdiction="BR-RS",
                channel="email",
                campaign_id="camp-1",
                decision=ReviewDecision.APPROVED,
                decided_at=NOW,
            )
        )
        repo.save_campaign_authorization(
            CampaignAuthorizationRecord(
                authorization_id="auth-1",
                campaign_id="camp-1",
                policy_id="policy-1",
                policy_version="v1",
                authorizer_reference="campaign-owner",
                authorized_at=NOW,
            )
        )
        snapshot = build_governance_operational_snapshot(
            repository=repo,
            scope=_scope(professional_required=False),
            now=NOW,
        )

    gate = next(item for item in snapshot.gates if item.gate_id == "EXT-CFO-001")
    assert gate.status is GateSnapshotStatus.NOT_REQUIRED
    assert snapshot.blockers == ()


def test_snapshot_rejects_naive_now() -> None:
    with GovernanceDecisionRepository() as repo:
        try:
            build_governance_operational_snapshot(
                repository=repo,
                scope=_scope(),
                now=datetime(2026, 9, 12, 2, 45),
            )
        except ValueError as exc:
            assert "timezone-aware" in str(exc)
        else:
            raise AssertionError("expected ValueError")
