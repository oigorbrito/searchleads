"""Evidence-preserving professional contact discovery for CONTACT_DISCOVERY_V1.

The extractor is deliberately conservative. It discovers contact observations
from one official/public HTML page, stores the complete page as Evidence, and
creates ContactPoint records in DISCOVERED state. It does not validate inboxes,
phone ownership, social-account ownership, or contact-form deliverability.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
import re
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

from .domain import Company, ContactKind, ContactPoint, ContactStatus, EntityRef, EntityType, Evidence, Provenance, Source, SourceType
from .persistence import SQLiteLeadStore

AGENT = "searchleads.contact_discovery.v1"
_EMAIL_RE = re.compile(r"(?<![\w.+-])([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})(?![\w.-])", re.I)
_PHONE_AFTER_LABEL_RE = re.compile(r"(?:telefone|fone|tel\.?|whatsapp)\s*:?[\s\u00a0]*(\+?\d[\d\s()./-]{6,}\d)", re.I)

class ContactDiscoveryError(RuntimeError):
    pass

class ContactAcquisitionError(ContactDiscoveryError):
    pass

@dataclass(frozen=True, slots=True)
class DiscoveredContact:
    kind: ContactKind
    value: str

@dataclass(frozen=True, slots=True)
class ContactDiscoveryResult:
    company: Company
    source: Source
    evidence: Evidence
    contacts: tuple[ContactPoint, ...]

HtmlTransport = Callable[[str], str]

class _ContactHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []
        self.forms: list[str | None] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        data = {key.lower(): value for key, value in attrs if key}
        if tag.lower() == "a" and data.get("href"):
            self.hrefs.append(data["href"])
        elif tag.lower() == "form":
            self.forms.append(data.get("action"))

    def handle_data(self, data: str) -> None:
        if data and data.strip():
            self.text_parts.append(data)

def _http_get(url: str) -> str:
    request = Request(url, headers={"Accept": "text/html,application/xhtml+xml", "User-Agent": "searchleads/0.7 (+https://github.com/tihotm/searchleads)"})
    try:
        with urlopen(request, timeout=20) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise ContactAcquisitionError(f"failed to fetch {url}: {exc}") from exc

def _content_hash(html: str) -> str:
    return hashlib.sha256(html.encode("utf-8")).hexdigest()

def _contact_key(contact: DiscoveredContact) -> tuple[str, str]:
    if contact.kind is ContactKind.EMAIL:
        return contact.kind.value, contact.value.casefold()
    if contact.kind in {ContactKind.PHONE, ContactKind.WHATSAPP}:
        return contact.kind.value, re.sub(r"\D", "", contact.value)
    return contact.kind.value, contact.value.rstrip("/").casefold()

def _valid_email(value: str) -> bool:
    local, _, domain = value.partition("@")
    return bool(local and domain and "." in domain and not domain.startswith(".") and not domain.endswith("."))

def _clean_phone(value: str) -> str | None:
    cleaned = " ".join(value.replace("\u00a0", " ").split()).strip(" ,;.")
    digits = re.sub(r"\D", "", cleaned)
    if not 8 <= len(digits) <= 15:
        return None
    return cleaned

def discover_contacts_from_html(url: str, html: str) -> tuple[DiscoveredContact, ...]:
    parsed_url = urlsplit(url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError("url must be an absolute http/https URL")
    parser = _ContactHTMLParser()
    parser.feed(html)
    text = "\n".join(parser.text_parts)
    found: list[DiscoveredContact] = []
    for href in parser.hrefs:
        lower = href.lower().strip()
        if lower.startswith("mailto:"):
            value = href.split(":", 1)[1].split("?", 1)[0].strip()
            if _valid_email(value):
                found.append(DiscoveredContact(ContactKind.EMAIL, value))
        elif lower.startswith("tel:"):
            value = href.split(":", 1)[1].split("?", 1)[0].strip()
            phone = _clean_phone(value)
            if phone:
                found.append(DiscoveredContact(ContactKind.PHONE, phone))
        else:
            absolute = urljoin(url, href)
            host = (urlsplit(absolute).hostname or "").casefold()
            if host == "linkedin.com" or host.endswith(".linkedin.com"):
                found.append(DiscoveredContact(ContactKind.LINKEDIN, absolute))
            elif host == "instagram.com" or host.endswith(".instagram.com"):
                found.append(DiscoveredContact(ContactKind.INSTAGRAM, absolute))
    for match in _EMAIL_RE.finditer(text):
        value = match.group(1).strip()
        if _valid_email(value):
            found.append(DiscoveredContact(ContactKind.EMAIL, value))
    for match in _PHONE_AFTER_LABEL_RE.finditer(text):
        phone = _clean_phone(match.group(1))
        if phone:
            found.append(DiscoveredContact(ContactKind.PHONE, phone))
    for action in parser.forms:
        target = url if not action else urljoin(url, action)
        found.append(DiscoveredContact(ContactKind.CONTACT_FORM, target))
    deduped: dict[tuple[str, str], DiscoveredContact] = {}
    for contact in found:
        deduped.setdefault(_contact_key(contact), contact)
    return tuple(sorted(deduped.values(), key=lambda item: (item.kind.value, item.value.casefold())))

class OfficialPageContactSource:
    def __init__(self, transport: HtmlTransport | None = None) -> None:
        self._transport = transport or _http_get

    def fetch(self, url: str) -> str:
        return self._transport(url)

    def ingest(self, store: SQLiteLeadStore, company_id: str, url: str, *, retrieved_at: datetime | None = None, html: str | None = None, official: bool = True) -> ContactDiscoveryResult:
        company = store.get_company(company_id)
        if company is None:
            raise ValueError(f"company must already be persisted: {company_id}")
        page = html if html is not None else self.fetch(url)
        fetched_at = retrieved_at or datetime.now(timezone.utc)
        if fetched_at.tzinfo is None or fetched_at.utcoffset() is None:
            raise ValueError("retrieved_at must be timezone-aware")
        digest = _content_hash(page)
        source = Source(source_id=f"source:contact-page:{hashlib.sha256(url.encode('utf-8')).hexdigest()[:20]}", source_type=SourceType.OFFICIAL_SOURCE if official else SourceType.WEBSITE, locator=url, label="Official company contact page" if official else "Company contact page")
        evidence = Evidence(evidence_id=f"evidence:contact-page:{digest[:24]}", source_id=source.source_id, retrieved_at=fetched_at, payload={"content_type": "text/html", "body": page}, locator=url, content_hash=f"sha256:{digest}")
        provenance = Provenance(evidence_ids=(evidence.evidence_id,), activity="discover_professional_contacts_from_html_v1", generated_at=fetched_at, agent=AGENT)
        owner = EntityRef(EntityType.COMPANY, company.company_id)
        contacts = tuple(ContactPoint(contact_id="contact:discovered:" + hashlib.sha256(f"{company.company_id}|{item.kind.value}|{item.value}|{evidence.evidence_id}".encode("utf-8")).hexdigest()[:28], owner=owner, kind=item.kind, value=item.value, provenance=provenance, status=ContactStatus.DISCOVERED) for item in discover_contacts_from_html(url, page))
        store.save_source(source)
        store.save_evidence(evidence)
        for contact in contacts:
            store.save_contact_point(contact)
        return ContactDiscoveryResult(company, source, evidence, contacts)
