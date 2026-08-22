#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from searchleads.acceptance import run_acceptance_fixture
from searchleads.dental_facial_surgery_icp import DEFAULT_DENTAL_FACIAL_SURGERY_ICP_V1

def main():
    r=run_acceptance_fixture(icp_policy_id=DEFAULT_DENTAL_FACIAL_SURGERY_ICP_V1.policy_id)
    for key,value in r.gates: print(f"{key}={value}")
    print(f"DISCOVERED_COMPANIES={r.discovered_companies}")
    print(f"EVIDENCE_COUNT={r.evidence_count}")
    print(f"VALIDATED_CONTACTS={r.validated_contacts}")
    print(f"PEOPLE_COUNT={r.people_count}")
    print(f"ROLES_COUNT={r.roles_count}")
    print(f"CONFLICTS={r.conflicts}")
    print(f"REVIEW_ITEMS={r.review_items}")
    print(f"TECHNICAL_QUALIFICATION={r.technical_qualification_status.value}")
    print(f"BUSINESS_QUALIFICATION={r.business_qualification_status.value}")
    print(f"EXPORT_SHA256={r.export_sha256}")
    print(f"EXPORT_BYTES={len(r.export_json.encode('utf-8'))}")
if __name__=='__main__': main()
