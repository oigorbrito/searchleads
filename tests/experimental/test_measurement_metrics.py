from __future__ import annotations

import json

import pytest

from searchleads.measurement import metrics as measurement_metrics
from searchleads.measurement.metrics import (
    MetricAvailability,
    MetricValue,
    build_measurement_report,
    compute_entity_resolution_metrics,
)


def test_entity_resolution_metrics_match_known_confusion_matrix() -> None:
    metrics = compute_entity_resolution_metrics(tp=12, fp=3, tn=45, fn=6)

    assert metrics.true_positive == 12
    assert metrics.false_positive == 3
    assert metrics.true_negative == 45
    assert metrics.false_negative == 6
    assert metrics.precision.availability is MetricAvailability.AVAILABLE
    assert metrics.recall.availability is MetricAvailability.AVAILABLE
    assert metrics.f1.availability is MetricAvailability.AVAILABLE
    assert metrics.false_merge_rate.availability is MetricAvailability.AVAILABLE
    assert metrics.false_split_rate.availability is MetricAvailability.AVAILABLE
    assert metrics.precision.value == pytest.approx(12 / 15)
    assert metrics.recall.value == pytest.approx(12 / 18)
    assert metrics.f1.value == pytest.approx(2 * (12 / 15) * (12 / 18) / ((12 / 15) + (12 / 18)))
    assert metrics.false_merge_rate.value == pytest.approx(3 / 48)
    assert metrics.false_split_rate.value == pytest.approx(6 / 18)


def test_entity_resolution_metrics_surface_unavailable_states_without_dividing_by_zero() -> None:
    metrics = compute_entity_resolution_metrics(tp=0, fp=0, tn=9, fn=0)

    assert metrics.precision.availability is MetricAvailability.UNAVAILABLE
    assert metrics.recall.availability is MetricAvailability.UNAVAILABLE
    assert metrics.f1.availability is MetricAvailability.UNAVAILABLE
    assert metrics.false_merge_rate.availability is MetricAvailability.AVAILABLE
    assert metrics.false_merge_rate.value == 0.0
    assert metrics.false_split_rate.availability is MetricAvailability.UNAVAILABLE
    assert metrics.precision.reason == "no predicted matches"
    assert metrics.recall.reason == "no labeled duplicate pairs"


def test_metric_value_validates_available_and_unavailable_contracts() -> None:
    with pytest.raises(ValueError, match="available metric requires value"):
        MetricValue(MetricAvailability.AVAILABLE, None)

    with pytest.raises(ValueError, match="unavailable metric requires reason"):
        MetricValue(MetricAvailability.UNAVAILABLE, None)

    assert MetricValue.unavailable("not measured").availability is MetricAvailability.UNAVAILABLE


def test_measurement_report_serializes_with_fixed_schema_version() -> None:
    discovery = measurement_metrics.DiscoveryMetrics(
        discovered_observations=1,
        unique_entities=1,
        duplicate_discovery_rate=MetricValue.rate(0, 1, zero_reason="no discovery observations"),
        bounded_coverage=MetricValue.unavailable("universe not supplied"),
        discovery_precision=MetricValue.unavailable("ground truth not supplied"),
    )
    enrichment = measurement_metrics.EnrichmentMetrics(
        field_coverage=MetricValue.rate(1, 1, zero_reason="no subject/field slots defined"),
        field_accuracy=MetricValue.unavailable("ground truth not supplied"),
        provenance_coverage=MetricValue.rate(1, 1, zero_reason="no facts to measure"),
        conflict_rate=MetricValue.rate(0, 1, zero_reason="no canonical/conflicting fields evaluated"),
    )
    contacts = measurement_metrics.ContactMetrics(
        logical_contacts=1,
        contact_discovery_rate=MetricValue.rate(1, 1, zero_reason="no owners supplied"),
        validation_rate=MetricValue.rate(1, 1, zero_reason="no contacts discovered"),
        invalid_rate=MetricValue.rate(0, 1, zero_reason="no contacts discovered"),
        stale_rate=MetricValue.rate(0, 1, zero_reason="no contacts discovered"),
    )
    qualification = measurement_metrics.QualificationMetrics(
        precision=MetricValue.unavailable("qualification ground truth is not supplied"),
        recall=MetricValue.unavailable("qualification ground truth is not supplied"),
        human_disagreement_rate=MetricValue.unavailable("human review decisions are not supplied"),
    )
    operation = measurement_metrics.OperationalMetrics(
        cost_per_discovered=MetricValue.unavailable("cost telemetry is not supplied"),
        cost_per_enriched=MetricValue.unavailable("cost telemetry is not supplied"),
        cost_per_qualified=MetricValue.unavailable("cost telemetry is not supplied"),
        cost_per_validated_contact=MetricValue.unavailable("cost telemetry is not supplied"),
        time_per_lead_seconds=MetricValue.unavailable("elapsed-time telemetry is not supplied"),
    )

    report = build_measurement_report(
        scope="er-benchmark",
        discovery=discovery,
        entity_resolution=compute_entity_resolution_metrics(tp=1, fp=0, tn=1, fn=0),
        enrichment=enrichment,
        contacts=contacts,
        qualification=qualification,
        operation=operation,
    )

    payload = json.loads(report.to_json())
    assert payload["schema_version"] == "searchleads_measurement_v1"
    assert payload["scope"] == "er-benchmark"
    assert payload["entity_resolution"]["precision"]["value"] == pytest.approx(1.0)
