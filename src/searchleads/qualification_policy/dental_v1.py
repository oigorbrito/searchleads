from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any


@dataclass(frozen=True, slots=True)
class DentalICPPolicyContractV1:
    policy_id: str = "dental-facial-surgery-education-br-v1"
    version: str = "1"
    decision_basis: str = "BUSINESS_REQUIREMENT_USER_DEFINED_2026_08_21"
    primary_commercial_entity: str = "PERSON"
    country: str = "BR"
    default_offer_track: str = "CEOF_SPECIALIZATION"
    target_profession: str = "DENTISTRY"
    eligible_professional_groups: tuple[str, ...] = (
        "GENERAL_DENTIST",
        "DENTAL_SPECIALIST",
        "BUCOMAXILLOFACIAL",
        "HOF_OR_FACIAL_ACTIVITY",
    )
    core_topics: tuple[str, ...] = (
        "BLEFAROPLASTIA",
        "LIP_LIFT",
        "LIFTING_FACIAL",
        "FRONTOPLASTIA",
    )
    offer_formats: tuple[str, ...] = (
        "IN_PERSON",
        "IMMERSION",
        "MENTORING",
        "LONG_FORM_TRAINING",
        "ONLINE_OR_HYBRID",
    )
    geography_default: str = "BRAZIL_WIDE"
    geography_filters: tuple[str, ...] = ("MACRO_REGION", "STATE")
    company_size_applicable: bool = False
    contact_required_by_default: bool = False
    validated_contact_may_be_required_by_campaign: bool = True
    missing_intent_result: str = "UNKNOWN"
    missing_required_filter_result: str = "UNKNOWN_REVIEW"
    unresolved_required_conflict_result: str = "UNKNOWN_REVIEW"
    ceof_specialization_missing_ceof_result: str = "NOT_REQUIRED_FOR_DEFAULT_TRACK"
    complementary_exclusive_ceof_missing_ceof_result: str = "UNKNOWN_REVIEW"
    complementary_exclusive_ceof_known_non_ceof_result: str = "NOT_QUALIFIED_EXCLUDE"
    fit_levels: tuple[str, ...] = ("HIGH", "MEDIUM", "LOW", "UNKNOWN")
    intent_levels: tuple[str, ...] = ("HIGH", "MEDIUM", "LOW", "UNKNOWN")
    priority_levels: tuple[str, ...] = ("P1", "P2", "P3", "REVIEW", "EXCLUDE")

    def __post_init__(self) -> None:
        if self.policy_id != "dental-facial-surgery-education-br-v1":
            raise ValueError("policy_id is fixed for V1")
        if self.version != "1":
            raise ValueError("version is fixed for V1")
        if self.primary_commercial_entity != "PERSON":
            raise ValueError("the approved V1 commercial target is Person")
        if self.country != "BR":
            raise ValueError("the approved V1 geography is Brazil")
        if self.company_size_applicable:
            raise ValueError("company size is not an ICP criterion in the approved Person-centered V1")
        if self.contact_required_by_default:
            raise ValueError("contactability is not a default ICP eligibility requirement in V1")
        if self.missing_intent_result != "UNKNOWN":
            raise ValueError("absence of intent evidence must remain UNKNOWN")
        if self.unresolved_required_conflict_result != "UNKNOWN_REVIEW":
            raise ValueError("unresolved required conflicts must not be coerced to a decision")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


APPROVED_DENTAL_ICP_POLICY_V1 = DentalICPPolicyContractV1()
