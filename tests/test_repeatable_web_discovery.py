from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import pytest

from searchleads.domain import Evidence, Source
from searchleads.repeatable_discovery import (
    DIRECTORY_URL, RECIPE_ID, DiscoveredCompanySeed, RepeatableDiscoveryResult,
    SeedAcquisitionItem, acquire_discovered_seeds, discover_serpro_office_seeds,
    ingest_serpro_office_directory,
)

ROOT=Path(__file__).parent
FIXTURE=ROOT/'fixtures'/'repeatable_web_discovery_v1.json'
DATA=json.loads(FIXTURE.read_text(encoding='utf-8'))
CURRENT_HTML=DATA['current_calibration']['html']
CURRENT_EXPECTED=set(DATA['current_calibration']['expected_cnpjs'])
NOW=datetime(2026,8,25,14,0,tzinfo=timezone.utc)
LATER=datetime(2026,8,26,14,0,tzinfo=timezone.utc)

class Repo:
    def __init__(self): self.records={}
    @staticmethod
    def _id(r): return getattr(r,'evidence_id',None) or getattr(r,'source_id',None)
    def load(self,t,i):
        r=self.records.get(i); return r if isinstance(r,t) else None
    def save(self,r):
        i=self._id(r); assert i
        old=self.records.get(i)
        if old is not None and old != r: raise ValueError('persistence conflict')
        self.records[i]=r; return old is None

@pytest.mark.parametrize('scenario', DATA['benchmark'], ids=lambda x:x['id'])
def test_curated_recipe_contract(scenario):
    predicted=[s.cnpj for s in discover_serpro_office_seeds(scenario['html'])]
    assert predicted == scenario['expected']

def test_visible_location_is_preserved_without_state_code_inference():
    seed=discover_serpro_office_seeds('<h3>Fortaleza</h3><p>Fortaleza/Ceará</p><p>CNPJ: 33.683.111/0004-41</p>')[0]
    assert (seed.label,seed.city,seed.state_text)==('Fortaleza','Fortaleza','Ceará')

def test_invalid_input_type_rejected():
    with pytest.raises(TypeError): discover_serpro_office_seeds(b'x') # type: ignore[arg-type]

def test_seed_and_result_invariants():
    with pytest.raises(ValueError): DiscoveredCompanySeed('123','x',None,None)
    with pytest.raises(ValueError): DiscoveredCompanySeed('33683111000280','x',None,None,' ')
    with pytest.raises(ValueError): DiscoveredCompanySeed('33683111000280','x',None,None,recipe_id='other')
    src=Source('s','known-web-directory',DIRECTORY_URL)
    ev=Evidence('e','s',DIRECTORY_URL,NOW,'x')
    with pytest.raises(ValueError): RepeatableDiscoveryResult(src,ev,(DiscoveredCompanySeed('33683111000280','x',None,None,'wrong'),),True)

def test_known_url_boundary_and_canonicalization():
    repo=Repo()
    html='<h3>X</h3><p>X/Y</p><p>CNPJ: 33.683.111/0002-80</p>'
    r=ingest_serpro_office_directory(repo,DIRECTORY_URL+'?ignored=1#frag',html,NOW)
    assert r.source.locator == DIRECTORY_URL
    assert r.evidence.locator == DIRECTORY_URL
    for bad in ('http://www.serpro.gov.br/menu/institucional/quem-somos/encontre-o-serpro','https://evil.example/x','https://www.serpro.gov.br/other','https://user:pass@www.serpro.gov.br/menu/institucional/quem-somos/encontre-o-serpro','https://www.serpro.gov.br:444/menu/institucional/quem-somos/encontre-o-serpro'):
        with pytest.raises(ValueError): ingest_serpro_office_directory(Repo(),bad,html,NOW)

def test_invalid_url_syntax_and_naive_time_rejected():
    with pytest.raises(ValueError): ingest_serpro_office_directory(Repo(),'https://[broken','x',NOW)
    with pytest.raises(ValueError): ingest_serpro_office_directory(Repo(),DIRECTORY_URL,'x',datetime(2026,8,25))
    with pytest.raises(TypeError): ingest_serpro_office_directory(Repo(),DIRECTORY_URL,b'x',NOW) # type: ignore[arg-type]

def test_raw_snapshot_and_recipe_metadata_persist_before_seed_use():
    repo=Repo(); html='<h3>X</h3><p>X/Y</p><p>CNPJ: 33.683.111/0002-80</p>'
    r=ingest_serpro_office_directory(repo,DIRECTORY_URL,html,NOW)
    assert r.evidence_was_new
    assert r.evidence.raw_payload==html
    assert r.evidence.metadata['recipe_id']==RECIPE_ID
    assert r.evidence.content_digest.startswith('sha256:')
    assert r.seeds[0].discovery_evidence_id==r.evidence.evidence_id
    assert repo.load(Source,r.source.source_id)==r.source
    assert repo.load(Evidence,r.evidence.evidence_id)==r.evidence

