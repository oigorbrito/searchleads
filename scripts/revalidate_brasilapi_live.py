from __future__ import annotations

import json

from searchleads.persistence import SQLiteRepository
from searchleads.sources.brasilapi import BrasilAPISource


KNOWN_PUBLIC_CNPJ = "00000000000191"


def main() -> int:
    repository = SQLiteRepository(":memory:")
    try:
        result = BrasilAPISource().ingest(KNOWN_PUBLIC_CNPJ, repository)
        fields = sorted(fact.field_name for fact in result.candidate_facts)
        required = {"business_registry_id", "legal_name", "registration_status"}
        missing = sorted(required.difference(fields))
        payload = {
            "status": "PASS" if not missing else "CONTRACT_FAIL",
            "source_id": result.source.source_id,
            "http_status": result.evidence.metadata.get("http_status"),
            "content_digest": result.evidence.content_digest,
            "captured_at": result.evidence.captured_at.isoformat(),
            "field_names": fields,
            "missing_required_fields": missing,
            "raw_payload_printed": False,
            "point_lookup_count": 1,
        }
        print(json.dumps(payload, sort_keys=True))
        return 0 if not missing else 2
    finally:
        repository.close()


if __name__ == "__main__":
    raise SystemExit(main())
