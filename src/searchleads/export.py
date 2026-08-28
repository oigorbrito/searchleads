from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
from dataclasses import asdict, dataclass
from typing import Any

from .domain import (
    CandidateFact,
    CanonicalFact,
    Company,
    ContactPoint,
    ContactValidation,
    Evidence,
    Lead,
    Person,
    ProfessionalRole,
    ReviewCase,
    Source,
)
from .normalization import Normalization
from .qualification import QualificationAssessment


@dataclass(frozen=True, slots=True)
class ExportBundle:
    sources: tuple[Source, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    companies: tuple[Company, ...] = ()
    candidate_facts: tuple[CandidateFact, ...] = ()
    canonical_facts: tuple[CanonicalFact, ...] = ()
    people: tuple[Person, ...] = ()
    professional_roles: tuple[ProfessionalRole, ...] = ()
    contacts: tuple[ContactPoint, ...] = ()
    contact_validations: tuple[ContactValidation, ...] = ()
    normalizations: tuple[Normalization, ...] = ()
    leads: tuple[Lead, ...] = ()
    review_cases: tuple[ReviewCase, ...] = ()
    qualification: tuple[QualificationAssessment, ...] = ()


def export_lossless_json(bundle: ExportBundle) -> str:
    payload = {
        "format": "searchleads-lossless-v1",
        "sources": [_plain(item) for item in bundle.sources],
        "evidence": [_evidence_plain(item) for item in bundle.evidence],
        "companies": [_plain(item) for item in bundle.companies],
        "candidate_facts": [_plain(item) for item in bundle.candidate_facts],
        "canonical_facts": [_plain(item) for item in bundle.canonical_facts],
        "people": [_plain(item) for item in bundle.people],
        "professional_roles": [_plain(item) for item in bundle.professional_roles],
        "contacts": [_plain(item) for item in bundle.contacts],
        "contact_validations": [_plain(item) for item in bundle.contact_validations],
        "normalizations": [_plain(item) for item in bundle.normalizations],
        "leads": [_plain(item) for item in bundle.leads],
        "review_cases": [_plain(item) for item in bundle.review_cases],
        "metadata": {
            "qualification": [_plain(item) for item in bundle.qualification],
        },
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def export_normalized_csv(bundle: ExportBundle) -> dict[str, str]:
    """Return one CSV document per normalized logical table."""

    tables: dict[str, list[dict[str, Any]]] = {
        "sources": [_plain(item) for item in bundle.sources],
        "evidence": [_evidence_csv(item) for item in bundle.evidence],
        "companies": [_plain(item) for item in bundle.companies],
        "candidate_facts": [_jsonify_nested(_plain(item)) for item in bundle.candidate_facts],
        "canonical_facts": [_jsonify_nested(_plain(item)) for item in bundle.canonical_facts],
        "people": [_plain(item) for item in bundle.people],
        "professional_roles": [_plain(item) for item in bundle.professional_roles],
        "contacts": [_plain(item) for item in bundle.contacts],
        "contact_validations": [_plain(item) for item in bundle.contact_validations],
        "normalizations": [_jsonify_nested(_plain(item)) for item in bundle.normalizations],
        "leads": [_plain(item) for item in bundle.leads],
        "review_cases": [_jsonify_nested(_plain(item)) for item in bundle.review_cases],
        "qualification_metadata": [_plain(item) for item in bundle.qualification],
    }
    return {name: _rows_to_csv(rows) for name, rows in tables.items()}


def decode_exported_evidence(item: dict[str, Any]) -> bytes:
    encoding = item.get("raw_content_encoding")
    value = item.get("raw_content_base64")
    expected_sha256 = item.get("sha256")
    if encoding != "base64" or not isinstance(value, str):
        raise ValueError("exported evidence does not contain Base64 raw content")
    if not isinstance(expected_sha256, str):
        raise ValueError("exported evidence does not contain SHA-256")
    raw = base64.b64decode(value.encode("ascii"), validate=True)
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("exported evidence SHA-256 does not match raw content")
    return raw


def _evidence_plain(evidence: Evidence) -> dict[str, Any]:
    return {
        "id": evidence.id,
        "source_id": evidence.source_id,
        "raw_content_encoding": "base64",
        "raw_content_base64": base64.b64encode(evidence.raw_content).decode("ascii"),
        "sha256": evidence.sha256,
        "retrieved_at": evidence.retrieved_at,
    }


def _evidence_csv(evidence: Evidence) -> dict[str, Any]:
    return _evidence_plain(evidence)


def _plain(item: Any) -> dict[str, Any]:
    return _enum_values(asdict(item))


def _enum_values(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _enum_values(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_enum_values(item) for item in value]
    if hasattr(value, "value") and isinstance(getattr(value, "value"), str):
        return value.value
    return value


def _jsonify_nested(row: dict[str, Any]) -> dict[str, Any]:
    converted: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, (dict, list, tuple)):
            converted[key] = json.dumps(
                value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
        else:
            converted[key] = value
    return converted


def _rows_to_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()
