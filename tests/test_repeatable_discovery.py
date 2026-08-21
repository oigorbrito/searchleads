from __future__ import annotations
import unittest
from datetime import datetime, timezone
from searchleads.brasilapi import BrasilAPISource
from searchleads.expansion import expand_cnpj_seeds
from searchleads.persistence import SQLiteLeadStore
from searchleads.repeatable_discovery import RECIPE_ID, SerproOfficeDirectorySource, discover_serpro_office_seeds

NOW=datetime(2026,8,21,13,0,tzinfo=timezone.utc)
URL="https://www.serpro.gov.br/menu/institucional/quem-somos/encontre-o-serpro"
HTML='''<html><body>
<h3>Fortaleza</h3><p>Av. Pontes Vieira, 832</p><p>Fortaleza/Ceará</p><p>CEP: 60.130-240</p><p>CNPJ: 33.683.111/0004-41</p><p>Início das Atividades: 30/6/1967</p>
<h3>Porto Alegre</h3><p>Av. Augusto de Carvalho, 1.133</p><p>Porto Alegre/Rio Grande do Sul</p><p>CEP: 90.010-390</p><p>CNPJ: 33.683.111/0011-70</p><p>Início das Atividades: 30/6/1967</p>
<h3>Recife</h3><p>Av. Parnamirim, 295</p><p>Recife/Pernambuco</p><p>CEP: 52.060-901</p><p>CNPJ: 33.683.111/0005-22</p><p>Início das Atividades: 30/6/1967</p>
<h3>Brasília</h3><p>SGAN Av. L-2 Norte Quadra 601 – Módulo G</p><p>Brasília/Distrito Federal</p><p>CEP: 70.836-900</p><p>CNPJ: 33.683.111/0002-80</p><p>Início das Atividades: 30/6/1967</p>
</body></html>'''
PAYLOADS={cnpj:{"cnpj":cnpj,"razao_social":"SERVICO FEDERAL DE PROCESSAMENTO DE DADOS (SERPRO)","nome_fantasia":"SERPRO","descricao_situacao_cadastral":"ATIVA","cnae_fiscal":6204000,"cnae_fiscal_descricao":"Consultoria em tecnologia da informação","municipio":city.upper(),"uf":state} for cnpj,city,state in [("33683111000441","Fortaleza","CE"),("33683111001170","Porto Alegre","RS"),("33683111000522","Recife","PE"),("33683111000280","Brasília","DF")]}
def transport(url): return PAYLOADS[url.rstrip('/').split('/')[-1]]

class RepeatableDiscoveryTests(unittest.TestCase):
    def test_known_recipe_discovers_four_office_cnpj_seeds(self):
        seeds=discover_serpro_office_seeds(HTML); self.assertEqual(len(seeds),4); self.assertEqual({s.cnpj for s in seeds},set(PAYLOADS)); self.assertTrue(all(s.recipe_id==RECIPE_ID for s in seeds))
    def test_recipe_is_deterministic_on_same_snapshot(self): self.assertEqual(discover_serpro_office_seeds(HTML),discover_serpro_office_seeds(HTML))
    def test_same_recipe_handles_later_snapshot_with_new_block(self):
        later=HTML.replace('</body>','<h3>São Paulo</h3><p>Rua 941</p><p>São Paulo/São Paulo</p><p>CEP: 04.766-900</p><p>CNPJ: 33.683.111/0009-56</p><p>Início das Atividades: 30/6/1967</p></body>'); seeds=discover_serpro_office_seeds(later); self.assertEqual(len(seeds),5); self.assertIn('33683111000956',{s.cnpj for s in seeds})
    def test_discovery_page_is_preserved_once_with_recipe_metadata(self):
        with SQLiteLeadStore() as store:
            r=SerproOfficeDirectorySource().ingest(store,URL,HTML,retrieved_at=NOW); self.assertEqual(r.evidence.payload['body'],HTML); self.assertEqual(r.evidence.payload['recipe_id'],RECIPE_ID); self.assertTrue(all(s.discovery_evidence_id==r.evidence.evidence_id for s in r.seeds))
    def test_discovered_seeds_feed_existing_structured_acquisition(self):
        with SQLiteLeadStore() as store:
            discovery=SerproOfficeDirectorySource().ingest(store,URL,HTML,retrieved_at=NOW); expanded=expand_cnpj_seeds(store,BrasilAPISource(transport=transport),(s.cnpj for s in discovery.seeds)); self.assertEqual((expanded.unique_seeds,expanded.ingested,expanded.failed),(4,4,0)); self.assertEqual(len(store.list_evidence()),5)
    def test_duplicate_cnpj_on_page_is_emitted_once(self): self.assertEqual(len(discover_serpro_office_seeds(HTML+"<p>CNPJ: 33.683.111/0002-80</p>")),4)

if __name__=='__main__': unittest.main()
