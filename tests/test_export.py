from __future__ import annotations

import hashlib
import json

import pytest

from searchleads.domain import CandidateFact, Company, Evidence, Source
from searchleads.export import ExportBundle, decode_exported_evidence, export_lossless_json, export_normalized_csv
from searchleads.qualification import qualification_without_icp


def _bundle() -> ExportBundle:
    raw = b"raw evidence bytes\x00\xff"
    source = Source(
        id="source:test",
        name="Test Source",
        kind="TEST",
        locator="https://example.com/source",
    )
    evidence = Evidence(
        id="evidence:test",
        source_id=source.id,
        raw_content=raw,
        sha256=hashlib.sha256(raw).hexdigest(),
    )
    company = Company(id="company:test", legal_name="Example Corp")
    fact = CandidateFact(
        id="candidate:test",
        subject_type="Company",
        subject_id=company.id,
        field_name="legal_name",
        value="Example Corp",
        evidence_id=evidence.id,
    )
    return ExportBundle(
        sources=(source,),
        evidence=(evidence,),
        companies=(company,),
        candidate_facts=(fact,),
        qualification=(qualification_without_icp(company.id),),
    )


def test_lossless_json_preserves_raw_evidence_byte_for_byte() -> None:
    bundle = _bundle()
    payload = json.loads(export_lossless_json(bundle))

    exported_evidence = payload["evidence"][0]
    restored = decode_exported_evidence(exported_evidence)

    assert restored == bundle.evidence[0].raw_content
    assert hashlib.sha256(restored).hexdigest() == exported_evidence["sha256"]


def test_lossless_decode_rejects_tampered_evidence() -> None:
    payload = json.loads(export_lossless_json(_bundle()))
    exported_evidence = payload["evidence"][0]
    exported_evidence["sha256"] = "0" * 64

    with pytest.raises(ValueError, match="does not match"):
        decode_exported_evidence(exported_evidence)


def test_json_preserves_fact_level_provenance() -> None:
    payload = json.loads(export_lossless_json(_bundle()))

    assert payload["candidate_facts"][0]["evidence_id"] == payload["evidence"][0]["id"]


def test_qualification_is_exported_as_metadata_not_invented_entity() -> None:
    payload = json.loads(export_lossless_json(_bundle()))

    assert payload["metadata"]["qualification"][0] == {
        "company_id": "company:test",
        "reason": "ICP_UNDEFINED",
        "state": "NOT_EVALUATED",
    }
    assert "qualifications" not in payload


def test_csv_export_is_separated_by_normalized_tables() -> None:
    tables = export_normalized_csv(_bundle())

    assert "sources" in tables
    assert "evidence" in tables
    assert "companies" in tables
    assert "candidate_facts" in tables
    assert "qualification_metadata" in tables
    assert "raw_content_base64" in tables["evidence"]
    assert "evidence:test" in tables["candidate_facts"]


def test_empty_normalized_table_exports_as_empty_document() -> None:
    tables = export_normalized_csv(_bundle())

    assert tables["leads"] == ""
