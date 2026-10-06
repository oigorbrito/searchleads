from __future__ import annotations

from datetime import datetime, timezone
from email.message import Message
from io import BytesIO
import re
from urllib.error import HTTPError, URLError

import pytest

from searchleads.contact_discovery import (
    USER_AGENT,
    CompanyPageContactSource,
    ContactAcquisitionError,
    ContactPageResponseError,
    DiscoveredContact,
    HTTPPageObservation,
    discover_contacts_from_html,
    http_get,
)
from searchleads.domain import Company, ContactKind, ContactPoint, ContactStatus, Evidence
from searchleads.persistence import SQLiteRepository

NOW = datetime(2026, 8, 25, 2, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 8, 25, 2, 1, tzinfo=timezone.utc)
URL = "https://example.com/contact"
HTML = """
<html><body>
<a href="mailto:Sales@Example.com?subject=Oi">Email</a>
<p>E-mail alternativo: support@example.com</p>
<a href="tel:+55%2011%2099999-0000">Telefone</a>
<p>Telefone: 0800 728 2323</p>
<a href="https://wa.me/5511988887777?text=oi">WhatsApp</a>
<form action="https://forms.vendor.example/submit"><input name="email"></form>
<a href="https://www.linkedin.com/company/acme/">LinkedIn</a>
<a href="https://instagram.com/acme/">Instagram</a>
</body></html>
"""


def kinds_values(items):
    return {(item.kind, item.value) for item in items}


def test_extracts_supported_company_contacts() -> None:
    found = discover_contacts_from_html(URL, HTML)
    values = kinds_values(found)
    assert (ContactKind.EMAIL, "Sales@Example.com") in values
    assert (ContactKind.EMAIL, "support@example.com") in values
    assert (ContactKind.PHONE, "+55 11 99999-0000") in values
    assert (ContactKind.PHONE, "0800 728 2323") in values
    assert (ContactKind.WHATSAPP, "+5511988887777") in values
    assert (ContactKind.CONTACT_FORM, URL) in values
    assert (ContactKind.LINKEDIN, "https://www.linkedin.com/company/acme/") in values
    assert (ContactKind.INSTAGRAM, "https://instagram.com/acme/") in values


def test_contact_form_represents_page_not_submission_endpoint() -> None:
    found = discover_contacts_from_html(URL, '<form action="https://evil.example/submit"></form>')
    assert found == (DiscoveredContact(ContactKind.CONTACT_FORM, URL),)


def test_duplicate_mailto_and_visible_email_collapse_case_insensitively() -> None:
    html = '<a href="mailto:Sales@Example.com">sales@example.com</a>'
    found = discover_contacts_from_html(URL, html)
    assert len(found) == 1
    assert found[0].kind is ContactKind.EMAIL


def test_duplicate_phone_formats_collapse_by_digits() -> None:
    html = '<a href="tel:+5511999990000">x</a><p>Telefone: +55 (11) 99999-0000</p>'
    found = discover_contacts_from_html(URL, html)
    phones = [item for item in found if item.kind is ContactKind.PHONE]
    assert len(phones) == 1


def test_cnpj_cep_date_and_unlabeled_digits_do_not_become_phone() -> None:
    html = '<p>CNPJ: 33.683.111/0002-80 CEP: 70836-900 30/06/1967 12345678901</p>'
    assert not any(item.kind is ContactKind.PHONE for item in discover_contacts_from_html(URL, html))


@pytest.mark.parametrize("html", ['<p>Telefone: 12345</p>', '<a href="tel:12345">short</a>'])
def test_short_phone_is_ignored(html: str) -> None:
    assert not any(item.kind is ContactKind.PHONE for item in discover_contacts_from_html(URL, html))


def test_long_phone_is_ignored() -> None:
    html = '<a href="tel:+1234567890123456">long</a>'
    assert not any(item.kind is ContactKind.PHONE for item in discover_contacts_from_html(URL, html))


