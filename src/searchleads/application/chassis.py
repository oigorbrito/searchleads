from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from types import SimpleNamespace
from typing import Any

try:  # pragma: no cover - imported in tests when FastAPI is installed
    from fastapi import FastAPI, HTTPException
    from fastapi.encoders import jsonable_encoder
except Exception as exc:  # pragma: no cover - fail closed if the optional dep is absent
    FastAPI = None  # type: ignore[assignment]
    class HTTPException(Exception):  # type: ignore[assignment]
        def __init__(self, status_code: int, detail: str) -> None:
            self.status_code = status_code
            self.detail = detail
            super().__init__(detail)

    jsonable_encoder = lambda value: value  # type: ignore[assignment]
    _FASTAPI_IMPORT_ERROR = exc
else:
    _FASTAPI_IMPORT_ERROR = None

from searchleads.domain import (
    CandidateFact,
    CanonicalFact,
    Company,
    Conflict,
    ContactKind,
    ContactPoint,
    ContactStatus,
    DecisionClass,
    Evidence,
    Lead,
    LeadStage,
    PersonCompanyRelationship,
    PersonIdentity,
    ProfessionalRegistration,
    QualificationDecision,
    QualificationStatus,
    RelationshipContactLink,
    Source,
    Statement,
    StatementEvidenceLink,
    utc_now,
)
from searchleads.domain.migration import project_legacy_person
from searchleads.lead_export.canonical import CanonicalLeadExportBundle, export_canonical_json
from searchleads.qualification import materialize_relationship_lead, qualify_dental_relationship
from searchleads.runtime_adapter import (
    AcquisitionRequest,
    AcquisitionRuntimeAdapter,
    AcquisitionResponse,
    ReferenceAcquisitionRuntimeAdapter,
    materialize_evidence,
)
from searchleads.selective_review import build_review_queue, review_qualification
from searchleads.persistence import SQLiteRepository


class _SimpleRoute:
    def __init__(self, path: str) -> None:
        self.path = path


def _candidate_fact(payload: dict[str, Any]) -> CandidateFact:
    return CandidateFact(
        payload["fact_id"],
        payload["subject_id"],
        payload["field_name"],
        payload["raw_value"],
        payload.get("normalized_value"),
        tuple(payload.get("evidence_ids", ())),
        payload["provenance_id"],
        payload.get("confidence"),
        DecisionClass(payload.get("decision_class", DecisionClass.UNKNOWN.value)),
        _dt(payload["observed_at"]) if payload.get("observed_at") is not None else utc_now(),
    )


def _canonical_fact(payload: dict[str, Any]) -> CanonicalFact:
    return CanonicalFact(
        payload["fact_id"],
        payload["subject_id"],
        payload["field_name"],
        payload["value"],
        tuple(payload.get("candidate_fact_ids", ())),
        payload["provenance_id"],
        payload.get("resolution_method", "canonical"),
    )


def _contact(payload: dict[str, Any]) -> ContactPoint:
    return ContactPoint(
        payload["contact_id"],
        payload["owner_id"],
        ContactKind(payload["kind"]),
        payload["value"],
        tuple(payload.get("discovery_evidence_ids", ())),
        ContactStatus(payload.get("status", ContactStatus.DISCOVERED.value)),
        _dt(payload["discovered_at"]) if payload.get("discovered_at") is not None else utc_now(),
        tuple(payload.get("validation_evidence_ids", ())),
        _dt(payload["validated_at"]) if payload.get("validated_at") is not None else None,
    )


def _relationship(payload: dict[str, Any]) -> PersonCompanyRelationship:
    return PersonCompanyRelationship(
        payload["relationship_id"],
        payload["person_id"],
        payload["company_id"],
        tuple(payload.get("evidence_ids", ())),
        payload.get("role_title"),
        payload.get("relationship_type", "UNKNOWN"),
        payload.get("status", "UNKNOWN"),
        _dt(payload["started_at"]) if payload.get("started_at") is not None else None,
        _dt(payload["ended_at"]) if payload.get("ended_at") is not None else None,
    )


def _identity(payload: dict[str, Any]) -> PersonIdentity:
    return PersonIdentity(payload["person_id"])


def _registration(payload: dict[str, Any]) -> ProfessionalRegistration:
    return ProfessionalRegistration(
        payload["registration_id"],
        payload["person_id"],
        payload["authority"],
        payload["number"],
        payload["status"],
        tuple(payload.get("evidence_ids", ())),
    )


def _relationship_link(payload: dict[str, Any]) -> RelationshipContactLink:
    return RelationshipContactLink(
        payload["link_id"],
        payload["relationship_id"],
        payload["contact_id"],
        tuple(payload.get("evidence_ids", ())),
        payload.get("status", "LINKED"),
    )


