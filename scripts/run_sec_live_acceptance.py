from __future__ import annotations

import json
import os

from searchleads.sources.sec import acquire_company_tickers_exchange, ingest_company_tickers_exchange


def main() -> int:
    user_agent = os.environ.get("SEARCHLEADS_SEC_USER_AGENT", "").strip()
    if not user_agent:
        raise SystemExit(
            "SEARCHLEADS_SEC_USER_AGENT is required for identified SEC access"
        )

    raw = acquire_company_tickers_exchange(user_agent=user_agent)
    batch = ingest_company_tickers_exchange(raw, limit=25)
    company_ids = {company.id for company in batch.companies}
    cik_facts = [fact for fact in batch.candidate_facts if fact.field_name == "cik"]

    report = {
        "REAL_COMPANIES_INGESTED": len(batch.companies),
        "UNIQUE_COMPANY_IDS": len(company_ids),
        "CIK_FACTS": len(cik_facts),
        "CANDIDATE_FACTS": len(batch.candidate_facts),
        "RAW_EVIDENCE_SHA256": batch.evidence.sha256,
    }
    print(json.dumps(report, sort_keys=True))

    if len(batch.companies) != 25:
        return 1
    if len(company_ids) != 25 or len(cik_facts) != 25:
        return 1
    if len(batch.candidate_facts) != 100:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
