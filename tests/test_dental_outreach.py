from __future__ import annotations

import unittest

from searchleads.dental_facial_surgery_icp import DentalICPSignal, DentalSignalKind
from searchleads.dental_outreach import (
    CFOProfessionalVerification,
    CFORegistrationState,
    CampaignLegalStatus,
    OutreachReadiness,
    evaluate_dental_outreach_readiness,
)
from searchleads.dental_regulatory import DentalOfferTrack, qualify_dental_person_for_offer

P = "person-1"
C = "clinic-1"


def sig(sid, kind, value):
    return DentalICPSignal(sid, P, kind, value, (f"ev-{sid}",), C)


class DentalOutreachMVPTests(unittest.TestCase):
    def test_unknown_intent_is_eligible_but_current_legal_review_blocks_ready_by_default(self):
        qualification = qualify_dental_person_for_offer(
            P,
            (
                sig("title", DentalSignalKind.PROFESSIONAL_TITLE, "Cirurgião-Dentista"),
                sig("contact", DentalSignalKind.DISCOVERED_CONTACT, "WHATSAPP"),
            ),
            company_id=C,
            offer_track=DentalOfferTrack.CEOF_SPECIALIZATION,
        )
        verification = CFOProfessionalVerification(
            P,
            CFORegistrationState.VERIFIED_ACTIVE,
            "SP",
            "12345",
            (),
            "ev-cfo",
        )
        pending = evaluate_dental_outreach_readiness(qualification, verification)
        confirmed = evaluate_dental_outreach_readiness(
            qualification,
            verification,
            campaign_legal_status=CampaignLegalStatus.CONFIRMED_FOR_OUTREACH,
        )
        self.assertEqual(pending.readiness, OutreachReadiness.REVIEW)
        self.assertEqual(confirmed.readiness, OutreachReadiness.READY)
        self.assertEqual(qualification.base.intent.value, "UNKNOWN")

    def test_complementary_exclusive_track_requires_ceof_in_official_specialties(self):
        qualification = qualify_dental_person_for_offer(
            P,
            (
                sig("title", DentalSignalKind.PROFESSIONAL_TITLE, "Especialista CEOF"),
                sig("contact", DentalSignalKind.VALIDATED_CONTACT, "EMAIL"),
            ),
            company_id=C,
            offer_track=DentalOfferTrack.COMPLEMENTARY_EXCLUSIVE_CEOF,
        )
        verification = CFOProfessionalVerification(
            P,
            CFORegistrationState.VERIFIED_ACTIVE,
            "RJ",
            "54321",
            ("Harmonização Orofacial",),
            "ev-cfo",
        )
        decision = evaluate_dental_outreach_readiness(
            qualification,
            verification,
            campaign_legal_status=CampaignLegalStatus.CONFIRMED_FOR_OUTREACH,
        )
        self.assertEqual(decision.readiness, OutreachReadiness.EXCLUDE)


if __name__ == "__main__":
    unittest.main()
