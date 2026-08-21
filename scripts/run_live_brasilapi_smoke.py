#!/usr/bin/env python3
"""Narrow manual closure command for the literal WU3 live-ingestion gate.

Run only in an environment with outbound DNS/HTTPS. This performs one point
lookup for the already-used SERPRO CNPJ; it is not a crawler or bulk scan.
"""
from __future__ import annotations

from searchleads.brasilapi import BrasilAPISource
from searchleads.persistence import SQLiteLeadStore

CNPJ = "33683111000280"


def main() -> None:
    with SQLiteLeadStore() as store:
        result = BrasilAPISource().ingest(store, CNPJ)
        if result.company.company_id != f"company:cnpj:{CNPJ}":
            raise SystemExit("FAIL: unexpected company ID")
        if not result.evidence.payload:
            raise SystemExit("FAIL: live evidence payload is empty")
        predicates = {fact.predicate for fact in result.candidate_facts}
        required = {"business_registry_id", "legal_name"}
        if not required.issubset(predicates):
            raise SystemExit(f"FAIL: missing required predicates: {sorted(required - predicates)}")
        print("WU3_LIVE_HTTP=PASS")
        print(f"COMPANY_ID={result.company.company_id}")
        print(f"EVIDENCE_ID={result.evidence.evidence_id}")
        print(f"CANDIDATE_FACTS={len(result.candidate_facts)}")


if __name__ == "__main__":
    main()
