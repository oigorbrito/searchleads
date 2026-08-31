from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from searchleads.domain import Company, Evidence, Lead, PersonCompanyRelationship, PersonIdentity, QualificationStatus, Source
from searchleads.operational import (
    ConfigurationClassification,
    OperationalConfiguration,
    OperationalError,
    OperationalEvent,
    OperationalFailureClass,
    OperationalRuntime,
    ProcessHealth,
    SendReadyInputs,
    SendReadyState,
    build_live_certification_matrix,
    default_compliance_blockers,
    evaluate_send_ready,
)
from searchleads.persistence import SQLiteRepository
from searchleads.runtime_adapter import AcquisitionRequest, ReferenceAcquisitionRuntimeAdapter
from searchleads.sources.brasilapi import HTTPObservation


NOW = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)


def _seed_repository(repository: SQLiteRepository) -> dict[str, object]:
    source = Source("source-1", "website", "https://example.test", "Example")
    evidence = Evidence("evidence-1", source.source_id, "https://example.test/acquire", NOW, "raw evidence", metadata={"purpose": "test"})
    company = Company("company-1")
    identity = PersonIdentity("person-1")
    relationship = PersonCompanyRelationship("relationship-1", identity.person_id, company.company_id, (evidence.evidence_id,), "Dentista", "employment", "ACTIVE", NOW, None)
    lead = Lead("lead-1", company.company_id, qualification_status=QualificationStatus.UNKNOWN, qualification_reasons=("waiting",), created_at=NOW)

    for item in (source, evidence, company, identity, relationship, lead):
        repository.save(item)

    return {
        "source": source,
        "evidence": evidence,
        "company": company,
        "identity": identity,
        "relationship": relationship,
        "lead": lead,
    }


def test_operational_configuration_classifies_and_validates() -> None:
    repo_path = Path(r"C:\Projetos\searchleads\var\searchleads.sqlite")
    backup_path = Path(r"C:\Projetos\searchleads\var\searchleads.backup.sqlite")
    configuration = OperationalConfiguration.from_mapping(
        {
            "SEARCHLEADS_REPOSITORY_PATH": str(repo_path),
            "SEARCHLEADS_SCHEMA_VERSION": "3",
            "SEARCHLEADS_BACKUP_PATH": str(backup_path),
            "SEARCHLEADS_RUNTIME_SOURCE_ID": "src-1",
            "SEARCHLEADS_RUNTIME_SOURCE_URL": "https://example.test",
            "SEARCHLEADS_SECRET_TOKEN": "secret-token",
            "SEARCHLEADS_DEPLOYMENT_MODE": "ci",
            "SEARCHLEADS_LOG_LEVEL": "debug",
        }
    )

    assert configuration.repository_path == repo_path
    assert configuration.backup_path == backup_path
    assert configuration.log_level == "DEBUG"
    assert configuration.classification_map()["SEARCHLEADS_REPOSITORY_PATH"] == (
        ConfigurationClassification.REQUIRED,
        ConfigurationClassification.NON_SECRET,
    )
    assert configuration.classification_map()["SEARCHLEADS_SECRET_TOKEN"] == (
        ConfigurationClassification.OPTIONAL,
        ConfigurationClassification.SECRET,
    )

    with pytest.raises(OperationalError) as missing_repo:
        OperationalConfiguration.from_mapping({"SEARCHLEADS_SCHEMA_VERSION": "3"})
    assert missing_repo.value.failure_class is OperationalFailureClass.CONFIGURATION_ERROR

    with pytest.raises(OperationalError) as relative_path:
        OperationalConfiguration.from_mapping(
            {
                "SEARCHLEADS_REPOSITORY_PATH": "relative.sqlite",
                "SEARCHLEADS_SCHEMA_VERSION": "3",
            }
        )
    assert relative_path.value.failure_class is OperationalFailureClass.CONFIGURATION_ERROR

    with pytest.raises(OperationalError) as bad_url:
        OperationalConfiguration.from_mapping(
            {
                "SEARCHLEADS_REPOSITORY_PATH": str(repo_path),
                "SEARCHLEADS_SCHEMA_VERSION": "3",
                "SEARCHLEADS_RUNTIME_SOURCE_URL": "ftp://example.test",
            }
        )
    assert bad_url.value.failure_class is OperationalFailureClass.CONFIGURATION_ERROR

    with pytest.raises(OperationalError) as unsupported_schema:
        OperationalConfiguration.from_mapping(
            {
                "SEARCHLEADS_REPOSITORY_PATH": str(repo_path),
                "SEARCHLEADS_SCHEMA_VERSION": "999",
            }
        )
    assert unsupported_schema.value.failure_class is OperationalFailureClass.SCHEMA_ERROR


