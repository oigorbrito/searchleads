from __future__ import annotations
import argparse,json,os
from searchleads.dental_discovery import build_dental_discovery_queries
from searchleads.external_providers import ApifyGoogleSearchProvider,discover_dental_candidates_with_provider
from searchleads.persistence import SQLiteRepository

def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument('--dry-run',action='store_true'); parser.add_argument('--max-queries',type=int,default=20); args=parser.parse_args(argv)
    queries=build_dental_discovery_queries(max_queries=args.max_queries)
    if args.dry_run:
        print(json.dumps({'mode':'dry-run','query_count':len(queries),'queries':[{'query_id':q.query_id,'query':q.query,'state':q.state,'professional_group':q.professional_group} for q in queries]},ensure_ascii=False,sort_keys=True)); return 0
    token=os.environ.get('APIFY_API_TOKEN','')
    if not token.strip(): raise SystemExit('APIFY_API_TOKEN is required unless --dry-run is used')
    with SQLiteRepository() as repo:
        result=discover_dental_candidates_with_provider(repo,ApifyGoogleSearchProvider(token),max_queries=args.max_queries)
        print(json.dumps({'provider':result.provider_batch.provider_id,'queries':len(result.queries),'evidence':len(result.provider_batch.evidence),'hits':len(result.provider_batch.hits),'candidates':len(result.candidates)},sort_keys=True))
    return 0
if __name__=='__main__': raise SystemExit(main())
