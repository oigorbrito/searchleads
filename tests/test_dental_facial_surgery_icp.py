from __future__ import annotations

import unittest

from searchleads.domain import (
    CanonicalFact,
    ContactKind,
    ContactPoint,
    ContactStatus,
    EntityRef,
    EntityType,
    LeadStatus,
    ProfessionalRole,
    Provenance,
)
from searchleads.dental_facial_surgery_icp import (
    BrazilRegion,
    DentalICPSignal,
    DentalIntentSignal,
    DentalSignalKind,
    DentalTitleGroup,
    FitLevel,
    IntentLevel,
    LeadPriority,
    DEFAULT_DENTAL_FACIAL_SURGERY_ICP_V1,
    qualify_dental_person,
    select_dental_icp,
    signals_from_existing_evidence,
)
from searchleads.dental_regulatory import (
    DentalOfferTrack,
    RegulatoryEligibility,
    qualify_dental_person_for_offer,
)
from searchleads.dental_person_lead import lead_from_dental_offer_qualification

P = "person-1"
C = "company-1"


def sig(sid, kind, value, evidence_id="ev-1"):
    return DentalICPSignal(sid, P, kind, value, (evidence_id,), C)


class DentalICPMVPTests(unittest.TestCase):
    def test_default_icp_is_brazil_wide_and_contains_core_procedures(self):
        icp = DEFAULT_DENTAL_FACIAL_SURGERY_ICP_V1
        self.assertEqual(icp.country, "BR")
        self.assertEqual(icp.selection.regions, ())
        self.assertEqual(icp.selection.states, ())
        self.assertEqual(
            set(icp.core_procedures),
            {"blefaroplastia", "lip lift", "lifting facial", "frontoplastia"},
        )

    def test_general_dentist_is_eligible_without_inventing_intent(self):
        result = qualify_dental_person(
            P,
            [sig("title", DentalSignalKind.PROFESSIONAL_TITLE, "Cirurgião-Dentista")],
            company_id=C,
        )
        self.assertEqual(result.status, LeadStatus.QUALIFIED)
        self.assertEqual(result.fit, FitLevel.MEDIUM)
        self.assertEqual(result.intent, IntentLevel.UNKNOWN)

    def test_general_dentist_with_facial_procedure_signal_is_high_fit(self):
        result = qualify_dental_person(
            P,
            [
                sig("title", DentalSignalKind.PROFESSIONAL_TITLE, "Dentista"),
                sig("procedure", DentalSignalKind.PROCEDURE, "Blefaroplastia e estética facial", "ev-procedure"),
            ],
            company_id=C,
        )
        self.assertEqual(result.fit, FitLevel.HIGH)

    def test_bucomax_with_explicit_course_interest_is_top_priority(self):
        result = qualify_dental_person(
            P,
            [
                sig("title", DentalSignalKind.PROFESSIONAL_TITLE, "Cirurgião Bucomaxilofacial"),
                sig("intent", DentalSignalKind.LEARNING_INTENT, DentalIntentSignal.COURSE_INTEREST, "ev-intent"),
            ],
            company_id=C,
        )
        self.assertEqual(result.status, LeadStatus.QUALIFIED)
        self.assertEqual(result.fit, FitLevel.HIGH)
        self.assertEqual(result.intent, IntentLevel.HIGH)
        self.assertEqual(result.priority, LeadPriority.P1)

    def test_region_filter_excludes_known_out_of_region_and_keeps_missing_as_unknown(self):
        icp = select_dental_icp(regions=(BrazilRegion.SOUTH,))
        excluded = qualify_dental_person(
            P,
            [
                sig("title", DentalSignalKind.PROFESSIONAL_TITLE, "Dentista"),
                sig("state", DentalSignalKind.STATE, "SP"),
            ],
            company_id=C,
            icp=icp,
        )
        unknown = qualify_dental_person(
            P,
            [sig("title", DentalSignalKind.PROFESSIONAL_TITLE, "Dentista")],
            company_id=C,
            icp=icp,
        )
        self.assertEqual(excluded.status, LeadStatus.NOT_QUALIFIED)
        self.assertEqual(excluded.priority, LeadPriority.EXCLUDE)
        self.assertEqual(unknown.status, LeadStatus.UNKNOWN)
        self.assertEqual(unknown.priority, LeadPriority.REVIEW)

    def test_title_filter_can_select_only_bucomax(self):
        icp = select_dental_icp(title_groups=(DentalTitleGroup.BUCOMAXILLOFACIAL,))
        generalist = qualify_dental_person(
            P,
            [sig("title", DentalSignalKind.PROFESSIONAL_TITLE, "Dentista")],
            company_id=C,
            icp=icp,
        )
        bucomax = qualify_dental_person(
            P,
            [sig("title", DentalSignalKind.PROFESSIONAL_TITLE, "Bucomaxilofacial")],
            company_id=C,
            icp=icp,
        )
        self.assertEqual(generalist.status, LeadStatus.NOT_QUALIFIED)
        self.assertEqual(bucomax.status, LeadStatus.QUALIFIED)

    def test_existing_evidence_bridge_does_not_create_learning_intent(self):
        provenance = Provenance(("ev-role",), "mvp-test")
        role = ProfessionalRole("role-1", P, C, "Cirurgião-Dentista", provenance)
        state = CanonicalFact(
            "state-1",
            EntityRef(EntityType.COMPANY, C),
            "state",
            "SP",
            ("candidate-state",),
            provenance,
        )
        contact = ContactPoint(
            "contact-1",
            EntityRef(EntityType.COMPANY, C),
            ContactKind.EMAIL,
            "clinic@example.com",
            provenance,
            ContactStatus.VALIDATED,
        )
        signals = signals_from_existing_evidence(
            P,
            company_id=C,
            roles=(role,),
            contacts=(contact,),
            canonical_facts=(state,),
        )
        kinds = {item.kind for item in signals}
        self.assertIn(DentalSignalKind.PROFESSIONAL_TITLE, kinds)
        self.assertIn(DentalSignalKind.STATE, kinds)
        self.assertIn(DentalSignalKind.VALIDATED_CONTACT, kinds)
        self.assertNotIn(DentalSignalKind.LEARNING_INTENT, kinds)

    def test_offer_track_keeps_generalist_for_specialization_but_gates_exclusive_short_course(self):
        generalist_signals = [
            sig("title", DentalSignalKind.PROFESSIONAL_TITLE, "Cirurgião-Dentista")
        ]
        formation = qualify_dental_person_for_offer(
            P,
            generalist_signals,
            company_id=C,
            offer_track=DentalOfferTrack.CEOF_SPECIALIZATION,
        )
        short_course = qualify_dental_person_for_offer(
            P,
            generalist_signals,
            company_id=C,
            offer_track=DentalOfferTrack.COMPLEMENTARY_EXCLUSIVE_CEOF,
        )
        ceof = qualify_dental_person_for_offer(
            P,
            [sig("ceof", DentalSignalKind.SPECIALTY, "Especialista em Cirurgia Estética Orofacial (CEOF)")],
            company_id=C,
            offer_track=DentalOfferTrack.COMPLEMENTARY_EXCLUSIVE_CEOF,
        )
        self.assertEqual(formation.regulatory_eligibility, RegulatoryEligibility.ELIGIBLE)
        self.assertEqual(short_course.status, LeadStatus.NOT_QUALIFIED)
        self.assertEqual(short_course.priority, LeadPriority.EXCLUDE)
        self.assertEqual(ceof.regulatory_eligibility, RegulatoryEligibility.ELIGIBLE)
        lead = lead_from_dental_offer_qualification(ceof)
        self.assertEqual(lead.metadata["primary_commercial_entity"], "PERSON")
        self.assertEqual(lead.metadata["offer_track"], "COMPLEMENTARY_EXCLUSIVE_CEOF")
        self.assertEqual(lead.metadata["regulatory_eligibility"], "ELIGIBLE")


if __name__ == "__main__":
    unittest.main()
