from __future__ import annotations
import unittest
from datetime import datetime, timezone
from searchleads.brasilapi import BrasilAPISource
from searchleads.company_enrichment import OfficialCompanyLocationSource, extract_official_location_facts
from searchleads.field_fusion import FusionStatus, fuse_candidate_facts
from searchleads.normalization import normalize_candidate_fact
from searchleads.persistence import SQLiteLeadStore

NOW=datetime(2026,8,21,12,30,tzinfo=timezone.utc)
CNPJ="33683111000280"
URL="https://www.transparencia.serpro.gov.br/acesso-a-informacao/institucional/enderecos"
HTML='''<html><body><h3>Brasília</h3><p>SGAN Av. L-2 Norte Quadra 601 – Módulo G</p><p>Brasília/Distrito Federal</p><p>CEP: 70.836-900</p><p>CNPJ: 33.683.111/0002-80</p><p>Início das Atividades: 30/6/1967</p></body></html>'''
BRASIL={"cnpj":CNPJ,"razao_social":"SERVICO FEDERAL DE PROCESSAMENTO DE DADOS (SERPRO)","nome_fantasia":"REGIONAL BRASILIA-DF","descricao_situacao_cadastral":"ATIVA","cnae_fiscal":6204000,"cnae_fiscal_descricao":"Consultoria em tecnologia da informação","municipio":"BRASILIA","uf":"DF"}

class CompanyEnrichmentTests(unittest.TestCase):
    def test_extracts_requested_office_fields(self):
        f=extract_official_location_facts(HTML,CNPJ)
        self.assertEqual(f["business_registry_id"],CNPJ)
        self.assertEqual(f["postal_code"],"70836900")
        self.assertEqual(f["city"],"Brasília")
        self.assertEqual(f["state"],"DF")
        self.assertEqual(f["street_address"],"SGAN Av. L-2 Norte Quadra 601 – Módulo G")
    def test_expected_cnpj_is_required(self):
        with self.assertRaises(ValueError): extract_official_location_facts(HTML,"00000000000000")
    def test_second_source_preserves_raw_html_and_candidate_provenance(self):
        with SQLiteLeadStore() as store:
            first=BrasilAPISource(transport=lambda _:BRASIL).ingest(store,CNPJ,retrieved_at=NOW)
            second=OfficialCompanyLocationSource().ingest(store,first.company.company_id,URL,CNPJ,retrieved_at=NOW,html=HTML)
            self.assertEqual(second.evidence.payload["body"],HTML)
            self.assertTrue(all(f.provenance.evidence_ids==(second.evidence.evidence_id,) for f in second.candidate_facts))
            self.assertEqual(len(store.list_evidence()),2)
    def test_overlapping_registry_and_state_can_fuse_across_two_sources(self):
        with SQLiteLeadStore() as store:
            first=BrasilAPISource(transport=lambda _:BRASIL).ingest(store,CNPJ,retrieved_at=NOW)
            second=OfficialCompanyLocationSource().ingest(store,first.company.company_id,URL,CNPJ,retrieved_at=NOW,html=HTML)
            allfacts=first.candidate_facts+second.candidate_facts
            for predicate in ("business_registry_id","state"):
                projected=[]
                for fact in allfacts:
                    if fact.predicate!=predicate: continue
                    normalized=normalize_candidate_fact(fact)
                    projected.append(normalized.normalized_fact or fact)
                outcome=fuse_candidate_facts(projected)
                self.assertEqual(outcome.status,FusionStatus.CANONICAL)
                self.assertEqual(len(outcome.canonical_fact.provenance.evidence_ids),2)
    def test_city_spelling_difference_remains_explicit_conflict(self):
        with SQLiteLeadStore() as store:
            first=BrasilAPISource(transport=lambda _:BRASIL).ingest(store,CNPJ,retrieved_at=NOW)
            second=OfficialCompanyLocationSource().ingest(store,first.company.company_id,URL,CNPJ,retrieved_at=NOW,html=HTML)
            facts=[f for f in first.candidate_facts+second.candidate_facts if f.predicate=="city"]
            outcome=fuse_candidate_facts(facts)
            self.assertEqual(outcome.status,FusionStatus.CONFLICT)
            self.assertEqual({s.value for s in outcome.supports},{"BRASILIA","Brasília"})
    def test_enrichment_adds_fields_not_present_in_brasilapi_adapter(self):
        with SQLiteLeadStore() as store:
            first=BrasilAPISource(transport=lambda _:BRASIL).ingest(store,CNPJ,retrieved_at=NOW)
            second=OfficialCompanyLocationSource().ingest(store,first.company.company_id,URL,CNPJ,retrieved_at=NOW,html=HTML)
            first_pred={f.predicate for f in first.candidate_facts}; second_pred={f.predicate for f in second.candidate_facts}
            self.assertNotIn("street_address",first_pred); self.assertIn("street_address",second_pred)
            self.assertIn("postal_code",second_pred); self.assertIn("activity_start_date",second_pred)

if __name__=='__main__': unittest.main()
