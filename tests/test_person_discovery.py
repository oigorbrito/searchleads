from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from searchleads.contact_discovery import HTTPPageObservation
from searchleads.domain import CandidateFact, Company, ContactKind, ContactPoint, ContactStatus, DecisionClass, Evidence, Person, Provenance
from searchleads.persistence import SQLiteRepository
from searchleads.person_discovery import (
    NAME_FIELD,
    ROLE_FIELD,
    CompanyPeopleSource,
    PersonAcquisitionError,
    PersonContactObservation,
    PersonPageResponseError,
    PersonRoleObservation,
    discover_person_roles_from_html,
)

NOW = datetime(2026, 8, 25, 2, 20, tzinfo=timezone.utc)
LATER = datetime(2026, 8, 25, 2, 21, tzinfo=timezone.utc)
URL = "https://www.example.com/about/leadership"

SERPRO_SEVEN = [
    ("Diretor-Presidente - DP", "Wilton Itaiguara Gonçalves Mota"),
    ("Diretor de Negócios Governamentais - DINGM", "Ermes Ferreira Costa Neto"),
    ("Diretor de Infraestrutura - DIINF", "Wallyson Lemos dos Reis Oliveira"),
    ("Diretor de Administração e Finanças - DIRAF", "Osmar Quirino da Silva"),
    ("Diretor de Pessoas e Assuntos Jurídicos - DIPEJ", "Alexandre Brandão Henriques Maimoni"),
    ("Diretora de Negócios Econômico-Fazendários - DINEF", "Ariadne de Santa Teresa Lopes Fonseca"),
    ("Diretor de Novos Negócios e Inteligência de TI - DINIT", "André Picoli Agatte"),
]


def page_for(pairs=SERPRO_SEVEN):
    return "<html><body>" + "".join(f"<h3>{title}</h3><p>{name}</p>" for title,name in pairs) + "</body></html>"


def test_current_serpro_seven_name_title_pairs_are_extractable() -> None:
    found = discover_person_roles_from_html(URL, page_for())
    assert [(item.title,item.name) for item in found] == SERPRO_SEVEN
    assert [item.ordinal for item in found] == list(range(1,8))


def test_diretoria_heading_is_not_misread_as_role() -> None:
    html = '<h2>Diretoria Executiva</h2><p>Empresa Pública</p><h3>Diretor de Infraestrutura</h3><p>João da Silva</p>'
    found = discover_person_roles_from_html(URL, html)
    assert [(x.title,x.name) for x in found] == [("Diretor de Infraestrutura","João da Silva")]


def test_name_without_role_does_not_create_observation() -> None:
    assert discover_person_roles_from_html(URL, '<p>Maria da Silva</p>') == ()


def test_role_without_plausible_name_does_not_create_observation() -> None:
    assert discover_person_roles_from_html(URL, '<h3>Diretor de Infraestrutura</h3><p>Telefone: 111111111</p>') == ()


@pytest.mark.parametrize("candidate", ["empresa pública", "Contato Institucional", "123 Pessoa", "email@example.com"])
def test_non_human_candidate_after_role_is_not_person(candidate: str) -> None:
    html = f'<h3>Diretor de Infraestrutura</h3><p>{candidate}</p>'
    assert discover_person_roles_from_html(URL, html) == ()


def test_all_caps_human_name_is_supported() -> None:
    found = discover_person_roles_from_html(URL, '<h3>CEO</h3><p>MARIA DE SOUZA</p>')
    assert found[0].name == "MARIA DE SOUZA"


def test_hidden_role_and_name_are_ignored() -> None:
    html = '<template><h3>CEO</h3><p>Fake Person</p></template><h3>CEO</h3><p>Real Person</p>'
    found = discover_person_roles_from_html(URL, html)
    assert len(found) == 1 and found[0].name == "Real Person"


def test_local_person_contacts_include_email_phone_and_linkedin_profile() -> None:
    html = '''
    <h3>CEO</h3><p>Maria da Silva</p>
    <a href="mailto:maria@example.com">email</a>
    <a href="tel:+5511999990000">phone</a>
    <a href="https://linkedin.com/in/maria-silva">profile</a>
    '''
    item = discover_person_roles_from_html(URL, html)[0]
    assert set(item.contacts) == {
        PersonContactObservation(ContactKind.EMAIL,"maria@example.com"),
        PersonContactObservation(ContactKind.PHONE,"+5511999990000"),
        PersonContactObservation(ContactKind.PROFESSIONAL_PROFILE,"https://linkedin.com/in/maria-silva"),
    }


