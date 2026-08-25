"""Evidence-preserving company contact discovery for CONTACT_DISCOVERY_V1."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
import hashlib
import re
from typing import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from searchleads.domain import Company, ContactKind, ContactPoint, ContactStatus, Evidence, Source, utc_now
from searchleads.persistence import SQLiteRepository

AGENT = "searchleads.contact_discovery.company_page.v1"
USER_AGENT = "searchleads-contact-discovery-v1 (+https://github.com/tihotm/searchleads)"
_EMAIL_RE = re.compile(r"(?<![\w.+-])([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})(?![\w.-])", re.I)
_PHONE_LABEL_RE = re.compile(
    r"(?:telefone|fone|tel\.?|phone)\s*:?[\s\u00a0]*(\+?\d[\d\s()./-]{5,}\d)", re.I
)
_IGNORED_TEXT_TAGS = {"script", "style", "noscript", "template"}


class ContactDiscoveryError(RuntimeError):
    """Base error for company contact discovery."""


class ContactAcquisitionError(ContactDiscoveryError):
    """No usable HTTP response was acquired."""


class ContactPageResponseError(ContactDiscoveryError):
    """Non-success HTTP response whose body was persisted as Evidence."""

    def __init__(self, status_code: int, evidence_id: str) -> None:
        self.status_code = status_code
        self.evidence_id = evidence_id
        super().__init__(f"contact page returned HTTP {status_code}; evidence={evidence_id}")


@dataclass(frozen=True, slots=True)
class HTTPPageObservation:
    url: str
    status_code: int
    raw_html: str
    captured_at: datetime = field(default_factory=utc_now)
    headers: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_page_url(self.url)
        if not 100 <= self.status_code <= 599:
            raise ValueError("status_code must be a valid HTTP status")
        if not isinstance(self.raw_html, str):
            raise TypeError("raw_html must be text")
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class DiscoveredContact:
    kind: ContactKind
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("discovered contact value must not be blank")


@dataclass(frozen=True, slots=True)
class ContactDiscoveryResult:
    company: Company
    source: Source
    evidence: Evidence
    contacts: tuple[ContactPoint, ...]
    evidence_was_new: bool


PageTransport = Callable[[str], HTTPPageObservation]


def _require_page_url(url: str) -> None:
    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        raise ValueError("url must be an absolute http/https URL") from exc
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("url must be an absolute http/https URL")


def _decode_body(body: bytes, headers: object) -> str:
    charset = "utf-8"
    getter = getattr(headers, "get_content_charset", None)
    if callable(getter):
        charset = getter() or "utf-8"
    try:
        return body.decode(charset)
    except (LookupError, UnicodeDecodeError) as exc:
        raise ContactAcquisitionError(f"contact page is not decodable text ({charset})") from exc


def _headers(headers: object) -> dict[str, str]:
    items = getattr(headers, "items", None)
    return {} if not callable(items) else dict(sorted((str(k).lower(), str(v)) for k, v in items()))


def http_get(url: str, *, timeout: float = 20.0) -> HTTPPageObservation:
    _require_page_url(url)
    request = Request(
        url,
        headers={"Accept": "text/html,application/xhtml+xml", "User-Agent": USER_AGENT},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return HTTPPageObservation(
                url,
                int(response.status),
                _decode_body(response.read(), response.headers),
                utc_now(),
                _headers(response.headers),
            )
    except HTTPError as exc:
        return HTTPPageObservation(
            url,
            exc.code,
            _decode_body(exc.read(), exc.headers),
            utc_now(),
            _headers(exc.headers),
        )
    except (URLError, TimeoutError, OSError) as exc:
        raise ContactAcquisitionError(f"failed to acquire {url}: {exc}") from exc


class _ContactParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []
        self.form_count = 0
        self.text_parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        if tag in _IGNORED_TEXT_TAGS:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        data = {k.casefold(): v for k, v in attrs if k}
        if tag == "a" and data.get("href"):
            self.hrefs.append(data["href"] or "")
        elif tag == "form":
            self.form_count += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in _IGNORED_TEXT_TAGS and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth and data.strip():
            self.text_parts.append(data)


def _valid_email(value: str) -> bool:
    if len(value) > 254 or value.count("@") != 1:
        return False
    local, domain = value.rsplit("@", 1)
    if not local or len(local) > 64 or not domain or "." not in domain:
        return False
    if re.fullmatch(r"[A-Z0-9._%+-]+", local, re.I) is None:
        return False
    if re.fullmatch(r"[A-Z0-9.-]+", domain, re.I) is None:
        return False
    if len(domain) > 253 or domain.startswith(".") or domain.endswith(".") or ".." in domain:
        return False
    labels = domain.split(".")
    return all(1 <= len(label) <= 63 and not label.startswith("-") and not label.endswith("-") for label in labels)


def _email_from_mailto(href: str) -> str | None:
    value = unquote(href.split(":", 1)[1].split("?", 1)[0]).strip()
    return value if _valid_email(value) else None


def _phone(value: str) -> str | None:
    cleaned = " ".join(unquote(value).replace("\u00a0", " ").split()).strip(" ,;.")
    digits = re.sub(r"\D", "", cleaned)
    if not 7 <= len(digits) <= 15:
        return None
    return cleaned


def _normalized_http_url(base_url: str, href: str) -> str | None:
    try:
        absolute = urljoin(base_url, href)
        parsed = urlsplit(absolute)
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return None
    scheme = parsed.scheme.lower()
    host = parsed.hostname.casefold().rstrip(".")
    try:
        port = parsed.port
    except ValueError:
        return None
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None
    netloc = host if port is None else f"{host}:{port}"
    return urlunsplit((scheme, netloc, parsed.path or "", parsed.query, ""))


def _social_contact(base_url: str, href: str) -> DiscoveredContact | None:
    absolute = _normalized_http_url(base_url, href)
    if absolute is None:
        return None
    parsed = urlsplit(absolute)
    host = (parsed.hostname or "").casefold()
    path = parsed.path.rstrip("/")
    if host == "linkedin.com" or host.endswith(".linkedin.com"):
        segments = [segment for segment in path.split("/") if segment]
        if len(segments) == 2 and segments[0].casefold() == "company":
            return DiscoveredContact(ContactKind.LINKEDIN, absolute)
        return None
    if host == "instagram.com" or host.endswith(".instagram.com"):
        segments = [segment for segment in path.split("/") if segment]
        reserved = {"p", "reel", "reels", "stories", "explore", "accounts", "direct"}
        if len(segments) == 1 and segments[0].casefold() not in reserved:
            return DiscoveredContact(ContactKind.INSTAGRAM, absolute)
    return None


def _whatsapp_contact(base_url: str, href: str) -> DiscoveredContact | None:
    absolute = _normalized_http_url(base_url, href)
    if absolute is None:
        return None
    parsed = urlsplit(absolute)
    if (parsed.hostname or "").casefold() != "wa.me":
        return None
    segments = [segment for segment in parsed.path.split("/") if segment]
    if len(segments) != 1 or not segments[0].isdigit():
        return None
    digits = segments[0]
    if not 7 <= len(digits) <= 15:
        return None
    return DiscoveredContact(ContactKind.WHATSAPP, f"+{digits}")


def _key(contact: DiscoveredContact) -> tuple[str, str]:
    if contact.kind is ContactKind.EMAIL:
        value = contact.value.casefold()
    elif contact.kind in {ContactKind.PHONE, ContactKind.WHATSAPP}:
        value = re.sub(r"\D", "", contact.value)
    else:
        value = contact.value.rstrip("/").casefold()
    return contact.kind.value, value


def discover_contacts_from_html(url: str, html: str) -> tuple[DiscoveredContact, ...]:
    _require_page_url(url)
    if not isinstance(html, str):
        raise TypeError("html must be text")
    parser = _ContactParser()
    parser.feed(html)
    text = "\n".join(parser.text_parts)
    found: list[DiscoveredContact] = []

    for href in parser.hrefs:
        stripped = href.strip()
        lower = stripped.casefold()
        if lower.startswith("mailto:"):
            if email := _email_from_mailto(stripped):
                found.append(DiscoveredContact(ContactKind.EMAIL, email))
            continue
        if lower.startswith("tel:"):
            tel_value = stripped.split(":", 1)[1].split("?", 1)[0].split(";", 1)[0]
            if phone := _phone(tel_value):
                found.append(DiscoveredContact(ContactKind.PHONE, phone))
            continue
        if whatsapp := _whatsapp_contact(url, stripped):
            found.append(whatsapp)
            continue
        if social := _social_contact(url, stripped):
            found.append(social)

    for match in _EMAIL_RE.finditer(text):
        email = match.group(1).strip()
        if _valid_email(email):
            found.append(DiscoveredContact(ContactKind.EMAIL, email))
    for match in _PHONE_LABEL_RE.finditer(text):
        if phone := _phone(match.group(1)):
            found.append(DiscoveredContact(ContactKind.PHONE, phone))
    if parser.form_count:
        page_url = _normalized_http_url(url, url)
        assert page_url is not None
        found.append(DiscoveredContact(ContactKind.CONTACT_FORM, page_url))

    deduped: dict[tuple[str, str], DiscoveredContact] = {}
    for item in found:
        deduped.setdefault(_key(item), item)
    return tuple(sorted(deduped.values(), key=lambda item: (item.kind.value, _key(item)[1])))


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class CompanyPageContactSource:
    def __init__(self, transport: PageTransport = http_get) -> None:
        self._transport = transport

    def ingest(self, company_id: str, url: str, repository: SQLiteRepository) -> ContactDiscoveryResult:
        company = repository.load(Company, company_id)
        if company is None:
            raise ValueError(f"company must already be persisted: {company_id}")
        _require_page_url(url)
        observation = self._transport(url)
        if observation.url != url:
            raise ContactAcquisitionError("transport returned an observation for a different URL")

        source_id = f"source:company-contact-page:{_digest(url)[:24]}"
        source = Source(source_id, "company-web-page", url, "Company contact page")
        repository.save(source)

        observation_id = _digest(f"{url}\0{observation.status_code}\0{observation.raw_html}")
        evidence_id = f"evidence:company-contact-page:{observation_id}"
        existing = repository.load(Evidence, evidence_id)
        if existing is not None:
            if existing.locator != url or existing.raw_payload != observation.raw_html:
                raise ContactAcquisitionError("content-addressed evidence ID collision")
            evidence = existing
            evidence_was_new = False
        else:
            evidence = Evidence(
                evidence_id,
                source_id,
                url,
                observation.captured_at,
                observation.raw_html,
                f"sha256:{_digest(observation.raw_html)}",
                {"http_status": observation.status_code, "headers": dict(observation.headers), "transport": "http"},
            )
            repository.save(evidence)
            evidence_was_new = True

        if observation.status_code != 200:
            raise ContactPageResponseError(observation.status_code, evidence.evidence_id)

        contacts: list[ContactPoint] = []
        for discovered in discover_contacts_from_html(url, observation.raw_html):
            contact_id = "contact:discovered:" + _digest(
                f"{company_id}\0{discovered.kind.value}\0{_key(discovered)[1]}\0{evidence.evidence_id}"
            )
            contact = ContactPoint(
                contact_id,
                company_id,
                discovered.kind,
                discovered.value,
                (evidence.evidence_id,),
                ContactStatus.DISCOVERED,
                evidence.captured_at,
            )
            repository.save(contact)
            contacts.append(contact)
        return ContactDiscoveryResult(company, source, evidence, tuple(contacts), evidence_was_new)
