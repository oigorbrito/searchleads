import unittest
from datetime import datetime, timezone
from searchleads.domain import CanonicalFact, ContactKind, ContactPoint, ContactStatus, EntityRef, EntityType, LeadStatus, ProfessionalRole, Provenance
from searchleads.qualification import CriterionOperator, QualificationCriterion, QualificationPolicy, qualify_company
from searchleads.qualification_signals import inputs_from_evidence, qualify_company_inputs

NOW=datetime(2026,8,21,17,0,tzinfo=timezone.utc)
COMPANY_ID='company-1'
OWNER=EntityRef(EntityType.COMPANY,COMPANY_ID)
PROV=Provenance(('ev-1',),'test',generated_at=NOW)

class QualificationSignalTests(unittest.TestCase):
    def test_negative_operator_on_canonical_fact(self):
        fact=CanonicalFact('cf',OWNER,'state','DF',('candidate-1',),PROV)
        policy=QualificationPolicy('p',(QualificationCriterion('x','state',CriterionOperator.NE,'SP'),))
        self.assertEqual(qualify_company(COMPANY_ID,(fact,),policy).status,LeadStatus.QUALIFIED)

    def test_not_exists_can_qualify_on_absence(self):
        policy=QualificationPolicy('p',(QualificationCriterion('x','blocked_signal',CriterionOperator.NOT_EXISTS),))
        self.assertEqual(qualify_company(COMPANY_ID,(),policy).status,LeadStatus.QUALIFIED)

    def test_role_becomes_typed_signal(self):
        role=ProfessionalRole('r','person-1',COMPANY_ID,'Diretor-Presidente',PROV)
        inputs=inputs_from_evidence(COMPANY_ID,roles=(role,))
        self.assertEqual(inputs[0].predicate,'professional_role_title')
        policy=QualificationPolicy('p',(QualificationCriterion('x','professional_role_title',CriterionOperator.CONTAINS,'Diretor'),))
        result=qualify_company_inputs(COMPANY_ID,inputs,policy)
        self.assertEqual(result.status,LeadStatus.QUALIFIED)
        self.assertEqual(result.qualification_input_ids,('r',))

    def test_multiple_roles_use_any_for_positive_match(self):
        roles=(ProfessionalRole('r1','p1',COMPANY_ID,'Analista',PROV),ProfessionalRole('r2','p2',COMPANY_ID,'Diretor Comercial',PROV))
        policy=QualificationPolicy('p',(QualificationCriterion('x','professional_role_title',CriterionOperator.CONTAINS,'Diretor'),))
        self.assertEqual(qualify_company_inputs(COMPANY_ID,inputs_from_evidence(COMPANY_ID,roles=roles),policy).status,LeadStatus.QUALIFIED)

    def test_validated_contact_kind_becomes_signal(self):
        contact=ContactPoint('ct',OWNER,ContactKind.EMAIL,'x@example.com',PROV,ContactStatus.VALIDATED)
        inputs=inputs_from_evidence(COMPANY_ID,contacts=(contact,))
        policy=QualificationPolicy('p',(QualificationCriterion('x','validated_contact_kind',CriterionOperator.EQ,'EMAIL'),))
        self.assertEqual(qualify_company_inputs(COMPANY_ID,inputs,policy).status,LeadStatus.QUALIFIED)

    def test_discovered_contact_is_not_qualification_input(self):
        contact=ContactPoint('ct',OWNER,ContactKind.EMAIL,'x@example.com',PROV,ContactStatus.DISCOVERED)
        self.assertEqual(inputs_from_evidence(COMPANY_ID,contacts=(contact,)),())

    def test_contact_signal_preserves_evidence(self):
        prov=Provenance(('ev-a','ev-b'),'test',generated_at=NOW)
        contact=ContactPoint('ct',OWNER,ContactKind.PHONE,'0800',prov,ContactStatus.VALIDATED)
        items=inputs_from_evidence(COMPANY_ID,contacts=(contact,))
        self.assertTrue(all(i.evidence_ids==('ev-a','ev-b') for i in items))

    def test_negative_multi_value_requires_all_values_outside_exclusion(self):
        roles=(ProfessionalRole('r1','p1',COMPANY_ID,'Analista',PROV),ProfessionalRole('r2','p2',COMPANY_ID,'Estagiário',PROV))
        policy=QualificationPolicy('p',(QualificationCriterion('x','professional_role_title',CriterionOperator.NOT_IN,('Estagiário',)),))
        self.assertEqual(qualify_company_inputs(COMPANY_ID,inputs_from_evidence(COMPANY_ID,roles=roles),policy).status,LeadStatus.NOT_QUALIFIED)

    def test_missing_positive_signal_is_unknown(self):
        policy=QualificationPolicy('p',(QualificationCriterion('x','professional_role_title',CriterionOperator.CONTAINS,'Diretor'),))
        self.assertEqual(qualify_company_inputs(COMPANY_ID,(),policy).status,LeadStatus.UNKNOWN)

    def test_no_policy_remains_unknown(self):
        self.assertEqual(qualify_company_inputs(COMPANY_ID,(),None).status,LeadStatus.UNKNOWN)

if __name__=='__main__': unittest.main()
