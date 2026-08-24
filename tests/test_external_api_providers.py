import json
import unittest
from datetime import datetime, timezone

from searchleads.apify_web_search import (
    ApifyActorClient,
    ApifyGoogleSearchConfig,
    ApifyGoogleSearchProvider,
    ApifyPayloadError,
)
from searchleads.dental_external_discovery import discover_dental_candidates_with_provider
from searchleads.dental_repeatable_discovery import CFOVerificationStatus
from searchleads.external_api import WebSearchQuery
from searchleads.persistence import SQLiteLeadStore


class FakeApifyTransport:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def __call__(self, url, headers, body, timeout):
        self.calls.append((url, dict(headers), json.loads(body.decode("utf-8")), timeout))
        return self.payload


class ExternalAPIProviderTests(unittest.TestCase):
    def test_apify_token_is_authorization_header_not_url(self):
        transport = FakeApifyTransport([])
        client = ApifyActorClient(transport=transport)

        client.run_sync_get_dataset_items(
            "apify/google-search-scraper",
            {"queries": "dentista CRO Brasil"},
            token="secret-token",
        )

        url, headers, body, _ = transport.calls[0]
        self.assertIn("apify~google-search-scraper", url)
        self.assertNotIn("secret-token", url)
        self.assertEqual(headers["Authorization"], "Bearer secret-token")
        self.assertEqual(body["queries"], "dentista CRO Brasil")

    def test_apify_provider_persists_raw_dataset_and_projects_hit(self):
        query = WebSearchQuery(
            query_id="q1",
            query='"harmonização orofacial" CRO dentista Brasil',
        )
        payload = [{
            "searchQuery": {
                "term": query.query,
                "url": "https://www.google.com/search?q=hof+cro",
            },
            "organicResults": [{
                "title": "Dra Ana — CRO-SP 12345",
                "url": "https://example.com/dra-ana",
                "description": "Dentista com atuação em harmonização orofacial",
                "position": 1,
            }],
        }]
        transport = FakeApifyTransport(payload)
        provider = ApifyGoogleSearchProvider(
            "token",
            client=ApifyActorClient(transport=transport),
        )

        with SQLiteLeadStore() as store:
            batch = provider.search(
                store,
                (query,),
                retrieved_at=datetime(2026, 8, 24, tzinfo=timezone.utc),
            )
            self.assertEqual(len(batch.evidence), 1)
            self.assertEqual(len(batch.hits), 1)
            self.assertEqual(batch.hits[0].evidence_id, batch.evidence[0].evidence_id)
            persisted = store.get_evidence(batch.evidence[0].evidence_id)
            self.assertIsNotNone(persisted)
            self.assertEqual(persisted.payload["provider"], "apify")
            self.assertEqual(
                persisted.payload["item"]["organicResults"][0]["url"],
                "https://example.com/dra-ana",
            )

    def test_same_apify_payload_is_idempotent(self):
        query = WebSearchQuery(query_id="q1", query="dentista CRO Brasil")
        payload = [{
            "searchQuery": {"term": query.query},
            "organicResults": [{
                "title": "Dentista CRO-SP 12345",
                "url": "https://example.com/a",
                "description": "cirurgião-dentista",
                "position": 1,
            }],
        }]
        provider = ApifyGoogleSearchProvider(
            "token",
            client=ApifyActorClient(transport=FakeApifyTransport(payload)),
        )
        with SQLiteLeadStore() as store:
            first = provider.search(
                store,
                (query,),
                retrieved_at=datetime(2026, 8, 24, 10, tzinfo=timezone.utc),
            )
            second = provider.search(
                store,
                (query,),
                retrieved_at=datetime(2026, 8, 24, 11, tzinfo=timezone.utc),
            )
            self.assertEqual(first.evidence[0].evidence_id, second.evidence[0].evidence_id)
            self.assertEqual(len(store.list_evidence()), 1)

    def test_apify_client_rejects_response_above_bound(self):
        client = ApifyActorClient(transport=FakeApifyTransport([{}, {}]))
        with self.assertRaises(ApifyPayloadError):
            client.run_sync_get_dataset_items(
                "apify~google-search-scraper",
                {"queries": "dentista"},
                token="token",
                max_items=1,
            )

    def test_dental_bridge_keeps_public_cro_as_pending_verification(self):
        query_text = '"cirurgião-dentista" CRO Brasil'
        payload = [{
            "searchQuery": {"term": query_text},
            "organicResults": [{
                "title": "Dra Ana — CRO-SP 12345",
                "url": "https://example.com/dra-ana",
                "description": "Cirurgião-dentista com harmonização orofacial",
                "position": 1,
            }],
        }]
        provider = ApifyGoogleSearchProvider(
            "token",
            client=ApifyActorClient(transport=FakeApifyTransport(payload)),
            config=ApifyGoogleSearchConfig(max_queries=1),
        )
        with SQLiteLeadStore() as store:
            result = discover_dental_candidates_with_provider(
                store,
                provider,
                max_queries=1,
                retrieved_at=datetime(2026, 8, 24, tzinfo=timezone.utc),
            )
            self.assertEqual(len(result.candidates), 1)
            candidate = result.candidates[0]
            self.assertEqual(candidate.cro_state, "SP")
            self.assertEqual(candidate.cro_number, "12345")
            self.assertEqual(
                candidate.cfo_verification_status,
                CFOVerificationStatus.PENDING,
            )
            self.assertTrue(store.get_evidence(candidate.evidence_ids[0]))

    def test_missing_organic_results_is_valid_empty_page(self):
        query = WebSearchQuery(query_id="q1", query="dentista CRO Brasil")
        provider = ApifyGoogleSearchProvider(
            "token",
            client=ApifyActorClient(transport=FakeApifyTransport([
                {"searchQuery": {"term": query.query}},
            ])),
        )
        with SQLiteLeadStore() as store:
            batch = provider.search(
                store,
                (query,),
                retrieved_at=datetime(2026, 8, 24, tzinfo=timezone.utc),
            )
            self.assertEqual(batch.hits, ())
            self.assertEqual(len(batch.evidence), 1)


if __name__ == "__main__":
    unittest.main()
