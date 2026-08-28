from __future__ import annotations

from searchleads.contact_validation import validate_contact_syntax
from searchleads.domain import ContactPoint, ReviewReason
from searchleads.entity_resolution import (
    CompanyIdentity,
    ResolutionDecision,
    resolve_company_pair,
)
from searchleads.review import review_for_contact_validation, review_for_resolution


def _contact(kind: str, value: str) -> ContactPoint:
    return ContactPoint(
        id=f"contact:{kind}:{value}",
        owner_type="Company",
        owner_id="company:test",
        kind=kind,
        value=value,
        evidence_id="evidence:test",
        discovery_rule="TEST",
    )


def test_unresolved_entity_pair_creates_review() -> None:
    left = CompanyIdentity("left", domain="shared.example")
    right = CompanyIdentity("right", domain="shared.example")
    result = resolve_company_pair(left, right)

    review = review_for_resolution(
        left_company_id=left.company_id,
        right_company_id=right.company_id,
        result=result,
    )

    assert result.decision is ResolutionDecision.UNRESOLVED
    assert review is not None
    assert review.reason is ReviewReason.ENTITY_AMBIGUITY


def test_possibly_different_entity_pair_creates_review() -> None:
    left = CompanyIdentity("left", normalized_name="acme", city="Boston")
    right = CompanyIdentity("right", normalized_name="acme", city="Austin")
    result = resolve_company_pair(left, right)

    assert review_for_resolution(
        left_company_id="left", right_company_id="right", result=result
    ) is not None


def test_deterministic_match_and_no_match_do_not_create_review() -> None:
    match = resolve_company_pair(
        CompanyIdentity("a", external_ids={"sec_cik": "1"}),
        CompanyIdentity("b", external_ids={"sec_cik": "1"}),
    )
    no_match = resolve_company_pair(
        CompanyIdentity("c", external_ids={"sec_cik": "1"}),
        CompanyIdentity("d", external_ids={"sec_cik": "2"}),
    )

    assert review_for_resolution(left_company_id="a", right_company_id="b", result=match) is None
    assert review_for_resolution(left_company_id="c", right_company_id="d", result=no_match) is None


def test_unknown_contact_validation_creates_review() -> None:
    validation = validate_contact_syntax(_contact("EMAIL", "info@example.com"))

    review = review_for_contact_validation(validation)

    assert review is not None
    assert review.reason is ReviewReason.CONTACT_VALIDATION_UNKNOWN


def test_invalid_contact_does_not_require_human_review() -> None:
    validation = validate_contact_syntax(_contact("EMAIL", "bad"))

    assert review_for_contact_validation(validation) is None
