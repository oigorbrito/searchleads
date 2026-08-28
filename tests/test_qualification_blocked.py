from __future__ import annotations

from searchleads.qualification import (
    ICP_UNDEFINED,
    NOT_EVALUATED,
    WU11_BLOCKED,
    qualification_without_icp,
    wu11_status,
)


def test_qualification_is_not_evaluated_when_icp_is_undefined() -> None:
    assessment = qualification_without_icp("company:sec:cik:0001045810")

    assert assessment.state == NOT_EVALUATED
    assert assessment.reason == ICP_UNDEFINED


def test_wu11_remains_explicitly_blocked() -> None:
    assert wu11_status() == WU11_BLOCKED == "BLOCKED_ICP_UNDEFINED"


def test_blocked_assessment_is_not_a_lead() -> None:
    assessment = qualification_without_icp("company:sec:cik:0001045810")

    assert assessment.__class__.__name__ == "QualificationAssessment"
    assert not hasattr(assessment, "qualification_score")
    assert not hasattr(assessment, "lead_id")
