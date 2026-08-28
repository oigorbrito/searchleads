from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from .domain import Company

COMPANY_NAME_NORMALIZATION_RULE_V1 = "COMPANY_NAME_NFKC_CASEFOLD_WS_V1"
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class Normalization:
    id: str
    subject_type: str
    subject_id: str
    field_name: str
    input_value: Any
    normalized_value: Any
    rule: str


def normalize_company_name_value(value: str) -> str:
    """Normalize representation without making an entity-match decision.

    V1 deliberately does not remove legal suffixes, punctuation, or tokens. Those
    transformations can erase distinctions needed later by entity resolution.
    """

    if not isinstance(value, str) or not value.strip():
        raise ValueError("company name must be non-empty text")
    nfkc = unicodedata.normalize("NFKC", value)
    collapsed = _WHITESPACE.sub(" ", nfkc).strip()
    return collapsed.casefold()


def normalize_company(company: Company) -> Normalization | None:
    if company.legal_name is None:
        return None

    normalized = normalize_company_name_value(company.legal_name)
    identity = {
        "subject_type": "Company",
        "subject_id": company.id,
        "field_name": "legal_name",
        "input_value": company.legal_name,
        "normalized_value": normalized,
        "rule": COMPANY_NAME_NORMALIZATION_RULE_V1,
    }
    digest = hashlib.sha256(
        json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    return Normalization(id=f"normalization:sha256:{digest}", **identity)


def normalize_companies(companies: tuple[Company, ...]) -> tuple[Normalization, ...]:
    records: list[Normalization] = []
    for company in companies:
        normalization = normalize_company(company)
        if normalization is not None:
            records.append(normalization)
    return tuple(records)
