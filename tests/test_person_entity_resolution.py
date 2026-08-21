import unittest

from searchleads.person_entity_resolution import (
    LabeledPersonPair,
    PersonRecord,
    PersonResolutionDisposition,
    evaluate_person_resolution,
    resolve_person_pair,
)


def record(record_id: str, **kwargs) -> PersonRecord:
    return PersonRecord(record_id, **kwargs)


class PersonEntityResolutionTests(unittest.TestCase):
    def test_same_name_alone_never_matches(self):
        decision = resolve_person_pair(
            record("a", name="João Silva"),
            record("b", name="Joao Silva"),
        )
        self.assertEqual(
            decision.disposition,
            PersonResolutionDisposition.INSUFFICIENT_EVIDENCE,
        )

    def test_same_name_company_role_goes_to_review(self):
        decision = resolve_person_pair(
            record("a", name="Ana Costa", company_id="c1", role="Diretora"),
            record("b", name="Ana Costa", company_id="c1", role="Diretora"),
        )
        self.assertEqual(decision.disposition, PersonResolutionDisposition.REVIEW)

    def test_person_unique_profile_auto_matches(self):
        decision = resolve_person_pair(
            record(
                "a",
                name="Ana Costa",
                profile_url="https://linkedin.com/in/ana/",
                profile_is_person_unique=True,
            ),
            record(
                "b",
                name="Ana Costa",
                profile_url="https://LINKEDIN.com/in/ana",
                profile_is_person_unique=True,
            ),
        )
        self.assertEqual(decision.disposition, PersonResolutionDisposition.AUTO_MATCH)

    def test_same_profile_without_person_unique_scope_is_review(self):
        decision = resolve_person_pair(
            record("a", name="João Silva", profile_url="https://example.org/curriculos"),
            record("b", name="Joao Silva", profile_url="https://example.org/curriculos"),
        )
        self.assertEqual(decision.disposition, PersonResolutionDisposition.REVIEW)

    def test_one_sided_unique_profile_claim_does_not_auto_match(self):
        decision = resolve_person_pair(
            record(
                "a",
                name="Ana Costa",
                profile_url="https://linkedin.com/in/ana",
                profile_is_person_unique=True,
            ),
            record(
                "b",
                name="Ana Costa",
                profile_url="https://linkedin.com/in/ana",
            ),
        )
        self.assertEqual(decision.disposition, PersonResolutionDisposition.REVIEW)

    def test_same_email_without_same_name_does_not_auto_match(self):
        decision = resolve_person_pair(
            record(
                "a",
                name="Ana Costa",
                professional_email="ana@example.com",
                professional_email_is_person_unique=True,
            ),
            record(
                "b",
                name="Bruna Lima",
                professional_email="ana@example.com",
                professional_email_is_person_unique=True,
            ),
        )
        self.assertEqual(
            decision.disposition,
            PersonResolutionDisposition.INSUFFICIENT_EVIDENCE,
        )

    def test_person_unique_professional_email_auto_matches(self):
        decision = resolve_person_pair(
            record(
                "a",
                name="Ana Costa",
                professional_email="ANA@EXAMPLE.COM",
                professional_email_is_person_unique=True,
            ),
            record(
                "b",
                name="Ana Costa",
                professional_email="ana@example.com",
                professional_email_is_person_unique=True,
            ),
        )
        self.assertEqual(decision.disposition, PersonResolutionDisposition.AUTO_MATCH)

    def test_functional_mailbox_same_name_is_review_not_auto_match(self):
        decision = resolve_person_pair(
            record(
                "a",
                name="Ana Costa",
                professional_email="presidencia@example.org",
            ),
            record(
                "b",
                name="Ana Costa",
                professional_email="presidencia@example.org",
            ),
        )
        self.assertEqual(decision.disposition, PersonResolutionDisposition.REVIEW)

    def test_same_name_same_location_only_is_insufficient(self):
        decision = resolve_person_pair(
            record("a", name="Carlos Souza", location="São Paulo"),
            record("b", name="Carlos Souza", location="Sao Paulo"),
        )
        self.assertEqual(
            decision.disposition,
            PersonResolutionDisposition.INSUFFICIENT_EVIDENCE,
        )

    def test_cross_company_same_name_role_is_review_not_auto_match(self):
        decision = resolve_person_pair(
            record("a", name="Maria Lima", company_id="c1", role="CFO"),
            record("b", name="Maria Lima", company_id="c2", role="CFO"),
        )
        self.assertEqual(decision.disposition, PersonResolutionDisposition.REVIEW)

    def test_curated_benchmark_has_zero_false_auto_merges(self):
        pairs = (
            LabeledPersonPair(
                "p1",
                record(
                    "1",
                    name="Ana Costa",
                    profile_url="https://linkedin.com/in/ana",
                    profile_is_person_unique=True,
                ),
                record(
                    "2",
                    name="Ana Costa",
                    profile_url="https://linkedin.com/in/ana/",
                    profile_is_person_unique=True,
                ),
                True,
                "same_person_unique_profile",
            ),
            LabeledPersonPair(
                "p2",
                record(
                    "3",
                    name="João Lima",
                    professional_email="joao@acme.com",
                    professional_email_is_person_unique=True,
                ),
                record(
                    "4",
                    name="Joao Lima",
                    professional_email="JOAO@ACME.COM",
                    professional_email_is_person_unique=True,
                ),
                True,
                "same_person_unique_email",
            ),
            LabeledPersonPair(
                "p3",
                record("5", name="Carlos Reis", company_id="c1", role="Diretor"),
                record("6", name="Carlos Reis", company_id="c1", role="Diretor"),
                True,
                "same_context",
            ),
            LabeledPersonPair(
                "n1",
                record(
                    "7",
                    name="Maria Souza",
                    profile_url="https://example.org/curriculos",
                ),
                record(
                    "8",
                    name="Maria Souza",
                    profile_url="https://example.org/curriculos",
                ),
                False,
                "shared_profile_same_name_false_friend",
            ),
            LabeledPersonPair(
                "n2",
                record(
                    "9",
                    name="Pedro Alves",
                    professional_email="financeiro@acme.com",
                ),
                record(
                    "10",
                    name="Pedro Alves",
                    professional_email="financeiro@acme.com",
                ),
                False,
                "functional_email_same_name_false_friend",
            ),
            LabeledPersonPair(
                "n3",
                record("11", name="Bruno Dias", professional_email="financeiro@acme.com"),
                record("12", name="Clara Dias", professional_email="financeiro@acme.com"),
                False,
                "shared_role_email_different_names",
            ),
            LabeledPersonPair(
                "n4",
                record("13", name="Rita Melo", profile_url="https://linkedin.com/company/acme"),
                record("14", name="Outra Pessoa", profile_url="https://linkedin.com/company/acme"),
                False,
                "shared_company_profile_different_names",
            ),
            LabeledPersonPair(
                "p4",
                record("15", name="Lucas Maia", company_id="c1", role="Analista"),
                record("16", name="Lucas Maia", company_id="c2", role="Analista"),
                True,
                "job_change_same_role",
            ),
        )
        metrics = evaluate_person_resolution(pairs)
        self.assertEqual(metrics.auto_false, 0)
        self.assertEqual(metrics.auto_true, 2)
        self.assertGreaterEqual(metrics.review_true, 2)


if __name__ == "__main__":
    unittest.main()
