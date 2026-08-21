from __future__ import annotations
import unittest
from searchleads.brasilapi import BrasilAPISource
from searchleads.expansion import expand_cnpj_seeds
from searchleads.persistence import SQLiteLeadStore

PAYLOADS={
"33683111000280":{"cnpj":"33683111000280","razao_social":"SERVICO FEDERAL DE PROCESSAMENTO DE DADOS (SERPRO)","nome_fantasia":"REGIONAL BRASILIA-DF","descricao_situacao_cadastral":"ATIVA","cnae_fiscal":6204000,"cnae_fiscal_descricao":"Consultoria em tecnologia da informação","municipio":"BRASILIA","uf":"DF"},
"00360305000104":{"cnpj":"00360305000104","razao_social":"CAIXA ECONOMICA FEDERAL","nome_fantasia":"CAIXA","descricao_situacao_cadastral":"ATIVA","cnae_fiscal":6423900,"cnae_fiscal_descricao":"Caixas econômicas","municipio":"BRASILIA","uf":"DF"},
"34028316000103":{"cnpj":"34028316000103","razao_social":"EMPRESA BRASILEIRA DE CORREIOS E TELEGRAFOS","nome_fantasia":"CORREIOS","descricao_situacao_cadastral":"ATIVA","cnae_fiscal":5310501,"cnae_fiscal_descricao":"Atividades do Correio Nacional","municipio":"BRASILIA","uf":"DF"},
}
def transport(url):
    cnpj=url.rstrip('/').split('/')[-1]
    if cnpj not in PAYLOADS: raise ValueError("fixture missing")
    return PAYLOADS[cnpj]

class ExpansionTests(unittest.TestCase):
    def test_three_verified_real_seeds_ingest_three_unique_companies(self):
        with SQLiteLeadStore() as store:
            r=expand_cnpj_seeds(store,BrasilAPISource(transport=transport),("33.683.111/0002-80","00.360.305/0001-04","34.028.316/0001-03")); self.assertEqual((r.requested,r.unique_seeds,r.ingested,r.already_present,r.failed),(3,3,3,0,0)); self.assertEqual(len(set(r.company_ids)),3)
    def test_duplicate_seed_is_skipped_before_transport(self):
        calls=[]
        def t(url): calls.append(url); return transport(url)
        with SQLiteLeadStore() as store:
            r=expand_cnpj_seeds(store,BrasilAPISource(transport=t),("33683111000280","33.683.111/0002-80","00360305000104")); self.assertEqual(r.duplicate_seeds_skipped,1); self.assertEqual(len(calls),2)
    def test_invalid_seed_is_recorded_as_failure_without_stopping_batch(self):
        with SQLiteLeadStore() as store:
            r=expand_cnpj_seeds(store,BrasilAPISource(transport=transport),("bad","33683111000280")); self.assertEqual(r.ingested,1); self.assertEqual(r.failed,1)
    def test_one_source_failure_does_not_abort_other_seeds(self):
        def t(url):
            if url.endswith("00360305000104"): raise ValueError("simulated source failure")
            return transport(url)
        with SQLiteLeadStore() as store:
            r=expand_cnpj_seeds(store,BrasilAPISource(transport=t),("33683111000280","00360305000104","34028316000103")); self.assertEqual(r.ingested,2); self.assertEqual(r.failed,1)
    def test_rerun_skips_existing_companies_without_rewriting_evidence(self):
        with SQLiteLeadStore() as store:
            source=BrasilAPISource(transport=transport); a=expand_cnpj_seeds(store,source,PAYLOADS.keys()); b=expand_cnpj_seeds(store,source,PAYLOADS.keys()); self.assertEqual(a.company_ids,b.company_ids); self.assertEqual((b.ingested,b.already_present,b.failed),(0,3,0)); self.assertEqual(len(store.list_evidence()),3)
    def test_requested_and_unique_metrics_are_separate(self):
        with SQLiteLeadStore() as store:
            r=expand_cnpj_seeds(store,BrasilAPISource(transport=transport),("33683111000280","33683111000280","33683111000280")); self.assertEqual(r.requested,3); self.assertEqual(r.unique_seeds,1); self.assertEqual(r.duplicate_seeds_skipped,2)

if __name__=='__main__': unittest.main()