def test_visible_labeled_person_contacts_are_supported() -> None:
    html = '<h3>CTO</h3><p>João da Silva</p><p>E-mail: joao@example.com</p><p>Telefone: (61) 2021-8000</p>'
    contacts = discover_person_roles_from_html(URL, html)[0].contacts
    assert PersonContactObservation(ContactKind.EMAIL,"joao@example.com") in contacts
    assert PersonContactObservation(ContactKind.PHONE,"(61) 2021-8000") in contacts


def test_company_linkedin_and_shared_curriculum_are_not_person_profiles() -> None:
    html = '''<h3>CEO</h3><p>Maria da Silva</p>
    <a href="https://linkedin.com/company/acme">company</a>
    <a href="https://example.com/curriculo">Currículo</a>'''
    assert not any(x.kind is ContactKind.PROFESSIONAL_PROFILE for x in discover_person_roles_from_html(URL, html)[0].contacts)


def test_person_profile_requires_exact_in_slug_path() -> None:
    html = '''<h3>CEO</h3><p>Maria da Silva</p>
    <a href="https://linkedin.com/in/maria/posts">posts</a>
    <a href="ftp://linkedin.com/in/maria">ftp</a>'''
    assert not any(x.kind is ContactKind.PROFESSIONAL_PROFILE for x in discover_person_roles_from_html(URL, html)[0].contacts)


def test_contacts_stop_before_next_role_block() -> None:
    html = '''
    <h3>CEO</h3><p>Maria da Silva</p>
    <h3>CTO</h3><p>João da Silva</p><a href="mailto:joao@example.com">mail</a>
    '''
    found = discover_person_roles_from_html(URL, html)
    assert found[0].contacts == ()
    assert found[1].contacts == (PersonContactObservation(ContactKind.EMAIL,"joao@example.com"),)


def test_contact_window_is_bounded() -> None:
    filler = ''.join(f'<span>Detalhe {i}</span>' for i in range(20))
    html = f'<h3>CEO</h3><p>Maria da Silva</p>{filler}<a href="mailto:far@example.com">far</a>'
    item = discover_person_roles_from_html(URL, html, contact_window_events=4)[0]
    assert item.contacts == ()


def test_invalid_contact_window_rejected() -> None:
    with pytest.raises(ValueError): discover_person_roles_from_html(URL, page_for(), contact_window_events=0)


@pytest.mark.parametrize("url", ["example.com/x", "ftp://example.com/x", "http://"])
def test_invalid_people_page_url_rejected(url: str) -> None:
    with pytest.raises(ValueError): discover_person_roles_from_html(url, page_for())


@pytest.mark.parametrize("url", [
    "https://user:password@example.com/leadership",
    "http://user@example.com/leadership",
])
def test_people_page_url_with_credentials_is_rejected(url: str) -> None:
    with pytest.raises(ValueError, match="embedded credentials"):
        discover_person_roles_from_html(url, page_for())


def test_html_must_be_text() -> None:
    with pytest.raises(TypeError): discover_person_roles_from_html(URL, b"x")  # type: ignore[arg-type]


def test_observation_validates_ordinal_and_required_text() -> None:
    with pytest.raises(ValueError): PersonRoleObservation(0,"Maria da Silva","CEO")
    with pytest.raises(ValueError): PersonRoleObservation(1," ","CEO")
    with pytest.raises(ValueError): PersonRoleObservation(1,"Maria da Silva"," ")


def test_missing_company_rejected_before_transport() -> None:
    called=False
    def transport(url):
        nonlocal called; called=True
        return HTTPPageObservation(url,200,page_for(),NOW)
    with SQLiteRepository() as repo:
        with pytest.raises(ValueError,match="company must already be persisted"):
            CompanyPeopleSource(transport).ingest("missing",URL,repo)
    assert called is False


def test_ingestion_creates_person_relationship_name_role_facts_and_contacts() -> None:
    html = '<h3>CEO</h3><p>Maria da Silva</p><a href="mailto:maria@example.com">mail</a>'
    with SQLiteRepository() as repo:
        company=Company("company-1"); repo.save(company)
        result=CompanyPeopleSource(lambda url:HTTPPageObservation(url,200,html,NOW)).ingest(company.company_id,URL,repo)
        assert len(result.people)==1 and len(result.candidate_facts)==2 and len(result.provenances)==2 and len(result.contacts)==1
        person=result.people[0]
        assert person.company_id==company.company_id
        assert person.relationship_evidence_ids==(result.evidence.evidence_id,)
        assert person.candidate_fact_ids==tuple(f.fact_id for f in result.candidate_facts)
        assert person.contact_point_ids==(result.contacts[0].contact_id,)
        assert repo.load(Person,person.person_id)==person
        fields={f.field_name:f for f in result.candidate_facts}
        assert fields[NAME_FIELD].raw_value=="Maria da Silva"
        assert fields[ROLE_FIELD].raw_value=="CEO"
        assert all(f.decision_class is DecisionClass.EVIDENCE_BACKED for f in fields.values())
        for fact in result.candidate_facts:
            assert fact.evidence_ids==(result.evidence.evidence_id,)
            assert repo.load(CandidateFact,fact.fact_id)==fact
            assert repo.load(Provenance,fact.provenance_id).evidence_ids==(result.evidence.evidence_id,)
        contact=result.contacts[0]
        assert contact.owner_id==person.person_id and contact.status is ContactStatus.DISCOVERED
        assert contact.validation_evidence_ids==() and contact.validated_at is None
        assert repo.load(ContactPoint,contact.contact_id)==contact


