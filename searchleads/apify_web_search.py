"""Apify-backed web-search provider for SearchLeads.

The provider uses Apify's synchronous Actor endpoint with the maintained
`apify/google-search-scraper` Actor by default. Raw Actor dataset items are
persisted as Evidence before organic results are projected into the provider-
neutral WebSearchHit contract.

An Apify result is discovery evidence, not authoritative professional identity,
credential, contact validity, or learning intent.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Callable, Iterable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .domain import Evidence, Source, SourceType
from .external_api import WebSearchBatch, WebSearchHit, WebSearchQuery
from .persistence import SQLiteLeadStore


APIFY_API_BASE_URL = "https://api.apify.com/v2"
DEFAULT_GOOGLE_SEARCH_ACTOR = "apify~google-search-scraper"
APIFY_GOOGLE_SEARCH_PROVIDER_ID = "apify-google-search-v1"
_AGENT = "searchleads.apify_google_search.v1"
_ACTOR_ID = re.compile(r"^[A-Za-z0-9_.-]+[~/][A-Za-z0-9_.-]+$")


class ApifyAPIError(RuntimeError):
    """Base error for Apify acquisition/response validation."""


class ApifyTransportError(ApifyAPIError):
    """Raised when the Apify HTTP request fails."""


class ApifyPayloadError(ApifyAPIError):
    """Raised when an Actor response cannot be safely interpreted."""


JsonPostTransport = Callable[[str, Mapping[str, str], bytes, float], Any]


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _normalized_actor_id(actor_id: str) -> str:
    value = actor_id.strip()
    if not _ACTOR_ID.fullmatch(value):
        raise ValueError("actor_id must be in owner/name or owner~name form")
    owner, name = re.split(r"[~/]", value, maxsplit=1)
    return f"{owner}~{name}"


def _http_post_json(
    url: str,
    headers: Mapping[str, str],
    body: bytes,
    timeout: float,
) -> Any:
    request = Request(url, data=body, headers=dict(headers), method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return json.loads(response.read().decode(charset))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ApifyTransportError(f"Apify request failed: {exc}") from exc


class ApifyActorClient:
    """Small REST client with injectable transport and no token in request URLs."""

    def __init__(
        self,
        transport: JsonPostTransport | None = None,
        *,
        base_url: str = APIFY_API_BASE_URL,
    ) -> None:
        self._transport = transport or _http_post_json
        self._base_url = base_url.rstrip("/")

    def run_sync_get_dataset_items(
        self,
        actor_id: str,
        run_input: Mapping[str, Any],
        *,
        token: str,
        timeout_seconds: float = 120.0,
        max_items: int = 200,
    ) -> tuple[Mapping[str, Any], ...]:
        normalized_actor = _normalized_actor_id(actor_id)
        if not token.strip():
            raise ValueError("Apify token must be non-blank")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")
        if max_items < 1:
            raise ValueError("max_items must be >= 1")
        if not isinstance(run_input, Mapping):
            raise TypeError("run_input must be a mapping")

        actor_path = quote(normalized_actor, safe="~")
        url = (
            f"{self._base_url}/actors/{actor_path}/"
            "run-sync-get-dataset-items?clean=true&format=json"
        )
        payload = self._transport(
            url,
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token.strip()}",
                "User-Agent": "searchleads/0.4 (+https://github.com/tihotm/searchleads)",
            },
            _canonical_json_bytes(dict(run_input)),
            timeout_seconds,
        )
        if isinstance(payload, bytes):
            try:
                payload = json.loads(payload.decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise ApifyPayloadError("Apify response bytes are not valid JSON") from exc
        elif isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise ApifyPayloadError("Apify response text is not valid JSON") from exc

        if not isinstance(payload, list):
            raise ApifyPayloadError("Apify synchronous dataset response must be a JSON array")
        if len(payload) > max_items:
            raise ApifyPayloadError(
                f"Apify returned {len(payload)} items, exceeding bounded max_items={max_items}"
            )
        if any(not isinstance(item, Mapping) for item in payload):
            raise ApifyPayloadError("every Apify dataset item must be a JSON object")
        return tuple(dict(item) for item in payload)


@dataclass(frozen=True, slots=True)
class ApifyGoogleSearchConfig:
    actor_id: str = DEFAULT_GOOGLE_SEARCH_ACTOR
    max_pages_per_query: int = 1
    max_queries: int = 20
    max_dataset_items: int = 200
    max_concurrency: int = 5

    def __post_init__(self) -> None:
        _normalized_actor_id(self.actor_id)
        for value, name in (
            (self.max_pages_per_query, "max_pages_per_query"),
            (self.max_queries, "max_queries"),
            (self.max_dataset_items, "max_dataset_items"),
            (self.max_concurrency, "max_concurrency"),
        ):
            if value < 1:
                raise ValueError(f"{name} must be >= 1")


class ApifyGoogleSearchProvider:
    provider_id = APIFY_GOOGLE_SEARCH_PROVIDER_ID

    def __init__(
        self,
        token: str,
        *,
        client: ApifyActorClient | None = None,
        config: ApifyGoogleSearchConfig = ApifyGoogleSearchConfig(),
    ) -> None:
        if not token.strip():
            raise ValueError("Apify token must be non-blank")
        self._token = token.strip()
        self._client = client or ApifyActorClient()
        self.config = config

    @staticmethod
    def _query_key(value: str) -> str:
        return " ".join(value.split()).casefold()

    def search(
        self,
        store: SQLiteLeadStore,
        queries: Iterable[WebSearchQuery],
        *,
        retrieved_at: datetime | None = None,
    ) -> WebSearchBatch:
        query_items = tuple(queries)
        if not query_items:
            return WebSearchBatch(provider_id=self.provider_id, hits=(), evidence=())
        if len(query_items) > self.config.max_queries:
            raise ValueError(
                f"query count {len(query_items)} exceeds max_queries={self.config.max_queries}"
            )
        if len({query.query_id for query in query_items}) != len(query_items):
            raise ValueError("query IDs must be unique within a provider batch")

        country_codes = {query.country_code.strip().lower() for query in query_items}
        language_codes = {query.language_code.strip().lower() for query in query_items}
        if len(country_codes) != 1 or len(language_codes) != 1:
            raise ValueError("one Apify Actor batch must use one country and one language")

        run_input = {
            "queries": "\n".join(query.query for query in query_items),
            "countryCode": next(iter(country_codes)),
            "languageCode": next(iter(language_codes)),
            "maxPagesPerQuery": self.config.max_pages_per_query,
            "includeUnfilteredResults": False,
            "mobileResults": False,
            "saveHtml": False,
            "saveHtmlToKeyValueStore": False,
            "maxConcurrency": self.config.max_concurrency,
        }
        raw_items = self._client.run_sync_get_dataset_items(
            self.config.actor_id,
            run_input,
            token=self._token,
            max_items=self.config.max_dataset_items,
        )

        fetched_at = retrieved_at or datetime.now(timezone.utc)
        if fetched_at.tzinfo is None or fetched_at.utcoffset() is None:
            raise ValueError("retrieved_at must be timezone-aware")

        normalized_actor = _normalized_actor_id(self.config.actor_id)
        source = Source(
            source_id=f"source:apify:actor:{normalized_actor}",
            source_type=SourceType.DATASET,
            locator=f"{APIFY_API_BASE_URL}/actors/{normalized_actor}",
            label="Apify Google Search Results Scraper",
        )
        store.save_source(source)

        query_by_text = {
            self._query_key(query.query): query for query in query_items
        }
        persisted: list[Evidence] = []
        hits: list[WebSearchHit] = []

        for raw_item in raw_items:
            wrapped_payload = {
                "provider": "apify",
                "actor_id": normalized_actor,
                "agent": _AGENT,
                "item": dict(raw_item),
            }
            digest = _sha256(wrapped_payload)
            evidence_id = f"evidence:apify:google-search:{digest[:20]}"
            existing = store.get_evidence(evidence_id)
            if existing is not None:
                evidence = existing
            else:
                search_query = raw_item.get("searchQuery")
                locator = source.locator
                if isinstance(search_query, Mapping) and str(search_query.get("url", "")).strip():
                    locator = str(search_query["url"])
                evidence = Evidence(
                    evidence_id=evidence_id,
                    source_id=source.source_id,
                    retrieved_at=fetched_at,
                    payload=wrapped_payload,
                    locator=locator,
                    content_hash=f"sha256:{digest}",
                )
                store.save_evidence(evidence)
            persisted.append(evidence)

            search_query = raw_item.get("searchQuery")
            term = ""
            if isinstance(search_query, Mapping):
                term = str(search_query.get("term", "")).strip()
            if not term:
                term = str(raw_item.get("query", "")).strip()
            source_query = query_by_text.get(self._query_key(term))
            if source_query is None:
                continue

            organic_results = raw_item.get("organicResults", ())
            if not isinstance(organic_results, list):
                raise ApifyPayloadError("organicResults must be an array when present")
            for organic in organic_results:
                if not isinstance(organic, Mapping):
                    raise ApifyPayloadError("organic result must be an object")
                title = str(organic.get("title", "")).strip()
                url = str(organic.get("url", "")).strip()
                if not title or not url:
                    continue
                snippet = str(organic.get("description", "")).strip()
                raw_position = organic.get("position")
                position = raw_position if isinstance(raw_position, int) and raw_position >= 1 else None
                hits.append(WebSearchHit(
                    query_id=source_query.query_id,
                    title=title,
                    url=url,
                    snippet=snippet,
                    position=position,
                    evidence_id=evidence.evidence_id,
                ))

        unique_evidence = {item.evidence_id: item for item in persisted}
        return WebSearchBatch(
            provider_id=self.provider_id,
            hits=tuple(hits),
            evidence=tuple(unique_evidence.values()),
        )
