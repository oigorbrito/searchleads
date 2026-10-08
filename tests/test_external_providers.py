from datetime import datetime, timezone
from urllib.error import URLError
import json
import pytest
from searchleads.persistence import SQLiteRepository
from searchleads.external_providers import *
from searchleads.external_providers.apify import _normalized_actor_id,_interface_language,_http_post_json

NOW=datetime(2026,8,26,5,0,tzinfo=timezone.utc)

def q(i=1,text='dentista CRO Brasil',country='BR',lang='pt'):
    return WebSearchQuery(f'q{i}',text,country,lang)

def test_contract_validation():
    with pytest.raises(ValueError): WebSearchQuery('','x')
    with pytest.raises(ValueError): WebSearchQuery('q','x','BRA')
    with pytest.raises(ValueError): WebSearchHit('q','','u','',None,'e')
    with pytest.raises(ValueError): WebSearchHit('q','t','u','',0,'e')
    with pytest.raises(ValueError): WebSearchBatch('',(),())

def test_batch_requires_same_batch_evidence():
    with pytest.raises(ValueError,match='same batch'):
        WebSearchBatch('p',(WebSearchHit('q','t','u','',1,'missing'),),())

def test_actor_normalization_and_language():
    assert _normalized_actor_id('apify/google-search-scraper')=='apify~google-search-scraper'
    assert _normalized_actor_id('apify~google-search-scraper')=='apify~google-search-scraper'
    with pytest.raises(ValueError): _normalized_actor_id('bad')
    assert _interface_language('pt','BR')=='pt-BR'
    assert _interface_language('en','US')=='en'

def test_client_sends_token_only_in_header_and_bounds():
    seen={}
    def transport(url,headers,body,timeout):
        seen.update(url=url,headers=headers,body=body,timeout=timeout); return []
    c=ApifyActorClient(transport)
    out=c.run_sync_get_dataset_items('apify/google-search-scraper',{'queries':'x'},token=' SECRET ',timeout_seconds=3,max_items=2)
    assert out==()
    assert 'SECRET' not in seen['url']
    assert seen['headers']['Authorization']=='Bearer SECRET'
    assert json.loads(seen['body'])=={'queries':'x'}
    assert seen['timeout']==3

def test_client_validates_inputs_and_payload_shapes():
    c=ApifyActorClient(lambda *a: [])
    with pytest.raises(ValueError): c.run_sync_get_dataset_items('a/b',{},token='')
    with pytest.raises(ValueError): c.run_sync_get_dataset_items('a/b',{},token='x',timeout_seconds=0)
    with pytest.raises(ValueError): c.run_sync_get_dataset_items('a/b',{},token='x',max_items=0)
    with pytest.raises(TypeError): c.run_sync_get_dataset_items('a/b',[],token='x')
    with pytest.raises(ApifyPayloadError): ApifyActorClient(lambda *a:{}).run_sync_get_dataset_items('a/b',{},token='x')
    with pytest.raises(ApifyPayloadError): ApifyActorClient(lambda *a:[1]).run_sync_get_dataset_items('a/b',{},token='x')
    with pytest.raises(ApifyPayloadError): ApifyActorClient(lambda *a:[{},{}]).run_sync_get_dataset_items('a/b',{},token='x',max_items=1)

def test_client_accepts_bytes_and_text_json_and_rejects_bad():
    assert ApifyActorClient(lambda *a:b'[{"x":1}]').run_sync_get_dataset_items('a/b',{},token='x')[0]['x']==1
    assert ApifyActorClient(lambda *a:'[{"x":1}]').run_sync_get_dataset_items('a/b',{},token='x')[0]['x']==1
    with pytest.raises(ApifyPayloadError): ApifyActorClient(lambda *a:b'bad').run_sync_get_dataset_items('a/b',{},token='x')
    with pytest.raises(ApifyPayloadError): ApifyActorClient(lambda *a:'bad').run_sync_get_dataset_items('a/b',{},token='x')

def test_config_and_provider_validation():
    with pytest.raises(ValueError): ApifyGoogleSearchConfig(max_pages_per_query=0)
    with pytest.raises(ValueError): ApifyGoogleSearchConfig(max_queries=0)
    with pytest.raises(ValueError): ApifyGoogleSearchConfig(max_dataset_items=0)
    with pytest.raises(ValueError): ApifyGoogleSearchConfig(timeout_seconds=0)
    with pytest.raises(ValueError): ApifyGoogleSearchProvider('')

def test_provider_repr_masks_secret_token():
    provider = ApifyGoogleSearchProvider('sk_live_secret_token_abc123')
    repr_str = repr(provider)
    assert 'sk_live_secret_token_abc123' not in repr_str
    assert 'token=\'***\'' in repr_str

def payload_for(term='dentista CRO Brasil',organic=None,url='https://www.google.com/search?q=dentista'):
    return [{'searchQuery':{'term':term,'url':url},'organicResults': organic if organic is not None else [{'title':'Dra Ana Dentista CRO-SP 12345','url':'https://clinic.example/ana','description':'Blefaroplastia','position':1}]}]

def provider_with_payload(payload,seen=None,config=None):
    def transport(url,headers,body,timeout):
        if seen is not None: seen.update(url=url,headers=headers,body=json.loads(body),timeout=timeout)
        return payload
    return ApifyGoogleSearchProvider('tok',client=ApifyActorClient(transport),config=config or ApifyGoogleSearchConfig())

def test_empty_search_does_not_call_transport():
    calls=[]
    p=ApifyGoogleSearchProvider('tok',client=ApifyActorClient(lambda *a:calls.append(a)))
    assert p.search(SQLiteRepository(),()).hits==() and calls==[]