def test_operational_runtime_health_readiness_and_failure_modes(tmp_path: Path) -> None:
    repository_path = tmp_path / "operational.sqlite"
    repository = SQLiteRepository(repository_path)
    seed = _seed_repository(repository)
    source = seed["source"]
    adapter = ReferenceAcquisitionRuntimeAdapter(
        source,
        lambda url: HTTPObservation(url, 200, '{"ok":true}', NOW, {"content-type": "application/json"}),
    )
    configuration = OperationalConfiguration(
        repository_path=repository_path,
        schema_version=repository.schema_version,
        deployment_mode="local",
        log_level="INFO",
    )
    runtime = OperationalRuntime(configuration, repository=repository, runtime_adapter=adapter)

    assert runtime.health_report().status is ProcessHealth.NOT_STARTED
    runtime.startup()
    assert runtime.health_report().status is ProcessHealth.HEALTHY
    assert runtime.readiness_report().ready

    request = AcquisitionRequest("request-1", "https://example.test/acquire", source.source_id, NOW, "acquisition")
    response = adapter.acquire(request)
    assert response.status_code == 200

    runtime.shutdown()
    assert runtime.stopped_at is not None
    repository.close()


def test_operational_runtime_reports_dependency_and_init_failures(tmp_path: Path) -> None:
    repository_path = tmp_path / "failure.sqlite"
    repository = SQLiteRepository(repository_path)
    _seed_repository(repository)
    configuration = OperationalConfiguration(repository_path=repository_path, schema_version=repository.schema_version)

    dependency_failure = OperationalRuntime(configuration, repository=repository, runtime_adapter=None)
    with pytest.raises(OperationalError) as dependency_error:
        dependency_failure.startup()
    assert dependency_error.value.failure_class is OperationalFailureClass.DEPENDENCY_ERROR
    assert dependency_failure.health_report().status is ProcessHealth.BROKEN
    assert not dependency_failure.readiness_report().ready

    init_failure = OperationalRuntime(
        configuration,
        repository=repository,
        runtime_adapter=object(),
        startup_checks=(lambda: (_ for _ in ()).throw(RuntimeError("boom")),),
    )
    with pytest.raises(RuntimeError):
        init_failure.startup()
    assert init_failure.health_report().status is ProcessHealth.BROKEN
    assert not init_failure.readiness_report().ready
    repository.close()


def test_sqlite_backup_restore_round_trip(tmp_path: Path) -> None:
    active_path = tmp_path / "active.sqlite"
    backup_path = tmp_path / "backup.sqlite"

    with SQLiteRepository(active_path) as repository:
        seed = _seed_repository(repository)
        backup_result = repository.backup_to(backup_path)
        assert backup_result.exists()
        original_evidence = repository.load(Evidence, seed["evidence"].evidence_id)
        original_relationship = repository.load(PersonCompanyRelationship, seed["relationship"].relationship_id)
        original_lead = repository.load(Lead, seed["lead"].lead_id)

    active_path.write_bytes(b"corrupted")
    SQLiteRepository.restore_from(backup_path, active_path)

    with SQLiteRepository(active_path) as restored:
        assert restored.load(Evidence, seed["evidence"].evidence_id) == original_evidence
        assert restored.load(PersonCompanyRelationship, seed["relationship"].relationship_id) == original_relationship
        assert restored.load(Lead, seed["lead"].lead_id) == original_lead
        assert restored.raw_evidence_bytes(seed["evidence"].evidence_id) == b"raw evidence"
        assert tuple(restored.iter_evidence()) == (original_evidence,)


def test_send_ready_state_machine_separates_qualification_from_send_ready() -> None:
    discovery_only = evaluate_send_ready(SendReadyInputs())
    qualified_but_pending = evaluate_send_ready(
        SendReadyInputs(
            discovered=True,
            validated=True,
            qualified=True,
            compliance_cleared=False,
            live_certified=False,
        )
    )
    ready = evaluate_send_ready(
        SendReadyInputs(
            discovered=True,
            validated=True,
            qualified=True,
            compliance_cleared=True,
            live_certified=True,
        )
    )
    compliance_blocked = evaluate_send_ready(
        SendReadyInputs(
            discovered=True,
            validated=True,
            qualified=True,
            compliance_cleared=True,
            live_certified=True,
            compliance_blockers=("campaign legal review",),
        )
    )

    assert discovery_only.state is SendReadyState.DISCOVERED
    assert qualified_but_pending.state is SendReadyState.COMPLIANCE_PENDING
    assert not qualified_but_pending.ready
    assert ready.state is SendReadyState.SEND_READY
    assert ready.ready
    assert compliance_blocked.state is SendReadyState.COMPLIANCE_BLOCKED
    assert not compliance_blocked.ready


def test_live_certification_matrix_and_compliance_blockers_are_explicit() -> None:
    matrix = build_live_certification_matrix()
    blockers = default_compliance_blockers()

    assert {row.source for row in matrix} == {
        "BrasilAPI CNPJ v1",
        "SERPRO transparency page",
        "DNS/HTTP contact path",
        "CRO/CFO registration",
    }
    assert all(not row.live_executed for row in matrix)
    assert all(not row.contract_passed for row in matrix)
    assert all(row.blocker for row in matrix)
    assert any(blocker.topic == "campaign legal review" for blocker in blockers)


def test_structured_event_is_redacted_to_scalar_details() -> None:
    event = OperationalEvent(
        "acquisition.request",
        NOW,
        "correlation-1",
        "acquisition",
        "success",
        entity_id="company-1",
        details=(("request_id", "request-1"), ("status_code", "200")),
    )

    payload = event.to_dict()
    assert payload["event"] == "acquisition.request"
    assert payload["details"]["request_id"] == "request-1"
    assert "raw_payload" not in payload["details"]
    assert payload["error_class"] is None
