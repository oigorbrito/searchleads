"""Versioned known-source extraction for REPEATABLE_WEB_DISCOVERY_V1.

This is intentionally a source-specific recipe, not a generic crawler or an
LLM-per-page extraction loop. It consumes a preserved HTML snapshot of the
known SERPRO office directory and emits evidence-linked CNPJ seeds.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
import hashlib
import re
from typing import Any, Callable, Generic, Protocol, TypeVar
from urllib.parse import urlsplit, urlunsplit

from searchleads.domain import Evidence, Source

RECIPE_ID = "serpro_office_directory_v1"
DIRECTORY_URL = "https://www.serpro.gov.br/menu/institucional/quem-somos/encontre-o-serpro"
SOURCE_TYPE = "known-web-directory"
_AGENT = "searchleads.repeatable_discovery.serpro_offices.v1"
_IGNORED = {"script", "style", "template", "noscript"}
_CNPJ_LABEL = re.compile(
    r"\bCNPJ\s*:\s*([0-9A-Z]{2}\.[0-9A-Z]{3}\.[0-9A-Z]{3}/[0-9A-Z]{4}-[0-9A-Z]{2})\b",
    re.I,
)
_LOCATION = re.compile(r"^\s*([^/\n]{2,80})\s*/\s*([^/\n]{2,80})\s*$")
_CNPJ_KEY = re.compile(r"^[0-9A-Z]{14}$")


@dataclass(frozen=True, slots=True)
class DiscoveredCompanySeed:
    cnpj: str
    label: str | None
    city: str | None
    state_text: str | None
    discovery_evidence_id: str | None = None
    recipe_id: str = RECIPE_ID

    def __post_init__(self) -> None:
        if _CNPJ_KEY.fullmatch(self.cnpj) is None:
            raise ValueError("cnpj seed must match the WU3 14-character routing-key contract")
        if self.discovery_evidence_id is not None and not self.discovery_evidence_id.strip():
            raise ValueError("discovery_evidence_id must not be blank")
        if self.recipe_id != RECIPE_ID:
            raise ValueError("seed recipe_id does not match this recipe")


@dataclass(frozen=True, slots=True)
class RepeatableDiscoveryResult:
    source: Source
    evidence: Evidence
    seeds: tuple[DiscoveredCompanySeed, ...]
    evidence_was_new: bool
    recipe_id: str = RECIPE_ID

    def __post_init__(self) -> None:
        if self.recipe_id != RECIPE_ID:
            raise ValueError("result recipe_id mismatch")
        if any(seed.discovery_evidence_id != self.evidence.evidence_id for seed in self.seeds):
            raise ValueError("all discovered seeds must link to discovery Evidence")


T = TypeVar("T")

class Repository(Protocol):
    def load(self, record_type: type[T], record_id: str) -> T | None: ...
    def save(self, record: object) -> bool: ...


R = TypeVar("R")

@dataclass(frozen=True, slots=True)
class SeedAcquisitionItem(Generic[R]):
    seed: DiscoveredCompanySeed
    succeeded: bool
    result: R | None = None
    error_type: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if self.succeeded:
            if self.result is None or self.error_type is not None or self.error_message is not None:
                raise ValueError("successful acquisition item must contain only a result")
        elif self.result is not None or not self.error_type:
            raise ValueError("failed acquisition item requires an error and no result")


@dataclass(frozen=True, slots=True)
class SeedAcquisitionRun(Generic[R]):
    items: tuple[SeedAcquisitionItem[R], ...]

    @property
    def attempted(self) -> int: return len(self.items)
    @property
    def succeeded(self) -> int: return sum(item.succeeded for item in self.items)
    @property
    def failed(self) -> int: return self.attempted - self.succeeded


@dataclass(frozen=True, slots=True)
class _Block:
    label: str | None
    texts: tuple[str, ...]


class _DirectoryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self._heading_depth = 0
        self._heading_parts: list[str] = []
        self._label: str | None = None
        self._texts: list[str] = []
        self.blocks: list[_Block] = []

    def _finish(self) -> None:
        if self._label is not None or self._texts:
            self.blocks.append(_Block(self._label, tuple(self._texts)))
        self._label = None
        self._texts = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        if tag in _IGNORED:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        if tag in {"h2", "h3"}:
            self._finish()
            self._heading_depth = 1
            self._heading_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if tag in _IGNORED:
            if self._ignored_depth:
                self._ignored_depth -= 1
            return
        if self._ignored_depth:
            return
        if tag in {"h2", "h3"} and self._heading_depth:
            self._heading_depth = 0
            label = " ".join(" ".join(self._heading_parts).split())
            self._label = label or None

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        text = " ".join(data.split())
        if not text:
            return
        if self._heading_depth:
            self._heading_parts.append(text)
        else:
            self._texts.append(text)

    def close(self) -> None:
        super().close()
        self._finish()


def _normalize_directory_url(url: str) -> str:
    try:
        parsed = urlsplit(url.strip())
        port = parsed.port
    except (ValueError, AttributeError) as exc:
        raise ValueError("directory URL is invalid") from exc
    if parsed.scheme.casefold() != "https" or not parsed.hostname:
        raise ValueError("directory URL must be the known HTTPS SERPRO directory")
    host = parsed.hostname.casefold()
    if host != "www.serpro.gov.br" or parsed.path.rstrip("/") != urlsplit(DIRECTORY_URL).path.rstrip("/"):
        raise ValueError("recipe can only run on the known SERPRO office directory")
    if port not in (None, 443) or parsed.username or parsed.password:
        raise ValueError("directory URL must not contain credentials or a non-default port")
    return urlunsplit(("https", host, urlsplit(DIRECTORY_URL).path, "", ""))


def _compact_cnpj(value: str) -> str:
    compact = re.sub(r"[.\-/\s]", "", value).upper()
    if _CNPJ_KEY.fullmatch(compact) is None:
        raise ValueError("invalid CNPJ routing key")
    return compact


def _location(texts: tuple[str, ...]) -> tuple[str | None, str | None]:
    for text in texts:
        match = _LOCATION.fullmatch(text)
        if match and not text.casefold().startswith("cnpj"):
            return match.group(1).strip(), match.group(2).strip()
    return None, None


def discover_serpro_office_seeds(html: str) -> tuple[DiscoveredCompanySeed, ...]:
    if not isinstance(html, str):
        raise TypeError("html must be text")
    parser = _DirectoryParser()
    parser.feed(html)
    parser.close()
    emitted: dict[str, DiscoveredCompanySeed] = {}
    for block in parser.blocks:
        body = "\n".join(block.texts)
        values = {_compact_cnpj(match.group(1)) for match in _CNPJ_LABEL.finditer(body)}
        if len(values) != 1:
            continue
        cnpj = next(iter(values))
        if cnpj in emitted:
            continue
        city, state_text = _location(block.texts)
        emitted[cnpj] = DiscoveredCompanySeed(cnpj, block.label, city, state_text)
    return tuple(emitted.values())


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def ingest_serpro_office_directory(
    repository: Repository,
    url: str,
    html: str,
    captured_at: datetime,
) -> RepeatableDiscoveryResult:
    normalized_url = _normalize_directory_url(url)
    if not isinstance(html, str):
        raise TypeError("html must be text")
    if captured_at.tzinfo is None:
        raise ValueError("captured_at must be timezone-aware")
    source_id = f"source:repeatable-web-discovery:{_digest(RECIPE_ID + chr(0) + normalized_url)[:24]}"
    source = Source(source_id, SOURCE_TYPE, normalized_url, "SERPRO office directory recipe")
    repository.save(source)
    body_digest = _digest(html)
    evidence_id = f"evidence:repeatable-web-discovery:{_digest(RECIPE_ID + chr(0) + normalized_url + chr(0) + html)}"
    existing = repository.load(Evidence, evidence_id)
    if existing is None:
        evidence = Evidence(
            evidence_id,
            source_id,
            normalized_url,
            captured_at,
            html,
            f"sha256:{body_digest}",
            {"recipe_id": RECIPE_ID, "agent": _AGENT, "content_type": "text/html"},
        )
        repository.save(evidence)
        was_new = True
    else:
        if (
            existing.source_id != source_id
            or existing.locator != normalized_url
            or existing.raw_payload != html
            or existing.content_digest != f"sha256:{body_digest}"
            or existing.metadata.get("recipe_id") != RECIPE_ID
        ):
            raise ValueError("content-addressed discovery Evidence collision")
        evidence = existing
        was_new = False
    seeds = tuple(
        DiscoveredCompanySeed(seed.cnpj, seed.label, seed.city, seed.state_text, evidence.evidence_id)
        for seed in discover_serpro_office_seeds(html)
    )
    return RepeatableDiscoveryResult(source, evidence, seeds, was_new)


def acquire_discovered_seeds(
    discovery: RepeatableDiscoveryResult,
    acquire: Callable[[str], R],
) -> SeedAcquisitionRun[R]:
    items: list[SeedAcquisitionItem[R]] = []
    for seed in discovery.seeds:
        try:
            result = acquire(seed.cnpj)
        except Exception as exc:  # caller decides the structured acquisition implementation
            items.append(SeedAcquisitionItem(seed, False, error_type=type(exc).__name__, error_message=str(exc)))
        else:
            items.append(SeedAcquisitionItem(seed, True, result=result))
    return SeedAcquisitionRun(tuple(items))
