from __future__ import annotations
from dataclasses import replace
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import pytest
from searchleads.contact_validation import ContactValidationDisposition as D,ContactValidationMethod as M,ContactValidationResult,validate_contact_publication as validate
from searchleads.domain import Company,ContactKind as K,ContactPoint,ContactStatus as S,Evidence,Source
NOW=datetime(2026,8,25,10,0,tzinfo=timezone.utc); LATER=NOW+timedelta(hours=1)

class Repo:
 def __init__(s): s.r={}
 @staticmethod
 def _id(x):
  for f in ('contact_id','evidence_id','source_id','company_id','person_id'):
   if hasattr(x,f): return getattr(x,f)
  raise TypeError(type(x).__name__)
 def save(s,x):
  k=(type(x),s._id(x)); old=s.r.get(k)
  if old is not None:
   if old!=x: raise ValueError('immutable id conflict')
   return False
  s.r[k]=x; return True
 def load(s,t,i): return s.r.get((t,i))

def ev(r,i,url,*,at=NOW,typ='company-web-page',status=200,raw='<html>x</html>'):
 src=Source('src:'+i,typ,url,'page'); r.save(src); x=Evidence(i,src.source_id,url,at,raw,metadata={'http_status':status}); r.save(x); return x

def cp(r,i,owner,k,val,eids,*,status=S.DISCOVERED,at=NOW):
 kw={} if status is S.DISCOVERED else {'validation_evidence_ids':eids,'validated_at':at}
 x=ContactPoint(i,owner,k,val,eids,status,at,**kw); r.save(x); return x

def pair(*,k=K.EMAIL,a='sales@example.com',b=None,u1='https://e.test/contact',u2='https://e.test/support',t1=NOW,t2=NOW,owner='company-1',owner2=None,k2=None,typ2='company-web-page',status2=200,raw2='<html>x</html>'):
 r=Repo(); r.save(Company(owner));
 if owner2 and owner2!=owner:r.save(Company(owner2))
 ev(r,'ev-1',u1,at=t1); ev(r,'ev-2',u2,at=t2,typ=typ2,status=status2,raw=raw2)
 x=cp(r,'c-1',owner,k,a,('ev-1',),at=t1); y=cp(r,'c-2',owner2 or owner,k2 or k,b or a,('ev-2',),at=t2); return r,x,y

def test_validated_snapshot_contract():
 r,a,b=pair(); z=validate(r,a.contact_id,(b.contact_id,)); v=z.validated_contact
 assert z.disposition is D.VALIDATED and z.method is M.PUBLICATION_CORROBORATION_V1 and v.status is S.VALIDATED
 assert (v.owner_id,v.value,v.discovery_evidence_ids,v.validation_evidence_ids,v.validated_at)==(a.owner_id,a.value,a.discovery_evidence_ids,('ev-1','ev-2'),NOW)
 assert not z.deliverability_verified and not z.reachability_verified and r.load(ContactPoint,v.contact_id)==v

def test_later_same_page_is_independent():
 r,a,b=pair(u2='https://e.test/contact',t2=LATER); z=validate(r,a.contact_id,(b.contact_id,)); assert z.disposition is D.VALIDATED and z.validated_contact.validated_at==LATER and z.validation_locators==('https://e.test/contact',)

def test_same_page_same_time_not_independent():
 r,a,b=pair(u2='https://e.test/contact'); assert validate(r,a.contact_id,(b.contact_id,)).disposition is D.INSUFFICIENT_EVIDENCE

@pytest.mark.parametrize('k,a,b',[(K.EMAIL,'Sales@Example.COM','sales@example.com'),(K.PHONE,'(11) 99999-0000','11 99999 0000'),(K.WHATSAPP,'+55 11 99999-0000','5511999990000'),(K.PROFESSIONAL_PROFILE,'HTTPS://LINKEDIN.COM:443/in/Maria/#x','https://linkedin.com/in/Maria'),(K.CONTACT_FORM,'http://example.com:80/contact/','http://example.com/contact'),(K.INSTAGRAM,'https://example.com:8443/acme/','https://EXAMPLE.com:8443/acme')])
def test_equivalence(k,a,b):
 r,x,y=pair(k=k,a=a,b=b); assert validate(r,x.contact_id,(y.contact_id,)).disposition is D.VALIDATED

@pytest.mark.parametrize('changes',[{'owner2':'company-2'},{'k2':K.OTHER},{'b':'other@example.com'},{'typ2':'dataset'},{'status2':404},{'raw2':None}])
def test_non_corroborating_observation(changes):
 r,a,b=pair(**changes); z=validate(r,a.contact_id,(b.contact_id,)); assert z.disposition is D.INSUFFICIENT_EVIDENCE

@pytest.mark.parametrize('k,val',[(K.EMAIL,'bad@'),(K.EMAIL,'x@'+'a'*64+'.com'),(K.EMAIL,'a@@example.com'),(K.EMAIL,'a b@example.com'),(K.PHONE,'12345'),(K.WHATSAPP,'abc'),(K.CONTACT_FORM,'ftp://example.com/contact'),(K.LINKEDIN,'https://[broken'),(K.OTHER,'opaque')])
def test_not_validatable(k,val):
 r=Repo(); r.save(Company('company-1')); ev(r,'ev-1','https://e.test/contact'); x=cp(r,'c','company-1',k,val,('ev-1',)); z=validate(r,x.contact_id); assert z.disposition is D.NOT_VALIDATABLE and z.validated_contact is None and z.validation_evidence_ids==()

