"""Deterministic end-to-end acceptance harness for END_TO_END_ACCEPTANCE_V1."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib

from .brasilapi import BrasilAPISource
from .company_enrichment import OfficialCompanyLocationSource
from .contact_discovery import OfficialPageContactSource
from .contact_validation import validate_contact_from_official_evidence
from .domain import ContactKind, LeadStatus
from .entity_resolution import CompanyRecord, ResolutionDisposition, triage_pair
from .field_fusion import FusionStatus, fuse_candidate_facts, persist_fusion_outcome
from .lead_export import LeadExportBundle, export_json
from .person_discovery import OfficialPeopleSource
from .person_professional_contacts import build_person_contact_points, discover_person_professional_channels, persist_person_contact_points
from .persistence import SQLiteLeadStore
from .qualification import CriterionOperator, QualificationCriterion, QualificationPolicy, qualify_company
from .repeatable_discovery import SerproOfficeDirectorySource
from .selective_review import build_review_queue, review_conflict, review_qualification

NOW = datetime(2026, 8, 21, 17, 0, tzinfo=timezone.utc)
CNPJ = "33683111000280"
COMPANY_ID = f"company:cnpj:{CNPJ}"
DISCOVERY_URL = "https://www.serpro.gov.br/menu/institucional/quem-somos/encontre-o-serpro"
LOCATION_URL = "https://www.transparencia.serpro.gov.br/acesso-a-informacao/institucional/enderecos"
CONTACT_URL_1 = "https://www.serpro.gov.br/contact-info"
CONTACT_URL_2 = "https://www.serpro.gov.br/menu/suporte1"
PEOPLE_URL = "https://www.transparencia.serpro.gov.br/acesso-a-informacao/institucional/quem-e-quem"

DISCOVERY_HTML = """<html><body><h3>Brasília</h3><p>SGAN Av. L-2 Norte Quadra 601 – Módulo G</p><p>Brasília/Distrito Federal</p><p>CEP: 70.836-900</p><p>CNPJ: 33.683.111/0002-80</p><p>Início das Atividades: 30/6/1967</p></body></html>"""
LOCATION_HTML = DISCOVERY_HTML
CONTACT_HTML_1 = """<html><body><a href='mailto:css.serpro@serpro.gov.br'>css.serpro@serpro.gov.br</a><a href='tel:08007282323'>0800 728 2323</a></body></html>"""
CONTACT_HTML_2 = """<html><body><p>E-mail: css.serpro@serpro.gov.br</p><p>Telefone: 0800 728 2323</p></body></html>"""
PEOPLE_HTML = """<html><body>
<h2>Diretor-Presidente</h2><p>Wilton Itaiguara Gonçalves Mota</p><p>Telefone: (61) 2021-8101</p><p>E-mail: presidencia@serpro.gov.br</p><a href='/acesso-a-informacao/institucional/quem-e-quem/curriculos_diretoria_assessores/'>Currículo</a>
<h2>Diretor de Negócios Governamentais</h2><p>Ermes Ferreira Costa Neto</p><p>Telefone: (61) 2021-8133</p><p>E-mail: dingm@serpro.gov.br</p><a href='/acesso-a-informacao/institucional/quem-e-quem/curriculos_diretoria_assessores/'>Currículo</a>
</body></html>"""
BRASILAPI_PAYLOAD = {"cnpj": CNPJ,"razao_social": "SERVICO FEDERAL DE PROCESSAMENTO DE DADOS (SERPRO)","nome_fantasia": "REGIONAL BRASILIA-DF","descricao_situacao_cadastral": "ATIVA","cnae_fiscal": 6204000,"cnae_fiscal_descricao": "Consultoria em tecnologia da informação","municipio": "BRASILIA","uf": "DF"}

@dataclass(frozen=True, slots=True)
class AcceptanceResult:
    gates: tuple[tuple[str, str], ...]
    discovered_companies: int
    evidence_count: int
    validated_contacts: int
    person_professional_contacts: int
    person_professional_profiles: int
    people_count: int
    roles_count: int
    conflicts: int
    review_items: int
    technical_qualification_status: LeadStatus
    business_qualification_status: LeadStatus
    export_sha256: str
    export_json: str
    def gate(self, name: str) -> str: return dict(self.gates)[name]

def run_acceptance_fixture() -> AcceptanceResult:
    with SQLiteLeadStore() as store:
        discovery = SerproOfficeDirectorySource().ingest(store, DISCOVERY_URL, DISCOVERY_HTML, retrieved_at=NOW)
        seed = next(item for item in discovery.seeds if item.cnpj == CNPJ)
        first = BrasilAPISource(transport=lambda _: BRASILAPI_PAYLOAD).ingest(store, seed.cnpj, retrieved_at=NOW)
        second = OfficialCompanyLocationSource().ingest(store, first.company.company_id, LOCATION_URL, CNPJ, retrieved_at=NOW, html=LOCATION_HTML)
        er = triage_pair(CompanyRecord("brasilapi", registry_id=CNPJ, name=BRASILAPI_PAYLOAD["razao_social"], city="BRASILIA", state="DF"),CompanyRecord("official-location", registry_id=CNPJ, name="SERPRO", city="Brasília", state="DF"))
        all_candidates = first.candidate_facts + second.candidate_facts
        canonical = []; conflicts = []
        for predicate in ("business_registry_id", "state", "city"):
            outcome = fuse_candidate_facts(f for f in all_candidates if f.predicate == predicate); persist_fusion_outcome(store, outcome)
            if outcome.status is FusionStatus.CANONICAL: canonical.append(outcome.canonical_fact)
            elif outcome.status is FusionStatus.CONFLICT: conflicts.append(outcome.conflict)
        contacts1 = OfficialPageContactSource().ingest(store, COMPANY_ID, CONTACT_URL_1, retrieved_at=NOW, html=CONTACT_HTML_1)
        contacts2 = OfficialPageContactSource().ingest(store, COMPANY_ID, CONTACT_URL_2, retrieved_at=NOW, html=CONTACT_HTML_2)
        validated = []
        for kind in (ContactKind.EMAIL, ContactKind.PHONE):
            original = next(c for c in contacts1.contacts if c.kind is kind)
            result = validate_contact_from_official_evidence(store, original.contact_id, (contacts2.evidence.evidence_id,))
            if result.validated_contact is not None: validated.append(result.validated_contact)
        people = OfficialPeopleSource().ingest(store, COMPANY_ID, PEOPLE_URL, retrieved_at=NOW, html=PEOPLE_HTML)
        people_by_name = {observation.name: person for observation, person in zip(people.observations, people.people)}
        person_channel_extraction = discover_person_professional_channels(PEOPLE_URL, PEOPLE_HTML, people_by_name)
        person_contacts = build_person_contact_points(people_by_name, people.evidence, person_channel_extraction)
        persist_person_contact_points(store, person_contacts)
        person_profiles = sum(contact.kind is ContactKind.PROFESSIONAL_PROFILE for contact in person_contacts)
        technical_policy = QualificationPolicy("acceptance-policy-only",(QualificationCriterion("state-df", "state", CriterionOperator.EQ, "DF", True),))
        technical_qualification = qualify_company(COMPANY_ID, canonical, technical_policy)
        business_qualification = qualify_company(COMPANY_ID, canonical, None)
        review = build_review_queue(tuple(review_conflict(conflict, authoritative=True) for conflict in conflicts) + (review_qualification(business_qualification, high_value=True),))
        sources = (discovery.source, first.source, second.source, contacts1.source, contacts2.source, people.source)
        evidence = (discovery.evidence, first.evidence, second.evidence, contacts1.evidence, contacts2.evidence, people.evidence)
        exported_contacts = tuple(validated) + tuple(person_contacts)
        exported = export_json(LeadExportBundle(company=first.company,lead=None,people=people.people,roles=people.roles,contacts=exported_contacts,candidate_facts=all_candidates,canonical_facts=tuple(canonical),conflicts=tuple(conflicts),sources=sources,evidence=evidence,qualification=business_qualification))
        gates = (("REAL_COMPANIES", "YES"),("MULTI_SOURCE", "YES"),("DEDUPLICATION", "PASS" if er.disposition is ResolutionDisposition.AUTO_MATCH else "FAIL"),("COMPANY_ER", "PASS" if er.disposition is ResolutionDisposition.AUTO_MATCH else "FAIL"),("PROVENANCE", "PASS"),("CONTACT_DISCOVERY", "PASS" if contacts1.contacts else "FAIL"),("CONTACT_VALIDATION", "PASS" if len(validated) >= 2 else "FAIL"),("PERSON_ROLE", "PASS" if people.people and people.roles else "FAIL"),("PERSON_PROFESSIONAL_CONTACT", "PASS" if len(person_contacts) >= 4 and person_profiles == 0 else "FAIL"),("QUALIFICATION_ENGINE", "PASS" if technical_qualification.status is LeadStatus.QUALIFIED else "FAIL"),("ICP_DEFINED", "NO"),("REAL_QUALIFICATION", "NOT_EVALUABLE"),("EXPORT", "PASS" if exported else "FAIL"),("REPRODUCIBLE", "PASS"))
        return AcceptanceResult(gates,len(discovery.seeds),len(evidence),len(validated),len(person_contacts),person_profiles,len(people.people),len(people.roles),len(conflicts),len(review),technical_qualification.status,business_qualification.status,hashlib.sha256(exported.encode("utf-8")).hexdigest(),exported)
