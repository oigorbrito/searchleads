from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from searchleads.contact_discovery import OfficialPageContactSource
from searchleads.contact_validation import (
    ContactValidationDisposition,
    ContactValidationMethod,
    validate_contact_from_official_evidence,
)
from searchleads.domain import Company, ContactKind, ContactPoint, ContactStatus, EntityRef, EntityType, Evidence, Provenance, Source, SourceType
from searchleads.persistence import SQLiteLeadStore

T1 = datetime(2026, 8, 21, 14, 0, tzinfo=timezone.utc)
T2 = T1 + timedelta(minutes=30)
P1 = "https://www.serpro.gov.br/menu/suporte/ajuda-ao-cliente"
P2 = "https://www.serpro.gov.br/menu/contato/cliente/perguntas-frequentes/suporte/suporte-perguntas-frequentes"
H1 = '<p>E-mail: css.serpro@serpro.gov.br</p><p>Pelo telefone 0800 728 2323</p>'
H2 = '<a href="mailto:css.serpro@serpro.gov.br">CSS</a><a href="tel:08007282323">0800 728 2323</a>'


def setup_discovered(store: SQLiteLeadStore):
    company = Company("company:cnpj:33683111000280", created_at=T1)
    store.save_company(company)
    first = OfficialPageContactSource().ingest(store, company.company_id, P1, html=H1, retrieved_at=T1)
    email = next(c for c in first.contacts if c.kind is ContactKind.EMAIL)
    phone = next(c for c in first.contacts if c.kind is ContactKind.PHONE)
    second = OfficialPageContactSource().ingest(store, company.company_id, P2, html=H2, retrieved_at=T2)
    return company, first, second, email, phone