def test_duplicate_contact_and_evidence_do_not_inflate():
 r=Repo(); r.save(Company('company-1')); ev(r,'ev','https://e.test/contact'); a=cp(r,'a','company-1',K.EMAIL,'a@example.com',('ev','ev')); b=cp(r,'b','company-1',K.EMAIL,'A@EXAMPLE.COM',('ev',)); z=validate(r,a.contact_id,(a.contact_id,b.contact_id,a.contact_id)); assert z.disposition is D.INSUFFICIENT_EVIDENCE and z.validation_evidence_ids==('ev',)

def test_non_discovered_corroboration_ignored():
 r,a,b=pair(); r.r[(ContactPoint,b.contact_id)]=replace(b,status=S.VALIDATED,validation_evidence_ids=('ev-2',),validated_at=NOW); assert validate(r,a.contact_id,(b.contact_id,)).disposition is D.INSUFFICIENT_EVIDENCE

def test_persist_false_and_idempotence():
 r,a,b=pair(); one=validate(r,a.contact_id,(b.contact_id,),persist=False); assert r.load(ContactPoint,one.validated_contact.contact_id) is None
 saved=validate(r,a.contact_id,(b.contact_id,)); again=validate(r,a.contact_id,(b.contact_id,)); assert saved.validated_contact==again.validated_contact

@pytest.mark.parametrize('mode',['missing_contact','wrong_status','missing_corrob','missing_evidence','missing_source'])
def test_reference_errors(mode):
 r=Repo()
 if mode=='missing_contact':
  with pytest.raises(ValueError,match='missing contact'): validate(r,'missing')
  return
 r.save(Company('company-1'))
 if mode=='missing_evidence': x=cp(r,'c','company-1',K.EMAIL,'a@example.com',('missing',))
 elif mode=='missing_source':
  r.save(Evidence('ev','missing-source','https://e.test/contact',NOW,'body',metadata={'http_status':200})); x=cp(r,'c','company-1',K.EMAIL,'a@example.com',('ev',))
 else:
  ev(r,'ev','https://e.test/contact'); x=cp(r,'c','company-1',K.EMAIL,'a@example.com',('ev',),status=S.VALIDATED) if mode=='wrong_status' else cp(r,'c','company-1',K.EMAIL,'a@example.com',('ev',))
 if mode=='missing_corrob':
  with pytest.raises(ValueError,match='missing corroborating contact'): validate(r,x.contact_id,('missing',))
 elif mode=='wrong_status':
  with pytest.raises(ValueError,match='original DISCOVERED'): validate(r,x.contact_id)
 elif mode=='missing_evidence':
  with pytest.raises(ValueError,match='missing contact discovery evidence'): validate(r,x.contact_id)
 else:
  with pytest.raises(ValueError,match='missing contact discovery source'): validate(r,x.contact_id)

def test_result_invariants():
 r,a,b=pair()
 with pytest.raises(ValueError,match='cannot claim'): ContactValidationResult(a,D.INSUFFICIENT_EVIDENCE,M.PUBLICATION_CORROBORATION_V1,None,(),(),(),True,False,'x')
 with pytest.raises(ValueError,match='requires validated contact'): ContactValidationResult(a,D.VALIDATED,M.PUBLICATION_CORROBORATION_V1,None,(),(),(),False,False,'x')
 v=validate(r,a.contact_id,(b.contact_id,),persist=False).validated_contact
 with pytest.raises(ValueError,match='non-validated'): ContactValidationResult(a,D.INSUFFICIENT_EVIDENCE,M.PUBLICATION_CORROBORATION_V1,v,(),(),(),False,False,'x')

def _bench(c):
 k=K(c['kind']); r=Repo(); r.save(Company('company-1')); r.save(Company('company-2')); cs=[]
 for n,o in enumerate(c['observations'],1):
  at=NOW+timedelta(minutes=int(o.get('minutes',0))); e=f'ev-{n}'; ev(r,e,o['locator'],at=at,typ=o.get('source_type','company-web-page')); cs.append(cp(r,f'c-{n}',o.get('owner','company-1'),K(o.get('kind',k.value)),o['value'],(e,),at=at))
 return validate(r,cs[0].contact_id,tuple(x.contact_id for x in cs[1:])).disposition is D.VALIDATED

def test_benchmark_exact_metrics():
 cases=json.loads((Path(__file__).parent/'fixtures'/'contact_validation_v1.json').read_text()); tp=fp=tn=fn=0
 for c in cases:
  p=_bench(c); e=c['expected_validated']; tp+=bool(e and p); fp+=bool(p and not e); fn+=bool(e and not p); tn+=bool(not e and not p)
 assert len(cases)==12 and (tp,fp,tn,fn)==(6,0,6,0) and tp/(tp+fp)==tp/(tp+fn)==1.0