def test_same_name_different_roles_in_same_snapshot_are_distinct_person_observations() -> None:
    html = '<h3>CEO</h3><p>Alex Silva</p><h3>CTO</h3><p>Alex Silva</p>'
    with SQLiteRepository() as repo:
        repo.save(Company("company-1"))
        result=CompanyPeopleSource(lambda url:HTTPPageObservation(url,200,html,NOW)).ingest("company-1",URL,repo)
    assert len(result.people)==2
    assert result.people[0].person_id != result.people[1].person_id


def test_repeated_same_snapshot_is_idempotent() -> None:
    obs=HTTPPageObservation(URL,200,'<h3>CEO</h3><p>Maria da Silva</p>',NOW)
    with SQLiteRepository() as repo:
        repo.save(Company("company-1")); source=CompanyPeopleSource(lambda url:obs)
        first=source.ingest("company-1",URL,repo); second=source.ingest("company-1",URL,repo)
        assert first.people==second.people and first.candidate_facts==second.candidate_facts
        assert first.evidence==second.evidence
        assert first.evidence_was_new is True and second.evidence_was_new is False


def test_changed_snapshot_creates_distinct_person_observation_identity() -> None:
    observations=iter([
        HTTPPageObservation(URL,200,'<h3>CEO</h3><p>Maria da Silva</p>',NOW),
        HTTPPageObservation(URL,200,'<h3>CEO</h3><p>Maria da Silva</p><p>Atualizado</p>',LATER),
    ])
    with SQLiteRepository() as repo:
        repo.save(Company("company-1")); source=CompanyPeopleSource(lambda url:next(observations))
        first=source.ingest("company-1",URL,repo); second=source.ingest("company-1",URL,repo)
    assert first.evidence.evidence_id != second.evidence.evidence_id
    assert first.people[0].person_id != second.people[0].person_id


def test_transport_url_mismatch_rejected() -> None:
    with SQLiteRepository() as repo:
        repo.save(Company("company-1"))
        source=CompanyPeopleSource(lambda url:HTTPPageObservation("https://other.example/x",200,page_for(),NOW))
        with pytest.raises(PersonAcquisitionError): source.ingest("company-1",URL,repo)


@pytest.mark.parametrize("status",[403,404,429,500])
def test_non_200_people_page_body_persisted_before_error(status: int) -> None:
    with SQLiteRepository() as repo:
        repo.save(Company("company-1"))
        source=CompanyPeopleSource(lambda url:HTTPPageObservation(url,status,"error-body",NOW))
        with pytest.raises(PersonPageResponseError) as exc: source.ingest("company-1",URL,repo)
        evidence=repo.load(Evidence,exc.value.evidence_id)
        assert evidence.raw_payload=="error-body" and evidence.metadata["http_status"]==status


def test_content_address_collision_guard(monkeypatch) -> None:
    obs=HTTPPageObservation(URL,200,page_for(),NOW)
    with SQLiteRepository() as repo:
        company=Company("company-1"); repo.save(company); real_load=repo.load
        fake=Evidence("x","s","https://wrong.example",NOW,page_for())
        def load(t,i):
            if t is Company: return real_load(t,i)
            if t is Evidence: return fake
            return real_load(t,i)
        monkeypatch.setattr(repo,"load",load)
        with pytest.raises(PersonAcquisitionError,match="collision"):
            CompanyPeopleSource(lambda url:obs).ingest("company-1",URL,repo)

def test_name_candidate_with_only_punctuation_word_is_rejected() -> None:
    assert discover_person_roles_from_html(URL, '<h3>CEO</h3><p>Maria --</p>') == ()


def test_name_candidate_with_non_letter_symbol_word_is_rejected() -> None:
    assert discover_person_roles_from_html(URL, '<h3>CEO</h3><p>Maria _</p>') == ()


@pytest.mark.parametrize("mailto", [
    "a@invalid",
    "a%20b@example.com",
    "a@@example.com",
    ("a" * 65) + "@example.com",
    "x@" + ("a" * 64) + ".example",
])
def test_invalid_person_mailto_is_ignored(mailto: str) -> None:
    html = f'<h3>CEO</h3><p>Maria da Silva</p><a href="mailto:{mailto}">mail</a>'
    assert not any(x.kind is ContactKind.EMAIL for x in discover_person_roles_from_html(URL, html)[0].contacts)


