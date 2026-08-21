from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from searchleads.contact_discovery import OfficialPageContactSource, discover_contacts_from_html
from searchleads.domain import Company, ContactKind, ContactStatus
from searchleads.persistence import SQLiteLeadStore

NOW = datetime(2026, 8, 21, 15, 10, tzinfo=timezone.utc)
URL = "https://www.serpro.gov.br/menu/suporte/ajuda-ao-cliente"
REAL_SERPRO_MINIMAL_HTML = """
<html><body>
<p>Enviando uma mensagem para <a href="mailto:css.serpro@serpro.gov.br">css.serpro@serpro.gov.br</a></p>
<p>Pelo telefone 0800 728 2323</p>
<form action="/contact-info"><input name="email"></form>
</body></html>
"""


class ContactDiscoveryTests(unittest.TestCase):
    def test_extracts_email_phone_and_contact_form(self):
        contacts = discover_contacts_from_html(URL, REAL_SERPRO_MINIMAL_HTML)
        values = {(c.kind, c.value) for c in contacts}
        self.assertIn((ContactKind.EMAIL, "css.serpro@serpro.gov.br"), values)
        self.assertIn((ContactKind.PHONE, "0800 728 2323"), values)
        self.assertIn((ContactKind.CONTACT_FORM, "https://www.serpro.gov.br/contact-info"), values)

    def test_discovers_mailto_and_tel_without_duplicate_visible_values(self):
        html = '<a href="mailto:sales@example.com">sales@example.com</a><a href="tel:+5511999990000">+55 11 99999-0000</a>'
        contacts = discover_contacts_from_html("https://example.com/contact", html)
        self.assertEqual(sum(c.kind is ContactKind.EMAIL for c in contacts), 1)
        self.assertEqual(sum(c.kind is ContactKind.PHONE for c in contacts), 1)

    def test_extracts_linkedin_and_instagram_links(self):
        html = '<a href="https://www.linkedin.com/company/acme/">LinkedIn</a><a href="https://instagram.com/acme/">Instagram</a>'
        contacts = discover_contacts_from_html("https://acme.example/contact", html)
        kinds = {c.kind for c in contacts}
        self.assertIn(ContactKind.LINKEDIN, kinds)
        self.assertIn(ContactKind.INSTAGRAM, kinds)

    def test_does_not_treat_cnpj_cep_or_date_as_phone(self):
        html = '<p>CNPJ: 33.683.111/0002-80 CEP: 70836-900 Início: 30/06/1967</p>'
        contacts = discover_contacts_from_html(URL, html)
        self.assertFalse(any(c.kind is ContactKind.PHONE for c in contacts))

    def test_invalid_short_phone_is_ignored(self):
        html = '<p>Telefone: 12345</p>'
        contacts = discover_contacts_from_html(URL, html)
        self.assertFalse(any(c.kind is ContactKind.PHONE for c in contacts))

    def test_invalid_url_is_rejected(self):
        with self.assertRaises(ValueError):
            discover_contacts_from_html("serpro.gov.br/contact", REAL_SERPRO_MINIMAL_HTML)

    def test_ingestion_persists_raw_html_and_contacts_as_discovered(self):
        with SQLiteLeadStore() as store:
            company = Company("company:cnpj:33683111000280", created_at=NOW)
            store.save_company(company)
            result = OfficialPageContactSource().ingest(
                store,
                company.company_id,
                URL,
                html=REAL_SERPRO_MINIMAL_HTML,
                retrieved_at=NOW,
            )
            self.assertEqual(result.evidence.payload["body"], REAL_SERPRO_MINIMAL_HTML)
            self.assertGreaterEqual(len(result.contacts), 3)
            self.assertTrue(all(c.status is ContactStatus.DISCOVERED for c in result.contacts))
            self.assertTrue(all(c.owner.entity_id == company.company_id for c in result.contacts))
            for contact in result.contacts:
                loaded = store.get_contact_point(contact.contact_id)
                self.assertEqual(loaded, contact)
                self.assertEqual(loaded.provenance.evidence_ids, (result.evidence.evidence_id,))

    def test_missing_company_rejected_before_evidence_persistence(self):
        with SQLiteLeadStore() as store:
            with self.assertRaises(ValueError):
                OfficialPageContactSource().ingest(
                    store,
                    "missing-company",
                    URL,
                    html=REAL_SERPRO_MINIMAL_HTML,
                    retrieved_at=NOW,
                )
            self.assertEqual(store.list_evidence(), ())

    def test_same_page_snapshot_is_idempotent(self):
        with SQLiteLeadStore() as store:
            company = Company("company:cnpj:33683111000280", created_at=NOW)
            store.save_company(company)
            source = OfficialPageContactSource()
            first = source.ingest(store, company.company_id, URL, html=REAL_SERPRO_MINIMAL_HTML, retrieved_at=NOW)
            second = source.ingest(store, company.company_id, URL, html=REAL_SERPRO_MINIMAL_HTML, retrieved_at=NOW)
            self.assertEqual(first, second)

    def test_roundtrip_survives_database_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "contacts.sqlite3"
            company = Company("company:cnpj:33683111000280", created_at=NOW)
            with SQLiteLeadStore(path) as store:
                store.save_company(company)
                result = OfficialPageContactSource().ingest(
                    store, company.company_id, URL, html=REAL_SERPRO_MINIMAL_HTML, retrieved_at=NOW
                )
                ids = [c.contact_id for c in result.contacts]
            with SQLiteLeadStore(path) as reopened:
                loaded = [reopened.get_contact_point(cid) for cid in ids]
                self.assertEqual(len(loaded), len(ids))
                self.assertTrue(all(c.status is ContactStatus.DISCOVERED for c in loaded))


if __name__ == "__main__":
    unittest.main()