def test_provider_bounds_unique_ids_and_batch_locale():
    p=provider_with_payload([],config=ApifyGoogleSearchConfig(max_queries=1))
    with pytest.raises(ValueError): p.search(SQLiteRepository(),(q(1),q(2)))
    with pytest.raises(ValueError): p.search(SQLiteRepository(),(q(1),q(1)))
    with pytest.raises(ValueError): provider_with_payload([]).search(SQLiteRepository(),(q(1,country='BR'),q(2,country='US')))
    with pytest.raises(ValueError): provider_with_payload([]).search(SQLiteRepository(),(q(1,lang='pt'),q(2,lang='en')))

def test_provider_builds_expected_bounded_actor_input():
    seen={}; p=provider_with_payload([],seen)
    p.search(SQLiteRepository(),(q(),),retrieved_at=NOW)
    assert seen['body']['countryCode']=='br' and seen['body']['languageCode']=='pt-BR'
    assert seen['body']['maxPagesPerQuery']==1
    assert seen['body']['saveHtml'] is False and seen['body']['includeUnfilteredResults'] is False

def test_provider_persists_raw_evidence_before_projection_and_replays_idempotently():
    repo=SQLiteRepository(); p=provider_with_payload(payload_for())
    batch=p.search(repo,(q(),),retrieved_at=NOW)
    assert len(batch.evidence)==1 and len(batch.hits)==1
    e=batch.evidence[0]
    assert repo.load_evidence(e.evidence_id)==e
    assert repo.raw_evidence_bytes(e.evidence_id)==e.raw_payload.encode()
    assert 'tok' not in e.raw_payload and 'tok' not in e.locator and 'tok' not in str(e.metadata)
    again=p.search(repo,(q(),),retrieved_at=NOW)
    assert again.evidence[0].evidence_id==e.evidence_id

def test_provider_projects_only_matching_query_and_valid_hits():
    payload=[
      {'searchQuery':{'term':'other'},'organicResults':[{'title':'X','url':'https://x.test'}]},
      {'searchQuery':{'term':'dentista CRO Brasil'},'organicResults':[{'title':'','url':'https://bad.test'},{'title':'Good','url':'','position':2},{'title':'Good','url':'https://good.test','description':'s','position':0}]}
    ]
    b=provider_with_payload(payload).search(SQLiteRepository(),(q(),),retrieved_at=NOW)
    assert len(b.hits)==1 and b.hits[0].url=='https://good.test' and b.hits[0].position is None

def test_provider_accepts_query_fallback_and_empty_organic_results():
    payload=[{'query':'dentista CRO Brasil'}]
    b=provider_with_payload(payload).search(SQLiteRepository(),(q(),),retrieved_at=NOW)
    assert len(b.evidence)==1 and b.hits==()

def test_provider_rejects_bad_organic_shapes_and_naive_time():
    with pytest.raises(ApifyPayloadError): provider_with_payload([{'query':'dentista CRO Brasil','organicResults':{}}]).search(SQLiteRepository(),(q(),),retrieved_at=NOW)
    with pytest.raises(ApifyPayloadError): provider_with_payload([{'query':'dentista CRO Brasil','organicResults':[1]}]).search(SQLiteRepository(),(q(),),retrieved_at=NOW)
    with pytest.raises(ValueError): provider_with_payload([]).search(SQLiteRepository(),(q(),),retrieved_at=datetime(2026,1,1))

def test_provider_detects_content_address_collision():
    repo=SQLiteRepository(); p=provider_with_payload(payload_for())
    b=p.search(repo,(q(),),retrieved_at=NOW); e=b.evidence[0]
    tampered=type(e)(e.evidence_id,e.source_id,'https://tampered.test',e.captured_at,e.raw_payload,e.content_digest,e.metadata)
    repo._connection.execute("UPDATE evidence_records SET envelope_json = ? WHERE evidence_id = ?", (__import__('searchleads.persistence.sqlite',fromlist=['encode_record']).encode_record(__import__('dataclasses').replace(tampered,raw_payload=None)),e.evidence_id)); repo._connection.commit()
    with pytest.raises(ApifyPayloadError,match='collision'): p.search(repo,(q(),),retrieved_at=NOW)

def test_dental_bridge_preserves_pending_candidate_and_evidence_link():
    from searchleads.dental_discovery import build_dental_discovery_queries
    repo=SQLiteRepository(); expected=build_dental_discovery_queries(max_queries=1)[0].query
    p=provider_with_payload(payload_for(term=expected))
    result=discover_dental_candidates_with_provider(repo,p,max_queries=1,retrieved_at=NOW)
    assert len(result.queries)==1 and len(result.observations)==1 and len(result.candidates)==1
    assert result.observations[0].evidence_id==result.provider_batch.evidence[0].evidence_id
    assert result.candidates[0].cfo_verification_status.value=='PENDING'

def test_http_transport_wraps_errors(monkeypatch):
    import searchleads.external_providers.apify as m
    def boom(*a,**k): raise URLError('offline')
    monkeypatch.setattr(m,'urlopen',boom)
    with pytest.raises(ApifyTransportError): _http_post_json('https://x.test',{},b'{}',1)

def test_http_transport_success_decodes_json(monkeypatch):
    import searchleads.external_providers.apify as m
    class Headers:
        def get_content_charset(self): return None
    class Response:
        headers=Headers()
        def __enter__(self): return self
        def __exit__(self,*a): return False
        def read(self): return b'[{"ok":true}]'
    monkeypatch.setattr(m,'urlopen',lambda *a,**k: Response())
    assert _http_post_json('https://x.test',{},b'{}',1)==[{'ok':True}]
