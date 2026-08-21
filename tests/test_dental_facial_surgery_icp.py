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
    OfferFormat,
    DEFAULT_DENTAL_FACIAL_SURGERY_ICP_V1,
    brazil_region_for_state,
    classify_dental_title,
    qualify_dental_person,
    select_dental_icp,
    signals_from_existing_evidence,
)

P = "person-1"
C = "company-1"


def sig(sid, kind, value, *evidence_ids):
    return DentalICPSignal(
        sid,
        P,
        kind,
        value,
        evidence_ids or ("ev-1",),
        C,
    )


class DentalICPV1Tests(unittest.TestCase):
    def test_business_icp_is_brazil_wide_by_default_and_combines_formats(self):
        icp = DEFAULT_DENTAL_FACIAL_SURGERY_ICP_V1
        self.assertEqual(icp.country, "BR")
        self.assertEqual(icp.selection.regions, ())
        self.assertEqual(icp.selection.states, ())
        self.assertEqual(
            set(icp.core_procedures),
            {"blefaroplastia", "lip lift", "lifting facial", "frontoplastia"},
        )
        self.assertEqual(set(icp.offer_formats), set(OfferFormat))
        self.assertTrue(icp.decision_basis.startswith("BUSINESS_REQUIREMENT"))

    def test_region_mapping_covers_user_selectable_brazil_regions(self):
        self.assertEqual(brazil_region_for_state("SP"), BrazilRegion.SOUTHEAST)
        self.assertEqual(brazil_region_for_state("BA"), BrazilRegion.NORTHEAST)
        self.assertEqual(brazil_region_for_state("AM"), BrazilRegion.NORTH)
        self.assertEqual(brazil_region_for_state("DF"), BrazilRegion.CENTRAL_WEST)
        self.assertEqual(brazil_region_for_state("RS"), BrazilRegion.SOUTH)

    def test_title_classification_supports_generalist_bucomax_hof_and_other_specialty(self):
        self.assertEqual(
            classify_dental_title("Cirurgião-Dentista"),
            DentalTitleGroup.GENERAL_DENTIST,
        )
        self.assertEqual(
            classify_dental_title("Cirurgião Bucomaxilofacial"),
            DentalTitleGroup.BUCOMAXILLOFACIAL,
        )
        self.assertEqual(
            classify_dental_title("Especialista em Harmonização Orofacial"),
            DentalTitleGroup.HOF,
        )
        self.assertEqual(
            classify_dental_title("Implantodontista"),
            DentalTitleGroup.OTHER_DENTAL_SPECIALTY,
        )

    def test_general_dentist_is_eligible_with_medium_fit_and_unknown_intent(self):
        result = qualify_dental_person(
            P,
            [sig("t", DentalSignalKind.PROFESSIONAL_TITLE, "Cirurgião-Dentista")],
            company_id=C,
        )
        self.assertEqual(result.status, LeadStatus.QUALIFIED)
        self.assertEqual(result.fit, FitLevel.MEDIUM)
        self.assertEqual(result.intent, IntentLevel.UNKNOWN)
        self.assertEqual(result.priority, LeadPriority.P3)

    def test_bucomax_is_high_fit_without_inventing_intent(self):
        result = qualify_dental_person(
            P,
            [sig("t", DentalSignalKind.PROFESSIONAL_TITLE, "Cirurgião Bucomaxilofacial")],
            company_id=C,
        )
        self.assertEqual(result.fit, FitLevel.HIGH)
        self.assertEqual(result.intent, IntentLevel.UNKNOWN)
        self.assertEqual(result.priority, LeadPriority.P2)

    def test_hof_is_high_fit(self):
        result = qualify_dental_person(
            P,
            [sig("t", DentalSignalKind.SPECIALTY, "Harmonização Orofacial")],
            company_id=C,
        )
        self.assertEqual(result.fit, FitLevel.HIGH)
        self.assertEqual(result.status, LeadStatus.QUALIFIED)

    def test_general_dentist_with_core_procedure_signal_becomes_high_fit(self):
        result = qualify_dental_person(
            P,
            [
                sig("t", DentalSignalKind.PROFESSIONAL_TITLE, "Dentista"),
                sig("p", DentalSignalKind.PROCEDURE, "Blefaroplastia e estética facial"),
            ],
            company_id=C,
        )
        self.assertEqual(result.fit, FitLevel.HIGH)

    def test_high_fit_and_explicit_course_interest_is_p1(self):
        result = qualify_dental_person(
            P,
            [
                sig("t", DentalSignalKind.PROFESSIONAL_TITLE, "Bucomaxilofacial"),
                sig("i", DentalSignalKind.LEARNING_INTENT, DentalIntentSignal.COURSE_INTEREST),
            ],
            company_id=C,
        )
        self.assertEqual(
            (result.fit, result.intent, result.priority),
            (FitLevel.HIGH, IntentLevel.HIGH, LeadPriority.P1),
        )

    def test_continuing_education_is_medium_intent(self):
        result = qualify_dental_person(
            P,
            [
                sig("t", DentalSignalKind.PROFESSIONAL_TITLE, "Dentista"),
                sig(
                    "i",
                    DentalSignalKind.LEARNING_INTENT,
                    DentalIntentSignal.CONTINUING_EDUCATION,
                ),
            ],
            company_id=C,
        )
        self.assertEqual(result.intent, IntentLevel.MEDIUM)

    def test_absence_of_intent_never_means_low_intent(self):
        result = qualify_dental_person(
            P,
            [sig("t", DentalSignalKind.PROFESSIONAL_TITLE, "Dentista")],
            company_id=C,
        )
        self.assertEqual(result.intent, IntentLevel.UNKNOWN)

    def test_region_filter_excludes_known_out_of_region_profile(self):
        icp = select_dental_icp(regions=(BrazilRegion.SOUTH,))
        result = qualify_dental_person(
            P,
            [
                sig("t", DentalSignalKind.PROFESSIONAL_TITLE, "Dentista"),
                sig("s", DentalSignalKind.STATE, "SP"),
            ],
            company_id=C,
            icp=icp,
        )
        self.assertEqual(
            (result.fit, result.status, result.priority),
            (FitLevel.LOW, LeadStatus.NOT_QUALIFIED, LeadPriority.EXCLUDE),
        )

    def test_region_filter_with_missing_state_is_unknown_not_rejected(self):
        icp = select_dental_icp(regions=(BrazilRegion.SOUTH,))
        result = qualify_dental_person(
            P,
            [sig("t", DentalSignalKind.PROFESSIONAL_TITLE, "Dentista")],
            company_id=C,
            icp=icp,
        )
        self.assertEqual(
            (result.fit, result.status, result.priority),
            (FitLevel.UNKNOWN, LeadStatus.UNKNOWN, LeadPriority.REVIEW),
        )

    def test_state_filter_is_configurable(self):
        icp = select_dental_icp(states=("sp", "rj"))
        self.assertEqual(icp.selection.states, ("SP", "RJ"))
        result = qualify_dental_person(
            P,
            [
                sig("t", DentalSignalKind.PROFESSIONAL_TITLE, "Dentista"),
                sig("s", DentalSignalKind.STATE, "RJ"),
            ],
            company_id=C,
            icp=icp,
        )
        self.assertEqual(result.status, LeadStatus.QUALIFIED)

    def test_title_group_filter_can_select_only_bucomax(self):
        icp = select_dental_icp(title_groups=(DentalTitleGroup.BUCOMAXILLOFACIAL,))
        result = qualify_dental_person(
            P,
            [sig("t", DentalSignalKind.PROFESSIONAL_TITLE, "Dentista")],
            company_id=C,
            icp=icp,
        )
        self.assertEqual(result.status, LeadStatus.NOT_QUALIFIED)

    def test_title_term_filter_can_select_specific_title_text(self):
        icp = select_dental_icp(title_terms=("bucomax",))
        yes = qualify_dental_person(
            P,
            [sig("t", DentalSignalKind.PROFESSIONAL_TITLE, "Cirurgião Bucomaxilofacial")],
            company_id=C,
            icp=icp,
        )
        no = qualify_dental_person(
            P,
            [sig("t", DentalSignalKind.PROFESSIONAL_TITLE, "Dentista")],
            company_id=C,
            icp=icp,
        )
        self.assertEqual(yes.status, LeadStatus.QUALIFIED)
        self.assertEqual(no.status, LeadStatus.NOT_QUALIFIED)

    def test_validated_contact_can_be_required_as_runtime_selection(self):
        icp = select_dental_icp(require_validated_contact=True)
        blocked = qualify_dental_person(
            P,
            [sig("t", DentalSignalKind.PROFESSIONAL_TITLE, "Dentista")],
            company_id=C,
            icp=icp,
        )
        allowed = qualify_dental_person(
            P,
            [
                sig("t", DentalSignalKind.PROFESSIONAL_TITLE, "Dentista"),
                sig("c", DentalSignalKind.VALIDATED_CONTACT, "EMAIL"),
            ],
            company_id=C,
            icp=icp,
        )
        self.assertEqual(blocked.status, LeadStatus.NOT_QUALIFIED)
        self.assertTrue(allowed.has_validated_contact)
        self.assertEqual(allowed.status, LeadStatus.QUALIFIED)

    def test_bridge_projects_existing_role_geography_and_contacts_without_inventing_intent(self):
        provenance = Provenance(("ev-role",), "test_dental_icp")
        role = ProfessionalRole("r1", P, C, "Cirurgião-Dentista", provenance)
        state = CanonicalFact(
            "f1",
            EntityRef(EntityType.COMPANY, C),
            "state",
            "SP",
            ("candidate-state",),
            provenance,
        )
        contact = ContactPoint(
            "c1",
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
        kinds = {signal.kind for signal in signals}
        self.assertIn(DentalSignalKind.PROFESSIONAL_TITLE, kinds)
        self.assertIn(DentalSignalKind.STATE, kinds)
        self.assertIn(DentalSignalKind.VALIDATED_CONTACT, kinds)
        self.assertNotIn(DentalSignalKind.LEARNING_INTENT, kinds)

    def test_result_preserves_signal_and_evidence_ids_for_audit(self):
        result = qualify_dental_person(
            P,
            [
                sig("a", DentalSignalKind.PROFESSIONAL_TITLE, "Dentista", "ev-a"),
                sig("b", DentalSignalKind.PROCEDURE, "Lip Lift", "ev-b"),
            ],
            company_id=C,
        )
        self.assertEqual(result.signal_ids, ("a", "b"))
        self.assertEqual(result.evidence_ids, ("ev-a", "ev-b"))

    def test_invalid_state_filter_is_rejected(self):
        with self.assertRaises(ValueError):
            select_dental_icp(states=("XX",))


if __name__ == "__main__":
    unittest.main()
