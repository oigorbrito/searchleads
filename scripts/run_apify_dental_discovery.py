#!/usr/bin/env python3
"""Run the dental deterministic query plan through Apify Google Search."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from searchleads.apify_web_search import ApifyGoogleSearchConfig, ApifyGoogleSearchProvider
from searchleads.dental_external_discovery import discover_dental_candidates_with_provider
from searchleads.dental_facial_surgery_icp import (
    BrazilRegion,
    DEFAULT_DENTAL_FACIAL_SURGERY_ICP_V1,
    select_dental_icp,
)
from searchleads.dental_repeatable_discovery import build_dental_discovery_queries
from searchleads.persistence import SQLiteLeadStore


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="searchleads-apify.db")
    parser.add_argument("--output")
    parser.add_argument("--max-queries", type=int, default=4)
    parser.add_argument("--state", action="append", default=[])
    parser.add_argument(
        "--region",
        action="append",
        choices=[item.value for item in BrazilRegion],
        default=[],
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print deterministic queries without calling Apify",
    )
    return parser


def _candidate_dict(candidate):
    return {
        "candidate_id": candidate.candidate_id,
        "display_name_hint": candidate.display_name_hint,
        "source_url": candidate.source_url,
        "evidence_ids": list(candidate.evidence_ids),
        "cro_state": candidate.cro_state,
        "cro_number": candidate.cro_number,
        "observed_title_group": (
            candidate.observed_title_group.value
            if candidate.observed_title_group is not None
            else None
        ),
        "facial_relevance_terms": list(candidate.facial_relevance_terms),
        "cfo_verification_status": candidate.cfo_verification_status.value,
    }


def main() -> int:
    args = _parser().parse_args()
    regions = tuple(BrazilRegion(value) for value in args.region)
    icp = select_dental_icp(
        DEFAULT_DENTAL_FACIAL_SURGERY_ICP_V1,
        regions=regions or None,
        states=tuple(args.state) or None,
    )

    if args.dry_run:
        queries = build_dental_discovery_queries(icp, max_queries=args.max_queries)
        print(json.dumps(
            [{"query_id": item.query_id, "query": item.query} for item in queries],
            ensure_ascii=False,
            indent=2,
        ))
        return 0

    token = os.environ.get("APIFY_API_TOKEN", "").strip()
    if not token:
        raise SystemExit("APIFY_API_TOKEN is required unless --dry-run is used")

    provider = ApifyGoogleSearchProvider(
        token,
        config=ApifyGoogleSearchConfig(max_queries=args.max_queries),
    )
    with SQLiteLeadStore(args.db) as store:
        result = discover_dental_candidates_with_provider(
            store,
            provider,
            icp=icp,
            max_queries=args.max_queries,
        )
        payload = {
            "provider": result.provider_batch.provider_id,
            "queries": len(result.queries),
            "evidence": len(result.provider_batch.evidence),
            "search_hits": len(result.provider_batch.hits),
            "candidates": [_candidate_dict(item) for item in result.candidates],
        }

    encoded = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(encoded + "\n", encoding="utf-8")
    else:
        print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
