from __future__ import annotations

from datetime import datetime, timezone

try:
    from fastapi.testclient import TestClient
except ModuleNotFoundError:  # pragma: no cover - local fallback when FastAPI is absent
    TestClient = None

from searchleads.application import create_app
from searchleads.domain import (
    CandidateFact,
    CanonicalFact,
    Company,
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
    Provenance,
    QualificationDecision,
    QualificationStatus,
    RelationshipContactLink,
    Source,
    Statement,
    StatementEvidenceLink,
)
from searchleads.lead_export import CanonicalLeadExportBundle, export_canonical_json
from searchleads.qualification import qualify_dental_relationship
from searchleads.runtime_adapter import AcquisitionRequest, ReferenceAcquisitionRuntimeAdapter, materialize_evidence
from searchleads.sources.brasilapi import HTTPObservation


NOW = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)


def _title_fact(fact_id: str, subject_id: str, value: str, provenance_id: str, evidence_id: str) -> CandidateFact:
    return CandidateFact(
        fact_id=fact_id,
        subject_id=subject_id,
        field_name="professional_role_title",
        raw_value=value,
        normalized_value=value,
        evidence_ids=(evidence_id,),
        provenance_id=provenance_id,
        confidence=None,
        decision_class=DecisionClass.EVIDENCE_BACKED,
        observed_at=NOW,
    )


def _geo_fact(fact_id: str, subject_id: str, field_name: str, value: str, provenance_id: str, evidence_id: str) -> CandidateFact:
    return CandidateFact(
        fact_id=fact_id,
        subject_id=subject_id,
        field_name=field_name,
        raw_value=value,
        normalized_value=value,
        evidence_ids=(evidence_id,),
        provenance_id=provenance_id,
        confidence=None,
        decision_class=DecisionClass.EVIDENCE_BACKED,
        observed_at=NOW,
    )


def test_canonical_runtime_adapter_materializes_evidence() -> None:
    source = Source("src-1", "website", "https://example.test", "Example")
    adapter = ReferenceAcquisitionRuntimeAdapter(
        source,
        lambda url: HTTPObservation(url, 200, '{"ok":true}', NOW, {"content-type": "application/json"}),
    )
    request = AcquisitionRequest("req-1", "https://example.test/acquire", source.source_id, NOW, "acquisition")

    response = adapter.acquire(request)
    evidence = materialize_evidence(request, response)

    assert response.request_id == request.request_id
    assert response.status_code == 200
    assert evidence.source_id == source.source_id
    assert evidence.raw_payload == '{"ok":true}'


def test_canonical_qualification_respects_relationship_scoped_contacts_and_roles() -> None:
    company_a = Company("company-a")
    company_b = Company("company-b")
    identity = PersonIdentity("person-ana")
    relationship_a = PersonCompanyRelationship("rel-a", identity.person_id, company_a.company_id, ("ev-rel-a",), "Dentista")
    relationship_b = PersonCompanyRelationship("rel-b", identity.person_id, company_b.company_id, ("ev-rel-b",), "Board Member")

    title_fact_a = _title_fact("fact-role-a", relationship_a.relationship_id, "Cirurgião-dentista", "prov-role-a", "ev-role-a")
    geo_fact_a_country = _geo_fact("fact-country-a", company_a.company_id, "country", "BR", "prov-country-a", "ev-country-a")
    geo_fact_a_state = _geo_fact("fact-state-a", company_a.company_id, "state", "SP", "prov-state-a", "ev-state-a")

    contact_a = ContactPoint(
        "contact-a",
        company_a.company_id,
        ContactKind.EMAIL,
        "ana@empresa-a.test",
        ("ev-contact-a",),
        ContactStatus.VALIDATED,
        NOW,
        ("ev-contact-a-validated",),
        NOW,
    )
    contact_link_a = RelationshipContactLink("link-a", relationship_a.relationship_id, contact_a.contact_id, ("ev-contact-link-a",))

    decision_a = qualify_dental_relationship(
        identity,
        relationship_a,
        relationship_candidate_facts=(title_fact_a,),
        company_candidate_facts=(geo_fact_a_country, geo_fact_a_state),
        contacts=(contact_a,),
        relationship_contact_links=(contact_link_a,),
        require_validated_contact=True,
    )
    decision_b = qualify_dental_relationship(
        identity,
        relationship_b,
        relationship_candidate_facts=(title_fact_a,),
        company_candidate_facts=(
            _geo_fact("fact-country-b", company_b.company_id, "country", "BR", "prov-country-b", "ev-country-b"),
            _geo_fact("fact-state-b", company_b.company_id, "state", "RJ", "prov-state-b", "ev-state-b"),
        ),
        contacts=(contact_a,),
        relationship_contact_links=(contact_link_a,),
        require_validated_contact=True,
    )

    assert decision_a.qualification_status is QualificationStatus.QUALIFIED
    assert "company a" not in " ".join(decision_a.reasons).casefold()
    assert decision_b.qualification_status is QualificationStatus.UNKNOWN
    assert decision_b.decision_id != decision_a.decision_id


