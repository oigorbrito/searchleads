from searchleads.external_governance import (
    GateAuthority,
    GateDecision,
    build_authority_references,
    build_external_gate_requirements,
    build_legal_review_packet,
    critical_path_gate_ids,
)


def test_authority_references_are_explicit_and_currently_observed() -> None:
    refs = {item.reference_id: item for item in build_authority_references()}

    assert set(refs) == {"AUTH-LGPD-001", "AUTH-ANPD-001", "AUTH-CFO-001", "AUTH-SERPRO-001"}
    assert refs["AUTH-LGPD-001"].jurisdiction == "BR"
    assert refs["AUTH-ANPD-001"].publisher.startswith("Autoridade Nacional")
    assert refs["AUTH-CFO-001"].observed_date == "2026-09-01"
    assert "Consulta CNPJ" in refs["AUTH-SERPRO-001"].title


def test_serpro_transparency_path_is_removed_from_minimum_commercial_critical_path() -> None:
    gates = {item.gate_id: item for item in build_external_gate_requirements()}

    serpro = gates["EXT-SERPRO-001"]
    assert serpro.authority is GateAuthority.ENGINEERING
    assert serpro.decision is GateDecision.NOT_REQUIRED
    assert serpro.reason_code == "NOT_ON_MINIMUM_COMMERCIAL_CRITICAL_PATH"
    assert "EXT-SERPRO-001" not in critical_path_gate_ids()


def test_cfo_surface_authority_does_not_self_certify_person_status() -> None:
    gates = {item.gate_id: item for item in build_external_gate_requirements()}

    cfo = gates["EXT-CFO-001"]
    assert cfo.authority is GateAuthority.HUMAN_REVIEW
    assert cfo.decision is GateDecision.REVIEW_REQUIRED
    assert "current consultation result" in cfo.required_evidence
    assert cfo.authority_refs == ("AUTH-CFO-001",)


def test_legal_review_packet_is_fail_closed_and_requires_controller_decision() -> None:
    packet = build_legal_review_packet()

    assert packet.decision is GateDecision.REVIEW_REQUIRED
    assert packet.reason_code == "LEGAL_REVIEW_REQUIRED"
    assert packet.authority_refs == ("AUTH-LGPD-001", "AUTH-ANPD-001")
    assert any("legal basis" in question for question in packet.questions_for_reviewer)
    assert any("retention/deletion" in question for question in packet.questions_for_reviewer)


def test_campaign_authorization_stays_blocked_after_engineering_reclassification() -> None:
    gates = {item.gate_id: item for item in build_external_gate_requirements()}

    authorization = gates["AUTH-CAMPAIGN-001"]
    assert authorization.authority is GateAuthority.CAMPAIGN_OWNER
    assert authorization.decision is GateDecision.BLOCKED
    assert "LEGAL-001" in critical_path_gate_ids()
    assert "EXT-CFO-001" in critical_path_gate_ids()
    assert "AUTH-CAMPAIGN-001" in critical_path_gate_ids()
