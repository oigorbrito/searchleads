from searchleads.release_candidate import (
    InternalReleaseCandidateInputs,
    InternalReleaseCandidateReason,
    InternalReleaseCandidateState,
    evaluate_internal_release_candidate,
)


def _inputs(**overrides: object) -> InternalReleaseCandidateInputs:
    values: dict[str, object] = {
        "installation_verified": True,
        "installed_import_verified": True,
        "regression_verified": True,
        "schema_verified": True,
        "recovery_verified": True,
        "evidence_integrity_verified": True,
        "configuration_safe": True,
        "send_boundary_safe": True,
        "documentation_synced": True,
        "ci_verified": True,
        "external_certification_gate": "PARTIAL",
        "commercial_pilot_gate": "BLOCKED_LEGAL",
    }
    values.update(overrides)
    return InternalReleaseCandidateInputs(**values)  # type: ignore[arg-type]


def test_internal_rc_can_be_ready_while_commercial_gate_is_blocked() -> None:
    assessment = evaluate_internal_release_candidate(_inputs())

    assert assessment.state is InternalReleaseCandidateState.READY
    assert assessment.ready is True
    assert assessment.blockers == ()
    assert assessment.external_certification_gate == "PARTIAL"
    assert assessment.commercial_pilot_gate == "BLOCKED_LEGAL"


def test_internal_rc_fails_closed_with_explicit_reason_codes() -> None:
    assessment = evaluate_internal_release_candidate(
        _inputs(
            installation_verified=False,
            recovery_verified=False,
            send_boundary_safe=False,
            ci_verified=False,
        )
    )

    assert assessment.state is InternalReleaseCandidateState.BLOCKED
    assert assessment.ready is False
    assert assessment.blockers == (
        InternalReleaseCandidateReason.INSTALLATION_UNVERIFIED,
        InternalReleaseCandidateReason.RECOVERY_UNVERIFIED,
        InternalReleaseCandidateReason.SEND_BOUNDARY_UNSAFE,
        InternalReleaseCandidateReason.CI_UNVERIFIED,
    )


def test_internal_rc_is_deterministic() -> None:
    inputs = _inputs(documentation_synced=False)

    first = evaluate_internal_release_candidate(inputs)
    second = evaluate_internal_release_candidate(inputs)

    assert first == second
    assert first.blockers == (
        InternalReleaseCandidateReason.DOCUMENTATION_DIVERGENT,
    )


def test_internal_rc_requires_nonblank_external_gate_context() -> None:
    try:
        _inputs(external_certification_gate=" ")
    except ValueError as exc:
        assert str(exc) == "external_certification_gate must not be blank"
    else:
        raise AssertionError("blank external gate must be rejected")
