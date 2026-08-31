"""Auditable selective human-review routing for SELECTIVE_REVIEW_V1.

The module converts already-computed ambiguity/conflict states into review work.
It never changes the source decision and deliberately exposes no opaque score.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
from typing import Iterable

from searchleads.domain import (
    Conflict, ConflictStatus, ContactPoint, ContactStatus, Lead, QualificationDecision, QualificationStatus,
)
from searchleads.entity_resolution import CompanyRecord, ResolutionDisposition, TriageDecision


class ReviewKind(StrEnum):
    COMPANY_MATCH = "COMPANY_MATCH"
    PERSON_MATCH = "PERSON_MATCH"
    DATA_CONFLICT = "DATA_CONFLICT"
    CONTACT = "CONTACT"
    QUALIFICATION = "QUALIFICATION"


class ReviewPriority(StrEnum):
    HIGH = "HIGH"
    NORMAL = "NORMAL"


@dataclass(frozen=True, slots=True)
class ReviewItem:
    review_id: str
    kind: ReviewKind
    priority: ReviewPriority
    record_ids: tuple[str, ...]
    reason: str
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.review_id.strip():
            raise ValueError("review_id must not be blank")
        if not self.record_ids or any(not item.strip() for item in self.record_ids):
            raise ValueError("review item requires non-blank record_ids")
        if not self.reason.strip():
            raise ValueError("review reason must be explicit")
        if any(not item.strip() for item in self.evidence_ids):
            raise ValueError("evidence_ids must not contain blanks")
        if tuple(sorted(set(self.evidence_ids))) != self.evidence_ids:
            raise ValueError("evidence_ids must be sorted and unique")


@dataclass(frozen=True, slots=True)
class ReviewQueue:
    items: tuple[ReviewItem, ...]

    @property
    def high_priority(self) -> int:
        return sum(item.priority is ReviewPriority.HIGH for item in self.items)

    @property
    def normal_priority(self) -> int:
        return len(self.items) - self.high_priority


def _clean_reason(value: str) -> str:
    reason = " ".join(value.split())
    if not reason:
        raise ValueError("review reason must be explicit")
    return reason


def _make_item(
    kind: ReviewKind,
    priority: ReviewPriority,
    record_ids: tuple[str, ...],
    reason: str,
    evidence_ids: tuple[str, ...] = (),
) -> ReviewItem:
    records = tuple(item.strip() for item in record_ids)
    if not records or any(not item for item in records):
        raise ValueError("review item requires non-blank record_ids")
    normalized_reason = _clean_reason(reason)
    evidence = tuple(sorted(set(item.strip() for item in evidence_ids if item.strip())))
    material = "\0".join((kind.value, *records, normalized_reason))
    review_id = "review:v1:" + hashlib.sha256(material.encode("utf-8")).hexdigest()
    return ReviewItem(review_id, kind, priority, records, normalized_reason, evidence)


def review_company_match(
    left: CompanyRecord,
    right: CompanyRecord,
    decision: TriageDecision,
) -> ReviewItem | None:
    if decision.disposition is not ResolutionDisposition.REVIEW:
        return None
    reasons = tuple(reason.strip() for reason in decision.reasons if reason.strip())
    if not reasons:
        raise ValueError("REVIEW company decision requires explicit reasons")
    records = tuple(sorted((left.record_id, right.record_id)))
    return _make_item(
        ReviewKind.COMPANY_MATCH,
        ReviewPriority.NORMAL,
        records,
        "company ER requires review: " + "; ".join(reasons),
    )


def review_person_match(
    left_person_id: str,
    right_person_id: str,
    company_id: str,
    reason: str,
    evidence_ids: tuple[str, ...],
) -> ReviewItem:
    people = tuple(sorted((left_person_id.strip(), right_person_id.strip())))
    if not company_id.strip() or not all(people) or people[0] == people[1]:
        raise ValueError("person review requires two distinct people and one company")
    evidence = tuple(item.strip() for item in evidence_ids)
    if not evidence or any(not item for item in evidence):
        raise ValueError("person ambiguity review requires explicit evidence")
    return _make_item(
        ReviewKind.PERSON_MATCH,
        ReviewPriority.NORMAL,
        (company_id.strip(), *people),
        "person identity unresolved: " + _clean_reason(reason),
        evidence,
    )


def review_conflict(
    conflict: Conflict,
    *,
    high_impact: bool = False,
    evidence_ids: tuple[str, ...] = (),
) -> ReviewItem | None:
    if conflict.status is not ConflictStatus.OPEN:
        return None
    priority = ReviewPriority.HIGH if high_impact else ReviewPriority.NORMAL
    return _make_item(
        ReviewKind.DATA_CONFLICT,
        priority,
        (conflict.subject_id, conflict.conflict_id, *tuple(sorted(conflict.candidate_fact_ids))),
        f"open field conflict: {conflict.field_name}",
        evidence_ids,
    )


def review_contact(contact: ContactPoint) -> ReviewItem | None:
    if contact.status not in {ContactStatus.DISCOVERED, ContactStatus.UNKNOWN}:
        return None
    evidence = tuple(sorted(set(contact.discovery_evidence_ids + contact.validation_evidence_ids)))
    return _make_item(
        ReviewKind.CONTACT,
        ReviewPriority.NORMAL,
        (contact.owner_id, contact.contact_id),
        f"uncertain contact state: {contact.status.value}",
        evidence,
    )


def review_qualification(lead: Lead, *, high_value: bool) -> ReviewItem | None:
    if lead.qualification_status is not QualificationStatus.UNKNOWN or not high_value:
        return None
    reasons = tuple(reason.strip() for reason in lead.qualification_reasons if reason.strip())
    suffix = "; ".join(reasons) if reasons else "qualification policy/evidence remains unresolved"
    return _make_item(
        ReviewKind.QUALIFICATION,
        ReviewPriority.HIGH,
        (lead.company_id, lead.lead_id),
        "high-value qualification ambiguity: " + suffix,
    )


def review_qualification_decision(
    lead: Lead,
    decision: QualificationDecision,
    *,
    high_value: bool,
) -> ReviewItem | None:
    item = review_qualification(lead, high_value=high_value)
    if item is None:
        return None
    reason = f"canonical qualification decision {decision.qualification_status.value}: " + item.reason
    return _make_item(
        ReviewKind.QUALIFICATION,
        ReviewPriority.HIGH,
        (lead.company_id, lead.lead_id, decision.decision_id),
        reason,
        decision.evidence_ids,
    )


def build_review_queue(items: Iterable[ReviewItem | None]) -> ReviewQueue:
    merged: dict[str, ReviewItem] = {}
    for item in items:
        if item is None:
            continue
        previous = merged.get(item.review_id)
        if previous is None:
            merged[item.review_id] = item
            continue
        if (previous.kind, previous.record_ids, previous.reason) != (item.kind, item.record_ids, item.reason):
            raise ValueError("review_id collision across different semantic review items")
        priority = (
            ReviewPriority.HIGH
            if ReviewPriority.HIGH in {previous.priority, item.priority}
            else ReviewPriority.NORMAL
        )
        evidence = tuple(sorted(set(previous.evidence_ids + item.evidence_ids)))
        merged[item.review_id] = ReviewItem(
            item.review_id, item.kind, priority, item.record_ids, item.reason, evidence
        )
    rank = {ReviewPriority.HIGH: 0, ReviewPriority.NORMAL: 1}
    ordered = tuple(sorted(merged.values(), key=lambda item: (rank[item.priority], item.kind.value, item.review_id)))
    return ReviewQueue(ordered)
