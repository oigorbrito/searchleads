from dataclasses import replace
from datetime import datetime, timezone

import pytest

from searchleads.domain import CandidateFact, Person, QualificationStatus
from searchleads.qualification import DentalFit, DentalPriority, materialize_lead, qualify_dental_person

NOW = datetime(2026, 8, 28, 21, 15, tzinfo=timezone.utc)


def _qualified_decision():
    person = Person("person-1", "company-1", ("relationship-evidence",))
    role = CandidateFact(
        "role-1",
        person.person_id,
        "professional_role_title",
        "Dentista",
        "Dentista",
        ("role-evidence",),
        "role-provenance",
        observed_at=NOW,
    )
    state = CandidateFact(
        "state-1",
        person.company_id,
        "state",
        "SP",
        "SP",
        ("state-evidence",),
        "state-provenance",
        observed_at=NOW,
    )
    return qualify_dental_person(person, candidate_facts=(role, state))


def test_decision_rejects_unapproved_policy_id_before_lead_materialization():
    decision = _qualified_decision()
    with pytest.raises(ValueError, match="approved dental ICP policy"):
        replace(decision, policy_id="unapproved-policy")


def test_decision_rejects_status_fit_inconsistency():
    decision = _qualified_decision()
    with pytest.raises(ValueError, match="QUALIFIED qualification requires HIGH or MEDIUM fit"):
        replace(decision, fit=DentalFit.LOW, priority=DentalPriority.EXCLUDE)


def test_decision_rejects_priority_inconsistency():
    decision = _qualified_decision()
    with pytest.raises(ValueError, match="priority is inconsistent"):
        replace(decision, priority=DentalPriority.P1)


def test_materialized_lead_can_only_consume_a_validated_decision_contract():
    decision = _qualified_decision()
    lead = materialize_lead(decision, created_at=NOW)
    assert lead.company_id == decision.company_id
    assert lead.qualification_status is QualificationStatus.QUALIFIED
