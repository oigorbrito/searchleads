from __future__ import annotations
import tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path
from searchleads.domain import Company, ProfessionalRole, Provenance, Source, SourceType, Evidence
from searchleads.person_discovery import OfficialPeopleSource, discover_person_roles_from_html
from searchleads.persistence import SQLiteLeadStore, MissingReferenceError
from searchleads.role_persistence import get_professional_role, save_professional_role

NOW=datetime(2026,8,21,15,30,tzinfo=timezone.utc)
URL="https://www.transparencia.serpro.gov.br/acesso-a-informacao/institucional/quem-e-quem"
HTML='''<h2>Diretoria-Executiva</h2>
<h3>Diretor-Presidente - DP</h3><p>Wilton Itaiguara Gonçalves Mota</p><p>Telefone: (61) 2021-8101</p>
<h3>Diretor de Negócios Governamentais - DINGM</h3><p>Ermes Ferreira Costa Neto</p>
<h3>Diretor de Infraestrutura - DIINF</h3><p>Wallyson Lemos dos Reis Oliveira</p>
<h3>Diretor de Administração e Finanças - DIRAF</h3><p>Osmar Quirino da Silva</p>
<h3>Diretor de Pessoas e Assuntos Jurídicos - DIPEJ</h3><p>Alexandre Brandão Henriques Maimoni</p>
<h3>Diretora de Negócios Econômico-Fazendários - DINEF</h3><p>Ariadne de Santa Teresa Lopes Fonseca</p>
<h3>Diretor de Novos Negócios e Inteligência de TI - DINIT</h3><p>André Picoli Agatte</p>'''

class PersonDiscoveryTests(unittest.TestCase):
    def test_extracts_seven_current_serpro_executive_observations(self):
        obs=discover_person_roles_from_html(HTML)
        self.assertEqual(len(obs),7); self.assertEqual(obs[0].name,"Wilton Itaiguara Gonçalves Mota"); self.assertIn("Diretor-Presidente",obs[0].title); self.assertEqual(obs[-1].name,"André Picoli Agatte")
    def test_does_not_treat_phone_email_or_company_text_as_person(self):
        self.assertEqual(discover_person_roles_from_html('<h3>Diretor de Teste</h3><p>Telefone: (61) 2021-0000</p><p>E-mail: x@serpro.gov.br</p><p>Serpro Sede</p>'),())
    def test_ingest_persists_people_and_evidence_backed_roles(self):
        with SQLiteLeadStore() as store:
            c=Company("company:cnpj:33683111000280",created_at=NOW); store.save_company(c); r=OfficialPeopleSource().ingest(store,c.company_id,URL,html=HTML,retrieved_at=NOW)
            self.assertEqual(len(r.people),7); self.assertEqual(len(r.roles),7)
            for p,role in zip(r.people,r.roles):
                self.assertEqual(store.get_person(p.person_id),p); self.assertEqual(get_professional_role(store,role.role_id),role); self.assertEqual(role.company_id,c.company_id); self.assertEqual(role.provenance.evidence_ids,(r.evidence.evidence_id,))
    def test_company_and_person_are_distinct_entities(self):
        with SQLiteLeadStore() as store:
            c=Company("company:cnpj:33683111000280",created_at=NOW); store.save_company(c); r=OfficialPeopleSource().ingest(store,c.company_id,URL,html=HTML,retrieved_at=NOW); self.assertTrue(all(p.person_id != c.company_id for p in r.people))
    def test_missing_company_rejected_before_evidence(self):
        with SQLiteLeadStore() as store:
            with self.assertRaises(ValueError): OfficialPeopleSource().ingest(store,"missing",URL,html=HTML,retrieved_at=NOW)
            self.assertEqual(store.list_evidence(),())
    def test_same_page_snapshot_is_idempotent(self):
        with SQLiteLeadStore() as store:
            c=Company("company:cnpj:33683111000280",created_at=NOW); store.save_company(c); src=OfficialPeopleSource(); a=src.ingest(store,c.company_id,URL,html=HTML,retrieved_at=NOW); b=src.ingest(store,c.company_id,URL,html=HTML,retrieved_at=NOW); self.assertEqual(a,b)
    def test_role_requires_persisted_person_company_and_provenance(self):
        with SQLiteLeadStore() as store:
            source=Source("src",SourceType.OFFICIAL_SOURCE,URL); ev=Evidence("ev","src",NOW,"x"); store.save_source(source); store.save_evidence(ev); role=ProfessionalRole("role","missing-person","missing-company","Director",Provenance(("ev",),"x",generated_at=NOW))
            with self.assertRaises(MissingReferenceError): save_professional_role(store,role)
    def test_role_roundtrip_survives_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"people.sqlite3"
            with SQLiteLeadStore(path) as store:
                c=Company("company:cnpj:33683111000280",created_at=NOW); store.save_company(c); r=OfficialPeopleSource().ingest(store,c.company_id,URL,html=HTML,retrieved_at=NOW); rid=r.roles[0].role_id
            with SQLiteLeadStore(path) as reopened:
                role=get_professional_role(reopened,rid); self.assertIsNotNone(role); self.assertEqual(role.company_id,c.company_id)

if __name__=='__main__': unittest.main()