def test_whatsapp_requires_explicit_wa_me_numeric_path() -> None:
    html = '''
    <a href="https://wa.me/5511999990000">ok</a>
    <a href="https://wa.me/not-a-number">bad</a>
    <a href="https://whatsapp.com/5511999990000">not-supported</a>
    '''
    found = [x for x in discover_contacts_from_html(URL, html) if x.kind is ContactKind.WHATSAPP]
    assert found == [DiscoveredContact(ContactKind.WHATSAPP, "+5511999990000")]


def test_linkedin_person_profile_is_not_company_contact() -> None:
    html = '<a href="https://linkedin.com/in/person">person</a><a href="https://linkedin.com/company/acme">company</a>'
    found = [x for x in discover_contacts_from_html(URL, html) if x.kind is ContactKind.LINKEDIN]
    assert len(found) == 1 and "/company/acme" in found[0].value


@pytest.mark.parametrize("href", [
    "https://instagram.com/p/ABC/",
    "https://instagram.com/reel/ABC/",
    "https://instagram.com/stories/acme/1/",
    "https://instagram.com/explore/",
])
def test_instagram_content_routes_are_not_profile_contacts(href: str) -> None:
    found = discover_contacts_from_html(URL, f'<a href="{href}">x</a>')
    assert not any(x.kind is ContactKind.INSTAGRAM for x in found)


def test_script_style_template_and_noscript_text_is_ignored() -> None:
    html = '''
    <script>fake@example.com; Telefone: 11999990000</script>
    <style>.x{content:"css@example.com"}</style>
    <template>template@example.com</template>
    <noscript>noscript@example.com</noscript>
    <p>real@example.com</p>
    '''
    found = [x.value for x in discover_contacts_from_html(URL, html) if x.kind is ContactKind.EMAIL]
    assert found == ["real@example.com"]


@pytest.mark.parametrize("email", [
    "@example.com", "a@.example.com", "a@example.com.", "a@example..com",
])
def test_invalid_visible_emails_are_not_extracted(email: str) -> None:
    assert not any(x.kind is ContactKind.EMAIL for x in discover_contacts_from_html(URL, f'<p>{email}</p>'))


def test_invalid_mailto_is_ignored() -> None:
    assert discover_contacts_from_html(URL, '<a href="mailto:a@invalid">bad</a>') == ()


@pytest.mark.parametrize("url", ["example.com/contact", "ftp://example.com/contact", "http://", "https://[bad"])
def test_invalid_page_url_is_rejected(url: str) -> None:
    with pytest.raises(ValueError):
        discover_contacts_from_html(url, HTML)


@pytest.mark.parametrize("url", [
    "https://user:password@example.com/contact",
    "http://user@example.com/contact",
])
def test_url_with_credentials_is_rejected(url: str) -> None:
    with pytest.raises(ValueError, match="embedded credentials"):
        discover_contacts_from_html(url, HTML)


def test_html_must_be_text() -> None:
    with pytest.raises(TypeError):
        discover_contacts_from_html(URL, b"html")  # type: ignore[arg-type]


def test_discovered_contact_rejects_blank_value() -> None:
    with pytest.raises(ValueError):
        DiscoveredContact(ContactKind.EMAIL, " ")


def test_http_observation_validates_url_status_time() -> None:
    with pytest.raises(ValueError): HTTPPageObservation("bad", 200, "x", NOW)
    with pytest.raises(ValueError): HTTPPageObservation(URL, 99, "x", NOW)
    with pytest.raises(ValueError): HTTPPageObservation(URL, 600, "x", NOW)
    with pytest.raises(ValueError): HTTPPageObservation(URL, 200, "x", datetime(2026,8,25,2,0))


def test_ingestion_requires_existing_company_before_transport_call() -> None:
    called = False
    def transport(url):
        nonlocal called; called = True
        return HTTPPageObservation(url, 200, HTML, NOW)
    with SQLiteRepository() as repo:
        with pytest.raises(ValueError, match="company must already be persisted"):
            CompanyPageContactSource(transport).ingest("missing", URL, repo)
    assert called is False


