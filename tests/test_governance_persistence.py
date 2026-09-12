from __future__ import annotations

from datetime import datetime, timezone

import pytest

from searchleads.campaign_preflight import (
    CampaignAuthorizationRecord,
    ComplianceSignoffRecord,
    ProfessionalVerificationRecord,
    ReviewDecision,
    VerificationDecision,
)
from searchleads.governance_persistence import (
    GovernanceDecisionConflictError,
    GovernanceDecisionIntegrityError,
    GovernanceDecisionRepository,
)


NOW = datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc)


def compliance(*, signoff_id: str = "legal:1", campaign_id: str = "campaign:1"):
    return ComplianceSignoffRecord(
        signoff_id=signoff_id,
        reviewer_reference="reviewer:legal",
        policy_id="policy:pilot",
        policy_version="v1",
        jurisdiction="BR",
        channel="email",
        campaign_id=campaign_id,
        decision=ReviewDecision.APPROVED,
        decided_at=NOW,
        authority_evidence_refs=("evidence:legal:1",),
    )


def verification(
    *, verification_id: str = "verification:1", person_id: str = "person:1", council: str = "CRO-RS"
):
    return ProfessionalVerificationRecord(
        verification_id=verification_id,
        person_id=person_id,
        council=council,
        registration_number="12345",
        decision=VerificationDecision.VERIFIED_ACTIVE,
        verified_at=NOW,
        evidence_refs=("evidence:council:1",),
        reviewer_reference="reviewer:professional",
    )


def authorization(*, authorization_id: str = "auth:1", campaign_id: str = "campaign:1"):
    return CampaignAuthorizationRecord(
        authorization_id=authorization_id,
        campaign_id=campaign_id,
        policy_id="policy:pilot",
        policy_version="v1",
        authorizer_reference="owner:campaign",
        authorized_at=NOW,
    )


def test_roundtrip_for_all_governance_record_types(tmp_path):
    path = tmp_path / "governance.sqlite"
    signoff = compliance()
    professional = verification()
    campaign_auth = authorization()

    with GovernanceDecisionRepository(path) as repository:
        assert repository.save_compliance_signoff(signoff) is True
        assert repository.save_professional_verification(professional) is True
        assert repository.save_campaign_authorization(campaign_auth) is True

        assert repository.load_compliance_signoff(signoff.signoff_id) == signoff
        assert repository.load_professional_verification(professional.verification_id) == professional
        assert repository.load_campaign_authorization(campaign_auth.authorization_id) == campaign_auth


def test_identical_replay_is_idempotent_and_conflicting_id_fails_closed(tmp_path):
    with GovernanceDecisionRepository(tmp_path / "governance.sqlite") as repository:
        original = compliance()
        assert repository.save_compliance_signoff(original) is True
        assert repository.save_compliance_signoff(original) is False

        conflicting = ComplianceSignoffRecord(
            signoff_id=original.signoff_id,
            reviewer_reference=original.reviewer_reference,
            policy_id=original.policy_id,
            policy_version=original.policy_version,
            jurisdiction=original.jurisdiction,
            channel=original.channel,
            campaign_id=original.campaign_id,
            decision=ReviewDecision.REJECTED,
            decided_at=original.decided_at,
            authority_evidence_refs=original.authority_evidence_refs,
        )
        with pytest.raises(GovernanceDecisionConflictError):
            repository.save_compliance_signoff(conflicting)


def test_latest_queries_are_scoped_and_do_not_cross_campaign_or_person(tmp_path):
    with GovernanceDecisionRepository(tmp_path / "governance.sqlite") as repository:
        repository.save_compliance_signoff(compliance(signoff_id="legal:campaign-1"))
        repository.save_compliance_signoff(
            compliance(signoff_id="legal:campaign-2", campaign_id="campaign:2")
        )
        repository.save_professional_verification(verification())
        repository.save_professional_verification(
            verification(verification_id="verification:2", person_id="person:2")
        )
        repository.save_campaign_authorization(authorization())
        repository.save_campaign_authorization(
            authorization(authorization_id="auth:2", campaign_id="campaign:2")
        )

        signoff = repository.latest_compliance_signoff(
            campaign_id="campaign:1",
            policy_id="policy:pilot",
            policy_version="v1",
            jurisdiction="BR",
            channel="email",
        )
        professional = repository.latest_professional_verification(
            person_id="person:1", council="CRO-RS"
        )
        campaign_auth = repository.latest_campaign_authorization(
            campaign_id="campaign:1",
            policy_id="policy:pilot",
            policy_version="v1",
        )

        assert signoff is not None and signoff.signoff_id == "legal:campaign-1"
        assert professional is not None and professional.verification_id == "verification:1"
        assert campaign_auth is not None and campaign_auth.authorization_id == "auth:1"


def test_storage_tampering_is_detected_before_deserialization(tmp_path):
    with GovernanceDecisionRepository(tmp_path / "governance.sqlite") as repository:
        record = verification()
        repository.save_professional_verification(record)
        repository._connection.execute(
            """UPDATE governance_decisions
               SET payload_json = ?
               WHERE kind = ? AND decision_id = ?""",
            ("{}", "professional-verification", record.verification_id),
        )
        repository._connection.commit()

        with pytest.raises(GovernanceDecisionIntegrityError):
            repository.load_professional_verification(record.verification_id)
