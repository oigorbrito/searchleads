from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class InternalReleaseCandidateState(StrEnum):
    READY = "READY"
    BLOCKED = "BLOCKED"


class InternalReleaseCandidateReason(StrEnum):
    INSTALLATION_UNVERIFIED = "INSTALLATION_UNVERIFIED"
    IMPORT_UNVERIFIED = "IMPORT_UNVERIFIED"
    REGRESSION_UNVERIFIED = "REGRESSION_UNVERIFIED"
    SCHEMA_UNVERIFIED = "SCHEMA_UNVERIFIED"
    RECOVERY_UNVERIFIED = "RECOVERY_UNVERIFIED"
    EVIDENCE_INTEGRITY_UNVERIFIED = "EVIDENCE_INTEGRITY_UNVERIFIED"
    CONFIGURATION_UNSAFE = "CONFIGURATION_UNSAFE"
    SEND_BOUNDARY_UNSAFE = "SEND_BOUNDARY_UNSAFE"
    DOCUMENTATION_DIVERGENT = "DOCUMENTATION_DIVERGENT"
    CI_UNVERIFIED = "CI_UNVERIFIED"


@dataclass(frozen=True, slots=True)
class InternalReleaseCandidateInputs:
    installation_verified: bool
    installed_import_verified: bool
    regression_verified: bool
    schema_verified: bool
    recovery_verified: bool
    evidence_integrity_verified: bool
    configuration_safe: bool
    send_boundary_safe: bool
    documentation_synced: bool
    ci_verified: bool
    external_certification_gate: str
    commercial_pilot_gate: str

    def __post_init__(self) -> None:
        if not self.external_certification_gate.strip():
            raise ValueError("external_certification_gate must not be blank")
        if not self.commercial_pilot_gate.strip():
            raise ValueError("commercial_pilot_gate must not be blank")


@dataclass(frozen=True, slots=True)
class InternalReleaseCandidateAssessment:
    state: InternalReleaseCandidateState
    ready: bool
    blockers: tuple[InternalReleaseCandidateReason, ...]
    external_certification_gate: str
    commercial_pilot_gate: str

    def __post_init__(self) -> None:
        if self.ready is not (self.state is InternalReleaseCandidateState.READY):
            raise ValueError("ready must agree with state")
        if self.ready and self.blockers:
            raise ValueError("READY assessment cannot contain blockers")
        if not self.ready and not self.blockers:
            raise ValueError("BLOCKED assessment requires blockers")


def evaluate_internal_release_candidate(
    inputs: InternalReleaseCandidateInputs,
) -> InternalReleaseCandidateAssessment:
    """Evaluate engineering release readiness independently from commercial authority.

    External certification and commercial-pilot gates are carried as audit context only.
    They deliberately do not promote or demote the internal engineering gate.
    """

    checks = (
        (
            inputs.installation_verified,
            InternalReleaseCandidateReason.INSTALLATION_UNVERIFIED,
        ),
        (
            inputs.installed_import_verified,
            InternalReleaseCandidateReason.IMPORT_UNVERIFIED,
        ),
        (
            inputs.regression_verified,
            InternalReleaseCandidateReason.REGRESSION_UNVERIFIED,
        ),
        (inputs.schema_verified, InternalReleaseCandidateReason.SCHEMA_UNVERIFIED),
        (inputs.recovery_verified, InternalReleaseCandidateReason.RECOVERY_UNVERIFIED),
        (
            inputs.evidence_integrity_verified,
            InternalReleaseCandidateReason.EVIDENCE_INTEGRITY_UNVERIFIED,
        ),
        (
            inputs.configuration_safe,
            InternalReleaseCandidateReason.CONFIGURATION_UNSAFE,
        ),
        (
            inputs.send_boundary_safe,
            InternalReleaseCandidateReason.SEND_BOUNDARY_UNSAFE,
        ),
        (
            inputs.documentation_synced,
            InternalReleaseCandidateReason.DOCUMENTATION_DIVERGENT,
        ),
        (inputs.ci_verified, InternalReleaseCandidateReason.CI_UNVERIFIED),
    )
    blockers = tuple(reason for passed, reason in checks if not passed)
    state = (
        InternalReleaseCandidateState.READY
        if not blockers
        else InternalReleaseCandidateState.BLOCKED
    )
    return InternalReleaseCandidateAssessment(
        state=state,
        ready=not blockers,
        blockers=blockers,
        external_certification_gate=inputs.external_certification_gate.strip(),
        commercial_pilot_gate=inputs.commercial_pilot_gate.strip(),
    )


__all__ = [
    "InternalReleaseCandidateAssessment",
    "InternalReleaseCandidateInputs",
    "InternalReleaseCandidateReason",
    "InternalReleaseCandidateState",
    "evaluate_internal_release_candidate",
]
