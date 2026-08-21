from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from searchleads.domain import (
    CandidateFact,
    Company,
    EntityRef,
    EntityType,
    Evidence,
    Provenance,
    Source,
    SourceType,
)
from searchleads.normalization import (
    NormalizationStatus,
    normalize_candidate_fact,
    normalize_persisted_candidate,
)
from searchleads.persistence import SQLiteLeadStore


NOW = datetime(2026, 8, 21, 15, 0, tzinfo=timezone.utc)


class CompanyNormalizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provenance = Provenance(
            evidence_ids=("ev-1",),
            activity="source_extract",
            generated_at=NOW,
            agent="test-source",
        )
        self.subject = EntityRef(EntityType.COMPANY, "company-1")

    def fact(self, predicate, raw, **kwargs):
        return CandidateFact(
            candidate_fact_id=f"fact-{predicate}",
            subject=self.subject,
            predicate=predicate,
            raw_value=raw,
            provenance=self.provenance,
            **kwargs,
        )

    def test_company_name_collapses_whitespace_without_removing_legal_suffix(self):
        source = self.fact("legal_name", "  ACME\tTecnologia   Ltda.  ")
        result = normalize_candidate_fact(source)
        self.assertEqual(result.status, NormalizationStatus.NORMALIZED)
        self.assertEqual(result.normalized_fact.raw_value, source.raw_value)
        self.assertEqual(result.normalized_fact.normalized_value, "ACME Tecnologia Ltda.")
        self.assertEqual(
            result.normalized_fact.normalization_rule,
            "company_name_nfkc_whitespace_v1",
        )

    def test_unicode_compatibility_is_normalized(self):
        source = self.fact("trade_name", "ＡＣＭＥ")
        result = normalize_candidate_fact(source)
        self.assertEqual(result.normalized_fact.normalized_value, "ACME")

    def test_domain_extracts_and_lowercases_host_without_inventing_root_domain(self):
        source = self.fact("domain", "HTTPS://WWW.Example.COM/path?q=1")
        result = normalize_candidate_fact(source)
        self.assertEqual(result.normalized_fact.normalized_value, "www.example.com")

    def test_url_lowercases_scheme_host_removes_default_port_and_fragment(self):
        source = self.fact(
            "website_url",
            "HTTPS://Example.COM:443/Contact?A=1#team",
        )
        result = normalize_candidate_fact(source)
        self.assertEqual(
            result.normalized_fact.normalized_value,
            "https://example.com/Contact?A=1",
        )

    def test_url_without_explicit_scheme_is_invalid_instead_of_assuming_https(self):
        source = self.fact("website_url", "example.com/contact")
        result = normalize_candidate_fact(source)
        self.assertEqual(result.status, NormalizationStatus.INVALID)
        self.assertIsNone(result.normalized_fact)

    def test_phone_strips_punctuation_without_inventing_country_code(self):
        domestic = normalize_candidate_fact(self.fact("phone", "(11) 99999-0000"))
        international = normalize_candidate_fact(self.fact("phone", "+55 (11) 99999-0000"))
        self.assertEqual(domestic.normalized_fact.normalized_value, "11999990000")
        self.assertEqual(international.normalized_fact.normalized_value, "+5511999990000")

    def test_address_only_normalizes_unicode_and_whitespace(self):
        source = self.fact("address", "  Av. Paulista,  1000  -  Bela Vista ")
        result = normalize_candidate_fact(source)
        self.assertEqual(
            result.normalized_fact.normalized_value,
            "Av. Paulista, 1000 - Bela Vista",
        )

    def test_state_two_letter_code_is_uppercased(self):
        source = self.fact("state", " sp ")
        result = normalize_candidate_fact(source)
        self.assertEqual(result.normalized_fact.normalized_value, "SP")
        self.assertEqual(result.normalized_fact.normalization_rule, "state_two_letter_upper_v1")

    def test_cnae_code_becomes_seven_digit_string(self):
        source = self.fact("primary_cnae_code", 6204000)
        result = normalize_candidate_fact(source)
        self.assertEqual(result.normalized_fact.normalized_value, "6204000")
        self.assertEqual(result.normalized_fact.normalization_rule, "cnae_digits7_v1")

    def test_industry_label_is_not_reclassified(self):
        source = self.fact("industry_label", "  Consultoria   em TI ")
        result = normalize_candidate_fact(source)
        self.assertEqual(result.normalized_fact.normalized_value, "Consultoria em TI")

    def test_social_profile_uses_url_normalizer(self):
        source = self.fact("linkedin_url", "https://WWW.LinkedIn.com/company/Acme/#about")
        result = normalize_candidate_fact(source)
        self.assertEqual(
            result.normalized_fact.normalized_value,
            "https://www.linkedin.com/company/Acme/",
        )

    def test_unknown_predicate_is_explicitly_unsupported(self):
        source = self.fact("employee_count", 42)
        result = normalize_candidate_fact(source)
        self.assertEqual(result.status, NormalizationStatus.UNSUPPORTED)
        self.assertIsNone(result.normalized_fact)

    def test_projection_preserves_identity_provenance_confidence_and_original_object(self):
        source = self.fact("city", "  São   Paulo ", confidence=0.8)
        result = normalize_candidate_fact(source)
        projected = result.normalized_fact
        self.assertEqual(projected.candidate_fact_id, source.candidate_fact_id)
        self.assertEqual(projected.provenance, source.provenance)
        self.assertEqual(projected.confidence, source.confidence)
        self.assertIsNone(source.normalized_value)
        self.assertIsNone(source.normalization_rule)

    def test_persisted_raw_candidate_can_be_normalized_after_database_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "leads.sqlite3"
            source = Source("src-1", SourceType.DATASET, "https://example.test/company")
            evidence = Evidence("ev-1", "src-1", NOW, {"municipio": "  São   Paulo "})
            company = Company("company-1", created_at=NOW)
            fact = self.fact("city", "  São   Paulo ")
            with SQLiteLeadStore(path) as store:
                store.save_source(source)
                store.save_evidence(evidence)
                store.save_company(company)
                store.save_candidate_fact(fact)
            with SQLiteLeadStore(path) as reopened:
                result = normalize_persisted_candidate(reopened, fact.candidate_fact_id)
            self.assertEqual(result.normalized_fact.normalized_value, "São Paulo")
            self.assertEqual(result.source_fact.raw_value, "  São   Paulo ")


if __name__ == "__main__":
    unittest.main()
