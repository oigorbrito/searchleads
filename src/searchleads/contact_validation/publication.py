"""Evidence-linked publication corroboration for CONTACT_VALIDATION_V1.

Validation here means that the same discovered contact association is supported
by at least two independent persisted page observations. It does *not* mean
mailbox deliverability, telephone reachability, account control, or freshness.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import re
from itertools import combinations
from typing import Protocol, TypeVar
from urllib.parse import urlsplit, urlunsplit

from searchleads.domain import ContactKind, ContactPoint, ContactStatus, Evidence, Source


class ContactValidationMethod(StrEnum):
    PUBLICATION_CORROBORATION_V1 = "PUBLICATION_CORROBORATION_V1"


class ContactValidationDisposition(StrEnum):
    VALIDATED = "VALIDATED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NOT_VALIDATABLE = "NOT_VALIDATABLE"


@dataclass(frozen=True, slots=True)
class ContactValidationResult:
    original_contact: ContactPoint
    disposition: ContactValidationDisposition
    method: ContactValidationMethod
    validated_contact: ContactPoint | None
    qualifying_contact_ids: tuple[str, ...]
    validation_evidence_ids: tuple[str, ...]
    validation_locators: tuple[str, ...]
    deliverability_verified: bool
    reachability_verified: bool
    reason: str

    def __post_init__(self) -> None:
        if self.deliverability_verified or self.reachability_verified:
            raise ValueError("publication corroboration cannot claim deliverability or reachability")
        if self.disposition is ContactValidationDisposition.VALIDATED:
            if self.validated_contact is None or not self.validation_evidence_ids:
                raise ValueError("VALIDATED result requires validated contact and validation evidence")
        elif self.validated_contact is not None:
            raise ValueError("non-validated result cannot expose a validated contact")


T = TypeVar("T")


class Repository(Protocol):
    def load(self, record_type: type[T], record_id: str) -> T | None: ...
    def save(self, record: object) -> bool: ...


_PAGE_SOURCE_TYPES = frozenset({"company-web-page", "company-people-page"})
_URL_KINDS = frozenset({
    ContactKind.CONTACT_FORM,
    ContactKind.LINKEDIN,
    ContactKind.INSTAGRAM,
    ContactKind.PROFESSIONAL_PROFILE,
})


def _valid_email(value: str) -> bool:
    value = value.strip()
    if len(value) > 254 or value.count("@") != 1:
        return False
    local, domain = value.rsplit("@", 1)
    if not local or len(local) > 64 or not domain or len(domain) > 253 or "." not in domain:
        return False
    if re.fullmatch(r"[A-Z0-9._%+-]+", local, re.I) is None:
        return False
    labels = domain.split(".")
    return all(
        1 <= len(label) <= 63
        and re.fullmatch(r"[A-Z0-9-]+", label, re.I) is not None
        and not label.startswith("-")
        and not label.endswith("-")
        for label in labels
    )


def _normalized_url(value: str) -> str | None:
    try:
        parsed = urlsplit(value.strip())
        if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
            return None
        port = parsed.port
    except ValueError:
        return None
    scheme = parsed.scheme.casefold()
    host = parsed.hostname.casefold().rstrip(".")
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None
    display_host = f"[{host}]" if ":" in host else host
    netloc = display_host if port is None else f"{display_host}:{port}"
    path = parsed.path
    if path not in {"", "/"}:
        path = path.rstrip("/")
    return urlunsplit((scheme, netloc, path, parsed.query, ""))


def _equivalence_key(kind: ContactKind, value: str) -> str | None:
    raw = value.strip()
    if kind is ContactKind.EMAIL:
        return raw.casefold() if _valid_email(raw) else None
    if kind in {ContactKind.PHONE, ContactKind.WHATSAPP}:
        digits = re.sub(r"\D", "", raw)
        return digits if 7 <= len(digits) <= 15 else None
    if kind in _URL_KINDS:
        return _normalized_url(raw)
    return None


def _independent_pair(confirmations: tuple[Evidence, ...]) -> bool:
    for left, right in combinations(confirmations, 2):
        if left.locator != right.locator:
            return True
        if left.captured_at != right.captured_at:
            return True
    return False


def _qualifying_evidence(repository: Repository, contact: ContactPoint) -> tuple[Evidence, ...]:
    evidence: list[Evidence] = []
    seen: set[str] = set()
    for evidence_id in contact.discovery_evidence_ids:
        if evidence_id in seen:
            continue
        seen.add(evidence_id)
        item = repository.load(Evidence, evidence_id)
        if item is None:
            raise ValueError(f"missing contact discovery evidence: {evidence_id}")
        source = repository.load(Source, item.source_id)
        if source is None:
            raise ValueError(f"missing contact discovery source: {item.source_id}")
        if source.source_type not in _PAGE_SOURCE_TYPES:
            continue
        if item.metadata.get("http_status") != 200 or not isinstance(item.raw_payload, str):
            continue
        evidence.append(item)
    return tuple(evidence)


def validate_contact_publication(
    repository: Repository,
    contact_id: str,
    corroborating_contact_ids: tuple[str, ...] = (),
    *,
    persist: bool = True,
) -> ContactValidationResult:
    """Validate a contact association from independent persisted observations.

    The original contact must be ``DISCOVERED``. Corroborating contacts count
    only when they are also ``DISCOVERED``, have the same owner and kind, and
    have an equivalent value. Page Evidence must be successful HTTP text from
    a SearchLeads company-contact or company-people page source.
    """
    original = repository.load(ContactPoint, contact_id)
    if original is None:
        raise ValueError(f"missing contact: {contact_id}")
    if original.status is not ContactStatus.DISCOVERED:
        raise ValueError("CONTACT_VALIDATION_V1 requires an original DISCOVERED contact")

    method = ContactValidationMethod.PUBLICATION_CORROBORATION_V1
    target_key = _equivalence_key(original.kind, original.value)
    if target_key is None:
        return ContactValidationResult(
            original, ContactValidationDisposition.NOT_VALIDATABLE, method, None,
            (), (), (), False, False,
            "contact kind/value is not structurally validatable by publication corroboration",
        )

    requested_ids = tuple(dict.fromkeys((contact_id,) + tuple(corroborating_contact_ids)))
    qualifying_contacts: list[ContactPoint] = []
    evidence_by_id: dict[str, Evidence] = {}
    for candidate_id in requested_ids:
        candidate = repository.load(ContactPoint, candidate_id)
        if candidate is None:
            raise ValueError(f"missing corroborating contact: {candidate_id}")
        if candidate.status is not ContactStatus.DISCOVERED:
            continue
        if candidate.owner_id != original.owner_id or candidate.kind is not original.kind:
            continue
        if _equivalence_key(candidate.kind, candidate.value) != target_key:
            continue
        candidate_evidence = _qualifying_evidence(repository, candidate)
        if not candidate_evidence:
            continue
        qualifying_contacts.append(candidate)
        for evidence in candidate_evidence:
            evidence_by_id.setdefault(evidence.evidence_id, evidence)

    confirmations = tuple(sorted(evidence_by_id.values(), key=lambda item: (item.captured_at, item.evidence_id)))
    evidence_ids = tuple(sorted(evidence_by_id))
    locators = tuple(sorted({item.locator for item in confirmations}))
    contact_ids = tuple(sorted({item.contact_id for item in qualifying_contacts}))

    if len(confirmations) < 2 or not _independent_pair(confirmations):
        return ContactValidationResult(
            original, ContactValidationDisposition.INSUFFICIENT_EVIDENCE, method, None,
            contact_ids, evidence_ids, locators, False, False,
            "fewer than two independent page observations corroborate the same owner/kind/value",
        )

    validated_at = max(item.captured_at for item in confirmations)
    material = "\0".join((
        method.value,
        original.owner_id,
        original.kind.value,
        target_key,
        *evidence_ids,
    ))
    validated = ContactPoint(
        "contact:validated:" + hashlib.sha256(material.encode("utf-8")).hexdigest(),
        original.owner_id,
        original.kind,
        original.value,
        original.discovery_evidence_ids,
        ContactStatus.VALIDATED,
        original.discovered_at,
        evidence_ids,
        validated_at,
    )
    if persist:
        repository.save(validated)
    return ContactValidationResult(
        original, ContactValidationDisposition.VALIDATED, method, validated,
        contact_ids, evidence_ids, locators, False, False,
        "publication association is corroborated; deliverability and reachability remain unverified",
    )


__all__ = [
    "ContactValidationDisposition",
    "ContactValidationMethod",
    "ContactValidationResult",
    "validate_contact_publication",
]