def test_canonical_export_preserves_identity_relationship_statement_and_decision_layers() -> None:
    company = Company("company-1")
    identity = PersonIdentity("person-1")
    relationship = PersonCompanyRelationship("rel-1", identity.person_id, company.company_id, ("ev-rel-1",), "Dentista")
    registration = ProfessionalRegistration("reg-1", identity.person_id, "CRO-SP", "123", "VERIFIED_ACTIVE", ("ev-reg-1",))
    source = Source("src-1", "website", "https://example.test", "Example")
    evidence = Evidence("ev-1", source.source_id, "https://example.test/people", NOW, "raw payload")
    relationship_evidence = Evidence("ev-rel-1", source.source_id, "https://example.test/people#relationship", NOW, "relationship payload")
    registration_evidence = Evidence("ev-reg-1", source.source_id, "https://example.test/people#registration", NOW, "registration payload")
    provenance = Provenance("prov-1", relationship.relationship_id, "professional_role_title", ("ev-1",), "structured")
    candidate_fact = _title_fact("fact-1", relationship.relationship_id, "Dentista", provenance.provenance_id, evidence.evidence_id)
    canonical_fact = CanonicalFact("canon-1", relationship.relationship_id, "professional_role_title", "Dentista", ("fact-1",), provenance.provenance_id, "fusion")
    statement = Statement("statement-1", relationship.relationship_id, "professional_role_title", "Dentista", provenance.provenance_id, "structured")
    statement_link = StatementEvidenceLink("statement-link-1", statement.statement_id, (evidence.evidence_id,))
    contact = ContactPoint("contact-1", company.company_id, ContactKind.EMAIL, "ana@example.test", (evidence.evidence_id,), ContactStatus.VALIDATED, NOW, (evidence.evidence_id,), NOW)
    lead = Lead("lead-1", company.company_id, LeadStage.REVIEW, QualificationStatus.UNKNOWN, ("review",), NOW)
    decision = QualificationDecision("decision-1", lead.lead_id, QualificationStatus.UNKNOWN, ("review",), (evidence.evidence_id,), NOW)

    bundle = CanonicalLeadExportBundle(
        company=company,
        lead=lead,
        identities=(identity,),
        relationships=(relationship,),
        registrations=(registration,),
        contacts=(contact,),
        candidate_facts=(candidate_fact,),
        canonical_facts=(canonical_fact,),
        statements=(statement,),
        statement_evidence_links=(statement_link,),
        provenances=(provenance,),
        sources=(source,),
        evidence=(evidence, relationship_evidence, registration_evidence),
        qualification_decisions=(decision,),
    )
    payload = export_canonical_json(bundle)

    assert '"schema_version":"lead_export_canonical_v1"' in payload
    assert '"identities"' in payload
    assert '"relationships"' in payload
    assert '"statements"' in payload
    assert '"qualification_decisions"' in payload