def test_ingestion_persists_evidence_and_all_contacts_as_discovered() -> None:
    with SQLiteRepository() as repo:
        company = Company("company-1")
        repo.save(company)
        result = CompanyPageContactSource(lambda url: HTTPPageObservation(url, 200, HTML, NOW)).ingest(company.company_id, URL, repo)
        assert result.evidence.raw_payload == HTML
        assert result.evidence.metadata["http_status"] == 200
        assert result.evidence_was_new is True
        assert len(result.contacts) == 8
        for contact in result.contacts:
            assert contact.owner_id == company.company_id
            assert contact.status is ContactStatus.DISCOVERED
            assert contact.discovery_evidence_ids == (result.evidence.evidence_id,)
            assert contact.validation_evidence_ids == ()
            assert contact.validated_at is None
            assert repo.load(ContactPoint, contact.contact_id) == contact


def test_same_response_snapshot_is_idempotent() -> None:
    obs = HTTPPageObservation(URL, 200, HTML, NOW)
    with SQLiteRepository() as repo:
        repo.save(Company("company-1"))
        source = CompanyPageContactSource(lambda url: obs)
        first = source.ingest("company-1", URL, repo)
        second = source.ingest("company-1", URL, repo)
        assert first.company == second.company
        assert first.source == second.source
        assert first.evidence == second.evidence
        assert first.contacts == second.contacts
        assert first.evidence_was_new is True
        assert second.evidence_was_new is False


def test_changed_body_creates_new_evidence_and_contact_snapshots() -> None:
    observations = iter([
        HTTPPageObservation(URL, 200, '<a href="mailto:a@example.com">a</a>', NOW),
        HTTPPageObservation(URL, 200, '<a href="mailto:a@example.com">a</a><a href="tel:11999990000">p</a>', LATER),
    ])
    with SQLiteRepository() as repo:
        repo.save(Company("company-1"))
        source = CompanyPageContactSource(lambda url: next(observations))
        first = source.ingest("company-1", URL, repo)
        second = source.ingest("company-1", URL, repo)
        assert first.evidence.evidence_id != second.evidence.evidence_id
        assert {c.contact_id for c in first.contacts}.isdisjoint({c.contact_id for c in second.contacts})
        assert len(first.contacts) == 1 and len(second.contacts) == 2


def test_same_body_different_http_status_is_distinct_evidence() -> None:
    observations = iter([
        HTTPPageObservation(URL, 429, "same body", NOW),
        HTTPPageObservation(URL, 200, "same body", LATER),
    ])
    with SQLiteRepository() as repo:
        repo.save(Company("company-1"))
        source = CompanyPageContactSource(lambda url: next(observations))
        with pytest.raises(ContactPageResponseError) as exc:
            source.ingest("company-1", URL, repo)
        first_id = exc.value.evidence_id
        second = source.ingest("company-1", URL, repo)
        assert first_id != second.evidence.evidence_id
        assert repo.load(Evidence, first_id).metadata["http_status"] == 429
        assert second.evidence.metadata["http_status"] == 200


@pytest.mark.parametrize("status", [400, 403, 404, 429, 500])
def test_non_200_body_is_persisted_before_error(status: int) -> None:
    body = f"error-{status}"
    with SQLiteRepository() as repo:
        repo.save(Company("company-1"))
        source = CompanyPageContactSource(lambda url: HTTPPageObservation(url, status, body, NOW))
        with pytest.raises(ContactPageResponseError) as exc:
            source.ingest("company-1", URL, repo)
        evidence = repo.load(Evidence, exc.value.evidence_id)
        assert evidence.raw_payload == body
        assert evidence.metadata["http_status"] == status


def test_transport_url_mismatch_is_rejected_before_source_evidence() -> None:
    with SQLiteRepository() as repo:
        repo.save(Company("company-1"))
        source = CompanyPageContactSource(lambda url: HTTPPageObservation("https://other.example/x", 200, HTML, NOW))
        with pytest.raises(ContactAcquisitionError):
            source.ingest("company-1", URL, repo)


