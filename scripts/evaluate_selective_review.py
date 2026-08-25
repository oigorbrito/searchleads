from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from searchleads.domain import Conflict, ConflictStatus, ContactKind, ContactPoint, ContactStatus, Lead, QualificationStatus
from searchleads.entity_resolution import CompanyRecord, ResolutionDisposition, TriageDecision
from searchleads.selective_review import review_company_match, review_conflict, review_contact, review_person_match, review_qualification
CASES=json.loads((ROOT/'tests'/'fixtures'/'selective_review_v1.json').read_text(encoding='utf-8'))
NOW=datetime(2026,8,25,17,0,tzinfo=timezone.utc)
def route(c):
    if c['type']=='company': return review_company_match(CompanyRecord('a'),CompanyRecord('b'),TriageDecision(ResolutionDisposition(c['state']),None,('domain_exact','name=0.900')))
    if c['type']=='person': return review_person_match('p1','p2','company','identity unresolved',('ev1','ev2') if c.get('more_evidence') else ('ev1',))
    if c['type']=='conflict':
        status=ConflictStatus(c['state']); selected='f1' if status is ConflictStatus.RESOLVED else None
        return review_conflict(Conflict('conf','company','legal_name',('f1','f2'),status,selected),high_impact=c.get('high_impact',False),evidence_ids=('ev1',))
    if c['type']=='contact': return review_contact(ContactPoint('ct','company',ContactKind.EMAIL,'x@example.com',('ev1',),ContactStatus(c['state']),NOW))
    if c['type']=='lead': return review_qualification(Lead('lead','company',qualification_status=QualificationStatus(c['state']),qualification_reasons=('ICP unresolved',)),high_value=c.get('high_value',False))
    raise ValueError(c['type'])
def main():
    tp=fp=tn=fn=high=0
    for c in CASES:
        item=route(c); pred=item is not None; truth=c['expected']
        if pred and truth: tp+=1
        elif pred: fp+=1
        elif truth: fn+=1
        else: tn+=1
        high += bool(item is not None and item.priority.value=='HIGH')
    precision=tp/(tp+fp) if tp+fp else 0.0; recall=tp/(tp+fn) if tp+fn else 0.0
    print(f'scenarios={len(CASES)} tp={tp} fp={fp} tn={tn} fn={fn} high_priority={high}')
    print(f'precision={precision:.3f} recall={recall:.3f} obvious_false_review={fp}/{tn+fp}')
if __name__=='__main__': main()
