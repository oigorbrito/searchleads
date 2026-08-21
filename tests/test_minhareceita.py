from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from searchleads.minhareceita import (
    BASE_URL,
    MinhaReceitaPayloadError,
    MinhaReceitaSource,
)
from searchleads.persistence import SQLiteLeadStore


NOW = datetime(2026, 8, 21, 14, 0, tzinfo=timezone.utc)
SERPRO = {
    "cnpj": "33683111000280",
    "identificador_matriz_filial": 2,
    "descricao_identificador_matriz_filial": "FILIAL",
    "nome_fantasia": "REGIONAL BRASILIA-DF",
    "descricao_situacao_cadastral": "ATIVA",
    "data_inicio_atividade": "1967-06-30",
    "cnae_fiscal": 6204000,
    "cnae_fiscal_descricao": "Consultoria em tecnologia da informação",
    "logradouro": "L2 SGAN",
    "numero": "601",
    "bairro": "ASA NORTE",
    "cep": "70836900",
    "uf": "DF",
    "municipio": "BRASILIA",
    "razao_social": "SERVICO FEDERAL DE PROCESSAMENTO DE DADOS (SERPRO)",
    "natureza_juridica": "Empresa Pública",
    "porte": "DEMAIS",
    "qsa": [{"nome_socio": "ANDRE DE CESERO", "qualificacao_socio": "Diretor"}],
}


class MinhaReceitaSourceTests(unittest.TestCase):
    def test_ingest_preserves_full_raw_payload_and_creates_company_candidate(self) -> None:
        calls = []

        def transport(url: str):
            calls.append(url)
            return SERPRO

        with SQLiteLeadStore() as store:
            result = MinhaReceitaSource(transport=transport).ingest(
                store, "33.683.111/0002-80", retrieved_at=NOW
            )

            self.assertEqual(calls, [f"{BASE_URL}/33683111000280"])
            self.assertEqual(result.company.company_id, "company:cnpj:33683111000280")
            self.assertEqual(result.evidence.payload, SERPRO)
            self.assertEqual(store.get_evidence(result.evidence.evidence_id).payload, SERPRO)
            self.assertEqual(store.get_company(result.company.company_id), result.company)

            facts = {fact.predicate: fact.raw_value for fact in result.candidate_facts}
            self.assertEqual(facts["business_registry_id"], "33683111000280")
            self.assertEqual(
                facts["legal_name"],
                "SERVICO FEDERAL DE PROCESSAMENTO DE DADOS (SERPRO)",
            )
            self.assertEqual(facts["trade_name"], "REGIONAL BRASILIA-DF")
            self.assertEqual(facts["registration_status"], "ATIVA")
            self.assertEqual(facts["primary_cnae_code"], 6204000)
            self.assertEqual(facts["city"], "BRASILIA")
            self.assertEqual(facts["state"], "DF")

    def test_source_does_not_extract_people_or_contacts_yet(self) -> None:
        with SQLiteLeadStore() as store:
            result = MinhaReceitaSource(transport=lambda _: SERPRO).ingest(
                store, SERPRO["cnpj"], retrieved_at=NOW
            )
            predicates = {fact.predicate for fact in result.candidate_facts}
            self.assertNotIn("email", predicates)
            self.assertNotIn("phone", predicates)
            self.assertNotIn("person", predicates)

    def test_response_cnpj_must_match_requested_cnpj(self) -> None:
        bad = dict(SERPRO, cnpj="00000000000000")
        with SQLiteLeadStore() as store:
            with self.assertRaises(MinhaReceitaPayloadError):
                MinhaReceitaSource(transport=lambda _: bad).ingest(
                    store, "33683111000280", retrieved_at=NOW
                )
            self.assertEqual(store.list_evidence(), ())
            self.assertIsNone(store.get_company("company:cnpj:33683111000280"))

    def test_legal_name_is_required_before_persistence(self) -> None:
        bad = dict(SERPRO, razao_social="")
        with SQLiteLeadStore() as store:
            with self.assertRaises(MinhaReceitaPayloadError):
                MinhaReceitaSource(transport=lambda _: bad).ingest(
                    store, "33683111000280", retrieved_at=NOW
                )
            self.assertEqual(store.list_evidence(), ())

    def test_same_payload_is_idempotent(self) -> None:
        with SQLiteLeadStore() as store:
            source = MinhaReceitaSource(transport=lambda _: SERPRO)
            first = source.ingest(store, "33683111000280", retrieved_at=NOW)
            second = source.ingest(store, "33683111000280", retrieved_at=NOW)
            self.assertEqual(first, second)
            self.assertEqual(len(store.list_evidence()), 1)

    def test_changed_payload_creates_new_evidence_snapshot(self) -> None:
        changed = dict(SERPRO, nome_fantasia="SERPRO BRASILIA")
        payloads = iter((SERPRO, changed))
        with SQLiteLeadStore() as store:
            source = MinhaReceitaSource(transport=lambda _: next(payloads))
            first = source.ingest(store, "33683111000280", retrieved_at=NOW)
            second = source.ingest(
                store,
                "33683111000280",
                retrieved_at=datetime(2026, 8, 21, 15, 0, tzinfo=timezone.utc),
            )
            self.assertNotEqual(first.evidence.evidence_id, second.evidence.evidence_id)
            self.assertEqual(len(store.list_evidence()), 2)

    def test_roundtrip_survives_database_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "leads.sqlite3"
            with SQLiteLeadStore(path) as store:
                result = MinhaReceitaSource(transport=lambda _: SERPRO).ingest(
                    store, "33683111000280", retrieved_at=NOW
                )
                evidence_id = result.evidence.evidence_id
                company_id = result.company.company_id
            with SQLiteLeadStore(path) as reopened:
                self.assertEqual(reopened.get_evidence(evidence_id).payload, SERPRO)
                self.assertIsNotNone(reopened.get_company(company_id))

    def test_invalid_cnpj_is_rejected_before_transport(self) -> None:
        called = False

        def transport(_: str):
            nonlocal called
            called = True
            return SERPRO

        with SQLiteLeadStore() as store:
            with self.assertRaises(ValueError):
                MinhaReceitaSource(transport=transport).ingest(
                    store, "123", retrieved_at=NOW
                )
        self.assertFalse(called)


if __name__ == "__main__":
    unittest.main()
