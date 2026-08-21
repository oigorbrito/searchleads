from __future__ import annotations
import unittest
from datetime import datetime, timezone

from searchleads.domain import CandidateFact, EntityRef, EntityType, Provenance
from searchleads.field_fusion import FusionStatus
from searchleads.qualification_field_canonicalization import canonicalize_selected_company_fields

NOW=datetime(2026,8,21,17,0,tzinfo=timezone.utc)
SUBJECT=EntityRef(EntityType.COMPANY,'company-1')

def fact(fid,predicate,raw,eid,normalized=None):
    return CandidateFact(
        candidate_fact_id=fid,
        subject=SUBJECT,
        predicate=predicate,
        raw_value=raw,
        provenance=Provenance((eid,),'test_extract',generated_at=NOW),
        normalized_value=normalized,
        normalization_rule='test_norm_v1' if normalized is not None else None,
    )

class QualificationFieldCanonicalizationTests(unittest.TestCase):
    def test_single_cnae_candidate_becomes_canonical_under_existing_fusion_rule(self):
        source=fact('cf-1','primary_cnae_code',6204000,'ev-1',normalized='6204000')
        result=canonicalize_selected_company_fields((source,),('primary_cnae_code',))
        self.assertEqual(len(result.canonical_facts),1)
        self.assertEqual(result.canonical_facts[0].value,'6204000')
        self.assertEqual(result.conflicts,())
        self.assertEqual(source.raw_value,6204000)

    def test_two_agreeing_registration_status_candidates_canonicalize(self):
        result=canonicalize_selected_company_fields((
            fact('cf-1','registration_status','ATIVA','ev-1'),
            fact('cf-2','registration_status','ATIVA','ev-2'),
        ),('registration_status',))
        self.assertEqual(result.canonical_facts[0].value,'ATIVA')
        self.assertEqual(result.canonical_facts[0].provenance.evidence_ids,('ev-1','ev-2'))

    def test_disagreement_remains_conflict(self):
        result=canonicalize_selected_company_fields((
            fact('cf-1','registration_status','ATIVA','ev-1'),
            fact('cf-2','registration_status','BAIXADA','ev-2'),
        ),('registration_status',))
        self.assertEqual(result.canonical_facts,())
        self.assertEqual(len(result.conflicts),1)
        self.assertEqual(result.conflicts[0].status.value,'OPEN')

    def test_only_explicit_predicates_are_processed(self):
        result=canonicalize_selected_company_fields((
            fact('cf-1','primary_cnae_code','6204000','ev-1'),
            fact('cf-2','legal_name','ACME','ev-2'),
        ),('primary_cnae_code',))
        self.assertEqual(tuple(f.predicate for f in result.canonical_facts),('primary_cnae_code',))

    def test_missing_requested_predicate_is_reported(self):
        result=canonicalize_selected_company_fields((fact('cf-1','state','DF','ev-1'),),('primary_cnae_code',))
        self.assertEqual(result.missing_predicates,('primary_cnae_code',))
        self.assertEqual(result.canonical_facts,())

    def test_duplicate_requested_predicates_are_deduplicated_preserving_order(self):
        result=canonicalize_selected_company_fields((fact('cf-1','state','DF','ev-1'),),('state','state'))
        self.assertEqual(result.requested_predicates,('state',))

    def test_empty_predicate_selection_is_rejected(self):
        with self.assertRaises(ValueError):
            canonicalize_selected_company_fields((),())

if __name__=='__main__': unittest.main()
