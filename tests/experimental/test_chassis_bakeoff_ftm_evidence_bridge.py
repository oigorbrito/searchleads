from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

pytest.importorskip("followthemoney")

from followthemoney import Statement

from searchleads.domain import Evidence, Source


@dataclass(frozen=True, slots=True)
class StatementEvidenceLink:
    """Experimental sidecar preserving SearchLeads raw-Evidence identity for FTM statements."""

    statement_id: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.statement_id.strip():
            raise ValueError("statement_id must not be blank")
        if not self.evidence_ids or any(not value.strip() for value in self.evidence_ids):
            raise ValueError("statement evidence link requires evidence_ids")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("statement evidence_ids must not contain duplicates")


def _captured_evidence() -> tuple[Source, Evidence]:
    source = Source(
        source_id="source:official-company-site",
        source_type="official_web",
        locator="https://clinic-a.example.org/",
        name="Clinic A official site",
    )
    evidence = Evidence(
        evidence_id="evidence:clinic-a-team:2026-08-30",
        source_id=source.source_id,
        locator="https://clinic-a.example.org/team",
        captured_at=datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc),
        raw_payload="<html><p>Ana Silva — Finance Director</p></html>",
        content_digest="sha256:fixture",
        metadata={"http_status": 200},
    )
    return source, evidence


def _statement(
    *,
    entity_id: str,
    prop: str,
    value: str,
    source: Source,
    evidence: Evidence,
) -> Statement:
    return Statement(
        entity_id=entity_id,
        schema="Directorship",
        prop=prop,
        value=value,
        dataset=source.source_id,
        origin=evidence.locator,
        first_seen=evidence.captured_at.isoformat(),
    )


def test_one_raw_evidence_can_support_multiple_distinct_ftm_statements() -> None:
    source, evidence = _captured_evidence()
    role = _statement(
        entity_id="directorship:ana:clinic-a",
        prop="role",
        value="Finance Director",
        source=source,
        evidence=evidence,
    )
    organization = _statement(
        entity_id="directorship:ana:clinic-a",
        prop="organization",
        value="company:clinic-a",
        source=source,
        evidence=evidence,
    )

    assert role.id is not None
    assert organization.id is not None
    assert role.id != organization.id

    links = (
        StatementEvidenceLink(role.id, (evidence.evidence_id,)),
        StatementEvidenceLink(organization.id, (evidence.evidence_id,)),
    )

    assert {link.statement_id for link in links} == {role.id, organization.id}
    assert {evidence_id for link in links for evidence_id in link.evidence_ids} == {
        evidence.evidence_id
    }
    assert evidence.raw_payload == "<html><p>Ana Silva — Finance Director</p></html>"

    print("FTM_SEARCHLEADS_EVIDENCE_BRIDGE_ONE_TO_MANY_V1")
    print("raw_evidence_records=1")
    print("ftm_statements=2")
    print("statement_ids_distinct=YES")
    print("same_evidence_supports_multiple_statements=YES")


def test_ftm_statement_id_must_not_be_overloaded_with_searchleads_evidence_id() -> None:
    source, evidence = _captured_evidence()
    role = Statement(
        id=evidence.evidence_id,
        entity_id="directorship:ana:clinic-a",
        schema="Directorship",
        prop="role",
        value="Finance Director",
        dataset=source.source_id,
        origin=evidence.locator,
    )
    organization = Statement(
        id=evidence.evidence_id,
        entity_id="directorship:ana:clinic-a",
        schema="Directorship",
        prop="organization",
        value="company:clinic-a",
        dataset=source.source_id,
        origin=evidence.locator,
    )

    # Statement equality is ID-based. Reusing one Evidence ID for multiple
    # statements collapses semantically distinct facts into the same identity.
    assert role.prop != organization.prop
    assert role.value != organization.value
    assert role.id == organization.id == evidence.evidence_id
    assert role == organization

    print("FTM_STATEMENT_ID_OVERLOAD_NEGATIVE_CONTROL_V1")
    print("reuse_evidence_id_as_statement_id=UNSAFE")
    print("reason=statement_identity_collision")
    print("required=EXPLICIT_STATEMENT_EVIDENCE_LINK")


def test_one_ftm_statement_can_reference_multiple_searchleads_evidence_records() -> None:
    source, first = _captured_evidence()
    second = Evidence(
        evidence_id="evidence:registry-role:2026-08-30",
        source_id=source.source_id,
        locator="https://registry.example.org/ana",
        captured_at=datetime(2026, 8, 30, 13, 0, tzinfo=timezone.utc),
        raw_payload="Ana Silva | Finance Director | Clinic A",
        content_digest="sha256:fixture-2",
    )
    role = _statement(
        entity_id="directorship:ana:clinic-a",
        prop="role",
        value="Finance Director",
        source=source,
        evidence=first,
    )
    assert role.id is not None

    link = StatementEvidenceLink(
        role.id,
        tuple(sorted((first.evidence_id, second.evidence_id))),
    )

    assert len(link.evidence_ids) == 2
    assert set(link.evidence_ids) == {first.evidence_id, second.evidence_id}

    print("FTM_SEARCHLEADS_EVIDENCE_BRIDGE_MANY_TO_ONE_V1")
    print("ftm_statements=1")
    print("supporting_evidence_records=2")
    print("multi_evidence_fact_supported=YES")


def test_bridge_keeps_ftm_lineage_and_searchleads_raw_reprocessing_roles_separate() -> None:
    source, evidence = _captured_evidence()
    role = _statement(
        entity_id="directorship:ana:clinic-a",
        prop="role",
        value="Finance Director",
        source=source,
        evidence=evidence,
    )
    assert role.id is not None
    link = StatementEvidenceLink(role.id, (evidence.evidence_id,))

    assert role.dataset == source.source_id
    assert role.origin == evidence.locator
    assert role.first_seen == evidence.captured_at.isoformat()
    assert link.evidence_ids == (evidence.evidence_id,)
    assert evidence.raw_payload is not None

    print("FTM_SEARCHLEADS_LINEAGE_RESPONSIBILITY_SPLIT_V1")
    print("ftm_dataset_origin_time=YES")
    print("searchleads_stable_evidence_identity=YES")
    print("searchleads_raw_payload_for_reprocessing=YES")
    print("bridge_required_for_lossless_composition=YES")