def test_http_get_success_uses_explicit_user_agent(monkeypatch) -> None:
    headers = Message(); headers["Content-Type"] = "text/html; charset=utf-8"
    seen = {}
    class Response:
        status=200
        def __enter__(self): return self
        def __exit__(self,*args): return None
        def read(self): return "olá".encode()
        @property
        def headers(self): return headers
    def fake(request, timeout):
        seen["ua"] = request.get_header("User-agent"); seen["accept"] = request.get_header("Accept"); return Response()
    monkeypatch.setattr("searchleads.contact_discovery.company_page.urlopen", fake)
    result = http_get(URL, timeout=1)
    assert result.raw_html == "olá"
    assert seen["ua"] == USER_AGENT
    assert "text/html" in seen["accept"]


def test_http_error_returns_observation_for_evidence(monkeypatch) -> None:
    headers = Message(); headers["Content-Type"] = "text/html; charset=utf-8"
    error = HTTPError(URL, 429, "slow", headers, BytesIO(b"slow down"))
    monkeypatch.setattr("searchleads.contact_discovery.company_page.urlopen", lambda req, timeout: (_ for _ in ()).throw(error))
    result = http_get(URL, timeout=1)
    assert result.status_code == 429 and result.raw_html == "slow down"


def test_network_error_has_no_fabricated_observation(monkeypatch) -> None:
    monkeypatch.setattr("searchleads.contact_discovery.company_page.urlopen", lambda req, timeout: (_ for _ in ()).throw(URLError("offline")))
    with pytest.raises(ContactAcquisitionError):
        http_get(URL, timeout=1)


def test_non_decodable_http_body_is_acquisition_error(monkeypatch) -> None:
    headers = Message(); headers["Content-Type"] = "text/html; charset=utf-8"
    class Response:
        status=200
        def __enter__(self): return self
        def __exit__(self,*args): return None
        def read(self): return b"\xff"
        @property
        def headers(self): return headers
    monkeypatch.setattr("searchleads.contact_discovery.company_page.urlopen", lambda req, timeout: Response())
    with pytest.raises(ContactAcquisitionError):
        http_get(URL, timeout=1)


def test_header_object_without_items_is_supported(monkeypatch) -> None:
    class Response:
        status=200; headers=object()
        def __enter__(self): return self
        def __exit__(self,*args): return None
        def read(self): return b"ok"
    monkeypatch.setattr("searchleads.contact_discovery.company_page.urlopen", lambda req, timeout: Response())
    assert http_get(URL, timeout=1).headers == {}

def test_overlong_mailto_email_is_ignored() -> None:
    local = "a" * 65
    assert discover_contacts_from_html(URL, f'<a href="mailto:{local}@example.com">x</a>') == ()


@pytest.mark.parametrize("href", ["https://[bad", "ftp://linkedin.com/company/acme", "https://linkedin.com:99999/company/acme"])
def test_malformed_social_urls_are_ignored(href: str) -> None:
    found = discover_contacts_from_html(URL, f'<a href="{href}">x</a>')
    assert not any(x.kind in {ContactKind.LINKEDIN, ContactKind.INSTAGRAM} for x in found)


def test_social_default_https_port_is_removed() -> None:
    found = discover_contacts_from_html(URL, '<a href="https://www.linkedin.com:443/company/acme">x</a>')
    item = next(x for x in found if x.kind is ContactKind.LINKEDIN)
    assert item.value == "https://www.linkedin.com/company/acme"


@pytest.mark.parametrize("href", ["https://[bad", "ftp://wa.me/5511999990000"])
def test_malformed_whatsapp_urls_are_ignored(href: str) -> None:
    found = discover_contacts_from_html(URL, f'<a href="{href}">x</a>')
    assert not any(x.kind is ContactKind.WHATSAPP for x in found)


