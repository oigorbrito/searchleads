"""Evidence-backed professional channels published alongside known people.

This bounded extractor completes the person/role discovery contract without
claiming deliverability or personal ownership beyond what the source publishes.
"""
from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import hashlib
import re
from typing import Iterable, Mapping
from urllib.parse import urljoin, urlsplit

from .domain import ContactKind, ContactPoint, ContactStatus, EntityRef, EntityType, Evidence, Person, Provenance

AGENT = "searchleads.person_professional_contacts.v1"
_EMAIL_RE = re.compile(r"([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})", re.I)
_PHONE_RE = re.compile(r"(?:telefone|fone|tel\.?)\s*:?\s*((?:\+?\d|\(\d)[\d\s()./-]{6,}\d)", re.I)


@dataclass(frozen=True, slots=True)
class _Chunk:
    text: str
    href: str | None = None


class _OrderedHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.chunks: list[_Chunk] = []
        self._href: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() == "a":
            data = {key.lower(): value for key, value in attrs if key}
            self._href = data.get("href")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a":
            self._href = None

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text:
            self.chunks.append(_Chunk(text, self._href))


@dataclass(frozen=True, slots=True)
class PublishedPersonChannel:
    person_name: str
    kind: ContactKind
    value: str
    source_label: str


@dataclass(frozen=True, slots=True)
class PersonChannelExtraction:
    channels: tuple[PublishedPersonChannel, ...]
    shared_profile_locators: tuple[str, ...]


def _norm_name(value: str) -> str:
    return " ".join(value.split()).casefold()


def _clean_phone(value: str) -> str | None:
    cleaned = " ".join(value.split()).strip(" ,;.")
    digits = re.sub(r"\D", "", cleaned)
    if not 8 <= len(digits) <= 15:
        return None
    return cleaned


def _absolute_http_url(base_url: str, href: str) -> str | None:
    absolute = urljoin(base_url, href)
    parsed = urlsplit(absolute)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return absolute


def discover_person_professional_channels(
    page_url: str,
    html: str,
    person_names: Iterable[str],
) -> PersonChannelExtraction:
    """Extract only channels located inside each known person's local page block.

    A profile link is emitted only when its URL is unique to one known person in
    the supplied page snapshot. Shared curriculum/listing URLs are retained as
    contextual evidence but are not promoted to PROFESSIONAL_PROFILE, because a
    shared URL is not a strong person identifier.
    """
    parsed = _OrderedHTML()
    parsed.feed(html)
    names = tuple(dict.fromkeys(" ".join(name.split()) for name in person_names if name.strip()))
    norm_to_name = {_norm_name(name): name for name in names}
    positions: list[tuple[int, str]] = []
    for idx, chunk in enumerate(parsed.chunks):
        name = norm_to_name.get(_norm_name(chunk.text))
        if name is not None:
            positions.append((idx, name))

    per_person: dict[str, list[PublishedPersonChannel]] = {name: [] for name in names}
    profile_candidates: dict[str, list[str]] = {name: [] for name in names}
    for pos_idx, (start, name) in enumerate(positions):
        next_start = positions[pos_idx + 1][0] if pos_idx + 1 < len(positions) else len(parsed.chunks)
        end = min(next_start, start + 16)
        for chunk in parsed.chunks[start + 1:end]:
            for match in _EMAIL_RE.finditer(chunk.text):
                per_person[name].append(
                    PublishedPersonChannel(name, ContactKind.EMAIL, match.group(1), "published alongside person/role")
                )
            phone_match = _PHONE_RE.search(chunk.text)
            if phone_match:
                phone = _clean_phone(phone_match.group(1))
                if phone:
                    per_person[name].append(
                        PublishedPersonChannel(name, ContactKind.PHONE, phone, "published alongside person/role")
                    )
            if chunk.href and "curr" in chunk.text.casefold():
                absolute = _absolute_http_url(page_url, chunk.href)
                if absolute:
                    profile_candidates[name].append(absolute)

    profile_users: dict[str, set[str]] = {}
    for name, urls in profile_candidates.items():
        for url in urls:
            profile_users.setdefault(url, set()).add(name)
    shared = tuple(sorted(url for url, users in profile_users.items() if len(users) > 1))
    for name, urls in profile_candidates.items():
        for url in urls:
            if len(profile_users[url]) == 1:
                per_person[name].append(
                    PublishedPersonChannel(name, ContactKind.PROFESSIONAL_PROFILE, url, "unique curriculum/profile link")
                )

    deduped: dict[tuple[str, str, str], PublishedPersonChannel] = {}
    for name in names:
        for item in per_person[name]:
            value_key = item.value.casefold() if item.kind is not ContactKind.PHONE else re.sub(r"\D", "", item.value)
            deduped.setdefault((item.person_name.casefold(), item.kind.value, value_key), item)
    channels = tuple(sorted(deduped.values(), key=lambda x: (x.person_name.casefold(), x.kind.value, x.value.casefold())))
    return PersonChannelExtraction(channels, shared)


def build_person_contact_points(
    people_by_name: Mapping[str, Person],
    evidence: Evidence,
    extraction: PersonChannelExtraction,
) -> tuple[ContactPoint, ...]:
    provenance = Provenance(
        (evidence.evidence_id,),
        "discover_person_professional_channels_from_official_page_v1",
        generated_at=evidence.retrieved_at,
        agent=AGENT,
    )
    normalized_people = {_norm_name(name): person for name, person in people_by_name.items()}
    contacts: list[ContactPoint] = []
    for item in extraction.channels:
        person = normalized_people.get(_norm_name(item.person_name))
        if person is None:
            continue
        material = f"{person.person_id}|{item.kind.value}|{item.value}|{evidence.evidence_id}"
        contacts.append(
            ContactPoint(
                "contact:person-published:" + hashlib.sha256(material.encode()).hexdigest()[:28],
                EntityRef(EntityType.PERSON, person.person_id),
                item.kind,
                item.value,
                provenance,
                ContactStatus.DISCOVERED,
            )
        )
    return tuple(contacts)
