from __future__ import annotations

from searchleads.domain import Company
from searchleads.normalization import (
    COMPANY_NAME_NORMALIZATION_RULE_V1,
    normalize_companies,
    normalize_company,
    normalize_company_name_value,
)


def test_company_name_normalization_is_minimal_and_deterministic() -> None:
    assert normalize_company_name_value("  NVIDIA\u00a0  CORP  ") == "nvidia corp"
    assert normalize_company_name_value("Acme, Inc.") == "acme, inc."


def test_normalization_does_not_strip_legal_suffixes_or_punctuation() -> None:
    assert normalize_company_name_value("Example Holdings, LLC") == "example holdings, llc"


def test_normalization_record_is_auditable_and_stable() -> None:
    company = Company(id="company:1", legal_name="NVIDIA CORP")

    first = normalize_company(company)
    second = normalize_company(company)

    assert first is not None
    assert first == second
    assert first.input_value == "NVIDIA CORP"
    assert first.normalized_value == "nvidia corp"
    assert first.rule == COMPANY_NAME_NORMALIZATION_RULE_V1
    assert first.id.startswith("normalization:sha256:")


def test_normalization_does_not_mutate_company() -> None:
    company = Company(id="company:1", legal_name="  NVIDIA CORP  ")

    normalization = normalize_company(company)

    assert normalization is not None
    assert company.legal_name == "  NVIDIA CORP  "
    assert normalization.normalized_value == "nvidia corp"


def test_missing_legal_name_produces_no_invented_value() -> None:
    company = Company(id="company:1", legal_name=None)

    assert normalize_company(company) is None


def test_batch_normalization_preserves_input_order_and_skips_missing_names() -> None:
    companies = (
        Company(id="company:1", legal_name="A Corp"),
        Company(id="company:2", legal_name=None),
        Company(id="company:3", legal_name="B Corp"),
    )

    records = normalize_companies(companies)

    assert [record.subject_id for record in records] == ["company:1", "company:3"]


def test_normalization_is_not_entity_resolution() -> None:
    left = Company(id="company:left", legal_name="Acme Inc.")
    right = Company(id="company:right", legal_name="ACME INC.")

    left_normalization = normalize_company(left)
    right_normalization = normalize_company(right)

    assert left_normalization is not None
    assert right_normalization is not None
    assert left_normalization.normalized_value == right_normalization.normalized_value
    assert left.id != right.id
