from __future__ import annotations
import json
from pathlib import Path
import pytest
from searchleads.repeatable_discovery import (
    DIRECTORY_URL, RECIPE_ID, DiscoveredCompanySeed, DiscoveryCoverageReference,
    measure_discovery_coverage, measure_serpro_snapshot_coverage, reference_from_mapping,
)
ROOT=Path(__file__).resolve().parents[1]
DATA=json.loads((ROOT/'tests/fixtures/discovery_coverage_v1.json').read_text())
REF=reference_from_mapping(DATA)

def seed(cnpj, recipe_id=RECIPE_ID): return DiscoveredCompanySeed(cnpj,None,None,None,recipe_id=recipe_id)

def test_current_bounded_scope_is_exact_12_of_12():
    r=measure_serpro_snapshot_coverage(REF,DATA['snapshot_html'])
    assert (r.reference_count,r.discovered_unique_count,r.true_positive,r.false_positive,r.false_negative)==(12,12,12,0,0)
    assert r.precision==1.0 and r.recall==1.0 and r.source_page_coverage==1.0
    assert r.missed_cnpjs==() and r.unexpected_cnpjs==()

def test_missing_reference_is_false_negative():
    r=measure_discovery_coverage(REF,tuple(seed(c) for c in REF.reference_cnpjs[:-1]))
    assert r.true_positive==11 and r.false_negative==1 and r.false_positive==0
    assert r.recall==11/12 and r.missed_cnpjs==(REF.reference_cnpjs[-1],)

def test_unexpected_seed_is_false_positive():
    observed=tuple(seed(c) for c in REF.reference_cnpjs)+(seed('99999999999999'),)
    r=measure_discovery_coverage(REF,observed)
    assert r.true_positive==12 and r.false_positive==1 and r.false_negative==0
    assert r.precision==12/13 and r.unexpected_cnpjs==('99999999999999',)

def test_duplicate_observation_does_not_inflate_counts():
    observed=(seed(REF.reference_cnpjs[0]),seed(REF.reference_cnpjs[0]))
    r=measure_discovery_coverage(REF,observed)
    assert r.discovered_unique_count==1 and r.duplicate_observation_count==1 and r.true_positive==1

def test_zero_discovery_has_undefined_precision_and_zero_recall():
    r=measure_discovery_coverage(REF,())
    assert r.precision is None and r.recall==0.0 and r.false_negative==12

def test_recipe_mismatch_is_rejected():
    bad=seed(REF.reference_cnpjs[0]); object.__setattr__(bad,'recipe_id','other')
    with pytest.raises(ValueError,match='recipe'): measure_discovery_coverage(REF,(bad,))

@pytest.mark.parametrize('kwargs',[
    {'scope_id':''},{'scope_definition':' '},{'reference_method':''},
    {'source_url':'https://example.test/x'},{'recipe_id':'other'},
    {'reference_cnpjs':()},
    {'reference_cnpjs':('33683111000107','33683111000107')},
    {'reference_cnpjs':('33683111000280','33683111000107')},
    {'reference_cnpjs':('bad',)},
])
def test_reference_invariants(kwargs):
    base=dict(scope_id='s',source_url=DIRECTORY_URL,recipe_id=RECIPE_ID,scope_definition='d',reference_method='m',reference_cnpjs=('33683111000107',))
    base.update(kwargs)
    with pytest.raises(ValueError): DiscoveryCoverageReference(**base)

def test_mapping_requires_string_list():
    bad=dict(DATA); bad['reference_cnpjs']='not-list'
    with pytest.raises(ValueError): reference_from_mapping(bad)
    bad=dict(DATA); bad['reference_cnpjs']=[1]
    with pytest.raises(ValueError): reference_from_mapping(bad)

def test_mapping_sorts_reference_for_determinism():
    data=dict(DATA); data['reference_cnpjs']=list(reversed(data['reference_cnpjs']))
    assert reference_from_mapping(data).reference_cnpjs==REF.reference_cnpjs
