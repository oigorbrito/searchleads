from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class GateStatus(str, Enum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    NOT_RUN = "NOT_RUN"


@dataclass(frozen=True, slots=True)
class AcceptanceMetrics:
    real_companies: int
    source_count: int
    multi_source_company_count: int
    entity_resolution_rules_verified: bool
    provenance_verified: bool
    contact_discovery_verified: bool
    export_roundtrip_verified: bool
    reproducible_replay_verified: bool
    dedup_labeled_pairs: int
    dedup_false_merge_measured: bool
    dedup_false_split_measured: bool
    icp_defined: bool


@dataclass(frozen=True, slots=True)
class AcceptanceReport:
    real_companies: GateStatus
    multi_source: GateStatus
    company_er: GateStatus
    provenance: GateStatus
    contact_discovery: GateStatus
    export: GateStatus
    reproducible: GateStatus
    deduplication: GateStatus
    qualification: GateStatus

    def as_dict(self) -> dict[str, str]:
        return {
            "REAL_COMPANIES": self.real_companies.value,
            "MULTI_SOURCE": self.multi_source.value,
            "COMPANY_ER": self.company_er.value,
            "PROVENANCE": self.provenance.value,
            "CONTACT_DISCOVERY": self.contact_discovery.value,
            "EXPORT": self.export.value,
            "REPRODUCIBLE": self.reproducible.value,
            "DEDUPLICATION": self.deduplication.value,
            "QUALIFICATION": self.qualification.value,
        }


def evaluate_acceptance(metrics: AcceptanceMetrics) -> AcceptanceReport:
    return AcceptanceReport(
        real_companies=(
            GateStatus.PASS if metrics.real_companies >= 25 else GateStatus.PARTIAL
        ),
        multi_source=(
            GateStatus.PASS
            if metrics.source_count >= 2 and metrics.multi_source_company_count >= 1
            else GateStatus.PARTIAL
        ),
        company_er=(
            GateStatus.PASS if metrics.entity_resolution_rules_verified else GateStatus.NOT_RUN
        ),
        provenance=(GateStatus.PASS if metrics.provenance_verified else GateStatus.NOT_RUN),
        contact_discovery=(
            GateStatus.PASS if metrics.contact_discovery_verified else GateStatus.NOT_RUN
        ),
        export=(GateStatus.PASS if metrics.export_roundtrip_verified else GateStatus.NOT_RUN),
        reproducible=(
            GateStatus.PASS if metrics.reproducible_replay_verified else GateStatus.NOT_RUN
        ),
        deduplication=_dedup_gate(metrics),
        qualification=(GateStatus.PASS if metrics.icp_defined else GateStatus.BLOCKED),
    )


def _dedup_gate(metrics: AcceptanceMetrics) -> GateStatus:
    if (
        metrics.dedup_labeled_pairs > 0
        and metrics.dedup_false_merge_measured
        and metrics.dedup_false_split_measured
    ):
        return GateStatus.PASS
    return GateStatus.PARTIAL
