"""Deterministic clean-stack end-to-end acceptance harness."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from searchleads.contact_discovery import CompanyPageContactSource, HTTPPageObservation
from searchleads.contact_validation import ContactValidationDisposition, validate_contact_publication
from searchleads.domain import ContactKind, Lead, QualificationStatus
from searchleads.entity_resolution import CompanyRecord, ResolutionDisposition, triage_pair
from searchleads.field_fusion import FusionStatus, fuse_candidate_facts, persist_fusion_outcome
from searchleads.gap_automation import AutomationInputs, GapRequirements, plan_gap_actions
from searchleads.lead_export import LeadExportBundle, export_csv, export_json
from searchleads.normalization import NormalizationStatus, normalize_candidate_fact
from searchleads.persistence import SQLiteRepository
from searchleads.person_discovery import CompanyPeopleSource, ROLE_FIELD
from searchleads.repeatable_discovery import DIRECTORY_URL, acquire_discovered_seeds, ingest_serpro_office_directory
from searchleads.selective_review import build_review_queue, review_conflict, review_qualification
from searchleads.sources import BrasilAPISource, HTTPObservation


@dataclass(frozen=True, slots=True)
class AcceptanceRun:
    export_json: str
    export_csv: str
    export_sha256: str
    discovered_seeds: int
    structured_snapshots: int
    evidence_records: int
    candidate_facts: int
    canonical_facts: int
    conflicts: int
    company_contacts: int
    validated_company_contacts: int
    people: int
    role_facts: int
    review_items: int
    gap_count: int
    ready_actions: int
    blocked_actions: int
    er_disposition: str
    persistence_replay_ok: bool


@dataclass(frozen=True, slots=True)
class EndToEndAcceptanceResult:
    first: AcceptanceRun
    second: AcceptanceRun
    reproducible: bool
    technical_data_path: str
    live_network_smoke: str
    commercial_qualification: str
    multi_source_company_enrichment: str


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("acceptance timestamps must be timezone-aware")
    return parsed


def _unique(records: tuple[Any, ...], attr: str) -> tuple[Any, ...]:
    by_id: dict[str, Any] = {}
    for record in records:
        by_id.setdefault(getattr(record, attr), record)
    return tuple(by_id[key] for key in sorted(by_id))


def _run_once(fixture: Mapping[str, Any]) -> AcceptanceRun:
    times = fixture["timestamps"]
    with SQLiteRepository(":memory:") as repository:
        discovery = ingest_serpro_office_directory(
            repository,
            DIRECTORY_URL,
            fixture["directory_html"],
            _dt(times["directory"]),
        )
        if len(discovery.seeds) != 1:
            raise AssertionError(f"acceptance requires exactly one discovered seed, got {len(discovery.seeds)}")
        seed = discovery.seeds[0]

        payloads = tuple(fixture["brasilapi_payloads"])
        capture_times = (_dt(times["brasilapi_1"]), _dt(times["brasilapi_2"]))
        call_index = 0

        def brasil_transport(url: str) -> HTTPObservation:
            nonlocal call_index
            if call_index >= len(payloads):
                raise AssertionError("unexpected extra BrasilAPI transport call")
            payload = json.dumps(payloads[call_index], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            observation = HTTPObservation(url, 200, payload, capture_times[call_index], {"content-type": "application/json"})
            call_index += 1
            return observation

        brasil = BrasilAPISource(brasil_transport)
        first_acquisition = acquire_discovered_seeds(discovery, lambda cnpj: brasil.ingest(cnpj, repository))
        if first_acquisition.attempted != 1 or first_acquisition.succeeded != 1:
            raise AssertionError("discovered seed did not pass the structured acquisition boundary")
        structured_1 = first_acquisition.items[0].result
        if structured_1 is None:
            raise AssertionError("structured acquisition unexpectedly returned no result")
        structured_2 = brasil.ingest(seed.cnpj, repository)

        legal_1 = next(f for f in structured_1.candidate_facts if f.field_name == "legal_name")
        legal_2 = next(f for f in structured_2.candidate_facts if f.field_name == "legal_name")
        norm_legal_1 = normalize_candidate_fact(legal_1)
        norm_legal_2 = normalize_candidate_fact(legal_2)
        if norm_legal_1.status not in {NormalizationStatus.NORMALIZED, NormalizationStatus.UNCHANGED}:
            raise AssertionError("first legal_name normalization failed")
        if norm_legal_2.status not in {NormalizationStatus.NORMALIZED, NormalizationStatus.UNCHANGED}:
            raise AssertionError("second legal_name normalization failed")
        legal_fusion = fuse_candidate_facts((norm_legal_1.normalized_fact, norm_legal_2.normalized_fact))
        if legal_fusion.status is not FusionStatus.CANONICAL:
            raise AssertionError("equal normalized legal_name snapshots must fuse canonically")
        persist_fusion_outcome(repository, legal_fusion)

        trade_1 = next(f for f in structured_1.candidate_facts if f.field_name == "trade_name")
        trade_2 = next(f for f in structured_2.candidate_facts if f.field_name == "trade_name")
        norm_trade_1 = normalize_candidate_fact(trade_1)
        norm_trade_2 = normalize_candidate_fact(trade_2)
        trade_fusion = fuse_candidate_facts((norm_trade_1.normalized_fact, norm_trade_2.normalized_fact))
        if trade_fusion.status is not FusionStatus.CONFLICT or trade_fusion.conflict is None:
            raise AssertionError("disagreeing trade_name snapshots must remain an explicit conflict")
        persist_fusion_outcome(repository, trade_fusion)

        structured_name = str(legal_fusion.canonical_fact.value)
        er = triage_pair(
            CompanyRecord("directory-observation", name=seed.label, registry_namespace="br:cnpj", registry_id=seed.cnpj, city=seed.city, state=seed.state_text),
            CompanyRecord("brasilapi-observation", name=structured_name, registry_namespace="br:cnpj", registry_id=seed.cnpj,
                          city=str(next(f.raw_value for f in structured_2.candidate_facts if f.field_name == "city")),
                          state=str(next(f.raw_value for f in structured_2.candidate_facts if f.field_name == "state"))),
        )
        if er.disposition is not ResolutionDisposition.AUTO_MATCH:
            raise AssertionError(f"same namespaced CNPJ must AUTO_MATCH, got {er.disposition}")

        contact_pages = fixture["contact_pages"]
        page_times = {
            contact_pages[0]["url"]: _dt(times["contact_1"]),
            contact_pages[1]["url"]: _dt(times["contact_2"]),
        }
        page_html = {item["url"]: item["html"] for item in contact_pages}

        def contact_transport(url: str) -> HTTPPageObservation:
            return HTTPPageObservation(url, 200, page_html[url], page_times[url], {"content-type": "text/html"})

        contact_source = CompanyPageContactSource(contact_transport)
        contact_1 = contact_source.ingest(structured_1.company.company_id, contact_pages[0]["url"], repository)
        contact_2 = contact_source.ingest(structured_1.company.company_id, contact_pages[1]["url"], repository)
        email_1 = next(c for c in contact_1.contacts if c.kind is ContactKind.EMAIL and c.value.casefold() == fixture["company_email"].casefold())
        email_2 = next(c for c in contact_2.contacts if c.kind is ContactKind.EMAIL and c.value.casefold() == fixture["company_email"].casefold())
        validation = validate_contact_publication(repository, email_1.contact_id, (email_2.contact_id,))
        if validation.disposition is not ContactValidationDisposition.VALIDATED or validation.validated_contact is None:
            raise AssertionError("two independent official-page observations must validate publication association")

        people_url = fixture["people_page"]["url"]
        people_observation = HTTPPageObservation(
            people_url, 200, fixture["people_page"]["html"], _dt(times["people"]), {"content-type": "text/html"}
        )
        people_result = CompanyPeopleSource(lambda url: people_observation).ingest(structured_1.company.company_id, people_url, repository)
        role_facts = tuple(f for f in people_result.candidate_facts if f.field_name == ROLE_FIELD)
        if not people_result.people or not role_facts:
            raise AssertionError("people page did not produce an evidence-backed Person + role fact")

        lead = Lead(
            fixture["lead_id"], structured_1.company.company_id,
            qualification_status=QualificationStatus.UNKNOWN,
            qualification_reasons=("ICP/policy is not defined",),
            created_at=_dt(times["lead"]),
        )
        repository.save(lead)
        conflict_review = review_conflict(
            trade_fusion.conflict,
            high_impact=True,
            evidence_ids=tuple(sorted((structured_1.evidence.evidence_id, structured_2.evidence.evidence_id))),
        )
        qualification_review = review_qualification(lead, high_value=True)
        review_queue = build_review_queue((conflict_review, qualification_review))

        canonical_facts = (legal_fusion.canonical_fact,)
        all_company_contacts = contact_1.contacts + contact_2.contacts + (validation.validated_contact,)
        all_contacts = all_company_contacts + people_result.contacts
        all_candidates = structured_1.candidate_facts + structured_2.candidate_facts + people_result.candidate_facts
        all_provenances = structured_1.provenances + structured_2.provenances + (legal_fusion.provenance,) + people_result.provenances
        all_sources = _unique((discovery.source, structured_1.source, structured_2.source, contact_1.source, contact_2.source, people_result.source), "source_id")
        all_evidence = _unique((discovery.evidence, structured_1.evidence, structured_2.evidence, contact_1.evidence, contact_2.evidence, people_result.evidence), "evidence_id")

        plan = plan_gap_actions(
            structured_1.company.company_id,
            GapRequirements(
                company_fields=("legal_name", "state", "employee_count"),
                require_validated_company_contact=True,
                require_person_role=True,
                require_qualification=True,
            ),
            inputs=AutomationInputs(known_cnpj=seed.cnpj),
            canonical_facts=canonical_facts,
            contacts=all_contacts,
            people=people_result.people,
            candidate_facts=all_candidates,
            lead=lead,
        )

        bundle = LeadExportBundle(
            company=structured_1.company,
            lead=lead,
            people=people_result.people,
            contacts=all_contacts,
            candidate_facts=all_candidates,
            canonical_facts=canonical_facts,
            conflicts=(trade_fusion.conflict,),
            provenances=all_provenances,
            sources=all_sources,
            evidence=all_evidence,
            review_items=review_queue.items,
        )
        json_export = export_json(bundle)
        csv_export = export_csv(bundle)
        digest = hashlib.sha256(json_export.encode("utf-8")).hexdigest()

        replayed = tuple(repository.iter_evidence())
        persistence_replay_ok = (
            len(replayed) == len(all_evidence)
            and all(repository.raw_evidence_bytes(item.evidence_id) == (item.raw_payload.encode("utf-8") if item.raw_payload is not None else None) for item in all_evidence)
        )
        if not persistence_replay_ok:
            raise AssertionError("persisted Evidence did not replay byte-for-byte")

        return AcceptanceRun(
            export_json=json_export,
            export_csv=csv_export,
            export_sha256=digest,
            discovered_seeds=len(discovery.seeds),
            structured_snapshots=2,
            evidence_records=len(all_evidence),
            candidate_facts=len(all_candidates),
            canonical_facts=len(canonical_facts),
            conflicts=1,
            company_contacts=len(all_company_contacts),
            validated_company_contacts=sum(c.status.value == "VALIDATED" for c in all_company_contacts),
            people=len(people_result.people),
            role_facts=len(role_facts),
            review_items=len(review_queue.items),
            gap_count=len(plan.gaps),
            ready_actions=len(plan.ready_actions),
            blocked_actions=len(plan.blocked_actions),
            er_disposition=er.disposition.value,
            persistence_replay_ok=persistence_replay_ok,
        )


def run_end_to_end_acceptance(fixture: Mapping[str, Any]) -> EndToEndAcceptanceResult:
    first = _run_once(fixture)
    second = _run_once(fixture)
    reproducible = first.export_json == second.export_json and first.export_sha256 == second.export_sha256
    technical_pass = (
        reproducible
        and first.discovered_seeds == 1
        and first.structured_snapshots == 2
        and first.er_disposition == ResolutionDisposition.AUTO_MATCH.value
        and first.canonical_facts >= 1
        and first.conflicts >= 1
        and first.validated_company_contacts >= 1
        and first.people >= 1
        and first.role_facts >= 1
        and first.persistence_replay_ok
        and first.ready_actions >= 1
        and first.blocked_actions >= 1
    )
    return EndToEndAcceptanceResult(
        first=first,
        second=second,
        reproducible=reproducible,
        technical_data_path="PASS" if technical_pass else "FAIL",
        live_network_smoke="NOT_EXECUTED_BY_DETERMINISTIC_ACCEPTANCE",
        commercial_qualification="BLOCKED_BY_UNDEFINED_ICP",
        multi_source_company_enrichment="NOT_IMPLEMENTED_IN_CLEAN_STACK",
    )


def load_fixture(path: str | Path) -> Mapping[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


__all__ = ["AcceptanceRun", "EndToEndAcceptanceResult", "load_fixture", "run_end_to_end_acceptance"]
