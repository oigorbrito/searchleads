#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from searchleads.acceptance import run_acceptance_fixture


def main():
    r=run_acceptance_fixture()
    for key,value in r.gates:
        print(f"{key}={value}")
    print(f"DISCOVERED_COMPANIES={r.discovered_companies}")
    print(f"EVIDENCE_COUNT={r.evidence_count}")
    print(f"NORMALIZED_CANDIDATES={r.normalized_candidate_count}")
    print(f"NORMALIZATION_RULES={r.normalization_rule_count}")
    print(f"VALIDATED_CONTACTS={r.validated_contacts}")
    print(f"PERSON_PROFESSIONAL_CONTACTS={r.person_professional_contacts}")
    print(f"PERSON_PROFESSIONAL_PROFILES={r.person_professional_profiles}")
    print(f"PEOPLE_COUNT={r.people_count}")
    print(f"ROLES_COUNT={r.roles_count}")
    print(f"PERSON_ER_DECISIONS={r.person_er_decisions}")
    print(f"PERSON_ER_REVIEW_ITEMS={r.person_er_review_items}")
    print(f"CONFLICTS={r.conflicts}")
    print(f"REVIEW_ITEMS={r.review_items}")
    print(f"TECHNICAL_QUALIFICATION={r.technical_qualification_status.value}")
    print(f"BUSINESS_QUALIFICATION={r.business_qualification_status.value}")
    print(f"EXPORT_SHA256={r.export_sha256}")
    print(f"EXPORT_BYTES={len(r.export_json.encode('utf-8'))}")


if __name__=='__main__':
    main()
