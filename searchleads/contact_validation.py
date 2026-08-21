"""Conservative contact validation for CONTACT_VALIDATION_V1.

Validation in this work unit means *official-publication corroboration*: the
same professional contact is observed on at least two distinct official page
observations for the already-associated company. This validates the published
company/contact association, not mailbox deliverability or phone reachability.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import re
from urllib.parse import urlsplit

from .contact_discovery import discover_contacts_from_html
from .domain import ContactKind, ContactPoint, ContactStatus, Provenance, SourceType
from .persistence import SQLiteLeadStore

AGENT = "searchleads.contact_validation.v1"


class ContactValidationMethod(str, Enum):
    OFFICIAL_CROSS_PAGE_CORROBORATION = "OFFICIAL_CROSS_PAGE_CORROBORATION"


class ContactValidationDisposition(str, Enum):
    VALIDATED = "VALIDATED"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ContactValidationResult:
    original_contact: ContactPoint
    disposition: ContactValidationDisposition
    method: ContactValidationMethod
    validated_contact: ContactPoint | None
    confirming_evidence_ids: tuple[str, ...]
    confirming_locators: tuple[str, ...]
    deliverability_verified: bool
    reason: str


def _equivalence_key(kind: ContactKind, value: str) -> str:
    if kind is ContactKind.EMAIL:
        return value.strip().casefold()
    if kind in {ContactKind.PHONE, ContactKind.WHATSAPP}:
        return re.sub(r"\D", "", value)
    return value.rstrip("/").casefold()


def _structurally_valid(contact: ContactPoint) -> bool:
    value = contact.value.strip()
    if contact.kind is ContactKind.EMAIL:
        if value.count("@") != 1:
            return False
        local, domain = value.split("@", 1)
        return bool(local and "." in domain and not domain.startswith(".") and not domain.endswith("."))
    if contact.kind in {ContactKind.PHONE, ContactKind.WHATSAPP}:
        digits = re.sub(r"\D", "", value)
        return 8 <= len(digits) <= 15
    if contact.kind in {ContactKind.CONTACT_FORM, ContactKind.LINKEDIN, ContactKind.INSTAGRAM, ContactKind.PROFESSIONAL_PROFILE}:
        parsed = urlsplit(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    return bool(value)


def _evidence_body(evidence) -> str | None:
    payload = evidence.payload
    if isinstance(payload, dict) and isinstance(payload.get("body"), str):
        return payload["body"]
    if isinstance(payload, str):
        return payload
    return None


def validate_contact_from_official_evidence(
    store: SQLiteLeadStore,
    contact_id: str,
    corroborating_evidence_ids: tuple[str, ...] = (),
    *,
    persist: bool = True,
) -> ContactValidationResult:
    """Validate official publication using distinct page observations.

    At least two distinct official evidence observations must contain an
    equivalent contact. Distinct locators are preferred; a later snapshot of the
    same locator also counts when its retrieval timestamp is strictly newer.
    """
    contact = store.get_contact_point(contact_id)
    if contact is None:
        raise ValueError(f"missing contact: {contact_id}")
    method = ContactValidationMethod.OFFICIAL_CROSS_PAGE_CORROBORATION

    if not _structurally_valid(contact):
        return ContactValidationResult(
            contact, ContactValidationDisposition.INVALID, method, None, (), (), False,
            "contact value is structurally invalid",
        )

    requested_ids = tuple(dict.fromkeys(contact.provenance.evidence_ids + tuple(corroborating_evidence_ids)))
    target_key = _equivalence_key(contact.kind, contact.value)
    confirmations: list[tuple[str, str, object]] = []

    for evidence_id in requested_ids:
        evidence = store.get_evidence(evidence_id)
        if evidence is None:
            raise ValueError(f"missing validation evidence: {evidence_id}")
        source = store.get_source(evidence.source_id)
        if source is None:
            raise ValueError(f"missing validation source: {evidence.source_id}")
        if source.source_type is not SourceType.OFFICIAL_SOURCE:
            continue
        body = _evidence_body(evidence)
        locator = evidence.locator or source.locator
        if body is None or not locator:
            continue
        observed = discover_contacts_from_html(locator, body)
        if any(item.kind is contact.kind and _equivalence_key(item.kind, item.value) == target_key for item in observed):
            confirmations.append((evidence.evidence_id, locator, evidence.retrieved_at))

    locators: dict[str, list[tuple[str, object]]] = {}
    for evidence_id, locator, retrieved_at in confirmations:
        locators.setdefault(locator, []).append((evidence_id, retrieved_at))
    observation_count = len(locators)
    for snapshots in locators.values():
        times = sorted({item[1] for item in snapshots})
        if len(times) >= 2:
            observation_count += 1

    evidence_ids = tuple(sorted({item[0] for item in confirmations}))
    locator_values = tuple(sorted(locators))
    if observation_count < 2:
        return ContactValidationResult(
            contact, ContactValidationDisposition.UNKNOWN, method, None,
            evidence_ids, locator_values, False,
            "fewer than two distinct official page observations confirm the contact",
        )

    evidences = [store.get_evidence(eid) for eid in evidence_ids]
    generated_at = max(e.retrieved_at for e in evidences if e is not None)
    provenance = Provenance(
        evidence_ids=evidence_ids,
        activity="validate_contact_official_corroboration_v1",
        generated_at=generated_at,
        agent=AGENT,
    )
    material = f"{contact.owner.entity_type.value}|{contact.owner.entity_id}|{contact.kind.value}|{target_key}|{'|'.join(evidence_ids)}"
    validated = ContactPoint(
        contact_id="contact:validated:" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:28],
        owner=contact.owner,
        kind=contact.kind,
        value=contact.value,
        provenance=provenance,
        status=ContactStatus.VALIDATED,
    )
    if persist:
        store.save_contact_point(validated)
    return ContactValidationResult(
        contact, ContactValidationDisposition.VALIDATED, method, validated,
        evidence_ids, locator_values, False,
        "contact is corroborated by at least two official page observations; deliverability remains unverified",
    )