def test_same_snapshot_reuses_original_evidence_even_if_recaptured_later():
    repo=Repo(); html='<h3>X</h3><p>CNPJ: 33.683.111/0002-80</p>'
    first=ingest_serpro_office_directory(repo,DIRECTORY_URL,html,NOW)
    second=ingest_serpro_office_directory(repo,DIRECTORY_URL,html,LATER)
    assert first.evidence==second.evidence
    assert first.evidence_was_new and not second.evidence_was_new

def test_changed_snapshot_creates_new_evidence_and_recipe_replays_without_code_change():
    repo=Repo(); first_html='<h3>A</h3><p>CNPJ: 33.683.111/0004-41</p>'
    later_html=first_html+'<h3>B</h3><p>CNPJ: 33.683.111/0005-22</p>'
    first=ingest_serpro_office_directory(repo,DIRECTORY_URL,first_html,NOW)
    later=ingest_serpro_office_directory(repo,DIRECTORY_URL,later_html,LATER)
    assert len(first.seeds)==1 and len(later.seeds)==2
    assert first.evidence.evidence_id != later.evidence.evidence_id

def test_content_address_collision_guard():
    class CollisionRepo(Repo):
        def load(self,t,i):
            if t is Evidence: return Evidence(i,'wrong','https://wrong.example',NOW,'wrong','sha256:bad',{'recipe_id':RECIPE_ID})
            return super().load(t,i)
    with pytest.raises(ValueError): ingest_serpro_office_directory(CollisionRepo(),DIRECTORY_URL,'<h3>X</h3>',NOW)

def test_wu3_routing_key_contract_for_all_emitted_seeds():
    seeds=discover_serpro_office_seeds(CURRENT_HTML)
    assert len(seeds)==12
    assert all(re.fullmatch(r'[0-9A-Z]{14}',s.cnpj) for s in seeds)
    assert {s.cnpj for s in seeds} >= {'33683111000441','33683111001170','33683111000522','33683111000280','33683111000956'}

def test_current_calibration_has_twelve_unique_public_cnpj_blocks():
    seeds=discover_serpro_office_seeds(CURRENT_HTML)
    assert {s.cnpj for s in seeds}==CURRENT_EXPECTED
    assert any(s.label=='Nossa Sede' and s.cnpj=='33683111000107' for s in seeds)

def test_structured_acquisition_boundary_preserves_seed_and_continues_after_failure():
    repo=Repo(); html='<h3>A</h3><p>CNPJ: 33.683.111/0004-41</p><h3>B</h3><p>CNPJ: 33.683.111/0005-22</p>'
    d=ingest_serpro_office_directory(repo,DIRECTORY_URL,html,NOW)
    calls=[]
    def acquire(cnpj):
        calls.append(cnpj)
        if cnpj.endswith('522'): raise RuntimeError('synthetic failure')
        return {'cnpj':cnpj}
    run=acquire_discovered_seeds(d,acquire)
    assert calls==['33683111000441','33683111000522']
    assert (run.attempted,run.succeeded,run.failed)==(2,1,1)
    assert run.items[0].seed.discovery_evidence_id==d.evidence.evidence_id
    assert run.items[0].result=={'cnpj':'33683111000441'}
    assert run.items[1].error_type=='RuntimeError'

def test_acquisition_item_invariants():
    seed=DiscoveredCompanySeed('33683111000280','x',None,None)
    with pytest.raises(ValueError): SeedAcquisitionItem(seed,True,result=None)
    with pytest.raises(ValueError): SeedAcquisitionItem(seed,True,result='x',error_type='E')
    with pytest.raises(ValueError): SeedAcquisitionItem(seed,False,result='x',error_type='E')
    with pytest.raises(ValueError): SeedAcquisitionItem(seed,False)

def test_result_rejects_recipe_mismatch():
    src=Source('s','known-web-directory',DIRECTORY_URL)
    ev=Evidence('e','s',DIRECTORY_URL,NOW,'x')
    with pytest.raises(ValueError): RepeatableDiscoveryResult(src,ev,(),True,recipe_id='other')

def test_whitespace_only_parser_data_is_ignored():
    seeds=discover_serpro_office_seeds('<h3>Office</h3>   <p>   </p><p>CNPJ: 33.683.111/0002-80</p>')
    assert [s.cnpj for s in seeds]==['33683111000280']

def test_compact_cnpj_defensive_invalid_guard():
    from searchleads.repeatable_discovery.serpro_offices import _compact_cnpj
    with pytest.raises(ValueError): _compact_cnpj('bad')
