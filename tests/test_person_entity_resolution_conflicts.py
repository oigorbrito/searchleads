import unittest

from searchleads.person_entity_resolution import (
    PersonRecord,
    PersonResolutionDisposition,
    resolve_person_pair,
)


def record(record_id: str, **kwargs) -> PersonRecord:
    return PersonRecord(record_id, **kwargs)


class PersonEntityResolutionConflictTests(unittest.TestCase):
    def test_matching_unique_profile_does_not_override_conflicting_unique_email(self):
        left = record(
            "a",
            name="Ana Costa",
            profile_url="https://linkedin.com/in/ana",
            profile_is_person_unique=True,
            professional_email="ana@acme.com",
            professional_email_is_person_unique=True,
        )
        right = record(
            "b",
            name="Ana Costa",
            profile_url="https://linkedin.com/in/ana/",
            profile_is_person_unique=True,
            professional_email="outra@acme.com",
            professional_email_is_person_unique=True,
        )
        decision = resolve_person_pair(left, right)
        self.assertEqual(decision.disposition, PersonResolutionDisposition.REVIEW)
        self.assertIn("professional_email_unique_conflict", decision.reasons)

    def test_matching_unique_email_does_not_override_conflicting_unique_profile(self):
        left = record(
            "a",
            name="Ana Costa",
            profile_url="https://linkedin.com/in/ana",
            profile_is_person_unique=True,
            professional_email="ana@acme.com",
            professional_email_is_person_unique=True,
        )
        right = record(
            "b",
            name="Ana Costa",
            profile_url="https://linkedin.com/in/ana-costa",
            profile_is_person_unique=True,
            professional_email="ANA@ACME.COM",
            professional_email_is_person_unique=True,
        )
        decision = resolve_person_pair(left, right)
        self.assertEqual(decision.disposition, PersonResolutionDisposition.REVIEW)
        self.assertIn("profile_unique_conflict", decision.reasons)

    def test_two_agreeing_unique_signals_can_auto_match(self):
        left = record(
            "a",
            name="Ana Costa",
            profile_url="https://linkedin.com/in/ana",
            profile_is_person_unique=True,
            professional_email="ana@acme.com",
            professional_email_is_person_unique=True,
        )
        right = record(
            "b",
            name="Ana Costa",
            profile_url="https://LINKEDIN.com/in/ana/",
            profile_is_person_unique=True,
            professional_email="ANA@ACME.COM",
            professional_email_is_person_unique=True,
        )
        decision = resolve_person_pair(left, right)
        self.assertEqual(decision.disposition, PersonResolutionDisposition.AUTO_MATCH)


if __name__ == "__main__":
    unittest.main()