def test_overall_person_email_length_is_rejected() -> None:
    domain = "a" * 249 + ".com"
    html = f'<h3>CEO</h3><p>Maria da Silva</p><a href="mailto:x@{domain}">mail</a>'
    assert not any(x.kind is ContactKind.EMAIL for x in discover_person_roles_from_html(URL, html)[0].contacts)


def test_malformed_linkedin_person_profile_is_ignored() -> None:
    html = '<h3>CEO</h3><p>Maria da Silva</p><a href="https://[broken">x</a>'
    assert not any(x.kind is ContactKind.PROFESSIONAL_PROFILE for x in discover_person_roles_from_html(URL, html)[0].contacts)


def test_href_between_role_and_name_does_not_block_name_search() -> None:
    html = '<h3>CEO</h3><a href="/bio">bio</a><p>Maria da Silva</p>'
    found = discover_person_roles_from_html(URL, html)
    assert len(found) == 1 and found[0].name == "Maria da Silva"


def test_new_role_before_name_stops_previous_role_search() -> None:
    html = '<h3>CEO</h3><h3>CTO</h3><p>Maria da Silva</p>'
    found = discover_person_roles_from_html(URL, html)
    assert [(x.title,x.name) for x in found] == [("CTO","Maria da Silva")]


def test_name_search_stops_after_five_non_name_text_events() -> None:
    filler = ''.join(f'<p>item {i}</p>' for i in range(5))
    html = f'<h3>CEO</h3>{filler}<p>Maria da Silva</p>'
    assert discover_person_roles_from_html(URL, html) == ()


def test_curated_person_role_benchmark_exact_metrics() -> None:
    scenarios = json.loads((Path(__file__).parent / "fixtures" / "person_role_discovery_v1.json").read_text(encoding="utf-8"))
    tp=fp=fn=0
    for scenario in scenarios:
        expected={tuple(item) for item in scenario["expected"]}
        predicted={(item.name,item.title) for item in discover_person_roles_from_html(scenario["url"],scenario["html"])}
        tp += len(expected & predicted)
        fp += len(predicted - expected)
        fn += len(expected - predicted)
    assert len(scenarios) == 15
    assert (tp,fp,fn) == (12,0,0)
    assert tp/(tp+fp) == 1.0
    assert tp/(tp+fn) == 1.0


def test_current_serpro_seven_role_blocks_keep_local_email_and_phone_association() -> None:
    rows = [
        ("Diretor-Presidente - DP", "Wilton Itaiguara Gonçalves Mota", "presidencia@serpro.gov.br", "(61) 2021-8101"),
        ("Diretor de Negócios Governamentais - DINGM", "Ermes Ferreira Costa Neto", "dingm@serpro.gov.br", "(61) 2021-8133"),
        ("Diretor de Infraestrutura - DIINF", "Wallyson Lemos dos Reis Oliveira", "diinf@serpro.gov.br", "(61) 2021-8330"),
        ("Diretor de Administração e Finanças - DIRAF", "Osmar Quirino da Silva", "diraf@serpro.gov.br", "(61) 2021-8133"),
        ("Diretor de Pessoas e Assuntos Jurídicos - DIPEJ", "Alexandre Brandão Henriques Maimoni", "dipej@serpro.gov.br", "(61) 2021-8330"),
        ("Diretora de Negócios Econômico-Fazendários - DINEF", "Ariadne de Santa Teresa Lopes Fonseca", "dinef@serpro.gov.br", "(61) 2021-8330"),
        ("Diretor de Novos Negócios e Inteligência de TI - DINIT", "André Picoli Agatte", "dinit@serpro.gov.br", "(61) 2021-8133"),
    ]
    html = "<html><body>" + "".join(
        f"<h3>{title}</h3><p>{name}</p><p>E-mail: {email}</p><p>Telefone: {phone}</p><a href='/curriculo'>Currículo</a>"
        for title,name,email,phone in rows
    ) + "</body></html>"
    found = discover_person_roles_from_html("https://www.transparencia.serpro.gov.br/acesso-a-informacao/institucional/quem-e-quem", html)
    assert len(found) == 7
    for observation, (_, name, email, phone) in zip(found, rows, strict=True):
        assert observation.name == name
        assert PersonContactObservation(ContactKind.EMAIL, email) in observation.contacts
        assert PersonContactObservation(ContactKind.PHONE, phone) in observation.contacts
        assert not any(item.kind is ContactKind.PROFESSIONAL_PROFILE for item in observation.contacts)