def _statement(payload: dict[str, Any]) -> Statement:
    return Statement(
        payload["statement_id"],
        payload["subject_id"],
        payload["field_name"],
        payload["value"],
        payload["provenance_id"],
        payload["resolution_method"],
    )


def _statement_link(payload: dict[str, Any]) -> StatementEvidenceLink:
    return StatementEvidenceLink(
        payload["link_id"],
        payload["statement_id"],
        tuple(payload.get("evidence_ids", ())),
    )


def _conflict(payload: dict[str, Any]) -> Conflict:
    return Conflict(
        payload["conflict_id"],
        payload["subject_id"],
        payload["field_name"],
        tuple(payload.get("candidate_fact_ids", ())),
        payload["status"],
    )


def _source(payload: dict[str, Any]) -> Source:
    return Source(
        payload["source_id"],
        payload["source_type"],
        payload["locator"],
        payload.get("name"),
    )


def _evidence(payload: dict[str, Any]) -> Evidence:
    return Evidence(
        payload["evidence_id"],
        payload["source_id"],
        payload["locator"],
        _dt(payload["captured_at"]),
        payload.get("raw_payload"),
        payload.get("content_digest"),
        payload.get("metadata", {}),
    )


def _dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return parsed


def _lead(payload: dict[str, Any]) -> Lead:
    return Lead(
        payload["lead_id"],
        payload["company_id"],
        LeadStage(payload["stage"]),
        QualificationStatus(payload["qualification_status"]),
        tuple(payload.get("qualification_reasons", ())),
        _dt(payload["created_at"]),
    )