def test_content_address_collision_guard(monkeypatch) -> None:
    obs = HTTPPageObservation(URL, 200, HTML, NOW)
    with SQLiteRepository() as repo:
        company = Company("company-1")
        repo.save(company)
        real_load = repo.load
        fake = Evidence("fake", "source", "https://wrong.example", NOW, HTML)
        def load(record_type, record_id):
            if record_type is Company:
                return real_load(record_type, record_id)
            if record_type is Evidence:
                return fake
            return real_load(record_type, record_id)
        monkeypatch.setattr(repo, "load", load)
        with pytest.raises(ContactAcquisitionError, match="collision"):
            CompanyPageContactSource(lambda url: obs).ingest("company-1", URL, repo)

def test_overall_email_length_limit_is_enforced() -> None:
    domain = "a" * 249 + ".com"
    assert discover_contacts_from_html(URL, f'<a href="mailto:x@{domain}">x</a>') == ()


def test_email_domain_label_length_limit_is_enforced() -> None:
    domain = "a" * 64 + ".example"
    assert discover_contacts_from_html(URL, f'<a href="mailto:x@{domain}">x</a>') == ()

def test_curated_contact_benchmark_exact_metrics() -> None:
    import json
    from pathlib import Path
    scenarios = json.loads((Path(__file__).parent / "fixtures" / "contact_discovery_v1.json").read_text(encoding="utf-8"))
    tp=fp=fn=0
    for scenario in scenarios:
        expected={tuple(item) for item in scenario["expected"]}
        predicted={(item.kind.value,item.value) for item in discover_contacts_from_html(scenario["url"],scenario["html"])}
        tp += len(expected & predicted)
        fp += len(predicted - expected)
        fn += len(expected - predicted)
    assert len(scenarios) == 12
    assert (tp,fp,fn) == (17,0,0)
    assert tp/(tp+fp) == 1.0
    assert tp/(tp+fn) == 1.0


def test_current_serpro_public_channels_are_extractable_from_minimal_calibration_html() -> None:
    url = "https://www.serpro.gov.br/contact-info"
    html = '''<p>E-mail: css.serpro@serpro.gov.br</p><p>Telefone: 0800 728 2323</p><form></form>'''
    values = kinds_values(discover_contacts_from_html(url, html))
    assert (ContactKind.EMAIL, "css.serpro@serpro.gov.br") in values
    assert (ContactKind.PHONE, "0800 728 2323") in values
    assert (ContactKind.CONTACT_FORM, url) in values

def test_template_links_and_forms_are_not_discovered() -> None:
    html = '<template><a href="mailto:hidden@example.com">x</a><form></form></template>'
    assert discover_contacts_from_html(URL, html) == ()


def test_linkedin_company_subroutes_are_not_promoted_to_profile_contact() -> None:
    html = '<a href="https://linkedin.com/company/acme/posts">posts</a>'
    assert not any(x.kind is ContactKind.LINKEDIN for x in discover_contacts_from_html(URL, html))


def test_whatsapp_requires_single_numeric_path_segment() -> None:
    html = '<a href="https://wa.me/5511999990000/123">bad</a>'
    assert not any(x.kind is ContactKind.WHATSAPP for x in discover_contacts_from_html(URL, html))


def test_mailto_rejects_space_and_non_ascii_domain() -> None:
    html = '<a href="mailto:a%20b@example.com">bad</a><a href="mailto:a@éxample.com">bad2</a>'
    assert not any(x.kind is ContactKind.EMAIL for x in discover_contacts_from_html(URL, html))


def test_tel_uri_extension_is_not_folded_into_phone_number() -> None:
    found = discover_contacts_from_html(URL, '<a href="tel:+5511999990000;ext=123">call</a>')
    phone = next(x for x in found if x.kind is ContactKind.PHONE)
    assert phone.value == "+5511999990000"

@pytest.mark.parametrize("digits", ["123456", "1" * 16])
def test_whatsapp_numeric_path_length_is_bounded(digits: str) -> None:
    found = discover_contacts_from_html(URL, f'<a href="https://wa.me/{digits}">bad</a>')
    assert not any(x.kind is ContactKind.WHATSAPP for x in found)


def test_http_observation_requires_text_body() -> None:
    with pytest.raises(TypeError, match="raw_html must be text"):
        HTTPPageObservation(URL, 200, b"html", NOW)  # type: ignore[arg-type]