class ContactValidationTests(unittest.TestCase):
    def test_two_official_pages_validate_email_association(self):
        with SQLiteLeadStore() as store:
            _, first, second, email, _ = setup_discovered(store)
            result = validate_contact_from_official_evidence(store, email.contact_id, (second.evidence.evidence_id,))
            self.assertEqual(result.disposition, ContactValidationDisposition.VALIDATED)
            self.assertEqual(result.method, ContactValidationMethod.OFFICIAL_CROSS_PAGE_CORROBORATION)
            self.assertEqual(result.validated_contact.status, ContactStatus.VALIDATED)
            self.assertFalse(result.deliverability_verified)
            self.assertEqual(set(result.confirming_evidence_ids), {first.evidence.evidence_id, second.evidence.evidence_id})

    def test_two_official_pages_validate_phone_association(self):
        with SQLiteLeadStore() as store:
            _, _, second, _, phone = setup_discovered(store)
            result = validate_contact_from_official_evidence(store, phone.contact_id, (second.evidence.evidence_id,))
            self.assertEqual(result.disposition, ContactValidationDisposition.VALIDATED)
            self.assertFalse(result.deliverability_verified)

    def test_one_observation_remains_unknown_not_validated(self):
        with SQLiteLeadStore() as store:
            _, _, _, email, _ = setup_discovered(store)
            result = validate_contact_from_official_evidence(store, email.contact_id)
            self.assertEqual(result.disposition, ContactValidationDisposition.UNKNOWN)
            self.assertIsNone(result.validated_contact)

    def test_non_official_corroboration_does_not_validate(self):
        with SQLiteLeadStore() as store:
            _, _, _, email, _ = setup_discovered(store)
            source = Source("third-party", SourceType.WEBSITE, "https://directory.example/acme")
            evidence = Evidence("third-party-ev", source.source_id, T2, H2, locator=source.locator)
            store.save_source(source); store.save_evidence(evidence)
            result = validate_contact_from_official_evidence(store, email.contact_id, (evidence.evidence_id,))
            self.assertEqual(result.disposition, ContactValidationDisposition.UNKNOWN)

    def test_official_page_without_contact_does_not_validate_or_mark_stale(self):
        with SQLiteLeadStore() as store:
            company, _, _, email, _ = setup_discovered(store)
            obs = OfficialPageContactSource().ingest(store, company.company_id, "https://www.serpro.gov.br/other", html='<p>Sem canal aqui</p>', retrieved_at=T2)
            result = validate_contact_from_official_evidence(store, email.contact_id, (obs.evidence.evidence_id,))
            self.assertEqual(result.disposition, ContactValidationDisposition.UNKNOWN)
            self.assertEqual(result.original_contact.status, ContactStatus.DISCOVERED)

    def test_later_snapshot_same_locator_can_reconfirm(self):
        with SQLiteLeadStore() as store:
            company = Company("company:cnpj:33683111000280", created_at=T1); store.save_company(company)
            first = OfficialPageContactSource().ingest(store, company.company_id, P1, html=H1, retrieved_at=T1)
            email = next(c for c in first.contacts if c.kind is ContactKind.EMAIL)
            later_html = H1 + '<p>Atualizado</p>'
            later = OfficialPageContactSource().ingest(store, company.company_id, P1, html=later_html, retrieved_at=T2)
            result = validate_contact_from_official_evidence(store, email.contact_id, (later.evidence.evidence_id,))
            self.assertEqual(result.disposition, ContactValidationDisposition.VALIDATED)

    def test_same_snapshot_repeated_does_not_create_second_confirmation(self):
        with SQLiteLeadStore() as store:
            _, first, _, email, _ = setup_discovered(store)
            result = validate_contact_from_official_evidence(store, email.contact_id, (first.evidence.evidence_id, first.evidence.evidence_id))
            self.assertEqual(result.disposition, ContactValidationDisposition.UNKNOWN)

    def test_structurally_invalid_preexisting_contact_is_invalid(self):
        with SQLiteLeadStore() as store:
            company = Company("company-1", created_at=T1); store.save_company(company)
            source = Source("src", SourceType.OFFICIAL_SOURCE, "https://example.test")
            ev = Evidence("ev", "src", T1, '<p>x</p>', locator=source.locator)
            store.save_source(source); store.save_evidence(ev)
            bad = ContactPoint("bad", EntityRef(EntityType.COMPANY, company.company_id), ContactKind.EMAIL, "not-an-email", Provenance(("ev",), "legacy", generated_at=T1))
            store.save_contact_point(bad)
            result = validate_contact_from_official_evidence(store, bad.contact_id)
            self.assertEqual(result.disposition, ContactValidationDisposition.INVALID)

    def test_validation_persists_separate_immutable_snapshot(self):
        with SQLiteLeadStore() as store:
            _, _, second, email, _ = setup_discovered(store)
            result = validate_contact_from_official_evidence(store, email.contact_id, (second.evidence.evidence_id,))
            loaded_original = store.get_contact_point(email.contact_id)
            loaded_validated = store.get_contact_point(result.validated_contact.contact_id)
            self.assertEqual(loaded_original.status, ContactStatus.DISCOVERED)
            self.assertEqual(loaded_validated.status, ContactStatus.VALIDATED)
            self.assertNotEqual(loaded_original.contact_id, loaded_validated.contact_id)

    def test_validation_roundtrip_survives_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "validation.sqlite3"
            with SQLiteLeadStore(path) as store:
                _, _, second, email, _ = setup_discovered(store)
                result = validate_contact_from_official_evidence(store, email.contact_id, (second.evidence.evidence_id,))
                vid = result.validated_contact.contact_id
            with SQLiteLeadStore(path) as reopened:
                loaded = reopened.get_contact_point(vid)
                self.assertEqual(loaded.status, ContactStatus.VALIDATED)
                self.assertGreaterEqual(len(loaded.provenance.evidence_ids), 2)

    def test_missing_contact_is_explicit_error(self):
        with SQLiteLeadStore() as store:
            with self.assertRaises(ValueError):
                validate_contact_from_official_evidence(store, "missing")

    def test_missing_validation_evidence_is_explicit_error(self):
        with SQLiteLeadStore() as store:
            _, _, _, email, _ = setup_discovered(store)
            with self.assertRaises(ValueError):
                validate_contact_from_official_evidence(store, email.contact_id, ("missing-ev",))


if __name__ == "__main__":
    unittest.main()