def create_app(
    *,
    repository: SQLiteRepository | None = None,
    runtime_adapter: AcquisitionRuntimeAdapter | None = None,
) -> Any:
    if FastAPI is not None:
        app: Any = FastAPI(title="SearchLeads", version="wave-05")
        app.state.repository = repository
        app.state.runtime_adapter = runtime_adapter
    else:
        app = SimpleNamespace(
            state=SimpleNamespace(repository=repository, runtime_adapter=runtime_adapter),
            routes=[],
        )

    def route(method: str, path: str):
        if FastAPI is not None:
            return getattr(app, method)(path)

        app.routes.append(_SimpleRoute(path))

        def decorator(func):
            setattr(app, func.__name__, func)
            return func

        return decorator

    @route("get", "/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @route("get", "/readyz")
    def readyz() -> dict[str, str]:
        ready = app.state.repository is not None and app.state.runtime_adapter is not None
        return {"status": "ready" if ready else "not_ready"}

    @route("post", "/acquisition/request")
    def acquisition_request(payload: dict[str, Any]) -> dict[str, Any]:
        adapter = app.state.runtime_adapter
        if adapter is None:
            raise HTTPException(status_code=503, detail="runtime adapter not configured")
        request = AcquisitionRequest(
            payload["request_id"],
            payload["url"],
            payload["source_id"],
            _dt(payload["requested_at"]),
            payload.get("purpose", "acquisition"),
        )
        response = adapter.acquire(request)
        evidence = materialize_evidence(request, response)
        return jsonable_encoder({
            "request": {
                "request_id": request.request_id,
                "url": request.url,
                "source_id": request.source_id,
                "requested_at": request.requested_at.isoformat(),
                "purpose": request.purpose,
            },
            "response": {
                "request_id": response.request_id,
                "url": response.url,
                "status_code": response.status_code,
                "captured_at": response.captured_at.isoformat(),
                "headers": list(response.headers),
            },
            "evidence": asdict(evidence) if is_dataclass(evidence) else evidence,
        })

    @route("get", "/evidence/{evidence_id}")
    def read_evidence(evidence_id: str) -> dict[str, Any]:
        repository = app.state.repository
        if repository is None:
            raise HTTPException(status_code=503, detail="repository not configured")
        evidence = repository.load(Evidence, evidence_id)
        if evidence is None:
            raise HTTPException(status_code=404, detail="evidence not found")
        return jsonable_encoder(asdict(evidence))

    @route("post", "/qualification/dental")
    def qualify_dental(payload: dict[str, Any]) -> dict[str, Any]:
        identity = _identity(payload["identity"])
        relationship = _relationship(payload["relationship"])
        candidate_facts = tuple(_candidate_fact(item) for item in payload.get("relationship_candidate_facts", ()))
        company_candidate_facts = tuple(_candidate_fact(item) for item in payload.get("company_candidate_facts", ()))
        canonical_facts = tuple(_canonical_fact(item) for item in payload.get("canonical_facts", ()))
        conflicts = tuple(_conflict(item) for item in payload.get("conflicts", ()))
        contacts = tuple(_contact(item) for item in payload.get("contacts", ()))
        links = tuple(_relationship_link(item) for item in payload.get("relationship_contact_links", ()))
        registrations = tuple(_registration(item) for item in payload.get("registrations", ()))
        decision = qualify_dental_relationship(
            identity,
            relationship,
            relationship_candidate_facts=candidate_facts,
            company_candidate_facts=company_candidate_facts,
            canonical_facts=canonical_facts,
            conflicts=conflicts,
            contacts=contacts,
            relationship_contact_links=links,
            registrations=registrations,
            require_validated_contact=bool(payload.get("require_validated_contact", False)),
        )
        lead = materialize_relationship_lead(
            decision,
            created_at=_dt(payload["created_at"]),
            lead_id=payload.get("lead_id"),
        )
        return jsonable_encoder({
            "decision": {
                "decision_id": decision.decision_id,
                "person_id": decision.person_id,
                "company_id": decision.company_id,
                "policy_id": decision.policy_id,
                "qualification_status": decision.qualification_status.value,
                "reasons": list(decision.reasons),
                "evidence_ids": list(decision.evidence_ids),
            },
            "lead": asdict(lead),
        })

    @route("post", "/review/qualification")
    def review_qualification_route(payload: dict[str, Any]) -> dict[str, Any]:
        lead = _lead(payload["lead"])
        item = review_qualification(lead, high_value=bool(payload.get("high_value", True)))
        return {} if item is None else jsonable_encoder(asdict(item))

    @route("post", "/export/canonical")
    def export_canonical(payload: dict[str, Any]) -> dict[str, Any]:
        bundle = CanonicalLeadExportBundle(
            company=Company(payload["company"]["company_id"], tuple(payload["company"].get("candidate_fact_ids", ())), tuple(payload["company"].get("canonical_fact_ids", ())), tuple(payload["company"].get("person_ids", ())), tuple(payload["company"].get("contact_point_ids", ()))),
            lead=_lead(payload["lead"]) if payload.get("lead") else None,
            identities=tuple(_identity(item) for item in payload.get("identities", ())),
            relationships=tuple(_relationship(item) for item in payload.get("relationships", ())),
            registrations=tuple(_registration(item) for item in payload.get("registrations", ())),
            contacts=tuple(_contact(item) for item in payload.get("contacts", ())),
            candidate_facts=tuple(_candidate_fact(item) for item in payload.get("candidate_facts", ())),
            canonical_facts=tuple(_canonical_fact(item) for item in payload.get("canonical_facts", ())),
            conflicts=tuple(_conflict(item) for item in payload.get("conflicts", ())),
            statements=tuple(_statement(item) for item in payload.get("statements", ())),
            statement_evidence_links=tuple(_statement_link(item) for item in payload.get("statement_evidence_links", ())),
            provenances=tuple(),
            sources=tuple(_source(item) for item in payload.get("sources", ())),
            evidence=tuple(_evidence(item) for item in payload.get("evidence", ())),
            review_items=tuple(),
            qualification_decisions=tuple(
                QualificationDecision(
                    item["decision_id"],
                    item["lead_id"],
                    QualificationStatus(item["qualification_status"]),
                    tuple(item.get("reasons", ())),
                    tuple(item.get("evidence_ids", ())),
                    _dt(item["decided_at"]),
                )
                for item in payload.get("qualification_decisions", ())
            ),
        )
        return {"export_json": export_canonical_json(bundle)}

    @route("get", "/capabilities")
    def capabilities() -> dict[str, Any]:
        return {
            "health": True,
            "readiness": app.state.repository is not None and app.state.runtime_adapter is not None,
            "runtime_adapter": type(app.state.runtime_adapter).__name__ if app.state.runtime_adapter else None,
            "repository": type(app.state.repository).__name__ if app.state.repository else None,
        }

    if FastAPI is None:
        app.routes = [
            _SimpleRoute("/healthz"),
            _SimpleRoute("/readyz"),
            _SimpleRoute("/acquisition/request"),
            _SimpleRoute("/evidence/{evidence_id}"),
            _SimpleRoute("/qualification/dental"),
            _SimpleRoute("/review/qualification"),
            _SimpleRoute("/export/canonical"),
            _SimpleRoute("/capabilities"),
        ]
        app.healthz = healthz
        app.readyz = readyz
        app.acquisition_request = acquisition_request
        app.read_evidence = read_evidence
        app.qualify_dental = qualify_dental
        app.review_qualification_route = review_qualification_route
        app.export_canonical = export_canonical
        app.capabilities = capabilities

    return app


__all__ = ["create_app"]
