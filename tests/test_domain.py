import hashlib

import pytest

from searchleads.domain import (
    CandidateFact,
    CanonicalFact,
    Company,
    ContactPoint,
    ContactValidation,
    ContactValidationStatus,
    DomainInvariantError,
    Evidence,
    Lead,
    ReviewCase,
    ReviewReason,
    Source,
)


def test_company_is_not_a_lead() -> None:
    company = Company(id="company-1", legal_name="Acme")
    assert not isinstance(company, Lead)


def test_candidate_fact_requires_evidence_reference() -> None:
    with pytest.raises(DomainInvariantError, match="evidence_id"):
        CandidateFact(
            id="fact-1",
            subject_type="company",
            subject_id="company-1",
            field_name="legal_name",
            value="Acme",
            evidence_id="",
        )


def test_canonical_fact_requires_supporting_candidate_fact() -> None:
    with pytest.raises(DomainInvariantError, match="supporting CandidateFact"):
        CanonicalFact(
            id="canonical-1",
            subject_type="company",
            subject_id="company-1",
            field_name="legal_name",
            value="Acme",
            supporting_candidate_fact_ids=(),
        )


def test_discovered_contact_is_not_implicitly_valid() -> None:
    contact = ContactPoint(
        id="contact-1",
        owner_type="company",
        owner_id="company-1",
        kind="email",
        value="info@example.com",
        evidence_id="evidence-1",
        discovery_rule="official_contact_page",
    )
    validation = ContactValidation(
        id="validation-1",
        contact_point_id=contact.id,
        status=ContactValidationStatus.UNKNOWN,
        rule="BASIC_SYNTAX_ONLY_V1",
    )
    assert validation.status is ContactValidationStatus.UNKNOWN
    assert validation.status is not ContactValidationStatus.VALID


def test_icp_undefined_cannot_create_lead() -> None:
    with pytest.raises(DomainInvariantError, match="ICP is undefined"):
        Lead(
            id="lead-1",
            company_id="company-1",
            qualification_state="ICP_UNDEFINED",
        )


def test_review_case_requires_explicit_review_reason() -> None:
    case = ReviewCase(
        id="review-1",
        reason=ReviewReason.ENTITY_AMBIGUITY,
        subject_type="company",
        subject_id="company-1",
        details={"rule": "domain_exact_only"},
    )
    assert case.reason is ReviewReason.ENTITY_AMBIGUITY


def test_evidence_raw_content_is_immutable_bytes() -> None:
    raw = b"raw payload"
    evidence = Evidence(
        id="evidence-1",
        source_id="source-1",
        raw_content=raw,
        sha256=hashlib.sha256(raw).hexdigest(),
    )
    with pytest.raises(Exception):
        evidence.raw_content = b"changed"  # type: ignore[misc]


def test_evidence_rejects_mutable_text_payload() -> None:
    with pytest.raises(DomainInvariantError, match="must be bytes"):
        Evidence(
            id="evidence-1",
            source_id="source-1",
            raw_content="raw payload",  # type: ignore[arg-type]
            sha256="a" * 64,
        )


def test_evidence_rejects_sha256_that_does_not_match_raw_content() -> None:
    with pytest.raises(DomainInvariantError, match="must match"):
        Evidence(
            id="evidence-1",
            source_id="source-1",
            raw_content=b"raw payload",
            sha256="a" * 64,
        )


def test_source_requires_locator() -> None:
    with pytest.raises(DomainInvariantError, match="locator"):
        Source(id="source-1", name="SEC EDGAR", kind="registry", locator="")
