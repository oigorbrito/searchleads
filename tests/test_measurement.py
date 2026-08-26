from dataclasses import replace
from datetime import datetime,timezone,timedelta
import json,pytest
from searchleads.domain import *
from searchleads.measurement.metrics import *
NOW=datetime(2026,8,26,5,0,tzinfo=timezone.utc)

def mv_avail(v): assert v.availability is MetricAvailability.AVAILABLE; return v.value

def test_metric_value_invariants_and_rate():
    with pytest.raises(ValueError): MetricValue(MetricAvailability.AVAILABLE,None)
    with pytest.raises(ValueError): MetricValue(MetricAvailability.UNAVAILABLE,None)
    with pytest.raises(ValueError): MetricValue.unavailable(' ')
    assert MetricValue.rate(1,2,zero_reason='x').value==.5
    assert MetricValue.rate(0,0,zero_reason='zero').reason=='zero'

def test_discovery_metrics_available_and_unavailable():
    m=compute_discovery_metrics(['a','a','b'])
    assert m.discovered_observations==3 and m.unique_entities==2 and mv_avail(m.duplicate_discovery_rate)==1/3
    assert m.bounded_coverage.availability is MetricAvailability.UNAVAILABLE and m.discovery_precision.availability is MetricAvailability.UNAVAILABLE
    m=compute_discovery_metrics(['a','b'],universe_entity_ids=['a','b','c'],true_relevant_entity_ids=['a'])
    assert mv_avail(m.bounded_coverage)==2/3 and mv_avail(m.discovery_precision)==.5

def test_discovery_zero_denominators_stay_unavailable():
    m=compute_discovery_metrics([],universe_entity_ids=[],true_relevant_entity_ids=[])
    assert all(x.availability is MetricAvailability.UNAVAILABLE for x in (m.duplicate_discovery_rate,m.bounded_coverage,m.discovery_precision))

def test_er_metrics_and_invalid_counts():
    m=compute_entity_resolution_metrics(8,2,10,2)
    assert mv_avail(m.precision)==.8 and mv_avail(m.recall)==.8 and round(mv_avail(m.f1),3)==.8
    assert mv_avail(m.false_merge_rate)==2/12 and mv_avail(m.false_split_rate)==.2
    with pytest.raises(ValueError): compute_entity_resolution_metrics(-1,0,0,0)

def test_er_f1_unavailable_when_no_signal():
    m=compute_entity_resolution_metrics(0,0,1,0)
    assert m.precision.availability is MetricAvailability.UNAVAILABLE and m.recall.availability is MetricAvailability.UNAVAILABLE and m.f1.availability is MetricAvailability.UNAVAILABLE
    m=compute_entity_resolution_metrics(0,1,1,1)
    assert m.f1.availability is MetricAvailability.UNAVAILABLE

def facts():
    c1=CandidateFact('cf1','s1','city','A','A',('e1',),'p1'); c2=CandidateFact('cf2','s1','state','SP','SP',('e2',),'p2')
    k1=CanonicalFact('k1','s1','city','A',('cf1',),'pc1','unanimous')
    p1=Provenance('p1','s1','city',('e1',),'extract'); p2=Provenance('p2','s1','state',('e2',),'extract'); pc1=Provenance('pc1','s1','city',('e1',),'fusion')
    conflict=Conflict('x','s1','state',('cf1','cf2'))
    return c1,c2,k1,p1,p2,pc1,conflict

def test_enrichment_metrics_measure_clean_fields_and_provenance():
    c1,c2,k1,p1,p2,pc1,conflict=facts()
    m=compute_enrichment_metrics(['s1'],['city','state'],canonical_facts=[k1],candidate_facts=[c1,c2],provenances=[p1,p2,pc1],conflicts=[conflict],field_accuracy_labels={('s1','city'):True})
    assert mv_avail(m.field_coverage)==.5 and mv_avail(m.field_accuracy)==1
    assert mv_avail(m.provenance_coverage)==1 and mv_avail(m.conflict_rate)==.5

def test_enrichment_unavailable_truth_and_empty_slots():
    m=compute_enrichment_metrics([],[],field_accuracy_labels={})
    assert all(x.availability is MetricAvailability.UNAVAILABLE for x in (m.field_coverage,m.field_accuracy,m.provenance_coverage,m.conflict_rate))
    assert compute_enrichment_metrics(['s'],['x']).field_accuracy.availability is MetricAvailability.UNAVAILABLE

def contact(cid,owner,kind,value,status=ContactStatus.DISCOVERED,dt=NOW):
    assessed=status in {ContactStatus.VALIDATED,ContactStatus.INVALID,ContactStatus.STALE}
    return ContactPoint(cid,owner,kind,value,('e',),status,dt,('v',) if assessed else (),dt if assessed else None)

