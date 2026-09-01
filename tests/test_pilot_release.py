from searchleads.campaign_preflight import CampaignPreflightResult, CampaignPreflightState
from searchleads.pilot_release import ActionOwner, PilotReleaseState, evaluate_pilot_release


def test_blocked_release_maps_each_gate_to_human_or_source_owner():
    preflight = CampaignPreflightResult(
        CampaignPreflightState.BLOCKED,
        ("LEGAL-001", "EXT-CFO-001", "AUTH-CAMPAIGN-001", "EXT-BRASILAPI-001"),
    )

    result = evaluate_pilot_release(preflight)

    assert result.state is PilotReleaseState.BLOCKED_EXTERNAL_DECISION
    assert result.authority_chain_valid is False
    assert [(item.gate_id, item.owner) for item in result.required_actions] == [
        ("LEGAL-001", ActionOwner.LEGAL_COMPLIANCE),
        ("EXT-CFO-001", ActionOwner.PROFESSIONAL_REVIEWER),
        ("AUTH-CAMPAIGN-001", ActionOwner.CAMPAIGN_OWNER),
        ("EXT-BRASILAPI-001", ActionOwner.SOURCE_OPERATOR),
    ]


def test_unknown_gate_stays_explicit_and_fail_closed():
    result = evaluate_pilot_release(
        CampaignPreflightResult(CampaignPreflightState.BLOCKED, ("EXT-UNKNOWN-001",))
    )

    assert result.state is PilotReleaseState.BLOCKED_EXTERNAL_DECISION
    assert result.authority_chain_valid is False
    assert result.required_actions[0].gate_id == "EXT-UNKNOWN-001"
    assert result.required_actions[0].owner is ActionOwner.NONE


def test_green_preflight_only_reports_release_authority_state():
    result = evaluate_pilot_release(
        CampaignPreflightResult(CampaignPreflightState.READY_FOR_AUTHORIZED_EXECUTION, ())
    )

    assert result.state is PilotReleaseState.READY_FOR_AUTHORIZED_EXECUTION
    assert result.required_actions == ()
    assert result.authority_chain_valid is True