def test_application_chassis_surfaces_health_ready_and_operational_endpoints() -> None:
    source = Source("src-1", "website", "https://example.test", "Example")
    adapter = ReferenceAcquisitionRuntimeAdapter(
        source,
        lambda url: HTTPObservation(url, 200, '{"ok":true}', NOW, {"content-type": "application/json"}),
    )
    app = create_app(repository=None, runtime_adapter=adapter)

    if TestClient is None:
        assert app.healthz() == {"status": "ok"}
        assert app.readyz() == {"status": "not_ready"}
        acquisition = app.acquisition_request(
            {
                "request_id": "req-1",
                "url": "https://example.test/acquire",
                "source_id": source.source_id,
                "requested_at": NOW.isoformat(),
                "purpose": "acquisition",
            }
        )
        qualification = app.qualify_dental(
            {
                "identity": {"person_id": "person-1"},
                "relationship": {
                    "relationship_id": "rel-1",
                    "person_id": "person-1",
                    "company_id": "company-1",
                    "evidence_ids": ["ev-rel-1"],
                    "role_title": "Dentista",
                    "relationship_type": "employment",
                    "status": "KNOWN",
                    "started_at": NOW.isoformat(),
                },
                "relationship_candidate_facts": [
                    {
                        "fact_id": "fact-role-1",
                        "subject_id": "rel-1",
                        "field_name": "professional_role_title",
                        "raw_value": "Cirurgião-dentista",
                        "normalized_value": "Cirurgião-dentista",
                        "evidence_ids": ["ev-role-1"],
                        "provenance_id": "prov-role-1",
                        "decision_class": "EVIDENCE_BACKED",
                        "observed_at": NOW.isoformat(),
                    }
                ],
                "company_candidate_facts": [
                    {
                        "fact_id": "fact-country-1",
                        "subject_id": "company-1",
                        "field_name": "country",
                        "raw_value": "BR",
                        "normalized_value": "BR",
                        "evidence_ids": ["ev-country-1"],
                        "provenance_id": "prov-country-1",
                        "decision_class": "EVIDENCE_BACKED",
                        "observed_at": NOW.isoformat(),
                    },
                    {
                        "fact_id": "fact-state-1",
                        "subject_id": "company-1",
                        "field_name": "state",
                        "raw_value": "SP",
                        "normalized_value": "SP",
                        "evidence_ids": ["ev-state-1"],
                        "provenance_id": "prov-state-1",
                        "decision_class": "EVIDENCE_BACKED",
                        "observed_at": NOW.isoformat(),
                    },
                ],
                "contacts": [
                    {
                        "contact_id": "contact-1",
                        "owner_id": "company-1",
                        "kind": "EMAIL",
                        "value": "ana@example.test",
                        "discovery_evidence_ids": ["ev-contact-1"],
                        "status": "VALIDATED",
                        "discovered_at": NOW.isoformat(),
                        "validation_evidence_ids": ["ev-contact-1-valid"],
                        "validated_at": NOW.isoformat(),
                    }
                ],
                "relationship_contact_links": [
                    {
                        "link_id": "link-1",
                        "relationship_id": "rel-1",
                        "contact_id": "contact-1",
                        "evidence_ids": ["ev-link-1"],
                    }
                ],
                "registrations": [],
                "created_at": NOW.isoformat(),
                "lead_id": "lead-1",
            }
        )
    else:
        client = TestClient(app)
        assert client.get("/healthz").json() == {"status": "ok"}
        assert client.get("/readyz").json() == {"status": "not_ready"}
        acquisition = client.post(
            "/acquisition/request",
            json={
                "request_id": "req-1",
                "url": "https://example.test/acquire",
                "source_id": source.source_id,
                "requested_at": NOW.isoformat(),
                "purpose": "acquisition",
            },
        ).json()
        qualification = client.post(
            "/qualification/dental",
            json={
                "identity": {"person_id": "person-1"},
                "relationship": {
                    "relationship_id": "rel-1",
                    "person_id": "person-1",
                    "company_id": "company-1",
                    "evidence_ids": ["ev-rel-1"],
                    "role_title": "Dentista",
                    "relationship_type": "employment",
                    "status": "KNOWN",
                    "started_at": NOW.isoformat(),
                },
                "relationship_candidate_facts": [
                    {
                        "fact_id": "fact-role-1",
                        "subject_id": "rel-1",
                        "field_name": "professional_role_title",
                        "raw_value": "Cirurgião-dentista",
                        "normalized_value": "Cirurgião-dentista",
                        "evidence_ids": ["ev-role-1"],
                        "provenance_id": "prov-role-1",
                        "decision_class": "EVIDENCE_BACKED",
                        "observed_at": NOW.isoformat(),
                    }
                ],
                "company_candidate_facts": [
                    {
                        "fact_id": "fact-country-1",
                        "subject_id": "company-1",
                        "field_name": "country",
                        "raw_value": "BR",
                        "normalized_value": "BR",
                        "evidence_ids": ["ev-country-1"],
                        "provenance_id": "prov-country-1",
                        "decision_class": "EVIDENCE_BACKED",
                        "observed_at": NOW.isoformat(),
                    },
                    {
                        "fact_id": "fact-state-1",
                        "subject_id": "company-1",
                        "field_name": "state",
                        "raw_value": "SP",
                        "normalized_value": "SP",
                        "evidence_ids": ["ev-state-1"],
                        "provenance_id": "prov-state-1",
                        "decision_class": "EVIDENCE_BACKED",
                        "observed_at": NOW.isoformat(),
                    },
                ],
                "contacts": [
                    {
                        "contact_id": "contact-1",
                        "owner_id": "company-1",
                        "kind": "EMAIL",
                        "value": "ana@example.test",
                        "discovery_evidence_ids": ["ev-contact-1"],
                        "status": "VALIDATED",
                        "discovered_at": NOW.isoformat(),
                        "validation_evidence_ids": ["ev-contact-1-valid"],
                        "validated_at": NOW.isoformat(),
                    }
                ],
                "relationship_contact_links": [
                    {
                        "link_id": "link-1",
                        "relationship_id": "rel-1",
                        "contact_id": "contact-1",
                        "evidence_ids": ["ev-link-1"],
                    }
                ],
                "registrations": [],
                "created_at": NOW.isoformat(),
                "lead_id": "lead-1",
            },
        ).json()
    assert acquisition["evidence"]["source_id"] == source.source_id
    assert qualification["decision"]["qualification_status"] == "QUALIFIED"
    assert qualification["lead"]["company_id"] == "company-1"