def test_contact_logical_dedupe_normalizes_and_latest_wins():
    items=[contact('a','c1',ContactKind.EMAIL,' A@X.COM '),contact('b','c1',ContactKind.EMAIL,'a@x.com',ContactStatus.VALIDATED,NOW+timedelta(seconds=1)),contact('c','c2',ContactKind.PHONE,'(11) 9999-0000'),contact('d','c2',ContactKind.PHONE,'11 99990000',ContactStatus.INVALID,NOW+timedelta(seconds=1))]
    m=compute_contact_metrics(items,owner_ids=['c1','c2'])
    assert m.logical_contacts==2 and mv_avail(m.contact_discovery_rate)==1 and mv_avail(m.validation_rate)==.5 and mv_avail(m.invalid_rate)==.5 and mv_avail(m.stale_rate)==0

def test_contact_tie_status_rank_and_url_normalization():
    items=[contact('a','c',ContactKind.LINKEDIN,'HTTPS://X/Y/'),contact('b','c',ContactKind.LINKEDIN,'https://x/y',ContactStatus.VALIDATED)]
    m=compute_contact_metrics(items,owner_ids=['c']); assert m.logical_contacts==1 and mv_avail(m.validation_rate)==1

def test_contact_empty_denominators_unavailable():
    m=compute_contact_metrics([],owner_ids=[])
    assert m.logical_contacts==0 and all(x.availability is MetricAvailability.UNAVAILABLE for x in (m.contact_discovery_rate,m.validation_rate,m.invalid_rate,m.stale_rate))

def test_qualification_metrics_ground_truth_and_human_decisions():
    pred={'a':QualificationStatus.QUALIFIED,'b':QualificationStatus.QUALIFIED,'c':QualificationStatus.NOT_QUALIFIED}
    m=compute_qualification_metrics(pred,ground_truth={'a':True,'b':False,'c':True},human_decisions={'a':QualificationStatus.QUALIFIED,'b':QualificationStatus.NOT_QUALIFIED})
    assert mv_avail(m.precision)==.5 and mv_avail(m.recall)==.5 and mv_avail(m.human_disagreement_rate)==.5

def test_qualification_missing_labels_are_explicit_unavailable():
    m=compute_qualification_metrics({'a':QualificationStatus.UNKNOWN})
    assert m.precision.availability is MetricAvailability.UNAVAILABLE and m.recall.availability is MetricAvailability.UNAVAILABLE and m.human_disagreement_rate.availability is MetricAvailability.UNAVAILABLE

def test_qualification_zero_overlap_stays_unavailable():
    m=compute_qualification_metrics({'a':QualificationStatus.UNKNOWN},ground_truth={'b':True},human_decisions={'b':QualificationStatus.QUALIFIED})
    assert all(x.availability is MetricAvailability.UNAVAILABLE for x in (m.precision,m.recall,m.human_disagreement_rate))

def test_operational_metrics_never_invent_missing_telemetry():
    m=compute_operational_metrics(discovered=10,enriched=5,qualified=2,validated_contacts=4,processed_leads=5)
    assert all(x.availability is MetricAvailability.UNAVAILABLE for x in (m.cost_per_discovered,m.cost_per_enriched,m.cost_per_qualified,m.cost_per_validated_contact,m.time_per_lead_seconds))

def test_operational_metrics_with_real_inputs_and_zero_units():
    m=compute_operational_metrics(total_cost=100,elapsed_seconds=50,discovered=10,enriched=5,qualified=2,validated_contacts=4,processed_leads=5)
    assert [x.value for x in (m.cost_per_discovered,m.cost_per_enriched,m.cost_per_qualified,m.cost_per_validated_contact,m.time_per_lead_seconds)]==[10,20,50,25,10]
    z=compute_operational_metrics(total_cost=10,elapsed_seconds=10)
    assert z.cost_per_discovered.availability is MetricAvailability.UNAVAILABLE and z.time_per_lead_seconds.availability is MetricAvailability.UNAVAILABLE

def test_operational_invalid_negative_inputs():
    with pytest.raises(ValueError): compute_operational_metrics(total_cost=-1)
    with pytest.raises(ValueError): compute_operational_metrics(elapsed_seconds=-1)
    with pytest.raises(ValueError): compute_operational_metrics(discovered=-1)

def test_measurement_report_is_deterministic_and_scope_explicit():
    report=build_measurement_report(scope='CALIBRATION_FIXTURE',discovery=compute_discovery_metrics(['a'],universe_entity_ids=['a']),entity_resolution=compute_entity_resolution_metrics(1,0,1,0),enrichment=compute_enrichment_metrics([],[]),contacts=compute_contact_metrics([],owner_ids=[]),qualification=compute_qualification_metrics({}),operation=compute_operational_metrics())
    assert report.to_json()==report.to_json(); payload=json.loads(report.to_json()); assert payload['scope']=='CALIBRATION_FIXTURE' and payload['schema_version']=='searchleads_measurement_v1'
    with pytest.raises(ValueError): replace(report,scope=' ')
    with pytest.raises(ValueError): replace(report,schema_version='v2')
