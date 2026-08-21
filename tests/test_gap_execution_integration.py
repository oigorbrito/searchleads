from __future__ import annotations

import unittest
from datetime import datetime, timezone

from searchleads.brasilapi import BrasilAPISource
from searchleads.contact_discovery import OfficialPageContactSource
from searchleads.contact_validation import validate_contact_from_official_evidence
from searchleads.domain import Company, ContactKind, ContactStatus
from searchleads.field_fusion import FusionStatus, fuse_candidate_facts, persist_fusion_outcome
from searchleads.gap_automation import ActionKind, GapRequirements, plan_gap_actions
from searchleads.gap_execution import GapLifecycleHooks, run_gap_automation_until_stable
from searchleads.normalization import normalize_candidate_facts
from searchleads.persistence import SQLiteLeadStore

NOW = datetime(2026, 8, 21, 17, 0, tzinfo=timezone.utc)
CNPJ = "33683111000280"
COMPANY_ID = f"company:cnpj:{CNPJ}"
PAYLOAD = {
    "cnpj": CNPJ,
    "razao_social": "SERVICO FEDERAL DE PROCESSAMENTO DE DADOS (SERPRO)",
    "nome_fantasia": "REGIONAL BRASILIA-DF",
    "descricao_situacao_cadastral": "ATIVA",
    "cnae_fiscal": 6204000,
    "cnae_fiscal_descricao": "Consultoria em tecnologia da informação",
    "municipio": "BRASILIA",
    "uf": "DF",
}
CONTACT_URL_1 = "https://www.serpro.gov.br/contact-info"
CONTACT_URL_2 = "https://www.serpro.gov.br/menu/suporte1"
CONTACT_HTML_1 = "<a href='mailto:css.serpro@serpro.gov.br'>css.serpro@serpro.gov.br</a>"
CONTACT_HTML_2 = "<p>E-mail: css.serpro@serpro.gov.br</p>"


class GapExecutionIntegrationTests(unittest.TestCase):
    def test_registry_gap_runs_enrich_resolve_validate_reassess_with_real_modules(self):
        with SQLiteLeadStore() as store:
            store.save_company(Company(COMPANY_ID, created_at=NOW))
            canonical_facts = []
            acquired_candidates = []
            events = []
            requirements = GapRequirements(company_predicates=("state",))

            def plan_factory():
                return plan_gap_actions(
                    COMPANY_ID,
                    requirements,
                    canonical_facts=tuple(canonical_facts),
                )

            def enrich(action):
                self.assertEqual(action.action_kind, ActionKind.BRASILAPI_LOOKUP)
                events.append("enrich")
                result = BrasilAPISource(transport=lambda _: PAYLOAD).ingest(
                    store,
                    CNPJ,
                    retrieved_at=NOW,
                )
                acquired_candidates[:] = result.candidate_facts

            def resolve():
                events.append("resolve")
                projected = tuple(
                    item.normalized_fact if item.normalized_fact is not None else item.source_fact
                    for item in normalize_candidate_facts(acquired_candidates)
                )
                outcome = fuse_candidate_facts(
                    fact for fact in projected if fact.predicate == "state"
                )
                self.assertEqual(outcome.status, FusionStatus.CANONICAL)
                persist_fusion_outcome(store, outcome)
                canonical_facts.append(outcome.canonical_fact)

            def validate():
                events.append("validate")
                canonical = canonical_facts[-1]
                self.assertEqual(canonical.value, "DF")
                self.assertTrue(canonical.provenance.evidence_ids)
                self.assertTrue(
                    all(
                        store.get_evidence(evidence_id) is not None
                        for evidence_id in canonical.provenance.evidence_ids
                    )
                )

            result = run_gap_automation_until_stable(
                plan_factory,
                {ActionKind.BRASILAPI_LOOKUP: enrich},
                clock=lambda: NOW,
                lifecycle_hooks=GapLifecycleHooks(resolve=resolve, validate=validate),
                max_cycles=3,
            )

            self.assertEqual(result.stop_reason, "GAPS_RESOLVED")
            self.assertEqual(events, ["enrich", "resolve", "validate"])
            self.assertEqual(len(result.cycles), 1)
            self.assertEqual(canonical_facts[0].predicate, "state")
            self.assertEqual(canonical_facts[0].value, "DF")
            self.assertFalse(result.final_plan.gaps)

    def test_contact_gap_runs_discovery_then_real_validation_before_reassess(self):
        with SQLiteLeadStore() as store:
            store.save_company(Company(COMPANY_ID, created_at=NOW))
            contacts = []
            observations = {}
            events = []
            requirements = GapRequirements(require_validated_contact=True)

            def plan_factory():
                return plan_gap_actions(
                    COMPANY_ID,
                    requirements,
                    contacts=tuple(contacts),
                )

            def enrich(action):
                self.assertEqual(
                    action.action_kind,
                    ActionKind.OFFICIAL_CONTACT_DISCOVERY,
                )
                events.append("enrich")
                source = OfficialPageContactSource()
                first = source.ingest(
                    store,
                    COMPANY_ID,
                    CONTACT_URL_1,
                    retrieved_at=NOW,
                    html=CONTACT_HTML_1,
                )
                second = source.ingest(
                    store,
                    COMPANY_ID,
                    CONTACT_URL_2,
                    retrieved_at=NOW,
                    html=CONTACT_HTML_2,
                )
                observations["first"] = first
                observations["second"] = second
                contacts.extend(first.contacts)
                contacts.extend(second.contacts)

            def resolve():
                events.append("resolve")
                first = observations["first"]
                email = next(
                    contact
                    for contact in first.contacts
                    if contact.kind is ContactKind.EMAIL
                )
                self.assertEqual(email.status, ContactStatus.DISCOVERED)
                self.assertEqual(email.owner.entity_id, COMPANY_ID)

            def validate():
                events.append("validate")
                first = observations["first"]
                second = observations["second"]
                email = next(
                    contact
                    for contact in first.contacts
                    if contact.kind is ContactKind.EMAIL
                )
                validation = validate_contact_from_official_evidence(
                    store,
                    email.contact_id,
                    (second.evidence.evidence_id,),
                )
                self.assertIsNotNone(validation.validated_contact)
                self.assertEqual(
                    validation.validated_contact.status,
                    ContactStatus.VALIDATED,
                )
                contacts.append(validation.validated_contact)

            result = run_gap_automation_until_stable(
                plan_factory,
                {ActionKind.OFFICIAL_CONTACT_DISCOVERY: enrich},
                clock=lambda: NOW,
                lifecycle_hooks=GapLifecycleHooks(resolve=resolve, validate=validate),
                max_cycles=3,
            )

            self.assertEqual(result.stop_reason, "GAPS_RESOLVED")
            self.assertEqual(events, ["enrich", "resolve", "validate"])
            self.assertTrue(
                any(contact.status is ContactStatus.VALIDATED for contact in contacts)
            )
            self.assertFalse(result.final_plan.gaps)


if __name__ == "__main__":
    unittest.main()
