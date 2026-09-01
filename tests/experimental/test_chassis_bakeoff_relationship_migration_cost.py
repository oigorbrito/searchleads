from __future__ import annotations

from pathlib import Path
import re


SRC = Path("src/searchleads")


def _hits(pattern: str) -> dict[str, int]:
    regex = re.compile(pattern)
    result: dict[str, int] = {}
    for path in sorted(SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        count = len(regex.findall(text))
        if count:
            result[path.as_posix()] = count
    return result


def test_measure_embedded_person_company_coupling_surface() -> None:
    person_company_access = _hits(r"\bperson\.company_id\b")
    person_construction = _hits(r"\bPerson\s*\(")
    company_person_snapshot = _hits(r"\bperson_ids\b")
    relationship_evidence = _hits(r"\brelationship_evidence_ids\b")

    assert person_construction
    assert company_person_snapshot
    assert relationship_evidence

    print("PERSON_RELATIONSHIP_MIGRATION_CODE_SURFACE_V1")
    print(f"person_company_id_access_occurrences={sum(person_company_access.values())}")
    print(f"person_company_id_access_files={len(person_company_access)}")
    print(f"person_constructor_occurrences={sum(person_construction.values())}")
    print(f"person_constructor_files={len(person_construction)}")
    print(f"company_person_ids_occurrences={sum(company_person_snapshot.values())}")
    print(f"company_person_ids_files={len(company_person_snapshot)}")
    print(f"relationship_evidence_occurrences={sum(relationship_evidence.values())}")
    print(f"relationship_evidence_files={len(relationship_evidence)}")
    print("files_with_person_company_id=" + ",".join(sorted(person_company_access)))
    print("files_with_person_construction=" + ",".join(sorted(person_construction)))
    print("files_with_company_person_ids=" + ",".join(sorted(company_person_snapshot)))


def test_generic_domain_record_table_shape_does_not_encode_person_company_columns() -> None:
    persistence = (SRC / "persistence" / "sqlite.py").read_text(encoding="utf-8")
    create_domain_records = re.search(
        r"CREATE TABLE IF NOT EXISTS domain_records \((.*?)\);",
        persistence,
        re.DOTALL,
    )
    assert create_domain_records is not None
    ddl = create_domain_records.group(1)
    assert "record_type" in ddl
    assert "record_id" in ddl
    assert "payload_json" in ddl
    assert "company_id" not in ddl
    assert "person_id" not in ddl

    print("GENERIC_DOMAIN_RECORD_SHAPE_V1")
    print("physical_company_id_column=NO")
    print("physical_person_id_column=NO")
    print("new_relation_record_requires_new_physical_table=NO_FOR_GENERIC_DOMAIN_RECORD_STORAGE")
    print("record_codec_registry_change_required=YES")
    print("semantic_reference_rule_change_required=YES")
