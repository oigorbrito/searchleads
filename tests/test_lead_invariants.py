import pytest

from searchleads.domain import DomainInvariantError, Lead


def test_lead_rejects_icp_undefined_state() -> None:
    with pytest.raises(DomainInvariantError, match="ICP is undefined"):
        Lead(id="lead-1", company_id="company-1", qualification_state="ICP_UNDEFINED")


def test_lead_rejects_not_evaluated_state() -> None:
    with pytest.raises(DomainInvariantError, match="explicit evaluated QUALIFIED"):
        Lead(id="lead-1", company_id="company-1", qualification_state="NOT_EVALUATED")


def test_lead_rejects_arbitrary_state() -> None:
    with pytest.raises(DomainInvariantError, match="explicit evaluated QUALIFIED"):
        Lead(id="lead-1", company_id="company-1", qualification_state="SOME_SCORE")


def test_lead_accepts_only_explicit_qualified_state() -> None:
    lead = Lead(id="lead-1", company_id="company-1", qualification_state="QUALIFIED")
    assert lead.qualification_state == "QUALIFIED"
