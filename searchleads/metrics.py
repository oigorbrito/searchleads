"""Explicit metrics from handoff section 41.

Metrics are computed only when their denominator / ground truth is supplied.
Unavailable measurements remain explicit instead of being estimated.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Iterable, Mapping, Sequence

from .domain import CandidateFact, CanonicalFact, Conflict, ContactKind, ContactPoint, ContactStatus, LeadStatus


class MetricAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class MetricValue:
    availability: MetricAvailability
    value: float | None
    numerator: float | None = None
    denominator: float | None = None
    reason: str | None = None

    @classmethod
    def rate(cls, numerator: float, denominator: float, *, zero_reason: str) -> "MetricValue":
        if denominator <= 0:
            return cls(MetricAvailability.UNAVAILABLE, None, numerator, denominator, zero_reason)
        return cls(MetricAvailability.AVAILABLE, numerator / denominator, numerator, denominator, None)

    @classmethod
    def unavailable(cls, reason: str) -> "MetricValue":
        return cls(MetricAvailability.UNAVAILABLE, None, None, None, reason)


@dataclass(frozen=True, slots=True)
class DiscoveryMetrics:
    discovered_observations: int
    unique_companies: int
    duplicate_discovery_rate: MetricValue
    company_coverage: MetricValue
    discovery_precision: MetricValue


def compute_discovery_metrics(
    discovered_company_ids: Sequence[str],
    *,
    universe_company_ids: Iterable[str] | None = None,
    true_relevant_company_ids: Iterable[str] | None = None,
) -> DiscoveryMetrics:
    observed = tuple(discovered_company_ids)
    unique = set(observed)
    duplicate_count = len(observed) - len(unique)
    duplicate_rate = MetricValue.rate(
        duplicate_count, len(observed), zero_reason="no discovery observations"
    )
    if universe_company_ids is None:
        coverage = MetricValue.unavailable("company universe / denominator is not defined")
    else:
        universe = set(universe_company_ids)
        coverage = MetricValue.rate(
            len(unique & universe), len(universe), zero_reason="company universe is empty"
        )
    if true_relevant_company_ids is None:
        precision = MetricValue.unavailable("discovery ground truth is not supplied")
    else:
        relevant = set(true_relevant_company_ids)
        precision = MetricValue.rate(
            len(unique & relevant), len(unique), zero_reason="no discovered companies"
        )
    return DiscoveryMetrics(len(observed), len(unique), duplicate_rate, coverage, precision)


@dataclass(frozen=True, slots=True)
class EntityResolutionMetrics:
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int
    precision: MetricValue
    recall: MetricValue
    f1: MetricValue
    false_merge_rate: MetricValue
    false_split_rate: MetricValue


def compute_entity_resolution_metrics(tp: int, fp: int, tn: int, fn: int) -> EntityResolutionMetrics:
    if min(tp, fp, tn, fn) < 0:
        raise ValueError("confusion-matrix counts must be non-negative")
    precision = MetricValue.rate(tp, tp + fp, zero_reason="no predicted matches")
    recall = MetricValue.rate(tp, tp + fn, zero_reason="no labeled duplicate pairs")
    if precision.value is None or recall.value is None or precision.value + recall.value == 0:
        f1 = MetricValue.unavailable("precision/recall are unavailable or both zero")
    else:
        value = 2 * precision.value * recall.value / (precision.value + recall.value)
        f1 = MetricValue(MetricAvailability.AVAILABLE, value)
    false_merge = MetricValue.rate(fp, fp + tn, zero_reason="no labeled distinct pairs")
    false_split = MetricValue.rate(fn, tp + fn, zero_reason="no labeled duplicate pairs")
    return EntityResolutionMetrics(tp, fp, tn, fn, precision, recall, f1, false_merge, false_split)


@dataclass(frozen=True, slots=True)
class EnrichmentMetrics:
    field_coverage: MetricValue
    field_accuracy: MetricValue
    provenance_coverage: MetricValue
    conflict_rate: MetricValue


def compute_enrichment_metrics(
    company_ids: Sequence[str],
    required_predicates: Sequence[str],
    *,
    canonical_facts: Iterable[CanonicalFact] = (),
    candidate_facts: Iterable[CandidateFact] = (),
    conflicts: Iterable[Conflict] = (),
    field_accuracy_labels: Mapping[tuple[str, str], bool] | None = None,
) -> EnrichmentMetrics:
    companies = tuple(dict.fromkeys(company_ids))
    predicates = tuple(dict.fromkeys(required_predicates))
    canonical = tuple(canonical_facts)
    candidates = tuple(candidate_facts)
    conflict_items = tuple(conflicts)
    present = {(fact.subject.entity_id, fact.predicate) for fact in canonical}
    total_slots = len(companies) * len(predicates)
    covered = sum((company_id, predicate) in present for company_id in companies for predicate in predicates)
    field_coverage = MetricValue.rate(covered, total_slots, zero_reason="no company/predicate slots defined")
    if field_accuracy_labels is None:
        field_accuracy = MetricValue.unavailable("field-accuracy ground truth is not supplied")
    else:
        labels = [bool(value) for key, value in field_accuracy_labels.items() if key in present]
        field_accuracy = MetricValue.rate(sum(labels), len(labels), zero_reason="no labeled present fields")
    evidence_backed = sum(bool(fact.provenance.evidence_ids) for fact in candidates + canonical)
    total_facts = len(candidates) + len(canonical)
    provenance_coverage = MetricValue.rate(evidence_backed, total_facts, zero_reason="no facts to measure")
    conflict_keys = {(item.subject.entity_id, item.predicate) for item in conflict_items}
    evaluated_keys = present | conflict_keys
    conflict_rate = MetricValue.rate(len(conflict_keys), len(evaluated_keys), zero_reason="no canonical/conflicting fields evaluated")
    return EnrichmentMetrics(field_coverage, field_accuracy, provenance_coverage, conflict_rate)


def _logical_contact_value(contact: ContactPoint) -> str:
    value = contact.value.strip()
    if contact.kind is ContactKind.EMAIL:
        return value.casefold()
    if contact.kind in {ContactKind.PHONE, ContactKind.WHATSAPP}:
        return re.sub(r"\D", "", value)
    return value.rstrip("/").casefold()


def _latest_logical_contacts(contacts: Iterable[ContactPoint]) -> tuple[ContactPoint, ...]:
    latest: dict[tuple[str, str, str, str], ContactPoint] = {}
    for contact in contacts:
        key = (
            contact.owner.entity_type.value,
            contact.owner.entity_id,
            contact.kind.value,
            _logical_contact_value(contact),
        )
        current = latest.get(key)
        if current is None or contact.provenance.generated_at > current.provenance.generated_at:
            latest[key] = contact
        elif current is not None and contact.provenance.generated_at == current.provenance.generated_at:
            rank = {
                ContactStatus.DISCOVERED: 0,
                ContactStatus.UNKNOWN: 1,
                ContactStatus.STALE: 2,
                ContactStatus.INVALID: 3,
                ContactStatus.VALIDATED: 4,
            }
            if rank[contact.status] > rank[current.status]:
                latest[key] = contact
    return tuple(latest.values())


@dataclass(frozen=True, slots=True)
class ContactMetrics:
    logical_contacts: int
    contact_discovery_rate: MetricValue
    validation_rate: MetricValue
    invalid_rate: MetricValue
    stale_rate: MetricValue


def compute_contact_metrics(contacts: Iterable[ContactPoint], *, company_ids: Sequence[str]) -> ContactMetrics:
    logical = _latest_logical_contacts(contacts)
    companies = set(company_ids)
    companies_with_contact = {c.owner.entity_id for c in logical if c.owner.entity_id in companies}
    discovery_rate = MetricValue.rate(
        len(companies_with_contact), len(companies), zero_reason="no companies supplied"
    )
    validation_rate = MetricValue.rate(
        sum(c.status is ContactStatus.VALIDATED for c in logical), len(logical), zero_reason="no contacts discovered"
    )
    invalid_rate = MetricValue.rate(
        sum(c.status is ContactStatus.INVALID for c in logical), len(logical), zero_reason="no contacts discovered"
    )
    stale_rate = MetricValue.rate(
        sum(c.status is ContactStatus.STALE for c in logical), len(logical), zero_reason="no contacts discovered"
    )
    return ContactMetrics(len(logical), discovery_rate, validation_rate, invalid_rate, stale_rate)


@dataclass(frozen=True, slots=True)
class QualificationMetrics:
    precision: MetricValue
    recall: MetricValue
    human_disagreement_rate: MetricValue


def compute_qualification_metrics(
    predictions: Mapping[str, LeadStatus],
    *,
    ground_truth: Mapping[str, bool] | None = None,
    human_decisions: Mapping[str, LeadStatus] | None = None,
) -> QualificationMetrics:
    if ground_truth is None:
        precision = MetricValue.unavailable("qualification ground truth is unavailable; ICP/labels required")
        recall = MetricValue.unavailable("qualification ground truth is unavailable; ICP/labels required")
    else:
        common = set(predictions) & set(ground_truth)
        tp = sum(predictions[key] is LeadStatus.QUALIFIED and ground_truth[key] for key in common)
        fp = sum(predictions[key] is LeadStatus.QUALIFIED and not ground_truth[key] for key in common)
        fn = sum(predictions[key] is not LeadStatus.QUALIFIED and ground_truth[key] for key in common)
        precision = MetricValue.rate(tp, tp + fp, zero_reason="no predicted qualified leads")
        recall = MetricValue.rate(tp, tp + fn, zero_reason="no positive qualification labels")
    if human_decisions is None:
        disagreement = MetricValue.unavailable("human review decisions are not supplied")
    else:
        common = set(predictions) & set(human_decisions)
        disagreements = sum(predictions[key] is not human_decisions[key] for key in common)
        disagreement = MetricValue.rate(disagreements, len(common), zero_reason="no overlapping human decisions")
    return QualificationMetrics(precision, recall, disagreement)


@dataclass(frozen=True, slots=True)
class OperationalMetrics:
    cost_per_discovered_company: MetricValue
    cost_per_enriched_company: MetricValue
    cost_per_qualified_lead: MetricValue
    cost_per_validated_contact: MetricValue
    time_per_lead_seconds: MetricValue


def _per_unit(total: float | None, count: int, missing_reason: str, zero_reason: str) -> MetricValue:
    if total is None:
        return MetricValue.unavailable(missing_reason)
    return MetricValue.rate(total, count, zero_reason=zero_reason)


def compute_operational_metrics(
    *,
    total_cost: float | None = None,
    elapsed_seconds: float | None = None,
    discovered_companies: int = 0,
    enriched_companies: int = 0,
    qualified_leads: int = 0,
    validated_contacts: int = 0,
    processed_leads: int = 0,
) -> OperationalMetrics:
    if total_cost is not None and total_cost < 0:
        raise ValueError("total_cost cannot be negative")
    if elapsed_seconds is not None and elapsed_seconds < 0:
        raise ValueError("elapsed_seconds cannot be negative")
    return OperationalMetrics(
        _per_unit(total_cost, discovered_companies, "cost telemetry is not supplied", "no discovered companies"),
        _per_unit(total_cost, enriched_companies, "cost telemetry is not supplied", "no enriched companies"),
        _per_unit(total_cost, qualified_leads, "cost telemetry is not supplied", "no qualified leads"),
        _per_unit(total_cost, validated_contacts, "cost telemetry is not supplied", "no validated contacts"),
        _per_unit(elapsed_seconds, processed_leads, "elapsed-time telemetry is not supplied", "no processed leads"),
    )
