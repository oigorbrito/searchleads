"""Selective review routing for SELECTIVE_REVIEW_V1.

The module does not review every record. It converts already-computed ambiguity
or conflict signals into a small auditable queue and never changes the source
decision itself.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import hashlib
from typing import Iterable

from .domain import Conflict, ConflictStatus, ContactPoint, ContactStatus, LeadStatus
from .entity_resolution import CompanyRecord, ResolutionDisposition, TriageDecision
from .person_entity_resolution import (
    PersonResolutionDecision,
    PersonResolutionDisposition,
)
from .qualification import QualificationResult


class ReviewKind(str, Enum):
    COMPANY_MATCH = "COMPANY_MATCH"
    PERSON_MATCH = "PERSON_MATCH"
    DATA_CONFLICT = "DATA_CONFLICT"
    CONTACT = "CONTACT"
    QUALIFICATION = "QUALIFICATION"


class ReviewPriority(str, Enum):
    HIGH = "HIGH"
    NORMAL = "NORMAL"


@dataclass(frozen=True, slots=True)
class ReviewItem:
    review_id: str
    kind: ReviewKind
    priority: ReviewPriority
    entity_ids: tuple[str, ...]
    reason: str
    evidence_ids: tuple[str, ...] = ()


def _item(
    kind: ReviewKind,
    priority: ReviewPriority,
    entity_ids: tuple[str, ...],
    reason: str,
    evidence_ids: tuple[str, ...] = (),
) -> ReviewItem:
    if not reason.strip():
        raise ValueError("review reason must be explicit")
    material = "|".join(
        (kind.value, priority.value, *entity_ids, reason, *sorted(evidence_ids))
    )
    return ReviewItem(
        "review:" + hashlib.sha256(material.encode()).hexdigest()[:24],
        kind,
        priority,
        entity_ids,
        reason,
        tuple(sorted(set(evidence_ids))),
    )


def review_company_match(
    left: CompanyRecord,
    right: CompanyRecord,
    decision: TriageDecision,
) -> ReviewItem | None:
    if decision.disposition is not ResolutionDisposition.REVIEW:
        return None
    return _item(
        ReviewKind.COMPANY_MATCH,
        ReviewPriority.NORMAL,
        (left.record_id, right.record_id),
        "ambiguous company match: " + ", ".join(decision.reasons),
    )


def review_person_match(
    left_person_id: str,
    right_person_id: str,
    company_id: str,
    reason: str,
    evidence_ids: tuple[str, ...] = (),
) -> ReviewItem:
    """Low-level constructor retained for explicit/manual ambiguity evidence."""
    return _item(
        ReviewKind.PERSON_MATCH,
        ReviewPriority.NORMAL,
        (left_person_id, right_person_id, company_id),
        "ambiguous person match: " + reason,
        evidence_ids,
    )


def review_person_resolution(
    left_person_id: str,
    right_person_id: str,
    company_id: str,
    decision: PersonResolutionDecision,
    evidence_ids: tuple[str, ...] = (),
) -> ReviewItem | None:
    """Route only typed Person ER review decisions into the selective queue."""
    if decision.disposition is not PersonResolutionDisposition.REVIEW:
        return None
    return review_person_match(
        left_person_id,
        right_person_id,
        company_id,
        ", ".join(decision.reasons),
        evidence_ids,
    )


def review_conflict(
    conflict: Conflict,
    *,
    authoritative: bool = False,
    evidence_ids: tuple[str, ...] = (),
) -> ReviewItem | None:
    if conflict.status is not ConflictStatus.OPEN:
        return None
    priority = ReviewPriority.HIGH if authoritative else ReviewPriority.NORMAL
    return _item(
        ReviewKind.DATA_CONFLICT,
        priority,
        (conflict.subject.entity_id, conflict.conflict_id),
        f"open conflict for {conflict.predicate}",
        evidence_ids,
    )


def review_contact(contact: ContactPoint) -> ReviewItem | None:
    if contact.status not in {ContactStatus.DISCOVERED, ContactStatus.UNKNOWN}:
        return None
    return _item(
        ReviewKind.CONTACT,
        ReviewPriority.NORMAL,
        (contact.owner.entity_id, contact.contact_id),
        f"uncertain contact state: {contact.status.value}",
        contact.provenance.evidence_ids,
    )


def review_qualification(
    result: QualificationResult,
    *,
    high_value: bool,
) -> ReviewItem | None:
    if result.status is not LeadStatus.UNKNOWN or not high_value:
        return None
    return _item(
        ReviewKind.QUALIFICATION,
        ReviewPriority.HIGH,
        (result.company_id,),
        "high-value qualification ambiguity: " + "; ".join(result.reasons),
        (),
    )


def build_review_queue(items: Iterable[ReviewItem | None]) -> tuple[ReviewItem, ...]:
    unique = {item.review_id: item for item in items if item is not None}
    rank = {ReviewPriority.HIGH: 0, ReviewPriority.NORMAL: 1}
    return tuple(
        sorted(
            unique.values(),
            key=lambda item: (rank[item.priority], item.kind.value, item.review_id),
        )
    )
