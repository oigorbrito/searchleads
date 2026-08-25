from __future__ import annotations
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src')); sys.path.insert(0,str(ROOT/'tests'))
from test_lead_export import base_bundle
from dataclasses import replace
from searchleads.domain import Lead, Person
from searchleads.lead_export import to_export_dict
CASES=json.loads((ROOT/'tests'/'fixtures'/'lead_export_v1.json').read_text())

def valid(name):
    b=base_bundle()
    if name=='coherent_full_bundle': return b
    if name=='company_without_lead': return replace(b,lead=None)
    if name=='input_order_changed': return replace(b,candidate_facts=tuple(reversed(b.candidate_facts)))
    if name=='cross_company_lead': return replace(b,lead=replace(b.lead,company_id='other'))
    if name=='person_other_company': return replace(b,people=(replace(b.people[0],company_id='other'),))
    if name=='missing_relationship_evidence': return replace(b,people=(replace(b.people[0],relationship_evidence_ids=('missing',)),))
    if name=='contact_outside_owner': return replace(b,contacts=(replace(b.contacts[0],owner_id='missing'),))
    if name=='candidate_missing_provenance': return replace(b,candidate_facts=(replace(b.candidate_facts[0],provenance_id='missing'),)+b.candidate_facts[1:])
    if name=='candidate_provenance_mismatch':
        p=replace(b.provenances[0],field_name='other'); return replace(b,provenances=(p,)+b.provenances[1:])
    if name=='canonical_missing_candidate': return replace(b,canonical_facts=(replace(b.canonical_facts[0],candidate_fact_ids=('missing',)),))
    if name=='conflict_field_mismatch':
        f=replace(b.candidate_facts[1],field_name='other'); return replace(b,candidate_facts=(b.candidate_facts[0],f)+b.candidate_facts[2:])
    if name=='provenance_missing_evidence':
        p=replace(b.provenances[0],evidence_ids=('missing',)); return replace(b,provenances=(p,)+b.provenances[1:])
    if name=='evidence_missing_source': return replace(b,evidence=(replace(b.evidence[0],source_id='missing'),)+b.evidence[1:])
    if name=='review_missing_evidence': return replace(b,review_items=(replace(b.review_items[0],evidence_ids=('missing',)),))
    if name=='duplicate_contact_id': return replace(b,contacts=b.contacts+b.contacts)
    raise ValueError(name)

def main():
    tp=fp=tn=fn=0
    for case in CASES:
        try: to_export_dict(valid(case['name'])); pred=True
        except (ValueError,TypeError): pred=False
        truth=case['expected']
        if pred and truth: tp+=1
        elif pred: fp+=1
        elif truth: fn+=1
        else: tn+=1
    print(f'scenarios={len(CASES)} accepted_coherent={tp} false_accept={fp} rejected_incoherent={tn} false_reject={fn}')
    print(f'integrity_accept_precision={tp/(tp+fp):.3f} integrity_reject_specificity={tn/(tn+fp):.3f}')
if __name__=='__main__': main()
